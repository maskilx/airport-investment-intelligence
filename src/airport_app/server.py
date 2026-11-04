"""HTTP API + static workspace UI.

  GET  /api/health                              backend, model, data build, catalog version
  GET  /api/conversations                       list
  POST /api/conversations                       create -> {id}
  GET  /api/conversations/{id}                  turns (question + rendered answer + charts), for reload
  POST /api/conversations/{id}/messages         {text} -> Server-Sent Events stream of agent events
  POST /api/conversations/{id}/cancel           stop the running turn (between steps)
  GET  /api/conversations/{id}/findings/{fid}   full provenance (definition, inputs, sources, exact fetch URLs)
  GET  /api/conversations/{id}/memory           memory inspector: state, summary, findings index, context stats
  GET  /api/sources                             data sources (title, publisher, license, homepage)
Everything model-related is behind airport_agent.models.backend_from_env(): offline by default, Gemini only when
explicitly enabled. No endpoint ever triggers a model call except posting a message.
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from airport_analytics.engine import Engine
from airport_analytics.render import fmt_value
from airport_analytics.semantic import CATALOG_VERSION
from airport_analytics.tools import Session
from airport_agent.memory import ContextBuilder, ConversationStore
from airport_agent.models import backend_from_env
from airport_agent.provenance import Provenance
from airport_agent.runtime import Agent
from airport_data.db import connect

WEB = Path(__file__).resolve().parents[2] / "web"


class Message(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    client_turn_id: str | None = Field(default=None, max_length=80)   # voice/retry de-duplication


class App:
    """Process-wide state: one read-only DuckDB, one conversation store, one model backend, agents per conversation."""

    def __init__(self, store_path: str | None = None, backend=None, extra_tools_factory=None):
        self.con = connect()
        from airport_data.config import get_paths
        default_store = get_paths().app / "conversations.sqlite"          # anchored: same history from any cwd
        default_store.parent.mkdir(parents=True, exist_ok=True)
        self.store = ConversationStore(store_path or os.environ.get("AIRPORT_CONV_DB") or str(default_store))
        self.backend = backend or backend_from_env()
        self.prov = Provenance(self.con.cursor())
        self.extra_tools_factory = extra_tools_factory
        # web research is offered to LLM planners (the offline planner never uses it); AIRPORT_WEB=0 disables it
        self.web_enabled = os.environ.get("AIRPORT_WEB", "1") != "0" and getattr(self.backend, "name", "") not in ("offline",)
        self.web_factory = None
        self.agents: dict[str, Agent] = {}
        from airport_agent.evidence_files import RawFiles
        from airport_data.config import get_paths as _gp
        self.raw_files = RawFiles(_gp().raw)                 # read-only, archive-only file access for the inspector
        from airport_agent.voice import Dedup, VoiceError, transcriber_from_env
        self.voice_dedup = Dedup()
        try:
            self.transcriber, self.voice_error = transcriber_from_env(), None
        except VoiceError as e:                              # voice misconfig never blocks text chat
            self.transcriber, self.voice_error = None, str(e)
        self.cancels: dict[str, set[threading.Event]] = {}     # one event per in-flight turn (never overwritten)
        self.lock = threading.Lock()

    def agent(self, cid: str) -> Agent:
        with self.lock:
            if cid not in self.agents:
                if not any(c["id"] == cid for c in self.store.list()):
                    raise HTTPException(404, "unknown conversation")
                sess = Session(Engine(self.con.cursor()))
                extra = self.extra_tools_factory(cid) if self.extra_tools_factory else None
                self.agents[cid] = Agent(self.backend, sess, self.store, cid, extra_tools=extra,
                                         web=self.web_enabled and (self.web_factory() if self.web_factory else True))
            return self.agents[cid]

    def build_info(self) -> dict:
        try:
            r = self.con.execute("SELECT * FROM build_info LIMIT 1").fetchone()
            cols = [d[0] for d in self.con.description]
            return dict(zip(cols, map(str, r))) if r else {}
        except Exception:
            return {}


def create_app(state: App | None = None) -> FastAPI:
    api = FastAPI(title="Airport Investment Intelligence", version="3.0")
    st = state or App()
    api.state.app = st

    @api.get("/api/health")
    def health():
        b = st.backend
        budget = {"used_today": b.requests, "max_per_day": b.max_requests} if hasattr(b, "max_requests") else None
        return {"ok": True, "backend": getattr(b, "name", "?"), "model": getattr(b, "model", None), "web": st.web_enabled,
                "llm": getattr(b, "name", "") not in ("offline", "scripted"), "catalog_version": CATALOG_VERSION,
                "build": st.build_info(), "budget": budget}

    @api.get("/api/conversations")
    def conversations():
        return st.store.list()

    @api.post("/api/conversations")
    def create():
        cid = uuid.uuid4().hex[:12]
        st.store.create(cid, "")
        return {"id": cid}

    @api.get("/api/conversations/{cid}")
    def conversation(cid: str):
        st.agent(cid)
        turns = [{"turn": t["turn"], "question": t.get("question"), "kind": t["kind"], "answer": t.get("answer"),
                  "tool_calls": [{"tool": c["tool"], "error": c["error"], "elapsed_s": c.get("elapsed_s")}
                                 for c in t.get("tool_calls", [])],
                  "usage": t.get("usage"), "latency_s": t.get("latency_s"), "context": t.get("context")}
                 for t in st.store.traces(cid)]
        meta = next((c for c in st.store.list() if c["id"] == cid), {})
        return {"id": cid, "title": meta.get("title", ""), "turns": turns}

    @api.get("/api/voice/config")
    def voice_config():
        return {"stt": "groq" if st.transcriber else "browser", "stt_model": getattr(st.transcriber, "model", None),
                "tts": "browser", "language": "en-US", "error": st.voice_error}

    @api.post("/api/voice/transcribe")
    async def transcribe(request: Request):
        from airport_agent.voice import VoiceError, is_wav
        if not st.transcriber:
            raise HTTPException(409, "server speech-to-text is not configured (AIRPORT_VOICE_STT=groq)")
        uid = request.headers.get("x-utterance-id") or ""
        hit = st.voice_dedup.seen(f"u:{uid}") if uid else None
        if hit is not None:                                  # a reconnect re-sent the same utterance: no second call
            return {"text": hit, "utterance_id": uid, "duplicate": True}
        body = await request.body()
        if not is_wav(body) or len(body) > 5_000_000:
            raise HTTPException(400, "expected a WAV utterance under 5 MB")
        try:
            text = await asyncio.get_running_loop().run_in_executor(None, st.transcriber.transcribe, body)
        except VoiceError as e:
            raise HTTPException(503, str(e))
        if uid:
            st.voice_dedup.remember(f"u:{uid}", text)
        return {"text": text, "utterance_id": uid, "duplicate": False}

    @api.post("/api/conversations/{cid}/messages")
    async def message(cid: str, m: Message):
        agent = st.agent(cid)
        if m.client_turn_id:
            key = f"t:{cid}:{m.client_turn_id}"
            if st.voice_dedup.seen(key) is not None:
                async def dup():
                    yield f"event: duplicate\ndata: {json.dumps({'type': 'duplicate'})}\n\n"
                    yield f"event: done\ndata: {json.dumps({'type': 'done'})}\n\n"
                return StreamingResponse(dup(), media_type="text/event-stream")
            st.voice_dedup.remember(key)
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()
        cancel = threading.Event()
        with st.lock:
            st.cancels.setdefault(cid, set()).add(cancel)

        def emit(e: dict):
            loop.call_soon_threadsafe(q.put_nowait, e)

        def run():
            try:
                agent.ask(m.text, on_event=emit, cancel=cancel)
            except Exception as e:                       # surface (number-free), never hang the stream
                import logging
                logging.getLogger("airport_app").exception("turn failed: %s", e)
                emit({"type": "error", "message": "The turn failed unexpectedly; details are in the server log."})
            finally:
                with st.lock:
                    st.cancels.get(cid, set()).discard(cancel)
                emit({"type": "done"})

        threading.Thread(target=run, daemon=True).start()

        async def stream():
            while True:
                e = await q.get()
                yield f"event: {e['type']}\ndata: {json.dumps(e, default=str)}\n\n"
                if e["type"] == "done":
                    break
        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @api.post("/api/conversations/{cid}/cancel")
    def cancel(cid: str):
        with st.lock:
            evs = list(st.cancels.get(cid, ()))
        for ev in evs:                                   # stops every in-flight turn of this conversation
            ev.set()
        return {"cancelled": bool(evs), "turns": len(evs)}

    @api.get("/api/conversations/{cid}/findings/{fid}")
    def finding(cid: str, fid: str):
        a = st.agent(cid)
        if fid not in a.evidence:
            raise HTTPException(404, f"{fid} is not a finding of this conversation")
        f = a.evidence.get(fid)
        d = st.prov.finding(f)
        d["formatted"] = fmt_value(f)
        d["input_findings"] = [{"id": i, "label": a.evidence.get(i).label, "formatted": fmt_value(a.evidence.get(i))}
                               for i in f.inputs if i in a.evidence]
        d["cited_in_turns"] = [x["turn"] for x in a.state.answers if fid in x.get("cited", [])]
        return d

    # ---------------- local evidence explorer: data used, original files (read-only, bounded, archive-only)
    @api.get("/api/conversations/{cid}/findings/{fid}/data")
    def finding_data(cid: str, fid: str, page: int = 0):
        from airport_analytics.evidence_data import data_used
        a = st.agent(cid)
        if fid not in a.evidence:
            raise HTTPException(404, f"{fid} is not a finding of this conversation")
        try:
            eng = Engine(st.con.cursor())                    # own cursor: never shares one with a running turn
            with eng.guard(20.0):
                return data_used(eng, a.evidence.get(fid), a.evidence, page=page)
        except Exception as e:                           # never break the inspector: report the traceability gap
            return {"level": "source", "summary": "The underlying rows could not be listed for this result "
                    f"({type(e).__name__}); the source files and periods are shown below."}

    @api.get("/api/evidence/vintage/{source_id}/{period}/{vintage_id}")
    def evidence_vintage(source_id: str, period: str, vintage_id: str):
        from airport_agent.evidence_files import EvidenceFileError
        try:
            meta = st.raw_files.meta(source_id, period, vintage_id)
        except EvidenceFileError as e:
            raise HTTPException(e.status, str(e))
        man = st.con.cursor().execute(
            "SELECT validation_status, row_counts, stored_at, url FROM ingest_manifest WHERE source_id = ? AND period = ? "
            "AND vintage_id = ?", [source_id, period, vintage_id]).fetchone()
        src = st.prov.source(source_id) or {}
        from airport_agent.provenance import link_for
        req = meta.get("request") or {}
        return {"source_id": source_id, "dataset": src.get("title") or meta.get("source_title"), "publisher": src.get("publisher"),
                "license": meta.get("license"), "period": period, "vintage_id": vintage_id,
                "downloaded_at": meta.get("stored_at"), "content_sha256": meta.get("content_sha256"),
                "files": [{"name": f["name"], "bytes": f.get("bytes"), "sha256": f.get("sha256")} for f in meta.get("files", [])],
                "request": {"method": req.get("method", "POST" if req.get("fields") else "GET"),
                            "fields": len(req.get("fields") or [])},
                "validation": man[0] if man else None,
                "rows_loaded": json.loads(man[1]) if man and man[1] else None,
                "publisher_links": ([{"label": "Official dataset page", "url": src["homepage"], "kind": "page"}]
                                    if src.get("homepage") else []) + [
                    {**l, "label": {"file": "Direct raw-file download", "form": "Download form"}.get(l["kind"], l["label"])}
                    for l in link_for(source_id, meta.get("url"))]}

    @api.get("/api/evidence/file/{source_id}/{period}/{vintage_id}/{name}/preview")
    def evidence_preview(source_id: str, period: str, vintage_id: str, name: str, member: str | None = None,
                         sheet: str | None = None, page: int = 0, find: str | None = None):
        from airport_agent.evidence_files import EvidenceFileError
        try:
            p = st.raw_files.file(source_id, period, vintage_id, name)
            return st.raw_files.preview(p, member=member, sheet=sheet, page=page, find=find)
        except EvidenceFileError as e:
            raise HTTPException(e.status, str(e))
        except Exception as e:
            raise HTTPException(422, f"preview not available ({type(e).__name__})")

    @api.get("/api/evidence/file/{source_id}/{period}/{vintage_id}/{name}/download")
    def evidence_download(source_id: str, period: str, vintage_id: str, name: str):
        from airport_agent.evidence_files import EvidenceFileError
        try:
            p = st.raw_files.file(source_id, period, vintage_id, name)
        except EvidenceFileError as e:
            raise HTTPException(e.status, str(e))
        return FileResponse(p, filename=p.name, media_type="application/octet-stream")

    @api.get("/api/conversations/{cid}/external/{wid}")
    def external(cid: str, wid: str):
        a = st.agent(cid)
        web = a.web_evidence
        if wid not in web:
            raise HTTPException(404, f"{wid} is not an external source of this conversation")
        from airport_agent.web import public_record
        return public_record(web[wid])

    @api.get("/api/conversations/{cid}/memory")
    def memory(cid: str):
        a = st.agent(cid)
        cb = ContextBuilder(st.store, a.ctx.budget)
        mem, recent, stats = cb.build(cid, "", a.state, a.evidence, fmt_value)
        s = a.state
        return {"budget": a.ctx.budget.__dict__, "context_stats": stats, "memory_block": mem,
                "summary": st.store.latest_summary(cid),
                "state": {"entities": [{"key": k, **e} for k, e in s.focus(50)], "metrics": s.metrics,
                          "assumptions": s.assumptions, "decisions": s.decisions, "preferences": s.preferences, "lists": s.lists,
                          "answers": s.answers[-30:]},
                "findings_total": len(a.evidence.all()), "usage": a.usage.__dict__}

    @api.get("/api/sources")
    def sources():
        rows = st.con.cursor().execute("SELECT id, title, publisher, license, homepage, cadence FROM source_catalog "
                                       "ORDER BY id").fetchall()
        return [dict(zip(("id", "title", "publisher", "license", "homepage", "cadence"), r)) for r in rows]

    if WEB.exists():
        api.mount("/static", StaticFiles(directory=WEB), name="static")

        @api.get("/")
        def index():
            return FileResponse(WEB / "index.html")
    return api


def main() -> None:                                       # python -m airport_app [--port N]
    import argparse

    import uvicorn
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    a = p.parse_args()
    from airport_data.config import get_paths, load_env
    loaded = load_env()
    paths = get_paths()
    line = "-" * 72
    print(line)
    print("Airport Investment Intelligence: local workspace")
    if loaded:
        print(f"  .env loaded        : {', '.join(sorted(loaded))} (values not shown)")
    if not paths.db_file.exists():
        print(f"  ERROR: database not found at {paths.db_file}")
        print("  Build it first:  ./scripts/bootstrap.sh   (or: .venv/bin/python -m airport_data build)")
        raise SystemExit(2)
    try:
        app = create_app()
    except Exception as e:                               # misconfiguration: say what to fix, never fall back
        print(f"  ERROR: could not start the model backend: {e}")
        print("  Offline mode needs no key: ./scripts/mode.sh offline")
        raise SystemExit(2)
    st = app.state.app
    b = st.backend
    if getattr(b, "name", "") == "groq":
        print(f"  Mode               : GROQ    (model {b.model}; {b.requests}/{b.max_requests} requests used today, "
              f"UTC; per-request context cap {b.max_context_tokens}; no fallback)")
        print(f"  Usage log          : {b.usage_log}")
    elif getattr(b, "name", "") == "gemini":
        print(f"  Mode               : GEMINI  (model {b.model}; {b.requests}/{b.max_requests} requests used today, "
              f"UTC; no paid fallback)")
        print(f"  Usage log          : {b.usage_log}")
    else:
        print(f"  Mode               : OFFLINE (rule-based planner; no model API calls)")
    bi = st.build_info()
    print(f"  Database           : {paths.db_file}  (built {bi.get('built_at', '?')}, rev {bi.get('git_rev', '?')})")
    print(f"  Conversations      : {st.store.path if hasattr(st.store, 'path') else paths.app}")
    print(f"  Web research       : {'on' if st.web_enabled else 'off'}")
    print(f"  Open               : http://{a.host}:{a.port}")
    print(line, flush=True)
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")


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
from fastapi import FastAPI, HTTPException
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


class App:
    """Process-wide state: one read-only DuckDB, one conversation store, one model backend, agents per conversation."""

    def __init__(self, store_path: str | None = None, backend=None, extra_tools_factory=None):
        self.con = connect()
        self.store = ConversationStore(store_path or os.environ.get("AIRPORT_CONV_DB", "data/app/conversations.sqlite"))
        self.backend = backend or backend_from_env()
        self.prov = Provenance(self.con.cursor())
        self.extra_tools_factory = extra_tools_factory
        self.agents: dict[str, Agent] = {}
        self.cancels: dict[str, threading.Event] = {}
        self.lock = threading.Lock()

    def agent(self, cid: str) -> Agent:
        with self.lock:
            if cid not in self.agents:
                if not any(c["id"] == cid for c in self.store.list()):
                    raise HTTPException(404, "unknown conversation")
                sess = Session(Engine(self.con.cursor()))
                extra = self.extra_tools_factory(cid) if self.extra_tools_factory else None
                self.agents[cid] = Agent(self.backend, sess, self.store, cid, extra_tools=extra)
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
        return {"ok": True, "backend": getattr(b, "name", "?"), "model": getattr(b, "model", None),
                "llm": getattr(b, "name", "") not in ("offline", "scripted"), "catalog_version": CATALOG_VERSION,
                "build": st.build_info()}

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

    @api.post("/api/conversations/{cid}/messages")
    async def message(cid: str, m: Message):
        agent = st.agent(cid)
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()
        cancel = threading.Event()
        st.cancels[cid] = cancel

        def emit(e: dict):
            loop.call_soon_threadsafe(q.put_nowait, e)

        def run():
            try:
                agent.ask(m.text, on_event=emit, cancel=cancel)
            except Exception as e:                       # surface, never hang the stream
                emit({"type": "error", "message": f"{type(e).__name__}: {e}"})
            finally:
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
        ev = st.cancels.get(cid)
        if ev:
            ev.set()
        return {"cancelled": bool(ev)}

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

    @api.get("/api/conversations/{cid}/external/{wid}")
    def external(cid: str, wid: str):
        a = st.agent(cid)
        web = getattr(a, "web_evidence", None) or {}
        if wid not in web:
            raise HTTPException(404, f"{wid} is not an external source of this conversation")
        return web[wid]

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
    uvicorn.run(create_app(), host=a.host, port=a.port, log_level="info")


"""Agent runtime: provider-agnostic tool loop + conversation memory + events + budgets.

One `Agent` per conversation. Per turn it:
  1. builds a token-budgeted context (memory.ContextBuilder): recent turns verbatim, older tool payloads collapsed to
     F# pointers, and a memory block (state, authoritative findings index, number-free summary, retrieved turns)
     pinned next to the question;
  2. runs the model/tool loop under step, tool-call, wall-clock and cancellation budgets, emitting events
     (for the streaming API / UI);
  3. accepts a final answer only via compose_answer (grounding-validated) or as a number-free clarification;
  4. persists transcript, findings (stable ids), state changes, a trace, and rolls the summary forward.
"""
from __future__ import annotations

import json
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from airport_analytics.render import ALLOW, ALLOWED_WORD_USES, NUMBER_WORDS, PH, _numeric_chars, fmt_value
from airport_analytics.tools import Session, tool_schemas

from .assumptions import on_change as on_assumption_change
from .assumptions import tag_new as tag_new_findings
from .charts import build_charts
from .memory import Budget, ContextBuilder, ConversationState, ConversationStore, FID, retrieve
from .models import ModelBackend, ModelError, ModelResponse, Usage

SYSTEM_PROMPT = """You are an airport-investment analyst assistant for a firm that invests in US airport modernization.
You answer ONLY with evidence produced by the tools. Workflow:
1. Identify entities (airports, regions), metrics, periods, comparisons. Call resolve_entities for places.
   - Ambiguous place (e.g. "Portland") and not a contrast that makes the intent clear -> ask a clarification question.
   - Contrast questions ("LA vs Santa Ana") -> bind each side to its most specific airport and STATE the assumption.
2. Use describe_catalog to pick valid metric ids; never invent ids. Compose analyses with run_analysis
   (ops: aggregate, rank, correlate, trend, anomaly, distribution, forecast_vs_actual, screen; metric transforms
   pct_change/abs_change/cagr). Multi-part questions = several run_analysis calls. Use derive for any arithmetic
   between findings. Use query_sql only when no catalog metric fits; its results are 'exploratory'.
3. Tool errors are information: out_of_coverage / not_applicable / insufficient_data / ambiguous_entity mean you
   must say what cannot be established (and why), or ask, or narrow the question. Never fill gaps yourself.
4. Finish with compose_answer: every number as a {F#} placeholder; claims labelled fact / inference / hypothesis
   with supporting finding ids; assumptions and limitations explicit. Distinguish observed, calculated, forecast,
   estimated values (the renderer labels them). Do not present hypotheses (causes, unmet demand, profitability) as
   facts. Unmet demand, terminal capacity, fares and profitability are NOT directly measured by this data — say so.
   Add charts:[{type, title, findings:[F#...]}] when a comparison, ranking or series is clearer as a chart.
5. For investment rankings use op=screen (a screening rank, not a valuation) and mention its flags and ties.
If a question cannot be answered with the available data, reply with a short plain-text explanation (no numbers)
of what is missing, or answer the closest answerable part via compose_answer and state the gap.

Conversation memory:
- The latest user message may start with a memory block: conversation state, a findings index, a summary of earlier
  turns and retrieved earlier turns. Findings listed there are authoritative and can be cited by id without re-running.
  The summary contains no numbers by design — never take values from it; cite findings.
- References like "that airport", "the second one", "same period" refer to the entities in focus (most recent first).
  State your interpretation as an assumption; if two readings are equally plausible, ask.
- When the user corrects you or changes an assumption, call update_memory (set_assumption with replaces=A#, or
  retract_assumption). If the assumption is a metric parameter or a screen option, pass binds (e.g. {metric:
  "long_haul_share", param: "min_miles", value: ...}); assumption text itself must contain no numbers. Code then marks
  dependent findings STALE; stale findings cannot be cited — re-run the affected analyses.
- Use recall to search older turns and findings when the memory block does not contain what the user refers to.

External web research (only if web_search / fetch_page are available):
- Use it only for context the internal data cannot provide (announced terminal programs, capacity projects, airline or
  airport announcements, regulatory caps). Never use the web for a metric the catalog covers.
- Cite web content only through claims {kind: "external", text, source: "W#", quote: "<verbatim words from the page>"}.
  Numbers from the web may appear only inside the verbatim quote. Keep internal findings and external sources distinct
  in the prose; say when sources disagree or are dated."""

MEMORY_TOOLS = [
    {"name": "recall",
     "description": "Search the whole conversation (older turns, their answers and findings) by keywords, airport codes or "
                    "finding ids. Returns matching turns and the findings they cited (values from the evidence store).",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer"}},
                      "required": ["query"]}},
    {"name": "update_memory",
     "description": "Record conversation memory: set_assumption {text (no numbers), replaces?: A#, binds?: {metric, param, "
                    "value} | {screen_option: scenario|min_enplanements, value}} | retract_assumption {id: A#} | "
                    "note_decision {text (no numbers), support: [F#]} | set_preference {key, text}. Bound assumptions are "
                    "enforced: findings computed with a different parameter value become stale and cannot be cited.",
     "input_schema": {"type": "object", "properties": {
         "action": {"enum": ["set_assumption", "retract_assumption", "note_decision", "set_preference"]},
         "text": {"type": "string"}, "id": {"type": "string"}, "replaces": {"type": "string"},
         "binds": {"type": "object", "properties": {"metric": {"type": "string"}, "param": {"type": "string"},
                                                    "screen_option": {"type": "string"},
                                                    "value": {"type": ["string", "number"]}}},
         "support": {"type": "array", "items": {"type": "string"}}, "key": {"type": "string"}}, "required": ["action"]}},
]


@dataclass
class Limits:
    max_steps: int = 14            # model requests per turn
    max_tool_calls: int = 30
    wall_clock_s: float = 240.0
    max_tool_result_chars: int = 60_000


@dataclass
class TurnResult:
    kind: str                         # answer | clarification | fallback | stopped | error
    markdown: str
    tool_calls: list[dict] = field(default_factory=list)
    cited_findings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    structured: dict | None = None
    charts: list[dict] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    turn: int = 0
    trace: dict = field(default_factory=dict)


def _has_numbers(text: str) -> bool:
    """A plain-text reply (clarification / refusal) must carry no quantity: digits, number words or Unicode numerals."""
    t = PH.sub("", text)
    return bool(re.search(r"\d", ALLOW.sub("", t)) or NUMBER_WORDS.search(ALLOWED_WORD_USES.sub("", t))
                or _numeric_chars(t))


def _normalize(msgs: list[dict]) -> list[dict]:
    """Canonical blocks; merge consecutive same-role messages (providers require alternation)."""
    out: list[dict] = []
    for m in msgs:
        blocks = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": m["content"]}]
        if out and out[-1]["role"] == m["role"]:
            out[-1]["content"] = out[-1]["content"] + blocks
        else:
            out.append({"role": m["role"], "content": list(blocks)})
    return out


def _summarise_result(name: str, res: Any) -> dict:
    """Small, UI-friendly digest of a tool result (the full result is sent too, truncated)."""
    if not isinstance(res, dict):
        return {}
    if res.get("error"):
        return {"error": res["error"], "message": str(res.get("message", ""))[:300]}
    ids = sorted(set(FID.findall(json.dumps(res, default=str))), key=lambda x: int(x[1:]))
    d: dict[str, Any] = {"findings": ids[:400]}
    if name == "run_analysis":
        d["op"] = res.get("op")
        if res.get("entities"):
            d["entities"] = res["entities"]
    if name in ("fetch_page", "web_search"):
        d = {"external": [res["id"]]} if res.get("id") else {"results": len(res.get("results", []))}
        return d
    if name == "resolve_entities":
        d["resolutions"] = [{"term": r.get("term") or r.get("group"), "kind": r.get("kind")} for r in res.get("resolutions", [])]
    return d


class Agent:
    def __init__(self, backend: ModelBackend, session: Session | None = None, store: ConversationStore | None = None,
                 conv_id: str | None = None, budget: Budget | None = None, limits: Limits | None = None,
                 summarizer: Callable[[str], str] | None = None, extra_tools: dict[str, tuple[dict, Callable]] | None = None,
                 max_steps: int | None = None, web: Any = None):
        self.backend = backend
        self.session = session or Session()
        self.store = store or ConversationStore(":memory:")
        self.conv_id = conv_id or uuid.uuid4().hex[:12]
        self.store.create(self.conv_id)
        loaded = self.store.load_findings(self.conv_id)
        if loaded.all():
            self.session.ctx.store = loaded
        self.state = self.store.load_state(self.conv_id)
        self.ctx = ContextBuilder(self.store, budget)
        self.limits = limits or Limits()
        if max_steps:
            self.limits.max_steps = max_steps
        self.summarizer = summarizer
        self.extra_tools = dict(extra_tools or {})
        self.session.web = self.store.load_external(self.conv_id)        # W# external evidence (own namespace)
        self.web = None
        if web:
            from .web import WebResearch
            self.web = web if isinstance(web, WebResearch) else WebResearch()
            self.web.items = self.session.web
            self.extra_tools.update(self.web.tools())
        self.usage = Usage()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ public
    @property
    def evidence(self):
        return self.session.ctx.store

    @property
    def web_evidence(self) -> dict[str, dict]:
        return self.session.web

    def tools(self) -> list[dict]:
        return tool_schemas() + MEMORY_TOOLS + [s for s, _ in self.extra_tools.values()]

    def ask(self, question: str, on_event: Callable[[dict], None] | None = None,
            cancel: threading.Event | None = None) -> TurnResult:
        with self._lock:                                     # one turn at a time per conversation
            return self._ask(question, on_event or (lambda e: None), cancel or threading.Event())

    # ------------------------------------------------------------------ turn
    def _ask(self, question: str, emit: Callable[[dict], None], cancel: threading.Event) -> TurnResult:
        t0 = time.time()
        cid = self.conv_id
        turn = self.store.last_turn(cid) + 1
        if turn == 1:
            self.store.set_title(cid, question.strip()[:80])
        emit({"type": "turn_started", "turn": turn, "question": question})
        if self.web:
            self.web.new_turn()
        mem, recent, ctx_stats = self.ctx.build(cid, question, self.state, self.evidence, fmt_value)
        emit({"type": "context", "turn": turn, **ctx_stats})
        user_for_model = f"{mem}\n\n## Current question\n{question}" if mem else question
        self.store.append(cid, turn, "user", question)
        msgs = _normalize(recent + [{"role": "user", "content": user_for_model}])
        calls: list[dict] = []
        usage = Usage()
        changes: list[dict] = []
        nudges = 0
        result: TurnResult | None = None
        steps = 0

        def persist(role, content):
            msgs.append({"role": role, "content": content})
            self.store.append(cid, turn, role, content)

        while result is None:
            if cancel.is_set():
                result = TurnResult("stopped", "Stopped by the user. Analyses already run are kept as findings.", calls)
                break
            if steps >= self.limits.max_steps or len(calls) >= self.limits.max_tool_calls or \
                    time.time() - t0 > self.limits.wall_clock_s:
                break
            steps += 1
            emit({"type": "model_request", "turn": turn, "step": steps})
            try:
                out = self.backend.complete(SYSTEM_PROMPT, _normalize(msgs), self.tools())
            except ModelError as e:
                emit({"type": "error", "turn": turn, "message": str(e)})
                result = TurnResult("error", f"The model provider returned an error: {e}", calls, errors=[str(e)])
                break
            if isinstance(out, dict):                          # legacy backends returning dicts
                out = ModelResponse(out["content"], out.get("stop_reason", "end_turn"))
            usage.add(out.usage)
            emit({"type": "model_response", "turn": turn, "step": steps, "latency_s": round(out.latency_s, 3),
                  "input_tokens": out.usage.input_tokens, "output_tokens": out.usage.output_tokens,
                  "tool_calls": [b["name"] for b in out.content if b.get("type") == "tool_use"]})
            blocks = out.content or []
            persist("assistant", blocks)
            uses = [b for b in blocks if b.get("type") == "tool_use"]
            thought = "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
            if uses and thought and not _has_numbers(thought):
                emit({"type": "thinking", "turn": turn, "text": thought[:600]})
            if not uses:
                if thought and not _has_numbers(thought):
                    result = TurnResult("clarification", thought, calls)
                    break
                if nudges < 2:
                    nudges += 1
                    note = ("System: final answers containing numbers must be submitted through compose_answer with {F#} "
                            "placeholders." if thought else "System: you stopped without an answer. Continue: call the "
                            "tools you need and finish with compose_answer (or ask a clarification question without numbers).")
                    persist("user", note)
                    continue
                break
            results = []
            for u in uses:
                name, args = u["name"], u.get("input") or {}
                emit({"type": "tool_started", "turn": turn, "id": u["id"], "name": name, "input": args})
                ts = time.time()
                res = self._call_tool(name, args, turn, changes)
                el = round(time.time() - ts, 3)
                err = res.get("error") if isinstance(res, dict) else None
                calls.append({"tool": name, "input": args, "error": err, "elapsed_s": el})
                digest = _summarise_result(name, res)
                if name == "compose_answer" and isinstance(res, dict) and "markdown" in res:
                    charts = build_charts(res["structured"], self.evidence)
                    cited = list(dict.fromkeys(res["cited_findings"] + [f for c in charts for f in c["findings"]]))
                    ans = args.get("answer") or args
                    self.state.answers.append({"turn": turn, "question": question[:300],
                                               "headline": str(ans.get("headline", ""))[:300], "cited": cited})
                    results.append({"type": "tool_result", "tool_use_id": u["id"], "name": name,
                                    "content": f"Answer rendered and shown to the user; cited {', '.join(cited)}"})
                    emit({"type": "tool_finished", "turn": turn, "id": u["id"], "name": name, "ok": True,
                          "elapsed_s": el, "digest": {"findings": cited}})
                    res["structured"]["evidence_detail"] = [self._brief(f) for f in dict.fromkeys(
                        res["structured"]["evidence"] + cited) if f in self.evidence]
                    result = TurnResult("answer", res["markdown"], calls, cited, structured=res["structured"],
                                        charts=charts)
                    break
                emit({"type": "tool_finished", "turn": turn, "id": u["id"], "name": name, "ok": not err,
                      "elapsed_s": el, "digest": digest,
                      "result": res if len(json.dumps(res, default=str)) < 40_000 else {"truncated": True, **digest}})
                results.append({"type": "tool_result", "tool_use_id": u["id"], "name": name,
                                "content": json.dumps(res, default=str)[: self.limits.max_tool_result_chars]})
            persist("user", results)
        if result is None:
            made = [c for c in calls if c["tool"] == "run_analysis" and not c["error"]]
            why = "time" if time.time() - t0 > self.limits.wall_clock_s else "step"
            ran = "The analyses that did run are recorded and remain available as findings" if made else \
                "No analysis completed"
            result = TurnResult("fallback", f"I could not produce a validated answer within the {why} budget. "
                                f"{ran}; please rephrase or narrow the question.", calls,
                                errors=[f"no validated compose_answer within {why} budget"])
            persist("assistant", [{"type": "text", "text": result.markdown}])
        elif result.kind in ("stopped", "error"):
            persist("assistant", [{"type": "text", "text": result.markdown}])
        if result.kind in ("clarification", "fallback", "stopped", "error"):
            self.state.answers.append({"turn": turn, "question": question[:300], "headline": f"({result.kind})",
                                       "cited": []})
        result.usage, result.turn = usage, turn
        self.usage.add(usage)
        # persist evidence + state; compaction
        self.store.save_findings(cid, self.evidence)
        self.store.save_external(cid, self.session.web)
        self.store.save_state(cid, self.state, turn, changes)
        comp = self.ctx.maybe_compact(cid, self.state, self.summarizer)
        if comp:
            emit({"type": "memory_compacted", "turn": turn, **comp})
        result.trace = {"turn": turn, "conv_id": cid, "backend": getattr(self.backend, "name", type(self.backend).__name__),
                        "kind": result.kind, "steps": steps, "tool_calls": calls, "latency_s": round(time.time() - t0, 3),
                        "usage": usage.__dict__, "context": ctx_stats, "state_changes": changes,
                        "cited": result.cited_findings, "errors": result.errors, "question": question,
                        "answer": {"markdown": result.markdown, "structured": result.structured, "charts": result.charts}}
        self.store.save_trace(cid, turn, result.trace)
        self.store.touch(cid)
        emit({"type": "answer", "turn": turn, "kind": result.kind, "markdown": result.markdown,
              "structured": result.structured, "charts": result.charts, "cited": result.cited_findings,
              "usage": usage.__dict__, "latency_s": result.trace["latency_s"]})
        return result

    # ------------------------------------------------------------------ tools
    def _call_tool(self, name: str, args: dict, turn: int, changes: list[dict]) -> Any:
        if name == "recall":
            return self._recall(args)
        if name == "update_memory":
            ch, err = self.state.apply_update(args, turn)
            if err:
                return {"error": "invalid_memory_update", "message": err}
            changes.append(ch)
            out = {"ok": True, "change": ch}
            if ch["op"] in ("assumption_set", "assumption_retracted"):
                old_id = ch.get("replaces") if ch["op"] == "assumption_set" else ch["id"]
                old = next((a for a in self.state.assumptions if a["id"] == old_id), None) if old_id else None
                new = next((a for a in self.state.assumptions if a["id"] == ch["id"]), None) \
                    if ch["op"] == "assumption_set" else None
                stale = on_assumption_change(self.evidence, old, new)
                if stale:
                    out["stale_findings"] = stale
                    out["note"] = "these findings no longer hold under the current assumptions and cannot be cited; re-run"
                    changes.append({"op": "findings_stale", "ids": [x["id"] for x in stale], "turn": turn})
            return out
        if name in self.extra_tools:
            try:
                return self.extra_tools[name][1](args)
            except Exception as e:                                    # tool errors are information for the model
                return {"error": "tool_failed", "message": f"{type(e).__name__}: {e}"}
        n0 = len(self.evidence)
        res = self.session.call(name, args)
        born_stale = tag_new_findings(self.evidence.added_since(n0), self.state.active_assumptions(), self.evidence)
        if born_stale and isinstance(res, dict):
            res["stale_findings"] = born_stale
            res["note"] = ("some findings contradict an active assumption and are stale (not citable); "
                           "re-run with the assumed parameters")
        try:
            changes += self.state.observe(name, args, res, turn)
        except Exception:                                             # memory bookkeeping never breaks a turn
            pass
        return res

    def _brief(self, fid: str) -> dict:
        f = self.evidence.get(fid)
        return {"id": f.id, "label": f.label, "formatted": fmt_value(f), "class": f.epistemic_class, "metric_id": f.metric_id,
                "period": f.window.get("label", ""), "sources": [s.label() for s in f.sources],
                "coverage": f.coverage, "inputs": f.inputs, "status": f.status, "status_reason": f.status_reason,
                "assumptions": f.assumptions}

    def _recall(self, args: dict) -> dict:
        q = str(args.get("query") or "")
        k = max(1, min(int(args.get("k") or 4), 10))
        msgs = self.store.messages(self.conv_id)
        docs = []
        for a in self.state.answers:
            uq = next((m["content"] for m in msgs if m["turn"] == a["turn"] and m["role"] == "user"
                       and isinstance(m["content"], str)), a.get("question", ""))
            docs.append((str(a["turn"]), f"{uq} {a.get('headline', '')} {' '.join(a.get('cited', []))}"))
        hits = retrieve(q, docs, k)
        turns = []
        for did, score in hits:
            a = next(x for x in self.state.answers if str(x["turn"]) == did)
            turns.append({"turn": a["turn"], "question": a["question"], "headline_template": a["headline"],
                          "cited": a["cited"], "score": round(score, 2)})
        fdocs = [(f.id, f"{f.id} {f.label} {f.metric_id} {f.subject.get('airport_code', '')}") for f in self.evidence.all()]
        fh = retrieve(q, fdocs, 12)
        return {"turns": turns, "findings": [self.evidence.get(fid).brief() for fid, _ in fh],
                "note": "values come from the evidence store; cite them by id"}

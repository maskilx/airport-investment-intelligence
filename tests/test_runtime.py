"""Agent runtime, charts, offline planner and the Gemini adapter — all with mocked/scripted models (no API calls)."""
import io
import json
import threading
import urllib.error

import pytest

from airport_analytics.evidence import EvidenceStore, Finding, SourceRef
from airport_analytics.render import validate
from airport_agent import models
from airport_agent.charts import build_chart, build_charts
from airport_agent.memory import ConversationStore
from airport_agent.models import GeminiBackend, ModelError, ScriptedBackend, gemini_schema
from airport_data.config import get_paths

needs_db = pytest.mark.skipif(not get_paths().db_file.exists(), reason="built DB required")


def tu(i, name, inp):
    return {"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}


SF_SPEC = {"op": "aggregate", "metrics": ["seat_factor"], "entities": {"airports": ["SFO"]}}
ANSWER = {"answer": {"headline": "SFO seat factor", "body": "Seat factor was {F1} ({F1.period}).",
                     "claims": [{"kind": "fact", "text": "{F1}", "support": ["F1"]}]}}


# ------------------------------------------------------------------ charts (synthetic findings, no DB)
def _f(fid, metric, code=None, month=None, value=1.0, unit="ratio", fmt="pct", cls="calculated"):
    subj = {k: v for k, v in (("airport_code", code), ("month", month)) if v}
    return Finding(fid, metric, f"{metric} — {code or ''}", value, unit, fmt, cls, "d", "1", subj, {"label": "w"},
                   [SourceRef("s", ["p"], ["v"])])


def test_chart_values_come_only_from_findings():
    ev = EvidenceStore()
    for i, (c, v) in enumerate([("LAX", 0.2), ("SNA", 0.21), ("SFO", None)], 1):
        ev.add(_f(f"F{i}", "Delay rate", c, value=v))
    ch = build_chart({"type": "auto", "title": "Delay", "findings": ["F1", "F2", "F3", "F99"]}, ev)
    assert ch["type"] == "bar" and ch["findings"] == ["F1", "F2", "F3"]
    vals = ch["vega_lite"]["data"]["values"]
    assert [(r["fid"], r["value"]) for r in vals] == [("F1", 0.2), ("F2", 0.21)]
    assert "F3" in ch["notes"][0]                       # not-established values are reported, not plotted as zero


def test_chart_types_line_and_mixed_units():
    ev = EvidenceStore()
    for i in range(1, 5):
        ev.add(_f(f"F{i}", "Passengers", "SFO", month=f"2026-0{i}", value=i * 10.0, unit="passengers", fmt="number"))
    assert build_chart({"findings": ["F1", "F2", "F3", "F4"]}, ev)["type"] == "line"
    ev.add(_f("F5", "Delay", "SFO", value=0.2))
    assert build_chart({"type": "bar", "findings": ["F1", "F5"]}, ev)["type"] == "table"


def test_auto_chart_when_answer_requests_none():
    ev = EvidenceStore()
    for i, c in enumerate(["BOS", "PWM", "BDL"], 1):
        ev.add(_f(f"F{i}", "Score", c, value=float(i), unit="points", fmt="number"))
    charts = build_charts({"charts": [], "evidence": ["F1", "F2", "F3"]}, ev)
    assert len(charts) == 1 and charts[0]["type"] == "bar"


def test_chart_titles_and_ids_are_validated():
    ev = EvidenceStore()
    ev.add(_f("F1", "Delay", "LAX"))
    bad = {"headline": "x", "body": "{F1}", "charts": [{"title": "Delay is 20%", "findings": ["F1"]},
                                                       {"title": "ok", "findings": ["F7"]}, {"title": "none"}]}
    errs = validate(bad, ev)
    assert any("charts[0].title" in e for e in errs) and any("F7" in e for e in errs) and any("charts[2]" in e for e in errs)


# ------------------------------------------------------------------ Gemini adapter (mocked HTTP, never the network)
def test_gemini_schema_translation():
    s = {"type": "object", "additionalProperties": False, "properties": {
        "m": {"oneOf": [{"type": "string"}, {"type": "object"}], "description": "metric"},
        "op": {"enum": ["a", 1]}, "o": {"type": "object", "default": {}}}}
    g = gemini_schema(s)
    assert "additionalProperties" not in g and g["properties"]["m"]["type"] == "string"
    assert g["properties"]["op"]["enum"] == ["a", "1"] and g["properties"]["o"]["properties"] == {}


def test_gemini_contents_mapping_echoes_thought_signature():
    msgs = [{"role": "user", "content": "q"},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "x1", "name": "run_analysis", "input": {"a": 1},
                                               "provider_meta": {"thoughtSignature": "SIG"}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x1", "content": "[1, 2]"}]}]
    c = GeminiBackend.to_contents(msgs)
    assert c[1]["role"] == "model" and c[1]["parts"][0]["thoughtSignature"] == "SIG"
    fr = c[2]["parts"][0]["functionResponse"]
    assert fr["name"] == "run_analysis" and fr["response"] == {"result": [1, 2]}


def test_gemini_refuses_without_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("AIRPORT_ALLOW_GEMINI", raising=False)
    with pytest.raises(ModelError, match="disabled"):
        GeminiBackend(api_key="k")


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _gemini(monkeypatch, tmp_path, handler, **kw):
    monkeypatch.setenv("AIRPORT_ALLOW_GEMINI", "1")
    seen = []

    def fake_urlopen(req, timeout=None, context=None):
        seen.append(json.loads(req.data))
        return handler(req)
    monkeypatch.setattr(models.urllib.request, "urlopen", fake_urlopen)
    return GeminiBackend(model="gemini-test", api_key="k", usage_log=tmp_path / "u.jsonl", **kw), seen


def test_gemini_parses_function_calls_usage_and_logs(monkeypatch, tmp_path):
    body = {"modelVersion": "gemini-test-001", "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 30,
                                                                 "thoughtsTokenCount": 7},
            "candidates": [{"finishReason": "STOP", "content": {"parts": [
                {"text": "thinking...", "thought": True},
                {"functionCall": {"name": "run_analysis", "args": {"spec": SF_SPEC}}, "thoughtSignature": "S1"}]}}]}
    g, seen = _gemini(monkeypatch, tmp_path, lambda req: _Resp(json.dumps(body).encode()))
    r = g.complete("sys", [{"role": "user", "content": "q"}], [{"name": "run_analysis", "description": "d",
                                                                 "input_schema": {"type": "object"}}])
    assert r.stop_reason == "tool_use" and r.content[0]["name"] == "run_analysis"
    assert r.content[0]["provider_meta"]["thoughtSignature"] == "S1" and len(r.content) == 1   # thought part dropped
    assert (r.usage.input_tokens, r.usage.output_tokens, r.usage.thinking_tokens) == (120, 30, 7)
    assert seen[0]["systemInstruction"]["parts"][0]["text"] == "sys"
    log = [json.loads(x) for x in (tmp_path / "u.jsonl").read_text().splitlines()]
    assert log[0]["model"] == "gemini-test-001" and log[0]["tool_calls"] == ["run_analysis"]


def test_gemini_quota_error_stops_without_fallback(monkeypatch, tmp_path):
    def h(req):
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, io.BytesIO(b'{"error":"RESOURCE_EXHAUSTED"}'))
    g, _ = _gemini(monkeypatch, tmp_path, h)
    with pytest.raises(ModelError, match="no fallback"):
        g.complete("s", [{"role": "user", "content": "q"}], [])


def test_gemini_request_budget(monkeypatch, tmp_path):
    body = {"candidates": [{"content": {"parts": [{"text": "hi"}]}}]}
    g, seen = _gemini(monkeypatch, tmp_path, lambda req: _Resp(json.dumps(body).encode()), max_requests=2)
    g.complete("s", [{"role": "user", "content": "q"}], [])
    g.complete("s", [{"role": "user", "content": "q"}], [])
    with pytest.raises(ModelError, match="budget"):
        g.complete("s", [{"role": "user", "content": "q"}], [])
    assert len(seen) == 2


def test_backend_from_env_never_picks_a_paid_provider(monkeypatch):
    monkeypatch.delenv("AIRPORT_MODEL", raising=False)
    assert models.backend_from_env().name == "offline"
    monkeypatch.setenv("AIRPORT_MODEL", "anthropic")
    monkeypatch.delenv("AIRPORT_ALLOW_PAID", raising=False)
    with pytest.raises(ModelError):
        models.backend_from_env()


# ------------------------------------------------------------------ runtime (scripted model over the real engine)
def _agent(turns, store=None, conv_id=None, **kw):
    from airport_agent.runtime import Agent
    return Agent(ScriptedBackend(turns), store=store, conv_id=conv_id, **kw)


@needs_db
def test_events_and_structured_answer():
    a = _agent([[tu(1, "run_analysis", {"spec": SF_SPEC})], [tu(2, "compose_answer", ANSWER)]])
    ev = []
    r = a.ask("SFO seat factor?", on_event=ev.append)
    kinds = [e["type"] for e in ev]
    assert kinds[0] == "turn_started" and kinds[-1] == "answer"
    assert "tool_started" in kinds and "tool_finished" in kinds and "model_response" in kinds
    assert r.structured["headline"] == "SFO seat factor" and r.structured["evidence"] == ["F1"]
    assert r.trace["usage"]["requests"] == 2 and r.trace["context"]["turns_total"] == 0


@needs_db
def test_follow_up_gets_memory_block_not_full_history(tmp_path):
    st = ConversationStore(tmp_path / "c.sqlite")
    a = _agent([[tu(1, "run_analysis", {"spec": SF_SPEC})], [tu(2, "compose_answer", ANSWER)],
                [{"type": "text", "text": "Do you mean the SFO seat factor again or another airport?"}]], store=st, conv_id="c")
    a.ask("SFO seat factor?")
    a.ask("and that airport?")
    last = a.backend.calls[-1]["messages"]
    final_user = last[-1]["content"]
    text = " ".join(b.get("text", "") for b in final_user if b.get("type") == "text")
    assert "## Conversation state" in text and "SFO (airport" in text and "F1: Seat factor — SFO" in text
    assert "## Current question\nand that airport?" in text
    blob = json.dumps(last)
    assert '"value": 0.8' not in blob and "earlier tool result" in blob     # old payload collapsed to a pointer
    roles = [m["role"] for m in last]
    assert all(x != y for x, y in zip(roles, roles[1:]))                    # strict alternation for providers


@needs_db
def test_persistence_keeps_finding_ids_stable_across_restarts(tmp_path):
    st = ConversationStore(tmp_path / "c.sqlite")
    _agent([[tu(1, "run_analysis", {"spec": SF_SPEC})], [tu(2, "compose_answer", ANSWER)]], store=st, conv_id="c").ask("q1")
    st2 = ConversationStore(tmp_path / "c.sqlite")
    b = _agent([[tu(3, "get_finding", {"id": "F1"})],
                [tu(4, "run_analysis", {"spec": {**SF_SPEC, "metrics": ["passengers"]}})],
                [tu(5, "compose_answer", {"answer": {"headline": "Both", "body": "{F1} and {F2}"}})]], store=st2, conv_id="c")
    r = b.ask("q2")
    assert r.kind == "answer" and r.cited_findings == ["F1", "F2"]
    assert b.evidence.get("F1").metric_id == "seat_factor" and b.evidence.get("F2").metric_id == "passengers"
    assert [t["turn"] for t in st2.traces("c")] == [1, 2]


@needs_db
def test_update_memory_correction_flow():
    a = _agent([[tu(1, "update_memory", {"action": "set_assumption", "text": "LA means LAX"})],
                [{"type": "text", "text": "Noted. Which metric?"}],
                [tu(2, "update_memory", {"action": "set_assumption", "text": "LA means the whole basin", "replaces": "A1"})],
                [{"type": "text", "text": "Updated."}], [{"type": "text", "text": "ok"}]])
    a.ask("LA = LAX")
    a.ask("no, I mean the whole LA basin")
    a.ask("continue")
    mem = a.backend.calls[-1]["messages"][-1]["content"]
    text = " ".join(b.get("text", "") for b in mem if b.get("type") == "text")
    assert "Active assumptions: A2: LA means the whole basin" in text and "A1 (superseded)" in text


@needs_db
def test_budgets_and_cancellation():
    loop = [[tu(i, "describe_catalog", {})] for i in range(20)]
    r = _agent(loop, max_steps=3).ask("q")
    assert r.kind == "fallback" and len(r.tool_calls) == 3
    c = threading.Event()
    c.set()
    assert _agent(loop).ask("q", cancel=c).kind == "stopped"


@needs_db
def test_provider_error_is_reported_not_retried_elsewhere():
    class Boom:
        name = "boom"

        def complete(self, *a):
            raise ModelError("quota reached (429); no fallback")
    from airport_agent.runtime import Agent
    r = Agent(Boom()).ask("q")
    assert r.kind == "error" and "429" in r.markdown


@needs_db
def test_recall_tool_finds_older_turns():
    a = _agent([[tu(1, "run_analysis", {"spec": SF_SPEC})], [tu(2, "compose_answer", ANSWER)],
                [tu(3, "recall", {"query": "SFO seat factor"})], [{"type": "text", "text": "Found it."}]])
    a.ask("SFO seat factor?")
    a.ask("what did we find before about SFO?")
    res = json.loads(a.backend.calls[-1]["messages"][-1]["content"][0]["content"])
    assert res["turns"][0]["turn"] == 1 and res["findings"][0]["id"] == "F1"


# ------------------------------------------------------------------ offline planner end-to-end
@needs_db
def test_offline_planner_answers_the_assignment_questions():
    from airport_agent.offline import OfflineBackend
    from airport_agent.runtime import Agent
    a = Agent(OfflineBackend())
    r1 = a.ask("Which airports in New England are strong candidates for terminal expansion?")
    assert r1.kind == "answer" and "BOS" in r1.markdown and r1.charts and r1.charts[0]["type"] == "bar"
    r2 = a.ask("Compare LA and Santa Ana airport congestion levels.")
    assert r2.kind == "answer" and "LAX" in r2.markdown and "SNA" in r2.markdown and len(r2.charts) >= 1
    r3 = a.ask("What percentage of flights out of Anchorage are long-haul?")
    assert r3.kind == "answer" and "ANC" in r3.markdown and "Long-haul share" in r3.markdown
    r4 = a.ask("What is the unmet flight demand at SFO, and why?")
    assert r4.kind == "answer" and "Hypothesis" in r4.markdown and "not directly measurable" in r4.markdown
    assert a.ask("How busy is Portland?").kind == "clarification"
    r6 = a.ask("Actually I meant Portland, Maine")
    assert r6.kind == "answer" and "PWM" in r6.markdown and a.state.assumptions
    r7 = a.ask("Compare that with the airport we discussed first")
    assert r7.kind == "answer" and "PWM" in r7.markdown and "BOS" in r7.markdown   # BOS: first airport (turn-1 screen)


@needs_db
def test_offline_ordinal_follow_up_uses_ranked_list():
    from airport_agent.offline import OfflineBackend
    from airport_agent.runtime import Agent
    a = Agent(OfflineBackend())
    a.ask("Which airports in New England are strong candidates for terminal expansion?")
    r = a.ask("Compare congestion at the top two of those")
    assert r.kind == "answer" and r.structured["headline"].endswith("BOS, PWM")

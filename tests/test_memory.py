"""Memory & context management — no database and no model calls needed."""
import json

from airport_analytics.evidence import EvidenceStore, Finding, SourceRef
from airport_analytics.render import fmt_value
from airport_agent.memory import (Budget, ContextBuilder, ConversationState, ConversationStore, compact_old_tool_results,
                                  est_tokens, extractive_summary, retrieve, summarize, summary_is_safe)

CODES = ["BOS", "SFO", "LAX", "SNA", "ANC", "PDX", "PWM", "JFK", "ORD", "DEN"]


def mk(fid, code, metric="seat_factor", value=0.8):
    return Finding(id=fid, metric_id=metric, label=f"{metric.replace('_', ' ').title()} — {code} — 2025-08…2026-07",
                   value=value, unit="ratio", fmt="pct", epistemic_class="calculated", definition="Σ pax / Σ seats",
                   formula_version="1", subject={"airport_code": code}, window={"label": "2025-08…2026-07"},
                   sources=[SourceRef("bts_t100_segment", ["2025-08"], ["v1"])])


def _store(tmp_path, name="c.sqlite"):
    return ConversationStore(tmp_path / name)


def test_store_roundtrip_and_stable_ids(tmp_path):
    st = _store(tmp_path)
    st.create("c1", "first")
    ev = EvidenceStore()
    for i in range(3):
        ev.add(mk(ev.new_id(), "BOS"))
    st.save_findings("c1", ev)
    st.append("c1", 1, "user", "hello")
    st2 = ConversationStore(tmp_path / "c.sqlite")           # reopen from disk
    ev2 = st2.load_findings("c1")
    assert [f.id for f in ev2.all()] == ["F1", "F2", "F3"]
    assert ev2.get("F2").sources[0].source_id == "bts_t100_segment"
    assert ev2.new_id() == "F4"                              # ids continue, never reused
    assert st2.messages("c1")[0]["content"] == "hello" and st2.last_turn("c1") == 1
    assert st2.list()[0]["title"] == "first"


def test_summary_must_not_contain_numbers():
    assert summary_is_safe("- User compared BOS and SFO (see F3, F7); assumption A2 applies; FY2025 window")
    assert not summary_is_safe("- BOS seat factor was 84.2% in FY2025")
    assert not summary_is_safe("- SFO had 26 million passengers")
    poison = lambda prompt: "- SFO seat factor 82.1% (F3)"           # noqa: E731
    recs = [{"turn": 1, "question": "SFO seat factor in 2025 above 80%?", "headline": "SFO {F3}", "cited": ["F3"]}]
    text, method = summarize(recs, poison)
    assert method == "extractive" and summary_is_safe(text) and "F3" in text and "80" not in text
    good = lambda prompt: "- User asked about SFO's seat factor; answered with F3"   # noqa: E731
    assert summarize(recs, good) == ("- User asked about SFO's seat factor; answered with F3", "model")


def test_extractive_summary_masks_digits():
    t = extractive_summary([{"turn": 2, "question": "Is 26.4M enplanements at SFO high?", "cited": ["F9"]}])
    assert summary_is_safe(t) and "F9" in t


def test_assumptions_supersede_and_decisions_are_number_free():
    s = ConversationState()
    a1, _ = s.apply_update({"action": "set_assumption", "text": "LA means LAX only"}, 1)
    a2, _ = s.apply_update({"action": "set_assumption", "text": "LA means the whole LA basin", "replaces": a1["id"]}, 3)
    assert s.assumptions[0]["status"] == "superseded" and s.assumptions[0]["superseded_by"] == a2["id"]
    _, err = s.apply_update({"action": "note_decision", "text": "Shortlist BOS because its score is 69", "support": ["F3"]}, 4)
    assert err and "numbers" in err
    d, err = s.apply_update({"action": "note_decision", "text": "Shortlist BOS and PWM", "support": ["F3", "x"]}, 4)
    assert not err and d["support"] == ["F3"]
    _, err = s.apply_update({"action": "retract_assumption", "id": "A9"}, 5)
    assert err
    _, err = s.apply_update({"action": "drop_table"}, 5)
    assert err


def test_state_observes_tool_calls():
    s = ConversationState()
    res = {"resolutions": [{"term": "Anchorage", "kind": "airport", "airport_ids": [10299], "candidates": [
        {"kind": "group", "group": {"cbsa": "Anchorage, AK"}, "airport_ids": [10299, 13467]},
        {"kind": "airport", "airport_id": 10299, "code": "ANC", "name": "Ted Stevens"}]}]}
    s.observe("resolve_entities", {"terms": ["Anchorage"]}, res, 1)
    assert "ANC" in s.entities                                   # not the CBSA group candidate
    s.observe("run_analysis", {"spec": {"op": "aggregate", "metrics": ["seat_factor"], "window": {"t12": True}}},
              {"entities": {"airports": [{"code": "SFO", "airport_id": 1, "name": "SFO Intl"}]}}, 2)
    assert s.focus(1)[0][0] == "SFO" and s.metrics["seat_factor"] == 2 and s.windows[-1]["turn"] == 2


def test_bm25_exact_codes_and_ids():
    docs = [("1", "seat factor at BOS answered F1"), ("2", "congestion LAX SNA F5 F6"), ("3", "long haul ANC F9")]
    assert retrieve("what did we find for SNA", docs, 1)[0][0] == "2"
    assert retrieve("F9", docs, 1)[0][0] == "3"
    assert retrieve("the", docs) == []


def test_old_tool_results_collapse_to_pointers():
    payload = json.dumps({"findings": [{"id": f"F{i}", "value": i * 1000} for i in range(10, 20)]})
    msgs = [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t", "content": payload}]}]
    out = compact_old_tool_results(msgs)[0]["content"][0]["content"]
    assert "F10" in out and "F19" in out and "1000" not in out


def _long_conversation(tmp_path, turns=120):
    st = _store(tmp_path)
    st.create("c")
    ev = EvidenceStore()
    state = ConversationState()
    for t in range(1, turns + 1):
        code = CODES[(t - 1) % len(CODES)]
        f = ev.add(mk(ev.new_id(), code, value=0.7 + t / 1000))
        st.append("c", t, "user", f"What is the seat factor at {code}? (turn {t})")
        st.append("c", t, "assistant", [{"type": "tool_use", "id": f"u{t}", "name": "run_analysis", "input": {}}])
        st.append("c", t, "user", [{"type": "tool_result", "tool_use_id": f"u{t}",
                                    "content": json.dumps({"findings": [f.brief()], "pad": "x" * 2000})}])
        st.append("c", t, "assistant", [{"type": "text", "text": "done"}])
        state.observe("run_analysis", {"spec": {"metrics": ["seat_factor"]}},
                      {"entities": {"airports": [{"code": code, "airport_id": t}]}}, t)
        state.answers.append({"turn": t, "question": f"seat factor at {code}", "headline": f"{code} seat factor {{{f.id}}}",
                              "cited": [f.id]})
    st.save_findings("c", ev)
    return st, ev, state


def test_long_conversation_stays_within_budget_and_keeps_findings(tmp_path):
    st, ev, state = _long_conversation(tmp_path)
    b = Budget(total=8000)
    cb = ContextBuilder(st, b)
    comp = cb.maybe_compact("c", state)
    assert comp and comp["method"] == "extractive"
    assert summary_is_safe(st.latest_summary("c")["text"])
    mem, recent, stats = cb.build("c", "Go back to turn one: what was the BOS seat factor F1?", state, ev, fmt_value)
    assert stats["turns_verbatim"] < 120 and stats["turns_summarised"] > 0
    assert stats["recent_tokens"] <= b.total * b.recent_share
    assert est_tokens(mem) <= b.total * 0.6
    assert "F1:" in mem                           # the authoritative finding is reachable, with its value from the store
    assert fmt_value(ev.get("F1")) in mem
    assert "Turn 1:" in mem                       # retrieved older turn
    assert "contains no numbers" in mem           # the summary is labelled as non-authoritative
    blob = json.dumps(recent)
    assert "x" * 2000 not in blob                 # raw tool payloads of earlier turns are not resent


def test_superseded_assumptions_are_flagged_in_context(tmp_path):
    st, ev, state = _long_conversation(tmp_path, 3)
    state.apply_update({"action": "set_assumption", "text": "use calendar year"}, 1)
    state.apply_update({"action": "set_assumption", "text": "use fiscal year", "replaces": "A1"}, 2)
    mem, _, _ = ContextBuilder(st).build("c", "next", state, ev, fmt_value)
    assert "Active assumptions: A2: use fiscal year" in mem
    assert "No longer valid (do not use): A1 (superseded): use calendar year" in mem

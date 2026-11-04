"""Trust layer (docs/10): execution envelopes and faithful replay, assumption staleness, typed claim validation.

Each test encodes a failure mode found by an independent review, not just the happy path.
"""
from __future__ import annotations

import copy

import pytest

from airport_data.config import get_paths

pytestmark = pytest.mark.skipif(not get_paths().db_file.exists(), reason="built DB required (python -m airport_data build)")


@pytest.fixture(scope="module")
def S():
    from airport_analytics.tools import Session
    return Session()


def run(S, spec):
    return S.call("run_analysis", {"spec": spec})


# ---------------------------------------------------------------- stage 1: execution envelopes and replay
def test_every_finding_carries_an_execution_envelope(S):
    r = run(S, {"op": "rank", "metrics": ["seat_factor"], "entities": {"airports": ["SFO", "LAX", "BOS", "SEA"]}})
    for b in r["findings"]:
        ex = S.ctx.store.get(b["id"]).execution
        assert ex["tool"] == "run_analysis" and ex["op"] == "rank"
        assert ex["spec"]["op"] == "rank" and ex["resolved_airport_ids"]
        assert ex["build"]["raw_fingerprint"] and ex["catalog_version"]


def test_screen_score_replays_as_screen_not_aggregate(S):
    """Review 2 §6.3: a screen score replayed through a generic aggregate is not a replay."""
    r = run(S, {"op": "screen", "entities": {"group": {"census_division": "New England"}}})
    fid = r["table"][0]["score"]["id"]
    n_before = len(S.ctx.store)
    rep = S.call("get_finding", {"id": fid, "reproduce": True})["replay"]
    assert rep["op"] == "screen" and rep["match"] is True
    assert rep["build_same"] and rep["entity_set_same"] and rep["config_same"]
    assert len(S.ctx.store) == n_before                      # replay never pollutes the session store


def test_replay_detects_a_changed_value(S):
    r = run(S, {"op": "aggregate", "metrics": ["seat_factor"], "entities": {"airports": ["SFO"]}})
    f = S.ctx.store.get(r["findings"][0]["id"])
    orig = f.value
    try:
        f.value = orig + 0.01                                 # simulate a tampered / drifted stored value
        rep = S.call("get_finding", {"id": f.id, "reproduce": True})["replay"]
        assert rep["match"] is False and rep["replayed_value"] == pytest.approx(orig)
    finally:
        f.value = orig


def test_derive_and_sql_findings_replay(S):
    a = run(S, {"op": "aggregate", "metrics": ["passengers"], "entities": {"airports": ["LAX"]}})["findings"][0]["id"]
    b = run(S, {"op": "aggregate", "metrics": ["passengers"], "entities": {"airports": ["SNA"]}})["findings"][0]["id"]
    d = S.call("derive", {"op": "ratio", "findings": [a, b]})["id"]
    assert S.call("get_finding", {"id": d, "reproduce": True})["replay"]["match"] is True
    q = S.call("query_sql", {"sql": "SELECT count(*) AS n FROM dim_airport WHERE state_abr = 'VT'"})
    sid = q["rows"][0]["n"]["id"]
    assert S.call("get_finding", {"id": sid, "reproduce": True})["replay"]["match"] is True


def test_legacy_finding_is_reported_not_replayable(S):
    r = run(S, {"op": "aggregate", "metrics": ["seat_factor"], "entities": {"airports": ["BOS"]}})
    f = S.ctx.store.get(r["findings"][0]["id"])
    saved, f.execution = f.execution, None
    try:
        rep = S.call("get_finding", {"id": f.id, "reproduce": True})["replay"]
        assert rep["replayable"] is False
    finally:
        f.execution = saved


# ---------------------------------------------------------------- stage 2: assumption dependencies and stale findings
def _tu(i, name, inp):
    return {"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}


LH = lambda miles=None: {"op": "aggregate", "entities": {"airports": ["ANC"]}, "metrics": [
    {"id": "long_haul_share", "params": {"weight": "departures", **({"min_miles": miles} if miles else {})}}]}


def test_bound_assumption_makes_default_threshold_findings_stale_and_uncitable():
    """Review 2 §6.1: threshold changed from the default to another value; old findings must not support the answer."""
    from airport_agent.memory import ConversationStore
    from airport_agent.models import ScriptedBackend
    from airport_agent.runtime import Agent
    st = ConversationStore(":memory:")
    a = Agent(ScriptedBackend([[_tu(1, "run_analysis", {"spec": LH()})], [{"type": "text", "text": "Done."}]]),
              store=st, conv_id="c")
    a.ask("long haul share at ANC")
    old = a.evidence.all()[0]
    assert old.status == "current" and "min_miles=3000" in old.metric_id
    b = Agent(ScriptedBackend([
        [_tu(2, "update_memory", {"action": "set_assumption", "text": "Long-haul threshold chosen by the analyst",
                                  "binds": {"metric": "long_haul_share", "param": "min_miles", "value": 2400}})],
        [_tu(3, "compose_answer", {"answer": {"headline": "ANC long haul", "body": f"{{{old.id}}}",
                                              "claims": [{"kind": "fact", "text": f"{{{old.id}}}", "support": [old.id]}]}})],
        [_tu(4, "run_analysis", {"spec": LH(2400)})],
        [{"type": "text", "text": "Re-ran with the analyst threshold."}]]), store=st, conv_id="c")
    r = b.ask("use 2400 miles instead")
    assert b.evidence.get(old.id).status == "stale" and "A1" in b.evidence.get(old.id).status_reason
    comp = next(c for c in r.tool_calls if c["tool"] == "compose_answer")
    assert comp["error"] == "grounding_validation_failed"          # the stale finding could not be cited
    new = [f for f in b.evidence.all() if "min_miles=2400" in f.metric_id]
    assert new and new[0].status == "current" and new[0].assumptions == ["A1"]
    # status survives a restart (persisted with INSERT OR REPLACE) and the memory block lists it as stale
    c = Agent(ScriptedBackend([]), store=st, conv_id="c")
    assert c.evidence.get(old.id).status == "stale"
    mem, _, _ = c.ctx.build("c", "again", c.state, c.evidence, lambda f: str(f.value))
    assert f"{old.id}:" not in mem.split("Stale findings")[0].split("Findings")[-1] and "Stale findings" in mem


def test_finding_contradicting_an_active_binding_is_born_stale():
    from airport_agent.models import ScriptedBackend
    from airport_agent.runtime import Agent
    a = Agent(ScriptedBackend([
        [_tu(1, "update_memory", {"action": "set_assumption", "text": "Analyst long-haul threshold",
                                  "binds": {"metric": "long_haul_share", "param": "min_miles", "value": 2400}})],
        [_tu(2, "run_analysis", {"spec": LH()})], [{"type": "text", "text": "ok"}]]))
    r = a.ask("long haul at ANC with the analyst threshold")
    f = a.evidence.all()[0]
    assert f.status == "stale" and "A1" in f.status_reason
    res = next(c for c in r.tool_calls if c["tool"] == "run_analysis")
    assert res["error"] is None


def test_unbound_assumption_supersede_invalidates_findings_made_under_it():
    from airport_agent.models import ScriptedBackend
    from airport_agent.runtime import Agent
    a = Agent(ScriptedBackend([
        [_tu(1, "update_memory", {"action": "set_assumption", "text": "LA means LAX only"})],
        [_tu(2, "run_analysis", {"spec": {"op": "aggregate", "metrics": ["seat_factor"], "entities": {"airports": ["LAX"]}}})],
        [_tu(3, "derive", {"op": "ratio", "findings": ["F1", "F1"]})],
        [_tu(4, "update_memory", {"action": "set_assumption", "text": "LA means all LA basin airports", "replaces": "A1"})],
        [{"type": "text", "text": "ok"}]]))
    a.ask("seat factor LA")
    assert a.evidence.get("F1").status == "stale" and "superseded" in a.evidence.get("F1").status_reason
    assert a.evidence.get("F2").status == "stale"                          # derived from a stale input


def test_assumption_text_with_numbers_or_bad_binds_is_rejected():
    from airport_agent.memory import ConversationState
    s = ConversationState()
    assert s.apply_update({"action": "set_assumption", "text": "eighty percent of seats"}, 1)[1]
    assert s.apply_update({"action": "set_assumption", "text": "threshold 2400 miles"}, 1)[1]
    assert s.apply_update({"action": "set_assumption", "text": "threshold",
                           "binds": {"metric": "long_haul_share", "param": "nope", "value": 1}}, 1)[1]
    assert s.apply_update({"action": "set_assumption", "text": "threshold",
                           "binds": {"metric": "long_haul_share", "param": "min_miles", "value": 99999}}, 1)[1]
    assert s.apply_update({"action": "set_preference", "key": "units", "text": "show twelve decimals"}, 1)[1]


def test_extractive_summary_masks_number_words():
    from airport_agent.memory import extractive_summary, summary_is_safe
    t = extractive_summary([{"turn": 1, "question": "Is eighty percent a high seat factor? ½ of it?", "cited": ["F1"]}])
    assert summary_is_safe(t) and "eighty" not in t


def test_offline_threshold_follow_up_binds_and_reruns():
    from airport_agent.offline import OfflineBackend
    from airport_agent.runtime import Agent
    a = Agent(OfflineBackend())
    r1 = a.ask("What is the percentage of long haul flights out of Anchorage airport?")
    assert r1.kind == "answer"
    r2 = a.ask("Use a 2000 miles long haul threshold instead")
    assert r2.kind == "answer", r2.markdown
    assert a.state.active_assumptions()[0]["binds"]["value"] == 2000
    cited = [a.evidence.get(f) for f in r2.cited_findings]
    assert all(f.status == "current" for f in cited)
    lh = [f for f in cited if f.metric_id.startswith("long_haul_share")]
    assert lh and all("min_miles=2000" in f.metric_id for f in lh)
    assert all(f.status == "stale" for f in a.evidence.all()
               if f.metric_id.startswith("long_haul_share") and "min_miles=2000" not in f.metric_id)

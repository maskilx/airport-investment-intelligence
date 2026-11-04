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


# ---------------------------------------------------------------- stage 3: typed claims (semantic validity)
@pytest.fixture(scope="module")
def ev(S):
    """A small fixed evidence set: seat factor SFO/LAX, delay LAX/SNA, TAF SFO FY2035, a NE screen."""
    out = {}
    agg = lambda m, codes, **kw: run(S, {"op": "aggregate", "metrics": [m], "entities": {"airports": codes},
                                         "group_by": ["airport"], **kw})["findings"]
    sf = agg("seat_factor", ["SFO", "LAX"])
    out["sf_sfo"], out["sf_lax"] = [f["id"] for f in sorted(sf, key=lambda f: f["label"].find("LAX"))]
    out["sf_sfo"] = next(f["id"] for f in sf if "SFO" in f["label"])
    out["sf_lax"] = next(f["id"] for f in sf if "LAX" in f["label"])
    out["taxi"] = {next(c for c in ("LAX", "SNA") if c in f["label"]): f["id"] for f in agg("avg_taxi_out_min", ["LAX", "SNA"])}
    out["delay"] = {next(c for c in ("LAX", "SNA") if c in f["label"]): f["id"] for f in agg("dep_delay15_rate", ["LAX", "SNA"])}
    out["pax_lax_cy"] = agg("passengers", ["LAX"], window={"cy": 2025})[0]["id"]
    out["pax_sna_t12"] = agg("passengers", ["SNA"])[0]["id"]
    out["taf_sfo"] = run(S, {"op": "aggregate", "metrics": [{"id": "taf_enplanements", "window": {"fy": 2035}}],
                             "entities": {"airports": ["SFO"]}})["findings"][0]["id"]
    scr = run(S, {"op": "screen", "entities": {"group": {"census_division": "New England"}}})
    out["screen"] = [r["score"]["id"] for r in scr["table"]]
    return out


def errs(S, answer):
    r = S.call("compose_answer", {"answer": answer})
    return r.get("errors", []) if r.get("error") else []


def test_reviewer_counterexample_guaranteed_profitable_is_rejected_everywhere(S, ev):
    f = ev["sf_sfo"]
    bad = [
        {"headline": "SFO", "body": f"Seat factor {{{f}}}.", "claims": [
            {"kind": "fact", "text": "SFO expansion is guaranteed profitable.", "support": [f]}]},
        {"headline": "SFO expansion will be profitable", "body": f"{{{f}}}"},
        {"headline": "SFO", "body": f"{{{f}}}", "claims": [
            {"kind": "inference", "text": "High load factors mean expansion pays back quickly.", "support": [f]}]},
        {"headline": "SFO", "body": f"{{{f}}}", "claims": [
            {"kind": "financial", "text": "Expansion returns exceed the cost of capital.", "support": [f]}]},
        {"headline": "SFO", "body": f"{{{f}}}", "limitations": ["Expansion at SFO is highly profitable."]},
    ]
    for a in bad:
        assert errs(S, a), a


def test_reviewer_counterexample_gates_in_2035_is_rejected(S, ev):
    f, taf = ev["sf_sfo"], ev["taf_sfo"]
    e = errs(S, {"headline": "SFO", "body": f"{{{f}}}", "claims": [
        {"kind": "inference", "text": "SFO will need additional gates in 2035.", "support": [f]}]})
    assert any("2035" in x for x in e) and any("gates" in x for x in e)
    # citing the FY2035 forecast legitimises the year, but not the capacity-need claim
    e = errs(S, {"headline": "SFO", "body": f"FAA forecast {{{taf}}}.", "claims": [
        {"kind": "inference", "text": "SFO will need additional gates in 2035.", "support": [taf]}]})
    assert e and not any("2035" in x for x in e)
    # as a hypothesis with evidence and a competing explanation it is allowed, and labelled as such
    assert not errs(S, {"headline": "SFO", "body": f"FAA forecast {{{taf}}}.", "claims": [
        {"kind": "hypothesis", "text": "Forecast growth could require more gates by 2035.", "support": [taf],
         "alternatives": ["airlines may up-gauge aircraft and absorb growth at existing gates"]}]})


def test_comparison_direction_compatibility_and_periods_are_checked_by_code(S, ev):
    t = ev["taxi"]
    ok = {"headline": "Taxi-out", "body": "Airside indicator.", "claims": [
        {"kind": "comparison", "relation": "higher", "findings": [t["LAX"], t["SNA"]]}]}
    assert not errs(S, ok)
    md = S.call("compose_answer", {"answer": ok})["markdown"]
    assert "LAX is higher than SNA" in md
    wrong = {**ok, "claims": [{"kind": "comparison", "relation": "lower", "findings": [t["LAX"], t["SNA"]]}]}
    assert any("do not support" in x for x in errs(S, wrong))
    near = {**ok, "claims": [{"kind": "comparison", "relation": "higher", "findings": [ev["delay"]["LAX"], ev["delay"]["SNA"]]}]}
    assert any("similar" in x for x in errs(S, near))                   # 20.6% vs 20.5% is not a direction
    mixed = {**ok, "claims": [{"kind": "comparison", "relation": "higher", "findings": [t["LAX"], ev["sf_lax"]]}]}
    assert any("different things" in x for x in errs(S, mixed))
    per = {**ok, "claims": [{"kind": "comparison", "relation": "higher", "findings": [ev["pax_lax_cy"], ev["pax_sna_t12"]]}]}
    assert any("different periods" in x for x in errs(S, per))
    per["claims"][0]["periods_differ"] = True
    assert not errs(S, per)
    assert "Periods differ" in S.call("compose_answer", {"answer": per})["markdown"]
    slip = {**ok, "claims": [{"kind": "comparison", "relation": "higher", "findings": [t["LAX"], t["SNA"]],
                              "text": "SNA is actually lower"}]}
    assert errs(S, slip)                                                # model text may not restate direction
    assert errs(S, {"headline": "LAX is busier than SNA", "body": "x"})  # comparisons outside a typed claim


def test_rank_claims_need_rank_findings_and_render_robustness(S, ev):
    t = ev["taxi"]
    assert errs(S, {"headline": "Taxi", "body": "x", "claims": [{"kind": "ranking", "findings": [t["LAX"]]}]})
    assert errs(S, {"headline": "Taxi", "body": "x", "claims": [
        {"kind": "fact", "text": "LAX has the highest taxi-out.", "support": [t["LAX"]]}]})
    top = ev["screen"][0]
    ans = {"headline": "New England screen", "body": "Screening result.", "claims": [
        {"kind": "ranking", "findings": [top], "text": "It is the strongest candidate on this growth screen."}]}
    assert not errs(S, ans)
    md = S.call("compose_answer", {"answer": ans})["markdown"]
    assert "is ranked 1 of" in md and "weighting scenario" in md


def test_hypothesis_needs_evidence_and_alternatives_and_caveats_need_negation(S, ev):
    f = ev["sf_sfo"]
    assert errs(S, {"headline": "SFO", "body": f"{{{f}}}", "claims": [
        {"kind": "hypothesis", "text": "Demand is constrained by terminal capacity.", "support": [f]}]})
    assert errs(S, {"headline": "SFO", "body": f"{{{f}}}", "claims": [
        {"kind": "hypothesis", "text": "Demand is constrained by terminal capacity.", "alternatives": ["airline choice"]}]})
    assert not errs(S, {"headline": "SFO", "body": f"{{{f}}}", "limitations": [
        "Profitability and terminal capacity are not modelled; unmet demand is not observed."]})


def test_legitimate_answers_still_pass(S, ev):
    f = ev["pax_lax_cy"]
    assert not errs(S, {"headline": "LAX traffic in 2025", "body": f"LAX carried {{{f}}} in CY2025.",
                        "claims": [{"kind": "fact", "text": f"LAX carried {{{f}}} ({{{f}.period}}).", "support": [f]}],
                        "assumptions": ["Passengers are T-100 segment passengers (all carriers)."]})

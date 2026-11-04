"""Trust layer (docs/10): execution envelopes and faithful replay, assumption staleness, typed claim validation.

Each test encodes a failure mode found by an independent review, not just the happy path.
"""
from __future__ import annotations

import copy
import json

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


# ---------------------------------------------------------------- stage 4: runtime hardening
def test_every_tool_use_is_paired_when_compose_is_not_last():
    """Grok product review #7: a successful compose_answer followed by another tool_use left it unpaired."""
    from airport_agent.models import ScriptedBackend
    from airport_agent.runtime import Agent
    a = Agent(ScriptedBackend([
        [_tu(1, "run_analysis", {"spec": {"op": "aggregate", "metrics": ["seat_factor"], "entities": {"airports": ["SFO"]}}})],
        [_tu(2, "compose_answer", {"answer": {"headline": "SFO", "body": "{F1}"}}), _tu(3, "recall", {"query": "x"})]]))
    r = a.ask("seat factor SFO")
    assert r.kind == "answer"
    uses, results = set(), set()
    for m in a.store.messages(a.conv_id):
        for b in m["content"] if isinstance(m["content"], list) else []:
            if b.get("type") == "tool_use":
                uses.add(b["id"])
            elif b.get("type") == "tool_result":
                results.add(b["tool_use_id"])
    assert uses == results


def test_tool_call_budget_is_enforced_within_a_step():
    from airport_agent.models import ScriptedBackend
    from airport_agent.runtime import Agent, Limits
    many = [_tu(i, "describe_catalog", {}) for i in range(8)]
    a = Agent(ScriptedBackend([many, [{"type": "text", "text": "ok"}]]), limits=Limits(max_tool_calls=3))
    r = a.ask("q")
    assert len(r.tool_calls) == 3                                        # not 8


def test_cancel_interrupts_an_in_flight_query(S):
    import threading
    import time
    cancel = threading.Event()
    threading.Timer(0.3, cancel.set).start()
    t0 = time.time()
    r = S.call("query_sql", {"sql": "SELECT count(*) AS n FROM v_t100_segment a, v_t100_segment b "
                                    "WHERE a.passengers > b.passengers"}, cancel=cancel)
    assert r.get("error") and time.time() - t0 < 3
    assert S.call("query_sql", {"sql": "SELECT count(*) AS n FROM dim_airport"})["rows"]   # connection still usable


def test_hard_context_budget_compacts_old_tool_results():
    from airport_agent.runtime import est_request_tokens, fit_context
    big = json.dumps({"rows": [{"id": f"F{i}", "v": "x" * 200} for i in range(400)]})
    msgs = [{"role": "user", "content": "q"},
            {"role": "assistant", "content": [{"type": "tool_use", "id": "a", "name": "run_analysis", "input": {}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a", "content": big}]},
            {"role": "assistant", "content": [{"type": "text", "text": "next"}]},
            {"role": "user", "content": "final question"}]
    out, tok, n = fit_context("sys", [], msgs, 5_000)
    assert n == 1 and tok <= 5_000 and est_request_tokens("sys", [], msgs) > 5_000
    body = json.loads(out[2]["content"][0]["content"])
    assert body["compacted"] and "F199" in body["findings"] and out[-1]["content"] == "final question"


def test_invalid_model_config_fails_loudly_and_paid_models_need_opt_in(monkeypatch, tmp_path):
    from airport_agent import models
    monkeypatch.setenv("AIRPORT_MODEL", "gemni")
    with pytest.raises(models.ModelError):
        models.backend_from_env()
    monkeypatch.setenv("AIRPORT_ALLOW_GEMINI", "1")
    monkeypatch.delenv("AIRPORT_ALLOW_PAID", raising=False)
    with pytest.raises(models.ModelError):
        models.GeminiBackend(model="gemini-3-pro", api_key="k", usage_log=tmp_path / "u.jsonl")


def test_gemini_daily_budget_survives_restart(monkeypatch, tmp_path):
    import time
    from airport_agent import models
    monkeypatch.setenv("AIRPORT_ALLOW_GEMINI", "1")
    log = tmp_path / "u.jsonl"
    day = time.strftime("%Y-%m-%d", time.gmtime())
    log.write_text("".join(json.dumps({"utc_day": day, "request": True}) + "\n" for _ in range(3)))
    g = models.GeminiBackend(model="gemini-3.8-flash", api_key="k", usage_log=log, max_requests=3)
    with pytest.raises(models.ModelError, match="budget"):
        g.complete("s", [{"role": "user", "content": "q"}], [])


def test_web_fetch_ignores_environment_proxies():
    """Grok #10: through an environment proxy the post-connect peer check would see the proxy, not the origin.
    (Source-level check: exercising it for real needs a proxy and a rebinding DNS name.)"""
    from airport_agent import web
    assert "urllib.request.ProxyHandler({})" in open(web.__file__).read()


# ---------------------------------------------------------------- stage 5: constraint records and stage-A framing
def test_constraints_respect_effective_dates_and_evidence_levels(S):
    """Review 2 §6.4: an expired cap was combined with the current one; snippet evidence counted as verified."""
    r = run(S, {"op": "screen", "entities": {"airports": ["SNA", "SFO", "LAX", "SEA"]},
                "options": {"as_of": "2026-11-04"}})
    sna = next(t for t in r["table"] if t["airport"] == "SNA")
    flags = sna["flags"]
    assert not any("Phase 2" in str(f.get("detail")) for f in flags)                 # ended 2025-12-31
    assert any("Phase 3" in str(f.get("detail")) for f in flags)
    assert all(f["flag"] == "REPORTED_CONSTRAINT_UNVERIFIED" for f in flags
               if f["flag"] in ("REGULATORY_CAP", "CURFEW", "REPORTED_CONSTRAINT_UNVERIFIED"))   # snippet-only evidence
    assert any(e["airport"] == "SNA" and "Phase 2" in e["item"] for e in r["constraints_not_in_effect"])
    # on a date inside Phase 2, Phase 2 is the one in effect
    r2 = run(S, {"op": "screen", "entities": {"airports": ["SNA", "SFO"]}, "options": {"as_of": "2024-06-01"}})
    sna2 = next(t for t in r2["table"] if t["airport"] == "SNA")
    assert any("Phase 2" in str(f.get("detail")) for f in sna2["flags"])
    assert not any("Phase 3" in str(f.get("detail")) for f in sna2["flags"])
    # LAX capacity rates are unverified -> not used; SFO's are primary -> used
    lax = next(t for t in r["table"] if t["airport"] == "LAX")
    sfo = next(t for t in r["table"] if t["airport"] == "SFO")
    assert any(f["flag"] == "AIRFIELD_UNKNOWN" for f in lax["flags"])
    assert any(f["flag"].startswith("AIRFIELD_") and f["flag"] != "AIRFIELD_UNKNOWN" for f in sfo["flags"])
    assert any(x["airport"] == "LAX" for x in r["capacity_rates_not_used"])


def test_strict_numeric_parsing_of_capacity_values():
    from airport_analytics.screening import strict_range
    assert strict_range("76-78") == (76.0, 78.0) and strict_range("83") == (83.0, 83.0)
    assert strict_range("12.2 (12.5 if 2021-2025 traffic reached 11.21 MAP)") is None
    assert strict_range("about 80") is None


def test_screen_is_framed_as_stage_a_and_replays_on_its_as_of_date(S):
    r = run(S, {"op": "screen", "entities": {"group": {"census_division": "New England"}}})
    f = S.ctx.store.get(r["table"][0]["score"]["id"])
    assert f.label.startswith("Passenger growth opportunity score") and "terminal" in r["disclaimer"].lower()
    assert f.execution["spec"]["options"]["as_of"] == r["constraints_as_of"]
    assert S.call("get_finding", {"id": f.id, "reproduce": True})["replay"]["match"] is True


# ---------------------------------------------------------------- explanation quality (first release)
def test_screen_answer_explains_score_composition_and_method():
    from airport_agent.offline import OfflineBackend
    from airport_agent.runtime import Agent
    a = Agent(OfflineBackend())
    r = a.ask("Which airports in New England are strong candidates for terminal expansion?")
    assert r.kind == "answer"
    s = r.structured
    method = " ".join(s["scoring_method"])
    for must in ("weight", "Eligibility", "Missing data", "no reweighting", "Ties", "Robustness", "does not establish"):
        assert must in method, must
    # each score equals the sum of its per-factor contribution findings (all inspectable)
    for f in [a.evidence.get(i) for i in r.cited_findings if a.evidence.get(i).metric_id.startswith("screen_score")]:
        parts = [a.evidence.get(i) for i in f.inputs if a.evidence.get(i).metric_id.startswith("screen_contribution")]
        assert len(parts) == 3 and abs(sum(p.value for p in parts) - f.value) < 1e-9
        assert f.subject["main_contributor"]
    assert "largest contribution" in r.markdown and "How the score is calculated" in r.markdown
    labels = {c["label"] for c in s["claims"]}
    assert "Ranking (computed)" in labels


def test_claim_labels_distinguish_measured_calculated_forecast_and_interpretation():
    from airport_analytics.evidence import EvidenceStore, Finding, SourceRef
    from airport_analytics.render import claim_label
    st = EvidenceStore()
    for fid, cls in (("F1", "observed"), ("F2", "calculated"), ("F3", "forecast")):
        st.add(Finding(fid, "m", "m — X", 1.0, "u", "number", cls, "d", "1", {}, {"label": "w"}, [SourceRef("s", [], [])]))
    assert claim_label({"kind": "fact", "support": ["F1"]}, st) == "Measured"
    assert claim_label({"kind": "fact", "support": ["F2"]}, st) == "Calculated"
    assert claim_label({"kind": "fact", "support": ["F3"]}, st).startswith("Forecast")
    assert claim_label({"kind": "inference", "support": ["F1"]}, st) == "Interpretation"


def test_not_established_values_become_a_limitation_not_a_fact():
    from airport_agent.offline import OfflineBackend
    from airport_agent.runtime import Agent
    r = Agent(OfflineBackend()).ask("How congested is HVN airport?")
    assert r.kind == "answer"
    assert "n/a" not in " ".join(c["text"] for c in r.structured["claims"])
    assert any("Not established" in x for x in r.structured["limitations"])


def test_chart_labels_repeated_airport_by_period():
    from airport_agent.charts import build_chart
    from airport_analytics.evidence import EvidenceStore, Finding, SourceRef
    st = EvidenceStore()
    for i, w in enumerate(["2024", "2025"], 1):
        st.add(Finding(f"F{i}", "pax", "Passengers — SFO", float(i), "passengers", "number", "observed", "d", "1",
                       {"airport_code": "SFO"}, {"label": w}, [SourceRef("s", [], [])]))
    ch = build_chart({"type": "bar", "findings": ["F1", "F2"]}, st)
    cats = [r["category"] for r in ch["vega_lite"]["data"]["values"]]
    assert len(set(cats)) == 2 and all("SFO" in c for c in cats)


def test_gemini_smoke_script_never_exceeds_five_requests(monkeypatch, tmp_path):
    """The live smoke test must stop at 5 generateContent calls even if the model keeps calling tools (fake endpoint)."""
    import importlib.util
    import io
    import urllib.request
    calls = []

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None, context=None):
        calls.append(req.full_url)
        body = {"modelVersion": "gemini-3.8-flash", "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 2},
                "candidates": [{"finishReason": "STOP", "content": {"parts": [
                    {"functionCall": {"name": "describe_catalog", "args": {}}}]}}]}
        return Resp(json.dumps(body).encode())
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    for k, v in {"AIRPORT_MODEL": "gemini", "AIRPORT_ALLOW_GEMINI": "1", "GEMINI_API_KEY": "test-not-a-key",
                 "AIRPORT_GEMINI_USAGE_LOG": str(tmp_path / "u.jsonl"), "AIRPORT_GEMINI_MODEL": "gemini-3.8-flash"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("AIRPORT_ALLOW_PAID", raising=False)
    spec = importlib.util.spec_from_file_location("gemini_smoke", str(get_paths().root.parent / "tools" / "gemini_smoke.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "model_in_catalog", lambda m, k: (True, "fake catalog"))
    monkeypatch.setenv("AIRPORT_GEMINI_SMOKE_COUNTER", str(tmp_path / "data" / "app" / "gemini_smoke_counter.json"))
    mod.main()
    assert len(calls) == 5                                                     # hard ceiling held
    assert sum(1 for _ in open(tmp_path / "u.jsonl")) == 5                    # every request counted persistently
    assert json.loads((tmp_path / "data" / "app" / "gemini_smoke_counter.json").read_text())["used"] == 5
    calls.clear()
    assert mod.main() == 2 and not calls                                       # a second run makes no request at all


# ---------------------------------------------------------------- general assessment capability
def test_assessment_intent_detection():
    from airport_analytics.claims import is_assessment_question as q
    for s in ("Which airport is a better investment opportunity?", "Which airport should we prioritize?",
              "Which airport is better suited for cargo?", "What is your assessment of these alternatives?",
              "Which is more attractive for expansion, BOS or PVD?"):
        assert q(s), s
    for s in ("What is the long-haul share at ANC?", "How many passengers used SFO?", "What was the average delay at LAX?",
              "Compare LAX and SNA congestion."):
        assert not q(s), s


def test_factual_questions_never_produce_assessments():
    from airport_agent.offline import OfflineBackend
    from airport_agent.runtime import Agent
    for question in ("What is the percentage of long haul flights out of Anchorage airport?",
                     "Compare LA and Santa Ana airport congestion levels."):
        r = Agent(OfflineBackend()).ask(question)
        assert r.kind == "answer" and not any(c["kind"] == "assessment" for c in r.structured["claims"])


def test_assessment_claim_rejected_for_a_factual_question(S, ev):
    from airport_analytics.render import validate
    t = ev["taxi"]
    a = {"headline": "Taxi-out", "body": "x", "claims": [{
        "kind": "assessment", "objective": "Lower airside congestion",
        "criteria": [{"name": "Taxi-out", "findings": [t["LAX"], t["SNA"]], "favors": "SNA", "direction": "lower_is_better"},
                     {"name": "Delay", "findings": [ev["delay"]["LAX"], ev["delay"]["SNA"]], "favors": "neither"}],
        "judgment": "SNA shows less airside congestion.", "conditional_on": ["airside view only"],
        "would_change": ["terminal data"]}]}
    assert any("only for questions that ask for a judgment" in e for e in validate(a, S.ctx.store, question="What is the taxi-out time at LAX and SNA?"))
    assert not validate(a, S.ctx.store, question="Which airport is less congested and better to prioritize, LAX or SNA?")


def test_recommendations_need_traceable_consistent_evidence(S, ev):
    from airport_analytics.render import validate
    t, d = ev["taxi"], ev["delay"]
    Q = "Which airport should we prioritize, LAX or SNA?"
    base = {"kind": "assessment", "objective": "Lower airside congestion", "conditional_on": ["airside view only"],
            "would_change": ["terminal data"]}
    good = [{"name": "Taxi-out", "findings": [t["LAX"], t["SNA"]], "favors": "SNA", "direction": "lower_is_better"},
            {"name": "Delay", "findings": [d["LAX"], d["SNA"]], "favors": "neither", "direction": "lower_is_better"}]
    ok = lambda **kw: validate({"headline": "h", "body": "x", "claims": [{**base, **kw}]}, S.ctx.store, question=Q)
    assert not ok(criteria=good, judgment="SNA shows less airside congestion.")
    assert ok(criteria=[{"name": "Reputation", "findings": []}, good[0]], judgment="SNA is better.")          # no evidence
    assert ok(criteria=[{**good[0], "favors": "LAX"}, good[1]], judgment="LAX is better.")                     # wrong direction
    assert ok(criteria=[good[0], {**good[1], "favors": "LAX"}], judgment="LAX is better.")                     # inside 5% band
    assert ok(criteria=good, judgment="LAX is better.")                                                         # no criterion favours LAX
    assert ok(criteria=good, judgment="SNA is better with a heavier weight on taxi-out.")                      # invented weights
    assert ok(criteria=good, judgment="SNA is guaranteed to be better.")                                       # certainty
    assert ok(criteria=good, judgment="SNA is the more profitable investment.")                                # financial
    assert ok(criteria=[good[0]], judgment="SNA.")                                                             # single criterion
    assert not ok(criteria=[good[1]], abstain=True, judgment="")                                               # abstention allowed


def test_offline_assessment_uses_objective_specific_criteria_or_asks():
    from airport_agent.offline import OfflineBackend
    from airport_agent.runtime import Agent
    r = Agent(OfflineBackend()).ask("Which is the better investment opportunity, BOS or PVD?")
    a = next(c for c in r.structured["claims"] if c["kind"] == "assessment")["assessment"]
    assert "growth" in a["objective"].lower() and len(a["criteria"]) >= 3 and a["conditional_on"] and a["would_change"]
    r = Agent(OfflineBackend()).ask("Which airport is less congested and better to prioritize operationally, LAX or SNA?")
    a = next(c for c in r.structured["claims"] if c["kind"] == "assessment")["assessment"]
    assert "congestion" in a["objective"].lower() and not any("growth" in c["name"].lower() for c in a["criteria"])
    r = Agent(OfflineBackend()).ask("Which is better, LAX or SNA?")
    assert r.kind == "clarification" and "Better for what" in r.markdown


# ---------------------------------------------------------------- FDE behaviour: understanding and missing information
def test_information_gap_cases_are_classified_not_refused():
    from airport_analytics.information import check
    assert check("unmet demand at SFO")["case"] == "not_measurable"
    assert check("average airfare out of AUS")["case"] == "external"
    assert check("how many gates does BOS have")["case"] == "external"
    assert check("weather at DEN")["case"] == "proxy"
    assert check("long haul share")["case"] == "exists"
    assert check("passenger growth per capita")["case"] == "derivable"
    assert check("xyzzy")["case"] == "unknown"
    for need in ("unmet demand", "fares", "gates", "landing fees"):
        r = check(need)
        assert r["proxies"] and r["next_step"] and r["cannot_establish"]            # always a useful path forward


def test_investigation_block_requires_cited_established_items(S, ev):
    from airport_analytics.render import validate
    f = ev["sf_sfo"]
    base = {"headline": "SFO", "body": f"{{{f}}}"}
    good = {"objective": "understand demand pressure at SFO", "question_type": "investigation",
            "investigated": ["load factor"], "established": [f"seat factor {{{f}}}"],
            "unknown": ["actual unmet demand"], "next_step": "add fares"}
    assert not validate({**base, "investigation": good}, S.ctx.store)
    assert validate({**base, "investigation": {**good, "established": ["load factor is high"]}}, S.ctx.store)
    assert validate({**base, "investigation": {**good, "unknown": [f"maybe {{{f}}}"]}}, S.ctx.store)
    assert validate({**base, "investigation": {**good, "next_step": "this will definitely work"}}, S.ctx.store)


def test_decision_uses_conversation_context_before_asking():
    from airport_agent.offline import OfflineBackend
    from airport_agent.runtime import Agent
    a = Agent(OfflineBackend())
    a.ask("Which airports in New England are strong candidates for terminal expansion?")
    r = a.ask("Which one should we prioritize?")                     # options and objective come from the conversation
    assert r.kind == "answer"
    assess = next(c for c in r.structured["claims"] if c["kind"] == "assessment")["assessment"]
    assert "growth" in assess["objective"].lower()
    assert any("Assumed from context" in x for x in r.structured["assumptions"])
    b = Agent(OfflineBackend())
    assert b.ask("Which is better, LAX or SNA?").kind == "clarification"   # no context: one focused question


def test_changing_the_objective_changes_the_criteria():
    from airport_agent.offline import OfflineBackend
    from airport_agent.runtime import Agent
    a = Agent(OfflineBackend())
    g = a.ask("Which is the better investment opportunity, BOS or PWM?")
    c = a.ask("Which of BOS or PWM is better to prioritize for lower congestion?")
    crit = lambda r: {x["name"] for x in next(k for k in r.structured["claims"] if k["kind"] == "assessment")["assessment"]["criteria"]}
    assert crit(g) and crit(c) and not (crit(g) & crit(c))


# ---------------------------------------------------------------- assessments: conflicts, unknowns, insufficiency, sensitivity
def _assess(S, criteria, **kw):
    from airport_analytics.render import validate
    c = {"kind": "assessment", "objective": "Lower airside congestion", "criteria": criteria,
         "conditional_on": ["airside view only"], "would_change": ["terminal data"], **kw}
    return validate({"headline": "h", "body": "x", "claims": [c]}, S.ctx.store,
                    question="Which airport should we prioritize, LAX or SNA?")


def test_conflicting_criteria_require_tradeoffs(S, ev):
    t = ev["taxi"]
    pk = {next(c for c in ("LAX", "SNA") if c in f["label"]): f["id"] for f in
          S.call("run_analysis", {"spec": {"op": "aggregate", "metrics": ["tower_operations"],
                                           "entities": {"airports": ["LAX", "SNA"]}, "group_by": ["airport"]}})["findings"]}
    crit = [{"name": "Taxi-out", "findings": [t["LAX"], t["SNA"]], "favors": "SNA", "direction": "lower_is_better"},
            {"name": "Scale of operations", "findings": [pk["LAX"], pk["SNA"]], "favors": "LAX", "direction": "higher_is_better"}]
    assert any("trade-offs" in e for e in _assess(S, crit, judgment="SNA, on balance."))
    assert not _assess(S, crit, judgment="SNA, on balance.", tradeoffs=["LAX handles far more traffic"])


def test_unknown_values_cannot_favour_and_insufficient_evidence_must_abstain(S, ev):
    from airport_analytics.evidence import Finding, SourceRef
    st = S.ctx.store
    fid = st.new_id()
    st.add(Finding(fid, "dep_delay15_rate", "Departure delay rate — HVN — w", None, "ratio", "pct", "calculated", "d", "1",
                   {"airport_code": "HVN"}, {"label": "w"}, [SourceRef("bts_ontime", [], [])]))
    t = ev["taxi"]
    errs = _assess(S, [{"name": "Delay", "findings": [fid, t["SNA"]], "favors": "HVN"},
                       {"name": "Taxi", "findings": [t["LAX"], t["SNA"]], "favors": "SNA", "direction": "lower_is_better"}],
                   judgment="SNA.")
    assert any("not established" in e for e in errs) and any("insufficient" in e for e in errs)
    assert not _assess(S, [{"name": "Delay", "findings": [fid, t["SNA"]], "favors": "unclear"}], abstain=True,
                       abstain_reason="the delay data is missing for one airport")


def test_sensitivity_is_computed_and_false_robustness_is_rejected():
    from airport_agent.offline import OfflineBackend
    from airport_agent.runtime import Agent
    from airport_analytics.claims import robustness
    a = Agent(OfflineBackend())
    r = a.ask("Which is the better investment opportunity, PVD or BDL?")
    claim = next(c for c in r.structured["claims"] if c["kind"] == "assessment")["assessment"]
    assert claim["robust"] is False and "momentum_heavy" in claim["robustness"]          # leader flips with weighting
    assert claim["abstain"] and "too close" in claim["abstain_reason"]
    # a model that claims robustness anyway is rejected
    from airport_analytics.render import validate
    crit = [{"name": k["name"], "findings": k["findings"], "favors": k["favors"]} for k in claim["criteria"]]
    bad = {"kind": "assessment", "objective": "growth opportunity", "criteria": crit, "judgment": "BDL is robustly better in every scenario.",
           "conditional_on": ["x not established"], "would_change": ["y"], "tradeoffs": ["t"]}
    errs = validate({"headline": "h", "body": "x", "claims": [bad]}, a.evidence, question="Which is better, PVD or BDL?")
    assert any("claims robustness" in e for e in errs)


# ---------------------------------------------------------------- Groq provider (fake endpoint only: no key, no quota)
class _FakeResp:
    def __init__(self, body, headers=None):
        self._b = json.dumps(body).encode()
        self.headers = headers or {"x-ratelimit-remaining-tokens": "7000", "x-ratelimit-reset-tokens": "2.5s",
                                   "x-ratelimit-limit-tokens": "8000"}

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _groq_env(monkeypatch, tmp_path):
    for k, v in {"AIRPORT_ALLOW_GROQ": "1", "GROQ_API_KEY": "test-not-a-key",
                 "AIRPORT_GROQ_USAGE_LOG": str(tmp_path / "groq.jsonl")}.items():
        monkeypatch.setenv(k, v)


def _tool_call(name, args, i):
    return {"model": "openai/gpt-oss-120b", "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            "choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [
                {"id": f"call_{i}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}}]}


def test_groq_adapter_runs_the_same_agent_end_to_end(monkeypatch, tmp_path):
    import urllib.request
    from airport_agent.models import GroqBackend
    from airport_agent.runtime import Agent
    _groq_env(monkeypatch, tmp_path)
    sent = []
    script = [_tool_call("run_analysis", {"spec": {"op": "aggregate", "metrics": ["seat_factor"],
                                                   "entities": {"airports": ["SFO"]}}}, 1),
              _tool_call("compose_answer", {"answer": {"headline": "SFO seat factor", "body": "SFO: {F1} ({F1.period}).",
                                                       "claims": [{"kind": "fact", "text": "{F1}", "support": ["F1"]}]}}, 2)]

    def fake(req, timeout=None, context=None):
        sent.append(json.loads(req.data))
        assert req.get_header("Authorization") == "Bearer test-not-a-key"
        return _FakeResp(script[len(sent) - 1])
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    g = GroqBackend(sleep=lambda s: None)
    r = Agent(g).ask("What is the seat factor at SFO?")
    assert r.kind == "answer" and r.cited_findings == ["F1"]
    first, second = sent
    assert first["model"] == "openai/gpt-oss-120b" and first["messages"][0]["role"] == "system"
    assert {t["function"]["name"] for t in first["tools"]} >= {"run_analysis", "compose_answer", "check_information"}
    assert first["parallel_tool_calls"] is False and first["include_reasoning"] is False
    roles = [m["role"] for m in second["messages"]]
    assert roles[-2:] == ["assistant", "tool"] and second["messages"][-1]["tool_call_id"] == "call_1"
    assert sum(1 for _ in open(tmp_path / "groq.jsonl")) == 2 and g.rate["remaining_tokens"] == 7000


def test_groq_errors_stop_without_fallback_and_free_tier_caps_context(monkeypatch, tmp_path):
    import io
    import urllib.error
    import urllib.request
    from airport_agent.models import GroqBackend, ModelError
    from airport_agent.runtime import Agent
    _groq_env(monkeypatch, tmp_path)

    def fake(req, timeout=None, context=None):
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, io.BytesIO(b'{"error":"rate"}'))
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    g = GroqBackend(sleep=lambda s: None)
    a = Agent(g)
    assert a.limits.max_context_tokens == g.max_context_tokens == 8000          # smaller requests for the free tier
    r = a.ask("seat factor SFO")
    assert r.kind == "error" and "429" in r.errors[0]
    with pytest.raises(ModelError):
        GroqBackend(model="llama-3.3-70b-versatile")                             # unsupported / enterprise-only
    monkeypatch.delenv("AIRPORT_ALLOW_GROQ")
    with pytest.raises(ModelError):
        GroqBackend()


def test_groq_paces_on_rate_limit_headers_instead_of_failing(monkeypatch, tmp_path):
    from airport_agent.models import GroqBackend
    _groq_env(monkeypatch, tmp_path)
    waits = []
    g = GroqBackend(sleep=waits.append)
    g.rate = {"remaining_tokens": 500.0, "reset_tokens_s": 12.0}
    g._pace(3000)
    assert waits == [12.5]
    g.rate = {"remaining_tokens": 7900.0, "reset_tokens_s": 12.0}
    g._pace(1000)
    assert waits == [12.5]


def test_groq_smoke_script_never_exceeds_five_requests(monkeypatch, tmp_path):
    import importlib.util
    import urllib.request
    calls = []

    def fake(req, timeout=None, context=None):
        calls.append(req.full_url)
        return _FakeResp(_tool_call("describe_catalog", {}, len(calls)),
                         {"x-ratelimit-remaining-tokens": "250000", "x-ratelimit-reset-tokens": "1s"})
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    _groq_env(monkeypatch, tmp_path)
    monkeypatch.setenv("AIRPORT_GROQ_SMOKE_COUNTER", str(tmp_path / "counter.json"))
    spec = importlib.util.spec_from_file_location("groq_smoke", str(get_paths().root.parent / "tools" / "groq_smoke.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "model_in_catalog", lambda m, k: (True, "fake catalog"))
    mod.main()
    assert len(calls) == 5 and json.loads((tmp_path / "counter.json").read_text())["used"] == 5
    calls.clear()
    assert mod.main() == 2 and not calls                                        # persistent: no further request

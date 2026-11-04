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

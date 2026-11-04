"""Analytics engine: golden values, typed errors, generated property tests, grounding validator."""
from __future__ import annotations

import random

import pytest

from airport_data.config import get_paths

pytestmark = pytest.mark.skipif(not get_paths().db_file.exists(), reason="built DB required (python -m airport_data build)")


@pytest.fixture(scope="module")
def S():
    from airport_analytics.tools import Session
    return Session()


def run(S, spec):
    from airport_analytics.analysis import run_analysis
    return run_analysis(spec, S.ctx)


def val(S, metric, airports, window=None, group_by=None, filters=None):
    r = run(S, {"op": "aggregate", "metrics": [metric], "entities": {"airports": airports},
                "window": window, "group_by": group_by if group_by is not None else [], "filters": filters})
    return [f["value"] for f in r["findings"]]


# ---------------------------------------------------------------- golden values (independently checked in Phase 0/1)
def test_golden_values(S):
    assert val(S, "peak_hour_ops_p95", ["SFO"])[0] == 66
    lh = val(S, {"id": "long_haul_share", "params": {"min_miles": 3000, "scope": "all", "weight": "departures"}}, ["ANC"],
             {"start": "2026-07", "end": "2026-07"})[0]
    assert lh == pytest.approx(0.2321, abs=5e-4)        # Phase 0: 23.1% incl. self-loops; view excludes them
    t100, acais = val(S, "passengers", ["SFO"], {"cy": 2025})[0], val(S, "acais_enplanements", ["SFO"], {"cy": 2025})[0]
    assert abs(t100 / acais - 1) < 0.015               # cross-source (T-100 vs FAA ACAIS), probe: 1.009


def test_distinct_area_not_double_counted(S):
    both = val(S, "cbsa_population", ["LAX", "SNA"], {"cy": 2024})[0]
    each = val(S, "cbsa_population", ["LAX", "SNA"], {"cy": 2024}, ["airport"])
    assert each[0] == each[1] == both                   # same CBSA: the group total counts it once


def test_historical_code_alias(S):
    assert val(S, "passengers", ["PBI"], {"cy": 2025}) == val(S, "passengers", ["DJT"], {"cy": 2025})


# ---------------------------------------------------------------- typed errors (never a silent wrong number)
@pytest.mark.parametrize("spec,code", [
    ({"op": "aggregate", "metrics": ["passengers"], "entities": {"airports": ["SFO"]}, "window": {"cy": 2019}}, "out_of_coverage"),
    ({"op": "aggregate", "metrics": ["nosuch"], "entities": {"airports": ["SFO"]}}, "invalid_spec"),
    ({"op": "aggregate", "metrics": ["seat_factor"], "entities": {"airports": ["Chicago"]}}, "ambiguous_entity"),
    ({"op": "aggregate", "metrics": ["seat_factor"], "entities": {"airports": ["Xanadu"]}}, "unknown_entity"),
    ({"op": "aggregate", "metrics": ["tower_operations"], "entities": {"airports": ["SFO"]}, "group_by": ["carrier"]}, "invalid_spec"),
    ({"op": "aggregate", "metrics": ["peak_hour_ops_max"], "entities": {"airports": ["SFO"]}, "group_by": ["month"]}, "invalid_spec"),
    ({"op": "aggregate", "metrics": ["taf_enplanements"], "entities": {"airports": ["SFO"]}}, "invalid_spec"),
    ({"op": "aggregate", "metrics": ["cbsa_population"], "entities": {"airports": ["SFO"]}, "window": {"cy_range": [2020, 2024]}}, "invalid_spec"),
    ({"op": "correlate", "entities": {"airports": ["SFO", "LAX"]}, "options": {"x": "passengers", "y": "seats"}}, "insufficient_data"),
    ({"op": "forecast_vs_actual", "entities": {"airports": ["SFO"]}, "options": {"fy": 2024}}, "not_applicable"),
    ({"op": "aggregate", "metrics": [{"id": "long_haul_share", "params": {"min_miles": 50}}], "entities": {"airports": ["ANC"]}}, "invalid_spec"),
])
def test_typed_errors(S, spec, code):
    from airport_analytics.evidence import AnalyticsError
    with pytest.raises(AnalyticsError) as e:
        run(S, spec)
    assert e.value.code == code


# ---------------------------------------------------------------- generated property tests
ADDITIVE = ["passengers", "seats", "departures", "freight_lbs", "tower_operations", "all_departures"]
RATIOS = {"seat_factor": ("passengers", "seats")}
WINDOWS = [{"t12": True}, {"cy": 2025}, {"fy": 2025}, {"start": "2025-03", "end": "2025-08"}]
POOL = ["SFO", "LAX", "BOS", "ATL", "DEN", "SEA", "PVD", "BDL", "ANC", "HNL", "MSP", "AUS", "SNA", "PWM", "BNA"]


def _cases(n, seed):
    rng = random.Random(seed)
    for _ in range(n):
        yield rng.choice(ADDITIVE), rng.sample(POOL, rng.randint(2, 6)), rng.choice(WINDOWS)


@pytest.mark.parametrize("metric,airports,window", list(_cases(25, 1)))
def test_group_total_equals_sum_of_members(S, metric, airports, window):
    tot = val(S, metric, airports, window)[0]
    parts = val(S, metric, airports, window, ["airport"])
    assert tot == pytest.approx(sum(p for p in parts if p is not None), rel=1e-9)


@pytest.mark.parametrize("metric,airports,window", list(_cases(12, 2)))
def test_ratio_metric_is_ratio_of_sums(S, metric, airports, window):
    sf = val(S, "seat_factor", airports, window)[0]
    p, s = val(S, "passengers", airports, window)[0], val(S, "seats", airports, window)[0]
    assert sf == pytest.approx(p / s, rel=1e-12)


@pytest.mark.parametrize("metric", ["passengers", "seats", "tower_operations"])
def test_year_equals_sum_of_months(S, metric):
    y = val(S, metric, ["BOS"], {"cy": 2025})[0]
    months = val(S, metric, ["BOS"], {"cy": 2025}, ["month"])
    assert len(months) == 12 and y == pytest.approx(sum(months))


def test_transform_matches_arithmetic(S):
    r = run(S, {"op": "aggregate", "entities": {"airports": ["SEA"]},
                "metrics": [{"id": "passengers", "window": {"cy": 2025}, "transform": {"type": "pct_change", "compare_window": {"cy": 2024}}}]})
    got = r["findings"][0]["value"]
    assert got == pytest.approx(val(S, "passengers", ["SEA"], {"cy": 2025})[0] / val(S, "passengers", ["SEA"], {"cy": 2024})[0] - 1)


def test_rank_order_matches_values(S):
    r = run(S, {"op": "rank", "metrics": ["seat_factor"], "entities": {"airports": POOL[:8]}})
    vals = [row["seat_factor"]["value"] for row in r["table"]]
    assert vals == sorted(vals, reverse=True)


def test_finding_reproduces(S):
    r = run(S, {"op": "aggregate", "metrics": ["arr_delay15_rate"], "entities": {"airports": ["SFO"]}})
    f = S.ctx.store.get(r["findings"][0]["id"])
    again = run(S, dict(f.spec, op="aggregate"))
    assert again["findings"][0]["value"] == f.value


def test_screen_is_additive_and_never_imputes(S):
    r = run(S, {"op": "screen", "entities": {"group": {"census_division": "New England"}}})
    for row in r["table"]:
        assert row["score"]["value"] == pytest.approx(sum(c["points"] for c in row["components"].values()), abs=0.15)
    scored = {row["airport"] for row in r["table"]}
    assert not scored & {b["airport"] for b in r["gate"]["below_scale"]}
    assert r["disclaimer"]


def test_ontime_metrics_carry_coverage(S):
    r = run(S, {"op": "aggregate", "metrics": ["dep_delay15_rate"], "entities": {"airports": ["JFK", "SNA"]}})
    cov = {S.ctx.store.get(f["id"]).subject["airport_code"]: f["coverage"]["ratio"] for f in r["findings"]}
    assert cov["JFK"] < 0.7 < cov["SNA"]
    jfk = next(f for f in r["findings"] if S.ctx.store.get(f["id"]).subject["airport_code"] == "JFK")
    assert any("ONTIME_LOW_COVERAGE" in c or "coverage" in c.lower() for c in jfk["caveats"])


# ---------------------------------------------------------------- grounding validator
def test_validator_rejects_ungrounded_numbers(S):
    from airport_analytics.render import validate
    r = run(S, {"op": "aggregate", "metrics": ["passengers"], "entities": {"airports": ["SFO"]}})
    fid = r["findings"][0]["id"]
    ok = {"headline": "SFO traffic in 2025", "body": f"SFO carried {{{fid}}} in the window.",
          "claims": [{"kind": "fact", "text": f"{{{fid}}}", "support": [fid]}]}
    assert validate(ok, S.ctx.store) == []
    for bad in ({"headline": "SFO carried 26M passengers", "body": "x"},
                {"headline": "h", "body": "growth was 4.2%"},
                {"headline": "h", "body": "{F999999}"},
                {"headline": "h", "body": "x", "claims": [{"kind": "fact", "text": "SFO is congested"}]},
                {"headline": "h", "body": "about 50 gates"}):
        assert validate(bad, S.ctx.store), bad


def test_sql_tool_is_read_only_and_whitelisted(S):
    for q in ("DROP TABLE dim_airport", "SELECT * FROM ingest_manifest", "SELECT * FROM read_csv('/etc/passwd')",
              "SELECT 1; SELECT 2", "COPY dim_airport TO 'x.csv'"):
        assert S.call("query_sql", {"sql": q}).get("error"), q
    out = S.call("query_sql", {"sql": "SELECT current_code, runways_open FROM dim_airport WHERE current_code = 'SFO'"})
    cell = out["rows"][0]["runways_open"]
    assert S.ctx.store.get(cell["id"]).epistemic_class == "exploratory"

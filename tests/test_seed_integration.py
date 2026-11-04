"""Integration tests on the committed seed archive (real data, offline).

The seed DB is built once per session into a temp dir with networking disabled.
"""
from __future__ import annotations

import duckdb
import pytest

from airport_data.build import build
from airport_data.config import get_paths
from airport_data.coverage import run_coverage
from airport_data.examples import EXAMPLES, run_file
from airport_data.rawstore import RawStore
from airport_data.sources import registry

pytestmark = pytest.mark.seed


@pytest.fixture(scope="session")
def con(seed_db):
    paths, _ = seed_db
    c = duckdb.connect(str(paths.db_file), read_only=True)
    yield c
    c.close()


def _table_fingerprints(db) -> dict[str, tuple]:
    c = duckdb.connect(str(db), read_only=True)
    names = [r[0] for r in c.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' "
                                     "AND table_name NOT IN ('build_info', 'fetch_events') ORDER BY 1").fetchall()]
    fp = {}
    for n in names:
        cols = [r[0] for r in c.execute(f'DESCRIBE "{n}"').fetchall()]
        fp[n] = c.execute(f'SELECT count(*), sum(hash(t)) FROM (SELECT * FROM "{n}") t').fetchone() + (tuple(cols),)
    c.close()
    return fp


# ---------------------------------------------------------------- reproducibility & preservation
def test_seed_build_has_no_rejected_or_uncovered_periods(seed_db):
    _, res = seed_db
    assert res.uncovered_periods == []
    assert res.failed == []


def test_rebuild_is_bit_for_bit_reproducible(seed_db, tmp_path_factory):
    paths, _ = seed_db
    first = _table_fingerprints(paths.db_file)
    build(paths, registry(paths), log=lambda *_: None)          # same raw archive, second build
    assert _table_fingerprints(paths.db_file) == first


def test_every_selected_raw_file_matches_its_checksum(seed_db):
    paths, res = seed_db
    store = RawStore(paths.raw)
    sel = [m for m in res.manifest if m["selected"]]
    assert sel
    for m in sel:
        v = next(v for v in store.vintages(m["source_id"], m["period"]) if v.vintage_id == m["vintage_id"])
        assert store.verify(v) == [], (m["source_id"], m["period"])


def test_manifest_records_required_lineage(con):
    rows = con.execute("""SELECT count(*) FILTER (WHERE url IS NULL OR content_sha256 IS NULL OR row_counts IS NULL
                                                   OR schema_sha256 IS NULL OR validation_status IS NULL OR files IS NULL)
                          FROM ingest_manifest WHERE selected""").fetchone()[0]
    assert rows == 0
    # every promoted row is traceable to a manifest entry
    orphans = con.execute("""SELECT count(*) FROM (SELECT DISTINCT _source_id, _period, _vintage_id FROM t100_segment) t
                             LEFT JOIN ingest_manifest m ON m.source_id = t._source_id AND m.period = t._period
                                                        AND m.vintage_id = t._vintage_id AND m.selected
                             WHERE m.source_id IS NULL""").fetchone()[0]
    assert orphans == 0


# ---------------------------------------------------------------- coverage
def test_coverage_requirements(con):
    failing = [(r.id, r.detail) for r in run_coverage(con) if not r.passed]
    # freshness depends on the wall clock; everything else must pass on the seed
    assert [f for f in failing if f[0] != "no_stale_or_missing_sources"] == []


# ---------------------------------------------------------------- known Phase-0 traps
def test_ontime_month_size_is_realistic(con):
    # Phase 0: a corrupt download produced ~225k rows; real months are ~0.6M
    for (n,) in con.execute("SELECT count(*) FROM ontime_flight GROUP BY _period").fetchall():
        assert 450_000 < n < 750_000


def test_t100_is_all_carriers_not_domestic_only(con):
    foreign = con.execute("SELECT count(DISTINCT unique_carrier) FROM t100_segment WHERE data_source LIKE '%F'").fetchone()[0]
    intl = con.execute("SELECT count(*) FROM t100_segment WHERE origin_country <> 'US' OR dest_country <> 'US'").fetchone()[0]
    assert foreign > 50 and intl > 10_000


def test_renamed_airport_keeps_one_identity(con):
    # Palm Beach: BTS code PBI -> FAA/ACAIS LID DJT; one airport_id across sources
    ids = con.execute("SELECT DISTINCT airport_id FROM xref_faa_lid WHERE faa_lid IN ('PBI', 'DJT')").fetchall()
    assert len(ids) == 1
    enp = con.execute("SELECT airport_id FROM v_faa_enplanements_annual WHERE locid = 'DJT' AND cy = 2025").fetchone()
    assert enp and enp[0] == ids[0][0]


def test_faa_lid_differs_from_iata_resolves(con):
    # FAA LID GPI = IATA FCA (Kalispell); IWA = AZA (Mesa)
    got = dict(con.execute("SELECT faa_lid, current_code FROM xref_faa_lid WHERE faa_lid IN ('GPI', 'IWA')").fetchall())
    assert got == {"GPI": "FCA", "IWA": "AZA"}


def test_taf_years_are_fiscal_and_split_historical_forecast(con):
    hist_max, fc_min = con.execute("""SELECT max(fiscal_year) FILTER (WHERE record_type='historical'),
                                             min(fiscal_year) FILTER (WHERE record_type='forecast') FROM v_taf_enplanements""").fetchone()
    assert hist_max < fc_min
    cols = {r[0] for r in con.execute("DESCRIBE v_taf_enplanements").fetchall()}
    assert "fiscal_year" in cols and "year" not in cols


def test_self_loops_excluded_from_semantic_view(con):
    assert con.execute("SELECT count(*) FROM v_t100_segment WHERE origin = dest").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM t100_segment WHERE origin = dest").fetchone()[0] > 0   # kept in source table


def test_unverified_curated_facts_are_labelled(con):
    bad = con.execute("""SELECT count(*) FROM curated_constraint
                         WHERE NOT (verification LIKE 'verified:%' OR verification LIKE 'unverified:%')""").fetchone()[0]
    assert bad == 0


# ---------------------------------------------------------------- the four validation cases
def _results(con, name):
    return run_file(con, EXAMPLES / name)


def test_q1_region_inputs(con):
    (_, cols, rows), = _results(con, "q1_region_expansion_inputs.sql")
    codes = {r[0] for r in rows}
    assert {"BOS", "BDL", "PVD", "MHT", "PWM", "BTV"} <= codes
    i = cols.index("t100_pax_t12"), cols.index("taf_growth_fy25_35_pct"), cols.index("seat_factor_t12_pct")
    big = [r for r in rows if r[cols.index("hub")] in ("L", "M", "S")]
    assert big and all(r[j] is not None for r in big for j in i)


def test_q1_generalises_to_another_region(con):
    con.execute("SET VARIABLE division = 'Mountain'")
    stmt = [s for s in (EXAMPLES / "q1_region_expansion_inputs.sql").read_text().split(";") if "WITH latest" in s][0]
    rows = con.execute(stmt).fetchall()
    assert {"DEN", "PHX", "LAS", "SLC"} <= {r[0] for r in rows}


def test_q2_congestion_inputs(con):
    (_, cols, rows), (_, _, constraints) = _results(con, "q2_congestion_compare_inputs.sql")
    by = {r[0]: dict(zip(cols, r)) for r in rows}
    assert set(by) == {"LAX", "SNA"}
    for code in by:
        for k in ("dep_delay15_pct", "avg_taxi_out_min", "peak_hour_sched_ops", "t100_deps_cy2025", "taf_total_ops_fy2024"):
            assert by[code][k] is not None, (code, k)
    assert by["SNA"]["ga_share_pct"] > by["LAX"]["ga_share_pct"]        # SNA is GA-heavy; LAX is not
    assert any(c[0] == "SNA" and c[1] == "regulatory_cap" for c in constraints)


def test_q3_long_haul_definitions(con):
    (_, cols, rows), = _results(con, "q3_long_haul_share_inputs.sql")
    t = {(r[0], r[1]): dict(zip(cols, r)) for r in rows}
    assert {("all", 3000), ("passenger", 3000), ("freight", 3000)} <= set(t)
    # Phase-0 finding: cargo is far more long-haul than passenger flying at ANC
    assert t[("freight", 3000)]["long_haul_pct"] > 3 * t[("passenger", 3000)]["long_haul_pct"]
    assert 0 < t[("passenger", 3000)]["long_haul_pct"] < t[("all", 3000)]["long_haul_pct"] < t[("freight", 3000)]["long_haul_pct"]


def test_q3_golden_july_2026_matches_phase0(con):
    # Phase 0 computed from a one-off download (Jul 2026, >=3000 mi, all departures): 23.1%
    v = con.execute("""SELECT round(100.0 * sum(departures_performed) FILTER (WHERE distance >= 3000) / sum(departures_performed), 1)
                       FROM t100_segment WHERE origin = 'ANC' AND year = 2026 AND month = 7""").fetchone()[0]
    assert v == pytest.approx(23.1, abs=0.05)


def test_q4_unmet_demand_inputs(con):
    res = _results(con, "q4_unmet_demand_inputs.sql")
    monthly, routes, ops, peak, taf = (r[2] for r in res)
    assert len(monthly) >= 24
    assert routes[0][0] > 100                      # route-months available for a spill-type estimate
    assert len(ops) >= 3                           # several on-time months with delay causes
    assert any("Instrument" in str(r[0]) for r in peak) and any(r[0].startswith("observed") for r in peak)
    assert any(r[1] == "forecast" for r in taf) and any(r[1] == "historical" for r in taf)
    for r in taf:                                   # total = domestic + international (semantic trap found in Phase 1)
        assert r[2] == r[3] + r[4]


# ---------------------------------------------------------------- graceful degradation
def test_build_with_no_data_still_produces_queryable_schema(tmp_path):
    paths = get_paths(tmp_path / "empty")
    (paths.root / "reference").mkdir(parents=True)
    res = build(paths, registry(paths), log=lambda *_: None)
    c = duckdb.connect(str(paths.db_file), read_only=True)
    for f in sorted(EXAMPLES.glob("q*.sql")):
        for stmt, cols, rows in run_file(c, f):
            pass                                    # binds and runs; empty results, not errors
    assert {r[3] for r in c.execute("SELECT * FROM v_source_freshness").fetchall()} == {None}
    assert c.execute("SELECT count(*) FROM v_source_freshness WHERE freshness = 'MISSING'").fetchone()[0] == len(registry(paths))

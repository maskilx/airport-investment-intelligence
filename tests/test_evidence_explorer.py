"""Local evidence explorer: the data behind a finding, the original files, and the security boundary around them."""
from __future__ import annotations

import hashlib
import json

import pytest

from airport_data.config import get_paths

pytestmark = pytest.mark.skipif(not get_paths().db_file.exists(), reason="built DB required")


@pytest.fixture(scope="module")
def S():
    from airport_analytics.tools import Session
    return Session()


def _finding(S, spec):
    r = S.call("run_analysis", {"spec": spec})
    return S.ctx.store.get(r["findings"][0]["id"])


@pytest.mark.parametrize("metric,airport,source", [
    ("seat_factor", "BOS", "bts_t100_segment"),
    ("dep_delay15_rate", "LAX", "bts_ontime"),
    ("tower_operations", "LAX", "faa_atads_ops"),
    ({"id": "taf_enplanements", "window": {"fy": 2035}}, "SFO", "faa_taf"),
    ({"id": "grants_awarded_usd", "window": {"fy_range": [2021, 2025]}}, "BOS", "faa_grants"),
    ({"id": "long_haul_share", "params": {"min_miles": 2000}}, "ANC", "bts_t100_segment"),
])
def test_data_used_recomputes_the_finding_exactly_from_listed_rows(S, metric, airport, source):
    from airport_analytics.evidence_data import data_used
    f = _finding(S, {"op": "aggregate", "metrics": [metric], "entities": {"airports": [airport]}})
    d = data_used(S.engine, f, S.ctx.store)
    assert d["level"] == "records"
    c = d["calculation"]
    assert c["matches_finding"] is True and c["by_period"] and c["totals"]
    r = d["records"]
    assert r["total"] > 0 and len(r["rows"]) <= r["page_size"]
    vi = r["columns"].index("_vintage_id")
    vintages = {v for s in f.sources if s.source_id == source for v in s.vintage_ids}
    assert {row[vi] for row in r["rows"]} <= vintages                    # rows trace to the finding's own file versions


def test_honest_traceability_levels(S):
    from airport_analytics.evidence_data import data_used
    custom = _finding(S, {"op": "aggregate", "metrics": ["peak_hour_ops_p95"], "entities": {"airports": ["SFO"]}})
    d = data_used(S.engine, custom, S.ctx.store)
    assert d["level"] == "aggregates" and "not an exact list" in d["summary"]
    area = _finding(S, {"op": "aggregate", "metrics": ["cbsa_per_capita_income"], "entities": {"airports": ["BOS"]}})
    assert data_used(S.engine, area, S.ctx.store)["level"] == "source"
    a = _finding(S, {"op": "aggregate", "metrics": ["passengers"], "entities": {"airports": ["LAX"]}})
    b = _finding(S, {"op": "aggregate", "metrics": ["passengers"], "entities": {"airports": ["SNA"]}})
    ratio = S.ctx.store.get(S.call("derive", {"op": "ratio", "findings": [a.id, b.id]})["id"])
    d = data_used(S.engine, ratio, S.ctx.store)
    assert d["level"] == "inputs" and [i["id"] for i in d["inputs"]] == [a.id, b.id]
    q = S.call("query_sql", {"sql": "SELECT count(*) AS n FROM dim_airport"})
    sq = S.ctx.store.get(q["rows"][0]["n"]["id"])
    assert data_used(S.engine, sq, S.ctx.store)["query"].startswith("SELECT")


def test_records_paginate_and_counted_flags_explain_filters(S):
    from airport_analytics.evidence_data import data_used
    f = _finding(S, {"op": "aggregate", "metrics": ["seat_factor"], "entities": {"airports": ["BOS"]}})
    p0, p1 = data_used(S.engine, f, S.ctx.store, 0), data_used(S.engine, f, S.ctx.store, 1)
    assert p0["records"]["rows"] != p1["records"]["rows"]
    assert any(c.startswith("counted_in_") for c in p0["records"]["columns"])          # passenger-service filter shown


# ---------------------------------------------------------------- original files over the API (read-only, bounded)
@pytest.fixture()
def client(tmp_path):
    from fastapi.testclient import TestClient

    from airport_agent.offline import OfflineBackend
    from airport_app.server import App, create_app
    return TestClient(create_app(App(str(tmp_path / "conv.sqlite"), backend=OfflineBackend())))


def _taf_vintage():
    import duckdb
    c = duckdb.connect(str(get_paths().db_file), read_only=True)
    return c.execute("SELECT period, vintage_id FROM ingest_manifest WHERE source_id='faa_taf' AND selected").fetchone()


def test_vintage_preview_find_and_download_from_the_local_archive(client):
    period, vid = _taf_vintage()
    v = client.get(f"/api/evidence/vintage/faa_taf/{period}/{vid}").json()
    assert v["files"][0]["name"] == "APO100_TAF_Final_2025.zip" and v["validation"] == "pass" and v["rows_loaded"]
    assert any(l["label"] == "Official dataset page" for l in v["publisher_links"])
    base = f"/api/evidence/file/faa_taf/{period}/{vid}/APO100_TAF_Final_2025.zip"
    pv = client.get(f"{base}/preview", params={"member": "Enplanements.xlsx", "find": "SFO"}).json()
    assert pv["member"] == "Enplanements.xlsx" and pv["rows"] and all("SFO" in [str(c).strip().upper() for c in r] for r in pv["rows"])
    dl = client.get(f"{base}/download")
    assert dl.status_code == 200 and hashlib.sha256(dl.content).hexdigest() == v["files"][0]["sha256"]


def test_conversation_finding_data_endpoint(client):
    cid = client.post("/api/conversations").json()["id"]
    client.post(f"/api/conversations/{cid}/messages", json={"text": "Compare LA and Santa Ana airport congestion levels."})
    d = client.get(f"/api/conversations/{cid}/findings/F1/data").json()
    assert d["level"] == "records" and d["calculation"]["matches_finding"] is True


@pytest.mark.parametrize("path", [
    "/api/evidence/file/faa_taf/2025/..%2F..%2F..%2Fapp/conversations.sqlite/download",
    "/api/evidence/file/..%2F..%2Fdb/x/y/airport.duckdb/download",
    "/api/evidence/file/faa_taf/2025/{vid}/meta.json/download",
    "/api/evidence/file/faa_taf/2025/{vid}/..%2F..%2F..%2F..%2F.env/download",
    "/api/evidence/file/faa_taf/2025/{vid}/%2Fetc%2Fpasswd/download",
    "/api/evidence/vintage/faa_taf/2025/..",
])
def test_no_access_outside_listed_archive_files(client, path):
    _, vid = _taf_vintage()
    r = client.get(path.replace("{vid}", vid))
    assert r.status_code in (400, 404, 405)
    assert b"GEMINI" not in r.content and b"SQLite format" not in r.content

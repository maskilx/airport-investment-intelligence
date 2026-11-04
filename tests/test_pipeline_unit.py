"""Pipeline mechanics on synthetic data: preservation, integrity, fallback, atomicity."""
from __future__ import annotations

import json
import os

import duckdb
import pytest

from airport_data.build import build
from airport_data.events import EventLog
from airport_data.ingest import fetch_period
from airport_data.rawstore import RawFile, RawStore
from airport_data.sources.base import month_periods, snake

from conftest import csv_for


def _ctx(paths):
    return RawStore(paths.raw), EventLog(paths.manifest / "fetch_events.jsonl")


# ---------------------------------------------------------------- raw store
def test_identical_redownload_does_not_create_vintage(tmp_paths):
    store = RawStore(tmp_paths.raw)
    v1, c1 = store.put("s", "2026-01", [RawFile("a.csv", b"x,y\n1,2\n")], {"url": "u"})
    v2, c2 = store.put("s", "2026-01", [RawFile("a.csv", b"x,y\n1,2\n")], {"url": "u"})
    assert c1 and not c2 and v1.vintage_id == v2.vintage_id
    assert len(store.vintages("s", "2026-01")) == 1


def test_revision_creates_new_vintage_and_preserves_old(tmp_paths):
    store = RawStore(tmp_paths.raw)
    v1, _ = store.put("s", "2026-01", [RawFile("a.csv", b"x\n1\n")], {})
    v2, created = store.put("s", "2026-01", [RawFile("a.csv", b"x\n2\n")], {})
    assert created and v2.vintage_id != v1.vintage_id
    assert v2.meta["supersedes"] == v1.vintage_id
    assert (v1.path / "a.csv").read_bytes() == b"x\n1\n"          # original untouched
    assert not os.access(v1.path / "a.csv", os.W_OK)              # read-only on disk
    assert [v.vintage_id for v in store.vintages("s", "2026-01")] == [v1.vintage_id, v2.vintage_id]


def test_verify_detects_tampering(tmp_paths):
    store = RawStore(tmp_paths.raw)
    v, _ = store.put("s", "p", [RawFile("a.csv", b"abc")], {})
    p = v.path / "a.csv"
    os.chmod(p, 0o644)
    p.write_bytes(b"abd")
    assert store.verify(v) == ["checksum mismatch a.csv"]


def test_incomplete_vintage_without_meta_is_ignored(tmp_paths):
    store = RawStore(tmp_paths.raw)
    (tmp_paths.raw / "s" / "p" / "20990101T000000Z").mkdir(parents=True)
    assert store.vintages("s", "p") == []


# ---------------------------------------------------------------- fetch
def test_truncated_zip_is_rejected_and_not_stored(tmp_paths, fake):
    store, log = _ctx(tmp_paths)
    good = csv_for("2026-01", [("SFO", 10)])
    fake.payload["2026-01"] = good[: len(good) // 2]              # simulated truncation
    out = fetch_period(fake, "2026-01", store, log, http=None)
    assert out.action == "rejected"
    assert store.vintages(fake.id, "2026-01") == []
    assert log.read()[-1]["action"] == "rejected"


def test_failed_fetch_keeps_previous_vintage(tmp_paths, fake):
    store, log = _ctx(tmp_paths)
    fake.payload["2026-01"] = csv_for("2026-01", [("SFO", 10)])
    assert fetch_period(fake, "2026-01", store, log, None).action == "stored"
    fake.fail.add("2026-01")
    assert fetch_period(fake, "2026-01", store, log, None).action == "failed"
    assert len(store.vintages(fake.id, "2026-01")) == 1
    assert [e["action"] for e in log.read()] == ["stored", "failed"]


# ---------------------------------------------------------------- build
def _fetch(fake, store, log, period, rows, **kw):
    fake.payload[period] = csv_for(period, rows, **kw)
    return fetch_period(fake, period, store, log, None)


def test_invalid_revision_falls_back_to_previous_valid_vintage(tmp_paths, fake):
    store, log = _ctx(tmp_paths)
    _fetch(fake, store, log, "2026-01", [("SFO", 10), ("LAX", 20)])
    # publisher "revision" that contains the wrong month -> blocking failure
    fake.payload["2026-01"] = csv_for("2026-02", [("SFO", 99)])
    fetch_period(fake, "2026-01", store, log, None)
    assert len(store.vintages(fake.id, "2026-01")) == 2
    res = build(tmp_paths, {fake.id: fake}, log=lambda *_: None)
    con = duckdb.connect(str(tmp_paths.db_file), read_only=True)
    assert con.execute("SELECT sum(flights) FROM fake_fact").fetchone()[0] == 30          # old valid data serves
    roles = con.execute("SELECT role, validation_status FROM ingest_manifest ORDER BY vintage_id").fetchall()
    assert roles == [("selected", "pass"), ("rejected", "fail")]
    assert res.uncovered_periods == []
    rep = json.loads(next((tmp_paths.manifest / "validation" / fake.id / "2026-01").glob("*.json")).read_text())
    assert "status" in rep and "checks" in rep


def test_period_with_no_valid_vintage_is_reported(tmp_paths, fake):
    store, log = _ctx(tmp_paths)
    _fetch(fake, store, log, "2026-01", [("SFO", -5)])                 # negative -> blocking
    res = build(tmp_paths, {fake.id: fake}, log=lambda *_: None)
    assert res.uncovered_periods == [(fake.id, "2026-01")]
    con = duckdb.connect(str(tmp_paths.db_file), read_only=True)
    assert con.execute("SELECT count(*) FROM fake_fact").fetchone()[0] == 0


def test_additive_schema_evolution(tmp_paths, fake):
    store, log = _ctx(tmp_paths)
    _fetch(fake, store, log, "2026-01", [("SFO", 1)])
    _fetch(fake, store, log, "2026-02", [("SFO", 2)], extra_col="NEW_FIELD")
    build(tmp_paths, {fake.id: fake}, log=lambda *_: None)
    con = duckdb.connect(str(tmp_paths.db_file), read_only=True)
    assert con.execute("SELECT count(*), count(new_field) FROM fake_fact").fetchone() == (2, 1)


def test_lineage_columns_and_manifest_fields(tmp_paths, fake):
    store, log = _ctx(tmp_paths)
    _fetch(fake, store, log, "2026-01", [("SFO", 1)])
    build(tmp_paths, {fake.id: fake}, log=lambda *_: None)
    con = duckdb.connect(str(tmp_paths.db_file), read_only=True)
    assert con.execute("SELECT _source_id, _period FROM fake_fact").fetchone() == (fake.id, "2026-01")
    cols = {r[0] for r in con.execute("DESCRIBE ingest_manifest").fetchall()}
    assert {"source_id", "period", "vintage_id", "url", "content_sha256", "row_counts", "schema_sha256",
            "validation_status", "selected", "files"} <= cols


def test_failed_build_leaves_existing_db_intact(tmp_paths, fake, monkeypatch):
    store, log = _ctx(tmp_paths)
    _fetch(fake, store, log, "2026-01", [("SFO", 1)])
    build(tmp_paths, {fake.id: fake}, log=lambda *_: None)
    before = tmp_paths.db_file.read_bytes()
    import airport_data.build as b
    monkeypatch.setattr(b, "_write_metadata", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        build(tmp_paths, {fake.id: fake}, log=lambda *_: None)
    assert tmp_paths.db_file.read_bytes() == before
    assert not list(tmp_paths.db_dir.glob("airport.duckdb.building*"))
    assert not (tmp_paths.db_dir / "build.lock").exists()


def test_build_is_offline(tmp_paths, fake, no_network):
    store, log = _ctx(tmp_paths)
    v, _ = store.put(fake.id, "2026-01", [RawFile("2026-01.zip", csv_for("2026-01", [("SFO", 1)]))], {})
    build(tmp_paths, {fake.id: fake}, log=lambda *_: None)   # would raise if it touched the network


# ---------------------------------------------------------------- helpers
@pytest.mark.parametrize("raw,expected", [
    ("DayofMonth", "day_of_month"), ("CRSDepTime", "crs_dep_time"), ("DOT_ID_Reporting_Airline", "dot_id_reporting_airline"),
    ("OriginAirportID", "origin_airport_id"), ("DEPARTURES_PERFORMED", "departures_performed"),
    ("Div1WheelsOn", "div1_wheels_on"), ("CY 25 Enplanements", "cy_25_enplanements"), ("DepDel15", "dep_del15"),
])
def test_snake(raw, expected):
    assert snake(raw) == expected


def test_month_periods_cross_year():
    assert month_periods("2025-11", "2026-02") == ["2025-11", "2025-12", "2026-01", "2026-02"]


# ---------------------------------------------------------------- regressions from a data-pipeline code review
def test_latest_history_mode_loads_only_newest_snapshot(tmp_paths, fake):
    fake.history_mode = "latest"          # e.g. lookups / OurAirports / TAF releases
    store, log = _ctx(tmp_paths)
    _fetch(fake, store, log, "2026-01", [("SFO", 1)])
    _fetch(fake, store, log, "2026-02", [("SFO", 2)])
    res = build(tmp_paths, {fake.id: fake}, log=lambda *_: None)
    con = duckdb.connect(str(tmp_paths.db_file), read_only=True)
    assert con.execute("SELECT count(*), sum(flights) FROM fake_fact").fetchone() == (1, 2)   # no double counting
    roles = dict(con.execute("SELECT period, role FROM ingest_manifest").fetchall())
    assert roles == {"2026-02": "selected", "2026-01": "superseded_period"}
    assert res.uncovered_periods == []


def test_rows_with_null_period_fields_are_rejected(tmp_paths, fake):
    store, log = _ctx(tmp_paths)
    from conftest import make_zip
    fake.payload["2026-01"] = make_zip("d.csv", "YEAR,MONTH,AIRPORT,FLIGHTS\n2026,1,SFO,1\n,,LAX,5\n")
    fetch_period(fake, "2026-01", store, log, None)
    res = build(tmp_paths, {fake.id: fake}, log=lambda *_: None)
    assert res.uncovered_periods == [(fake.id, "2026-01")]


def test_check_crash_rejects_vintage_instead_of_aborting_build(tmp_paths, fake):
    store, log = _ctx(tmp_paths)
    from conftest import make_zip
    _fetch(fake, store, log, "2026-01", [("SFO", 1)])
    fake.payload["2026-01"] = make_zip("d.csv", "YEAR,MONTH,AIRPORT,FLIGHTS\n2026,1,SFO,abc\n")  # non-numeric
    fetch_period(fake, "2026-01", store, log, None)
    build(tmp_paths, {fake.id: fake}, log=lambda *_: None)                 # must not raise
    con = duckdb.connect(str(tmp_paths.db_file), read_only=True)
    assert con.execute("SELECT sum(flights) FROM fake_fact").fetchone()[0] == 1               # older valid vintage
    assert con.execute("SELECT count(*) FROM ingest_manifest WHERE role = 'rejected'").fetchone()[0] == 1


def test_unreadable_meta_is_ignored(tmp_paths):
    store = RawStore(tmp_paths.raw)
    store.put("s", "p", [RawFile("a.csv", b"x")], {})
    bad = tmp_paths.raw / "s" / "p" / "29990101T000000Z"
    bad.mkdir()
    (bad / "meta.json").write_text("{truncated")
    assert len(store.vintages("s", "p")) == 1


def test_identical_download_replaces_bitrotted_copy(tmp_paths):
    store = RawStore(tmp_paths.raw)
    v1, _ = store.put("s", "p", [RawFile("a.csv", b"good")], {})
    p = v1.path / "a.csv"
    os.chmod(p, 0o644)
    p.write_bytes(b"rot!")
    v2, created = store.put("s", "p", [RawFile("a.csv", b"good")], {})
    assert created and store.verify(v2) == []


def test_concurrent_build_is_refused(tmp_paths, fake):
    tmp_paths.db_dir.mkdir(parents=True)
    (tmp_paths.db_dir / "build.lock").write_text("123")
    with pytest.raises(RuntimeError, match="another build"):
        build(tmp_paths, {fake.id: fake}, log=lambda *_: None)

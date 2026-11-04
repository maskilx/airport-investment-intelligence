"""Missing periods must be distinguishable from zero activity (v_source_period_status logic)."""
from __future__ import annotations

import re

import duckdb

from airport_data.build import DERIVED_SQL


def _view_sql(name: str) -> str:
    sql = DERIVED_SQL.read_text()
    m = re.search(rf"CREATE OR REPLACE VIEW {name} AS.*?;\n", sql, re.S)
    assert m, name
    return m.group(0)


def test_gap_is_missing_and_recent_month_is_not_yet_expected():
    con = duckdb.connect()
    con.execute("CREATE TABLE source_catalog (id VARCHAR, period_kind VARCHAR, period_basis VARCHAR, expected_lag_days INTEGER)")
    con.execute("INSERT INTO source_catalog VALUES ('m', 'month', 'calendar', 60), ('y', 'year', 'calendar', 300)")
    con.execute("CREATE TABLE ingest_manifest (source_id VARCHAR, period VARCHAR, selected BOOLEAN)")
    today = con.execute("SELECT current_date").fetchone()[0]
    months = [con.execute(f"SELECT strftime(DATE '{today}' - INTERVAL {k} MONTH, '%Y-%m')").fetchone()[0]
              for k in (8, 7, 5, 4, 3)]                       # 6 months ago is a gap
    con.executemany("INSERT INTO ingest_manifest VALUES ('m', ?, true)", [[p] for p in months])
    con.execute("INSERT INTO ingest_manifest VALUES ('m', ?, false)",
                [con.execute(f"SELECT strftime(DATE '{today}' - INTERVAL 6 MONTH, '%Y-%m')").fetchone()[0]])  # rejected
    con.execute(_view_sql("v_source_period_status"))
    st = dict(con.execute("SELECT period, status FROM v_source_period_status WHERE source_id = 'm'").fetchall())
    gap = con.execute(f"SELECT strftime(DATE '{today}' - INTERVAL 6 MONTH, '%Y-%m')").fetchone()[0]
    assert st[gap] == "missing"                                 # a rejected vintage does not count as loaded
    assert all(st[p] == "loaded" for p in months)
    this_month = con.execute("SELECT strftime(current_date, '%Y-%m')").fetchone()[0]
    assert st[this_month] == "not_yet_expected"                 # inside publication lag


def test_fiscal_year_source_due_after_september_plus_lag():
    con = duckdb.connect()
    con.execute("CREATE TABLE source_catalog (id VARCHAR, period_kind VARCHAR, period_basis VARCHAR, expected_lag_days INTEGER)")
    con.execute("INSERT INTO source_catalog VALUES ('fy', 'year', 'fiscal', 30), ('cy', 'year', 'calendar', 30)")
    con.execute("CREATE TABLE ingest_manifest (source_id VARCHAR, period VARCHAR, selected BOOLEAN)")
    y = con.execute("SELECT year(current_date) - 3").fetchone()[0]
    con.executemany("INSERT INTO ingest_manifest VALUES (?, ?, true)", [["fy", str(y)], ["cy", str(y)]])
    con.execute(_view_sql("v_source_period_status"))
    st = {(s, p): v for s, p, v in con.execute("SELECT source_id, period, status FROM v_source_period_status").fetchall()}
    assert st[("fy", str(y + 1))] == "missing" and st[("cy", str(y + 1))] == "missing"
    # FY of the previous calendar year ended Sep 30 -> due; the calendar year equivalent is due too (Dec 31 + 30d)
    today = con.execute("SELECT current_date").fetchone()[0]
    fy_due = today >= __import__("datetime").date(today.year - 1, 9, 30) + __import__("datetime").timedelta(days=30)
    assert (st[("fy", str(today.year - 1))] == "missing") == fy_due

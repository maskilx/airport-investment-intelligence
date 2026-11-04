"""Command line: fetch | build | status | coverage | sources.

    python -m airport_data fetch --source bts_t100_segment --periods 2024-01:2026-07
    python -m airport_data fetch --all-default          # periods from config/ingest.toml
    python -m airport_data build                        # offline: raw archive -> DuckDB
    python -m airport_data status                       # manifest + freshness
    python -m airport_data coverage                     # coverage assertions report
"""
from __future__ import annotations

import argparse
import sys
import tomllib

from .config import REPO_ROOT, get_paths
from .events import EventLog
from .http import HttpClient
from .ingest import fetch_period, resolve_periods
from .rawstore import RawStore
from .sources import registry


def _fetch(args, paths, reg) -> int:
    store, log, http = RawStore(paths.raw), EventLog(paths.manifest / "fetch_events.jsonl"), HttpClient()
    plan: list[tuple[str, str]] = []
    if args.all_default:
        cfg = tomllib.loads((REPO_ROOT / "config" / "ingest.toml").read_text())
        plan = [(sid, s["periods"]) for sid, s in cfg["sources"].items() if s.get("enabled", True)]
    else:
        plan = [(args.source, args.periods)]
    bad = 0
    for sid, spec in plan:
        src = reg[sid]
        try:
            periods = resolve_periods(src, spec, http)
        except Exception as e:
            log.write(sid, None, "failed", error=f"period discovery: {e}")
            print(f"{sid}: period discovery failed: {e}")
            bad += 1
            continue
        for p in periods:
            o = fetch_period(src, p, store, log, http)
            print(f"{sid:22s} {p:10s} {o.action:9s} {o.vintage_id or ''} {o.detail[:120]}")
            bad += o.action in ("failed", "rejected")
    return 1 if bad else 0


def _build(args, paths, reg) -> int:
    from .build import build
    res = build(paths, reg)
    print(f"\nbuilt {res.db_path} in {res.seconds}s; vintages evaluated={sum(m['role'] != 'superseded' for m in res.manifest)}"
          f" rejected={len(res.failed)} uncovered_periods={res.uncovered_periods}")
    return 1 if res.uncovered_periods else 0


def _status(args, paths, reg) -> int:
    from .db import connect
    con = connect(paths)
    print(con.sql("SELECT * FROM v_source_freshness ORDER BY source_id"))
    print(con.sql("""SELECT source_id, count(*) FILTER (WHERE selected) AS periods_loaded,
                     min(period) FILTER (WHERE selected) AS first, max(period) FILTER (WHERE selected) AS last,
                     count(*) AS vintages, count(*) FILTER (WHERE validation_status='warn') AS warn,
                     count(*) FILTER (WHERE validation_status='fail') AS fail
                     FROM ingest_manifest GROUP BY 1 ORDER BY 1"""))
    return 0


def _coverage(args, paths, reg) -> int:
    from .coverage import run_coverage
    from .db import connect
    results = run_coverage(connect(paths))
    for r in results:
        print(f"[{'PASS' if r.passed else 'FAIL'}] {r.id}: {r.detail}")
    return 0 if all(r.passed for r in results) else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="airport_data")
    ap.add_argument("--data-dir", help="override data root (default: ./data or $AIRPORT_DATA_DIR)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--source")
    f.add_argument("--periods", default="latest")
    f.add_argument("--all-default", action="store_true")
    sub.add_parser("build")
    sub.add_parser("status")
    sub.add_parser("coverage")
    sub.add_parser("sources")
    sub.add_parser("demo-import", help="demo/snapshot (Parquet subset) -> demo/data/db/airport.duckdb")
    args = ap.parse_args(argv)
    if args.cmd == "demo-import":
        from .demo import import_snapshot
        print(f"demo database: {import_snapshot()}")
        return 0
    paths = get_paths(args.data_dir)
    reg = registry(paths)
    if args.cmd == "sources":
        for s in reg.values():
            print(f"{s.id:22s} {s.period_kind:8s} {s.cadence:8s} lag~{s.expected_lag_days:>3}d  {s.title}")
        return 0
    if args.cmd == "fetch" and not (args.all_default or args.source):
        ap.error("fetch needs --source or --all-default")
    return {"fetch": _fetch, "build": _build, "status": _status, "coverage": _coverage}[args.cmd](args, paths, reg)


if __name__ == "__main__":
    sys.exit(main())

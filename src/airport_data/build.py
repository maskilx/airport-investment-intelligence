"""Reproducible DuckDB build from the raw archive.

For every (source, period) the newest vintage is staged and validated; if it
fails a blocking check the next-older vintage is tried, so a bad revision never
replaces good data. The build writes to a temp file and atomically replaces the
DB only on success. Validation reports are persisted next to the manifest so
the outcome is auditable without the DB.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import duckdb

from . import __version__
from .config import Paths
from .events import EventLog
from .rawstore import RawStore, Vintage, sha256_bytes, utc_now
from .sources.base import Source
from .validation import RULES_VERSION, ValidationReport, error, generic_checks

LINEAGE = ("_source_id", "_period", "_vintage_id")
MANIFEST_COLUMNS = ["source_id", "period", "vintage_id", "role", "selected", "stored_at", "url", "request", "files",
                    "content_sha256", "bytes", "supersedes", "source_reported", "response_headers", "validation_status",
                    "rules_version", "row_counts", "schema_sha256", "schema", "errors", "warnings"]
DERIVED_SQL = Path(__file__).with_name("derived.sql")
DERIVED_DEPENDS_ON = ("t100_segment", "ontime_flight", "bts_lookup", "oa_airport", "oa_runway", "ref_us_state",
                      "faa_enplanements", "faa_cargo", "taf_airport", "taf_enplanements", "taf_operations")
# A derived-SQL error is a code bug, not a data problem: it fails the build loudly (old DB stays).


@dataclass
class BuildResult:
    db_path: Path
    manifest: list[dict[str, Any]] = field(default_factory=list)
    seconds: float = 0.0

    @property
    def failed(self) -> list[dict[str, Any]]:
        return [m for m in self.manifest if m["validation_status"] == "fail"]

    @property
    def uncovered_periods(self) -> list[tuple[str, str]]:
        """(source, period) pairs where no vintage passed validation."""
        sel = {(m["source_id"], m["period"]) for m in self.manifest if m["selected"]}
        allp = {(m["source_id"], m["period"]) for m in self.manifest if m["role"] != "superseded_period"}
        return sorted(allp - sel)


def _git_rev() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=Path(__file__).parent, timeout=5).stdout.strip() or None
    except Exception:
        return None


def _columns(con, table) -> dict[str, str]:
    return {r[0]: r[1] for r in con.execute(f'DESCRIBE "{table}"').fetchall()}


def _exists(con, table) -> bool:
    return bool(con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [table]).fetchone()[0])


def _promote(con, final: str, staging: str, v: Vintage) -> None:
    lineage = f"'{v.source_id}' AS _source_id, '{v.period}' AS _period, '{v.vintage_id}' AS _vintage_id"
    if not _exists(con, final):
        con.execute(f'CREATE TABLE "{final}" AS SELECT *, {lineage} FROM "{staging}"')
        return
    have, new = _columns(con, final), _columns(con, staging)
    for c, t in new.items():          # additive schema evolution (publisher added a column)
        if c not in have:
            con.execute(f'ALTER TABLE "{final}" ADD COLUMN "{c}" {t}')
    con.execute(f'INSERT INTO "{final}" BY NAME SELECT *, {lineage} FROM "{staging}"')


def _stage_and_validate(con, src: Source, v: Vintage, store: RawStore, tmp: Path) -> tuple[ValidationReport, dict[str, str]]:
    rep = ValidationReport(src.id, v.period, v.vintage_id)
    staging = {t.name: f"stg__{t.name}" for t in src.tables}
    integrity = store.verify(v)
    rep.add(error("raw_checksums", not integrity, "; ".join(integrity) or "sha256 verified"))
    if integrity:
        return rep, staging
    try:
        src.load(con, v, staging, tmp)
    except Exception as e:
        rep.add(error("load", False, f"{type(e).__name__}: {e}"))
        return rep, staging
    try:
        for spec in src.tables:
            generic_checks(con, spec, staging[spec.name], rep)
    except Exception as e:   # e.g. a column of unexpected type: reject this vintage, keep building
        rep.add(error("generic_checks", False, f"{type(e).__name__}: {e}"))
        return rep, staging
    if rep.status != "fail":
        try:
            for c in src.checks(con, v, staging):
                rep.add(c)
        except Exception as e:
            rep.add(error("source_checks", False, f"{type(e).__name__}: {e}"))
    return rep, staging


def _drop(con, names) -> None:
    for t in names:
        con.execute(f'DROP TABLE IF EXISTS "{t}"')


def build(paths: Paths, sources: dict[str, Source], log=print) -> BuildResult:
    t0 = time.time()
    store = RawStore(paths.raw)
    paths.db_dir.mkdir(parents=True, exist_ok=True)
    lock = paths.db_dir / "build.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        raise RuntimeError(f"another build holds {lock} (delete it if no build is running)") from None
    tmp_db = paths.db_dir / f"airport.duckdb.building-{os.getpid()}"
    work = paths.tmp / f"build-{os.getpid()}"
    con = duckdb.connect(str(tmp_db))
    res = BuildResult(paths.db_file)
    checks_rows: list[dict[str, Any]] = []
    try:
        for sid in sorted(sources):
            src = sources[sid]
            latest_only = getattr(src, "history_mode", "accumulate") == "latest"
            source_done = False
            for period in sorted(store.periods(sid), reverse=latest_only):
                selected = None
                for v in reversed(store.vintages(sid, period)):          # newest first
                    if selected is not None or source_done:   # kept on disk, recorded, not loaded
                        res.manifest.append(_manifest_row(src, v, None, False,
                                                          "superseded" if selected else "superseded_period"))
                        continue
                    rep, staging = _stage_and_validate(con, src, v, store, work)
                    ok = rep.status != "fail"
                    if ok:
                        con.execute("BEGIN TRANSACTION")   # all tables of a vintage promote together, or none
                        try:
                            for spec in src.tables:
                                _promote(con, spec.name, staging[spec.name], v)
                            con.execute("COMMIT")
                        except duckdb.Error as e:
                            con.execute("ROLLBACK")
                            rep.add(error("schema_compatible", False, str(e)))
                            ok = False
                    _save_report(paths, rep)
                    checks_rows += [{**c.__dict__, "source_id": sid, "period": period, "vintage_id": v.vintage_id}
                                    for c in rep.checks]
                    _drop(con, staging.values())
                    res.manifest.append(_manifest_row(src, v, rep, ok, "selected" if ok else "rejected"))
                    log(f"  {sid:22s} {period:10s} {v.vintage_id}  {rep.status:5s} "
                        f"{'' if ok else '-> REJECTED'} rows={rep.row_counts}")
                    if ok:
                        selected = v
                if selected is None and not source_done:
                    log(f"  !! {sid} {period}: no valid vintage — period is NOT in the database")
                if selected is not None and latest_only:
                    source_done = True   # snapshot/version sources: only the newest valid period is loaded
        _write_metadata(con, paths, sources, res.manifest, checks_rows)
        missing = [t for t in DERIVED_DEPENDS_ON if not _exists(con, t)]
        if missing:   # e.g. a test registry with only synthetic sources
            con.execute(f"ALTER TABLE build_info ADD COLUMN derived_layer VARCHAR DEFAULT 'skipped: missing {','.join(missing)}'")
        else:
            con.execute(DERIVED_SQL.read_text())
            con.execute("ALTER TABLE build_info ADD COLUMN derived_layer VARCHAR DEFAULT 'built'")
        con.execute("CHECKPOINT")
        con.close()
        for side in (".wal", ".wal.checkpoint", ".wal.recovery"):   # stale sidecars must not replay onto the new file
            Path(str(paths.db_file) + side).unlink(missing_ok=True)
        os.replace(tmp_db, paths.db_file)
    except BaseException:
        con.close()
        tmp_db.unlink(missing_ok=True)
        Path(str(tmp_db) + ".wal").unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
        lock.unlink(missing_ok=True)
    res.seconds = round(time.time() - t0, 1)
    return res


def _manifest_row(src: Source, v: Vintage, rep: ValidationReport | None, selected: bool, role: str) -> dict[str, Any]:
    m = v.meta
    return {
        "source_id": src.id, "period": v.period, "vintage_id": v.vintage_id, "role": role, "selected": selected,
        "stored_at": m.get("stored_at"), "url": m.get("url"), "request": json.dumps(m.get("request", {}), sort_keys=True),
        "files": json.dumps(m["files"]), "content_sha256": m["content_sha256"],
        "bytes": sum(f["bytes"] for f in m["files"]), "supersedes": m.get("supersedes"),
        "source_reported": json.dumps(m.get("source_reported", {}), sort_keys=True),
        "response_headers": json.dumps(m.get("response_headers", {}), sort_keys=True),
        "validation_status": rep.status if rep else None,
        "rules_version": rep.rules_version if rep else None,
        "row_counts": json.dumps(rep.row_counts if rep else {}),
        "schema_sha256": sha256_bytes(json.dumps(rep.schemas, sort_keys=True).encode()) if rep else None,
        "schema": json.dumps(rep.schemas) if rep else None,
        "errors": json.dumps([c.name + ": " + c.detail for c in rep.checks if not c.passed and c.severity == "error"]) if rep else None,
        "warnings": json.dumps([c.name + ": " + c.detail for c in rep.checks if not c.passed and c.severity == "warning"]) if rep else None,
    }


def _save_report(paths: Paths, rep: ValidationReport) -> None:
    d = paths.manifest / "validation" / rep.source_id / rep.period
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{rep.vintage_id}.json").write_text(json.dumps(rep.to_dict(), indent=1, sort_keys=True, default=str))


def _insert_dicts(con, table: str, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    if not rows and not columns:
        return
    cols = columns or list(rows[0].keys())
    con.execute(f'CREATE OR REPLACE TABLE "{table}" ({", ".join(f""""{c}" VARCHAR""" for c in cols)})')
    if rows:
        con.executemany(f'INSERT INTO "{table}" VALUES ({", ".join("?" * len(cols))})',
                        [[None if r.get(c) is None else str(r.get(c)) for c in cols] for r in rows])


def _write_metadata(con, paths: Paths, sources: dict[str, Source], manifest, checks_rows) -> None:
    _insert_dicts(con, "ingest_manifest", manifest, MANIFEST_COLUMNS)
    con.execute("ALTER TABLE ingest_manifest ALTER selected TYPE BOOLEAN USING selected = 'True'")
    con.execute("ALTER TABLE ingest_manifest ALTER bytes TYPE BIGINT")
    _insert_dicts(con, "validation_check", checks_rows,
                  ["source_id", "period", "vintage_id", "name", "severity", "passed", "detail", "table", "value"])
    con.execute("ALTER TABLE validation_check ALTER passed TYPE BOOLEAN USING passed = 'True'")
    _insert_dicts(con, "source_catalog", [s.describe() for s in sources.values()])
    con.execute("ALTER TABLE source_catalog ALTER expected_lag_days TYPE INTEGER")
    _insert_dicts(con, "table_catalog", [
        {"table_name": t.name, "source_id": s.id, "description": t.description,
         "required_columns": ",".join(t.required_columns), "unique_key": ",".join(t.unique_key)}
        for s in sources.values() for t in s.tables])
    events = EventLog(paths.manifest / "fetch_events.jsonl").read()
    _insert_dicts(con, "fetch_events", [{k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
                                         for k, v in e.items()} for e in events],
                  ["ts", "source_id", "period", "action", "vintage_id", "content_sha256", "bytes", "error", "errors", "url"])
    raw_fingerprint = sha256_bytes("\n".join(sorted(
        f"{m['source_id']}/{m['period']}/{m['vintage_id']}:{m['content_sha256']}" for m in manifest if m["selected"])).encode())
    _insert_dicts(con, "build_info", [{"built_at": utc_now(), "package_version": __version__, "git_rev": _git_rev(),
                                       "rules_version": RULES_VERSION, "selected_raw_fingerprint": raw_fingerprint}])
    # empty-but-present tables so derived SQL never breaks when a source has no data yet
    for s in sources.values():
        for t in s.tables:
            if not _exists(con, t.name):
                typ = dict(t.placeholder_types)
                cols = ", ".join(f'"{c}" {typ.get(c, "VARCHAR")}' for c in (t.required_columns + LINEAGE))
                con.execute(f'CREATE TABLE "{t.name}" ({cols})')

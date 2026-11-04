"""Demo dataset: a subset of the real database, shipped as Parquet in demo/snapshot/ (see tools/build_demo_snapshot.py).

    python -m airport_data demo-import     # demo/snapshot -> demo/data/db/airport.duckdb (seconds, offline)

The snapshot is portable: schema.sql lists tables, macros and views in a valid creation order, and load.sql names
Parquet files relative to the snapshot directory.
"""
from __future__ import annotations

import pathlib
import re

import duckdb

from .config import REPO_ROOT

SNAPSHOT = REPO_ROOT / "demo" / "snapshot"
DEMO_DATA = REPO_ROOT / "demo" / "data"


def statements(sql: str) -> list[str]:
    return [s.strip() for s in re.split(r";\s*\n", sql) if s.strip()]


def import_snapshot(snapshot: pathlib.Path = SNAPSHOT, db_file: pathlib.Path | None = None) -> pathlib.Path:
    db_file = db_file or DEMO_DATA / "db" / "airport.duckdb"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = db_file.with_suffix(".importing")
    tmp.unlink(missing_ok=True)
    con = duckdb.connect(str(tmp))
    try:
        for s in statements((snapshot / "schema.sql").read_text()):
            if not s.upper().startswith("CREATE VIEW"):
                con.execute(s)
        for s in statements((snapshot / "load.sql").read_text()):
            m = re.match(r"COPY (\S+) FROM '([^']+)'", s)
            if not m:
                raise ValueError(f"unexpected load statement: {s[:80]}")
            con.execute(f"COPY {m.group(1)} FROM '{(snapshot / pathlib.Path(m.group(2)).name).as_posix()}' (FORMAT PARQUET)")
        for s in statements((snapshot / "schema.sql").read_text()):
            if s.upper().startswith("CREATE VIEW"):
                con.execute(s)
        con.execute("CHECKPOINT")
    finally:
        con.close()
    tmp.replace(db_file)                                     # atomic: a half-imported file is never served
    return db_file


def order_and_relativise(snapshot: pathlib.Path) -> None:
    """Rewrite an EXPORT DATABASE output so it imports anywhere: views in dependency order, relative file names."""
    schema = statements((snapshot / "schema.sql").read_text())
    base = [s for s in schema if not s.upper().startswith("CREATE VIEW")]
    views = [s for s in schema if s.upper().startswith("CREATE VIEW")]
    con = duckdb.connect()
    for s in base:
        con.execute(s)
    ordered, pending = [], views
    while pending:
        nxt = []
        for s in pending:
            try:
                con.execute(s)
                ordered.append(s)
            except duckdb.CatalogException:
                nxt.append(s)
        if len(nxt) == len(pending):
            raise RuntimeError(f"cannot order {len(nxt)} views: {[v[:60] for v in nxt]}")
        pending = nxt
    con.close()
    (snapshot / "schema.sql").write_text(";\n".join(base + ordered) + ";\n")
    loads = [re.sub(r"FROM '([^']+)'", lambda m: f"FROM '{pathlib.Path(m.group(1)).name}'", s)
             for s in statements((snapshot / "load.sql").read_text())]
    (snapshot / "load.sql").write_text(";\n".join(loads) + ";\n")

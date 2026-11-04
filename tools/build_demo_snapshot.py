"""Build the redistributable demo snapshot (demo/snapshot/) from a full local database.

The demo snapshot is a SUBSET of the real database, not synthetic data:
  * every reference and annual table is copied whole (airports, TAF, FAA enplanements, BEA/Census, curated records);
  * the two large flight tables (BTS On-Time, BTS T-100) keep only rows that touch a demo airport
    (all New England airports, LAX, SNA, SFO, ANC); columns the analytics never read are blanked to save space;
  * `demo_scope` lists the demo airports, and the engine refuses analyses outside them (no silent partial answers);
  * `build_info.git_rev` records the source build, so findings remain traceable.

Every value comes from the publishers' files (US federal public-domain data, OurAirports public domain, and cited
curated records). The original source files themselves are not part of the snapshot.

    .venv/bin/python tools/build_demo_snapshot.py            # reads data/db/airport.duckdb, writes demo/snapshot/
"""
from __future__ import annotations

import pathlib
import re
import shutil
import sys
import tempfile

import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_DB = ROOT / "data" / "db" / "airport.duckdb"
OUT = ROOT / "demo" / "snapshot"
DEMO_CODES = ("LAX", "SNA", "SFO", "ANC")            # plus every airport in the New England census division
FACTS = ("ontime_flight", "t100_segment")


def referenced_columns(con, table: str) -> set[str]:
    """Columns that any analytics code or SQL mentions; the rest are blanked (they cannot affect a result)."""
    src = "\n".join(p.read_text() for p in (ROOT / "src").rglob("*.py"))
    src += (ROOT / "src" / "airport_data" / "derived.sql").read_text()
    src += "\n".join(p.read_text() for p in (ROOT / "config").glob("*.toml"))
    cols = [c[0] for c in con.execute(f"DESCRIBE {table}").fetchall()]
    return {c for c in cols if re.search(r"\b" + re.escape(c) + r"\b", src)}


def main() -> int:
    if not SRC_DB.exists():
        print(f"no full database at {SRC_DB}; run ./scripts/bootstrap.sh first", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / "demo.duckdb"
        shutil.copyfile(SRC_DB, work)                         # the full database is never modified
        con = duckdb.connect(str(work))
        codes = ", ".join(f"'{c}'" for c in DEMO_CODES)
        con.execute(f"""CREATE TABLE demo_scope AS SELECT airport_id, current_code AS code, name, census_division
                        FROM dim_airport WHERE census_division = 'New England' OR current_code IN ({codes})""")
        n_scope = con.execute("SELECT count(*) FROM demo_scope").fetchone()[0]
        for t in FACTS:
            before = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            con.execute(f"""DELETE FROM {t} WHERE origin_airport_id NOT IN (SELECT airport_id FROM demo_scope)
                            AND dest_airport_id NOT IN (SELECT airport_id FROM demo_scope)""")
            keep = referenced_columns(con, t)
            blank = [c[0] for c in con.execute(f"DESCRIBE {t}").fetchall() if c[0] not in keep]
            if blank:
                con.execute(f"UPDATE {t} SET " + ", ".join(f'"{c}" = NULL' for c in blank))
            after = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            print(f"{t}: {before:,} -> {after:,} rows; {len(blank)} unreferenced columns blanked")
        con.execute("ALTER TABLE build_info ADD COLUMN dataset VARCHAR DEFAULT 'demo'")
        con.execute("UPDATE build_info SET dataset = 'demo'")
        con.execute("CHECKPOINT")
        if OUT.exists():
            shutil.rmtree(OUT)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        con.execute(f"EXPORT DATABASE '{OUT}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        con.close()
    sys.path.insert(0, str(ROOT / "src"))
    from airport_data.demo import order_and_relativise
    order_and_relativise(OUT)                                 # portable: view order + relative Parquet paths
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"demo snapshot: {n_scope} airports in scope, {size / 1e6:.1f} MB in {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

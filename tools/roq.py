#!/usr/bin/env python3
"""Read-only SQL over the built DuckDB, for auditing.

usage: roq.py "SELECT ..."            (one statement; SELECT/WITH/DESCRIBE/SHOW/SUMMARIZE/PRAGMA table_info only)
       roq.py --raw-file <published-path-inside-data/raw>   prints first 40 lines of a raw CSV/TXT member listing
The DB is opened read_only; writes, ATTACH, COPY, INSTALL/LOAD, and file-reading functions are refused.
"""
import os, re, sys
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db" / "airport.duckdb"
ALLOWED = re.compile(r"^\s*(select|with|describe|show|summarize|pragma\s+table_info)\b", re.I | re.S)
BANNED = re.compile(r"\b(attach|detach|copy|install|load|export|import|create|insert|update|delete|drop|alter|"
                    r"read_csv\w*|read_parquet|read_json\w*|read_text|read_blob|glob|httpfs|getenv|system)\b", re.I)

def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sql = sys.argv[1].strip().rstrip(";")
    if ";" in sql or not ALLOWED.match(sql) or BANNED.search(sql):
        sys.exit("refused: one read-only SELECT/WITH/DESCRIBE statement only")
    con = duckdb.connect(str(DB), read_only=True, config={"enable_external_access": False})
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchmany(201)
    print("\t".join(cols))
    for r in rows[:200]:
        print("\t".join("" if v is None else str(v) for v in r))
    if len(rows) > 200:
        print("... (truncated at 200 rows)")

if __name__ == "__main__":
    main()

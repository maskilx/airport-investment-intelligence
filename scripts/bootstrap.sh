#!/usr/bin/env bash
# One-time setup on a new machine: Python env, public-source data download, database build.
# Safe to re-run: it skips steps that are already done. Nothing is deleted.
#   ./scripts/bootstrap.sh            # env + data (if missing) + DB (if missing)
#   ./scripts/bootstrap.sh --rebuild  # also rebuild the DB from the local raw archive
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3.12}"
if [ ! -x .venv/bin/python ]; then
  echo "== creating .venv with $PY"
  "$PY" -m venv .venv
fi
echo "== installing package (app + dev extras)"
.venv/bin/pip install -q -e ".[app,dev]"
[ -f .env ] || { cp .env.example .env; echo "== created .env from .env.example (offline mode)"; }

if [ ! -d data/raw/bts_t100_segment ]; then
  echo "== downloading public source files (BTS, FAA, Census, BEA, OurAirports); ~500 MB, can take 20-40 min"
  echo "   plan: config/ingest.toml. Every file is checksummed and stored as an immutable vintage under data/raw/."
  .venv/bin/python -m airport_data fetch --all-default
fi
if [ ! -f data/db/airport.duckdb ] || [ "${1:-}" = "--rebuild" ]; then
  echo "== building data/db/airport.duckdb from data/raw (validation is blocking)"
  .venv/bin/python -m airport_data build
fi
.venv/bin/python -m airport_data status | tail -n 25
echo
echo "Ready. Start the workspace with:  ./scripts/start.sh   then open http://127.0.0.1:8765"

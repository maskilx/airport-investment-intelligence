#!/usr/bin/env bash
# Fast demo: the real application on a bundled subset of the real data (demo/snapshot), offline planner,
# no API key and no data download. First run: about 15 seconds (measured from a clean clone without a pip cache).
#   ./scripts/demo.sh              open http://127.0.0.1:8765
#   ./scripts/demo.sh --port 8800  use another port
# Full data and live AI: ./scripts/bootstrap.sh, then ./scripts/start.sh (see README).
set -euo pipefail
cd "$(dirname "$0")/.."
PORT=8765
[ "${1:-}" = "--port" ] && PORT="${2:?--port needs a number}"

if [ ! -x .venv/bin/python ]; then
  PY=""
  for c in ${PYTHON:-} python3.12 python3.13 python3.14 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null; then PY="$c"; break; fi
  done
  [ -n "$PY" ] || { echo "ERROR: Python 3.12 or newer is required (set PYTHON=/path/to/python3.12)." >&2; exit 2; }
  echo "== creating .venv with $PY"
  "$PY" -m venv .venv
fi
if ! .venv/bin/python -c "import airport_app, fastapi, uvicorn, duckdb" 2>/dev/null; then
  echo "== installing the application"
  .venv/bin/pip install -q -e ".[app]"
fi
if [ ! -f demo/data/db/airport.duckdb ] || [ demo/snapshot/schema.sql -nt demo/data/db/airport.duckdb ]; then
  echo "== loading the demo dataset (demo/snapshot -> demo/data/db)"
  .venv/bin/python -m airport_data demo-import
fi
# Offline planner forced (no model calls, whatever .env says); demo data dir keeps demo conversations separate.
exec env AIRPORT_MODEL=offline AIRPORT_DATA_DIR="$PWD/demo/data" .venv/bin/python -m airport_app --port "$PORT"

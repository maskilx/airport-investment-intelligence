#!/usr/bin/env bash
# Start the local workspace. Mode comes from .env (see .env.example): OFFLINE by default, no model API calls.
# Usage: ./scripts/start.sh [--port 8765]
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ]; then
  echo "No virtualenv yet. Run ./scripts/bootstrap.sh first." >&2
  exit 2
fi
exec .venv/bin/python -m airport_app "$@"

#!/usr/bin/env bash
# Switch planner mode in .env (non-secret settings only), then restart the app.
#   ./scripts/mode.sh offline | gemini | status
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-status}" in
  offline|gemini) .venv/bin/python - "$1" <<'PY'
import runpy
import sys
ns = runpy.run_path("scripts/configure-gemini-key.py", run_name="helper")
mode = sys.argv[1]
ns["env_update"]({"AIRPORT_MODEL": mode, "AIRPORT_ALLOW_GEMINI": "1" if mode == "gemini" else None})
print(f"Mode set to {mode.upper()}. Restart: ./scripts/start.sh --restart")
PY
  ;;
  status) grep -E '^(AIRPORT_MODEL|AIRPORT_GEMINI_MODEL|AIRPORT_GEMINI_MAX_REQUESTS)=' .env 2>/dev/null || echo "AIRPORT_MODEL=offline (no .env)";;
  *) echo "usage: $0 offline|gemini|status" >&2; exit 2;;
esac

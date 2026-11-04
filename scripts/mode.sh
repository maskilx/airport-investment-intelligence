#!/usr/bin/env bash
# Switch planner mode in .env (non-secret settings only), then restart the app.
#   ./scripts/mode.sh offline | gemini | groq | status
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-status}" in
  offline|gemini|groq) .venv/bin/python - "$1" <<'PY'
import runpy
import sys
ns = runpy.run_path("scripts/configure-gemini-key.py", run_name="helper")
mode = sys.argv[1]
upd = {"AIRPORT_MODEL": mode}
if mode == "gemini":
    upd["AIRPORT_ALLOW_GEMINI"] = "1"
if mode == "groq":
    upd["AIRPORT_ALLOW_GROQ"] = "1"
ns["env_update"](upd)
print(f"Mode set to {mode.upper()}. Restart: ./scripts/start.sh --restart")
PY
  ;;
  status) grep -E '^(AIRPORT_MODEL|AIRPORT_GEMINI_MODEL|AIRPORT_GROQ_MODEL|AIRPORT_GEMINI_MAX_REQUESTS|AIRPORT_GROQ_MAX_REQUESTS)=' .env 2>/dev/null || echo "AIRPORT_MODEL=offline (no .env)";;
  *) echo "usage: $0 offline|gemini|groq|status" >&2; exit 2;;
esac

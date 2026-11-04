#!/usr/bin/env bash
# Start the local workspace from anywhere:  ~/Downloads/airport-investment-intelligence/scripts/start.sh
#   ./scripts/start.sh             start (refuses to start a second copy; tells you where the running one is)
#   ./scripts/start.sh --restart   stop the running copy of THIS app, then start (use after changing mode or key)
#   ./scripts/start.sh --stop      stop the running copy
#   ./scripts/start.sh --port 8800 use another port
# Mode comes from .env (./scripts/mode.sh offline|gemini). OFFLINE by default: no model API calls.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PORT=8765; ACTION=start; EXTRA=()
while [ $# -gt 0 ]; do
  case "$1" in
    --restart) ACTION=restart ;;
    --stop) ACTION=stop ;;
    --port) PORT="$2"; shift ;;
    *) EXTRA+=("$1") ;;
  esac
  shift
done

die() { echo "ERROR: $*" >&2; exit 2; }
[ -x .venv/bin/python ] || die "no Python environment in $ROOT/.venv. Run ./scripts/bootstrap.sh first."
[ -f data/db/airport.duckdb ] || die "database missing ($ROOT/data/db/airport.duckdb). Run ./scripts/bootstrap.sh (or: .venv/bin/python -m airport_data build)."
[ -d data/raw ] || echo "note: data/raw is absent; the app works from the built database, but it cannot be rebuilt without the raw archive."

our_pid() {   # pid listening on PORT, only if it is this app
  local pid; pid=$(lsof -t -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | head -1 || true)
  [ -n "$pid" ] || return 1
  if ps -o command= -p "$pid" | grep -q "airport_app"; then echo "$pid"; return 0; fi
  echo "other:$pid"; return 0
}

PID=$(our_pid || true)
if [ "$ACTION" = stop ] || [ "$ACTION" = restart ]; then
  case "$PID" in
    "") [ "$ACTION" = stop ] && { echo "Not running on port $PORT."; exit 0; } ;;
    other:*) die "port $PORT is used by another program (pid ${PID#other:}); not stopping it." ;;
    *) echo "Stopping the running app (pid $PID)..."; kill "$PID"; for _ in $(seq 1 30); do kill -0 "$PID" 2>/dev/null || break; sleep 0.2; done ;;
  esac
  [ "$ACTION" = stop ] && exit 0
  PID=""
fi
case "$PID" in
  "") ;;
  other:*) die "port $PORT is already used by another program (pid ${PID#other:}). Use --port N." ;;
  *) echo "Already running (pid $PID): http://127.0.0.1:$PORT"
     echo "Use ./scripts/start.sh --restart after changing mode or key."; exit 0 ;;
esac
exec .venv/bin/python -m airport_app --port "$PORT" "${EXTRA[@]+"${EXTRA[@]}"}"

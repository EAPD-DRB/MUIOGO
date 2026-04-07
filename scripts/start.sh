#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# MUIOGO Launcher (macOS / Linux)
#
# Starts the API with the setup venv and opens the browser automatically.
# Usage:
#   ./scripts/start.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -n "${CONDA_DEFAULT_ENV:-}" ]; then
    echo "ERROR: Conda environment '${CONDA_DEFAULT_ENV}' is active."
    echo "Run 'conda deactivate' (repeat until no conda env is active), then launch again."
    exit 1
fi

VENV_DIR="${MUIOGO_VENV_DIR:-$HOME/.venvs/muiogo}"
PYTHON="$VENV_DIR/bin/python"
HOST="127.0.0.1"
PORT="${PORT:-5002}"
URL="http://${HOST}:${PORT}/"
TIMEOUT_SECONDS=30

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: Venv Python not found at: $PYTHON"
    echo "Run setup first:"
    echo "  ./scripts/setup.sh"
    exit 1
fi

echo "Starting MUIOGO on ${URL}"
cd "$PROJECT_ROOT"
"$PYTHON" API/app.py &
SERVER_PID=$!

cleanup() {
    if kill -0 "$SERVER_PID" >/dev/null 2>&1; then
        kill "$SERVER_PID" >/dev/null 2>&1 || true
    fi
}

probe_ready() {
    "$PYTHON" -c '
import sys
import urllib.request

url = sys.argv[1]

try:
    with urllib.request.urlopen(url, timeout=2) as response:
        status = getattr(response, "status", 200)
        raise SystemExit(0 if 200 <= status < 400 else 1)
except Exception:
    raise SystemExit(1)
' "$URL"
}

trap cleanup INT TERM

elapsed=0
while ! probe_ready; do
    if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
        echo "ERROR: MUIOGO server exited before becoming ready."
        exit 1
    fi
    if [ "$elapsed" -ge "$TIMEOUT_SECONDS" ]; then
        echo "ERROR: MUIOGO did not become ready within ${TIMEOUT_SECONDS}s."
        cleanup
        exit 1
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

if [ "$(uname -s)" = "Darwin" ]; then
    open "$URL"
else
    xdg-open "$URL" >/dev/null 2>&1 || true
fi

echo "Browser opened. Press CTRL+C here to stop MUIOGO."
wait "$SERVER_PID"

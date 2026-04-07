#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# MUIOGO Development Environment Setup (macOS / Linux)
#
# Usage:
#   ./scripts/setup.sh                  # full setup (installs demo data by default)
#   ./scripts/setup.sh --no-demo-data   # skip demo data
#   ./scripts/setup.sh --check          # verification only
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -n "${CONDA_DEFAULT_ENV:-}" ]; then
    echo "ERROR: Conda environment '${CONDA_DEFAULT_ENV}' is active."
    echo "Run 'conda deactivate' (repeat until your prompt no longer shows '(base)' or a conda env), then re-run setup."
    exit 1
fi

# Try versioned executables in order (3.12, 3.11, 3.10)
PYTHON=""
for VER in 3.12 3.11 3.10; do
    if command -v "python${VER}" &>/dev/null; then
        PYTHON="python${VER}"
        break
    fi
done

# Fall back to plain python3 if it's in the supported range
if [ -z "$PYTHON" ] && command -v python3 &>/dev/null; then
    if python3 -c "import sys; v=sys.version_info; exit(0 if (3,10)<=v<(3,13) else 1)" 2>/dev/null; then
        PYTHON="python3"
    fi
fi

if [ -z "$PYTHON" ]; then
    echo "ERROR: No supported Python runtime found (requires 3.10, 3.11, or 3.12)."
    if [ "$(uname -s)" = "Darwin" ]; then
        echo "  Homebrew: brew install python@3.12"
        echo "  Python.org macOS installer: https://www.python.org/downloads/macos/"
    else
        echo "  Linux package manager (example): sudo apt install python3.12 python3.12-venv"
        echo "  Python.org downloads: https://www.python.org/downloads/"
    fi
    exit 1
fi

echo "Using Python: $($PYTHON --version) at $(command -v "$PYTHON")"

exec "$PYTHON" "$SCRIPT_DIR/setup_dev.py" "$@"

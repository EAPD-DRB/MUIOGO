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

PYTHON="python3.11"
if ! command -v "$PYTHON" &>/dev/null; then
    echo "ERROR: python3.11 was not found in PATH."
    echo "Install Python 3.11 and re-run setup."
    if [ "$(uname -s)" = "Darwin" ]; then
        echo "  In Terminal (Homebrew): brew install python@3.11"
        echo "  Python.org macOS installer: https://www.python.org/downloads/macos/"
    else
        echo "  Linux package manager (example): sudo apt install python3.11 python3.11-venv"
        echo "  Python.org downloads: https://www.python.org/downloads/"
    fi
    exit 1
fi

is_py311=$("$PYTHON" -c "import sys; print(sys.version_info[:2] == (3, 11))" 2>/dev/null || echo "False")
if [ "$is_py311" != "True" ]; then
    echo "ERROR: Found '$($PYTHON --version)', but MUIOGO setup expects Python 3.11."
    if [ "$(uname -s)" = "Darwin" ]; then
        echo "Install/upgrade Python 3.11 in Terminal:"
        echo "  brew install python@3.11"
        echo "  Python.org macOS installer: https://www.python.org/downloads/macos/"
    else
        echo "Install/upgrade Python 3.11 with your package manager."
        echo "Python.org downloads: https://www.python.org/downloads/"
    fi
    exit 1
fi

echo "Using Python: $($PYTHON --version) at $(command -v "$PYTHON")"

exec "$PYTHON" "$SCRIPT_DIR/setup_dev.py" "$@"

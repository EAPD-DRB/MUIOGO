#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_VENV_PY="${HOME}/.venvs/muiogo/bin/python"
ACTIVE_VENV_PY="${VIRTUAL_ENV:-}/bin/python"
CONFIGURED_VENV_PY="${MUIOGO_VENV_PYTHON:-}"

if [ -n "${CONDA_DEFAULT_ENV:-}" ]; then
    echo "ERROR: Conda environment '${CONDA_DEFAULT_ENV}' is active."
    echo "Run 'conda deactivate' (repeat until your prompt no longer shows a conda env), then re-run smoke."
    exit 1
fi

PYTHON=""

if [ -n "$CONFIGURED_VENV_PY" ]; then
    if [ ! -x "$CONFIGURED_VENV_PY" ]; then
        echo "ERROR: MUIOGO_VENV_PYTHON is set but not executable: $CONFIGURED_VENV_PY"
        exit 1
    fi
    PYTHON="$CONFIGURED_VENV_PY"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$ACTIVE_VENV_PY" ]; then
    PYTHON="$ACTIVE_VENV_PY"
elif [ -x "$DEFAULT_VENV_PY" ]; then
    PYTHON="$DEFAULT_VENV_PY"
fi

if [ -z "$PYTHON" ]; then
    echo "ERROR: MUIOGO is not installed in a supported venv."
    echo "Run ./scripts/setup.sh first."
    echo "If you used a custom venv path, activate it before running smoke or set MUIOGO_VENV_PYTHON to that interpreter."
    exit 1
fi

echo "Using Python: $($PYTHON --version) at $(command -v "$PYTHON" || printf '%s' "$PYTHON")"
exec "$PYTHON" -m unittest discover -s "$PROJECT_ROOT/tests" -p "test_*smoke.py"

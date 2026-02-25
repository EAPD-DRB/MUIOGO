#!/usr/bin/env bash
# ============================================================================
# MUIOGO Setup Script — Cross-platform (macOS / Linux)
# ============================================================================
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# What this script does:
#   1. Creates a Python virtual environment in .venv/
#   2. Installs Python dependencies from requirements.txt
#   3. Installs GLPK and CBC solvers via Homebrew (macOS) or apt (Linux)
#   4. Verifies solver availability
#   5. Creates required data directories
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; }

# ── Detect platform ──────────────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"
echo ""
echo "══════════════════════════════════════════"
echo "  MUIOGO Setup"
echo "  Platform: $OS ($ARCH)"
echo "══════════════════════════════════════════"
echo ""

# ── Check Python ─────────────────────────────────────────────────────────────
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    error "Python 3 is required but not found."
    echo "  macOS:  brew install python3"
    echo "  Linux:  sudo apt install python3 python3-venv"
    exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1)
info "Found $PY_VERSION ($PYTHON)"

# ── Create virtual environment ───────────────────────────────────────────────
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment in $VENV_DIR/"
    $PYTHON -m venv "$VENV_DIR"
else
    info "Virtual environment already exists at $VENV_DIR/"
fi

# Activate it
source "$VENV_DIR/bin/activate"
info "Activated virtual environment"

# ── Install Python dependencies ──────────────────────────────────────────────
if [ -f "requirements.txt" ]; then
    info "Installing Python dependencies..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    info "Python dependencies installed"
else
    warn "requirements.txt not found — skipping pip install"
fi

# ── Install solvers ──────────────────────────────────────────────────────────
install_solvers_macos() {
    if ! command -v brew &>/dev/null; then
        error "Homebrew is required on macOS. Install from https://brew.sh"
        exit 1
    fi

    info "Installing solvers via Homebrew..."

    if ! command -v glpsol &>/dev/null; then
        brew install glpk
        info "GLPK installed"
    else
        info "GLPK already installed ($(glpsol --version 2>&1 | head -1))"
    fi

    if ! command -v cbc &>/dev/null; then
        brew install cbc
        info "CBC installed"
    else
        info "CBC already installed ($(cbc -quit 2>&1 | head -1))"
    fi
}

install_solvers_linux() {
    if command -v apt-get &>/dev/null; then
        info "Installing solvers via apt..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq glpk-utils coinor-cbc
    elif command -v dnf &>/dev/null; then
        info "Installing solvers via dnf..."
        sudo dnf install -y glpk-utils coin-or-Cbc
    else
        warn "Could not detect package manager."
        warn "Please manually install glpk-utils and coinor-cbc."
    fi
}

case "$OS" in
    Darwin) install_solvers_macos ;;
    Linux)  install_solvers_linux ;;
    *)      warn "Unsupported OS ($OS). Please install GLPK and CBC manually." ;;
esac

# ── Verify solvers ───────────────────────────────────────────────────────────
echo ""
SOLVERS_OK=true

if command -v glpsol &>/dev/null; then
    GLPK_LOC=$(which glpsol)
    info "glpsol found at $GLPK_LOC"
else
    error "glpsol NOT found on PATH"
    SOLVERS_OK=false
fi

if command -v cbc &>/dev/null; then
    CBC_LOC=$(which cbc)
    info "cbc found at $CBC_LOC"
else
    error "cbc NOT found on PATH"
    SOLVERS_OK=false
fi

# ── Create required directories ──────────────────────────────────────────────
mkdir -p WebAPP/DataStorage
info "WebAPP/DataStorage/ directory ready"

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════"
if [ "$SOLVERS_OK" = true ]; then
    info "Setup complete! To run MUIOGO:"
else
    warn "Setup mostly complete, but solver(s) missing."
    echo "  You can still start the app but model runs will fail."
    echo "  Install solvers and re-run this script, or set:"
    echo "    export GLPK_PATH=/path/to/glpsol/bin"
    echo "    export CBC_PATH=/path/to/cbc/bin"
    echo ""
    info "To run MUIOGO:"
fi
echo ""
echo "    source .venv/bin/activate"
echo "    cd API"
echo "    python app.py"
echo ""
echo "    Then open http://127.0.0.1:5002/ in your browser"
echo "══════════════════════════════════════════"

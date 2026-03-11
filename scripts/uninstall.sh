#!/usr/bin/env bash
# ============================================================================
# MUIOGO – Uninstall / Reset Script (macOS / Linux)
#
# Reverses the local environment changes created by scripts/setup.sh
# so that running setup again behaves like a first-time install.
#
# Usage:  bash scripts/uninstall.sh
# ============================================================================
set -euo pipefail

# ── Resolve repo root (this script lives in <repo>/scripts/) ────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Pretty logging helpers ──────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'

info()    { printf "${CYAN}[INFO]${NC}    %s\n" "$*"; }
warn()    { printf "${YELLOW}[WARN]${NC}    %s\n" "$*"; }
success() { printf "${GREEN}[OK]${NC}      %s\n" "$*"; }
error()   { printf "${RED}[ERROR]${NC}   %s\n" "$*"; }

# ── Prompt helper (default = No) ────────────────────────────────────────────
confirm() {
    local msg="$1"
    printf "%s (y/N) " "$msg"
    read -r answer
    case "$answer" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

# ============================================================================
#  1. Detect state to remove
# ============================================================================

ITEMS_TO_REMOVE=()

# ── 1a. Virtual environment ─────────────────────────────────────────────────
VENV_DIR="${MUIOGO_VENV_DIR:-$HOME/.venvs/muiogo}"

if [ -d "$VENV_DIR" ]; then
    ITEMS_TO_REMOVE+=("Virtual environment: $VENV_DIR")
fi

# ── 1b. .env entries ────────────────────────────────────────────────────────
ENV_FILE="$REPO_ROOT/.env"
HAS_SETUP_ENTRIES=false

if [ -f "$ENV_FILE" ]; then
    if grep -q '# MUIOGO-setup' "$ENV_FILE" 2>/dev/null; then
        HAS_SETUP_ENTRIES=true
        ITEMS_TO_REMOVE+=(".env setup entries in: $ENV_FILE")
    fi
fi

# ── 1c. Demo data ──────────────────────────────────────────────────────────
DEMO_MARKER="$REPO_ROOT/.muiogo_demo_installed"
DEMO_DIR="$REPO_ROOT/WebAPP/DataStorage/CLEWs Demo"

if [ -f "$DEMO_MARKER" ]; then
    ITEMS_TO_REMOVE+=("Demo data directory: $DEMO_DIR")
    ITEMS_TO_REMOVE+=("Demo marker file:    $DEMO_MARKER")
fi

# ── 1d. Package-manager solvers (advisory only) ────────────────────────────
PKG_SOLVERS=()

detect_pkg_solver() {
    local name="$1"
    # Homebrew
    if command -v brew &>/dev/null && brew list --formula "$name" &>/dev/null; then
        PKG_SOLVERS+=("$name (Homebrew): brew uninstall $name")
    fi
    # apt / dpkg
    if command -v dpkg &>/dev/null && dpkg -s "$name" &>/dev/null 2>&1; then
        PKG_SOLVERS+=("$name (apt): sudo apt remove $name")
    fi
    # dnf / rpm
    if command -v rpm &>/dev/null && rpm -q "$name" &>/dev/null 2>&1; then
        PKG_SOLVERS+=("$name (dnf/rpm): sudo dnf remove $name")
    fi
    # pacman
    if command -v pacman &>/dev/null && pacman -Qi "$name" &>/dev/null 2>&1; then
        PKG_SOLVERS+=("$name (pacman): sudo pacman -R $name")
    fi
}

detect_pkg_solver "glpk"
detect_pkg_solver "cbc"
# Common alternate package names
detect_pkg_solver "coinor-cbc"
detect_pkg_solver "coin-or-cbc"

# ============================================================================
#  2. Show summary
# ============================================================================
echo ""
info "============================================"
info " MUIOGO Uninstall / Reset"
info "============================================"
echo ""

if [ ${#ITEMS_TO_REMOVE[@]} -eq 0 ] && [ ${#PKG_SOLVERS[@]} -eq 0 ]; then
    success "Nothing to uninstall — your environment is already clean."
    exit 0
fi

if [ ${#ITEMS_TO_REMOVE[@]} -gt 0 ]; then
    info "The following items will be removed:"
    echo ""
    for i in "${!ITEMS_TO_REMOVE[@]}"; do
        printf "  %d. %s\n" "$((i + 1))" "${ITEMS_TO_REMOVE[$i]}"
    done
    echo ""
fi

if [ ${#PKG_SOLVERS[@]} -gt 0 ]; then
    warn "The following solvers were installed via a package manager."
    warn "They may be used outside MUIOGO, so they are NOT auto-removed."
    echo ""
    for entry in "${PKG_SOLVERS[@]}"; do
        printf "  • %s\n" "$entry"
    done
    echo ""
fi

# ============================================================================
#  3. Confirm before proceeding
# ============================================================================
if [ ${#ITEMS_TO_REMOVE[@]} -gt 0 ]; then
    if ! confirm "Continue with removal?"; then
        warn "Aborted. No changes were made."
        exit 0
    fi
    echo ""
fi

# ============================================================================
#  4. Execute removal
# ============================================================================

# ── 4a. Remove virtual environment ──────────────────────────────────────────
if [ -d "$VENV_DIR" ]; then
    info "Removing virtual environment: $VENV_DIR"
    rm -rf "$VENV_DIR"
    success "Virtual environment removed."
fi

# ── 4b. Clean .env ─────────────────────────────────────────────────────────
if [ "$HAS_SETUP_ENTRIES" = true ] && [ -f "$ENV_FILE" ]; then
    info "Cleaning setup entries from .env"

    # Remove lines containing the sentinel
    TEMP_ENV="$(mktemp)"
    grep -v '# MUIOGO-setup' "$ENV_FILE" > "$TEMP_ENV" || true

    # If the file is now empty (only whitespace), delete it entirely
    if [ ! -s "$TEMP_ENV" ] || ! grep -q '[^[:space:]]' "$TEMP_ENV" 2>/dev/null; then
        rm -f "$ENV_FILE"
        success ".env file removed (it contained only setup entries)."
    else
        mv "$TEMP_ENV" "$ENV_FILE"
        success "Setup entries removed from .env (user entries preserved)."
    fi
    rm -f "$TEMP_ENV" 2>/dev/null || true
fi

# ── 4c. Remove demo data ───────────────────────────────────────────────────
if [ -f "$DEMO_MARKER" ]; then
    if [ -d "$DEMO_DIR" ]; then
        info "Removing demo data directory: $DEMO_DIR"
        rm -rf "$DEMO_DIR"
        success "Demo data removed."
    else
        warn "Demo marker exists but demo directory not found — skipping data removal."
    fi
    info "Removing demo marker file."
    rm -f "$DEMO_MARKER"
    success "Demo marker removed."
fi

# ── 4d. Offer package-manager solver removal ───────────────────────────────
if [ ${#PKG_SOLVERS[@]} -gt 0 ]; then
    echo ""
    for entry in "${PKG_SOLVERS[@]}"; do
        # entry format: "name (manager): command"
        local_name="${entry%%:*}"
        local_cmd="${entry#*: }"
        if confirm "$local_name appears to have been installed via a package manager. Remove it?"; then
            info "Running: $local_cmd"
            eval "$local_cmd" && success "$local_name removed." || warn "Failed to remove $local_name. You can run manually: $local_cmd"
        else
            info "Skipped $local_name. To remove manually: $local_cmd"
        fi
    done
fi

# ============================================================================
#  5. Done
# ============================================================================
echo ""
success "============================================"
success " MUIOGO uninstall complete."
success " You can now run setup again for a fresh install."
success "============================================"
echo ""

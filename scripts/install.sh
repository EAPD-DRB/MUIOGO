#!/usr/bin/env bash
# MUIOGO installer for macOS / Linux (uv-based).
#
# Takes a user from a clean machine to a running MUIOGO environment:
#   1. Check git is installed
#   2. Install uv (if not present)
#   3. Clone MUIOGO
#   4. uv sync (installs Python + all dependencies)
#   5. Platform setup: solvers, demo data, secret key, verification
#   6. Start the app (optional, user prompted)
#
# Usage:
#   bash install.sh [options]
#
# Options:
#   --dest DIR          Parent directory for the clone (default: current dir)
#   --branch BRANCH     Clone a non-default branch (useful for testing forks/PRs)
#   --repo-url URL      Override the repository URL (default: EAPD-DRB/MUIOGO)
#   --yes               Auto-confirm every prompt (non-interactive)
#   --no-demo-data      Skip demo data installation
#   --skip-uv-install   Skip uv installation; assume uv is already on PATH
#   --log               Write an install log file
#
# One-liner:
#   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/EAPD-DRB/MUIOGO/main/scripts/install.sh)"
#
# Test a fork:
#   bash install.sh --repo-url https://github.com/YOUR_FORK/MUIOGO.git --branch YOUR_BRANCH

set -euo pipefail

# -- Defaults ------------------------------------------------------------------
REPO_URL="https://github.com/EAPD-DRB/MUIOGO.git"
REPO_NAME="MUIOGO"
DEST=""
BRANCH=""
YES=0
NO_DEMO_DATA=0
SKIP_UV_INSTALL=0
NO_LOG=1

SCRIPT_DIR="$(pwd)"
TOTAL_STEPS=5

# -- Argument parsing ----------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dest)          DEST="$2";         shift 2 ;;
        --branch)        BRANCH="$2";       shift 2 ;;
        --repo-url)      REPO_URL="$2";     shift 2 ;;
        --yes|-y)        YES=1;             shift   ;;
        --no-demo-data)  NO_DEMO_DATA=1;    shift   ;;
        --skip-uv-install) SKIP_UV_INSTALL=1; shift ;;
        --log)           NO_LOG=0;          shift   ;;
        -h|--help)
            sed -n '/^# Usage/,/^[^#]/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# -- Colors (detect before any stdout redirect) --------------------------------
if [[ -t 1 ]]; then
    BOLD="\033[1m"; DIM="\033[2m"
    RED="\033[91m"; GREEN="\033[92m"; YELLOW="\033[93m"; RESET="\033[0m"
else
    BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; RESET=""
fi

# -- Interactivity (detect before any stdout redirect) -------------------------
STDIN_IS_TTY=0
[[ -t 0 ]] && STDIN_IS_TTY=1

# -- Logging -------------------------------------------------------------------
TS="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="${SCRIPT_DIR}/.install-${TS}.log"
if [[ $NO_LOG -eq 0 ]]; then
    exec > >(tee -a "$LOG_FILE") 2>&1
fi

# -- Helpers -------------------------------------------------------------------
hr()      { echo "--------------------------------------------------------------"; }
hr_thick(){ echo "=============================================================="; }

pass() { local d="${2:-}"; [[ -n "$d" ]] && echo -e "  ${GREEN}[PASS]${RESET} $1  ${DIM}($d)${RESET}" || echo -e "  ${GREEN}[PASS]${RESET} $1"; }
fail() { local d="${2:-}"; [[ -n "$d" ]] && echo -e "  ${RED}[FAIL]${RESET} $1  ${DIM}($d)${RESET}" || echo -e "  ${RED}[FAIL]${RESET} $1"; }
warn() { local d="${2:-}"; [[ -n "$d" ]] && echo -e "  ${YELLOW}[WARN]${RESET} $1  ${DIM}($d)${RESET}" || echo -e "  ${YELLOW}[WARN]${RESET} $1"; }
skip() { local d="${2:-}"; [[ -n "$d" ]] && echo -e "  ${YELLOW}[SKIP]${RESET} $1  ${DIM}($d)${RESET}" || echo -e "  ${YELLOW}[SKIP]${RESET} $1"; }
cmd()  { echo -e "  ${DIM}\$ $1${RESET}"; }

step_banner() {
    echo ""
    hr
    echo -e "  ${BOLD}Step $1 of ${TOTAL_STEPS}: $2${RESET}"
    hr
}

# -- Result tracking -----------------------------------------------------------
STEP_NAMES=()
STEP_STATES=()
STEP_DETAILS=()

record_step() {
    STEP_NAMES+=("$1")
    STEP_STATES+=("$2")
    STEP_DETAILS+=("${3:-}")
}

# -- Interactive helpers -------------------------------------------------------
is_interactive() { [[ $STDIN_IS_TTY -eq 1 ]]; }

prompt_yn() {
    local prompt="$1" default="${2:-y}"
    local opts="[Y/N]"

    if [[ $YES -eq 1 ]]; then
        echo -e "$prompt $opts ${DIM}(auto: yes)${RESET}"
        return 0
    fi
    if ! is_interactive; then
        echo -e "${RED}ERROR:${RESET} non-interactive session and --yes not given." >&2
        return 1
    fi
    while true; do
        read -rp "$prompt $opts " ans
        [[ -z "$ans" ]] && ans="$default"
        case "$(echo "$ans" | tr '[:upper:]' '[:lower:]')" in
            y|yes)      return 0 ;;
            n|no)       return 1 ;;
            *)          echo "  Please answer Y or N." ;;
        esac
    done
}

# -- Pre-flight ----------------------------------------------------------------
if [[ -n "${CONDA_DEFAULT_ENV:-}" ]]; then
    echo -e "${RED}ERROR:${RESET} conda env '${CONDA_DEFAULT_ENV}' is active. Run 'conda deactivate' first."
    exit 1
fi
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    echo -e "${RED}ERROR:${RESET} virtualenv '${VIRTUAL_ENV}' is active. Run 'deactivate' first."
    exit 1
fi

if ! command -v curl &>/dev/null; then
    echo -e "${RED}ERROR:${RESET} 'curl' is required to install uv. Please install curl and re-run."
    exit 1
fi

# -- Detect existing uv --------------------------------------------------------
UV_BIN=""
detect_uv() {
    if command -v uv &>/dev/null; then
        UV_BIN="$(command -v uv)"
        return 0
    fi
    local candidates=(
        "$HOME/.local/bin/uv"
        "$HOME/.cargo/bin/uv"
    )
    for c in "${candidates[@]}"; do
        if [[ -x "$c" ]]; then
            UV_BIN="$c"
            return 0
        fi
    done
    return 1
}
detect_uv || true
UV_PRESENT=$( [[ -n "$UV_BIN" ]] && echo 1 || echo 0 )

# -- Pick destination ----------------------------------------------------------
if [[ -z "$DEST" ]]; then
    if ! is_interactive; then
        DEST="."
    else
        echo ""
        echo "  Where would you like to install MUIOGO?"
        echo "  Enter the PARENT directory; MUIOGO will be cloned as a subfolder inside."
        echo "  Default: current directory ($(pwd))"
        read -rp "  Parent directory [.]: " entered
        DEST="${entered:-.}"
    fi
fi

# Expand ~ manually (works in bash without eval)
if [[ "$DEST" == "~"* ]]; then
    DEST="${HOME}${DEST:1}"
fi

if [[ ! -d "$DEST" ]]; then
    echo -e "${RED}ERROR:${RESET} parent directory does not exist: $DEST"
    echo "Create it first or pick a different --dest."
    exit 1
fi

PARENT_ABS="$(cd "$DEST" && pwd)"
DEST_ABS="${PARENT_ABS}/${REPO_NAME}"

# -- Detect OS -----------------------------------------------------------------
OS_LABEL="Linux"
if [[ "$(uname)" == "Darwin" ]]; then
    OS_LABEL="macOS $(sw_vers -productVersion 2>/dev/null || true)"
fi

# -- Banner --------------------------------------------------------------------
echo ""
hr_thick
echo -e "  ${BOLD}MUIOGO Installer (uv-based)${RESET}"
hr_thick
echo    "  Platform    : ${OS_LABEL}"
echo    "  Destination : ${DEST_ABS}"
[[ -n "$BRANCH" ]] && echo "  Branch      : ${BRANCH}"
if [[ $UV_PRESENT -eq 1 ]]; then
    echo -e "  uv          : ${UV_BIN} ${GREEN}detected${RESET}"
else
    echo -e "  uv          : ${YELLOW}will install${RESET} (~5MB, official installer)"
fi
[[ $NO_LOG -eq 0 ]] && echo "  Log file    : ${LOG_FILE}"
echo ""
echo -e "  ${BOLD}Plan (${TOTAL_STEPS} steps):${RESET}"
echo    "    1. Check git"
if [[ $UV_PRESENT -eq 1 || $SKIP_UV_INSTALL -eq 1 ]]; then
    echo -e "    2. Install uv                      ${DIM}skipped (already present)${RESET}"
else
    echo -e "    2. Install uv                      ${DIM}~5MB, seconds${RESET}"
fi
echo -e "    3. Clone MUIOGO                    ${DIM}depends on network${RESET}"
echo -e "    4. uv sync (Python + deps)         ${DIM}~30s${RESET}"
echo    "    5. Platform setup (solvers, demo data, secret key, verification)"
echo ""

if ! prompt_yn "Proceed with installation?" y; then
    echo -e "${YELLOW}Aborted by user.${RESET}"
    exit 0
fi

START_TIME="$(date +%s)"

# -- Step 1: Check git ---------------------------------------------------------
step_banner 1 "Check git"
# macOS ships a /usr/bin/git stub that exists even when the Command Line Tools
# (which provide the real git) are not installed. `command -v git` would then
# report git as present, and the clone would later trigger a GUI prompt or fail.
# On macOS we confirm with `xcode-select -p`, which is the reliable check.
git_ok=0
if [[ "$(uname)" == "Darwin" ]]; then
    if xcode-select -p &>/dev/null && command -v git &>/dev/null; then
        git_ok=1
    fi
elif command -v git &>/dev/null; then
    git_ok=1
fi
if [[ $git_ok -eq 0 ]]; then
    fail "git is not installed or not on PATH"
    echo ""
    echo "  Install git, then re-run this installer:"
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "    xcode-select --install"
        echo "    # or: brew install git"
    else
        echo "    sudo apt install git   # Debian/Ubuntu"
        echo "    sudo dnf install git   # Fedora/RHEL"
    fi
    record_step "git" "FAIL" "not installed"
    exit 1
fi
GIT_BIN="$(command -v git)"
GIT_VER="$(git --version 2>/dev/null || true)"
pass "git" "$GIT_VER"
record_step "git" "PASS" "$GIT_VER"

# -- Step 2: Install uv --------------------------------------------------------
step_banner 2 "Install uv"
if [[ $UV_PRESENT -eq 1 ]]; then
    UV_VER="$("$UV_BIN" --version 2>/dev/null | head -1 || true)"
    pass "uv already present" "${UV_BIN} (${UV_VER})"
    record_step "uv" "SKIP" "already present"
elif [[ $SKIP_UV_INSTALL -eq 1 ]]; then
    fail "--skip-uv-install given but uv not found"
    record_step "uv" "FAIL" "no uv and --skip-uv-install"
    exit 1
else
    echo "  Installing uv via the official installer (no sudo required)..."
    cmd "curl -LsSf https://astral.sh/uv/install.sh | sh"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Reload PATH so uv is findable without a new shell
    export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
    if ! detect_uv; then
        fail "uv installed but binary not found; open a new terminal and re-run"
        record_step "uv" "FAIL" "binary not found post-install"
        exit 1
    fi
    UV_VER="$("$UV_BIN" --version 2>/dev/null | head -1 || true)"
    pass "uv installed" "${UV_BIN} (${UV_VER})"
    record_step "uv" "PASS" "$UV_BIN"
fi

# -- Step 3: Clone MUIOGO ------------------------------------------------------
step_banner 3 "Clone MUIOGO"

normalize_url() { echo "$1" | sed 's/\.git\/*$//' | tr '[:upper:]' '[:lower:]'; }

DEST_HAS_REPO=0
if [[ -d "$DEST_ABS" ]]; then
    if [[ -d "${DEST_ABS}/.git" ]]; then
        EXISTING_URL="$("$GIT_BIN" -C "$DEST_ABS" config --get remote.origin.url 2>/dev/null || true)"
        if [[ "$(normalize_url "$EXISTING_URL")" == "$(normalize_url "$REPO_URL")" ]]; then
            DEST_HAS_REPO=1
        else
            fail "Destination exists but points to a different remote" "$EXISTING_URL"
            echo "  Remove ${DEST_ABS} or pick a different --dest."
            record_step "Clone" "FAIL" "wrong remote"
            exit 1
        fi
    else
        if [[ -n "$(ls -A "$DEST_ABS" 2>/dev/null)" ]]; then
            fail "Destination exists and is not empty" "$DEST_ABS"
            echo "  Remove ${DEST_ABS} or pick a different --dest."
            record_step "Clone" "FAIL" "destination not empty"
            exit 1
        fi
    fi
fi

if [[ $DEST_HAS_REPO -eq 1 ]]; then
    CURRENT_BRANCH="$("$GIT_BIN" -C "$DEST_ABS" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
    echo "  Existing MUIOGO clone found at ${DEST_ABS} (branch: ${CURRENT_BRANCH})."

    # -- Version check against what `git pull` would bring in ------------------
    # The clone's own tracked branch (the branch and repository it was installed
    # from); EAPD-DRB/MUIOGO:main only when it tracks nothing, e.g. a detached HEAD.
    LOCAL_SHA="$("$GIT_BIN" -C "$DEST_ABS" rev-parse --short HEAD 2>/dev/null || echo '?')"
    UPSTREAM="$("$GIT_BIN" -C "$DEST_ABS" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
    if [[ -n "$UPSTREAM" ]]; then
        "$GIT_BIN" -C "$DEST_ABS" fetch --quiet 2>/dev/null || true
        COMPARE_REF="@{u}"
        LATEST_LABEL="${UPSTREAM}"
    else
        "$GIT_BIN" -C "$DEST_ABS" fetch https://github.com/EAPD-DRB/MUIOGO.git main --quiet 2>/dev/null || true
        COMPARE_REF="FETCH_HEAD"
        LATEST_LABEL="EAPD-DRB/MUIOGO:main"
    fi
    REMOTE_SHA="$("$GIT_BIN" -C "$DEST_ABS" rev-parse --short "$COMPARE_REF" 2>/dev/null || echo '?')"
    BEHIND="$("$GIT_BIN" -C "$DEST_ABS" rev-list --count "HEAD..${COMPARE_REF}" 2>/dev/null || echo '?')"
    AHEAD="$("$GIT_BIN" -C "$DEST_ABS" rev-list --count "${COMPARE_REF}..HEAD" 2>/dev/null || echo '?')"

    echo "  Local:   ${LOCAL_SHA}  (${CURRENT_BRANCH})"
    echo "  Latest:  ${REMOTE_SHA}  (${LATEST_LABEL})"
    echo ""

    if [[ "$BEHIND" == "?" ]]; then
        warn "Could not check for updates — continuing with current version"
        record_step "Clone" "WARN" "could not reach remote"
    elif [[ "$BEHIND" == "0" ]]; then
        pass "Up to date  --  0 behind, ${AHEAD} ahead"
        record_step "Clone" "PASS" "up to date (${CURRENT_BRANCH})"
    else
        warn "${BEHIND} behind, ${AHEAD} ahead  --  update now?"
        if prompt_yn "Update now?" y; then
            PULL_ARGS=(pull --ff-only)
            [[ "$COMPARE_REF" == "FETCH_HEAD" ]] && PULL_ARGS+=(https://github.com/EAPD-DRB/MUIOGO.git main)
            cmd "git -C ${DEST_ABS} ${PULL_ARGS[*]}"
            if "$GIT_BIN" -C "$DEST_ABS" "${PULL_ARGS[@]}"; then
                pass "Updated to $("$GIT_BIN" -C "$DEST_ABS" rev-parse --short HEAD)"
                record_step "Clone" "PASS" "updated (was ${BEHIND} behind)"
            else
                warn "git pull failed; continuing with existing state"
                record_step "Clone" "WARN" "pull failed; existing state used"
            fi
        else
            skip "Update skipped" "continuing with ${LOCAL_SHA}"
            record_step "Clone" "SKIP" "user declined update"
        fi
    fi
else
    CLONE_ARGS=("clone")
    [[ -n "$BRANCH" ]] && CLONE_ARGS+=("--branch" "$BRANCH")
    CLONE_ARGS+=("$REPO_URL" "$DEST_ABS")

    echo "  Cloning MUIOGO into ${DEST_ABS}..."
    cmd "git ${CLONE_ARGS[*]}"
    "$GIT_BIN" "${CLONE_ARGS[@]}"

    CURRENT_BRANCH="$("$GIT_BIN" -C "$DEST_ABS" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
    pass "Cloned MUIOGO" "${DEST_ABS} (branch: ${CURRENT_BRANCH})"
    record_step "Clone" "PASS" "$CURRENT_BRANCH"
fi

# -- Step 4: uv sync -----------------------------------------------------------
step_banner 4 "Install dependencies (uv sync)"
echo "  Installing Python + all dependencies into ${DEST_ABS}/.venv"
cmd "uv sync"
pushd "$DEST_ABS" >/dev/null
"$UV_BIN" sync
popd >/dev/null
pass "Dependencies installed" ".venv"
record_step "uv sync" "PASS" ".venv"

# -- Step 5: Platform setup ----------------------------------------------------
step_banner 5 "Platform setup (solvers, demo data, secret key, verification)"
if [[ -x "${DEST_ABS}/.venv/bin/python" ]]; then
    VENV_PYTHON="${DEST_ABS}/.venv/bin/python"
elif [[ -x "${DEST_ABS}/.venv/Scripts/python.exe" ]]; then
    VENV_PYTHON="${DEST_ABS}/.venv/Scripts/python.exe"
else
    fail "venv Python not found" "${DEST_ABS}/.venv"
    record_step "Platform setup" "FAIL" "no venv python"
    exit 1
fi

SETUP_ARGS=("scripts/setup_dev.py" "--platform-only" "--venv-dir" ".venv")
[[ $NO_DEMO_DATA -eq 1 ]] && SETUP_ARGS+=("--no-demo-data")
[[ $YES -eq 1 ]] && SETUP_ARGS+=("--yes")

cmd "python ${SETUP_ARGS[*]}"
pushd "$DEST_ABS" >/dev/null
# Capture the exit code instead of letting `set -e` abort here, so a failure is
# reported in the summary below (matching install.ps1) rather than aborting
# before the summary prints.
SETUP_EXIT=0
"$VENV_PYTHON" "${SETUP_ARGS[@]}" || SETUP_EXIT=$?
popd >/dev/null

if [[ $SETUP_EXIT -ne 0 ]]; then
    fail "Platform setup reported failures -- review output above"
    record_step "Platform setup" "FAIL" "setup_dev.py exited ${SETUP_EXIT}"
else
    record_step "Platform setup" "PASS" "solvers, demo data, secret key, verification"
fi

# -- Summary -------------------------------------------------------------------
END_TIME="$(date +%s)"
ELAPSED=$(( END_TIME - START_TIME ))
ELAPSED_MIN=$(( ELAPSED / 60 ))
ELAPSED_SEC=$(( ELAPSED % 60 ))

echo ""
hr_thick
echo -e "  ${BOLD}Installation Summary${RESET}"
hr_thick

ALL_OK=1
for i in "${!STEP_NAMES[@]}"; do
    case "${STEP_STATES[$i]}" in
        PASS) pass  "${STEP_NAMES[$i]}" "${STEP_DETAILS[$i]}" ;;
        SKIP) skip  "${STEP_NAMES[$i]}" "${STEP_DETAILS[$i]}" ;;
        WARN) warn  "${STEP_NAMES[$i]}" "${STEP_DETAILS[$i]}" ;;
        FAIL) fail  "${STEP_NAMES[$i]}" "${STEP_DETAILS[$i]}"; ALL_OK=0 ;;
        *)    warn  "${STEP_NAMES[$i]}" "unknown state" ;;
    esac
done

echo ""
echo    "  Elapsed  : ${ELAPSED_MIN}m ${ELAPSED_SEC}s"
echo    "  Location : ${DEST_ABS}"
[[ $NO_LOG -eq 0 ]] && echo "  Log      : ${LOG_FILE}"
echo ""

if [[ $ALL_OK -eq 1 ]]; then
    echo -e "  ${GREEN}${BOLD}MUIOGO is installed and ready.${RESET}"
    echo ""
    if prompt_yn "Start MUIOGO now?" y; then
        PORT="${PORT:-5002}"
        URL="http://127.0.0.1:${PORT}/"
        echo "  Opening browser at ${URL}"
        echo "  Press Ctrl+C to stop the app."
        if command -v cmd.exe &>/dev/null; then
            cmd.exe /c start "" "$URL"
        elif command -v open &>/dev/null; then
            open "$URL"
        elif command -v xdg-open &>/dev/null; then
            xdg-open "$URL" &>/dev/null &
        fi
        pushd "$DEST_ABS" >/dev/null
        "$VENV_PYTHON" API/app.py
        popd >/dev/null
    fi

    exit 0
else
    echo -e "  ${RED}${BOLD}One or more steps failed -- review the output above.${RESET}"
    [[ $NO_LOG -eq 0 ]] && echo "  Full log: ${LOG_FILE}"
    exit 1
fi

#!/usr/bin/env python3
"""
MUIOGO Cross-Platform Development Setup Script

Sets up a complete development environment for MUIOGO:
  1. Creates or validates a Python virtual environment (venv)
  2. Installs Python dependencies from requirements.txt
  3. Installs solver dependencies (GLPK, CBC) via OS package managers
  4. Installs demo data from local archive (default; can be skipped)
  5. Runs post-setup verification checks

Usage:
    python scripts/setup_dev.py          # full setup
    python scripts/setup_dev.py --no-demo-data
    python scripts/setup_dev.py --check  # verification only (skip install)
    python scripts/setup_dev.py --venv-dir ~/my-envs/muiogo
    python scripts/setup_dev.py --force-demo-data --yes

Supports: macOS, Linux (apt/dnf/pacman), Windows

Python support: >=3.10 and <3.13 (recommended: 3.11)

Default venv location: ~/.venvs/muiogo (outside repo)
"""

import argparse
import hashlib
import json
import os
import platform
import secrets
import shutil
import subprocess
import sys
import textwrap
import venv
import zipfile
from pathlib import Path
import urllib.request
import tempfile

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = (Path.home() / ".venvs" / "muiogo").resolve()
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
ENV_FILE = PROJECT_ROOT / ".env"
SYSTEM = platform.system()  # 'Darwin', 'Linux', 'Windows'
MIN_PYTHON = (3, 10)
MAX_PYTHON = (3, 13)  # exclusive
DATA_STORAGE_DIR = PROJECT_ROOT / "WebAPP" / "DataStorage"
DEMO_DATA_ARCHIVE = PROJECT_ROOT / "assets" / "demo-data" / "CLEWs.Demo.zip"
DEMO_DATA_ARCHIVE_SHA256 = "facf4bda703f67b3c8b8697fea19d7d49be72bc2029fc05a68c61fd12ba7edde"
DEMO_DATA_REQUIRED_DIRS = [DATA_STORAGE_DIR / "CLEWs Demo"]
DEMO_DATA_MARKER = DATA_STORAGE_DIR / ".demo_data_installed.json"
_CBC_WINDOWS_VERSION = "2.10.12"
_CBC_WINDOWS_URL = (
    f"https://github.com/coin-or/Cbc/releases/download/releases%2F{_CBC_WINDOWS_VERSION}/"
    f"Cbc-releases.{_CBC_WINDOWS_VERSION}-w64-msvc17-md.zip"
)
_CBC_WINDOWS_SHA256 = "6acf3e300945b815b2cbb2b16d3732eeeec968a4962249167827062bbf83b3a3"

# Core packages that must be importable after setup
REQUIRED_IMPORTS = [
    "flask",
    "flask_cors",
    "pandas",
    "numpy",
    "openpyxl",
    "waitress",
    "dotenv",
]

# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# Disable colours when not in a real terminal (CI, pipes, Windows without ANSI)
if not sys.stdout.isatty():
    BOLD = GREEN = YELLOW = RED = RESET = ""


def _print_header(msg: str) -> None:
    print(f"\n{BOLD}{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}{RESET}\n")


def _print_pass(label: str, detail: str = "") -> None:
    suffix = f"  ({detail})" if detail else ""
    print(f"  {GREEN}[PASS]{RESET} {label}{suffix}")


def _print_fail(label: str, detail: str = "") -> None:
    suffix = f"  ({detail})" if detail else ""
    print(f"  {RED}[FAIL]{RESET} {label}{suffix}")


def _print_warn(label: str, detail: str = "") -> None:
    suffix = f"  ({detail})" if detail else ""
    print(f"  {YELLOW}[WARN]{RESET} {label}{suffix}")


def _print_skipped(label: str, detail: str = "") -> None:
    suffix = f"  ({detail})" if detail else ""
    print(f"  {YELLOW}[SKIPPED]{RESET} {label}{suffix}")


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command, printing it first, and return the result."""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, **kwargs)


def _which(name: str) -> str | None:
    """Cross-platform shutil.which wrapper."""
    return shutil.which(name)


def _python_supported(version: tuple[int, int]) -> bool:
    return MIN_PYTHON <= version < MAX_PYTHON


def _requirements_hash_file() -> Path:
    return VENV_DIR / ".requirements.sha256"


def _ensure_secret_key_in_env() -> bool:
    """Create a persistent MUIOGO secret key in .env if one does not exist."""
    _print_header("Step 2a: App secret key")

    lines: list[str] = []
    if ENV_FILE.exists():
        try:
            lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
        except Exception as exc:
            _print_fail("Could not read .env file", str(exc))
            return False

    key_line_index: int | None = None
    for i, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line.startswith("MUIOGO_SECRET_KEY="):
            value = line.split("=", 1)[1].strip()
            if value:
                _print_pass("MUIOGO_SECRET_KEY already configured", str(ENV_FILE))
                return True
            key_line_index = i  # empty value — will replace below

    existing_key = os.environ.get("MUIOGO_SECRET_KEY", "").strip()
    new_key = existing_key or secrets.token_hex(32)
    new_entry = f"MUIOGO_SECRET_KEY={new_key}"

    if key_line_index is not None:
        lines[key_line_index] = new_entry
    else:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(new_entry)

    try:
        ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as exc:
        _print_fail("Could not write .env file", str(exc))
        return False

    if SYSTEM != "Windows":
        try:
            os.chmod(ENV_FILE, 0o600)
        except OSError:
            pass  # best-effort

    if existing_key:
        _print_pass("Persisted existing MUIOGO_SECRET_KEY to .env", str(ENV_FILE))
    else:
        _print_pass("Created persistent MUIOGO_SECRET_KEY", str(ENV_FILE))
    return True


def _resolve_venv_dir(venv_dir_arg: str | None) -> Path:
    if venv_dir_arg:
        return Path(venv_dir_arg).expanduser().resolve()

    env_override = os.environ.get("MUIOGO_VENV_DIR", "").strip()
    if env_override:
        return Path(env_override).expanduser().resolve()

    return (Path.home() / ".venvs" / "muiogo").resolve()


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _read_requirements_hash() -> str | None:
    hash_file = _requirements_hash_file()
    if not hash_file.exists():
        return None
    try:
        return hash_file.read_text(encoding="utf-8").strip() or None
    except Exception:
        return None


def _read_demo_marker() -> dict | None:
    if not DEMO_DATA_MARKER.exists():
        return None
    try:
        return json.loads(DEMO_DATA_MARKER.read_text(encoding="utf-8"))
    except Exception:
        return None


def demo_data_present() -> bool:
    """Fast presence check only: marker + required directory existence."""
    if _read_demo_marker() is None:
        return False
    return all(path.exists() and path.is_dir() for path in DEMO_DATA_REQUIRED_DIRS)


def _confirm_force_demo_data(force: bool, yes: bool) -> bool:
    if not force:
        return True
    if yes:
        return True
    if not sys.stdin.isatty():
        _print_fail(
            "Refusing forced demo-data reinstall in non-interactive mode",
            "Re-run with --force-demo-data --yes to confirm.",
        )
        return False
    print()
    print("  [WARN] --force-demo-data will remove existing demo-data folders before reinstall.")
    answer = input("  Type REINSTALL to continue: ").strip()
    if answer != "REINSTALL":
        _print_warn("Demo-data reinstall cancelled by user")
        return False
    return True


def _safe_extract_zip(zf: zipfile.ZipFile, target_dir: Path) -> None:
    target_root = target_dir.resolve()
    for member in zf.infolist():
        member_path = target_root / member.filename
        resolved = member_path.resolve()
        if not str(resolved).startswith(str(target_root)):
            raise RuntimeError(f"Unsafe zip entry path: {member.filename}")
    zf.extractall(target_root)


def _demo_data_paths_to_remove() -> list[Path]:
    marker = _read_demo_marker() or {}
    paths: list[Path] = []
    marker_paths = marker.get("installed_paths", [])
    for rel in marker_paths:
        p = (PROJECT_ROOT / rel).resolve()
        if str(p).startswith(str(DATA_STORAGE_DIR.resolve())):
            paths.append(p)
    for p in DEMO_DATA_REQUIRED_DIRS:
        if p not in paths:
            paths.append(p)
    return paths


def install_demo_data(force: bool, yes: bool) -> bool:
    _print_header("Step 4: Demo data")

    if not DEMO_DATA_ARCHIVE.exists():
        _print_fail("Demo-data archive not found", str(DEMO_DATA_ARCHIVE))
        return False

    if not _confirm_force_demo_data(force=force, yes=yes):
        return False

    if demo_data_present() and not force:
        _print_pass("Demo data already installed", str(DEMO_DATA_REQUIRED_DIRS[0]))
        return True

    if force:
        targets = [p for p in _demo_data_paths_to_remove() if p.exists()]
        if targets:
            print("  Removing existing demo-data targets:")
            for target in targets:
                print(f"    - {target}")
        for target in targets:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        if DEMO_DATA_MARKER.exists():
            DEMO_DATA_MARKER.unlink()

    print("  Verifying demo-data archive checksum ...")
    current_sha = _sha256(DEMO_DATA_ARCHIVE)
    if current_sha != DEMO_DATA_ARCHIVE_SHA256:
        _print_fail(
            "Demo-data checksum mismatch",
            f"expected {DEMO_DATA_ARCHIVE_SHA256}, got {current_sha}",
        )
        return False
    _print_pass("Demo-data archive checksum", current_sha)

    print("  Extracting demo data archive ...")
    try:
        with zipfile.ZipFile(DEMO_DATA_ARCHIVE, "r") as zf:
            _safe_extract_zip(zf, PROJECT_ROOT)
    except Exception as exc:
        _print_fail("Failed to extract demo-data archive", str(exc))
        return False

    if not all(path.exists() and path.is_dir() for path in DEMO_DATA_REQUIRED_DIRS):
        missing = [str(path) for path in DEMO_DATA_REQUIRED_DIRS if not path.exists()]
        _print_fail("Demo data extraction incomplete", ", ".join(missing))
        return False

    marker_data = {
        "archive": str(DEMO_DATA_ARCHIVE.relative_to(PROJECT_ROOT)),
        "archive_sha256": DEMO_DATA_ARCHIVE_SHA256,
        "installed_paths": [str(path.relative_to(PROJECT_ROOT)) for path in DEMO_DATA_REQUIRED_DIRS],
    }
    DEMO_DATA_MARKER.write_text(json.dumps(marker_data, indent=2), encoding="utf-8")
    _print_pass("Demo data installed", str(DEMO_DATA_REQUIRED_DIRS[0]))
    return True


def check_demo_data() -> bool:
    _print_header("Step 4: Demo data (check)")
    if demo_data_present():
        _print_pass("Demo data present", str(DEMO_DATA_REQUIRED_DIRS[0]))
        return True
    _print_fail(
        "Demo data not found",
        "Run setup (default installs demo data), or use --force-demo-data --yes to reinstall.",
    )
    return False


def _is_admin() -> bool:
    if SYSTEM != "Windows":
        return True
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _windows_add_to_user_path(bin_dir: Path) -> None:
    """Mutate current-session PATH, persist to HKCU registry, and broadcast change."""
    # Mutate PATH in current session so verification passes immediately
    current = os.environ.get("PATH", "")
    entries = current.split(os.pathsep)
    bin_str = str(bin_dir)

    entries_lower = [e.lower() for e in entries]
    if bin_str.lower() not in entries_lower:
        os.environ["PATH"] = bin_str + os.pathsep + current

    # Persist to user PATH via registry
    try:
        import winreg
        import ctypes
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            "Environment",
            0,
            winreg.KEY_READ | winreg.KEY_SET_VALUE,
        ) as key:
            try:
                cur, _ = winreg.QueryValueEx(key, "PATH")
            except FileNotFoundError:
                cur = ""

            existing_paths_lower = [p.strip().lower() for p in cur.split(";") if p.strip()]

            if bin_str.lower() not in existing_paths_lower:
                new_path = f"{bin_str};{cur}" if cur else bin_str
                winreg.SetValueEx(
                    key,
                    "PATH",
                    0,
                    winreg.REG_EXPAND_SZ,
                    new_path,
                )
        # Broadcast PATH change
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF, 0x001A, 0, "Environment", 0, 1000, None
        )
    except Exception as exc:
        _print_warn(
            "Could not persist CBC to user PATH; add manually", f"{bin_dir} ({exc})"
        )
    print("  Note: open a NEW terminal for this PATH change to take effect.")


def _install_cbc_windows_manual() -> bool:
    """
    Download the official CBC Windows binary, verify its SHA-256 checksum,
    extract to %LOCALAPPDATA%\\cbc, and add the bin directory to the user PATH.
    """
    install_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "cbc"
    tmp_path: Path | None = None

    try:
        _print_warn("Attempting manual CBC installation...")
        install_dir.mkdir(parents=True, exist_ok=True)

        fd, tmp_str = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        tmp_path = Path(tmp_str)

        print(f"  Downloading CBC {_CBC_WINDOWS_VERSION} from GitHub ...")
        req = urllib.request.Request(_CBC_WINDOWS_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as response:
            with open(tmp_path, "wb") as f:
                f.write(response.read())

        print("  Verifying CBC archive checksum ...")
        actual_sha = _sha256(tmp_path)
        if actual_sha.lower() != _CBC_WINDOWS_SHA256.lower():
            _print_fail(
                "CBC download checksum mismatch — aborting installation",
                f"expected {_CBC_WINDOWS_SHA256}, got {actual_sha}",
            )
            return False
        _print_pass("CBC archive checksum verified", actual_sha)

        print("  Extracting CBC ...")
        with zipfile.ZipFile(tmp_path, "r") as zf:
            _safe_extract_zip(zf, install_dir)

        bin_dir = install_dir / f"Cbc-releases.{_CBC_WINDOWS_VERSION}-w64-msvc17-md" / "bin"
        if not bin_dir.exists():
            # Fallback: search extracted tree for cbc.exe
            matches = list(install_dir.rglob("cbc.exe"))
            if not matches:
                _print_fail("cbc.exe not found in extracted archive")
                return False
            bin_dir = matches[0].parent

        _windows_add_to_user_path(bin_dir)
        _print_pass("CBC installed", str(bin_dir))
        return True

    except Exception as exc:
        _print_fail("CBC manual install failed", str(exc))
        return False

    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


# ──────────────────────────────────────────────────────────────────────────────
# Step 1 – Python virtual environment
# ──────────────────────────────────────────────────────────────────────────────

def _venv_python() -> Path:
    """Return the path to the venv Python interpreter."""
    if SYSTEM == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def setup_venv() -> bool:
    """Create a Python venv if one does not already exist."""
    _print_header("Step 1: Python virtual environment")

    try:
        VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        _print_fail("Could not create parent directory for venv", str(exc))
        return False

    if _venv_python().exists():
        print(f"  Virtual environment already exists at {VENV_DIR}")
        return True

    print(f"  Creating virtual environment at {VENV_DIR} ...")
    try:
        venv.create(str(VENV_DIR), with_pip=True)
        print(f"  {GREEN}Virtual environment created.{RESET}")
        return True
    except Exception as exc:
        _print_fail("Could not create venv", str(exc))
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Step 2 – Python dependencies
# ──────────────────────────────────────────────────────────────────────────────

def install_python_deps() -> bool:
    """Install Python dependencies from requirements.txt into the venv."""
    _print_header("Step 2: Python dependencies")

    if not REQUIREMENTS.exists():
        _print_fail("requirements.txt not found", str(REQUIREMENTS))
        return False

    python = str(_venv_python())
    current_req_hash = _sha256(REQUIREMENTS)
    cached_req_hash = _read_requirements_hash()

    if cached_req_hash == current_req_hash:
        # Guard against stale cache file if environment is partially broken.
        sanity = subprocess.run(
            [python, "-c", "import flask"],
            capture_output=True,
            text=True,
        )
        if sanity.returncode == 0:
            _print_pass("Python dependencies already up to date", "requirements hash unchanged")
            return True
        _print_warn(
            "Dependency cache invalid",
            "requirements unchanged but import sanity check failed; reinstalling",
        )

    # Upgrade pip first
    _run([python, "-m", "pip", "install", "--upgrade", "pip"],
         capture_output=True)

    result = _run(
        [python, "-m", "pip", "install", "-r", str(REQUIREMENTS)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        _print_fail("pip install failed")
        print(result.stderr[-2000:] if result.stderr else "(no stderr)")
        return False

    try:
        _requirements_hash_file().write_text(current_req_hash + "\n", encoding="utf-8")
    except Exception as exc:
        _print_warn("Could not write requirements cache file", str(exc))

    print(f"  {GREEN}Python dependencies installed.{RESET}")
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Step 3 – Solver dependencies (GLPK & CBC)
# ──────────────────────────────────────────────────────────────────────────────

def _detect_linux_pkg_manager() -> tuple[str, list[str], list[str]] | None:
    """
    Detect the Linux package manager and return
    (manager_name, glpk_install_cmd, cbc_install_cmd) or None.
    """
    if _which("apt-get"):
        return (
            "apt",
            ["sudo", "apt-get", "install", "-y", "glpk-utils"],
            ["sudo", "apt-get", "install", "-y", "coinor-cbc"],
        )
    if _which("dnf"):
        return (
            "dnf",
            ["sudo", "dnf", "install", "-y", "glpk-utils"],
            ["sudo", "dnf", "install", "-y", "coin-or-Cbc"],
        )
    if _which("pacman"):
        return (
            "pacman",
            ["sudo", "pacman", "-S", "--noconfirm", "glpk"],
            ["sudo", "pacman", "-S", "--noconfirm", "coin-or-cbc"],
        )
    return None


def install_solvers() -> bool:
    """Install GLPK and CBC solver binaries using OS package managers."""
    _print_header("Step 3: Solver dependencies (GLPK & CBC)")

    glpk_ok = _which("glpsol") is not None
    cbc_ok = _which("cbc") is not None

    if glpk_ok and cbc_ok:
        _print_pass("  Both solvers are already available in PATH — skipping.")
        return True

    success = True

    # ── macOS (Homebrew) ──────────────────────────────────────────────────
    if SYSTEM == "Darwin":
        if not _which("brew"):
            _print_fail(
                "Homebrew not found",
                "Install from https://brew.sh then re-run this script.",
            )
            return False

        if not glpk_ok:
            r = _run(["brew", "install", "glpk"], capture_output=True, text=True)
            if r.returncode != 0:
                _print_fail("brew install glpk", r.stderr.strip())
                success = False

        if not cbc_ok:
            r = _run(["brew", "install", "cbc"], capture_output=True, text=True)
            if r.returncode != 0:
                _print_fail("brew install cbc", r.stderr.strip())
                success = False

    # ── Linux ─────────────────────────────────────────────────────────────
    elif SYSTEM == "Linux":
        pkg = _detect_linux_pkg_manager()
        if pkg is None:
            _print_fail(
                "No supported package manager found (apt, dnf, pacman)",
                "Install GLPK and CBC manually, then re-run with --check.",
            )
            return False

        mgr_name, glpk_cmd, cbc_cmd = pkg
        print(f"  Detected package manager: {mgr_name}")

        if not glpk_ok:
            r = _run(glpk_cmd, capture_output=True, text=True)
            if r.returncode != 0:
                _print_fail(" ".join(glpk_cmd), r.stderr.strip())
                success = False

        if not cbc_ok:
            r = _run(cbc_cmd, capture_output=True, text=True)
            if r.returncode != 0:
                _print_fail(" ".join(cbc_cmd), r.stderr.strip())
                success = False

    # ── Windows ───────────────────────────────────────────────────────────
    elif SYSTEM == "Windows":
        if _which("choco"):
            if not _is_admin():
                _print_warn(
                    "Not running as Administrator",
                    "choco installs may fail; CBC will use manual fallback if needed.",
                )

            if not glpk_ok:
                r = _run(["choco", "install", "glpk", "-y"],
                         capture_output=True, text=True)
                if r.returncode != 0:
                    _print_fail("choco install glpk", r.stderr.strip())
                    success = False

            if not cbc_ok:
                r = _run(["choco", "install", "coinor-cbc", "-y"],
                         capture_output=True, text=True)
                if r.returncode != 0:
                    _print_warn("coinor-cbc not available via Chocolatey, using manual fallback")

                    if not _install_cbc_windows_manual():
                        success = False

        elif _which("winget"):
            _print_warn("winget detected but GLPK/CBC not available via winget.")

            if not glpk_ok:
                success = False

            if not cbc_ok:
                if not _install_cbc_windows_manual():
                    success = False

        else:
            _print_warn(
                "No supported package manager (choco/winget) found on Windows",
                "Install Chocolatey (https://chocolatey.org/) or install GLPK manually.",
            )

            if not glpk_ok:
                success = False

            if not cbc_ok:
                if not _install_cbc_windows_manual():
                    success = False

    if success:
        print(f"  {GREEN}Solver dependencies installed.{RESET}")
    else:
        _print_warn("Some solvers could not be installed automatically.")
        _print_solver_manual_instructions()

    return success


def _print_solver_manual_instructions() -> None:
    """Print manual installation instructions for solvers."""
    print(textwrap.dedent(f"""
    {YELLOW}Manual solver installation:{RESET}

    GLPK:
      macOS:   brew install glpk
      Ubuntu:  sudo apt-get install -y glpk-utils
      Fedora:  sudo dnf install -y glpk-utils
      Arch:    sudo pacman -S glpk
      Windows: choco install glpk
               or download from https://www.gnu.org/software/glpk/

    CBC (COIN-OR):
      macOS:   brew install cbc
      Ubuntu:  sudo apt-get install -y coinor-cbc
      Fedora:  sudo dnf install -y coin-or-Cbc
      Arch:    sudo pacman -S coin-or-cbc
      Windows: choco install coinor-cbc
               or download from https://github.com/coin-or/Cbc/releases
    """))


# ──────────────────────────────────────────────────────────────────────────────
# Step 5 – Post-setup verification
# ──────────────────────────────────────────────────────────────────────────────

def run_checks() -> bool:
    """Run all verification checks and return True if everything passes."""
    _print_header("Step 5: Verification checks")

    all_ok = True
    venv_python = _venv_python()
    python = str(venv_python)

    # 4a – venv Python exists
    if venv_python.exists():
        _print_pass("Python venv exists", str(venv_python))
    else:
        _print_fail("Python venv not found", str(venv_python))
        all_ok = False

    # 4b – Key Python packages importable
    print()
    print("  Checking Python imports:")
    if venv_python.exists():
        for pkg in REQUIRED_IMPORTS:
            result = subprocess.run(
                [python, "-c", f"import {pkg}"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                _print_pass(f"import {pkg}")
            else:
                _print_fail(f"import {pkg}", result.stderr.strip().split("\n")[-1])
                all_ok = False
    else:
        _print_warn("Skipping import checks", "venv is missing; run full setup first")

    # 4c – Solver binaries
    print()
    print("  Checking solver binaries:")

    # GLPK: glpsol --version works normally
    glpsol_path = _which("glpsol")
    if glpsol_path:
        try:
            r = subprocess.run(
                ["glpsol", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            version_line = (r.stdout or r.stderr or "").strip().split("\n")[0]
            if r.returncode == 0:
                _print_pass("GLPK (glpsol)", version_line)
            else:
                _print_fail("GLPK (glpsol)", f"exit={r.returncode}; {version_line}")
                all_ok = False
        except subprocess.TimeoutExpired:
            _print_fail("GLPK (glpsol)", "timed out while checking solver")
            all_ok = False
    else:
        _print_fail("GLPK (glpsol)", "'glpsol' not found in PATH")
        all_ok = False

    # CBC: probe with -stop for a non-interactive check.
    cbc_path = _which("cbc")
    if cbc_path:
        try:
            r = subprocess.run(
                ["cbc", "-stop"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = (r.stdout or r.stderr or "").strip()
            lines = [line.strip() for line in output.splitlines() if line.strip()]
            version_info = lines[1] if len(lines) > 1 else (lines[0] if lines else "cbc responded")
            if r.returncode == 0:
                _print_pass("CBC", version_info)
            else:
                _print_fail("CBC", f"exit={r.returncode}; {version_info}")
                all_ok = False
        except subprocess.TimeoutExpired:
            _print_fail("CBC", "timed out while checking solver")
            all_ok = False
    else:
        _print_fail("CBC", "'cbc' not found in PATH")
        all_ok = False

    # 4d – Basic app startup check (import the Flask app module)
    print()
    print("  Checking app startup:")
    if venv_python.exists():
        startup_check = subprocess.run(
            [
                python, "-c",
                (
                    "import sys; "
                    f"sys.path.insert(0, {str(PROJECT_ROOT / 'API')!r}); "
                    "import app as muiogo_app; "
                    "assert hasattr(muiogo_app, 'app'); "
                    "print('API app module loadable')"
                ),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        if startup_check.returncode == 0:
            _print_pass("Flask app module loads without error")
        else:
            err = startup_check.stderr.strip().split("\n")[-1] if startup_check.stderr else "unknown"
            _print_fail("Flask app module failed to load", err)
            all_ok = False
    else:
        _print_warn("Skipping app startup check", "venv is missing; run full setup first")

    return all_ok


# ──────────────────────────────────────────────────────────────────────────────
# Summary and next steps
# ──────────────────────────────────────────────────────────────────────────────

def _print_summary(results: dict[str, tuple[bool, str]]) -> None:
    """Print a final summary table and actionable next steps."""
    _print_header("Setup Summary")

    all_ok = all(passed for passed, _ in results.values())

    for step, (passed, detail) in results.items():
        if detail.lower().startswith("skipped"):
            _print_skipped(step, detail)
            continue
        if passed:
            _print_pass(step, detail)
        else:
            _print_fail(step, detail)

    print()

    if all_ok:
        start_cmd = r'scripts\start.bat' if SYSTEM == "Windows" else "./scripts/start.sh"
        run_cmd = f'"{_venv_python()}" "{PROJECT_ROOT / "API" / "app.py"}"'
        print(textwrap.dedent(f"""\
        {GREEN}{BOLD}All checks passed! Your MUIOGO environment is ready.{RESET}

        Next steps:
          1. Start the app (opens browser automatically):
               {start_cmd}
          2. Stop the app with CTRL+C in the terminal.
          3. Advanced/manual start (without launcher):
               {run_cmd}
        """))
    else:
        check_cmd = r'scripts\setup.bat --check' if SYSTEM == "Windows" else "./scripts/setup.sh --check"
        setup_cmd = r'scripts\setup.bat' if SYSTEM == "Windows" else "./scripts/setup.sh"
        print(textwrap.dedent(f"""\
        {RED}{BOLD}Some checks failed.{RESET}

        Next steps:
          - Review the [FAIL] items above.
          - Fix the issues and re-run:
               {check_cmd}
          - If solver install failed, see manual instructions above or run:
               {setup_cmd}
            after installing the solvers manually.
          - For help, see CONTRIBUTING.md or open an issue.
        """))


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="MUIOGO cross-platform development environment setup",
    )
    parser.add_argument(
        "--venv-dir",
        help=(
            "Virtual environment directory path. "
            "Default: ~/.venvs/muiogo (or MUIOGO_VENV_DIR if set)."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run verification checks only (skip install steps)",
    )
    parser.add_argument(
        "--with-demo-data",
        action="store_true",
        dest="with_demo_data",
        help="Install demo data from local archive (default behavior).",
    )
    parser.add_argument(
        "--no-demo-data",
        action="store_false",
        dest="with_demo_data",
        help="Skip demo-data installation.",
    )
    parser.add_argument(
        "--force-demo-data",
        action="store_true",
        help="Reinstall demo data by deleting existing demo-data targets first.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation prompts (required for non-interactive force reinstall).",
    )
    parser.set_defaults(with_demo_data=True)
    args = parser.parse_args()

    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "").strip()
    if conda_env:
        print(
            f"{RED}{BOLD}Conda environment is active: {conda_env}{RESET}\n"
            "Run 'conda deactivate' (repeat until no conda env is active), then run setup again."
        )
        return 1

    if args.force_demo_data:
        args.with_demo_data = True

    global VENV_DIR
    VENV_DIR = _resolve_venv_dir(
        venv_dir_arg=args.venv_dir,
    )

    current_py = sys.version_info[:2]
    if not _python_supported(current_py):
        if SYSTEM == "Darwin":
            install_hint = (
                "Install Python 3.11 in Terminal: brew install python@3.11\n"
                "Python.org macOS installer: https://www.python.org/downloads/macos/"
            )
        elif SYSTEM == "Windows":
            install_hint = (
                "Install Python 3.11 in PowerShell: winget install -e --id Python.Python.3.11\n"
                "Python.org Windows installer: https://www.python.org/downloads/windows/"
            )
        else:
            install_hint = (
                "Install Python 3.11 with your package manager.\n"
                "Python.org downloads: https://www.python.org/downloads/"
            )
        print(
            f"{RED}{BOLD}Unsupported Python version: {sys.version.split()[0]}{RESET}\n"
            f"MUIOGO setup currently supports Python >={MIN_PYTHON[0]}.{MIN_PYTHON[1]} "
            f"and <{MAX_PYTHON[0]}.{MAX_PYTHON[1]} (recommended: 3.11).\n"
            f"{install_hint}"
        )
        return 1

    print(f"\n{BOLD}MUIOGO Development Environment Setup{RESET}")
    print(f"  Platform : {SYSTEM} ({platform.machine()})")
    print(f"  Python   : {sys.version.split()[0]}")
    print(f"  Support  : >={MIN_PYTHON[0]}.{MIN_PYTHON[1]}, <{MAX_PYTHON[0]}.{MAX_PYTHON[1]}")
    print(f"  Project  : {PROJECT_ROOT}")
    print(f"  Venv dir : {VENV_DIR}")

    if PROJECT_ROOT.resolve() in VENV_DIR.resolve().parents:
        _print_warn(
            "Using in-repo virtual environment",
            "This can cause high CPU in Codex Desktop. External venv is recommended.",
        )

    if args.check:
        demo_ok = True
        if args.with_demo_data:
            demo_ok = check_demo_data()
        else:
            _print_header("Step 4: Demo data (check)")
            if demo_data_present():
                _print_warn("Demo data check skipped (--no-demo-data)", "demo data currently present")
            else:
                _print_warn("Demo data check skipped (--no-demo-data)", "demo data not installed")
        check_ok = run_checks()
        return 0 if demo_ok and check_ok else 1

    results: dict[str, tuple[bool, str]] = {}

    step1_ok = setup_venv()
    results["Python virtual environment"] = (step1_ok, str(VENV_DIR))

    if step1_ok:
        results["Python dependencies"] = (install_python_deps(), "")
    else:
        results["Python dependencies"] = (False, "skipped because venv setup failed")
        _print_fail("Skipping Python deps (venv setup failed)")

    results["App secret key"] = (_ensure_secret_key_in_env(), str(ENV_FILE))

    results["Solver dependencies (GLPK & CBC)"] = (install_solvers(), "")

    demo_detail = ""
    if args.with_demo_data:
        had_demo_before = demo_data_present()
        demo_ok = install_demo_data(
            force=args.force_demo_data,
            yes=args.yes,
        )
        if demo_ok:
            if had_demo_before and not args.force_demo_data:
                demo_detail = "already installed"
            elif args.force_demo_data:
                demo_detail = "reinstalled"
            else:
                demo_detail = "installed"
        else:
            demo_detail = "failed (see logs above)"
        results["Demo data"] = (demo_ok, demo_detail)
    else:
        if demo_data_present():
            demo_detail = "skipped (--no-demo-data); already present"
        else:
            demo_detail = "skipped (--no-demo-data); not installed"
        results["Demo data"] = (True, demo_detail)

    results["Verification checks"] = (run_checks(), "")

    _print_summary(results)

    return 0 if all(passed for passed, _ in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

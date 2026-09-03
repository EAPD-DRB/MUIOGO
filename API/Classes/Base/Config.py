from pathlib import Path
import os
import tempfile
from dotenv import load_dotenv
import platform

# Central path validation utility (prevents path traversal).
def validate_path(base_dir, user_input):
    """Resolve user_input under base_dir, or raise PermissionError.

    Containment is decided lexically on the requested string, not on where the
    path resolves to, so that a case reached through an operator-placed symlink
    in DataStorage still works. See the stage comments below.
    """
    base_raw = os.fspath(base_dir)
    user_raw = "" if user_input is None else os.fspath(user_input)

    if isinstance(base_raw, (bytes, bytearray)):
        base_raw = base_raw.decode("utf-8", "surrogateescape")
    if isinstance(user_raw, (bytes, bytearray)):
        user_raw = user_raw.decode("utf-8", "surrogateescape")

    if "\x00" in base_raw or "\x00" in user_raw:
        raise PermissionError("Path Traversal Attempt Detected")

    # ---- Stage 1: judge the caller's string, before resolving anything. ----
    # This is the containment decision, and it is made lexically so that it
    # cannot be changed by what happens to exist on disk. A request must be a
    # relative path, of at least one component, that never climbs above base.
    if os.path.isabs(user_raw) or os.path.splitdrive(user_raw)[0]:
        raise PermissionError("Path Traversal Attempt Detected")

    flat = user_raw.replace(os.altsep, os.sep) if os.altsep else user_raw
    parts = [p for p in flat.split(os.sep) if p not in ("", ".")]
    depth = 0
    for part in parts:
        depth += -1 if part == ".." else 1
        if depth < 0:
            raise PermissionError("Path Traversal Attempt Detected")
    if depth == 0:
        # Empty, None, or something like "case/.." - the base itself.
        raise PermissionError("Path Traversal Attempt Detected")

    base_abs = os.path.realpath(os.path.abspath(os.path.normpath(base_raw)))
    target_abs = os.path.abspath(os.path.normpath(os.path.join(base_abs, user_raw)))
    resolved = os.path.realpath(target_abs)

    # ---- Stage 2: the ordinary case - a real path inside base. ----
    try:
        if os.path.commonpath([base_abs, resolved]) == base_abs and resolved != base_abs:
            return resolved
    except ValueError:
        raise PermissionError("Path Traversal Attempt Detected")

    # ---- Stage 3: the operator symlink. ----
    # Resolution left base. That is legitimate in exactly one shape: an operator
    # has made <base>/<case> a symlink to a case living in its own country
    # repository (the CLEWs-FJI / CLEWs-PHL handoff, where the case is tracked
    # in its own repo and DataStorage only points at it). Allow it only when the
    # FIRST component under base is that symlink, and the resolved path is still
    # inside what the symlink points at - so a second symlink planted deeper in
    # the linked case cannot redirect the read anywhere it likes.
    #
    # This does mean any symlink an operator plants directly in DataStorage is
    # followed. That is safe only for as long as no request can create one:
    # UploadRoute._extract_case_zip writes regular files only, and nothing in
    # API/ calls os.symlink or ZipFile.extractall. If that changes, so must this.
    entry = os.path.join(base_abs, parts[0])
    if not os.path.islink(entry):
        raise PermissionError("Path Traversal Attempt Detected")
    root = os.path.realpath(entry)
    if not os.path.isdir(root):
        raise PermissionError("Path Traversal Attempt Detected")
    try:
        if os.path.commonpath([root, resolved]) != root:
            raise PermissionError("Path Traversal Attempt Detected")
    except ValueError:
        raise PermissionError("Path Traversal Attempt Detected")

    return resolved

#load environment variables
load_dotenv()

SYSTEM = platform.system()

# S3_BUCKET = os.environ.get("S3_BUCKET")
# S3_KEY = os.environ.get("S3_KEY")
# S3_SECRET = os.environ.get("S3_SECRET")

#S3 bucket is not used in Osemosys
S3_BUCKET = ""
S3_KEY = ""
S3_SECRET = ""

ALLOWED_EXTENSIONS = set(['zip', 'application/zip'])
ALLOWED_EXTENSIONS_XLS = set(['xls', 'xlsx'])
# -------------------------
# FIX: Make paths independent of working directory
# -------------------------

# This file is in: API/Classes/Base/Config.py
# So project root is 3 levels up
BASE_DIR = Path(__file__).resolve().parents[3]

WEBAPP_PATH = BASE_DIR / "WebAPP"

UPLOAD_FOLDER = WEBAPP_PATH
DATA_STORAGE = WEBAPP_PATH / "DataStorage"
CLASS_FOLDER = WEBAPP_PATH / "Classes"
SOLVERs_FOLDER = WEBAPP_PATH / "SOLVERs"
EXTRACT_FOLDER = BASE_DIR
PRIMARY_RUNTIME_DIR = BASE_DIR / ".runtime"
PRIMARY_RUNTIME_LOG_DIR = PRIMARY_RUNTIME_DIR / "logs"
TEMP_RUNTIME_LOG_DIR = Path(tempfile.gettempdir()) / "muiogo-runtime" / "logs"
_RUNTIME_LOG_PATH = None

# Ensure DataStorage exists
DATA_STORAGE.mkdir(parents=True, exist_ok=True)

# Validate writability instead of forcing permissions
if not os.access(DATA_STORAGE, os.W_OK):
    raise PermissionError(f"Data storage path is not writable: {DATA_STORAGE}")

# -------------------------
# OG-Core calibration install + registry layer
# -------------------------
# OG country models live in their OWN uv environments, installed by the OG-Core
# Universal Installer. MUIOGO neither installs nor imports OG-Core; it drives the
# installer and tracks what is installed.

# MUIOGO-side OG state (registry, install-job state, caches) lives at the user level
# under ~/.muiogo, never inside the CLEWS DataStorage tree and never inside a
# calibration's .venv. Keeping it out of DataStorage is what stops the CLEWS case
# picker (and the other DataStorage walkers) from treating it as a case. See #500.
OGC_DATA_STORAGE = Path(
    os.environ.get("MUIOGO_OG_DATA_DIR", "").strip()
    or (Path.home() / ".muiogo" / "og-state")
)
OGC_INSTALLED_REGISTRY = OGC_DATA_STORAGE / "og_calibrations_installed.json"
OGC_INSTALL_JOBS_DIR = OGC_DATA_STORAGE / "install_jobs"
OGC_CATALOG_CACHE = OGC_DATA_STORAGE / "catalog_cache.json"
OGC_INSTALLER_CACHE_DIR = OGC_DATA_STORAGE / "installer"
# Cases live in their own subfolder so they never collide with the registry,
# install-job, and installer-cache entries that #486 stores in OGC_DATA_STORAGE.
OGC_CASES_DIR = OGC_DATA_STORAGE / "cases"

# Calibration environments install OUTSIDE the repo. Default ~/.muiogo/og-models,
# overridable so a user can point installs elsewhere. A country lands at
# OGC_MODELS_DIR/<RepoName>/ with its own .venv.
OGC_MODELS_DIR = Path(
    os.environ.get("MUIOGO_OG_MODELS_DIR", "").strip()
    or (Path.home() / ".muiogo" / "og-models")
)

# OG-CLEWS link run outputs (manifests, macro tables, decks, the link's OG
# baseline cache). Same rule as OG state: under ~/.muiogo, never inside the
# CLEWS DataStorage tree -- these can be hundreds of MB and must not ride
# along in case zips or case copies.
OGLINK_RUNS_DIR = Path(
    os.environ.get("MUIOGO_OGLINK_RUNS_DIR", "").strip()
    or (Path.home() / ".muiogo" / "oglink-runs")
)

# Where the ogclews-link installer is expected to place the link on an
# end-user machine (same convention as og-models). The post-run hook probes
# this after the OGCLEWS_LINK_* env overrides and before the dev-layout
# ../ogclews-link sibling.
OGLINK_HOME_DIR = Path.home() / ".muiogo" / "ogclews-link"

# -------------------------
# CLEWs country install + registry layer
# -------------------------
# A CLEWs country install is DATA, not code: verified case archives extracted into
# DataStorage through the same importer the browser upload uses. Two kinds of state:
#
# - The installed-case index describes ONE DataStorage, so it lives inside it, as
#   the dot-file .clews_registry.json (resolved at call time in CountryRegistry so
#   it always tracks the active DATA_STORAGE). A file is safe under the #500 rule:
#   the case picker and the reconcile scan list DIRECTORIES, and DataStorage's root
#   already carries app-level files (Parameters.json etc.). Keeping it per-storage
#   is what lets several MUIOGO checkouts on one machine not fight over one index.
#
# - Transient machine-level state (install-job status, download staging) lives at
#   the user level like the OG state above. Archives download and verify THERE,
#   never into DataStorage, so a partial download can never appear as a case.
CLEWS_DATA_STORAGE = Path(
    os.environ.get("MUIOGO_CLEWS_DATA_DIR", "").strip()
    or (Path.home() / ".muiogo" / "clews-state")
)
CLEWS_INSTALL_JOBS_DIR = CLEWS_DATA_STORAGE / "install_jobs"
CLEWS_DOWNLOADS_DIR = CLEWS_DATA_STORAGE / "downloads"
CLEWS_REGISTRY_BASENAME = ".clews_registry.json"

# The CLEWs country register: the CLEWs mirror of the OG installer's repos.json,
# listing country repos that ship portable MUIO cases. MUIOGO ships it as
# scripts/clews-repos.json and reads it from the main branch, so adding a country
# there is enough for every installation to offer it (the same way OG-Core's
# register is read from its repository). The env override points tests and
# offline runs at another URL, a file:// one included; an empty override is
# honoured as "no register" and the catalogue reports source "none".
CLEWS_CATALOG_URL = os.environ.get(
    "MUIOGO_CLEWS_CATALOG_URL",
    "https://raw.githubusercontent.com/EAPD-DRB/MUIOGO/main/scripts/clews-repos.json",
).strip()
CLEWS_CATALOG_CACHE = CLEWS_DATA_STORAGE / "catalog_cache.json"

# Where the installer's machine-readable catalogue and scripts are fetched from.
# Env overrides let tests/offline runs point at a local mirror.
_OGC_INSTALLER_RAW_BASE = (
    os.environ.get("MUIOGO_OG_INSTALLER_RAW_BASE", "").strip()
    or "https://raw.githubusercontent.com/PSLmodels/OG-Core/master/scripts"
)
OGC_INSTALLER_REPOS_JSON_URL = (
    os.environ.get("MUIOGO_OG_INSTALLER_REPOS_JSON_URL", "").strip()
    or f"{_OGC_INSTALLER_RAW_BASE}/repos.json"
)
OGC_INSTALLER_SH_URL = (
    os.environ.get("MUIOGO_OG_INSTALLER_SH_URL", "").strip()
    or f"{_OGC_INSTALLER_RAW_BASE}/install.sh"
)
OGC_INSTALLER_PS1_URL = (
    os.environ.get("MUIOGO_OG_INSTALLER_PS1_URL", "").strip()
    or f"{_OGC_INSTALLER_RAW_BASE}/install.ps1"
)


def venv_python_path(venv_dir):
    """Return the interpreter inside a uv/venv directory for this platform.

    Windows: <venv>/Scripts/python.exe. macOS/Linux: <venv>/bin/python.
    """
    venv_dir = Path(venv_dir)
    if SYSTEM == "Windows":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def ogc_clean_env():
    """A copy of os.environ with any active venv/conda markers stripped.

    The universal installer refuses to run when a virtualenv or conda env is
    active, and MUIOGO itself runs inside its own venv. Spawn installer/uv
    subprocesses with this env so the guard does not abort every install.
    """
    env = os.environ.copy()
    for marker in ("VIRTUAL_ENV", "CONDA_DEFAULT_ENV", "CONDA_PREFIX", "CONDA_SHLVL"):
        env.pop(marker, None)
    return env


def get_runtime_log_path():
    global _RUNTIME_LOG_PATH

    if _RUNTIME_LOG_PATH is not None:
        return _RUNTIME_LOG_PATH

    for log_dir in (PRIMARY_RUNTIME_LOG_DIR, TEMP_RUNTIME_LOG_DIR):
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            probe = log_dir / ".write_test"
            with open(probe, "a", encoding="utf-8"):
                pass
            probe.unlink(missing_ok=True)
            _RUNTIME_LOG_PATH = log_dir / "app.log"
            return _RUNTIME_LOG_PATH
        except OSError:
            continue

    raise PermissionError("No writable runtime log directory is available.")
#absolute paths
# OSEMOSYS_ROOT = os.path.abspath(os.getcwd())
# UPLOAD_FOLDER = Path(OSEMOSYS_ROOT, 'WebAPP')
# WebAPP_PATH = Path(OSEMOSYS_ROOT, 'WebAPP')
# DATA_STORAGE = Path(OSEMOSYS_ROOT, "WebAPP", 'DataStorage')
# CLASS_FOLDER = Path(OSEMOSYS_ROOT, "WebAPP", 'Classes')
# EXTRACT_FOLDER = Path(OSEMOSYS_ROOT, "")
# SOLVERs_FOLDER = Path(OSEMOSYS_ROOT, 'WebAPP', 'SOLVERs')

HEROKU_DEPLOY = 0
AWS_SYNC = 0

# API base URL: configurable via MUIOGO_API_URL env var.
# Defaults to window.location.origin on the frontend when not set.
API_BASE_URL = os.environ.get("MUIOGO_API_URL", "")

# CORS allowed origins: configurable via MUIOGO_CORS_ORIGINS env var.
# Accepts a comma-separated list. Defaults to localhost origins for local dev.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "MUIOGO_CORS_ORIGINS",
        "http://127.0.0.1:5002,http://localhost:5002,http://127.0.0.1,http://localhost"
    ).split(",")
    if origin.strip()
]

PINNED_COLUMNS = ('Sc', 'Tech', 'Comm', 'Emis','Stg', 'Ts', 'MoO', 'UnitId', 'Se','Dt', 'Dtb', 'paramName','TechName', 'CommName', 'EmisName', 'ConName', 'MoId')

TECH_GROUPS = ('RYT', 'RYTM', 'RYTC', 'RYTCn', 'RYTCM', 'RYTE', 'RYTEM', 'RYTTs')
COMM_GROUPS = ('RYC', 'RYTC', 'RYTCM','RYCTs')
EMIS_GROUPS = ('RYE', 'RYTE', 'RYTEM')

SINGLE_TECH_GROUPS = ['RT']
SINGLE_EMIS_GROUPS = ['RE']

# Variable and dual definitions previously lived here as `VARIABLES_C` and
# `DUALS`. Both moved to data files in #460 (Variables.json / Duals.json) with
# a `setrelation` field on each entry, accessed at runtime via
# OsemosysClass.VAR_BY_NAME / DUALS_BY_NAME — see docs/UPSTREAM_SYNC.md.

#needed for validation of inputs
PARAMETERS_C = {
        'DiscountRate': ['r'],
        'OutputActivityRatio':['r','f','t','y','m'],
        'InputActivityRatio':['r','f','t','y','m'],
        'EmissionActivityRatio':['r','e','t','y','m'],
        'TotalAnnualMaxCapacityInvestment':['r','t','y'],
        'TotalAnnualMinCapacityInvestment':['r','t','y'],
        'TotalTechnologyAnnualActivityUpperLimit':['r','t','y'],
        'TotalTechnologyAnnualActivityLowerLimit':['r','t','y'],
        'TotalAnnualMaxCapacity':['r','t','y'],
        'ResidualCapacity': ['r','t','y'],
        'AvailabilityFactor': ['r','t','y'],
        'CapacityToActivityUnit': ['r','t'],
        'DiscountRateIdv': ['r','t'],
        'OperationalLife': ['r','t'],
        'TotalTechnologyModelPeriodActivityLowerLimit': ['r','t'],
        'TotalTechnologyModelPeriodActivityUpperLimit': ['r','t'],
        'CapacityFactor': ['r','t', 'y', 'l'],
        'YearSplit': ['r','y', 'l'],
        'SpecifiedDemandProfile': ['r','f','y','l']
    }

PARAMETERS_C_full = {
        'DiscountRate': ['r', 'DiscountRate'],
        'OutputActivityRatio':['r','f','t','y','m','OutputActivityRatio'],
        'InputActivityRatio':['r','f','t','y','m','InputActivityRatio'],
        'EmissionActivityRatio':['r','e','t','y','m','EmissionActivityRatio'],
        'TotalAnnualMaxCapacityInvestment':['r','t','y','TotalAnnualMaxCapacityInvestment'],
        'TotalAnnualMinCapacityInvestment':['r','t','y','TotalAnnualMinCapacityInvestment'],
        'TotalTechnologyAnnualActivityUpperLimit':['r','t','y','TotalTechnologyAnnualActivityUpperLimit'],
        'TotalTechnologyAnnualActivityLowerLimit':['r','t','y','TotalTechnologyAnnualActivityLowerLimit'],
        'TotalAnnualMaxCapacity':['r','t','y','TotalAnnualMaxCapacity'],
        'ResidualCapacity': ['r','t','y','ResidualCapacity'],
        'AvailabilityFactor': ['r','t','y','AvailabilityFactor'],
        'CapacityToActivityUnit': ['r','t','CapacityToActivityUnit'],
        'DiscountRateIdv': ['r','t','DiscountRateIdv'],
        'OperationalLife': ['r','t','OperationalLife'],
        'TotalTechnologyModelPeriodActivityLowerLimit': ['r','t','TotalTechnologyModelPeriodActivityLowerLimit'],
        'TotalTechnologyModelPeriodActivityUpperLimit': ['r','t','TotalTechnologyModelPeriodActivityUpperLimit'],
        'CapacityFactor': ['r','t', 'y', 'l','CapacityFactor'],
        'YearSplit': ['r','y', 'l','YearSplit'],
        'SpecifiedDemandProfile': ['r','f','y','l','SpecifiedDemandProfile'],
        'ResidualStorageCapacity': ['r','s','y','ResidualStorageCapacity'],
    }

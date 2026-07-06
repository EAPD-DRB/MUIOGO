from pathlib import Path
import os
import tempfile
from dotenv import load_dotenv
import platform

# Central path validation utility (prevents path traversal).
def validate_path(base_dir, user_input):
    base_raw = os.fspath(base_dir)
    user_raw = "" if user_input is None else os.fspath(user_input)

    if isinstance(base_raw, (bytes, bytearray)):
        base_raw = base_raw.decode("utf-8", "surrogateescape")
    if isinstance(user_raw, (bytes, bytearray)):
        user_raw = user_raw.decode("utf-8", "surrogateescape")

    if "\x00" in base_raw or "\x00" in user_raw:
        raise PermissionError("Path Traversal Attempt Detected")

    base_abs = os.path.realpath(os.path.abspath(os.path.normpath(base_raw)))
    target_abs = os.path.realpath(
        os.path.abspath(os.path.normpath(os.path.join(base_abs, user_raw)))
    )

    try:
        common = os.path.commonpath([base_abs, target_abs])
    except ValueError:
        raise PermissionError("Path Traversal Attempt Detected")

    if common != base_abs or target_abs == base_abs:
        raise PermissionError("Path Traversal Attempt Detected")

    return target_abs

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
# installer and tracks what is installed. See:
#   universal installer setup OGC/Universal-Installer-Master-Doc.md
#   Track1-API-Schema-Discussion/OGCore-API-Schema-FINAL.md

# MUIOGO-side storage (registry + install-job state) lives under DataStorage,
# never inside a calibration's .venv.
OGC_DATA_STORAGE = DATA_STORAGE / "OGCore"
OGC_INSTALLED_REGISTRY = OGC_DATA_STORAGE / "og_calibrations_installed.json"
OGC_INSTALL_JOBS_DIR = OGC_DATA_STORAGE / "install_jobs"
OGC_CATALOG_CACHE = OGC_DATA_STORAGE / "catalog_cache.json"
OGC_INSTALLER_CACHE_DIR = OGC_DATA_STORAGE / "installer"

# Calibration environments install OUTSIDE the repo. Default ~/.muiogo/og-models,
# overridable so a user can point installs elsewhere. A country lands at
# OGC_MODELS_DIR/<RepoName>/ with its own .venv.
OGC_MODELS_DIR = Path(
    os.environ.get("MUIOGO_OG_MODELS_DIR", "").strip()
    or (Path.home() / ".muiogo" / "og-models")
)

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

from flask import Blueprint, jsonify
import platform
import shutil
import os
import time
import logging
from pathlib import Path
from Classes.Base import Config

health_api = Blueprint('HealthRoute', __name__)

# Basic module-level variables to cache solver check results
_SOLVER_CACHE_DATA = {}
_SOLVER_CACHE_TIME = 0.0
CACHE_TTL = 300  # 5 minutes


def _check_solver(binary_name, env_var):
    """Check if a solver binary is reachable.

    Resolution order mirrors Osemosys._resolve_solver_folder:
    1. Environment variable
    2. System PATH (shutil.which)
    3. Bundled binary under SOLVERs_FOLDER
    """
    allowed_names = _binary_names(binary_name)

    # 1 — env var
    env_val = os.environ.get(env_var, "").strip().strip("\"'")
    if env_val:
        env_path = Path(env_val).expanduser()
        if env_path.is_file():
            # Validate that the file is actually one of the expected binary names
            if env_path.name.lower() in [n.lower() for n in allowed_names]:
                return {"found": True, "source": "env", "path": str(env_path)}
        # directory — look inside
        if env_path.is_dir():
            for name in allowed_names:
                candidate = env_path / name
                if candidate.is_file():
                    return {"found": True, "source": "env", "path": str(candidate)}
        return {"found": False, "source": None, "path": None}

    # 2 — system PATH
    for name in allowed_names:
        which_result = shutil.which(name)
        if which_result:
            return {"found": True, "source": "path", "path": which_result}

    # 3 — bundled
    # Optimize search by checking common subdirectories (GLPK, CBC) first
    bundled_dir = Config.SOLVERs_FOLDER
    # Subdirs to check to avoid full recursive scan of a large SOLVERs_FOLDER
    search_dirs = [bundled_dir]
    if binary_name.lower() == "glpsol":
        search_dirs.append(bundled_dir / "GLPK")
    elif binary_name.lower() == "cbc":
        search_dirs.append(bundled_dir / "COIN-OR")
        search_dirs.append(bundled_dir / "cbc")

    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        for name in allowed_names:
            # Check shallowly first to avoid rglob complexity when possible
            candidate = s_dir / name
            if candidate.is_file():
                return {"found": True, "source": "bundled", "path": str(candidate)}

            # Only rglob if we haven't found it (rglob is expensive)
            # We limit to first match if rglob is used
            for r_candidate in s_dir.rglob(name):
                if r_candidate.is_file():
                    return {"found": True, "source": "bundled", "path": str(r_candidate)}
                break

    return {"found": False, "source": None, "path": None}


def _binary_names(binary_name):
    """Return list of possible binary filenames for the current platform."""
    names = [binary_name]
    if platform.system() == "Windows" and not binary_name.lower().endswith(".exe"):
        names.insert(0, binary_name + ".exe")
    return names


@health_api.route("/api/health", methods=['GET'])
def healthCheck():
    """Basic liveness and readiness check — confirms the Flask backend is healthy."""
    try:
        # verify DataStorage is accessible and writable
        storage_ok = Config.DATA_STORAGE.is_dir() and os.access(Config.DATA_STORAGE, os.W_OK)

        response = {
            "status": "ok" if storage_ok else "error",
            "platform": platform.system(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "dataStorage": "writable" if storage_ok else "error"
        }

        if not storage_ok:
            return jsonify(response), 503

        return jsonify(response), 200
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return jsonify({"status": "error", "message": "Failed to perform system health check"}), 500


@health_api.route("/api/health/solvers", methods=['GET'])
def solverStatus():
    """Report availability of GLPK and CBC solvers on this machine.

    Uses simple module variables to avoid repeated disk scans during high-frequency polling.
    """
    global _SOLVER_CACHE_DATA, _SOLVER_CACHE_TIME
    try:
        # Check cache
        current_time = time.time()
        if _SOLVER_CACHE_DATA and (current_time - _SOLVER_CACHE_TIME < CACHE_TTL):
            return jsonify(_SOLVER_CACHE_DATA), 200

        glpk = _check_solver("glpsol", "SOLVER_GLPK_PATH")
        cbc = _check_solver("cbc", "SOLVER_CBC_PATH")

        response = {
            "glpk": glpk,
            "cbc": cbc,
            "anyAvailable": glpk["found"] or cbc["found"]
        }

        _SOLVER_CACHE_DATA = response
        _SOLVER_CACHE_TIME = current_time

        return jsonify(response), 200
    except Exception as e:
        logging.error(f"Solver health check failed: {e}")
        return jsonify({"status": "error", "message": "Failed to perform solver health check"}), 500

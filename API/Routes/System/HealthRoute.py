from flask import Blueprint, jsonify
import platform
import shutil
import os
from pathlib import Path
from Classes.Base import Config

health_api = Blueprint('HealthRoute', __name__)


def _check_solver(binary_name, env_var):
    """Check if a solver binary is reachable.

    Resolution order mirrors Osemosys._resolve_solver_folder:
    1. Environment variable
    2. System PATH (shutil.which)
    3. Bundled binary under SOLVERs_FOLDER
    """

    # 1 — env var
    env_val = os.environ.get(env_var, "").strip().strip("\"'")
    if env_val:
        env_path = Path(env_val).expanduser()
        if env_path.is_file():
            return {"found": True, "source": "env", "path": str(env_path)}
        # directory — look inside
        if env_path.is_dir():
            for name in _binary_names(binary_name):
                candidate = env_path / name
                if candidate.is_file():
                    return {"found": True, "source": "env", "path": str(candidate)}
        return {"found": False, "source": None, "path": None}

    # 2 — system PATH
    for name in _binary_names(binary_name):
        which_result = shutil.which(name)
        if which_result:
            return {"found": True, "source": "path", "path": which_result}

    # 3 — bundled
    bundled_dir = Config.SOLVERs_FOLDER
    for name in _binary_names(binary_name):
        # check top-level and one level deep (GLPK/, COIN-OR/ subdirs)
        for candidate in bundled_dir.rglob(name):
            if candidate.is_file():
                return {"found": True, "source": "bundled", "path": str(candidate)}

    return {"found": False, "source": None, "path": None}


def _binary_names(binary_name):
    """Return list of possible binary filenames for the current platform."""
    names = [binary_name]
    if platform.system() == "Windows" and not binary_name.lower().endswith(".exe"):
        names.insert(0, binary_name + ".exe")
    return names


@health_api.route("/api/health", methods=['GET'])
def healthCheck():
    """Basic liveness check — confirms the Flask backend is running."""
    try:
        # verify DataStorage is accessible
        storage_ok = Config.DATA_STORAGE.is_dir() and os.access(Config.DATA_STORAGE, os.W_OK)

        response = {
            "status": "ok",
            "platform": platform.system(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "dataStorage": "writable" if storage_ok else "error"
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@health_api.route("/api/health/solvers", methods=['GET'])
def solverStatus():
    """Report availability of GLPK and CBC solvers on this machine.

    Useful for cross-platform diagnostics — lets users (and the frontend)
    know whether solvers are ready before attempting a model run.
    """
    try:
        glpk = _check_solver("glpsol", "SOLVER_GLPK_PATH")
        cbc = _check_solver("cbc", "SOLVER_CBC_PATH")

        response = {
            "glpk": glpk,
            "cbc": cbc,
            "anyAvailable": glpk["found"] or cbc["found"]
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

"""OG calibration install + registry endpoints.

All routes live under /ogc. The frontend never runs uv or shell directly; it calls
these endpoints and the backend either wraps the OG-Core universal installer
(catalog / repo URL) or validates and records a local copy. See:
    Track1-API-Schema-Discussion/OGCore-API-Schema-FINAL.md
"""
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from Classes.Base import Config
from Classes.OGCore.CalibrationCatalog import CalibrationCatalog
from Classes.OGCore.CalibrationRegistry import CalibrationRegistry
from Classes.OGCore.InstallJob import InstallJob
from Classes.OGCore.Installer import (
    Installer,
    read_pyproject_package_name,
    repo_name_from_url,
)

ogcore_install_api = Blueprint("OGCoreInstallRoute", __name__, url_prefix="/ogc")

_COUNTRY_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_GIT_URL_RE = re.compile(r"^(https://|http://|git@|ssh://)", re.IGNORECASE)
_INSTALL_ID_RE = re.compile(r"^install_\d{4}_\d{2}_\d{2}_\d{3}$")
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


# ── small helpers ────────────────────────────────────────────────────────────
def _err(message, http=400, status="error"):
    return jsonify({"message": message, "status_code": status}), http


def _blocked_cross_site():
    """Refuse a state-changing request that a cross-site page drove via the browser.

    A browser always attaches an Origin header on a cross-origin POST, so if one is
    present it must be the local app. Non-browser callers (the desktop shell, curl,
    tests) send no Origin and are allowed, matching the app's local-only model.
    Returns an error response to short-circuit, or None to proceed.
    """
    origin = request.headers.get("Origin")
    if origin:
        host = urlparse(origin).hostname
        if host not in _LOCAL_HOSTS:
            return _err("Cross-site request refused.", http=403)
    return None


def _clean_path(raw):
    """Normalise a user-supplied path; reject null bytes. Returns an abspath or None.

    We do not confine local_path to a base dir: registering an existing clone from
    anywhere on disk is an intended feature. This only rejects the obviously unsafe
    (null bytes) and normalises, so downstream sees a clean absolute path.
    """
    if not raw or "\x00" in raw:
        return None
    try:
        return os.path.abspath(os.path.normpath(raw))
    except (OSError, ValueError):
        return None


def _body():
    """Return the JSON body or None (for a 400)."""
    return request.get_json(silent=True)


def _missing(data, *fields):
    """First missing/empty field name, or None."""
    for field in fields:
        if data.get(field) in (None, ""):
            return field
    return None


def _valid_country_id(country_id):
    return bool(country_id) and bool(_COUNTRY_ID_RE.match(country_id))


def _default_dest_parent():
    return str(Config.OGC_MODELS_DIR)


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── 1. catalogue ─────────────────────────────────────────────────────────────
@ogcore_install_api.route("/getCalibrationCatalog", methods=["GET"])
def getCalibrationCatalog():
    countries, source = CalibrationCatalog.get_catalog_with_state()
    return jsonify({
        "status_code": "success",
        "countries": countries,
        "catalog_source": source,  # live | cache | none
    }), 200


# ── 2. installed list ────────────────────────────────────────────────────────
@ogcore_install_api.route("/getInstalledCalibrations", methods=["GET"])
def getInstalledCalibrations():
    return jsonify({
        "status_code": "success",
        "calibrations": CalibrationRegistry.list_all(),
    }), 200


# ── 3. pre-install check ─────────────────────────────────────────────────────
@ogcore_install_api.route("/checkCalibration", methods=["POST"])
def checkCalibration():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = _body()
    if data is None:
        return _err("Request body must be valid JSON.")
    miss = _missing(data, "source_type", "country_id", "country_name")
    if miss:
        return _err(f"Missing required field: {miss}")
    if not _valid_country_id(data["country_id"]):
        return _err("country_id must be a short code (letters, digits, - or _).")

    source_type = data["source_type"]

    if source_type == "local_path":
        if not data.get("local_path"):
            return _err("Missing required field: local_path")
        local_path = _clean_path(data["local_path"])
        if not local_path:
            return _err("That path is not valid.")
        path = Path(local_path)
        if not path.is_dir():
            return _err("That folder does not exist.", http=400)
        has_pyproject = (path / "pyproject.toml").exists()
        detected = {
            "has_pyproject": has_pyproject,
            "has_uv_lock": (path / "uv.lock").exists(),
            "package_name": read_pyproject_package_name(path),
            "repo_url": Installer.git_remote_url(path),
            "commit_sha": Installer.git_head_sha(path),
            "has_venv": Config.venv_python_path(path / ".venv").exists(),
        }
        warnings = []
        if not detected["has_uv_lock"]:
            warnings.append("No uv.lock found; uv sync will create one.")
        return jsonify({
            "status_code": "success",
            "check_state": "valid" if has_pyproject else "invalid",
            "source_type": source_type,
            "country_id": data["country_id"],
            "country_name": data["country_name"],
            "local_path": str(path),
            "detected": detected,
            "warnings": warnings,
        }), 200

    if source_type == "repo_url":
        repo_url = data.get("repo_url")
        if not repo_url:
            return _err("Missing required field: repo_url")
        if not _GIT_URL_RE.match(repo_url.strip()):
            return jsonify({
                "status_code": "success",
                "check_state": "invalid",
                "source_type": source_type,
                "country_id": data["country_id"],
                "country_name": data["country_name"],
                "repo_url": repo_url,
                "detected": {},
                "warnings": ["That does not look like a Git URL."],
            }), 200
        # A remote cannot be fully inspected without cloning; that happens at install.
        return jsonify({
            "status_code": "success",
            "check_state": "valid",
            "source_type": source_type,
            "country_id": data["country_id"],
            "country_name": data["country_name"],
            "repo_url": repo_url,
            "detected": {"repo_name": repo_name_from_url(repo_url)},
            "warnings": ["The repository is fully validated during install."],
        }), 200

    return _err("source_type must be one of: catalog, repo_url, local_path.")


# ── 4. install from catalog or Git URL ───────────────────────────────────────
@ogcore_install_api.route("/installCalibration", methods=["POST"])
def installCalibration():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = _body()
    if data is None:
        return _err("Request body must be valid JSON.")
    miss = _missing(data, "source_type", "country_id")
    if miss:
        return _err(f"Missing required field: {miss}")
    if not _valid_country_id(data["country_id"]):
        return _err("country_id must be a short code (letters, digits, - or _).")

    source_type = data["source_type"]
    dest_parent = _clean_path(data.get("dest_parent") or _default_dest_parent())
    if not dest_parent:
        return _err("dest_parent is not a valid path.")

    if source_type == "catalog":
        catalog_key = data.get("catalog_key")
        if not catalog_key:
            return _err("Missing required field: catalog_key")
        entry = CalibrationCatalog.find_entry(catalog_key)
        if entry is None:
            return _err(
                f"'{catalog_key}' is not in the installer catalogue. "
                "Use a Git URL instead, or try again when the catalogue is reachable.",
                http=404,
            )
        # Key the install by the catalogue's own country_id so the card that reads
        # the catalogue and the installed record always agree (no ETH/eth mismatch).
        country_id = entry["country_id"]
        job = InstallJob.start_install(
            source_type="catalog",
            country_id=country_id,
            country_name=data.get("country_name") or entry["country_name"],
            repo_name=repo_name_from_url(entry["repo_url"]),
            dest_parent=dest_parent,
            catalog_key=catalog_key,
            package_name=entry["package_name"],
        )

    elif source_type == "repo_url":
        country_id = data["country_id"]
        repo_url = data.get("repo_url")
        if not repo_url:
            return _err("Missing required field: repo_url")
        if not _GIT_URL_RE.match(repo_url.strip()):
            return _err("repo_url does not look like a Git URL.")
        country_name = data.get("country_name")
        if not country_name:
            return _err("Missing required field: country_name")
        job = InstallJob.start_install(
            source_type="repo_url",
            country_id=country_id,
            country_name=country_name,
            repo_name=repo_name_from_url(repo_url),
            dest_parent=dest_parent,
            repo_url=repo_url,
            branch=data.get("branch") or None,
            package_name=data.get("package_name") or None,
        )

    else:
        return _err("source_type must be 'catalog' or 'repo_url'.")

    if job is None:
        return _err("An install is already running for this country.")
    return jsonify({
        "status_code": "success",
        "install_id": job["install_id"],
        "install_state": job["install_state"],
        "message": "Calibration install started.",
    }), 200


# ── 5. register an existing local copy ───────────────────────────────────────
@ogcore_install_api.route("/registerLocalCalibration", methods=["POST"])
def registerLocalCalibration():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = _body()
    if data is None:
        return _err("Request body must be valid JSON.")
    miss = _missing(data, "country_id", "country_name", "local_path")
    if miss:
        return _err(f"Missing required field: {miss}")
    country_id = data["country_id"]
    if not _valid_country_id(country_id):
        return _err("country_id must be a short code (letters, digits, - or _).")
    local_path = _clean_path(data["local_path"])
    if not local_path:
        return _err("That path is not valid.")
    if not Path(local_path).is_dir():
        return _err("That folder does not exist.")

    run_uv_sync = data.get("run_uv_sync", True)
    job = InstallJob.start_local_register(
        country_id=country_id,
        country_name=data["country_name"],
        local_path=local_path,
        package_name=data.get("package_name") or None,
        run_uv_sync=bool(run_uv_sync),
    )
    if job is None:
        return _err("A registration is already running for this country.")
    return jsonify({
        "status_code": "success",
        "install_id": job["install_id"],
        "install_state": job["install_state"],
        "message": "Local calibration registration started.",
    }), 200


# ── 6. install/registration status ───────────────────────────────────────────
@ogcore_install_api.route("/getInstallStatus", methods=["GET"])
def getInstallStatus():
    install_id = request.args.get("install_id")
    if not install_id:
        return _err("Missing required query value: install_id")
    if not _INSTALL_ID_RE.match(install_id):
        return _err("Invalid install_id.")
    job = InstallJob.get_status(install_id)
    if job is None:
        return _err("No install job with that id.", http=404)
    return jsonify({
        "status_code": "success",
        "install_id": job["install_id"],
        "country_id": job["country_id"],
        "country_name": job["country_name"],
        "install_state": job["install_state"],
        "install_stage": job["install_stage"],
        "progress_label": job["progress_label"],
        "local_path": job.get("local_path"),
        "log_tail": job.get("log_tail", []),
        "error": job.get("error"),
    }), 200


# ── 7. unregister ────────────────────────────────────────────────────────────
@ogcore_install_api.route("/unregisterCalibration", methods=["POST"])
def unregisterCalibration():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = _body()
    if data is None:
        return _err("Request body must be valid JSON.")
    miss = _missing(data, "country_id")
    if miss:
        return _err(f"Missing required field: {miss}")
    country_id = data["country_id"]
    if data.get("delete_local_files"):
        return _err(
            "Deleting the calibration's files is not supported in this version. "
            "Unregister removes only MUIOGO's record.",
        )
    if InstallJob.is_country_active(country_id):
        return _err("An install is still running for this country.")
    removed = CalibrationRegistry.remove(country_id)
    if removed is None:
        return _err("That calibration is not registered.", http=404)
    return jsonify({
        "status_code": "success",
        "country_id": country_id,
        "message": "Calibration unregistered.",
    }), 200


# ── 8. refresh / update ──────────────────────────────────────────────────────
@ogcore_install_api.route("/refreshCalibration", methods=["POST"])
def refreshCalibration():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = _body()
    if data is None:
        return _err("Request body must be valid JSON.")
    miss = _missing(data, "country_id")
    if miss:
        return _err(f"Missing required field: {miss}")
    country_id = data["country_id"]
    record = CalibrationRegistry.get(country_id)
    if record is None:
        return _err("That calibration is not registered.", http=404)

    check_only = data.get("check_only", True)
    local_path = record.get("local_path")

    # A locally-registered calibration is the user's own clone (possibly with
    # uncommitted work). Never git pull / rebuild over it automatically; a check is
    # fine, but applying an update must be the user's own action outside MUIOGO.
    if not check_only and record.get("source_type") == "local_path":
        return _err(
            "This calibration was registered from a local folder, so MUIOGO will not "
            "update it automatically. Update that clone yourself, then refresh."
        )

    if check_only:
        result = Installer.check_update(local_path)
        state = "update_available" if result["update_available"] else "installed"
        CalibrationRegistry.update_fields(
            country_id, install_state=state, last_checked_at=_now_iso(),
        )
        message = (
            "A newer version is available."
            if result["update_available"]
            else "This calibration is up to date."
        )
        return jsonify({
            "status_code": "success",
            "country_id": country_id,
            "install_state": state,
            "local_commit_sha": result["local_commit_sha"],
            "remote_commit_sha": result["remote_commit_sha"],
            "message": message,
        }), 200

    # Apply an update: re-run the installer over the existing clone (pull + uv sync).
    repo_url = record.get("repo_url")
    if not repo_url:
        return _err(
            "This calibration has no known Git remote, so it cannot be updated "
            "automatically. Re-register it from a Git URL or a fresh clone.",
        )
    if InstallJob.is_country_active(country_id):
        return _err("An update is already running for this country.")
    path = Path(local_path)
    job = InstallJob.start_install(
        source_type="repo_url",
        country_id=country_id,
        country_name=record.get("country_name") or country_id,
        repo_name=path.name,
        dest_parent=str(path.parent),
        repo_url=repo_url,
        package_name=record.get("package_name"),
    )
    if job is None:
        return _err("An update is already running for this country.")
    return jsonify({
        "status_code": "success",
        "install_id": job["install_id"],
        "install_state": job["install_state"],
        "message": "Calibration update started.",
    }), 200

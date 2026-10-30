"""OG-CLEWS link endpoints.

All routes live under /oglink. They are session-free by design (like /run and
/createCaseRun): the callers are headless -- the oglink CLI, the post-run
hook, and MUIOGO-AI over HTTP -- and every request names its case explicitly.
No route here ever writes into a live case; patches land in case copies.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from Classes.Base import Config
from Classes.Base.FileClass import File
from Classes.OGLink.PatchApply import OGLinkPatch, OGLinkPatchError
from Classes.OGLink.PostRunHook import PostRunHook

oglink_api = Blueprint("OGLinkRoute", __name__, url_prefix="/oglink")

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _err(message, http=400, status="error", **extra):
    payload = {"message": message, "status_code": status}
    payload.update(extra)
    return jsonify(payload), http


def _blocked_cross_site():
    """Refuse a state-changing request driven cross-site from a browser; same
    rule as the OGCore install routes (non-browser callers send no Origin)."""
    origin = request.headers.get("Origin")
    if origin:
        host = urlparse(origin).hostname
        if host not in _LOCAL_HOSTS:
            return _err("Cross-site request refused.", http=403)
    return None


@oglink_api.route("/applyPatch", methods=["POST"])
def applyPatch():
    """Materialize a clews_patch.json into a solved caserun of a case copy.

    Body: {"patch": {...}} or {"patch_path": "/abs/path/clews_patch.json"},
    plus "base_caserun" (required; the caserun whose scenario set the new run
    clones), and optional "caserun_name", "copy_name", "solver" (default CBC),
    "overwrite_copy". Solves synchronously, like /run.
    """
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")

    patch = data.get("patch")
    patch_path = data.get("patch_path")
    if patch is None and patch_path:
        if "\x00" in str(patch_path):
            return _err("patch_path is not a valid path.")
        path = Path(os.path.abspath(os.path.normpath(str(patch_path))))
        if not path.is_file():
            return _err(f"patch_path does not exist: {path}", http=404)
        try:
            patch = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return _err(f"patch_path is not readable JSON: {exc}")
    if not isinstance(patch, dict):
        return _err("Provide the patch inline ('patch') or as a file "
                    "('patch_path').")

    base_caserun = data.get("base_caserun")
    if not base_caserun:
        return _err("Missing required field: base_caserun")

    try:
        result = OGLinkPatch.apply(
            patch,
            base_caserun,
            caserun_name=data.get("caserun_name") or None,
            copy_name=data.get("copy_name") or None,
            solver=data.get("solver") or "CBC",
            overwrite_copy=bool(data.get("overwrite_copy")),
        )
    except OGLinkPatchError as exc:
        return _err(exc.message, http=exc.http, **exc.details)
    except PermissionError as exc:  # Config.validate_path on a hostile name
        return _err(str(exc))
    except ValueError as exc:  # a non-numeric change value
        return _err(str(exc))

    result["status_code"] = "success"
    result["message"] = "Patch applied and solved."
    return jsonify(result), 200


def _case_dir(casename):
    """Validated case dir, or None (caller returns a 400/404)."""
    if not casename:
        return None
    try:
        Config.validate_path(Config.DATA_STORAGE, casename)
    except PermissionError:
        return None
    path = Path(Config.DATA_STORAGE, casename)
    return path if (path / "genData.json").is_file() else None


@oglink_api.route("/status", methods=["GET"])
def status():
    """Is the OG-CLEWS linker (oglink) installed and resolvable? The capability check the
    UI reads before offering coupled-run actions. ?deep=1 additionally asks
    the link which OG models it has registered (a subprocess, ~seconds)."""
    info = PostRunHook.status()
    if info["installed"] and request.args.get("deep") in ("1", "true"):
        info.update(PostRunHook.models_check(info["python"], info["home"]))
    info["status_code"] = "success"
    return jsonify(info), 200


@oglink_api.route("/runs", methods=["GET"])
def runs():
    """The case's registered OG-link runs (the 'oglink-runs' key the post-run
    hook maintains in view/resData.json)."""
    case_dir = _case_dir(request.args.get("case"))
    if case_dir is None:
        return _err("Pass a valid ?case=<name>.", http=404)
    res_data_path = case_dir / "view" / "resData.json"
    res_data = File.readFile(res_data_path) if res_data_path.is_file() else {}
    return jsonify({"status_code": "success",
                    "runs": res_data.get("oglink-runs", [])}), 200


# hook.json fields a POST may set, with their type checks.
_HOOK_FIELDS = {
    "enabled": lambda v: isinstance(v, bool),
    "experiment": lambda v: isinstance(v, str) and v.strip(),
    "base_caserun": lambda v: isinstance(v, str) and v.strip(),
    "country": lambda v: v is None or (isinstance(v, str) and v.strip()),
    "workers": lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0,
    "timeout_s": lambda v: isinstance(v, int) and not isinstance(v, bool) and v > 0,
    "out": lambda v: v is None or (isinstance(v, str) and "\x00" not in v),
    "extra_args": lambda v: isinstance(v, list) and all(isinstance(a, str) for a in v),
}


@oglink_api.route("/hookConfig", methods=["GET", "POST"])
def hookConfig():
    """Read or write a case's <case>/oglink/hook.json (the post-run hook's
    opt-in config), so the UI never hand-edits files."""
    if request.method == "GET":
        case_dir = _case_dir(request.args.get("case"))
        if case_dir is None:
            return _err("Pass a valid ?case=<name>.", http=404)
        cfg_path = case_dir / "oglink" / "hook.json"
        if not cfg_path.is_file():
            return jsonify({"status_code": "success", "configured": False,
                            "config": None}), 200
        return jsonify({"status_code": "success", "configured": True,
                        "config": File.readFile(cfg_path)}), 200

    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case_dir = _case_dir(data.get("case"))
    if case_dir is None:
        return _err("Missing or unknown 'case'.", http=404)
    config = data.get("config")
    if not isinstance(config, dict):
        return _err("Missing required field: config (an object).")
    unknown = sorted(set(config) - set(_HOOK_FIELDS))
    if unknown:
        return _err(f"Unknown config fields: {unknown}. "
                    f"Allowed: {sorted(_HOOK_FIELDS)}")
    for field, valid in _HOOK_FIELDS.items():
        if field in config and not valid(config[field]):
            return _err(f"Config field {field!r} has an invalid value.")
    for required in ("experiment", "base_caserun"):
        if not config.get(required):
            return _err(f"Config must set {required!r}.")
    (case_dir / "oglink").mkdir(exist_ok=True)
    File.writeFile(config, case_dir / "oglink" / "hook.json")
    warnings = []
    if not (case_dir / "res" / config["base_caserun"] / "csv").is_dir():
        warnings.append(f"base caserun {config['base_caserun']!r} has no solved "
                        "results yet; the hook will skip until it is solved")
    return jsonify({"status_code": "success", "configured": True,
                    "config": config, "warnings": warnings,
                    "message": "Hook configured."}), 200

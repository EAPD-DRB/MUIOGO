"""OG-Core case and run endpoints (disk CRUD only).

All routes live under /ogc. They wrap OGCoreCase, which owns the on-disk case/run
layout; nothing here executes OG-Core or imports the ogcore package. Model runs
happen in a separate OG environment driven by the worker layer.
"""
import csv
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from flask import (
    Blueprint,
    after_this_request,
    jsonify,
    request,
    send_file,
    session,
)

from Classes.Base import Config
from Classes.Base.FileClass import File
from Classes.OGCore import OGSchema, OGTables
from Classes.OGCore.CalibrationRegistry import CalibrationRegistry
from Classes.OGCore.OGCoreCase import OGCoreCase, is_safe_name
from Classes.OGCore.OGResults import OGResults
from Classes.OGCore.OGRunner import kill_worker_tree
from Classes.OGCore.RunJob import RunJob

ogcore_run_api = Blueprint("OGCoreRunRoute", __name__, url_prefix="/ogc")

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


# ── small helpers (local copies of the installer route's, do not modify those) ─
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


def _missing(data, *fields):
    """First field absent from the body, or None."""
    for field in fields:
        if field not in data:
            return field
    return None


def _unsafe_name(*names):
    """Error response if any name is unsafe as a path component, else None.

    Every casename/run_name becomes a directory under OGC_CASES_DIR, so each one
    is checked before any Path is built from it. Blocks traversal like '..' and
    separator characters at the door.
    """
    for name in names:
        if not is_safe_name(name):
            return _err("Invalid name.")
    return None


def _active_country_guard():
    """Keep every case-addressed route inside the backend workspace country.

    The frontend may activate a country before selecting an individual case. Once
    active, the guard is blueprint-wide so a forgotten check on a new read/write
    route cannot expose another country's case by casename.
    """
    active_country = session.get("ogccountry")
    data = request.get_json(silent=True)
    casename = None
    requested_country = None
    if isinstance(data, dict):
        casename = data.get("casename")
        requested_country = data.get("country_id")
        nested = data.get("data")
        if isinstance(nested, dict):
            casename = casename or nested.get("ogc-casename")
            requested_country = requested_country or nested.get("country_id")
    casename = casename or request.args.get("casename") or request.form.get("casename")
    requested_country = (
        requested_country
        or request.args.get("country_id")
        or request.form.get("country_id")
    )
    endpoint = (request.endpoint or "").rsplit(".", 1)[-1]
    if endpoint == "setSession":
        return None
    if not active_country:
        # Discovery and the explicit activation route work outside a workspace.
        # New case names may also proceed to saveCase, which validates and records
        # their country. Existing case data is fail-closed until setSession activates
        # its country, so losing/clearing the session cannot expose a known case.
        if not casename or not is_safe_name(casename):
            return None
        if not requested_country or not is_safe_name(requested_country):
            return None
        if not OGCoreCase(requested_country, casename).case_path.is_dir():
            return None
        return _err("Open that country workspace before accessing this case.", http=403)
    if requested_country and requested_country != active_country:
        return _err(
            "Unauthorised: case country does not match the active workspace.",
            http=403,
        )
    if not casename or not is_safe_name(casename):
        return None
    case = OGCoreCase(active_country, casename)
    if not case.case_path.is_dir():
        return None
    try:
        case_country = case.country_id
    except (OSError, ValueError, KeyError, IndexError):
        return None
    if case_country != active_country:
        return _err(
            "Unauthorised: case country does not match the active workspace.",
            http=403,
        )
    return None


@ogcore_run_api.before_request
def guard_active_country():
    return _active_country_guard()


def _utc_now_z():
    """ISO-8601 UTC timestamp with a trailing Z, seconds precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── active workspace country and optional active case ─────────────────────────
def _set_active_case(country_id, casename):
    session["ogccase"] = casename
    session["ogccountry"] = country_id


def _clear_active_case():
    session["ogccase"] = None


def _active_case():
    """The active workspace country and its optional selected case."""
    return session.get("ogccountry") or None, session.get("ogccase") or None


def _resolve_case(data, *also_required):
    """(case, error) for the country_id/casename pair in a request body.

    also_required names further fields to check. Fields are reported in the order
    given, so the caller decides which missing one is named first.
    """
    miss = _missing(data, "country_id", "casename", *also_required)
    if miss:
        return None, _err(f"Missing required field: {miss}")
    bad = _unsafe_name(data["country_id"], data["casename"])
    if bad:
        return None, bad
    return OGCoreCase(data["country_id"], data["casename"]), None


# The worker reads a run's parameters when it launches, not when the run is queued,
# so a write after submission would either silently disagree with a finished run's
# results or slip past the dimension guard a queued run already passed.
_BUSY_PARAMS_MESSAGE = (
    "That run is running or queued; its parameters cannot be changed until it finishes."
)

# A case backup carries a run's full results, so it is legitimately large. These
# cap the upload itself, and separately what a small archive may expand into.
_MAX_BACKUP_BYTES = 512 * 1024 * 1024
_MAX_BACKUP_UNPACKED_BYTES = 2 * 1024 * 1024 * 1024


# ── 1. read active-case session ──────────────────────────────────────────────
@ogcore_run_api.route("/getSession", methods=["GET"])
def getSession():
    return jsonify({
        "ogccase": session.get("ogccase") or None,
        "ogccountry": session.get("ogccountry") or None,
    }), 200


# ── 2. set active-case session ───────────────────────────────────────────────
@ogcore_run_api.route("/setSession", methods=["POST"])
def setSession():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    if "casename" not in data:
        return _err("Missing required field: casename")
    casename = data["casename"]
    if casename is None:
        session.pop("ogccase", None)
        country_id = data.get("country_id")
        if country_id is None:
            session.pop("ogccountry", None)
            return jsonify({"ogccase": None, "ogccountry": None}), 200
        if CalibrationRegistry.get(country_id) is None:
            return _err("That country calibration is not installed.")
        active_country = session.get("ogccountry")
        if active_country and active_country != country_id:
            return _err(
                "Exit the active country workspace before opening another.", http=409
            )
        session["ogccountry"] = country_id
        return jsonify({"ogccase": None, "ogccountry": country_id}), 200
    if "country_id" not in data:
        return _err("Missing required field: country_id")
    country_id = data["country_id"]
    if not is_safe_name(casename) or not is_safe_name(country_id):
        return _err("Invalid case name.")
    active_country = session.get("ogccountry")
    if active_country and active_country != country_id:
        return _err(
            "Exit the active country workspace before opening another.", http=409
        )
    if not OGCoreCase(country_id, casename).case_path.is_dir():
        return _err("Case not found.", http=404)
    _set_active_case(country_id, casename)
    return jsonify({"ogccase": casename, "ogccountry": country_id}), 200


# ── 3. list cases ────────────────────────────────────────────────────────────
@ogcore_run_api.route("/getCases", methods=["GET"])
def getCases():
    active_country = session.get("ogccountry")
    country_id = request.args.get("country_id")
    if country_id is not None and not is_safe_name(country_id):
        return _err("Invalid country id.")
    return jsonify(OGCoreCase.list_cases(country_id=active_country or country_id)), 200


# ── 4. create or edit a case ─────────────────────────────────────────────────
@ogcore_run_api.route("/saveCase", methods=["POST"])
def saveCase():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    body = request.get_json(silent=True)
    if body is None:
        return _err("Request body must be valid JSON.")
    data = body.get("data")
    if not isinstance(data, dict):
        return _err("Missing required field: data")
    name = data.get("ogc-casename")
    if not name:
        return _err("Missing required field: ogc-casename")
    country_id = data.get("country_id")
    if not country_id:
        return _err("Missing required field: country_id")
    if not is_safe_name(name):
        return _err("Invalid case name.")
    if not is_safe_name(country_id):
        return _err("Invalid country id.")
    data.setdefault("ogc-description", "")

    case = OGCoreCase(country_id, name)
    if not case.case_path.is_dir():
        # Create path: the country's calibration must be installed.
        if CalibrationRegistry.get(country_id) is None:
            return _err("That country calibration is not installed.")
        case.create_case(data)
        _set_active_case(country_id, name)
        return jsonify({"message": f"Case {name} created.", "status_code": "created"}), 200

    # Edit path: the country needs no check. Another one addresses a different case
    # entirely, and save_case pins genData to the directory a case was found in.
    case.save_case(data)
    return jsonify({"message": f"Case {name} updated.", "status_code": "edited"}), 200


# ── 5. delete a case ─────────────────────────────────────────────────────────
@ogcore_run_api.route("/deleteCase", methods=["POST"])
def deleteCase():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data)
    if err:
        return err
    casename = data["casename"]
    country_id = data["country_id"]

    active_country, active_case = _active_case()
    if active_case is None:
        return _err("No active session.", http=403)
    if (active_country, active_case) != (country_id, casename):
        return _err("Unauthorised: case does not match active session.", http=403)

    if not case.case_path.is_dir():
        return _err("Case not found.", http=404)
    if RunJob.case_busy(country_id, casename):
        return _err("A run in this case is running or queued; stop it first.")
    result = case.delete_case()
    _clear_active_case()
    return jsonify(result), 200


# ── 6. create a run ──────────────────────────────────────────────────────────
@ogcore_run_api.route("/createRun", methods=["POST"])
def createRun():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data, "run_name", "run_type")
    if err:
        return err
    run_name = data["run_name"]
    run_type = data["run_type"]
    bad = _unsafe_name(run_name)
    if bad:
        return bad

    if not case.case_path.is_dir():
        return _err("Case not found.", http=404)
    if run_type == "reform" and not data.get("baseline_run_name"):
        return _err("Missing required field: baseline_run_name")

    params = data.get("params")
    if params is not None and not isinstance(params, dict):
        return _err("params must be an object.")

    result = case.create_run(run_name, run_type, data.get("baseline_run_name"), params)
    sc = result.get("status_code")
    if sc == "error":
        return jsonify(result), 400
    if sc == "exist":
        return jsonify(result), 200
    return jsonify({"message": "Run created.", "status_code": "success"}), 200


# ── 7. list a case's runs ────────────────────────────────────────────────────
@ogcore_run_api.route("/getRuns", methods=["POST"])
def getRuns():
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data)
    if err:
        return err
    if not case.case_path.is_dir():
        return _err("Case not found.", http=404)
    shaped = case.get_runs_shaped()
    for item in ([shaped.get("baseline")] + shaped.get("reforms", [])):
        if not item:
            continue
        live = RunJob.get_live(
            data["country_id"], data["casename"], item["RunName"]
        )
        item["queue_position"] = live.get("queue_position") if live else None
        if live:
            item["status"] = "queued" if live.get("queued") else "running"
    return jsonify(shaped), 200


# ── 8. delete a run ──────────────────────────────────────────────────────────
@ogcore_run_api.route("/deleteRun", methods=["POST"])
def deleteRun():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data, "run_name")
    if err:
        return err
    casename = data["casename"]
    country_id = data["country_id"]
    run_name = data["run_name"]
    bad = _unsafe_name(run_name)
    if bad:
        return bad

    if not case.case_path.is_dir():
        return _err("Case not found.", http=404)
    in_index = any(r.get("RunName") == run_name for r in case.gen_data.get("ogc-runs", []))
    if not in_index:
        return _err("Run not found.", http=404)
    # Deleting the baseline removes the whole case, so it has to clear the same
    # session gate deleteCase does; without it this is an unguarded case delete.
    if case.get_baseline_name() == run_name:
        active_country, active_case = _active_case()
        if active_case is None:
            return _err("No active session.", http=403)
        if (active_country, active_case) != (country_id, casename):
            return _err("Unauthorised: case does not match active session.", http=403)
    if RunJob.case_busy(country_id, casename) and (
        RunJob.is_busy(country_id, casename, run_name)
        or case.get_baseline_name() == run_name
    ):
        return _err("That run is running or queued; stop it first.")

    result = case.delete_run(run_name)
    if result.get("status_code") == "success_session":
        _clear_active_case()
    return jsonify(result), 200


# ── 9. read a run's parameters ───────────────────────────────────────────────
@ogcore_run_api.route("/getParams", methods=["POST"])
def getParams():
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data, "run_name")
    if err:
        return err
    bad = _unsafe_name(data["run_name"])
    if bad:
        return bad
    run_dir = case.res_path / data["run_name"]
    if not run_dir.is_dir():
        return _err("Run not found.", http=404)
    return jsonify(case.get_params(data["run_name"])), 200


# ── 10. save a run's parameters ──────────────────────────────────────────────
@ogcore_run_api.route("/saveParams", methods=["POST"])
def saveParams():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data, "run_name", "params")
    if err:
        return err
    params = data["params"]
    if not isinstance(params, dict):
        return _err("params must be an object.")
    bad = _unsafe_name(data["run_name"])
    if bad:
        return bad
    run_dir = case.res_path / data["run_name"]
    if not run_dir.is_dir():
        return _err("Run not found.", http=404)
    result = RunJob.save_params(
        data["country_id"], data["casename"], data["run_name"], params
    )
    if result.get("status_code") == "error":
        return _err(result.get("message") or _BUSY_PARAMS_MESSAGE)
    return jsonify({"message": "Parameters saved.", "status_code": "success"}), 200


def _run_log_tail(case, run_name, n=50):
    """Last ``n`` lines of a run's persisted run_log.txt, or [] if none/unreadable."""
    path = case.res_path / run_name / "run_log.txt"
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    return lines[-n:]


# ── 11. start (or queue) a model run ─────────────────────────────────────────
@ogcore_run_api.route("/run", methods=["POST"])
def run():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data, "run_name", "time_path")
    if err:
        return err
    country_id = data["country_id"]
    casename = data["casename"]
    run_name = data["run_name"]
    time_path = data["time_path"]
    if not isinstance(time_path, bool):
        return _err("time_path must be a boolean.")
    bad = _unsafe_name(run_name)
    if bad:
        return bad

    if not case.case_path.is_dir():
        return _err("Case not found.", http=404)
    in_index = any(
        r.get("RunName") == run_name for r in case.gen_data.get("ogc-runs", [])
    )
    if not in_index:
        return _err("Run not found.", http=404)

    result = RunJob.start(country_id, casename, run_name, time_path)
    if result.get("status_code") == "error":
        return jsonify(result), 400
    return jsonify(result), 200


# ── 12. read a run's live execution status ───────────────────────────────────
@ogcore_run_api.route("/getRunStatus", methods=["POST"])
def getRunStatus():
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data, "run_name")
    if err:
        return err
    country_id = data["country_id"]
    casename = data["casename"]
    run_name = data["run_name"]
    bad = _unsafe_name(run_name)
    if bad:
        return bad

    meta = case.get_run_meta(run_name)
    if not meta:
        return _err("Run not found.", http=404)

    live = RunJob.get_live(country_id, casename, run_name)
    run_state = meta.get("status")
    # A persisted active/queued state without in-memory ownership was orphaned by a
    # restart (including WSGI startup paths that skip reconcile). Repair truthfully.
    if run_state in ("running", "queued") and live is None:
        # Re-read first: the run may have finished between the read above and the
        # live check, and marking a completed run failed would lose it.
        meta = case.get_run_meta(run_name)
        run_state = meta.get("status")
        if run_state in ("running", "queued"):
            # This is also the only repair path under a WSGI loader, which never runs
            # the startup reconcile, so kill the orphan before its pid is cleared.
            was_running = run_state == "running"
            if was_running:
                kill_worker_tree(meta.get("pid"), case.res_path / run_name)
            case.update_run_status(
                run_name, "failed",
                error=(
                    "Run was interrupted by an application restart."
                    if was_running
                    else "Queued run was interrupted by an application restart before it started."
                ),
            )
            meta = case.get_run_meta(run_name)
            run_state = meta.get("status")

    if live:
        run_state = "queued" if live.get("queued") else "running"
        run_stage = live.get("stage_label") or (
            "Queued" if live.get("queued") else None
        )
        run_iteration = live.get("iteration") or None
        run_log = live.get("log_tail")
        queue_position = live.get("queue_position")
        queue_length = live.get("queue_length")
    else:
        run_stage = None
        run_iteration = None
        run_log = _run_log_tail(case, run_name)
        queue_position = None
        queue_length = 0

    return jsonify({
        "status_code": "success",
        "run_state": run_state,
        "run_stage": run_stage,
        "run_iteration": run_iteration,
        "run_log": run_log,
        "queue_position": queue_position,
        "queue_length": queue_length,
        "reusable": case.is_run_reusable(run_name),
        # Carried here as well as on getRuns: this is the endpoint a client polls, so
        # without it a run that fails mid-poll reads as failed with no reason given.
        "error": meta.get("error"),
    }), 200


@ogcore_run_api.route("/getRunQueue", methods=["POST"])
def getRunQueue():
    """Current in-process FIFO ownership for Run-page reconstruction."""
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data)
    if err:
        return err
    if not case.case_path.is_dir():
        return _err("Case not found.", http=404)
    snapshot = RunJob.get_queue_snapshot(data["country_id"], data["casename"])
    return jsonify({"status_code": "success", **snapshot}), 200


# ── 13. cancel a running or queued run ───────────────────────────────────────
@ogcore_run_api.route("/cancelRun", methods=["POST"])
def cancelRun():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data, "run_name")
    if err:
        return err
    country_id = data["country_id"]
    casename = data["casename"]
    run_name = data["run_name"]
    bad = _unsafe_name(run_name)
    if bad:
        return bad

    result = RunJob.cancel(country_id, casename, run_name)
    if result.get("status_code") == "cancelled":
        return jsonify({"status_code": "cancelled"}), 200
    return jsonify(result), 400


# ── results: shared validation ───────────────────────────────────────────────
def _bad_vars(vars_arg):
    """Error response if an optional ``vars`` field is present but not a list of
    strings, else None. Absent (None) is always fine."""
    if vars_arg is None:
        return None
    if not isinstance(vars_arg, list) or not all(isinstance(v, str) for v in vars_arg):
        return _err("vars must be a list of strings.")
    return None


# ── 14. read a run's steady-state variables ──────────────────────────────────
@ogcore_run_api.route("/getSSVars", methods=["POST"])
def getSSVars():
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data, "run_name")
    if err:
        return err
    country_id = data["country_id"]
    casename = data["casename"]
    run_name = data["run_name"]
    bad = _unsafe_name(run_name)
    if bad:
        return bad
    vars_arg = data.get("vars")
    bad_vars = _bad_vars(vars_arg)
    if bad_vars:
        return bad_vars

    meta = case.get_run_meta(run_name)
    if not meta:
        return _err("Run not found.", http=404)
    if meta.get("status") != "completed":
        return _err("No results - run it first", http=404)
    ss = OGResults.load_ss(case.res_path / run_name)
    if ss is None:
        return _err("No results - run it first", http=404)
    return jsonify(OGResults.subset(ss, vars_arg)), 200


# ── 15. read a run's transition-path variables ───────────────────────────────
@ogcore_run_api.route("/getTPIVars", methods=["POST"])
def getTPIVars():
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data, "run_name")
    if err:
        return err
    country_id = data["country_id"]
    casename = data["casename"]
    run_name = data["run_name"]
    bad = _unsafe_name(run_name)
    if bad:
        return bad
    vars_arg = data.get("vars")
    bad_vars = _bad_vars(vars_arg)
    if bad_vars:
        return bad_vars

    meta = case.get_run_meta(run_name)
    if not meta:
        return _err("Run not found.", http=404)
    if meta.get("status") != "completed":
        return _err("No results - run it first", http=404)
    tpi = OGResults.load_tpi(case.res_path / run_name)
    if tpi is None:
        return _err("No transition path results for this run.", http=404)
    return jsonify(OGResults.subset(tpi, vars_arg)), 200


def _results_gate(case, run_name):
    """None if the run has usable results, else the response to return now.

    A run in progress or queued returns the running envelope; a failed run or one
    with no results returns the error envelope; a missing meta is a 404. Both
    envelopes carry the casename so the dashboard can key its state to the case.
    """
    meta = case.get_run_meta(run_name)
    if not meta:
        return _err("Run not found.", http=404)
    status = meta.get("status")
    # "In progress" means the run is actually active or queued right now. A run
    # that is merely pending (created but never started) has no results to wait
    # for, so it gets the run-it-first envelope, not a spinner.
    if RunJob.is_busy(case.country_id, case.casename, run_name):
        return jsonify({
            "status_code": "running",
            "casename": case.casename,
            "message": "Solve in progress",
        }), 200
    if status != "completed":
        return jsonify({
            "status_code": "error",
            "casename": case.casename,
            "message": "No results - run it first",
        }), 404
    return None


# ── 16. read the consolidated results object ──────────────────────────────────
@ogcore_run_api.route("/getResults", methods=["POST"])
def getResults():
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data, "base_run")
    if err:
        return err
    casename = data["casename"]
    base_run = data["base_run"]
    reform_run = data.get("reform_run")
    names = [base_run]
    if reform_run is not None:
        names.append(reform_run)
    bad = _unsafe_name(*names)
    if bad:
        return bad

    if not case.case_path.is_dir():
        return _err("Case not found.", http=404)

    gate = _results_gate(case, base_run)
    if gate:
        return gate
    if reform_run is not None:
        gate = _results_gate(case, reform_run)
        if gate:
            return gate

    base_dir = case.res_path / base_run
    reform_dir = case.res_path / reform_run if reform_run is not None else None
    payload, err = OGResults.consolidated(
        casename, base_run, reform_run, base_dir, reform_dir
    )
    if err is not None:
        message, http = err
        return jsonify({
            "status_code": "error",
            "casename": casename,
            "message": message,
        }), http
    return jsonify(payload), 200


# ── analysis tables: shared endpoint ─────────────────────────────────────────
def _table_endpoint(table_key):
    """Serve one OG-Core analysis table built by the worker.

    Validates the request against the table's TABLES spec, gates on the run(s)
    having usable results, then spawns the worker's tables mode and returns the
    list of row objects it produced. A worker failure surfaces as a 502.
    """
    worker_key, reform_required, allowed = OGTables.TABLES[table_key]

    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data, "base_run")
    if err:
        return err
    base_run = data["base_run"]
    reform_run = data.get("reform_run")
    if reform_required and not reform_run:
        return _err("This table requires a reform run.")

    names = [base_run]
    if reform_run is not None:
        names.append(reform_run)
    bad = _unsafe_name(*names)
    if bad:
        return bad

    # Only whitelisted, present, non-null option fields pass through.
    options = {}
    for key in allowed:
        if key in data and data[key] is not None:
            options[key] = data[key]

    # OG-Core's macro table defaults to percent-change output, which asserts on
    # reform data. A baseline-only request is only meaningful as levels, so that
    # becomes the default when no reform is selected (the caller can still say
    # otherwise explicitly and get OG-Core's own refusal).
    if table_key == "macro" and reform_run is None and "output_type" not in options:
        options["output_type"] = "levels"

    if not case.case_path.is_dir():
        return _err("Case not found.", http=404)

    gate = _results_gate(case, base_run)
    if gate:
        return gate
    if reform_run is not None:
        gate = _results_gate(case, reform_run)
        if gate:
            return gate

    python_path, err = OGTables.resolve_python(case)
    if err:
        return _err(err)

    base_dir = case.res_path / base_run
    reform_dir = case.res_path / reform_run if reform_run is not None else None
    argv = OGTables.table_args(table_key, base_dir, reform_dir, options)
    payload, werr = OGTables.run_worker_mode(python_path, argv)
    if werr is not None:
        return jsonify({"message": werr, "status_code": "error"}), 502

    rows = payload.get("rows") if isinstance(payload, dict) else None
    if rows is None:
        return jsonify(
            {"message": "The table result was malformed.", "status_code": "error"}
        ), 502
    if reform_run is None:
        rows = OGTables.relabel_single_run(rows, base_run)
    return jsonify(rows), 200


@ogcore_run_api.route("/getMacroTable", methods=["POST"])
def getMacroTable():
    return _table_endpoint("macro")


@ogcore_run_api.route("/getMacroTableSS", methods=["POST"])
def getMacroTableSS():
    return _table_endpoint("macro_ss")


@ogcore_run_api.route("/getIneqTable", methods=["POST"])
def getIneqTable():
    return _table_endpoint("ineq")


@ogcore_run_api.route("/getGiniTable", methods=["POST"])
def getGiniTable():
    return _table_endpoint("gini")


@ogcore_run_api.route("/getWealthMomentsTable", methods=["POST"])
def getWealthMomentsTable():
    return _table_endpoint("wealth_moments")


@ogcore_run_api.route("/getTimeSeriesTable", methods=["POST"])
def getTimeSeriesTable():
    return _table_endpoint("time_series")


@ogcore_run_api.route("/getRevenueDecomposition", methods=["POST"])
def getRevenueDecomposition():
    return _table_endpoint("revenue_decomp")


# ── validate a run's parameters against OG-Core's own rules ───────────────────
@ogcore_run_api.route("/validateParams", methods=["POST"])
def validateParams():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = request.get_json(silent=True)
    if data is None:
        return _err("Request body must be valid JSON.")
    case, err = _resolve_case(data, "run_name")
    if err:
        return err
    country_id = data["country_id"]
    casename = data["casename"]
    run_name = data["run_name"]
    bad = _unsafe_name(run_name)
    if bad:
        return bad

    run_dir = case.res_path / run_name
    if not run_dir.is_dir():
        return _err("Run not found.", http=404)

    python_path, err = OGTables.resolve_python(case)
    if err:
        return _err(err)

    payload, werr = OGTables.run_worker_mode(
        python_path, ["validate", "--run-dir", str(run_dir)]
    )
    if werr is not None:
        return jsonify({"message": werr, "status_code": "error"}), 502
    return jsonify(payload), 200


# ── upload a run's tax-function parameter pickle ─────────────────────────────
@ogcore_run_api.route("/uploadTaxParams", methods=["POST"])
def uploadTaxParams():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked

    country_id = request.form.get("country_id")
    casename = request.form.get("casename")
    run_name = request.form.get("run_name")
    if not country_id or not casename or not run_name:
        return _err(
            "Missing required field: country_id, casename and run_name are required."
        )
    bad = _unsafe_name(country_id, casename, run_name)
    if bad:
        return bad

    case = OGCoreCase(country_id, casename)
    run_dir = case.res_path / run_name
    if not run_dir.is_dir():
        return _err("Run not found.", http=404)
    if RunJob.is_busy(country_id, casename, run_name):
        return _err(_BUSY_PARAMS_MESSAGE)

    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return _err("No file uploaded.")
    if not upload.filename.lower().endswith(".pkl"):
        return _err("The tax parameter file must be a .pkl file.")

    max_bytes = 16 * 1024 * 1024
    if request.content_length is not None and request.content_length > max_bytes:
        return _err("The uploaded file is too large (max 16MB).", http=413)

    python_path, err = OGTables.resolve_python(case)
    if err:
        return _err(err)

    fd, tmp_path = tempfile.mkstemp(suffix=".pkl")
    os.close(fd)
    try:
        upload.save(tmp_path)
        payload, werr = OGTables.run_worker_mode(
            python_path, ["taxcheck", "--file", tmp_path]
        )
        if werr is not None:
            return jsonify({"message": werr, "status_code": "error"}), 502
        if not payload.get("valid"):
            return jsonify({
                "message": payload.get("message") or "Invalid tax parameter file.",
                "status_code": "error",
            }), 400

        tax_func_type = payload.get("tax_func_type")
        def publish_tax_params():
            nonlocal tmp_path
            try:
                os.replace(tmp_path, run_dir / "ogcTaxParams.pkl")
            except OSError:
                # The temp dir can sit on a different drive than DataStorage.
                import shutil

                shutil.move(tmp_path, run_dir / "ogcTaxParams.pkl")
            tmp_path = None  # moved into place; do not delete in finally
            File.writeFile(
                {"tax_func_type": tax_func_type, "uploaded_at": _utc_now_z()},
                run_dir / "ogcTaxParams.info.json",
            )

        result = RunJob.commit_parameter_change(
            country_id, casename, run_name, publish_tax_params
        )
        if result.get("status_code") == "error":
            return _err(result.get("message") or _BUSY_PARAMS_MESSAGE)
        return jsonify({
            "message": "Tax params loaded.",
            "tax_func_type": tax_func_type,
            "status_code": "success",
        }), 200
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ── read the stored tax-params info sidecar ──────────────────────────────────
@ogcore_run_api.route("/getTaxParamsInfo", methods=["GET"])
def getTaxParamsInfo():
    country_id = request.args.get("country_id")
    casename = request.args.get("casename")
    run_name = request.args.get("run_name")
    if not country_id or not casename or not run_name:
        return _err(
            "Missing required field: country_id, casename and run_name are required."
        )
    bad = _unsafe_name(country_id, casename, run_name)
    if bad:
        return bad

    case = OGCoreCase(country_id, casename)
    info_path = case.res_path / run_name / "ogcTaxParams.info.json"
    if not info_path.exists():
        return jsonify({"loaded": False}), 200
    try:
        info = File.readFile(info_path)
    except (OSError, ValueError, IndexError):
        return jsonify({"loaded": False}), 200
    return jsonify({
        "loaded": True,
        "tax_func_type": info.get("tax_func_type"),
        "uploaded_at": info.get("uploaded_at"),
    }), 200


# ── download the macro comparison table as a CSV file ────────────────────────
@ogcore_run_api.route("/downloadResults", methods=["GET"])
def downloadResults():
    country_id = request.args.get("country_id")
    casename = request.args.get("casename")
    base_run = request.args.get("base_run")
    reform_run = request.args.get("reform_run")
    if not country_id or not casename or not base_run:
        return _err(
            "Missing required field: country_id, casename and base_run are required."
        )

    names = [country_id, casename, base_run]
    if reform_run is not None:
        names.append(reform_run)
    bad = _unsafe_name(*names)
    if bad:
        return bad

    case = OGCoreCase(country_id, casename)
    if not case.case_path.is_dir():
        return _err("Case not found.", http=404)

    gate = _results_gate(case, base_run)
    if gate:
        return gate
    if reform_run is not None:
        gate = _results_gate(case, reform_run)
        if gate:
            return gate

    python_path, err = OGTables.resolve_python(case)
    if err:
        return _err(err)

    base_dir = case.res_path / base_run
    reform_dir = case.res_path / reform_run if reform_run is not None else None
    # Baseline-only downloads must be levels; percent change needs a reform.
    options = {} if reform_run is not None else {"output_type": "levels"}
    argv = OGTables.table_args("macro", base_dir, reform_dir, options)
    payload, werr = OGTables.run_worker_mode(python_path, argv)
    if werr is not None:
        return jsonify({"message": werr, "status_code": "error"}), 502

    rows = payload.get("rows") if isinstance(payload, dict) else None
    if not rows:
        return jsonify(
            {"message": "No results to download.", "status_code": "error"}
        ), 502

    if reform_run is None:
        rows = OGTables.relabel_single_run(rows, base_run)

    # Header is the union of row keys in first-appearance order (first row first).
    header = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                header.append(key)

    fd, csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
    except OSError:
        try:
            os.unlink(csv_path)
        except OSError:
            pass
        return jsonify(
            {"message": "Failed to build the download.", "status_code": "error"}
        ), 500

    @after_this_request
    def _cleanup(response):
        try:
            os.unlink(csv_path)
        except OSError:
            pass
        return response

    return send_file(
        csv_path,
        as_attachment=True,
        download_name=f"{casename}_{base_run}_results.csv",
        mimetype="text/csv",
    )


# ── parameter form metadata for the active/selected case ─────────────────────
@ogcore_run_api.route("/getParameterSchema", methods=["GET"])
def getParameterSchema():
    # Both halves fall back to the session together: a country from the query with a
    # name from the session would address a case the caller never asked for.
    session_country, session_case = _active_case()
    casename = request.args.get("casename")
    country_id = request.args.get("country_id")
    if not casename:
        country_id, casename = session_country, session_case
    if not casename or not country_id:
        return _err("No case selected.")
    bad = _unsafe_name(country_id, casename)
    if bad:
        return bad
    case = OGCoreCase(country_id, casename)
    if not case.case_path.is_dir():
        return _err("Case not found.", http=404)

    schema, error = OGSchema.build_schema(case)
    if error is not None:
        # Only the missing-definitions case is a 404; a not-installed calibration
        # is a client-state problem the caller can fix by installing it.
        http = 404 if error == "The calibration's parameter definitions were not found." else 400
        return _err(error, http=http)
    return jsonify(schema), 200


# ── download the whole case directory as a zip backup ────────────────────────
@ogcore_run_api.route("/backupCase", methods=["GET"])
def backupCase():
    country_id = request.args.get("country_id")
    casename = request.args.get("casename")
    if not country_id or not casename:
        return _err("Missing required field: country_id and casename are required.")
    bad = _unsafe_name(country_id, casename)
    if bad:
        return bad

    case = OGCoreCase(country_id, casename)
    if not case.case_path.is_dir():
        return _err("Case not found.", http=404)

    fd, zip_path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Arcnames are relative to the case dir root (genData.json at the top),
            # so restoreCase can read genData.json straight from the archive root.
            for path in sorted(case.case_path.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(case.case_path).as_posix())
    except OSError:
        try:
            os.unlink(zip_path)
        except OSError:
            pass
        return jsonify(
            {"message": "Failed to build the backup.", "status_code": "error"}
        ), 500

    @after_this_request
    def _cleanup(response):
        try:
            os.unlink(zip_path)
        except OSError:
            pass
        return response

    return send_file(
        zip_path,
        as_attachment=True,
        download_name=f"{casename}_ogc_backup.zip",
        mimetype="application/zip",
    )


def _unsafe_zip_member(member) -> bool:
    """True if a zip member name is unsafe to extract under the case dir.

    Blocks absolute paths, Windows drive letters, and any parent-directory
    segment, after normalising backslash separators to forward slashes so a
    backslash-encoded traversal cannot slip past the segment check.
    """
    norm = member.replace("\\", "/")
    if norm.startswith("/"):
        return True
    if len(norm) >= 2 and norm[1] == ":":  # drive-letter prefix like "C:"
        return True
    return any(part == ".." for part in norm.split("/"))


# ── restore a case from a backup zip ─────────────────────────────────────────
@ogcore_run_api.route("/restoreCase", methods=["POST"])
def restoreCase():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked

    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return _err("No file uploaded.")
    if not upload.filename.lower().endswith(".zip"):
        return _err("The backup must be a .zip file.")
    if (request.content_length is not None
            and request.content_length > _MAX_BACKUP_BYTES):
        limit_mb = _MAX_BACKUP_BYTES // (1024 * 1024)
        return _err(f"The backup is too large (max {limit_mb}MB).", http=413)

    fd, tmp_path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    staging = None
    try:
        upload.save(tmp_path)
        try:
            zf = zipfile.ZipFile(tmp_path)
        except zipfile.BadZipFile:
            return _err("Not a valid backup file.")
        with zf:
            names = zf.namelist()
            # genData.json must sit at the archive root, exactly as backupCase writes it.
            if "genData.json" not in names:
                return _err("Not an OG-Core case backup.")
            try:
                gen_data = json.loads(zf.read("genData.json").decode("utf-8"))
            except (OSError, ValueError, zipfile.BadZipFile):
                return _err("Not an OG-Core case backup.")
            # A CLEWS backup carries osy-casename; only an OG-Core case has this key.
            if not isinstance(gen_data, dict) or "ogc-casename" not in gen_data:
                return _err("Not an OG-Core case backup.")

            target = gen_data.get("ogc-casename")
            if not is_safe_name(target):
                return _err("Invalid case name.")
            # A case is restored into the country it was backed up from. Backups
            # taken before cases were nested carry no country, so the caller has to
            # say which one it belongs to.
            country_id = gen_data.get("country_id") or request.form.get("country_id")
            if not country_id:
                return _err(
                    "This backup does not record a country; choose one and try again."
                )
            if not is_safe_name(country_id):
                return _err("Invalid country id.")
            target_dir = OGCoreCase(country_id, target).case_path
            if target_dir.exists():
                return jsonify(
                    {"message": "Case already exists.", "status_code": "exist"}
                ), 200

            # Validate every member before writing anything to disk.
            for member in names:
                if _unsafe_zip_member(member):
                    return _err("The backup contains unsafe paths.")

            # A small archive can still expand to fill the disk, so check the
            # declared uncompressed size before extracting anything.
            total = sum(info.file_size for info in zf.infolist())
            if total > _MAX_BACKUP_UNPACKED_BYTES:
                return _err("The backup expands to too much data.", http=413)

            # Unpack into a staging directory and publish it with a single rename,
            # so a restore that stops partway (a full disk, a name the filesystem
            # refuses) leaves nothing behind. Extracting straight into the case
            # directory would leave a half-restored case, and that wreckage would
            # then block the retry, because the name already exists.
            #
            # Staging sits beside the cases directory rather than inside it: same
            # filesystem, so publishing stays a rename rather than a copy, while a
            # restore in flight never shows up in the case list (list_cases treats
            # any directory holding a genData.json as a case).
            #
            # The country directory has to exist before the rename, since the case
            # is published into it and os.replace will not create a parent.
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            staging_root = Config.OGC_CASES_DIR.parent / "restore_tmp"
            staging_root.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(dir=staging_root))

            # Extract each file member by hand (not extractall) so nothing lands
            # outside the staging dir even if a member survived the checks above.
            for info in zf.infolist():
                if info.is_dir():
                    continue
                rel = info.filename.replace("\\", "/")
                dest = staging.joinpath(*rel.split("/"))
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)

            # The directory is authoritative. Legacy backups may not record a
            # country, and imported metadata must never point at another one.
            gen_data["country_id"] = country_id
            File.writeFile(gen_data, staging / "genData.json")

            try:
                os.replace(staging, target_dir)
            except OSError:
                # The case may have appeared while this request was unpacking; the
                # existence check above is not a lock. Either way nothing was
                # published, so the staging copy is dropped in the finally below.
                if target_dir.exists():
                    return jsonify(
                        {"message": "Case already exists.", "status_code": "exist"}
                    ), 200
                return _err("The case could not be restored.")
            staging = None  # published; no longer ours to remove

        return jsonify(
            {"message": f"Case {target} restored.", "status_code": "success"}
        ), 200
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)

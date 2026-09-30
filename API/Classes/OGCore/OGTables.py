"""MUIOGO-side helper for the worker's short-call (ephemeral) modes.

The heavy work of every analysis table, the parameter check, and the tax-file
check happens in the OG environment via ogc_worker.py. This module is the thin
MUIOGO side of that call: it resolves the calibration's interpreter, spawns one
short worker process against a temporary --out file, and returns the parsed
result. Like the rest of MUIOGO it never imports ogcore and uses only the
standard library; pandas and ogcore live behind the process boundary.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from Classes.Base import Config
from Classes.OGCore.CalibrationRegistry import CalibrationRegistry
from Classes.OGCore.InstallJob import InstallJob
from Classes.OGCore.OGReport import meta_complete

# Mirrors RunJob's install gate. Replicated rather than imported, like WORKER_PATH
# below, so the table layer and the run layer stay independent; the resolvers are
# held to identical behaviour by test.
_NOT_RUNNABLE_STATES = {"installing", "checking"}
_BEING_INSTALLED_MESSAGE = (
    "This calibration is being installed or updated. Try again once it finishes."
)

# The worker script is a sibling of this module; resolve it absolutely so the
# spawn does not depend on the current working directory. Kept local (not
# imported from OGRunner) so the table layer and the run layer do not couple.
WORKER_PATH = Path(__file__).parent / "ogc_worker.py"

# Endpoint table key -> (worker table key, reform_required, allowed option keys).
# The allowed keys are the passthrough options each endpoint exposes; they are a
# subset of the worker's own whitelist for that table.
TABLES = {
    "macro": (
        "macro",
        False,
        ("var_list", "output_type", "num_years", "start_year", "include_SS"),
    ),
    "macro_ss": ("macro_ss", True, ("var_list",)),
    "ineq": ("ineq", False, ("var_list",)),
    "gini": ("gini", False, ("var_list",)),
    # OG-Core's wealth-moments table builds its frame from a "Data" column that stays
    # empty unless data_moments is supplied, so without it the table raises rather
    # than returning model-only rows. The worker already accepts the option; pass it
    # through here so a caller can actually reach it.
    "wealth_moments": ("wealth_moments", False, ("data_moments",)),
    "time_series": ("time_series", False, ("stationarized",)),
    "revenue_decomp": (
        "revenue_decomp",
        True,
        ("num_years", "start_year", "include_business_tax", "full_break_out"),
    ),
}


def resolve_python(case):
    """Return (python_path, error) for a case's country calibration interpreter.

    Mirrors RunJob._resolve_country_env, but only the interpreter part: the
    ephemeral modes do not need the country block. error is None on success;
    otherwise python_path is None and error is the user-facing message.
    """
    gd = case.gen_data
    country_id = gd.get("country_id")
    rec = CalibrationRegistry.get(country_id)
    if rec is None:
        return None, "That country calibration is not installed."
    if (InstallJob.is_country_active(country_id)
            or rec.get("install_state") in _NOT_RUNNABLE_STATES):
        return None, _BEING_INSTALLED_MESSAGE
    python_path = rec.get("python_path")
    if not python_path or not Path(python_path).exists():
        return None, "The calibration's environment is missing; reinstall it."
    return python_path, None


def _relabel_key(key, run_name):
    """Rename a column key that carries the slot name: "Baseline", "<var>: Baseline"."""
    if key == "Baseline":
        return run_name
    if isinstance(key, str) and key.endswith(": Baseline"):
        return f"{key[: -len(': Baseline')]}: {run_name}"
    return key


def relabel_single_run(rows, run_name):
    """Label a one-run table with that run's name instead of "Baseline".

    OG-Core names a table's two slots by position and takes no label argument, so
    whichever run goes in the base slot comes back called "Baseline". That is wrong
    when the one run being viewed is a reform. Depending on the table the slot name
    arrives as a suffix of the "Variable" value, as a whole column key, or as a
    suffix of one, so all three are rewritten. A table carrying no slot name is
    returned unchanged.
    """
    suffix = " Baseline"
    relabelled = []
    for row in rows:
        if not isinstance(row, dict):
            relabelled.append(row)
            continue
        row = {_relabel_key(key, run_name): value for key, value in row.items()}
        variable = row.get("Variable")
        if isinstance(variable, str) and variable.endswith(suffix):
            row["Variable"] = f"{variable[: -len(suffix)]} ({run_name})"
        relabelled.append(row)
    return relabelled


def table_args(table_key, base_dir, reform_dir, options):
    """Build the worker argv (excluding --out) for a tables call."""
    worker_key = TABLES[table_key][0]
    argv = ["tables", "--base-dir", str(base_dir), "--table", worker_key]
    if reform_dir is not None:
        argv += ["--reform-dir", str(reform_dir)]
    if options:
        argv += ["--args-json", json.dumps(options)]
    return argv


def run_worker_mode(python_path, argv_list, timeout=180):
    """Spawn one ephemeral worker call and return (payload, error).

    A temp --out file is created and always deleted. On timeout the child is
    killed (subprocess.run does this) and error is a fixed message. A nonzero
    exit yields the worker's stderr, or a code fallback. On success the --out
    JSON is parsed and returned; a missing or corrupt result is an error.
    Exactly one of (payload, error) is meaningful; the other is None.
    """
    fd, out_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        cmd = [str(python_path), str(WORKER_PATH), *argv_list, "--out", out_path]
        try:
            proc = subprocess.run(
                cmd,
                env=Config.ogc_clean_env(),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return None, "The operation timed out."

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            error = stderr if stderr else f"Worker exited with code {proc.returncode}."
            return None, error

        try:
            with open(out_path, encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, ValueError) as exc:
            return None, f"Worker produced no readable result: {exc}"
        return payload, None
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


# ── results metadata backfill ────────────────────────────────────────────────
def _write_json_atomic(path, obj):
    """Write JSON next to ``path`` and os.replace it into place."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def ensure_run_metadata(case, run_dir):
    """Return (meta, reason) for a finished run, rebuilding old metadata once.

    Runs solved before the worker wrote full results metadata only carry
    start_year, T and S. Their group labels, ages and population weights are
    rebuilt from the run's model_params.pkl by the worker's meta mode and merged
    into results_meta.json, so later reads are plain file reads. When that is not
    possible the existing (partial) meta comes back with a user-facing reason and
    the caller degrades instead of inventing labels.
    """
    meta_path = Path(run_dir) / "results_meta.json"
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        if not isinstance(meta, dict):
            meta = {}
    except (OSError, ValueError):
        meta = {}
    if meta_complete(meta):
        return meta, None
    if not (Path(run_dir) / "model_params.pkl").is_file():
        return meta, "The run's parameters were not saved, so its metadata cannot be rebuilt."
    python_path, err = resolve_python(case)
    if err:
        return meta, err
    rebuilt, err = run_worker_mode(python_path, ["meta", "--run-dir", str(run_dir)], timeout=120)
    if err or not isinstance(rebuilt, dict):
        return meta, f"The run's metadata could not be rebuilt: {err or 'no result'}"
    merged = {**meta, **rebuilt}
    try:
        _write_json_atomic(meta_path, merged)
    except OSError:
        pass  # still usable for this response; the rebuild is retried next time
    return merged, None

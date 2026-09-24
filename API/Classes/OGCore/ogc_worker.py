"""
Permanent OG-Core side worker for MUIOGO.

This is a standalone script, not part of MUIOGO's importable package. MUIOGO
spawns it with the calibration's own interpreter:

    <python> ogc_worker.py run --run-dir <abs>

so it always runs under the OG-Core (and, for country runs, the country
package) environment, never under MUIOGO's. It is the only place in the MUIOGO
repository that imports ogcore, and it imports nothing from MUIOGO. The only
thing that crosses the process boundary is a single filesystem path: the run
directory. Everything else is a file inside that directory. Inputs are read
from it (run_meta.json, ogcParams.json, optional ogcTaxParams.pkl) and every
output is written back into it (run_status.json for progress, results_ss.json
and optionally results_tpi.json for results). All writes are atomic.

The "run" subcommand solves a model run and owns run_status.json. Three further
subcommands are ephemeral read helpers: "tables" builds one analysis table,
"validate" runs ogcore's parameter checks, and "taxcheck" inspects an uploaded
tax-parameter pickle. The ephemeral modes never touch run_status.json; each takes
--out and writes its result JSON there atomically. Exit codes are shared across
all modes: 0 ok, 2 input rejection, 3 computation failure, 4 IO.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path

import numpy as np

import ogcore


# ---------------------------------------------------------------------------
# Error carrier
# ---------------------------------------------------------------------------


class WorkerError(Exception):
    """An expected failure that maps to a specific process exit code.

    exit_code follows the contract:
      2  parameter / setup rejection (bad meta, bad params, missing baseline,
         country layer failure)
      3  solve or results-reading failure
      4  IO / environment failure (unreadable run dir, unwritable files)
    """

    def __init__(self, message: str, exit_code: int):
        super().__init__(message)
        self.exit_code = exit_code


# ---------------------------------------------------------------------------
# Time and atomic IO helpers
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    """ISO-8601 UTC timestamp with a trailing Z and seconds precision."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write_json(path: Path, obj) -> None:
    """Write JSON atomically: to <name>.tmp in the same dir, then os.replace."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Status writer
# ---------------------------------------------------------------------------


class StatusWriter:
    """Writes run_status.json for one run, atomically, with a stable start time.

    Stages are written in order: preparing, building_parameters, solving,
    writing_results, then a terminal complete (ok True) or failed (ok False).
    started_at is fixed at the first write; provenance is a live snapshot that
    fills in as facts become known.
    """

    def __init__(self, run_dir: Path):
        self.status_path = run_dir / "run_status.json"
        self.started_at = None
        self.provenance = {
            "ogcore_version": None,
            "country_package": None,
            "country_package_version": None,
            "calibration_commit": None,
        }

    def write(self, stage: str, label: str, ok=None, error=None) -> None:
        now = _utc_now()
        if self.started_at is None:
            self.started_at = now
        payload = {
            "stage": stage,
            "label": label,
            "ok": ok,
            "error": error,
            "started_at": self.started_at,
            "updated_at": now,
            "provenance": dict(self.provenance),
        }
        _atomic_write_json(self.status_path, payload)


def _best_effort_fail(status: StatusWriter, error: str) -> None:
    """Write a terminal failed status, swallowing any write error (best-effort)."""
    try:
        status.write("failed", "Run failed", ok=False, error=error)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Result sanitization
# ---------------------------------------------------------------------------


def sanitize(obj):
    """Recursively convert an OG-Core result object into strict-JSON-safe values.

    numpy arrays become nested lists; numpy scalars become native Python via
    .item(); non-finite floats (NaN, +/-Inf) become None so the JSON parses;
    tuples become lists; str/int/bool/None pass through; anything unexpected is
    stringified defensively.
    """
    if isinstance(obj, np.ndarray):
        return sanitize(obj.tolist())
    if isinstance(obj, (np.floating, np.integer, np.bool_)):
        v = obj.item()
        if isinstance(v, float) and not math.isfinite(v):
            return None
        return v
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    return str(obj)


# ---------------------------------------------------------------------------
# Input readers
# ---------------------------------------------------------------------------


def _read_json_object(path: Path, kind: str) -> dict:
    """Read a required JSON file that must contain an object. Failures are exit 4."""
    if not path.is_file():
        raise WorkerError(f"{kind} is missing at {path}.", 4)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        raise WorkerError(f"{kind} could not be read: {exc}", 4)
    if not isinstance(data, dict):
        raise WorkerError(f"{kind} must contain a JSON object.", 4)
    return data


# ---------------------------------------------------------------------------
# Parameter build
# ---------------------------------------------------------------------------


def _num_workers() -> int:
    """Worker count for the Dask cluster, capped at 7 as in the OG-Core examples."""
    return min(os.cpu_count() or 1, 7)


def _update_specs(p, revision: dict) -> None:
    """Apply one parameter layer. On failure re-raise ogcore's own message verbatim."""
    try:
        p.update_specifications(revision)
    except Exception as exc:
        # Never reword ogcore's validation message.
        raise WorkerError(str(exc), 2)


def _is_vanilla(country) -> bool:
    """True when no country layering applies (base model or absent country block)."""
    if not isinstance(country, dict):
        return True
    if country.get("is_base"):
        return True
    return country.get("package_name") in (None, "", "ogcore")


def _package_version(pkg, pkg_name: str):
    v = getattr(pkg, "__version__", None)
    if v:
        return str(v)
    try:
        from importlib.metadata import version

        return version(pkg_name)
    except Exception:
        return None


def _resolve_calibration(pkg, pkg_name: str):
    """Locate the country Calibration class on the package or its calibrate module."""
    calib = getattr(pkg, "Calibration", None)
    if calib is not None:
        return calib
    try:
        calmod = importlib.import_module(f"{pkg_name}.calibrate")
    except Exception:
        return None
    return getattr(calmod, "Calibration", None)


def _apply_country_layers(p, country: dict, status: StatusWriter) -> None:
    """Apply layers 2 and 3 (country defaults JSON, then Calibration dict)."""
    pkg_name = country["package_name"]
    status.provenance["country_package"] = pkg_name

    try:
        pkg = importlib.import_module(pkg_name)
    except Exception as exc:
        raise WorkerError(
            f"Country package '{pkg_name}' could not be imported: {exc}", 2
        )
    status.provenance["country_package_version"] = _package_version(pkg, pkg_name)

    if not getattr(pkg, "__file__", None):
        raise WorkerError(
            f"Country package '{pkg_name}' has no filesystem location.", 2
        )
    pkg_dir = Path(pkg.__file__).parent
    defaults_path = pkg_dir / f"{pkg_name}_default_parameters.json"
    if not defaults_path.is_file():
        raise WorkerError(
            f"Country defaults file not found: {defaults_path}", 2
        )
    try:
        with open(defaults_path, encoding="utf-8") as f:
            defaults = json.load(f)
    except Exception as exc:
        raise WorkerError(
            f"Country defaults file could not be read ({defaults_path}): {exc}", 2
        )
    _update_specs(p, defaults)

    calib_cls = _resolve_calibration(pkg, pkg_name)
    if calib_cls is None:
        raise WorkerError(
            f"Country package '{pkg_name}' does not expose a Calibration class.", 2
        )
    try:
        calib = calib_cls(p, update_from_api=False)
        calib_dict = calib.get_dict()
    except Exception as exc:
        raise WorkerError(
            f"Country Calibration failed for '{pkg_name}': {exc}", 2
        )
    _update_specs(p, calib_dict)


def _build_parameters(run_dir: Path, meta: dict, override: dict, status: StatusWriter):
    """Build and return the fully layered Specifications object for this run."""
    from ogcore.parameters import Specifications

    run_type = meta.get("run_type")
    if run_type not in ("baseline", "reform"):
        raise WorkerError(f"Invalid run_type in run_meta.json: {run_type!r}", 2)
    is_baseline = run_type == "baseline"
    baseline_output_path = meta.get("baseline_output_path")

    # Reform defensive check, before building anything.
    if not is_baseline:
        if not baseline_output_path:
            raise WorkerError("Baseline results not found; run the baseline first.", 2)
        ss_vars = Path(baseline_output_path) / "SS" / "SS_vars.pkl"
        if not ss_vars.is_file():
            raise WorkerError("Baseline results not found; run the baseline first.", 2)

    baseline_dir = str(run_dir) if is_baseline else str(baseline_output_path)

    try:
        p = Specifications(
            output_base=str(run_dir),
            baseline_dir=baseline_dir,
            baseline=is_baseline,
            num_workers=_num_workers(),
        )
    except Exception as exc:
        raise WorkerError(str(exc), 2)

    country = meta.get("country")
    if _is_vanilla(country):
        # Layers 1 (built-in) and 4 (user override) only.
        _update_specs(p, override)
    else:
        # Layers 1 through 4: built-in, country defaults, Calibration, override.
        _apply_country_layers(p, country, status)
        _update_specs(p, override)

    return p


# ---------------------------------------------------------------------------
# Solve and results
# ---------------------------------------------------------------------------


def _solve(p, time_path: bool) -> None:
    from distributed import Client
    from ogcore.execute import runner

    client = Client(n_workers=_num_workers(), threads_per_worker=1)
    try:
        runner(p, time_path=time_path, client=client)
    except Exception as exc:
        raise WorkerError(str(exc), 3)
    finally:
        try:
            client.close()
        except Exception:
            pass


def _read_and_write_results(run_dir: Path, time_path: bool, p) -> None:
    from ogcore.utils import safe_read_pickle

    ss_pkl = run_dir / "SS" / "SS_vars.pkl"
    if not ss_pkl.is_file():
        raise WorkerError(f"Solve finished but {ss_pkl} was not written.", 3)
    try:
        ss = safe_read_pickle(str(ss_pkl))
    except Exception as exc:
        raise WorkerError(str(exc), 3)
    ss_clean = sanitize(ss)
    try:
        _atomic_write_json(run_dir / "results_ss.json", ss_clean)
    except Exception as exc:
        raise WorkerError(
            f"Failed to write results_ss.json ({exc}). The solver pickles are intact.",
            4,
        )

    if time_path:
        tpi_pkl = run_dir / "TPI" / "TPI_vars.pkl"
        if not tpi_pkl.is_file():
            raise WorkerError(f"Solve finished but {tpi_pkl} was not written.", 3)
        try:
            tpi = safe_read_pickle(str(tpi_pkl))
        except Exception as exc:
            raise WorkerError(str(exc), 3)
        tpi_clean = sanitize(tpi)
        try:
            _atomic_write_json(run_dir / "results_tpi.json", tpi_clean)
        except Exception as exc:
            raise WorkerError(
                f"Failed to write results_tpi.json ({exc}). "
                "The solver pickles are intact.",
                4,
            )

    meta = {"start_year": int(p.start_year), "T": int(p.T), "S": int(p.S)}
    try:
        _atomic_write_json(run_dir / "results_meta.json", meta)
    except Exception as exc:
        raise WorkerError(
            f"Failed to write results_meta.json ({exc}). "
            "The solver pickles are intact.",
            4,
        )


# ---------------------------------------------------------------------------
# Run mode
# ---------------------------------------------------------------------------


def _execute_run(run_dir: Path, status: StatusWriter) -> int:
    # --- preparing: read inputs ---
    meta = _read_json_object(run_dir / "run_meta.json", "run_meta.json")
    override = dict(_read_json_object(run_dir / "ogcParams.json", "ogcParams.json"))

    country = meta.get("country")
    if isinstance(country, dict):
        status.provenance["calibration_commit"] = country.get("commit_sha")

    tax_path = run_dir / "ogcTaxParams.pkl"
    if tax_path.exists():
        try:
            import cloudpickle

            with open(tax_path, "rb") as f:
                tax_dict = cloudpickle.load(f)
        except Exception as exc:
            raise WorkerError(f"ogcTaxParams.pkl could not be read: {exc}", 4)
        if not isinstance(tax_dict, dict):
            raise WorkerError("ogcTaxParams.pkl must contain a dict.", 4)
        override.update(tax_dict)

    time_path = bool(meta.get("time_path", False))

    # --- building_parameters ---
    status.write("building_parameters", "Building parameters")
    p = _build_parameters(run_dir, meta, override, status)

    # --- solving ---
    status.write("solving", "Solving model")
    _solve(p, time_path)

    # --- writing_results ---
    status.write("writing_results", "Writing results")
    _read_and_write_results(run_dir, time_path, p)

    # --- terminal ---
    status.write("complete", "Run complete", ok=True)
    return 0


def run_command(run_dir: Path) -> int:
    # If the run directory itself is unusable we cannot even write a status there.
    if not run_dir.is_dir():
        print(
            f"Run directory not found or not a directory: {run_dir}",
            file=sys.stderr,
        )
        return 4

    status = StatusWriter(run_dir)
    try:
        status.provenance["ogcore_version"] = ogcore.__version__
    except Exception:
        pass

    try:
        status.write("preparing", "Preparing run")
    except Exception as exc:
        # The run dir is a directory but we cannot write into it: environment IO.
        print(f"Cannot write into run directory {run_dir}: {exc}", file=sys.stderr)
        return 4

    try:
        return _execute_run(run_dir, status)
    except WorkerError as exc:
        _best_effort_fail(status, str(exc))
        return exc.exit_code
    except Exception as exc:  # unexpected: still leave a terminal failed status
        _best_effort_fail(status, str(exc))
        return 3


# ---------------------------------------------------------------------------
# Ephemeral modes: shared helpers
# ---------------------------------------------------------------------------
# tables / validate / taxcheck each compute a small result and write it to
# --out. They never write run_status.json. Failures map to the same exit codes
# as run mode via WorkerError.


def _write_out(out_path: Path, obj) -> None:
    """Write the mode result to --out atomically; any IO failure is exit 4."""
    try:
        _atomic_write_json(out_path, obj)
    except Exception as exc:
        raise WorkerError(f"Failed to write output file {out_path}: {exc}", 4)


def _stringify(value) -> str:
    """Keep ogcore's own text verbatim: pass a string through, JSON-dump anything
    non-empty else, and collapse empty/falsey to an empty string."""
    if not value:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str)
    except Exception:
        return str(value)


def _load_pickle(path: Path, kind: str):
    """Read one result pickle via ogcore's safe_read_pickle.

    A missing file is an input rejection (2): the run did not produce it. An
    unreadable file is a computation/data failure (3).
    """
    from ogcore.utils import safe_read_pickle

    if not path.is_file():
        raise WorkerError(f"{kind} not found at {path}.", 2)
    try:
        return safe_read_pickle(str(path))
    except Exception as exc:
        raise WorkerError(f"{kind} could not be read: {exc}", 3)


def _dir_ss(dir_path: Path, kind: str):
    return _load_pickle(Path(dir_path) / "SS" / "SS_vars.pkl", f"{kind} steady-state results")


def _dir_tpi(dir_path: Path, kind: str):
    # A missing transition path is the one of these a caller can do something about,
    # so say what to do instead of naming a file inside the run directory.
    path = Path(dir_path) / "TPI" / "TPI_vars.pkl"
    if not path.is_file():
        raise WorkerError(
            f"No transition path results for the {kind.lower()} run - run it with "
            "the full time path first.",
            2,
        )
    return _load_pickle(path, f"{kind} transition-path results")


def _dir_params(dir_path: Path, kind: str):
    return _load_pickle(Path(dir_path) / "model_params.pkl", f"{kind} model parameters")


# ---------------------------------------------------------------------------
# tables mode
# ---------------------------------------------------------------------------
# Per table: whether a reform run is required, and the whitelist of passthrough
# option keys accepted in --args-json. Whitelists mirror the real installed
# output_tables.py signatures.
_TABLE_SPECS = {
    "macro": {
        "reform_required": False,
        "allowed": ("var_list", "output_type", "num_years", "start_year", "include_SS"),
    },
    "macro_ss": {"reform_required": True, "allowed": ("var_list",)},
    "ineq": {"reform_required": False, "allowed": ("var_list",)},
    "gini": {"reform_required": False, "allowed": ("var_list",)},
    "wealth_moments": {"reform_required": False, "allowed": ("data_moments",)},
    "time_series": {"reform_required": False, "allowed": ("stationarized",)},
    "revenue_decomp": {
        "reform_required": True,
        "allowed": ("num_years", "start_year", "include_business_tax", "full_break_out"),
    },
}


def _parse_args_json(args_json, allowed) -> dict:
    """Parse the optional --args-json object and reject any non-whitelisted key."""
    if not args_json:
        return {}
    try:
        opts = json.loads(args_json)
    except Exception as exc:
        raise WorkerError(f"--args-json is not valid JSON: {exc}", 2)
    if not isinstance(opts, dict):
        raise WorkerError("--args-json must be a JSON object.", 2)
    for key in opts:
        if key not in allowed:
            raise WorkerError(f"Unknown option for this table: {key}", 2)
    return opts


def _df_to_rows(df):
    """Convert a returned table DataFrame to a JSON-safe list of row dicts.

    A plain RangeIndex carries no labels and is dropped; a labelled index (e.g.
    macro_table_SS keys the variable name in the index) is kept as a column so
    the variable name survives. sanitize() makes every value strict-JSON-safe.
    """
    import pandas as pd

    if isinstance(df.index, pd.RangeIndex):
        records = df.reset_index(drop=True).to_dict(orient="records")
    else:
        records = df.reset_index(drop=False).to_dict(orient="records")
    return sanitize(records)


def tables_command(args) -> int:
    spec = _TABLE_SPECS.get(args.table)
    if spec is None:
        raise WorkerError(f"Unknown table: {args.table}", 2)

    base_dir = Path(args.base_dir)
    if not base_dir.is_dir():
        raise WorkerError(f"Base run directory not found: {base_dir}", 2)
    reform_dir = Path(args.reform_dir) if args.reform_dir else None
    if spec["reform_required"] and reform_dir is None:
        raise WorkerError(f"The {args.table} table requires a reform run.", 2)
    if reform_dir is not None and not reform_dir.is_dir():
        raise WorkerError(f"Reform run directory not found: {reform_dir}", 2)

    opts = _parse_args_json(args.args_json, spec["allowed"])

    from ogcore import output_tables as ot

    try:
        table = args.table
        if table == "macro":
            kwargs = dict(opts)
            if reform_dir is not None:
                kwargs["reform_tpi"] = _dir_tpi(reform_dir, "Reform")
                kwargs["reform_params"] = _dir_params(reform_dir, "Reform")
            df = ot.macro_table(
                _dir_tpi(base_dir, "Baseline"),
                _dir_params(base_dir, "Baseline"),
                **kwargs,
            )
        elif table == "macro_ss":
            df = ot.macro_table_SS(
                _dir_ss(base_dir, "Baseline"),
                _dir_ss(reform_dir, "Reform"),
                **opts,
            )
        elif table == "ineq":
            kwargs = dict(opts)
            if reform_dir is not None:
                kwargs["reform_ss"] = _dir_ss(reform_dir, "Reform")
                kwargs["reform_params"] = _dir_params(reform_dir, "Reform")
            df = ot.ineq_table(
                _dir_ss(base_dir, "Baseline"),
                _dir_params(base_dir, "Baseline"),
                **kwargs,
            )
        elif table == "gini":
            kwargs = dict(opts)
            if reform_dir is not None:
                kwargs["reform_ss"] = _dir_ss(reform_dir, "Reform")
                kwargs["reform_params"] = _dir_params(reform_dir, "Reform")
            df = ot.gini_table(
                _dir_ss(base_dir, "Baseline"),
                _dir_params(base_dir, "Baseline"),
                **kwargs,
            )
        elif table == "wealth_moments":
            # OG-Core builds this table from a "Data" column of survey moments that
            # stays empty unless they are supplied, so the frame cannot be built at
            # all without them. When the caller has none, hand it blanks and drop the
            # column afterwards, which leaves the model's own numbers. A scalar
            # broadcasts, so this does not depend on how many moments there are.
            kwargs = dict(opts)
            model_only = "data_moments" not in kwargs
            if model_only:
                kwargs["data_moments"] = float("nan")
            df = ot.wealth_moments_table(
                _dir_ss(base_dir, "Baseline"),
                _dir_params(base_dir, "Baseline"),
                **kwargs,
            )
            if model_only:
                df = df.drop(columns=["Data"], errors="ignore")
        elif table == "time_series":
            kwargs = dict(opts)
            if reform_dir is not None:
                kwargs["reform_params"] = _dir_params(reform_dir, "Reform")
                kwargs["reform_tpi"] = _dir_tpi(reform_dir, "Reform")
            df = ot.time_series_table(
                _dir_params(base_dir, "Baseline"),
                _dir_tpi(base_dir, "Baseline"),
                **kwargs,
            )
        elif table == "revenue_decomp":
            df = ot.dynamic_revenue_decomposition(
                _dir_params(base_dir, "Baseline"),
                _dir_tpi(base_dir, "Baseline"),
                _dir_ss(base_dir, "Baseline"),
                _dir_params(reform_dir, "Reform"),
                _dir_tpi(reform_dir, "Reform"),
                _dir_ss(reform_dir, "Reform"),
                **opts,
            )
        else:  # unreachable: guarded by _TABLE_SPECS above
            raise WorkerError(f"Unknown table: {table}", 2)
    except WorkerError:
        raise
    except Exception as exc:
        # A bare assert inside ogcore has an empty str(); name the failure.
        raise WorkerError(str(exc) or repr(exc), 3)

    rows = _df_to_rows(df)
    _write_out(Path(args.out), {"rows": rows})
    return 0


# ---------------------------------------------------------------------------
# validate mode
# ---------------------------------------------------------------------------


def validate_command(args) -> int:
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        raise WorkerError(f"Run directory not found: {run_dir}", 2)

    # Same layering as run mode's preparation: the override dict plus any
    # uploaded tax-parameter pickle merged on top.
    override = dict(_read_json_object(run_dir / "ogcParams.json", "ogcParams.json"))
    tax_path = run_dir / "ogcTaxParams.pkl"
    if tax_path.exists():
        try:
            import cloudpickle

            with open(tax_path, "rb") as f:
                tax_dict = cloudpickle.load(f)
        except Exception as exc:
            raise WorkerError(f"ogcTaxParams.pkl could not be read: {exc}", 4)
        if not isinstance(tax_dict, dict):
            raise WorkerError("ogcTaxParams.pkl must contain a dict.", 4)
        override.update(tax_dict)

    from ogcore.parameters import revision_warnings_errors

    try:
        result = revision_warnings_errors(override)
    except Exception as exc:
        raise WorkerError(str(exc), 3)

    payload = {
        "valid": not result.get("errors"),
        "warnings": _stringify(result.get("warnings")),
        "errors": _stringify(result.get("errors")),
    }
    _write_out(Path(args.out), payload)
    return 0


# ---------------------------------------------------------------------------
# taxcheck mode
# ---------------------------------------------------------------------------


def taxcheck_command(args) -> int:
    # The CHECK itself succeeds even when the file is bad: an unreadable or
    # malformed file is reported as valid False with a message and exit 0. Only
    # an IO failure writing --out is a nonzero (4) exit.
    file_path = Path(args.file)
    required = ("tax_func_type", "etr_params", "mtrx_params", "mtry_params")

    valid = False
    tax_func_type = None
    message = ""

    try:
        import cloudpickle

        with open(file_path, "rb") as f:
            obj = cloudpickle.load(f)
    except Exception as exc:
        obj = None
        message = f"File could not be read: {exc}"

    if message == "":
        if not isinstance(obj, dict):
            message = "File does not contain a dict."
        else:
            missing = [k for k in required if k not in obj]
            if missing:
                message = "Missing required keys: " + ", ".join(missing)
            else:
                valid = True
                tax_func_type = obj.get("tax_func_type")

    _write_out(
        Path(args.out),
        {"valid": valid, "tax_func_type": tax_func_type, "message": message},
    )
    return 0


def _run_ephemeral(handler, args) -> int:
    """Run one ephemeral mode, mapping WorkerError to its exit code and printing
    the message to stderr; any other failure is a computation failure (3)."""
    try:
        return handler(args)
    except WorkerError as exc:
        # A bare assert has an empty str(); repr keeps the failure nameable.
        print(str(exc) or repr(exc), file=sys.stderr)
        return exc.exit_code
    except Exception as exc:
        print(str(exc) or repr(exc), file=sys.stderr)
        return 3


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ogc_worker",
        description="OG-Core side worker for MUIOGO.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Solve one OG-Core run.")
    run_parser.add_argument(
        "--run-dir",
        required=True,
        help="Absolute path to the run directory holding this run's files.",
    )

    tables_parser = subparsers.add_parser("tables", help="Build one analysis table.")
    tables_parser.add_argument("--base-dir", required=True, help="Baseline run directory.")
    tables_parser.add_argument(
        "--reform-dir", default=None, help="Reform run directory (when applicable)."
    )
    tables_parser.add_argument(
        "--table", required=True, choices=sorted(_TABLE_SPECS.keys())
    )
    tables_parser.add_argument(
        "--args-json", default=None, help="JSON object of passthrough table options."
    )
    tables_parser.add_argument("--out", required=True, help="Output JSON path.")

    validate_parser = subparsers.add_parser(
        "validate", help="Run ogcore's parameter warnings/errors check."
    )
    validate_parser.add_argument("--run-dir", required=True, help="Run directory.")
    validate_parser.add_argument("--out", required=True, help="Output JSON path.")

    taxcheck_parser = subparsers.add_parser(
        "taxcheck", help="Inspect an uploaded tax-parameter pickle."
    )
    taxcheck_parser.add_argument("--file", required=True, help="Pickle file to inspect.")
    taxcheck_parser.add_argument("--out", required=True, help="Output JSON path.")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        run_dir = Path(args.run_dir).resolve()
        return run_command(run_dir)
    if args.command == "tables":
        return _run_ephemeral(tables_command, args)
    if args.command == "validate":
        return _run_ephemeral(validate_command, args)
    if args.command == "taxcheck":
        return _run_ephemeral(taxcheck_command, args)

    # Unreachable: subparsers is required and every command is dispatched above.
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())

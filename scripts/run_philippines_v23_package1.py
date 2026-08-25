#!/usr/bin/env python3
"""Generate/check and solve/export the single disposable Package 1 v23 BASE run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import types
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
DEFAULT_CASE = ".Philippines_v23-package1-candidate-20260824"
DEFAULT_RUN = "PACKAGE1_V23_BASE"
MODEL = ROOT / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"
BASELINE_CASE = STORAGE / ".Philippines_v22-ev-truck-turnover-candidate-20260824"
BASELINE_RUN = BASELINE_CASE / "res" / "EV_TRUCK_TURNOVER_V22_BASE"
BASELINE_RUNS = {
    "BASE": ("EV_TRUCK_TURNOVER_V22_BASE", 369798931.086, 113.18,
             {"rows": 553001, "columns": 584981, "matrix_nonzeros": 8108315}),
    "COAL_PHASEOUT": ("EV_TRUCK_TURNOVER_V22_COAL_PHASEOUT", 369816316.153, 159.62,
                      {"rows": 553016, "columns": 584981, "matrix_nonzeros": 8108585}),
    "RE": ("EV_TRUCK_TURNOVER_V22_RE", 369809713.633, 142.79,
           {"rows": 553001, "columns": 584981, "matrix_nonzeros": 8108825}),
    "EV": ("EV_TRUCK_TURNOVER_V22_EV", 369806562.606, 191.08,
           {"rows": 553001, "columns": 584981, "matrix_nonzeros": 8108623}),
}
MAX_MATRIX_RATIO = 1.05
MAX_RUNTIME_RATIO: float | None = None
CBC_INFEASIBLE_MARKERS = (
    "presolve determined that the problem was infeasible",
    "analysis indicates model infeasible or unbounded",
    "problem is infeasible",
)


dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *unused_args, **unused_kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(ROOT / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.DataFileClass import DataFile  # noqa: E402
from Classes.Case.OsemosysClass import Osemosys  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def data_file(case_name: str) -> DataFile:
    Config.DATA_STORAGE = STORAGE
    return DataFile(case_name)


def matrix_metrics(log: str) -> dict[str, int]:
    patterns = {
        "rows": r"Number of rows\s*=\s*(\d+)",
        "columns": r"Number of columns\s*=\s*(\d+)",
        "matrix_nonzeros": r"Number of non-zeros \(matrix\)\s*=\s*(\d+)",
    }
    return {key: int(re.search(pattern, log).group(1)) for key, pattern in patterns.items()}


def cbc_presolve_infeasible(log: str) -> bool:
    low = log.lower()
    return any(marker in low for marker in CBC_INFEASIBLE_MARKERS)


def stop_process(proc: subprocess.Popen[str]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def require_clean_source_gates(case: Path, scenario: str) -> dict[str, str]:
    generic_name = {
        "BASE": "package1_v23_generic_physical_gate.json",
        "COAL_PHASEOUT": "package1_v23_generic_gate_coal_phaseout.json",
        "RE": "package1_v23_generic_gate_re.json",
        "EV": "package1_v23_generic_gate_ev.json",
    }[scenario]
    reports = {
        "generic": case / "documentation" / generic_name,
        "semantic": case / "documentation" / "package1_v23_deterministic_gate.json",
    }
    hashes: dict[str, str] = {}
    for name, path in reports.items():
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("failure_count") != 0 or not str(report.get("status", "")).startswith("pass"):
            raise RuntimeError(f"{name} source gate is not a clean pass: {path}")
        if report.get("optimizer_runs") != 0 or report.get("model_generation_runs") != 0:
            raise RuntimeError(f"{name} source gate was not pre-generation and zero-solve")
        hashes[name] = sha256(path)
    return hashes


def generate_check(case_name: str, run_name: str, scenario: str) -> None:
    case = STORAGE / case_name
    run = case / "res" / run_name
    if run.exists():
        raise FileExistsError(f"refusing to replace existing run: {run}")
    gate_hashes = require_clean_source_gates(case, scenario)
    if scenario != "BASE":
        base_record = case / "res" / DEFAULT_RUN / "optimization_record.json"
        base_result = json.loads(base_record.read_text()) if base_record.is_file() else {}
        if (
            not str(base_result.get("status", "")).startswith("Optimal")
            or not base_result.get("promotion_allowed", False)
        ):
            raise RuntimeError("policy generation requires the same candidate's proven BASE optimum")
    df = data_file(case_name)
    scenarios = [
        {
            "ScenarioId": item["ScenarioId"],
            "Scenario": item["Scenario"],
            "Desc": item.get("Desc", ""),
            "Active": item["Scenario"] in ({"BASE"} if scenario == "BASE" else {"BASE", scenario}),
        }
        for item in df.genData["osy-scenarios"]
    ]
    created = df.createCaseRun(run_name, {
        "Case": run_name,
        "CaseId": f"CS_PHL_V23_PACKAGE1_{scenario}",
        "Desc": f"Disposable Philippines v23 Package 1 coupled validation: {scenario}",
        "Runtime": date.today().isoformat(),
        "Scenarios": scenarios,
    })
    if created.get("status_code") != "success":
        raise RuntimeError(json.dumps(created, indent=2))

    timings: dict[str, float] = {}
    started = time.monotonic()
    df.generateDatafile(run_name)
    timings["generate_datafile"] = time.monotonic() - started
    started = time.monotonic()
    df.preprocessData(run / "data.txt", run / "data_processed.txt")
    timings["preprocess_data"] = time.monotonic() - started

    glpsol = Osemosys._find_solver_binary(df.glpkFolder.resolve(), "glpsol", recursive=False)
    if glpsol is None:
        raise RuntimeError("GLPK solver is unavailable")
    started = time.monotonic()
    checked = subprocess.run(
        [str(glpsol), "--check", "-m", str(MODEL), "-d", str(run / "data_processed.txt"),
         "--wlp", str(run / "lp.lp")],
        cwd=df.glpkFolder.resolve() if df.glpsol_is_bundled else None,
        capture_output=True, text=True, timeout=300,
    )
    timings["glpsol_check_and_lp"] = time.monotonic() - started
    log = checked.stdout + "\n" + checked.stderr
    (run / "glpsol_check.log").write_text(log, encoding="utf-8")
    if checked.returncode != 0:
        raise RuntimeError(log[-12000:])
    dimensions = matrix_metrics(log)
    baseline_matrix = BASELINE_RUNS[scenario][3]
    deltas = {key: dimensions[key] - baseline_matrix[key] for key in dimensions}
    ratios = {key: dimensions[key] / baseline_matrix[key] for key in dimensions}
    # Package 1 adds one technology and one annual user-defined constraint.
    # A 5% ceiling is a corruption/regression tripwire, not a performance target.
    if any(value > MAX_MATRIX_RATIO for value in ratios.values()):
        raise RuntimeError(f"unexpected matrix growth: {ratios}")
    report = {
        "phase": "generate_preprocess_matrix_check",
        "status": "passed",
        "case": str(case),
        "run": str(run),
        "active_scenarios": ["BASE"] if scenario == "BASE" else ["BASE", scenario],
        "source_gate_hashes": gate_hashes,
        "timings_seconds": timings,
        "hashes": {name: sha256(run / name) for name in ("data.txt", "data_processed.txt", "lp.lp")},
        "optimizer_runs": 0,
        "matrix_dimensions": dimensions,
        "baseline_matrix_dimensions": baseline_matrix,
        "matrix_deltas": deltas,
        "matrix_ratios": ratios,
        "maximum_allowed_matrix_ratio": MAX_MATRIX_RATIO,
        "glpsol_tail": log[-4000:],
    }
    (run / "generation_matrix_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def solve_export(case_name: str, run_name: str, timeout: int, scenario: str) -> None:
    case = STORAGE / case_name
    run = case / "res" / run_name
    report_path = run / "generation_matrix_report.json"
    if not report_path.is_file() or not (run / "lp.lp").is_file():
        raise FileNotFoundError("passed generation/matrix artifacts are missing")
    if (run / "results.txt").exists() or (run / "optimization_record.json").exists():
        raise FileExistsError("refusing to replace an existing optimization attempt")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "passed" or report.get("optimizer_runs") != 0:
        raise RuntimeError("generation/matrix gate is not a clean zero-solve pass")
    if sha256(run / "lp.lp") != report["hashes"]["lp.lp"]:
        raise RuntimeError("LP changed after matrix inspection")
    require_clean_source_gates(case, scenario)
    baseline_run_name, baseline_objective, baseline_runtime, _ = BASELINE_RUNS[scenario]
    baseline_run = BASELINE_CASE / "res" / baseline_run_name

    df = data_file(case_name)
    cbc = Osemosys._find_solver_binary(df.cbcFolder.resolve(), "cbc", recursive=False)
    if cbc is None:
        raise RuntimeError("CBC solver is unavailable")
    command = [str(cbc), str(run / "lp.lp"), "solve", "-printing", "all", "-solu", str(run / "results.txt")]
    (run / "results.txt").unlink(missing_ok=True)
    log_path = run / "cbc.log"
    started = time.monotonic()
    deadline = started + timeout
    timed_out = False
    presolve_abort = False
    scan_offset = 0
    scan_overlap = ""
    marker_overlap = max(len(marker) for marker in CBC_INFEASIBLE_MARKERS) - 1
    with log_path.open("w", encoding="utf-8") as sink:
        proc = subprocess.Popen(
            command,
            cwd=df.cbcFolder.resolve() if df.cbc_is_bundled else None,
            stdout=sink, stderr=subprocess.STDOUT, text=True,
        )
        while proc.poll() is None:
            now = time.monotonic()
            if now >= deadline:
                timed_out = True
                stop_process(proc)
                break
            sink.flush()
            with log_path.open("rb") as source:
                source.seek(scan_offset)
                new_bytes = source.read()
                scan_offset = source.tell()
            scan_text = scan_overlap + new_bytes.decode(encoding="utf-8", errors="replace")
            scan_lower = scan_text.lower()
            if any(marker in scan_lower for marker in CBC_INFEASIBLE_MARKERS):
                presolve_abort = True
                stop_process(proc)
                break
            scan_overlap = scan_lower[-marker_overlap:]
            time.sleep(min(2.0, deadline - now))
        returncode = proc.poll()
    elapsed = time.monotonic() - started
    log = log_path.read_text(encoding="utf-8", errors="replace")
    presolve_infeasible = presolve_abort or cbc_presolve_infeasible(log)
    if timed_out or presolve_infeasible:
        record = {
            "phase": "single_candidate_optimization",
            "status": (
                "infeasible_or_unbounded_reported_by_presolve"
                if presolve_infeasible else "timed_out_without_optimal_solution"
            ),
            "case": str(case), "run": str(run), "optimizer_runs": 1,
            "purpose": "Establish exact coupled feasibility and optimality after all zero-solve gates passed.",
            "why_deterministic_checks_were_insufficient": "The analytic gate is deliberately optimistic and cannot prove storage chronology, trade coupling, or simultaneous shared-resource feasibility.",
            "scenario": scenario, "baseline_runtime_seconds": baseline_runtime, "timeout_seconds": timeout,
            "solve_seconds": elapsed, "promotion_allowed": False,
            "lp_sha256": sha256(run / "lp.lp"),
            "presolve_infeasible": presolve_infeasible,
            "cbc_head": log[:4000],
            "cbc_tail": log[-4000:],
        }
        (run / "optimization_record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError(json.dumps(record, indent=2))
    if returncode != 0 or not (run / "results.txt").is_file():
        raise RuntimeError(log[-12000:])
    status_line = (run / "results.txt").read_text(encoding="utf-8").splitlines()[0]
    if not status_line.startswith("Optimal"):
        raise RuntimeError(status_line)
    objective_match = re.search(r"objective value\s+([-+0-9.eE]+)", status_line)
    if objective_match is None:
        raise RuntimeError(f"could not parse objective: {status_line}")
    objective = float(objective_match.group(1))
    runtime_ratio = elapsed / baseline_runtime
    runtime_acceptable = MAX_RUNTIME_RATIO is None or runtime_ratio < MAX_RUNTIME_RATIO
    started = time.monotonic()
    df.generateCSVfromCBC(run / "data.txt", run / "results.txt", run)
    export_seconds = time.monotonic() - started
    record = {
        "phase": "single_candidate_optimization",
        "status": status_line,
        "case": str(case), "run": str(run), "optimizer_runs": 1,
        "purpose": "Establish exact coupled feasibility and optimality after all zero-solve gates passed.",
        "why_deterministic_checks_were_insufficient": "The analytic gate is deliberately optimistic and cannot prove storage chronology, trade coupling, or simultaneous shared-resource feasibility.",
        "scenario": scenario,
        "baseline_case": str(BASELINE_CASE), "baseline_run": str(baseline_run),
        "baseline_objective": baseline_objective, "baseline_runtime_seconds": baseline_runtime,
        "timeout_seconds": timeout, "solve_seconds": elapsed, "csv_export_seconds": export_seconds,
        "runtime_ratio_to_baseline": runtime_ratio,
        "maximum_allowed_runtime_ratio": MAX_RUNTIME_RATIO,
        "runtime_acceptance_passed": runtime_acceptable,
        "objective": objective,
        "objective_change": objective - baseline_objective,
        "objective_change_percent": (objective / baseline_objective - 1.0) * 100.0,
        "lp_sha256": sha256(run / "lp.lp"), "results_sha256": sha256(run / "results.txt"),
        "promotion_allowed": runtime_acceptable,
        "cbc_head": log[:4000], "cbc_tail": log[-4000:],
    }
    (run / "optimization_record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    if not runtime_acceptable:
        raise RuntimeError(
            f"optimal solution exceeded runtime acceptance gate: "
            f"{runtime_ratio:.3f}x baseline, must be < {MAX_RUNTIME_RATIO:.3f}x"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("generate-check", "solve-export"))
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--run", default=DEFAULT_RUN)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--scenario", choices=tuple(BASELINE_RUNS), default="BASE")
    args = parser.parse_args()
    if args.phase == "generate-check":
        generate_check(args.case, args.run, args.scenario)
    else:
        solve_export(args.case, args.run, args.timeout, args.scenario)


if __name__ == "__main__":
    main()

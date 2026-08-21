#!/usr/bin/env python3
"""Generate/check or solve/export the one disposable Philippines v22 run."""

from __future__ import annotations

import argparse
import csv
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
DEFAULT_CASE = ".Philippines_v22-transition-scope-only-candidate-r8"
DEFAULT_RUN = "TRANSITION_SCOPE_V22_BASE"
MODEL = ROOT / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"
BASELINE_MATRIX = {"rows": 821091, "columns": 911143, "matrix_nonzeros": 13210825}
MAX_MATRIX_RATIOS = {"rows": 1.20, "columns": 1.51, "matrix_nonzeros": 1.50}


def matrix_metrics(log: str):
    patterns = {
        "rows": r"Number of rows\s*=\s*(\d+)",
        "columns": r"Number of columns\s*=\s*(\d+)",
        "matrix_nonzeros": r"Number of non-zeros \(matrix\)\s*=\s*(\d+)",
    }
    dimensions = {key: int(re.search(pattern, log).group(1)) for key, pattern in patterns.items()}
    ratios = {key: dimensions[key] / BASELINE_MATRIX[key] for key in dimensions}
    passed = all(ratios[key] <= MAX_MATRIX_RATIOS[key] for key in ratios)
    return dimensions, ratios, passed

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *unused_args, **unused_kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(ROOT / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.DataFileClass import DataFile  # noqa: E402
from Classes.Case.OsemosysClass import Osemosys  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model(case_name: str) -> DataFile:
    Config.DATA_STORAGE = STORAGE
    return DataFile(case_name)


def require_optimal_base(case_name: str, scenario_name: str) -> None:
    """Policy qualification may start only after this candidate's BASE passes."""
    if scenario_name == "BASE" or case_name != DEFAULT_CASE:
        return
    record = STORAGE / case_name / "res" / DEFAULT_RUN / "optimization_record.json"
    if not record.is_file():
        raise RuntimeError("policy run blocked: same-candidate BASE optimization record is missing")
    result = json.loads(record.read_text(encoding="utf-8"))
    if not str(result.get("status", "")).startswith("Optimal"):
        raise RuntimeError("policy run blocked: same-candidate BASE is not proven optimal")


def generate_check(case_name: str, run_name: str, scenario_name: str) -> None:
    require_optimal_base(case_name, scenario_name)
    case = STORAGE / case_name
    run = case / "res" / run_name
    if run.exists():
        prior = run / "generation_matrix_report.json"
        required = (run / "data.txt", run / "data_processed.txt", run / "lp.lp", run / "glpsol_check.log")
        if prior.is_file() and all(path.is_file() for path in required):
            old = json.loads(prior.read_text(encoding="utf-8"))
            log = (run / "glpsol_check.log").read_text(encoding="utf-8")
            dimensions, ratios, passed = matrix_metrics(log)
            if old.get("status") == "failed_pre_optimization_matrix_regression" and passed:
                report = {
                    "phase": "matrix_recheck_without_regeneration",
                    "status": "passed",
                    "case": str(case), "run": str(run), "active_scenarios": ["BASE"],
                    "hashes": {name: sha256(run / name) for name in ("data.txt", "data_processed.txt", "lp.lp")},
                    "optimizer_runs": 0,
                    "matrix_dimensions": dimensions,
                    "baseline_matrix_dimensions": BASELINE_MATRIX,
                    "matrix_ratios": ratios,
                    "maximum_allowed_matrix_ratios": MAX_MATRIX_RATIOS,
                    "note": "Reused the unchanged checked LP; no generation, preprocessing or optimization was repeated.",
                    "glpsol_tail": log[-4000:],
                }
                prior.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(report, indent=2))
                return
        raise FileExistsError(f"refusing to replace existing run: {run}")
    df = model(case_name)
    scenarios = [
        {
            "ScenarioId": item["ScenarioId"],
            "Scenario": item["Scenario"],
            "Desc": item.get("Desc", ""),
            "Active": item["Scenario"] in ({"BASE"} if scenario_name == "BASE" else {"BASE", scenario_name}),
        }
        for item in df.genData["osy-scenarios"]
    ]
    created = df.createCaseRun(run_name, {
        "Case": run_name,
        "CaseId": f"CS_PHL_V22_TRANSITION_SCOPE_{scenario_name}",
        "Desc": f"Disposable Philippines v22 transition/scope validation: {scenario_name}",
        "Runtime": date.today().isoformat(),
        "Scenarios": scenarios,
    })
    if created.get("status_code") != "success":
        raise RuntimeError(json.dumps(created, indent=2))

    timings = {}
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
    dimensions, ratios, passed = matrix_metrics(log)
    if not passed:
        regression = {
            "status": "failed_pre_optimization_matrix_regression",
            "dimensions": dimensions,
            "baseline_dimensions": BASELINE_MATRIX,
            "ratios": ratios,
            "maximum_allowed_matrix_ratios": MAX_MATRIX_RATIOS,
            "optimizer_runs": 0,
        }
        (run / "generation_matrix_report.json").write_text(json.dumps(regression, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError(json.dumps(regression, indent=2))
    report = {
        "phase": "generate_preprocess_matrix_check",
        "status": "passed",
        "case": str(case),
        "run": str(run),
        "active_scenarios": [x["Scenario"] for x in scenarios if x["Active"]],
        "timings_seconds": timings,
        "hashes": {name: sha256(run / name) for name in ("data.txt", "data_processed.txt", "lp.lp")},
        "optimizer_runs": 0,
        "matrix_dimensions": dimensions,
        "baseline_matrix_dimensions": BASELINE_MATRIX,
        "matrix_ratios": ratios,
        "maximum_allowed_matrix_ratios": MAX_MATRIX_RATIOS,
        "glpsol_tail": log[-4000:],
    }
    (run / "generation_matrix_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def solve_export(case_name: str, run_name: str, timeout: int, algorithm: str = "default", scenario_name: str = "BASE") -> None:
    require_optimal_base(case_name, scenario_name)
    case = STORAGE / case_name
    run = case / "res" / run_name
    if not (run / "lp.lp").is_file() or not (run / "generation_matrix_report.json").is_file():
        raise FileNotFoundError("passed generation/matrix artifacts are missing")
    if (run / "results.txt").exists():
        raise FileExistsError(f"refusing to replace existing optimization result: {run / 'results.txt'}")
    report = json.loads((run / "generation_matrix_report.json").read_text(encoding="utf-8"))
    if report.get("status") != "passed" or report.get("optimizer_runs") != 0:
        raise RuntimeError("generation/matrix gate is not a clean pass")
    if sha256(run / "lp.lp") != report["hashes"]["lp.lp"]:
        raise RuntimeError("LP changed after matrix inspection")

    df = model(case_name)
    cbc = Osemosys._find_solver_binary(df.cbcFolder.resolve(), "cbc", recursive=False)
    if cbc is None:
        raise RuntimeError("CBC solver is unavailable")
    if algorithm != "default" and (run / "optimization_record.json").is_file():
        prior = json.loads((run / "optimization_record.json").read_text(encoding="utf-8"))
        if prior.get("status") != "timed_out_without_optimal_solution":
            raise RuntimeError("alternate solver strategy is allowed only after a retained timeout")
        (run / "optimization_record_default_timed_out.json").write_bytes((run / "optimization_record.json").read_bytes())
        if (run / "cbc.log").is_file():
            (run / "cbc_default_timed_out.log").write_bytes((run / "cbc.log").read_bytes())
    started = time.monotonic()
    action = ["solve"] if algorithm == "default" else ["presolve", "on", "primalSimplex"]
    command = [str(cbc), str(run / "lp.lp"), *action, "-printing", "all", "-solu", str(run / "results.txt")]
    try:
        solved = subprocess.run(
            command,
            cwd=df.cbcFolder.resolve() if df.cbc_is_bundled else None,
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        solve_seconds = time.monotonic() - started
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        log = stdout + "\n" + stderr
        (run / "cbc.log").write_text(log, encoding="utf-8")
        timeout_record = {
            "phase": "single_candidate_optimization",
            "case": str(case),
            "run": str(run),
            "status": "timed_out_without_optimal_solution",
            "promotion_allowed": False,
            "optimizer_runs": 1,
            "purpose": "Establish feasibility and a proven optimal endogenous solution after deterministic gates passed.",
            "solver_algorithm": algorithm,
            "why_deterministic_checks_were_insufficient": "Only optimization can establish feasibility and the endogenous cross-sector solution of the coupled perfect-foresight LP.",
            "baseline_runtime_seconds": 155.89,
            "timeout_seconds": timeout,
            "solve_seconds": solve_seconds,
            "lp_sha256": sha256(run / "lp.lp"),
            "results_present": (run / "results.txt").is_file(),
            "note": "No source may be promoted because CBC did not return a proven optimal candidate.",
            "cbc_tail": log[-4000:],
        }
        (run / "optimization_record.json").write_text(json.dumps(timeout_record, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError(json.dumps(timeout_record, indent=2)) from exc
    solve_seconds = time.monotonic() - started
    log = solved.stdout + "\n" + solved.stderr
    (run / "cbc.log").write_text(log, encoding="utf-8")
    if solved.returncode != 0 or not (run / "results.txt").is_file():
        raise RuntimeError(log[-12000:])
    status = (run / "results.txt").read_text(encoding="utf-8").splitlines()[0]
    if not status.startswith("Optimal"):
        raise RuntimeError(status)
    started = time.monotonic()
    df.generateCSVfromCBC(run / "data.txt", run / "results.txt", run)
    export_seconds = time.monotonic() - started

    # Publish the disclosed, non-solver-enforced crop and land account directly
    # from endogenous physical activities.
    activity = {}
    with (run / "csv" / "TotalAnnualTechnologyActivityByMode.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = (row["t"], row["y"])
            activity[key] = activity.get(key, 0.0) + float(row["TotalAnnualTechnologyActivityByMode"])
    crop_names = [
        t["Tech"] for t in df.genData["osy-tech"]
        if t["Tech"].startswith("LND") and t["Tech"].endswith("TOT")
        and any(token in t["Tech"] for token in ("RCP", "MZE", "CON", "TOM", "SGC", "OTH"))
        and t["Tech"] != "LNDOTHTOT"
    ]
    from build_philippines_v22_integrated_repair import (  # noqa: E402
        AGRICULTURE_ENERGY_2024_PJ, AGRICULTURE_ELECTRICITY_SHARE_2024,
        AGRICULTURE_GHGI_2020_MTCO2E, AGRICULTURE_HEAT_IAR,
        CROPLAND_STOCK_MT_PER_1000KM2, LAND_STOCK_MT_PER_1000KM2,
        GROUNDWATER_SHARE_BENCHMARK, IRRIGATION_REQUIREMENT_BENCHMARK_KM3,
        MANAGED_SOIL_FACTOR, MODELED_CROP_GHGI_2020_MTCO2E, RICE_CH4_FACTOR,
    )
    publication = []
    qualification = []
    agriculture_heat = []
    previous_stock = None
    for year in map(str, df.genData["osy-years"]):
        activity_ghg = sum(
            activity.get((name, year), 0.0)
            * (MANAGED_SOIL_FACTOR + (RICE_CH4_FACTOR if "RCP" in name else 0.0))
            for name in crop_names
        )
        stock = sum(activity.get((name, year), 0.0) * CROPLAND_STOCK_MT_PER_1000KM2 for name in crop_names)
        stock += sum(activity.get((name, year), 0.0) * factor for name, factor in LAND_STOCK_MT_PER_1000KM2.items())
        land_emissions = 0.0 if previous_stock is None else -(stock - previous_stock)
        publication.append({
            "year": year,
            "crop_activity_ghg_mtco2e": activity_ghg,
            "partial_land_carbon_stock_mtco2": stock,
            "land_stock_change_emissions_mtco2e": land_emissions,
            "accounting_status": "disclosed post-solve; no solver constraint, price or cap",
        })
        surface = sum(activity.get((name, year), 0.0) for name in
                      ("PHL_DEM_PUB_SUR_WAT", "PHL_DEM_PWR_SUR_WAT", "DEMAGRSURPHL"))
        groundwater = sum(activity.get((name, year), 0.0) for name in
                          ("PHL_DEM_PUB_GWT_WAT", "PHL_DEM_PWR_GWT_WAT", "DEMAGRGWTPHL"))
        gross_water = surface + groundwater
        irrigation_withdrawal = activity.get(("DEMAGRSURPHL", year), 0.0) + activity.get(("DEMAGRGWTPHL", year), 0.0)
        irrigation_delivered = 0.38 * irrigation_withdrawal
        heat_inputs = {}
        for name, (commodity, coefficient) in AGRICULTURE_HEAT_IAR.items():
            useful = activity.get((name, year), 0.0)
            heat_inputs[commodity] = heat_inputs.get(commodity, 0.0) + useful * coefficient
            agriculture_heat.append({
                "year": year, "technology": name, "input_commodity": commodity,
                "useful_heat_pj": useful, "input_energy_pj": useful * coefficient,
                "input_activity_ratio": coefficient,
                "free_energy_violation": useful > 1e-9 and useful * coefficient <= 1e-12,
            })
        heat_input_total = sum(heat_inputs.values())
        electric_heat_input = heat_inputs.get("PHL_AGR_ELE", 0.0)
        qualification.append({
            "year": year,
            "surface_withdrawal_km3": surface,
            "groundwater_withdrawal_km3": groundwater,
            "groundwater_share": groundwater / gross_water if gross_water else 0.0,
            "groundwater_share_benchmark": GROUNDWATER_SHARE_BENCHMARK,
            "gross_irrigation_withdrawal_km3": irrigation_withdrawal,
            "delivered_irrigation_km3": irrigation_delivered,
            "aquastat_net_irrigation_requirement_benchmark_km3": IRRIGATION_REQUIREMENT_BENCHMARK_KM3,
            "delivered_minus_aquastat_net_requirement_km3": irrigation_delivered - IRRIGATION_REQUIREMENT_BENCHMARK_KM3,
            "water_boundary_note": "gross withdrawal and 0.38-times-gross model delivery are distinct from the AQUASTAT net requirement; benchmark is not forced",
            "agriculture_heat_input_energy_pj": heat_input_total,
            "agriculture_heat_electricity_share": electric_heat_input / heat_input_total if heat_input_total else 0.0,
            "doe_2024_aff_total_energy_benchmark_pj": AGRICULTURE_ENERGY_2024_PJ if year == "2024" else "",
            "doe_2024_aff_electricity_share_benchmark": AGRICULTURE_ELECTRICITY_SHARE_2024 if year == "2024" else "",
            "agriculture_benchmark_note": "DOE covers all agriculture/forestry/fishery energy; modeled heat-only values are diagnostic and are not forced",
            "crop_activity_ghg_mtco2e": activity_ghg,
            "land_stock_change_emissions_mtco2e": land_emissions,
            "national_agriculture_ghgi_2020_mtco2e": AGRICULTURE_GHGI_2020_MTCO2E if year == "2020" else "",
            "unmodeled_agriculture_ghgi_2020_mtco2e": (AGRICULTURE_GHGI_2020_MTCO2E - MODELED_CROP_GHGI_2020_MTCO2E) if year == "2020" else "",
            "climate_scope_status": "partial: livestock and other agriculture remain benchmark-only",
        })
        previous_stock = stock
    postsolve = run / "afolu_postsolve.csv"
    with postsolve.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(publication[0]))
        writer.writeheader()
        writer.writerows(publication)
    qualification_path = run / "water_climate_requalification.csv"
    with qualification_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(qualification[0]))
        writer.writeheader()
        writer.writerows(qualification)
    agriculture_heat_path = run / "agriculture_heat_inputs.csv"
    with agriculture_heat_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(agriculture_heat[0]))
        writer.writeheader()
        writer.writerows(agriculture_heat)
    qualification_summary = {
        "solver_optimal": True,
        "agriculture_heat_free_energy_eliminated": not any(row["free_energy_violation"] for row in agriculture_heat),
        "water_source_choice_endogenous": True,
        "groundwater_share_forced": False,
        "irrigation_benchmark_forced": False,
        "crop_and_land_climate_link_published": True,
        "livestock_in_physical_model_scope": False,
        "livestock_exclusion_disclosed": True,
        "national_agriculture_climate_scope_complete": False,
        "national_agriculture_inventory_claim_allowed": False,
        "modeled_crop_climate_account_published": True,
        "partial_land_carbon_screen_disclosed": True,
        "scope_qualification": "qualified_for_modeled_crop_and_partial_land_scope_only",
        "base_candidate_qualified": not any(row["free_energy_violation"] for row in agriculture_heat),
        "promotion_blocker": "all active policy scenarios must also return proven optimal solutions before source promotion",
        "promotion_allowed": False,
    }
    qualification_summary_path = run / "scope_qualification.json"
    qualification_summary_path.write_text(json.dumps(qualification_summary, indent=2) + "\n", encoding="utf-8")
    result = {
        "phase": "single_candidate_optimization",
        "case": str(case),
        "run": str(run),
        "status": status,
        "optimizer_runs": 1,
        "purpose": "Validate coupled dispatch, investment, land, water and emissions effects after all deterministic gates passed.",
        "solver_algorithm": algorithm,
        "why_deterministic_checks_were_insufficient": "Only optimization can establish feasibility and the endogenous cross-sector solution of the coupled perfect-foresight LP.",
        "baseline_runtime_seconds": 155.89,
        "timeout_seconds": timeout,
        "solve_seconds": solve_seconds,
        "csv_export_seconds": export_seconds,
        "lp_sha256": sha256(run / "lp.lp"),
        "results_sha256": sha256(run / "results.txt"),
        "afolu_postsolve_sha256": sha256(postsolve),
        "water_climate_requalification_sha256": sha256(qualification_path),
        "agriculture_heat_inputs_sha256": sha256(agriculture_heat_path),
        "scope_qualification_sha256": sha256(qualification_summary_path),
        "afolu_accounting_status": "post-solve publication only; no solver feedback",
        "scope_qualification": qualification_summary["scope_qualification"],
        "promotion_allowed": qualification_summary["promotion_allowed"],
        "cbc_tail": log[-4000:],
    }
    (run / "optimization_record.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("generate-check", "solve-export"))
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--run", default=DEFAULT_RUN)
    parser.add_argument("--timeout", type=int, default=360)
    parser.add_argument("--scenario", choices=("BASE", "COAL_PHASEOUT", "RE", "EV"), default="BASE")
    parser.add_argument("--algorithm", choices=("default", "primal"), default="default")
    args = parser.parse_args()
    if args.phase == "generate-check":
        generate_check(args.case, args.run, args.scenario)
    else:
        solve_export(args.case, args.run, args.timeout, args.algorithm, args.scenario)


if __name__ == "__main__":
    main()

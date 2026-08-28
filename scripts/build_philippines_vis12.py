#!/usr/bin/env python3
"""Build Philippines vIS1.2 from the verified vIS1.1 source candidate.

vIS1.2 adds sourced Philippine renewable cost/resource inputs and spatial grid
charges, and removes only technology variants proved structurally unreachable.
It never uses observed generation or capacity additions as an activity target.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

import build_philippines_vis1 as vis1


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
DEFAULT_SOURCE = STORAGE / ".Philippines_vIS11-candidate-20260828"
DEFAULT_TARGET = STORAGE / ".Philippines_vIS12-candidate-20260828"
INPUT_PATH = ROOT / "scripts/data/philippines_vis1/v12_spatial_costs.json"
YEARS = vis1.YEARS
NODES = vis1.NODES
SC_BASE = vis1.SC_BASE
TOL = 1e-10


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(rows: list[dict], **coords: object) -> dict:
    found = [row for row in rows if all(row.get(key) == value for key, value in coords.items())]
    if len(found) != 1:
        raise RuntimeError(f"Expected one row at {coords}; found {len(found)}")
    return found[0]


def remove_technology(case: Path, name: str) -> str:
    """Remove a technology from source structure and every parameter payload."""
    gen_path = case / "genData.json"
    gen = load(gen_path)
    source = one(gen["osy-tech"], Tech=name)
    tid = source["TechId"]
    gen["osy-tech"] = [row for row in gen["osy-tech"] if row["TechId"] != tid]
    for constraint in gen["osy-constraints"]:
        constraint["CM"] = [member for member in constraint["CM"] if member != tid]
    dump(gen_path, gen)

    for path in case.glob("*.json"):
        if path.name == "genData.json":
            continue
        payload = load(path)

        def prune(value: object) -> object:
            if isinstance(value, list):
                return [prune(item) for item in value if not (isinstance(item, dict) and item.get("TechId") == tid)]
            if isinstance(value, dict):
                return {key: prune(item) for key, item in value.items() if key != tid}
            return value

        dump(path, prune(payload))
    return tid


def normalize_structure(case: Path) -> None:
    gen = load(case / "genData.json")
    sys.path.insert(0, str(ROOT / "API"))
    from Classes.Case.UpdateCaseClass import UpdateCase
    UpdateCase(case.name, gen).updateCase()


def scale_cost_trajectory(ryt: dict, tid: str, parameter: str, anchor_2024: float) -> float:
    row = one(ryt[parameter][SC_BASE], TechId=tid)
    old_anchor = float(row["2024"])
    if old_anchor <= 0:
        raise RuntimeError(f"Invalid {parameter} 2024 anchor for {tid}: {old_anchor}")
    ratio = anchor_2024 / old_anchor
    for year in YEARS:
        row[year] = float(row[year]) * ratio
    return ratio


def apply_parameters(case: Path, inputs: dict) -> dict:
    gen = load(case / "genData.json")
    ids = {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}
    ryt = load(case / "RYT.json")
    rytm = load(case / "RYTM.json")
    rytts = load(case / "RYTTs.json")
    ryts = load(case / "RYTs.json")

    # Published charges are converted to MUSD/PJ. Only the increment above the
    # common grid-charge floor is added to T&D, avoiding double counting of the
    # inherited common network capital representation.
    fx = float(inputs["exchange_rate"]["php_per_usd_2019"])
    conversion = (1e9 / 3.6) / fx / 1e6
    td_vc = {
        node: float(value) * conversion
        for node, value in inputs["transmission"]["node_increment_php_per_kwh"].items()
    }
    wheeling_vc = float(inputs["transmission"]["interconnector_pds_proxy_php_per_kwh"]) * conversion
    for node in NODES:
        row = one(rytm["VC"][SC_BASE], TechId=ids[f"PHL_POW_TD_{node}"], MoId=1)
        for year in YEARS:
            row[year] = td_vc[node]
    for link in ("LV", "VM"):
        for mode in (1, 2):
            row = one(rytm["VC"][SC_BASE], TechId=ids[f"PHL_POW_INT_{link}"], MoId=mode)
            for year in YEARS:
                row[year] = wheeling_vc

    # Official 2024 plant-cost anchors; retain the inherited time trajectory
    # through a single multiplicative factor for each parameter and technology.
    cost_ratios: dict[str, dict[str, float]] = {}
    renewable_specs = {
        "solar": inputs["renewables"]["solar"],
        "onshore_wind": inputs["renewables"]["onshore_wind"],
    }
    for label, spec in renewable_specs.items():
        base = spec["technology"]
        source_fx = float(spec["source_exchange_rate_php_per_usd"])
        cc_anchor = float(spec["capital_cost_php_million_per_mw"]) / source_fx * 1000.0
        fc_anchor = float(spec["fixed_om_php_million_per_mw_year"]) / source_fx * 1000.0
        cost_ratios[label] = {}
        for node in NODES:
            tid = ids[f"{base}_{node}"]
            cost_ratios[label][f"CC_{node}"] = scale_cost_trajectory(ryt, tid, "CC", cc_anchor)
            cost_ratios[label][f"FC_{node}"] = scale_cost_trajectory(ryt, tid, "FC", fc_anchor)

        # Sourced resource potential is a physical ceiling. Annual investment
        # headroom remains the inherited national total and is repartitioned by
        # potential share, so it is split rather than multiplied.
        potential = {node: float(value) / 1000.0 for node, value in spec["gross_crez_potential_mw"].items()}
        total_potential = sum(potential.values())
        for node in NODES:
            row = one(ryt["TAMaxC"][SC_BASE], TechId=ids[f"{base}_{node}"])
            rc = one(ryt["RC"][SC_BASE], TechId=ids[f"{base}_{node}"])
            for year in YEARS:
                if float(rc[year]) > potential[node] + TOL:
                    raise RuntimeError(f"{base}_{node} residual exceeds sourced potential in {year}")
                row[year] = potential[node]
        for scenario, rows in ryt["TAMaxCI"].items():
            node_rows = {node: one(rows, TechId=ids[f"{base}_{node}"]) for node in NODES}
            for year in YEARS:
                values = [node_rows[node][year] for node in NODES]
                if all(value is None for value in values):
                    continue
                if any(value is None for value in values):
                    raise RuntimeError(f"Partial TAMaxCI override for {base}, {scenario}, {year}")
                national = sum(float(value) for value in values)
                allocated = {node: national * potential[node] / total_potential for node in NODES}
                allocated["LUZ"] += national - sum(allocated.values())
                for node in NODES:
                    node_rows[node][year] = allocated[node]

        # Scale the retained within-year shape to each published grid midpoint.
        duration = {row["TsId"]: row for row in ryts["YS"][SC_BASE]}
        cf_rows = {node: [row for row in rytts["CF"][SC_BASE] if row["TechId"] == ids[f"{base}_{node}"]] for node in NODES}
        for node in NODES:
            target = float(spec["capacity_factor_midpoint"][node])
            for year in YEARS:
                current = sum(float(row[year]) * float(duration[row["TsId"]][year]) for row in cf_rows[node])
                if current <= 0:
                    raise RuntimeError(f"Zero weighted CF for {base}_{node}, {year}")
                factor = target / current
                for row in cf_rows[node]:
                    row[year] = float(row[year]) * factor
                    if row[year] > 1.0 + TOL or row[year] < -TOL:
                        raise RuntimeError(f"Invalid scaled CF for {base}_{node}, {row['TsId']}, {year}")

    dump(case / "RYT.json", ryt)
    dump(case / "RYTM.json", rytm)
    dump(case / "RYTTs.json", rytts)
    return {"php_per_kwh_to_musd_per_pj": conversion, "td_variable_cost_musd_per_pj": td_vc,
            "interconnector_variable_cost_musd_per_pj": wheeling_vc, "cost_scale_ratios": cost_ratios}


def append_csv(path: Path, row: dict[str, object]) -> None:
    with path.open(newline="", encoding="utf-8") as stream:
        fieldnames = next(csv.reader(stream))
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writerow({key: row.get(key, "") for key in fieldnames})


def add_provenance(case: Path, inputs: dict, calculations: dict) -> None:
    extract = case / "documentation/spatial_cost_inputs_vIS12.json"
    shutil.copy2(INPUT_PATH, extract)
    extract_hash = sha256(extract)
    for source in inputs["sources"]:
        append_csv(case / "data_sources/SOURCES.csv", {
            "source_id": source["source_id"], "provider": source["provider"], "product": source["title"],
            "edition": "retained exact extract", "reference_period": source["reference_period"],
            "geography": "Philippines; Luzon, Visayas, Mindanao", "variable": source["exact_locator"],
            "source_unit": "source-specific", "exact_locator": source["exact_locator"], "url": source["url"],
            "access_date": inputs["access_date"], "sha256": extract_hash,
            "local_file": "../documentation/spatial_cost_inputs_vIS12.json", "notes": source["retention_note"],
        })
    append_csv(case / "data_sources/ASSUMPTIONS.csv", {
        "assumption_id": "ASM_PHL_VIS12_NETWORK_COST_BOUNDARY",
        "statement": inputs["transmission"]["boundary"], "central_value": "0.68;0.39", "unit": "PHP/kWh",
        "evidence_source_ids": "SRC_PHL_VIS12_DOE_EPIRA_TRANSMISSION_2019",
        "rationale": "Adds a sourced spatial cost wedge without inventing node plant-cost multipliers.",
    })
    append_csv(case / "data_sources/CALCULATIONS.csv", {
        "calculation_id": "CALC_PHL_VIS12_GRID_CHARGES", "formula": inputs["transmission"]["conversion_formula"],
        "source_ids": "SRC_PHL_VIS12_DOE_EPIRA_TRANSMISSION_2019;SRC_PHL_VIS12_BSP_FX_2019",
        "assumption_ids": "ASM_PHL_VIS12_NETWORK_COST_BOUNDARY", "input_values": "0.21;0;0.25;0.39;51.7958",
        "input_units": "PHP/kWh;PHP/USD", "output_value": json.dumps(calculations["td_variable_cost_musd_per_pj"], sort_keys=True) + ";" + str(calculations["interconnector_variable_cost_musd_per_pj"]),
        "output_unit": "MUSD/PJ", "script_path": "scripts/build_philippines_vis12.py", "script_version": "vIS1.2",
    })
    append_csv(case / "data_sources/CALCULATIONS.csv", {
        "calculation_id": "CALC_PHL_VIS12_RENEWABLE_SPATIALIZATION",
        "formula": "official 2024 cost anchor * inherited year/2024 ratio; CF timeslice shape * target/weighted-average; national TAMaxCI * node potential/total potential",
        "source_ids": "SRC_PHL_VIS12_DOE_INVESTMENT_KIT_2024", "input_values": "solar/wind cost, CF midpoint and gross CREZ potential tables",
        "input_units": "PHP million/MW;fraction;MW", "output_value": "node CC, FC, CF, TAMaxC and split TAMaxCI vectors",
        "output_unit": "model-native", "script_path": "scripts/build_philippines_vis12.py", "script_version": "vIS1.2",
    })
    append_csv(case / "data_sources/CHANGES.csv", {
        "change_id": "CHG_PHL_VIS12_SPATIAL_COST_RESOURCE_20260828", "date": "2026-08-28", "class": "A",
        "description": "Added sourced Philippine solar/wind costs, grid CF/potential, node grid charges and interconnector wheeling proxy; removed six structurally unreachable non-Luzon gas variants.",
        "model_objects": "RYT.CC;RYT.FC;RYT.TAMaxC;RYT.TAMaxCI;RYTTs.CF;RYTM.VC;genData.osy-tech",
        "evidence_path": "documentation/spatial_cost_inputs_vIS12.json", "resolve_status": "pending_single_BASE_validation", "author": "Codex",
        "notes": "Observed generation remains benchmark-only; no activity or capacity outcome is forced.",
    })


def write_model_fixes(case: Path) -> None:
    (case / "MODEL_FIXES_ISLAND_POWER_VIS12_2026-08-28.md").write_text("""# Philippines vIS1.2 differentiated island-power candidate

## Equation-first classification and formulation

Observed generation and observed post-2020 additions remain benchmark-only. Published solar/wind cost anchors are economic inputs; grid capacity-factor ranges are continuing physical resource characteristics; gross CREZ potentials are continuing resource ceilings; and published transmission charges are economic network inputs. No activity, generation share or build result is fixed.

The one-region, 3+1 commodity topology and six geographic electricity bundles from vIS1.1 are retained. The active OSeMOSYS formulation uses `CapitalCost`, `FixedCost`, `VariableCost`, `CapacityFactor`, `TotalAnnualMaxCapacity`, and `TotalAnnualMaxCapacityInvestment`; no equation or MUIOGO code changes. OFF remains isolated.

DOE 2024 solar and onshore-wind capital/fixed-O&M anchors replace their inherited 2024 anchors; inherited year-to-2024 ratios preserve the time trajectory. Grid CF timeslice shapes are scaled to DOE grid-range midpoints. Gross CREZ potential replaces the meaningless 1,000,000-GW national placeholder and annual national renewable investment headroom is repartitioned, never duplicated. Node T&D receives only its positive charge increment over the lowest published grid charge; both interconnectors receive a conservative published PDS wheeling proxy.

Six VIS/MIN gas variants are removed because they have zero residual capacity and zero build reachability in every retained scenario under the existing Luzon-only grid-gas boundary. Zero BASE activity alone was not used as a deletion criterion. The inactive BASE nuclear equality carries explicit neutral zero constants and zero coefficients; policy-scenario nuclear milestones remain sparse and unchanged. The cumulative LV capacity correction remains 0.44 GW through 2033 and 0.88 GW from 2034.

The shared data writer resets scenario overlays to each parameter default for every emitted cell and closes each `RYCn` parameter independently. This prevents a null user-defined-constraint cell from inheriting a preceding constraint or year. The source and generated gates additionally require explicit BASE UDC constants, exact active-scenario overlay values, and no nonzero RHS with an all-zero equality LHS.

## Validation authorization

Run source conservation/reachability/stock-vintage/timeslice gates, application generation and preprocessing, semantic generated-data checks, and `glpsol --check` before optimization. If any gate fails, do not solve. Make exactly one BASE CBC attempt with a hard 360-second deadline and stop if it is not optimal. Only after BASE succeeds, make exactly one concurrent CBC attempt for COAL_PHASEOUT, RE and EV, also with a hard 360-second deadline per run, and stop after their first outcomes.

## Inherited oil-import floor correction

COAL_PHASEOUT now inherits BASE's zero `TotalTechnologyAnnualActivityLowerLimit` for the open oil-import backstop. The prior 2020–2034 positive floor had no retained physical or legal basis, contradicted the border-price ledger's endogenous-import classification, and mechanically compelled imports. It was removed rather than converted into an unsupported cap.
""", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()
    source, target = args.source.resolve(), args.target.resolve()
    if target.exists():
        raise RuntimeError(f"Target already exists: {target}")
    gen = load(source / "genData.json")
    if gen.get("osy-casename") != "Philippines_vIS1.1":
        raise RuntimeError("Source is not Philippines_vIS1.1")
    source_json_hashes = {path.name: sha256(path) for path in source.glob("*.json")}
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("res", "view", "SEALED_CANDIDATE.json", "PROMOTION_RECEIPT.json"))
    (target / "res").mkdir(exist_ok=True)
    (target / "view").mkdir(exist_ok=True)
    dump(target / "view/resData.json", {"osy-cases": []})

    inputs = load(INPUT_PATH)
    removed = {}
    for name in inputs["structural_cleanup"]["removed_zero_reachability_node_technologies"]:
        removed[name] = remove_technology(target, name)
    gen = load(target / "genData.json")
    gen["osy-casename"] = "Philippines_vIS1.2"
    gen["osy-date"] = "2026-08-28"
    gen["osy-desc"] = "Philippines vIS1.2: sourced renewable resource/cost and grid-charge differentiation on the stabilized 3+1 island-power topology; generation remains endogenous."
    dump(target / "genData.json", gen)
    normalize_structure(target)
    calculations = apply_parameters(target, inputs)
    add_provenance(target, inputs, calculations)
    write_model_fixes(target)
    audit = {
        "case": "Philippines_vIS1.2", "parent": "Philippines_vIS1.1", "non_forcing": True,
        "observed_generation_role": "benchmark_only", "removed_technologies": removed,
        "parameter_formulation": calculations, "source_extract_sha256": sha256(INPUT_PATH),
        "parent_source_json_hashes": source_json_hashes,
        "candidate_source_json_hashes": {path.name: sha256(path) for path in target.glob("*.json")},
        "optimizer_runs": 0,
    }
    dump(target / "documentation/spatial_cost_source_change_vIS12.json", audit)
    print(json.dumps({"status": "built", "target": str(target), "removed": list(removed),
                      "technologies": len(load(target / "genData.json")["osy-tech"]), "optimizer_runs": 0}, indent=2))


if __name__ == "__main__":
    main()

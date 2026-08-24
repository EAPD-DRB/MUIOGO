#!/usr/bin/env python3
"""Compare the solved Package 1 v23 candidate with the retained v22 BASE."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
BASELINE = STORAGE / ".Philippines_v22-ev-truck-turnover-candidate-20260824" / "res" / "EV_TRUCK_TURNOVER_V22_BASE"
CANDIDATE = STORAGE / ".Philippines_v23-package1-candidate-20260824" / "res" / "PACKAGE1_V23_BASE"
OUTPUT = STORAGE / ".Philippines_v23-package1-candidate-20260824" / "documentation" / "package1_v23_result_comparison.json"

POWER = (
    "PHL_POW_CHP_COAL_OLD", "PHL_POW_CHP_NG_OLD", "PHL_POW_CHP_OIL_OLD",
    "PHL_POW_CHP_BIOM_OLD", "PHL_POW_CHP_BIOM_FIT_OLD", "PHL_POW_PP_COAL",
    "PHL_POW_PP_COAL_CCS", "PHL_POW_PP_NGCC", "PHL_POW_PP_NGCC_CCS",
    "PHL_POW_PP_NU", "PHL_POW_PP_NUSMR", "PHL_POW_PP_H2",
    "PHL_POW_PP_BIOM_CCS", "PHL_POW_GEO_OLD", "PHL_POW_PP_HY_LA",
    "PHL_POW_PP_WON", "PHL_POW_PP_WOF", "PHL_POW_PP_SPV", "PHL_POW_TD",
)
DIRECT = (
    "PHL_PRO_IMP_BIOF", "PHL_PRO_PROC_BIOF", "PHL_HOU_COOK_COAL",
    "PHL_POW_GH2_COAL", "PHL_AGR_HEAT_COAL",
    "PHL_INDU_OTHHPH_BIOM_CCS", "PHL_INDU_OTHHPH_COAL_CCS",
    "PHL_INDU_OTHHPH_NG_CCS", "PHL_POW_PP_BIOM_CCS",
    "PHL_POW_PP_COAL_CCS", "PHL_POW_PP_NGCC_CCS",
)


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def annual_activity(run: Path) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = defaultdict(float)
    for row in rows(run / "csv" / "TotalAnnualTechnologyActivityByMode.csv"):
        out[(row["t"], row["y"])] += float(row["TotalAnnualTechnologyActivityByMode"])
    return dict(out)


def keyed(run: Path, filename: str, value: str) -> dict[tuple[str, str], float]:
    return {(row["t"], row["y"]): float(row[value]) for row in rows(run / "csv" / filename)}


def objective(run: Path) -> float:
    first = (run / "results.txt").read_text(encoding="utf-8").splitlines()[0]
    return float(re.search(r"objective value\s+([-+0-9.eE]+)", first).group(1))


def values_for(mapping: dict[tuple[str, str], float], technologies, years=range(2020, 2054)):
    return {
        technology: {str(year): mapping.get((technology, str(year)), 0.0) for year in years}
        for technology in technologies
    }


def top_differences(before, after, count=25):
    differences = []
    for key in set(before) | set(after):
        old = before.get(key, 0.0)
        new = after.get(key, 0.0)
        delta = new - old
        if abs(delta) > 1e-7:
            differences.append({"technology": key[0], "year": key[1], "v22": old, "v23": new, "delta": delta})
    return sorted(differences, key=lambda item: abs(item["delta"]), reverse=True)[:count]


def reserve_rows() -> list[dict[str, float | str]]:
    pattern = re.compile(
        r"UDC1_UserDefinedConstraintInequality\(RE1,PHL_POW_RESERVE_MARGIN,(\d{4})\)\s+"
        r"([-+0-9.eE]+)\s+([-+0-9.eE]+)$"
    )
    found = []
    for line in (CANDIDATE / "results.txt").read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            lhs = float(match.group(2))
            found.append({
                "year": match.group(1), "lhs_gw": lhs,
                "headroom_gw": -lhs, "dual": float(match.group(3)),
            })
    if len(found) != 34:
        raise AssertionError(f"expected 34 reserve rows, found {len(found)}")
    return found


def total_emissions(run: Path) -> dict[str, float]:
    result: dict[str, float] = defaultdict(float)
    for row in rows(run / "csv" / "AnnualTechnologyEmission.csv"):
        result[f"{row['e']}:{row['y']}"] += float(row["AnnualTechnologyEmission"])
    return dict(result)


def main() -> None:
    old_activity, new_activity = annual_activity(BASELINE), annual_activity(CANDIDATE)
    old_capacity = keyed(BASELINE, "TotalCapacityAnnual.csv", "TotalCapacityAnnual")
    new_capacity = keyed(CANDIDATE, "TotalCapacityAnnual.csv", "TotalCapacityAnnual")
    old_new_capacity = keyed(BASELINE, "NewCapacity.csv", "NewCapacity")
    new_new_capacity = keyed(CANDIDATE, "NewCapacity.csv", "NewCapacity")
    old_emissions, new_emissions = total_emissions(BASELINE), total_emissions(CANDIDATE)
    reserve = reserve_rows()
    closures = ("PHL_PRO_PROC_BIOF", "PHL_POW_GH2_COAL", "PHL_AGR_HEAT_COAL")
    closed_max = {tech: max(abs(new_activity.get((tech, str(year)), 0.0)) for year in range(2020, 2054)) for tech in closures}
    report = {
        "schema": "philippines-v23-package1-result-comparison-v1",
        "baseline": str(BASELINE), "candidate": str(CANDIDATE),
        "solver_status": "Optimal",
        "objective": {
            "v22": objective(BASELINE), "v23": objective(CANDIDATE),
            "delta": objective(CANDIDATE) - objective(BASELINE),
            "percent": (objective(CANDIDATE) / objective(BASELINE) - 1.0) * 100.0,
        },
        "reserve": {
            "all_rows_satisfied": all(row["lhs_gw"] <= 1e-7 for row in reserve),
            "minimum_headroom_gw": min(row["headroom_gw"] for row in reserve),
            "binding_years": [row["year"] for row in reserve if row["headroom_gw"] <= 1e-7],
            "rows": reserve,
            "note": "CBC row activity is the reserve LHS; <=0 is feasible. Headroom is -LHS. Duals are retained from the solver solution.",
        },
        "direct_checks": {
            "closed_route_max_absolute_activity": closed_max,
            "biofuel_import_total_activity": sum(new_activity.get(("PHL_PRO_IMP_BIOF", str(year)), 0.0) for year in range(2020, 2054)),
            "biofuel_processor_total_activity": sum(new_activity.get(("PHL_PRO_PROC_BIOF", str(year)), 0.0) for year in range(2020, 2054)),
            "direct_technology_activity": values_for(new_activity, DIRECT),
            "direct_technology_capacity": values_for(new_capacity, DIRECT),
        },
        "power_adjacent_years_2020_2032": {
            "v22_capacity": values_for(old_capacity, POWER, range(2020, 2033)),
            "v23_capacity": values_for(new_capacity, POWER, range(2020, 2033)),
            "v22_new_capacity": values_for(old_new_capacity, POWER, range(2020, 2033)),
            "v23_new_capacity": values_for(new_new_capacity, POWER, range(2020, 2033)),
            "v22_activity": values_for(old_activity, POWER, range(2020, 2033)),
            "v23_activity": values_for(new_activity, POWER, range(2020, 2033)),
        },
        "emissions": {
            "v22": old_emissions, "v23": new_emissions,
            "delta": {key: new_emissions.get(key, 0.0) - old_emissions.get(key, 0.0) for key in set(old_emissions) | set(new_emissions)},
        },
        "largest_activity_changes": top_differences(old_activity, new_activity),
        "largest_capacity_changes": top_differences(old_capacity, new_capacity),
        "largest_new_capacity_changes": top_differences(old_new_capacity, new_new_capacity),
        "qualification": {
            "candidate_optimal": True,
            "reserve_satisfied": all(row["lhs_gw"] <= 1e-7 for row in reserve),
            "disabled_routes_zero": all(value <= 1e-7 for value in closed_max.values()),
            "promotion_allowed": all(row["lhs_gw"] <= 1e-7 for row in reserve) and all(value <= 1e-7 for value in closed_max.values()),
            "optimizer_runs": 1,
        },
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT), "objective": report["objective"],
        "reserve": {key: report["reserve"][key] for key in ("all_rows_satisfied", "minimum_headroom_gw", "binding_years")},
        "direct_checks": report["direct_checks"] | {"direct_technology_activity": "retained in report", "direct_technology_capacity": "retained in report"},
        "largest_activity_changes": report["largest_activity_changes"][:10],
        "qualification": report["qualification"],
    }, indent=2))


if __name__ == "__main__":
    main()

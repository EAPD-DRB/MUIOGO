#!/usr/bin/env python3
"""Finalize r8 post-solve publications and its blocked validation record."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "WebAPP" / "DataStorage" / ".Philippines_v22-transition-scope-only-candidate-r8"
CONTROL = ROOT / "WebAPP" / "DataStorage" / ".Philippines_v21-power-allocation-candidate-r4"
RUNS = {
    "BASE": "TRANSITION_SCOPE_V22_BASE",
    "COAL_PHASEOUT": "TRANSITION_SCOPE_V22_COAL_PHASEOUT",
    "RE": "TRANSITION_SCOPE_V22_RE",
    "EV": "TRANSITION_SCOPE_V22_EV",
}
HEAT_IAR = {
    "PHL_AGR_HEAT_OIL": ("PHL_PRO_OIL", 1.123595506),
    "PHL_AGR_HEAT_NG": ("PHL_PRO_NG", 1.123595506),
    "PHL_AGR_HEAT_ELE": ("PHL_AGR_ELE", 1.0),
    "PHL_AGR_HEAT_COAL": ("PHL_PRO_COAL", 1.123595506),
    "PHL_AGR_HEAT_BIOM": ("PHL_PRO_BIOM", 1.123595506),
}
BASELINE_OBJECTIVE = 369746369.55929643


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def activity(run: Path):
    values = {}
    with (run / "csv" / "TotalAnnualTechnologyActivityByMode.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            key = row["t"], row["y"]
            values[key] = values.get(key, 0.0) + float(row["TotalAnnualTechnologyActivityByMode"])
    return values


def publish_heat(run: Path):
    values = activity(run)
    rows = []
    for year in map(str, range(2020, 2054)):
        total = sum(values.get((tech, year), 0.0) * ratio for tech, (_, ratio) in HEAT_IAR.items())
        for tech, (commodity, ratio) in HEAT_IAR.items():
            useful = values.get((tech, year), 0.0)
            rows.append({
                "year": year, "technology": tech, "input_commodity": commodity,
                "useful_heat_pj": useful, "input_activity_ratio": ratio,
                "input_energy_pj": useful * ratio,
                "input_energy_share": useful * ratio / total if total else 0.0,
                "free_energy_violation": useful > 1e-9 and useful * ratio <= 1e-12,
            })
    path = run / "agriculture_heat_all_routes.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    return path, rows


def generated_modes(path: Path):
    pattern = re.compile(r"^set MODEperTECHNOLOGY\[([^]]+)\]:=\s*(.*?)\s*;$", re.M)
    return {tech: frozenset(values.split()) for tech, values in pattern.findall(path.read_text(encoding="utf-8"))}


def main():
    records, heat_summary = {}, {}
    for scenario, name in RUNS.items():
        run = CASE / "res" / name
        record = json.loads((run / "optimization_record.json").read_text(encoding="utf-8"))
        records[scenario] = record
        if str(record.get("status", "")).startswith("Optimal"):
            path, rows = publish_heat(run)
            record["agriculture_heat_all_routes_sha256"] = sha(path)
            (run / "optimization_record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            by_year = {}
            for year in ("2020", "2024", "2030", "2050"):
                selected = [x for x in rows if x["year"] == year]
                by_year[year] = {
                    "useful_heat_pj": sum(x["useful_heat_pj"] for x in selected),
                    "input_energy_pj": sum(x["input_energy_pj"] for x in selected),
                    "useful_heat_by_technology_pj": {x["technology"]: x["useful_heat_pj"] for x in selected},
                }
            heat_summary[scenario] = by_year
    re_default = json.loads((CASE/"res"/RUNS["RE"]/"optimization_record_default_timed_out.json").read_text())
    control = json.loads((CONTROL/"res"/"POWER_ALLOCATION_V21_RE_CONTROL"/"optimization_record.json").read_text())
    base_objective = float(records["BASE"]["status"].split()[-1])
    old_modes = generated_modes(CONTROL/"res"/"POWER_ALLOCATION_V21_BASE"/"data_processed.txt")
    new_modes = generated_modes(CASE/"res"/RUNS["BASE"]/"data_processed.txt")
    matrix_report = json.loads((CASE/"res"/RUNS["BASE"]/"generation_matrix_report.json").read_text())
    build_manifest = json.loads((CASE/"documentation"/"integrated_repair_v22_build_manifest.json").read_text())
    source_hashes_match = all(
        sha(CASE/name) == digest for name, digest in build_manifest["candidate_hashes"].items()
    )
    summary = {
        "schema": "philippines-v22-transition-scope-r8-validation-v1",
        "promotion_allowed": False,
        "promotion_rule": "BASE must solve first; only then COAL_PHASEOUT, RE and EV run in parallel; all four must be proven optimal from the same candidate source.",
        "candidate_scenarios": {k: v["status"] for k, v in records.items()},
        "optimal_candidate_scenarios": [k for k, v in records.items() if str(v["status"]).startswith("Optimal")],
        "failed_candidate_scenarios": [k for k, v in records.items() if not str(v["status"]).startswith("Optimal")],
        "optimizer_executions": [
            {"case": "r8", "scenario": "BASE", "algorithm": "default", "status": records["BASE"]["status"], "seconds": records["BASE"]["solve_seconds"]},
            {"case": "r8", "scenario": "COAL_PHASEOUT", "algorithm": "default concurrent", "status": records["COAL_PHASEOUT"]["status"], "seconds": records["COAL_PHASEOUT"]["solve_seconds"]},
            {"case": "r8", "scenario": "RE", "algorithm": "default concurrent", "status": re_default["status"], "seconds": re_default["solve_seconds"]},
            {"case": "r8", "scenario": "EV", "algorithm": "default concurrent", "status": records["EV"]["status"], "seconds": records["EV"]["solve_seconds"]},
            {"case": "r8", "scenario": "RE", "algorithm": "primal diagnostic", "status": records["RE"]["status"], "seconds": records["RE"]["solve_seconds"]},
            {"case": "v21 r4 control", "scenario": "RE", "algorithm": "default", "status": control["status"], "seconds": control["solve_seconds"]},
        ],
        "base_objective": base_objective,
        "accepted_v21_base_objective": BASELINE_OBJECTIVE,
        "base_objective_change": base_objective - BASELINE_OBJECTIVE,
        "base_objective_change_percent": 100 * (base_objective / BASELINE_OBJECTIVE - 1),
        "candidate_source_hashes_match_build_manifest": source_hashes_match,
        "matrix": matrix_report["matrix_dimensions"],
        "generated_mode_sets": {"v21_technologies": len(old_modes), "r8_technologies": len(new_modes), "membership_identical": old_modes == new_modes},
        "agriculture_heat": heat_summary,
        "known_limitations": [
            "RE did not prove optimal; r8 is not promotable.",
            "v21 RE also timed out, so the RE numerical/UDC issue predates r8 but remains unresolved.",
            "DOE 2024 AFF energy is a broader sector boundary than agriculture heat and is benchmark-only.",
            "Groundwater remains zero and unqualified pending physical infrastructure and aquifer data.",
            "Livestock is outside the physical model; national-agriculture climate completeness is not claimed.",
            "The wider biofuel, power reliability/timing, cooling, T&D and availability repairs remain deferred.",
        ],
    }
    doc = CASE / "documentation" / "TRANSITION_SCOPE_R8_VALIDATION_SUMMARY.json"
    doc.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

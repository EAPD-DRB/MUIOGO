#!/usr/bin/env python3
"""Deterministically validate the Philippines v18 RE nuclear-cap candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


RE_SCENARIO = "SC_w03qj"
BASE_SCENARIO = "SC_0"
TECHS = {"PHL_POW_PP_NU": "TEC_yv6yo", "PHL_POW_PP_NUSMR": "TEC_fa6fe"}
MILESTONES = {2032: 1.2, 2035: 2.4, 2050: 4.8}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_by_tech(parameter: dict, scenario: str) -> dict:
    return {row["TechId"]: row for row in parameter[scenario]}


def resolved_value(ryt: dict, scenario_order: list[str], tech_id: str, year: int):
    value = None
    for scenario in scenario_order:
        row = rows_by_tech(ryt["TAMaxCI"], scenario)[tech_id]
        if row[str(year)] is not None:
            value = row[str(year)]
    return value


def parse_solution(run_dir: Path, resolved: dict[str, dict[int, float]]) -> dict:
    status = (run_dir / "results.txt").read_text(encoding="utf-8").splitlines()[0]
    if not status.startswith("Optimal - objective value"):
        raise AssertionError(f"Candidate did not solve optimally: {status}")
    values: dict[str, float] = {}
    row_pattern = re.compile(r"^\s*\d+\s+(\S+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$")
    with (run_dir / "results.txt").open(encoding="utf-8") as stream:
        next(stream)
        for line in stream:
            match = row_pattern.match(line)
            if match:
                values[match.group(1)] = float(match.group(2))

    new_capacity: dict[str, dict[int, float]] = {}
    total_capacity: dict[str, dict[int, float]] = {}
    for tech in TECHS:
        new_capacity[tech] = {}
        total_capacity[tech] = {}
        for year in range(2020, 2054):
            new_name = f"NewCapacity(RE1,{tech},{year})"
            total_name = f"TotalCapacityAnnual(RE1,{tech},{year})"
            if new_name not in values or total_name not in values:
                raise AssertionError(f"Missing result variable for {tech}, {year}")
            new_capacity[tech][year] = values[new_name]
            total_capacity[tech][year] = values[total_name]
            if year < 2032 and abs(values[new_name]) > 1e-8:
                raise AssertionError(f"Retroactive or early nuclear build: {new_name}={values[new_name]}")
            if year >= 2026 and values[new_name] > resolved[tech][year] + 1e-8:
                raise AssertionError(f"Construction cap violated: {new_name}={values[new_name]}")

    milestone_capacity = {}
    milestone_rows = {}
    for year, target in MILESTONES.items():
        combined = sum(total_capacity[tech][year] for tech in TECHS)
        if abs(combined - target) > 1e-7:
            raise AssertionError(f"Nuclear target mismatch in {year}: {combined} != {target}")
        row_name = f"UDC2_UserDefinedConstraintEquality(RE1,NUCLEAR_CAPACITY_TARGET,{year})"
        row_value = values.get(row_name)
        if row_value is None or abs(row_value + target) > 1e-7:
            raise AssertionError(f"Unexpected reported target-row activity: {row_name}={row_value}")
        milestone_capacity[year] = {
            tech: total_capacity[tech][year] for tech in TECHS
        } | {"combined": combined}
        milestone_rows[year] = row_value

    cbc_log = (run_dir / "cbc.log").read_text(encoding="utf-8")
    final = re.search(
        r"Optimal objective\s+([-+0-9.eE]+)\s+-\s+(\d+) iterations time ([0-9.]+).*?"
        r"Total time \(CPU seconds\):\s+([0-9.]+)\s+\(Wallclock seconds\):\s+([0-9.]+)",
        cbc_log,
        re.DOTALL,
    )
    if not final:
        raise AssertionError("Could not parse final CBC optimality and timing lines")
    glpk_log = (run_dir / "glpk_check.log").read_text(encoding="utf-8")
    matrix_match = re.search(
        r"Number of rows\s*=\s*(\d+).*?Number of columns\s*=\s*(\d+).*?"
        r"Number of non-zeros \(matrix\)\s*=\s*(\d+).*?"
        r"Number of non-zeros \(objrow\)\s*=\s*(\d+)",
        glpk_log,
        re.DOTALL,
    )
    if not matrix_match:
        raise AssertionError("Could not parse GLPK matrix characteristics")
    return {
        "status": status,
        "objective": float(final.group(1)),
        "iterations": int(final.group(2)),
        "cbc_cpu_seconds": float(final.group(4)),
        "cbc_wall_seconds": float(final.group(5)),
        "matrix": {
            "rows": int(matrix_match.group(1)),
            "columns": int(matrix_match.group(2)),
            "matrix_nonzeros": int(matrix_match.group(3)),
            "objective_nonzeros": int(matrix_match.group(4)),
        },
        "new_capacity_gw": {
            year: {tech: new_capacity[tech][year] for tech in TECHS}
            for year in range(2032, 2054)
            if any(abs(new_capacity[tech][year]) > 1e-8 for tech in TECHS)
        },
        "milestone_capacity_gw": milestone_capacity,
        "target_row_activity": milestone_rows,
        "pre_2032_new_capacity_zero": True,
        "all_new_capacity_within_resolved_caps": True,
        "results_sha256": digest(run_dir / "results.txt"),
        "lp_sha256": digest(run_dir / "lp.lp"),
    }


def validate(control: Path, candidate: Path, run_dir: Path | None = None) -> dict:
    control_files = {path.name: digest(path) for path in control.glob("*.json")}
    candidate_files = {path.name: digest(path) for path in candidate.glob("*.json")}
    if control_files.keys() != candidate_files.keys():
        raise AssertionError("Top-level source JSON inventory changed")
    changed = sorted(name for name in control_files if control_files[name] != candidate_files[name])
    if changed != ["RYT.json"]:
        raise AssertionError(f"Expected only RYT.json to change, found {changed}")

    original = load(control / "RYT.json")
    proposed = load(candidate / "RYT.json")
    restored = load(candidate / "RYT.json")
    original_re = rows_by_tech(original["TAMaxCI"], RE_SCENARIO)
    restored_re = rows_by_tech(restored["TAMaxCI"], RE_SCENARIO)
    for year in range(2032, 2054):
        restored_re[TECHS["PHL_POW_PP_NU"]][str(year)] = original_re[TECHS["PHL_POW_PP_NU"]][str(year)]
    for year in range(2032, 2035):
        restored_re[TECHS["PHL_POW_PP_NUSMR"]][str(year)] = original_re[TECHS["PHL_POW_PP_NUSMR"]][str(year)]
    if restored != original:
        raise AssertionError("RYT.json contains a change outside the approved 25 cells")

    proposed_re = rows_by_tech(proposed["TAMaxCI"], RE_SCENARIO)
    nu = proposed_re[TECHS["PHL_POW_PP_NU"]]
    smr = proposed_re[TECHS["PHL_POW_PP_NUSMR"]]
    for year in range(2032, 2035):
        if nu[str(year)] != 1.2 or smr[str(year)] != 0.3:
            raise AssertionError(f"Incorrect 2032-2034 nuclear cap at {year}")
    for year in range(2035, 2054):
        if nu[str(year)] is not None:
            raise AssertionError(f"Conventional nuclear must inherit BASE from 2035: {year}")

    run_data = load(candidate / "view" / "resData.json")
    tomorrowland = next(row for row in run_data["osy-cases"] if row["Case"] == "TOMORROWLAND")
    active = [row["ScenarioId"] for row in tomorrowland["Scenarios"] if row["Active"]]
    if active != ["SC_0", "SC_3hgjb", "SC_w03qj", "SC_huc7i"]:
        raise AssertionError(f"Unexpected TOMORROWLAND scenario order: {active}")

    resolved: dict[str, dict[int, float]] = {}
    for tech, tech_id in TECHS.items():
        resolved[tech] = {year: resolved_value(proposed, active, tech_id, year) for year in range(2026, 2054)}
    for year in range(2026, 2032):
        if any(resolved[tech][year] != 0 for tech in TECHS):
            raise AssertionError(f"Nuclear commissioning opened before 2032: {year}")
    for year in range(2032, 2054):
        if resolved["PHL_POW_PP_NU"][year] != 1.2:
            raise AssertionError(f"Unexpected conventional nuclear resolved cap in {year}")
        expected_smr = 0.3 if year < 2040 else 0.6
        if resolved["PHL_POW_PP_NUSMR"][year] != expected_smr:
            raise AssertionError(f"Unexpected SMR resolved cap in {year}")

    commissioning_room = {}
    for milestone, target in MILESTONES.items():
        room = sum(sum(resolved[tech][year] for tech in TECHS) for year in range(2032, milestone + 1))
        if room < target:
            raise AssertionError(f"Cap envelope cannot reach {target} GW by {milestone}: {room}")
        commissioning_room[milestone] = room

    report = {
        "status": "pass",
        "changed_source_files": changed,
        "approved_cell_count": 25,
        "unchanged_top_level_json_count": len(control_files) - 1,
        "tomorrowland_active_scenarios": active,
        "resolved_caps_gw_per_year": {
            "2026-2031": {tech: resolved[tech][2031] for tech in TECHS},
            "2032-2034": {tech: resolved[tech][2032] for tech in TECHS},
            "2035-2039": {tech: resolved[tech][2035] for tech in TECHS},
            "2040-2053": {tech: resolved[tech][2040] for tech in TECHS},
        },
        "cumulative_commissioning_room_gw": commissioning_room,
        "milestones_unchanged_by_source_diff": True,
        "candidate_ryt_sha256": digest(candidate / "RYT.json"),
    }
    if run_dir is not None:
        report["optimizer_run_count"] = 1
        report["candidate_solve"] = parse_solution(run_dir, resolved)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate(
        args.control.resolve(),
        args.candidate.resolve(),
        args.run_dir.resolve() if args.run_dir else None,
    )
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()

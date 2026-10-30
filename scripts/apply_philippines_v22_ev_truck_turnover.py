#!/usr/bin/env python3
"""Repair v22 truck turnover headroom and locate the BASE EV ban in TAMaxCI."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "scripts" / "philippines_v22_ev_truck_turnover_inputs.json"
YEARS = tuple(str(year) for year in range(2020, 2054))


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".codex-tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_by_id(payload: dict[str, Any], parameter: str, scenario: str,
               id_field: str) -> dict[str, dict[str, Any]]:
    rows = payload[parameter][scenario]
    result = {row[id_field]: row for row in rows}
    if len(result) != len(rows):
        raise AssertionError(f"duplicate {id_field} in {parameter}.{scenario}")
    return result


def constraint_rows(payload: dict[str, Any], parameter: str, scenario: str,
                    constraint: str) -> dict[str, dict[str, Any]]:
    rows = [row for row in payload[parameter][scenario] if row["ConId"] == constraint]
    result = {row["TechId"]: row for row in rows}
    if len(result) != len(rows):
        raise AssertionError(f"duplicate technology in {parameter}.{scenario}.{constraint}")
    return result


def append_ledger(path: Path, key: str, values: dict[str, str]) -> None:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if not fieldnames or key not in values:
        raise AssertionError((path, key))
    if values[key] in {row[key] for row in rows}:
        raise AssertionError(f"duplicate ledger identifier {values[key]} in {path}")
    unknown = set(values) - set(fieldnames)
    if unknown:
        raise AssertionError((path, unknown))
    rows.append({name: values.get(name, "") for name in fieldnames})
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_truck_envelopes(case: Path, spec: dict[str, Any]) -> dict[str, dict[str, float]]:
    gen = read(case / "genData.json")
    ryt = read(case / "RYT.json")
    ryc = read(case / "RYC.json")
    rt = read(case / "RT.json")
    base = next(row["ScenarioId"] for row in gen["osy-scenarios"]
                if row["Scenario"] == spec["base_scenario"])
    tech_id = {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}
    commodity_id = {row["Comm"]: row["CommId"] for row in gen["osy-comm"]}
    residual = rows_by_id(ryt, "RC", base, "TechId")
    demand = rows_by_id(ryc, "SAD", base, "CommId")
    life = rt["OL"][base][0]
    cau = rt["CAU"][base][0]
    result: dict[str, dict[str, float]] = {}

    for group in spec["truck_groups"]:
        members = [tech_id[name] for name in group["members"]]
        service = commodity_id[group["service_commodity"]]
        minimum_cau = min(float(cau[technology]) for technology in members)
        initial_retirement: dict[str, float] = {}
        for index, year in enumerate(YEARS):
            if index == 0:
                initial_retirement[year] = 0.0
            else:
                prior = YEARS[index - 1]
                initial_retirement[year] = sum(
                    max(0.0, float(residual[technology][prior]) - float(residual[technology][year]))
                    for technology in members
                )
        for technology in members:
            series: dict[str, float] = {}
            operational_life = int(float(life[technology]))
            for index, year in enumerate(YEARS):
                if index == 0:
                    ceiling = 0.0
                else:
                    prior = YEARS[index - 1]
                    growth = max(0.0, float(demand[service][year]) - float(demand[service][prior]))
                    ceiling = initial_retirement[year] + growth / minimum_cau
                    replacement_year = str(int(year) - operational_life)
                    if replacement_year in series:
                        ceiling += series[replacement_year]
                series[year] = round(ceiling, 12)
            result[technology] = series
    return result


def update_ledgers(case: Path, manifest_path: Path, manifest_sha: str) -> None:
    ledger = case / "data_sources"
    append_ledger(ledger / "SOURCES.csv", "source_id", {
        "source_id": "SRC_PHL_V22_EV_TRUCK_FORMULATION",
        "provider": "MUIOGO",
        "product": "Philippines v22 EV availability and truck-turnover equation audit",
        "edition": "2026-08-24", "reference_period": "2020-2053",
        "geography": "Philippines",
        "variable": "EV scenario availability; truck residual retirement, service growth, CAU and TAMaxCI",
        "source_unit": "10^3 vehicles/year;10^9 service-km/year",
        "exact_locator": "scripts/philippines_v22_ev_truck_turnover_inputs.json; data_sources/snapshots/ev_truck_turnover_build_manifest.json",
        "access_date": "2026-08-24", "license": "Repository license",
        "sha256": manifest_sha,
        "local_file": str(manifest_path.relative_to(ledger)),
        "notes": "Internal equation-first audit using full-precision source parameters; observed powertrain shares are not imposed.",
    })
    append_ledger(ledger / "ASSUMPTIONS.csv", "assumption_id", {
        "assumption_id": "ASM_PHL_V22_BASE_ZERO_EV",
        "statement": "BASE is the full-horizon no-EV counterfactual: the 11 technologies in CO_sdx29 have zero residual stock and may not build; policy scenarios other than EV inherit the restriction, while EV explicitly reopens them.",
        "central_value": "0", "unit": "10^3 vehicles/year",
        "evidence_source_ids": "SRC_PHL_V22_EV_TRUCK_FORMULATION",
        "rationale": "Defines the requested comparison through technology availability rather than an aggregate zero-activity equality.",
        "notes": "The post-2023 restriction is a scenario definition, not an assertion about observed future adoption.",
    })
    append_ledger(ledger / "ASSUMPTIONS.csv", "assumption_id", {
        "assumption_id": "ASM_PHL_V22_TRUCK_REPLACEMENT_ENVELOPE",
        "statement": "Each truck powertrain receives enough annual entry headroom to cover scheduled initial-stock retirement, positive class-service growth at the minimum class CAU, and replacement of its own expiring allowed vintages.",
        "central_value": "see CALC_PHL_V22_TRUL_TAMAXCI and CALC_PHL_V22_TRUH_TAMAXCI",
        "unit": "10^3 vehicles/year", "evidence_source_ids": "SRC_PHL_V22_EV_TRUCK_FORMULATION;SRC_MUIO_FORMULATION;SRC_PHL_V14_LTO_AR_2020",
        "rationale": "Removes a deterministic capacity shortage without fixing diesel activity, fuel shares or powertrain choice.",
        "notes": "This is an optimistic per-technology feasibility envelope, not an aggregate observed sales cap.",
    })
    for suffix, group in (("TRUL", "light trucks"), ("TRUH", "heavy trucks")):
        append_ledger(ledger / "CALCULATIONS.csv", "calculation_id", {
            "calculation_id": f"CALC_PHL_V22_{suffix}_TAMAXCI",
            "formula": "scheduled initial-stock retirement + max(0, SAD[y]-SAD[y-1])/minimum class CAU + allowed vintage reaching operational life",
            "source_ids": "SRC_PHL_V22_EV_TRUCK_FORMULATION;SRC_MUIO_FORMULATION",
            "assumption_ids": "ASM_PHL_V22_TRUCK_REPLACEMENT_ENVELOPE",
            "input_values": f"full-precision RC, SAD, CAU and OL for {group}",
            "input_units": "10^3 vehicles;10^9 service-km/year;10^9 service-km/(10^3 vehicles);years",
            "output_value": "annual series retained in ev_truck_turnover_build_manifest.json",
            "output_unit": "10^3 vehicles/year",
            "script_path": "scripts/apply_philippines_v22_ev_truck_turnover.py",
            "script_version": "v1",
            "notes": "No activity, market share or historical technology outcome is constrained.",
        })
    append_ledger(ledger / "CALCULATIONS.csv", "calculation_id", {
        "calculation_id": "CALC_PHL_V22_EV_SCENARIO_REOPEN",
        "formula": "EV TAMaxCI override = repaired truck envelope for electric/PHEV trucks; unchanged former BASE envelope for the other listed EV/PHEV technologies",
        "source_ids": "SRC_PHL_V22_EV_TRUCK_FORMULATION",
        "assumption_ids": "ASM_PHL_V22_BASE_ZERO_EV;ASM_PHL_V22_TRUCK_REPLACEMENT_ENVELOPE",
        "input_values": "11 CO_sdx29 members; SC_0 and SC_huc7i source rows",
        "input_units": "technology IDs;10^3 vehicles/year",
        "output_value": "explicit SC_huc7i TAMaxCI series",
        "output_unit": "10^3 vehicles/year",
        "script_path": "scripts/apply_philippines_v22_ev_truck_turnover.py", "script_version": "v1",
        "notes": "The existing EV equality trajectory and Tag remain unchanged.",
    })
    maps = [
        {
            "map_id": "MAP_PHL_V22_BASE_ZERO_EV", "model_file": "RYT.json",
            "parameter": "TAMaxCI", "entity": "11 CO_sdx29 EV/PHEV technologies",
            "scenario": "BASE with inheritance by COAL_PHASEOUT and RE", "years": "2020-2053",
            "value_or_expression": "0", "model_unit": "10^3 vehicles/year",
            "evidence_ids": "ASM_PHL_V22_BASE_ZERO_EV;CALC_PHL_V22_EV_SCENARIO_REOPEN",
            "evidence_type": "counterfactual technology-availability restriction",
            "notes": "All 11 residual-capacity series are zero; TAMaxCI=0 is sufficient to guarantee zero capacity and activity.",
        },
        {
            "map_id": "MAP_PHL_V22_TRUCK_TURNOVER", "model_file": "RYT.json",
            "parameter": "TAMaxCI", "entity": "TURN_TRUL;TURN_TRUH members",
            "scenario": "BASE for non-EV; EV explicit for EV/PHEV", "years": "2020-2053",
            "value_or_expression": "CALC_PHL_V22_TRUL_TAMAXCI;CALC_PHL_V22_TRUH_TAMAXCI",
            "model_unit": "10^3 vehicles/year",
            "evidence_ids": "ASM_PHL_V22_TRUCK_REPLACEMENT_ENVELOPE;CALC_PHL_V22_TRUL_TAMAXCI;CALC_PHL_V22_TRUH_TAMAXCI",
            "evidence_type": "derived non-forcing physical envelope",
            "notes": "The same class envelope is available to any permitted powertrain; aggregate additions are not capped.",
        },
        {
            "map_id": "MAP_PHL_V22_EV_REOPEN", "model_file": "RYT.json;RYTCn.json;RYCn.json",
            "parameter": "TAMaxCI;CAM;UCC", "entity": "CO_sdx29 and its 11 members",
            "scenario": "EV", "years": "2020-2053",
            "value_or_expression": "explicit build-envelope restoration; existing CAM and exact UCC trajectory retained",
            "model_unit": "10^3 vehicles/year;UDC activity unit",
            "evidence_ids": "CALC_PHL_V22_EV_SCENARIO_REOPEN",
            "evidence_type": "scenario override",
            "notes": "Constraint Tag=1 and all UCC values are unchanged.",
        },
        {
            "map_id": "MAP_PHL_V22_EV_UDC_SCOPE", "model_file": "RYTCn.json",
            "parameter": "CAM", "entity": "CO_sdx29 and its 11 members",
            "scenario": "BASE=0; EV explicit", "years": "2020-2053",
            "value_or_expression": "BASE CAM=0; EV CAM restores former effective series",
            "model_unit": "activity coefficient",
            "evidence_ids": "ASM_PHL_V22_BASE_ZERO_EV",
            "evidence_type": "constraint-scope correction",
            "notes": "The UDC object remains for EV; it no longer implements the BASE ban.",
        },
    ]
    for values in maps:
        append_ledger(ledger / "MODEL_MAP.csv", "map_id", values)
    append_ledger(ledger / "GAPS.csv", "item", {
        "item": "Truck stock, survival, utilization and powertrain availability",
        "why_absent": "The light/heavy freight stocks remain model-derived and aggregate LTO categories do not map one-to-one to freight classes; fuel-specific registrations, age cohorts and infrastructure availability are not retained.",
        "upgrade_source": "LTO body-type/use/fuel microdata, deregistrations and age cohorts reconciled to freight service; observed vehicle-km and load factors; NG, hydrogen and EV market/infrastructure start dates.",
        "priority": "high",
        "notes": "The repair removes deterministic scarcity but does not claim the resulting endogenous non-EV powertrain mix reproduces history.",
    })
    append_ledger(ledger / "CHANGES.csv", "change_id", {
        "change_id": "CHG_PHL_V22_EV_TRUCK_TURNOVER_20260824", "date": str(date.today()), "class": "B",
        "description": "Moved the requested full-horizon BASE no-EV restriction into technology investment availability, explicitly reopened EV technologies in the existing EV scenario, and replaced defective light/heavy truck registration-indexed limits with retirement-plus-growth envelopes.",
        "model_objects": "RYT.json TAMaxCI;RYTCn.json CAM;CO_sdx29;TURN_TRUL;TURN_TRUH",
        "evidence_path": "documentation/MODEL_FIXES_EV_TRUCK_TURNOVER_2026-08-24.md;data_sources/snapshots/ev_truck_turnover_build_manifest.json",
        "map_rows_affected": "MAP_PHL_V22_BASE_ZERO_EV;MAP_PHL_V22_TRUCK_TURNOVER;MAP_PHL_V22_EV_REOPEN;MAP_PHL_V22_EV_UDC_SCOPE",
        "resolve_status": "candidate_pending_four_scenario_validation", "author": "Codex",
        "notes": "No activity/share/diesel target is added. BASE must solve first; the other three scenarios may run concurrently only after a proven BASE optimum.",
    })


def apply(case: Path) -> dict[str, Any]:
    spec = read(SPEC_PATH)
    gen = read(case / "genData.json")
    if gen["osy-casename"] != "Philippines_v22":
        raise AssertionError(gen["osy-casename"])
    scenario_id = {row["Scenario"]: row["ScenarioId"] for row in gen["osy-scenarios"]}
    base = scenario_id[spec["base_scenario"]]
    ev = scenario_id[spec["ev_scenario"]]
    tech_name = {row["TechId"]: row["Tech"] for row in gen["osy-tech"]}
    constraint = next(row for row in gen["osy-constraints"]
                      if row["ConId"] == spec["constraint_id"])
    ev_technologies = tuple(constraint["CM"])
    if len(ev_technologies) != 11 or constraint["Tag"] != 1:
        raise AssertionError(constraint)

    source_files = sorted(case.glob("*.json"))
    before_hashes = {path.name: digest(path) for path in source_files}
    ryt = read(case / "RYT.json")
    rytcn = read(case / "RYTCn.json")
    rycn_before = digest(case / "RYCn.json")
    base_tamaxci = rows_by_id(ryt, "TAMaxCI", base, "TechId")
    ev_tamaxci = rows_by_id(ryt, "TAMaxCI", ev, "TechId")
    residual = rows_by_id(ryt, "RC", base, "TechId")
    original_base = {technology: {year: base_tamaxci[technology][year] for year in YEARS}
                     for technology in ev_technologies}
    for technology in ev_technologies:
        if any(abs(float(residual[technology][year])) > 1e-12 for year in YEARS):
            raise AssertionError(f"nonzero EV residual stock: {tech_name[technology]}")

    truck_envelopes = build_truck_envelopes(case, spec)
    truck_technologies = set(truck_envelopes)
    for technology, series in truck_envelopes.items():
        for year, value in series.items():
            base_tamaxci[technology][year] = 0.0 if technology in ev_technologies else value
    for technology in ev_technologies:
        for year in YEARS:
            base_tamaxci[technology][year] = 0.0
            ev_tamaxci[technology][year] = (
                truck_envelopes[technology][year]
                if technology in truck_technologies else original_base[technology][year]
            )

    base_cam = constraint_rows(rytcn, "CAM", base, spec["constraint_id"])
    ev_cam = constraint_rows(rytcn, "CAM", ev, spec["constraint_id"])
    original_cam = {technology: {year: base_cam[technology][year] for year in YEARS}
                    for technology in ev_technologies}
    for technology in ev_technologies:
        for year in YEARS:
            base_cam[technology][year] = 0
            ev_cam[technology][year] = original_cam[technology][year]

    write(case / "RYT.json", ryt)
    write(case / "RYTCn.json", rytcn)
    after_hashes = {path.name: digest(path) for path in source_files}
    changed = sorted(name for name in before_hashes if before_hashes[name] != after_hashes[name])
    if changed != ["RYT.json", "RYTCn.json"] or digest(case / "RYCn.json") != rycn_before:
        raise AssertionError(changed)

    manifest = {
        "schema": "philippines-v22-ev-truck-turnover-build-v1",
        "date": str(date.today()), "case": str(case),
        "changed_source_files": changed,
        "before_sha256": before_hashes, "after_sha256": after_hashes,
        "constraint": {"id": spec["constraint_id"], "tag_before_after": 1,
                       "UCC_changed": False, "base_CAM": 0,
                       "EV_CAM": "former effective BASE CAM explicitly restored"},
        "ev_technologies": [{"id": technology, "name": tech_name[technology]}
                            for technology in ev_technologies],
        "truck_envelopes": {
            tech_name[technology]: series for technology, series in truck_envelopes.items()
        },
        "classification": spec["classification"],
        "optimizer_runs": 0,
    }
    manifest_path = case / "data_sources" / "snapshots" / "ev_truck_turnover_build_manifest.json"
    write(manifest_path, manifest)
    update_ledgers(case, manifest_path, digest(manifest_path))
    print(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    args = parser.parse_args()
    apply(args.case.resolve())


if __name__ == "__main__":
    main()

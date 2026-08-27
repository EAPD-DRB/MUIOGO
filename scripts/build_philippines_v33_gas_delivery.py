#!/usr/bin/env python3
"""Build the source-only Philippines v33 gas-delivery candidate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


YEARS = [str(year) for year in range(2020, 2054)]
OLD_GAS = "PHL_POW_CHP_NG_OLD"
REFERENCE_GAS = "PHL_POW_PP_NGCC"
END_USE_TECHS = (
    "PHL_AGR_HEAT_NG",
    "PHL_INDU_OTHHPH_NG",
    "PHL_INDU_OTHHPH_NG_CCS",
    "PHL_INDU_OTHLPH_NG",
    "PHL_POW_BH2_NG",
    "PHL_POW_GH2_NG",
    "PHL_SER_HEAT_NG",
    "PHL_TRA_23WHEEL_NG",
    "PHL_TRA_BUS_NG",
    "PHL_TRA_CAR_NG",
    "PHL_TRA_TRUH_NG",
    "PHL_TRA_TRUL_NG",
    "PHL_TRA_VAN_NG",
    "PHL_HOU_COOK_NG",
)
GAS_COMMODITY = "PHL_PRO_NG"
DELIVERY_ADDER = 8.2  # MUSD/PJ of gas input
EXPECTED_VOM = 0.7050283513976835  # MUSD/PJ of activity
EPSILON_VC = 0.0001
EVIDENCE_RELATIVE = Path(
    "data_sources/evidence/v33_gas_delivery/elizabethtown_cng_vs_traditional_fuels.html"
)
EVIDENCE_SHA256 = "5a9de93aa4ae8c3768de6decf8a4b9e274c207d12c9a925e96bf63712cb6bc4e"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def one(rows: list[dict], **coordinates: object) -> dict:
    matches = [row for row in rows if all(row.get(key) == value for key, value in coordinates.items())]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one row at {coordinates}, found {len(matches)}")
    return matches[0]


def append_unique(path: Path, key: str, values: list[dict[str, str]]) -> None:
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise RuntimeError(f"Missing CSV header: {path}")
        rows = list(reader)
    incoming = {row[key] for row in values}
    if incoming & {row[key] for row in rows}:
        raise RuntimeError(f"Duplicate provenance identifier in {path}: {sorted(incoming)}")
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows + [{name: row.get(name, "") for name in fieldnames} for row in values])


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    return parser.parse_args()


def main() -> None:
    case = arguments().case.resolve()
    gen_path = case / "genData.json"
    vc_path = case / "RYTM.json"
    iar_path = case / "RYTCM.json"
    evidence_path = case / EVIDENCE_RELATIVE
    if sha256(evidence_path) != EVIDENCE_SHA256:
        raise RuntimeError("Archived Elizabethtown evidence hash does not match")

    parent_hashes = {
        name: sha256(case / name)
        for name in ("genData.json", "RYTM.json", "RYTCM.json", "RYC.json", "RYT.json", "RYTs.json")
    }
    gen = json.loads(gen_path.read_text())
    if gen.get("osy-casename") != "Philippines_v32":
        raise RuntimeError(f"Unexpected parent identity: {gen.get('osy-casename')}")
    tech_ids = {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}
    comm_ids = {row["Comm"]: row["CommId"] for row in gen["osy-comm"]}
    required = {OLD_GAS, REFERENCE_GAS, *END_USE_TECHS}
    if not required <= set(tech_ids):
        raise RuntimeError(f"Missing technologies: {sorted(required - set(tech_ids))}")

    vc = json.loads(vc_path.read_text())
    iar = json.loads(iar_path.read_text())
    vc_rows = vc["VC"]["SC_0"]
    iar_rows = iar["IAR"]["SC_0"]
    ref_row = one(vc_rows, TechId=tech_ids[REFERENCE_GAS], MoId=1)
    if any(float(ref_row[year]) != EXPECTED_VOM for year in YEARS):
        raise RuntimeError("Reference NGCC VOM is not the exact expected sourced series")

    changes: list[dict[str, object]] = []
    old_gas_row = one(vc_rows, TechId=tech_ids[OLD_GAS], MoId=1)
    for year in YEARS:
        before = float(old_gas_row[year])
        if year in {"2020", "2021"}:
            # Preserve the inherited take-or-pay credit exactly; replace only the epsilon VOM.
            after = before + EXPECTED_VOM - EPSILON_VC
        else:
            if before != EPSILON_VC:
                raise RuntimeError(f"Unexpected old-gas VC in {year}: {before}")
            after = EXPECTED_VOM
        old_gas_row[year] = after
        changes.append({
            "technology": OLD_GAS, "year": int(year), "before": before, "after": after,
            "formula": "retain take-or-pay credit; replace epsilon VOM with sourced NGCC VOM",
        })

    gas_id = comm_ids[GAS_COMMODITY]
    for technology in END_USE_TECHS:
        vc_row = one(vc_rows, TechId=tech_ids[technology], MoId=1)
        iar_row = one(iar_rows, TechId=tech_ids[technology], CommId=gas_id, MoId=1)
        for year in YEARS:
            before = float(vc_row[year])
            gas_input = float(iar_row[year])
            after = before + gas_input * DELIVERY_ADDER
            vc_row[year] = after
            changes.append({
                "technology": technology, "year": int(year), "before": before, "after": after,
                "input_activity_ratio": gas_input,
                "formula": "VC_after = VC_before + gas IAR * 8.2 MUSD/PJ_input",
            })

    expected_changes = (1 + len(END_USE_TECHS)) * len(YEARS)
    if len(changes) != expected_changes:
        raise RuntimeError(f"Expected {expected_changes} changed cells, found {len(changes)}")
    for scenario, rows in vc["VC"].items():
        if scenario == "SC_0":
            continue
        for technology in (OLD_GAS, *END_USE_TECHS):
            row = one(rows, TechId=tech_ids[technology], MoId=1)
            if any(row[year] is not None for year in YEARS):
                raise RuntimeError(f"Policy override unexpectedly active for {technology} in {scenario}")

    gen["osy-casename"] = "Philippines_v33"
    gen["osy-desc"] = (
        "Philippines v33 candidate: v32 plus sourced legacy-gas VOM and a conservative "
        "delivered-gas cost proxy for every processed-gas route not producing electricity; "
        "take-or-pay retained and all outcomes endogenous."
    )
    gen["osy-date"] = "2026-08-27"
    gen_path.write_text(json.dumps(gen, indent=2) + "\n")
    vc_path.write_text(json.dumps(vc, indent=2) + "\n")

    data_sources = case / "data_sources"
    append_unique(data_sources / "SOURCES.csv", "source_id", [
        {
            "source_id": "SRC_PHL_V33_ETOWN_CNG_DELIVERY",
            "provider": "Elizabethtown Gas", "product": "CNG vs. Traditional Fuels",
            "edition": "archived 2026-08-27", "reference_period": "undated", "geography": "United States",
            "variable": "CNG commodity and delivered station price components", "source_unit": "USD/GGE",
            "exact_locator": "Archived page: CNG pricing and comparison sections",
            "url": "https://www.elizabethtowngas.com/business/business-service/natural-gas-vehicles/about-ngvs/cng-vs-traditional-fuels",
            "access_date": "2026-08-27", "license": "Provider terms",
            "sha256": EVIDENCE_SHA256, "local_file": EVIDENCE_RELATIVE.as_posix(),
            "notes": "Supports a delivery-cost range, not a Philippines-specific point estimate; used conservatively as a proxy.",
        },
        {
            "source_id": "SRC_PHL_V33_DOE_ENERGY_INVESTMENT_2024",
            "provider": "Philippines Department of Energy", "product": "2024 Energy Investment Kit",
            "edition": "2024", "reference_period": "2019-2024", "geography": "Philippines",
            "variable": "Natural-gas industry status and consuming sectors", "source_unit": "narrative; MMSCF",
            "exact_locator": "Conventional Energy / downstream natural gas section: current demand is solely power generation",
            "url": "https://doe.gov.ph/sites/default/files/pdf/e_ipo/2024-Energy-Investment-Kit.pdf",
            "access_date": "2026-08-27", "license": "Philippines government publication",
            "sha256": "", "local_file": "",
            "notes": "Official source establishes the calibration-period market boundary; the current DOE URL was discoverable but no longer returned the PDF for local archiving.",
        },
    ])
    append_unique(data_sources / "ASSUMPTIONS.csv", "assumption_id", [
        {
            "assumption_id": "ASM_PHL_V33_GAS_DELIVERY_MIDPOINT",
            "statement": "Use 8.2 MUSD/PJ_input as a conservative central delivery proxy for processed-gas routes that do not produce electricity.",
            "central_value": "8.2", "unit": "MUSD/PJ gas input",
            "evidence_source_ids": "SRC_PHL_V33_ETOWN_CNG_DELIVERY;SRC_PHL_V33_DOE_ENERGY_INVESTMENT_2024", "lower_bound": "6.17", "upper_bound": "10.29",
            "rationale": "Midpoint of the retained source-derived range, used as a floor where DOE reports no established non-power gas market.",
            "notes": "Proxy and sensitivity candidate; route-specific Philippine costs may differ. Energy-basis conversion is uncertain.",
        },
        {
            "assumption_id": "ASM_PHL_V33_NONPOWER_DELIVERY_PROXY",
            "statement": "Apply the same conservative proxy to every processed-gas conversion whose mapped output is not electricity because the model has no gas delivery stage.",
            "central_value": "8.2", "unit": "MUSD/PJ gas input",
            "evidence_source_ids": "SRC_PHL_V33_ETOWN_CNG_DELIVERY;SRC_PHL_V33_DOE_ENERGY_INVESTMENT_2024", "lower_bound": "", "upper_bound": "",
            "rationale": "Prevents production-node-price access while avoiding a structural network addition; electricity-producing gas routes are excluded by exact OAR mapping.",
            "notes": "Not a route-specific tariff; structural gas-network representation remains a gap.",
        },
        {
            "assumption_id": "ASM_PHL_V33_RETAIN_TAKE_OR_PAY",
            "statement": "Retain the inherited 2020-2021 take-or-pay contract credit and replace only the epsilon nonfuel VOM.",
            "central_value": "retained", "unit": "model formulation",
            "evidence_source_ids": "SRC_PHL_INHERITED_BASE_SNAPSHOT", "lower_bound": "", "upper_bound": "",
            "rationale": "Explicit user direction; no dispatch target or bound is introduced.",
            "notes": "Contract evidence and interpretation should be strengthened in a future provenance upgrade.",
        },
    ])
    append_unique(data_sources / "CALCULATIONS.csv", "calculation_id", [
        {
            "calculation_id": "CALC_PHL_V33_GAS_DELIVERY_ADDER",
            "formula": "VC_after[y] = VC_v32[y] + IAR_v32[y] * 8.2",
            "source_ids": "SRC_PHL_V33_ETOWN_CNG_DELIVERY;SRC_PHL_V33_DOE_ENERGY_INVESTMENT_2024", "assumption_ids": "ASM_PHL_V33_GAS_DELIVERY_MIDPOINT;ASM_PHL_V33_NONPOWER_DELIVERY_PROXY",
            "input_calculation_ids": "", "input_values": "row-specific v32 VC; row/year-specific v32 gas IAR; 8.2",
            "input_units": "MUSD/PJ activity; PJ gas/PJ activity; MUSD/PJ gas", "output_value": "row/year-specific",
            "output_unit": "MUSD/PJ activity", "script_path": "scripts/build_philippines_v33_gas_delivery.py",
            "script_version": "2026-08-27", "notes": "No IAR, efficiency, stock, bound, demand or equation change.",
        },
        {
            "calculation_id": "CALC_PHL_V33_OLD_GAS_VOM",
            "formula": "2020-21 VC_after = VC_v32 + 0.7050283513976835 - 0.0001; 2022-53 VC_after = 0.7050283513976835",
            "source_ids": "SRC_VC_EIA_AEO2023_T1;SRC_VC_WB_CPI_USA", "assumption_ids": "ASM_PHL_V33_RETAIN_TAKE_OR_PAY",
            "input_calculation_ids": "", "input_values": "v32 old-gas VC; v32 NGCC VOM", "input_units": "MUSD/PJ activity",
            "output_value": "year-specific", "output_unit": "MUSD/PJ activity",
            "script_path": "scripts/build_philippines_v33_gas_delivery.py", "script_version": "2026-08-27",
            "notes": "Uses the exact already-registered PHL_POW_PP_NGCC VOM; retains the inherited contract credit.",
        },
    ])
    map_rows = []
    for index, technology in enumerate((OLD_GAS, *END_USE_TECHS), start=1):
        expression = (
            "retain v32 take-or-pay credit in 2020-21 and use 0.7050283513976835 VOM"
            if technology == OLD_GAS else "VC_v32[y] + gas_IAR_v32[y] * 8.2"
        )
        evidence = (
            "CALC_PHL_V33_OLD_GAS_VOM;ASM_PHL_V33_RETAIN_TAKE_OR_PAY"
            if technology == OLD_GAS else "CALC_PHL_V33_GAS_DELIVERY_ADDER"
        )
        map_rows.append({
            "map_id": f"MAP_PHL_V33_GAS_VC_{index:02d}", "model_file": "RYTM.json", "parameter": "VC",
            "entity": technology, "mode": "1", "scenario": "SC_0", "years": "2020-2053",
            "value_or_expression": expression, "model_unit": "MUSD/PJ activity", "evidence_ids": evidence,
            "superseded_by": "", "evidence_type": "source+assumption",
            "notes": "Objective coefficient only; endogenous activity remains unbounded by this change.",
        })
    append_unique(data_sources / "MODEL_MAP.csv", "map_id", map_rows)
    append_unique(data_sources / "GAPS.csv", "item", [{
        "item": "Philippines-specific gas distribution and CNG station cost evidence",
        "why_absent": "No retained national source was found and the model has no gas-delivery network representation.",
        "upgrade_source": "Philippine pipeline/LNG distributor tariffs, CNG station engineering costs, and network coverage evidence.",
        "priority": "high",
        "notes": "The v33 adder is a transparent proxy and cannot support endogenous gas-network investment or distinguish delivery routes.",
    }])
    append_unique(data_sources / "CHANGES.csv", "change_id", [{
        "change_id": "CHG_PHL_V33_GAS_DELIVERY", "date": "2026-08-27", "class": "B",
        "description": "Added sourced legacy-gas VOM and a conservative delivery-cost proxy to every processed-gas route not producing electricity while retaining take-or-pay.",
        "model_objects": "RYTM.json VC SC_0: PHL_POW_CHP_NG_OLD plus 14 exact IAR/OAR-classified non-electricity processed-gas routes",
        "evidence_path": "documentation/gas_delivery_source_change_v33.json", "map_rows_affected": "MAP_PHL_V33_GAS_VC_01..15",
        "resolve_status": "candidate_built", "author": "Codex", "commit": "",
        "notes": "510 cost cells; no demand, efficiency, capacity, bound, structure or equation changes.",
    }])

    audit = {
        "case": "Philippines_v33", "parent_case": "Philippines_v32", "status": "source_candidate_built",
        "parameter": "RYTM.json VC SC_0", "years": [2020, 2053], "changed_rows": 15,
        "changed_cells": len(changes), "delivery_adder_musd_per_pj_input": DELIVERY_ADDER,
        "reference_vom_musd_per_pj_activity": EXPECTED_VOM, "take_or_pay_retained": True,
        "delivery_technologies": list(END_USE_TECHS),
        "non_forcing": True, "evidence_sha256": EVIDENCE_SHA256,
        "parent_source_hashes": parent_hashes,
        "candidate_source_hashes": {name: sha256(case / name) for name in parent_hashes},
        "changes": changes,
    }
    output = case / "documentation/gas_delivery_source_change_v33.json"
    output.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({key: value for key, value in audit.items() if key != "changes"}, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Zero-solve gate that v36 source values survived MUIOGO export/preprocess."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "WebAPP/DataStorage/.Philippines_v36-power-gas-history-candidate-20260827"
DEFAULT_RUN = "BASE_V36_POWER_GAS_HISTORY"
YEARS = [str(year) for year in range(2020, 2054)]
TOL = 1e-12


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(rows: list[dict], **coordinates: object) -> dict:
    matches = [row for row in rows if all(row.get(key) == value for key, value in coordinates.items())]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one row at {coordinates}, found {len(matches)}")
    return matches[0]


def section(text: str, parameter: str) -> tuple[float, str]:
    match = re.search(rf"param {re.escape(parameter)} default ([^ ]+) :=\s*(.*?)\n;", text, re.S)
    if not match:
        raise RuntimeError(f"parameter missing from data.txt: {parameter}")
    return float(match.group(1)), match.group(2)


def vector(text: str, parameter: str, technology: str) -> list[float]:
    default, body = section(text, parameter)
    for line in body.splitlines():
        parts = line.split()
        if parts and parts[0] == technology:
            if len(parts) != 35:
                raise RuntimeError(f"bad vector length for {parameter} {technology}: {len(parts)}")
            return [float(value) for value in parts[1:]]
    return [default] * len(YEARS)


def block(
    text: str, parameter: str, technology: str, mode: int,
    commodity: str | None = None,
) -> list[float]:
    default, body = section(text, parameter)
    coordinate = rf"\[RE1,{re.escape(technology)},"
    coordinate += rf"{re.escape(commodity)},\*,\*\]" if commodity else r"\*,\*\]"
    match = re.search(
        coordinate + r":\s*\n2020(?:\s+\d{4}){33}\s*:=\s*\n(.*?)(?=\n\[RE1,|\Z)",
        body, re.S,
    )
    if not match:
        return [default] * len(YEARS)
    for line in match.group(1).splitlines():
        parts = line.split()
        if parts and parts[0] == str(mode):
            if len(parts) != 35:
                raise RuntimeError(f"bad block length for {parameter} {technology} mode {mode}")
            return [float(value) for value in parts[1:]]
    return [default] * len(YEARS)


def expected(row: dict) -> list[float]:
    return [float(row[year]) for year in YEARS]


def matches(left: list[float], right: list[float]) -> bool:
    return len(left) == len(right) and all(abs(a - b) <= TOL * max(1.0, abs(b)) for a, b in zip(left, right))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default=DEFAULT_RUN)
    args = parser.parse_args()
    run = CASE / "res" / args.run
    data = (run / "data.txt").read_text(encoding="utf-8")
    processed = (run / "data_processed.txt").read_text(encoding="utf-8")
    generation = json.loads((run / "generation_matrix_report.json").read_text())
    gen = json.loads((CASE / "genData.json").read_text())
    ryt = json.loads((CASE / "RYT.json").read_text())
    rytm = json.loads((CASE / "RYTM.json").read_text())
    rytcm = json.loads((CASE / "RYTCM.json").read_text())
    ids = {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}
    comms = {row["Comm"]: row["CommId"] for row in gen["osy-comm"]}
    old_id = ids["PHL_POW_CHP_NG_OLD"]
    td_id = ids["PHL_POW_TD"]

    checks = []
    for parameter in ("ResidualCapacity", "AvailabilityFactor", "FixedCost"):
        source_name = {"ResidualCapacity": "RC", "AvailabilityFactor": "AF", "FixedCost": "FC"}[parameter]
        source = one(ryt[source_name]["SC_0"], TechId=old_id)
        checks.append({
            "name": f"{parameter}_legacy_gas",
            "passed": matches(vector(data, parameter, "PHL_POW_CHP_NG_OLD"), expected(source)),
        })

    for parameter, source_name in (
        ("VariableCost", "VC"),
        ("TechnologyActivityByModeUpperLimit", "TAMUL"),
        ("TechnologyActivityByModeLowerLimit", "TAMLL"),
    ):
        for mode in (1, 2):
            source = one(rytm[source_name]["SC_0"], TechId=old_id, MoId=mode)
            checks.append({
                "name": f"{parameter}_legacy_gas_mode_{mode}",
                "passed": matches(block(data, parameter, "PHL_POW_CHP_NG_OLD", mode), expected(source)),
            })

    ratio_series = [
        ("InputActivityRatio", "IAR", "PHL_POW_TD", "PHL_POW_ELE", 1, td_id, comms["PHL_POW_ELE"]),
        ("InputActivityRatio", "IAR", "PHL_POW_CHP_NG_OLD", "PHL_PRO_NG", 1, old_id, comms["PHL_PRO_NG"]),
        ("InputActivityRatio", "IAR", "PHL_POW_CHP_NG_OLD", "PHL_PRO_NG", 2, old_id, comms["PHL_PRO_NG"]),
        ("OutputActivityRatio", "OAR", "PHL_POW_CHP_NG_OLD", "PHL_POW_ELE", 1, old_id, comms["PHL_POW_ELE"]),
        ("OutputActivityRatio", "OAR", "PHL_POW_CHP_NG_OLD", "PHL_POW_ELE", 2, old_id, comms["PHL_POW_ELE"]),
    ]
    for parameter, source_name, tech, commodity, mode, tech_id, comm_id in ratio_series:
        source = one(rytcm[source_name]["SC_0"], TechId=tech_id, CommId=comm_id, MoId=mode)
        checks.append({
            "name": f"{parameter}_{tech}_{commodity}_mode_{mode}",
            "passed": matches(block(data, parameter, tech, mode, commodity), expected(source)),
        })

    mode_checks = {
        "technology_modes": "set MODEperTECHNOLOGY[PHL_POW_CHP_NG_OLD]:= 1 2;" in processed,
        "electricity_output_modes": "set MODExTECHNOLOGYperFUELout[PHL_POW_ELE]:=" in processed
        and "(2, PHL_POW_CHP_NG_OLD)" in processed.split("set MODExTECHNOLOGYperFUELout[PHL_POW_ELE]:=", 1)[1].split(";", 1)[0],
        "gas_input_modes": "set MODExTECHNOLOGYperFUELin[PHL_PRO_NG]:=" in processed
        and "(2, PHL_POW_CHP_NG_OLD)" in processed.split("set MODExTECHNOLOGYperFUELin[PHL_PRO_NG]:=", 1)[1].split(";", 1)[0],
        "emission_modes": "set MODExTECHNOLOGYperEMISSION[PM2_5]:=" in processed
        and "(2, PHL_POW_CHP_NG_OLD)" in processed.split("set MODExTECHNOLOGYperEMISSION[PM2_5]:=", 1)[1].split(";", 1)[0],
    }
    hash_checks = {
        name: sha256(run / name) == digest
        for name, digest in generation["hashes"].items()
    }
    failure_count = sum(not item["passed"] for item in checks)
    failure_count += sum(not value for value in mode_checks.values())
    failure_count += sum(not value for value in hash_checks.values())
    report = {
        "schema": "philippines-v36-generated-power-gas-gate-v1",
        "status": "pass" if failure_count == 0 else "fail",
        "failure_count": failure_count,
        "optimizer_runs": 0,
        "case_identity": gen["osy-casename"],
        "run": str(run),
        "checks": checks,
        "derived_mode_checks": mode_checks,
        "generated_hashes_current": hash_checks,
        "matrix_dimensions": generation["matrix_dimensions"],
        "matrix_deltas": generation["matrix_deltas"],
    }
    path = run / "generated_power_gas_gate.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "failure_count": failure_count, "case_identity": report["case_identity"]}, indent=2))
    if failure_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

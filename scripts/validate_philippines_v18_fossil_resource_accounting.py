#!/usr/bin/env python3
"""Deterministic source checks for the PHL v18 fossil-resource candidate."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
LIVE = REPO / "WebAPP" / "DataStorage" / "Philippines_v18"
DEFAULT_CANDIDATE = (
    REPO
    / "WebAPP"
    / "DataStorage"
    / ".Philippines_v18-fossil-resource-candidate"
)
YEARS = [str(year) for year in range(2020, 2054)]
SC = "SC_0"

IDS = {
    "coal_extraction": "TEC_4qu6p",
    "oil_extraction": "TEC_0",
    "coal_import": "TEC_khtrp",
    "oil_import": "TEC_d3fyp",
    "coal_tag": "COM_cdom0",
    "oil_tag": "COM_odom0",
    "coal_pool": "COM_g7h7w",
    "oil_pool": "COM_62exk",
    "coal_bridge": "TEC_cdom0",
    "oil_bridge": "TEC_odom0",
    "coal_export": "TEC_cexp0",
    "oil_export": "TEC_oexp0",
}
NEW_TECHS = {
    IDS["coal_bridge"],
    IDS["oil_bridge"],
    IDS["coal_export"],
    IDS["oil_export"],
}
NEW_COMMS = {IDS["coal_tag"], IDS["oil_tag"]}


def load(case: Path, name: str) -> Any:
    return json.loads((case / name).read_text())


def close(actual: float, expected: float, *, tol: float = 1e-9) -> None:
    if not math.isclose(float(actual), float(expected), rel_tol=tol, abs_tol=tol):
        raise AssertionError(f"{actual!r} != {expected!r}")


def row(data: dict[str, Any], parameter: str, tech: str, **keys: Any) -> dict[str, Any]:
    matches = []
    for item in data[parameter][SC]:
        if item.get("TechId") != tech:
            continue
        if all(item.get(key) == value for key, value in keys.items()):
            matches.append(item)
    if len(matches) != 1:
        raise AssertionError(
            f"Expected one {parameter} row for {tech} {keys}, found {len(matches)}"
        )
    return matches[0]


def base_tech_map(rt: dict[str, Any], parameter: str) -> dict[str, float]:
    rows = rt[parameter][SC]
    if len(rows) != 1:
        raise AssertionError(f"Unexpected {parameter} base structure")
    return rows[0]


def check_candidate(candidate: Path) -> dict[str, Any]:
    checks: list[str] = []
    manifest = load(candidate, "fossil_resource_candidate_manifest.json")
    expected_changed = {
        "RT.json",
        "RYC.json",
        "RYCTs.json",
        "RYCn.json",
        "RYT.json",
        "RYTCM.json",
        "RYTCn.json",
        "RYTM.json",
        "RYTTs.json",
        "genData.json",
    }
    if set(manifest["changed_source_files"]) != expected_changed:
        raise AssertionError("Unexpected source-file change set")
    checks.append("source file allowlist")

    live_gen = load(LIVE, "genData.json")
    gen = load(candidate, "genData.json")
    techs = {item["TechId"]: item for item in gen["osy-tech"]}
    comms = {item["CommId"]: item for item in gen["osy-comm"]}
    live_techs = {item["TechId"]: item for item in live_gen["osy-tech"]}
    live_comms = {item["CommId"]: item for item in live_gen["osy-comm"]}
    if set(techs) != set(live_techs) | NEW_TECHS:
        raise AssertionError("Technology set changed outside the four additions")
    if set(comms) != set(live_comms) | NEW_COMMS:
        raise AssertionError("Commodity set changed outside the two additions")
    expected_io = {
        IDS["coal_extraction"]: ([], [IDS["coal_tag"]]),
        IDS["oil_extraction"]: ([], [IDS["oil_tag"]]),
        IDS["coal_bridge"]: ([IDS["coal_tag"]], [IDS["coal_pool"]]),
        IDS["oil_bridge"]: ([IDS["oil_tag"]], [IDS["oil_pool"]]),
        IDS["coal_export"]: ([IDS["coal_tag"]], []),
        IDS["oil_export"]: ([IDS["oil_tag"]], []),
    }
    for tech, (inputs, outputs) in expected_io.items():
        if techs[tech]["IAR"] != inputs or techs[tech]["OAR"] != outputs:
            raise AssertionError(f"Incorrect structural flow for {tech}")
    for tech in (IDS["coal_import"], IDS["oil_import"]):
        if NEW_COMMS & set(techs[tech].get("IAR", []) + techs[tech].get("OAR", [])):
            raise AssertionError(f"Import technology {tech} can reach an export tag")
    checks.append("source-tagged domestic/export topology")

    ryt = load(candidate, "RYT.json")
    rt = load(candidate, "RT.json")
    rytcm = load(candidate, "RYTCM.json")
    rytm = load(candidate, "RYTM.json")
    coal_tau = row(ryt, "TAU", IDS["coal_extraction"])
    oil_tau = row(ryt, "TAU", IDS["oil_extraction"])
    for year in YEARS:
        coal_mt = 20.0 if 2025 <= int(year) <= 2027 else 16.0
        close(coal_tau[year], coal_mt * 22.1)
        expected_bbl = 0.0
        if int(year) <= 2026:
            expected_bbl = 360_000.0 / (0.9 ** (2026 - int(year)))
        elif year == "2027":
            expected_bbl = 360_000.0 / 365.0 * 76.0
        close(oil_tau[year], expected_bbl * 6.119 / 1_000_000.0)
    close(base_tech_map(rt, "TMPAU")[IDS["coal_extraction"]], 9244.9474715)
    close(base_tech_map(rt, "TMPAU")[IDS["oil_extraction"]], 22.522423584)
    if sum(coal_tau[year] for year in YEARS) <= 9244.9474715:
        raise AssertionError("Coal cumulative cap is redundant over the horizon")
    if sum(oil_tau[year] for year in YEARS) > 22.522423584 + 1e-9:
        raise AssertionError("Oil annual envelope exceeds opening reserve")
    checks.append("annual deliverability and opening reserve caps")

    for tech in (IDS["coal_import"], IDS["oil_import"]):
        import_tau = row(ryt, "TAU", tech)
        if any(import_tau[year] != 999999 for year in YEARS):
            raise AssertionError(f"Import TAU was not left open for {tech}")
        if base_tech_map(rt, "TMPAU")[tech] != 999999:
            raise AssertionError(f"Import TMPAU was not left open for {tech}")
    checks.append("coal and oil imports remain open")

    for scenario, rows in ryt["TAU"].items():
        if scenario == SC:
            continue
        for tech in (
            IDS["coal_extraction"],
            IDS["oil_extraction"],
            IDS["coal_import"],
            IDS["oil_import"],
        ):
            matches = [item for item in rows if item.get("TechId") == tech]
            if len(matches) != 1 or any(matches[0].get(year) is not None for year in YEARS):
                raise AssertionError(f"TAU scenario override survives for {scenario}/{tech}")
    checks.append("global fossil-supply TAU inheritance across scenarios")

    expected_mode1 = {
        ("OAR", IDS["coal_extraction"], IDS["coal_tag"]),
        ("OAR", IDS["oil_extraction"], IDS["oil_tag"]),
        ("IAR", IDS["coal_bridge"], IDS["coal_tag"]),
        ("OAR", IDS["coal_bridge"], IDS["coal_pool"]),
        ("IAR", IDS["oil_bridge"], IDS["oil_tag"]),
        ("OAR", IDS["oil_bridge"], IDS["oil_pool"]),
        ("IAR", IDS["coal_export"], IDS["coal_tag"]),
        ("IAR", IDS["oil_export"], IDS["oil_tag"]),
    }
    for parameter, tech, comm in expected_mode1:
        link = row(rytcm, parameter, tech, CommId=comm, MoId=1)
        if any(link[year] != 1.0 for year in YEARS):
            raise AssertionError(f"Non-unit {parameter} mapping for {tech}/{comm}")
    checks.append("lossless mode-1 conversion and balance mappings")

    for tech in NEW_TECHS:
        for parameter, expected in (("AF", 1), ("CC", 0), ("TAU", 999999)):
            values = row(ryt, parameter, tech)
            if any(values[year] != expected for year in YEARS):
                raise AssertionError(f"Unexpected {parameter} for {tech}")
        if base_tech_map(rt, "OL")[tech] != 1:
            raise AssertionError(f"Unexpected operating life for {tech}")
    checks.append("new pass-through/export technology defaults")

    coal_export_vc = row(rytm, "VC", IDS["coal_export"], MoId=1)
    oil_export_vc = row(rytm, "VC", IDS["oil_export"], MoId=1)
    if any(coal_export_vc[year] >= 0 for year in YEARS):
        raise AssertionError("Coal export revenue was not represented as negative cost")
    if any(oil_export_vc[year] >= 0 for year in YEARS):
        raise AssertionError("Oil export revenue was not represented as negative cost")
    checks.append("endogenous export revenue drivers")

    # UpdateCase adds null scenario rows for new objects.  They must inherit the
    # base physical/economic data rather than create scenario-specific pins.
    for data, parameters in (
        (ryt, ("TAU", "AF", "CC")),
        (rytm, ("VC",)),
        (rytcm, ("IAR", "OAR")),
    ):
        for parameter in parameters:
            for scenario, rows in data[parameter].items():
                if scenario == SC:
                    continue
                for item in rows:
                    if item.get("TechId") in NEW_TECHS:
                        if any(item.get(year) is not None for year in YEARS):
                            raise AssertionError(
                                f"Scenario override found: {scenario}/{parameter}/{item['TechId']}"
                            )
    checks.append("scenario inheritance for new objects")

    return {
        "status": "passed",
        "candidate": str(candidate),
        "checks": checks,
        "coal_tau_pj": {year: coal_tau[year] for year in ("2020", "2025", "2028")},
        "oil_tau_pj": {year: oil_tau[year] for year in ("2020", "2026", "2027", "2028")},
        "coal_tmpau_pj": base_tech_map(rt, "TMPAU")[IDS["coal_extraction"]],
        "oil_tmpau_pj": base_tech_map(rt, "TMPAU")[IDS["oil_extraction"]],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    args = parser.parse_args()
    print(json.dumps(check_candidate(args.candidate.resolve()), indent=2))


if __name__ == "__main__":
    main()

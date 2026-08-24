#!/usr/bin/env python3
"""Deterministic, solver-free semantic gate for Philippines v23 Package 1."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import build_philippines_v23_package1 as spec


TOL = 1e-10


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keyed(rows, *fields):
    return {tuple(row[field] for field in fields): row for row in rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--parent", type=Path, default=spec.SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    parent = args.parent.resolve()

    gen = read_json(candidate / "genData.json")
    parent_gen = read_json(parent / "genData.json")
    tech_id = {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}
    comm_id = {row["Comm"]: row["CommId"] for row in gen["osy-comm"]}
    checks = []

    def check(name, passed, detail):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    check("identity", gen["osy-casename"] == "Philippines_v23", gen["osy-casename"])
    check(
        "structural_delta",
        len(gen["osy-tech"]) == len(parent_gen["osy-tech"]) + 1
        and len(gen["osy-constraints"]) == len(parent_gen["osy-constraints"]) + 1
        and len(gen["osy-comm"]) == len(parent_gen["osy-comm"]),
        {
            "technology_delta": len(gen["osy-tech"]) - len(parent_gen["osy-tech"]),
            "constraint_delta": len(gen["osy-constraints"]) - len(parent_gen["osy-constraints"]),
            "commodity_delta": len(gen["osy-comm"]) - len(parent_gen["osy-comm"]),
        },
    )

    ryt = read_json(candidate / "RYT.json")
    parent_ryt = read_json(parent / "RYT.json")
    base_rows = {key: keyed(ryt[key][spec.BASE], "TechId") for key in ryt}
    parent_rows = {key: keyed(parent_ryt[key][spec.BASE], "TechId") for key in parent_ryt}

    bio_import = tech_id[spec.BIOFUEL_IMPORT_NAME]
    bio_process = tech_id["PHL_PRO_PROC_BIOF"]
    check(
        "undefined_biofuel_processor_disabled",
        all(float(base_rows["TAU"][(bio_process,)][year]) == 0 for year in spec.YEARS)
        and all(float(base_rows["TAMaxCI"][(bio_process,)][year]) == 0 for year in spec.YEARS),
        "TAU=TAMaxCI=0, 2020-2053",
    )
    rytm = read_json(candidate / "RYTM.json")
    rytcm = read_json(candidate / "RYTCM.json")
    bio_vc = [row for row in rytm["VC"][spec.BASE] if row["TechId"] == bio_import]
    bio_oar = [
        row for row in rytcm["OAR"][spec.BASE]
        if row["TechId"] == bio_import and row["CommId"] == comm_id["PHL_PRO_BIOF"]
    ]
    check(
        "biofuel_import_boundary",
        bool(bio_vc) and bool(bio_oar)
        and all(
            abs(float(row[year]) - (spec.BIOFUEL_IMPORT_COST if row["MoId"] == 1 else 0.0)) < TOL
            for row in bio_vc for year in spec.YEARS
        )
        and all(
            abs(float(row[year]) - (1.0 if row["MoId"] == 1 else 0.0)) < TOL
            for row in bio_oar for year in spec.YEARS
        ),
        {"technology": spec.BIOFUEL_IMPORT_NAME, "cost": spec.BIOFUEL_IMPORT_COST},
    )

    charcoal = tech_id["PHL_HOU_COOK_COAL"]
    charcoal_gen = next(row for row in gen["osy-tech"] if row["TechId"] == charcoal)
    charcoal_iar = [row for row in rytcm["IAR"][spec.BASE] if row["TechId"] == charcoal]
    check(
        "closed_charcoal_proxy",
        charcoal_gen["IAR"] == [comm_id["PHL_PRO_BIOM"]]
        and all(float(base_rows["TAMaxCI"][(charcoal,)][year]) == 0 for year in spec.YEARS)
        and base_rows["RC"][(charcoal,)] == parent_rows["RC"][(charcoal,)]
        and all(
            abs(float(row[year]) - (5.0 if row["MoId"] == 1 else 0.0)) < TOL
            for row in charcoal_iar for year in spec.YEARS
        ),
        "biomass-energy input; existing RC preserved; no new capacity",
    )

    ccs_names = sorted(row["Tech"] for row in gen["osy-tech"] if "_CCS" in row["Tech"])
    check(
        "ccs_entry_date",
        all(
            float(base_rows["TAMaxCI"][(tech_id[name],)][str(year)]) == 0
            for name in ccs_names for year in range(2020, 2030)
        ),
        {"first_eligible_year": 2030, "technologies": ccs_names},
    )
    check(
        "unsupported_coal_routes_closed",
        all(
            float(base_rows["TAMaxCI"][(tech_id[name],)][year]) == 0
            for name in ("PHL_POW_GH2_COAL", "PHL_AGR_HEAT_COAL")
            for year in spec.YEARS
        ),
        ["PHL_POW_GH2_COAL", "PHL_AGR_HEAT_COAL"],
    )

    build_ok = True
    for name, ceiling in spec.PRE2026_BUILD_GW.items():
        row = base_rows["TAMaxCI"][(tech_id[name],)]
        build_ok &= float(row["2020"]) == 0
        build_ok &= all(abs(float(row[str(year)]) - ceiling) < TOL for year in range(2021, 2026))
    check("pre2026_build_envelopes", build_ok, spec.PRE2026_BUILD_GW)
    check(
        "pass_throughs_not_misclassified_as_stocks",
        all(
            base_rows["TAMaxCI"][(tech_id[name],)]
            == parent_rows["TAMaxCI"][(tech_id[name],)]
            for name in (
                "PHL_POW_TD_AGR", "PHL_POW_TD_HOU", "PHL_POW_TD_INDU",
                "PHL_POW_TD_SER", "PHL_POW_TD_TRA", "PHL_POW_TD_FSH",
            )
        ),
        "sector adapters retain parent capacity-free semantics",
    )

    af_ok = all(
        all(abs(float(base_rows["AF"][(tech_id[name],)][year]) - value) < TOL for year in spec.YEARS)
        for name, value in spec.NEW_THERMAL_AF.items()
    )
    check("new_thermal_availability", af_ok, spec.NEW_THERMAL_AF)

    td_rows = [
        row for row in rytcm["IAR"][spec.BASE]
        if row["TechId"] == tech_id["PHL_POW_TD"] and row["CommId"] == comm_id["PHL_POW_ELE"]
    ]
    check(
        "td_losses",
        all(
            abs(float(row[year]) - (spec.TD_INPUT_PER_OUTPUT if row["MoId"] == 1 else 0.0)) < TOL
            for row in td_rows for year in spec.YEARS
        ),
        spec.TD_INPUT_PER_OUTPUT,
    )

    water = comm_id["PHL_PWR_WAT"]
    cooling_ok = True
    for name, gallons in spec.COOLING_GAL_MWH.items():
        rows = [
            row for row in rytcm["IAR"][spec.BASE]
            if row["TechId"] == tech_id[name] and row["CommId"] == water
        ]
        cooling_ok &= bool(rows)
        expected = gallons * spec.GAL_MWH_TO_KM3_PJ
        cooling_ok &= all(
            abs(float(row[year]) - (expected if row["MoId"] == 1 else 0.0)) < TOL
            for row in rows for year in spec.YEARS
        )
    check("cooling_water_factors", cooling_ok, spec.COOLING_GAL_MWH)

    rytts = read_json(candidate / "RYTTs.json")
    parent_rytts = read_json(parent / "RYTTs.json")
    cf = keyed(rytts["CF"][spec.BASE], "TechId", "TsId")
    parent_cf = keyed(parent_rytts["CF"][spec.BASE], "TechId", "TsId")
    solar = tech_id["PHL_POW_PP_SPV"]
    ts_sorted = sorted(gen["osy-ts"], key=lambda row: int(row["Ts"]))
    ordinary = {}
    for season in (row["SeId"] for row in gen["osy-se"] if row["SeId"] != "SE_ugd96"):
        ordinary[season] = [row["TsId"] for row in ts_sorted if row["SE"] == season]
    night_ok = all(
        abs(float(cf[(solar, block[index])][year])) < TOL
        for block in ordinary.values() for index in (0, 5) for year in spec.YEARS
    )
    worst = [row["TsId"] for row in ts_sorted if row["SE"] == "SE_ugd96"]
    night_ok &= all(abs(float(cf[(solar, ts)][year])) < TOL for ts in worst for year in spec.YEARS)
    check("no_nighttime_solar", night_ok, {"night_brackets": [1, 6], "worst_day": "all zero"})

    ryts = read_json(candidate / "RYTs.json")
    ys = keyed(ryts["YS"][spec.BASE], "TsId")
    solar_energy_ok = all(
        abs(
            sum(float(cf[(solar, ts)][year]) * float(ys[(ts,)][year]) for ts in block)
            - sum(float(parent_cf[(solar, ts)][year]) * float(ys[(ts,)][year]) for ts in block)
        ) < TOL
        for block in ordinary.values() for year in spec.YEARS
    )
    check("solar_annual_energy_preserved", solar_energy_ok, "rotation only")
    non_solar_cf_unchanged = all(
        row == parent_cf[(row["TechId"], row["TsId"])]
        for row in rytts["CF"][spec.BASE]
        if row["TechId"] not in (solar, bio_import)
    )
    check("no_peak_cf_reserve_hack", non_solar_cf_unchanged, "all existing non-solar CF rows unchanged")

    rycts = read_json(candidate / "RYCTs.json")
    parent_rycts = read_json(parent / "RYCTs.json")
    sdp = keyed(rycts["SDP"][spec.BASE], "CommId", "TsId")
    parent_sdp = keyed(parent_rycts["SDP"][spec.BASE], "CommId", "TsId")
    profiled = (comm_id["PHL_HOU_ELEF"], comm_id["PHL_SER_ELEF"])
    peak_ts = worst[4]
    profile_ok = all(
        abs(sum(float(sdp[(commodity, ts)][year]) for ts in (row["TsId"] for row in ts_sorted)) - 1.0) < TOL
        and abs(float(sdp[(commodity, peak_ts)][year]) / float(ys[(peak_ts,)][year]) - spec.PEAK_TO_AVERAGE) < TOL
        for commodity in profiled for year in spec.YEARS
    )
    check("electricity_worst_day_profile", profile_ok, {"commodities": ["PHL_HOU_ELEF", "PHL_SER_ELEF"], "ratio": spec.PEAK_TO_AVERAGE})
    agriculture_unchanged = all(
        sdp[(comm_id[name], ts)] == parent_sdp[(comm_id[name], ts)]
        for name in ("PHL_AGR_MOT", "PHL_AGR_PRO")
        for ts in (row["TsId"] for row in ts_sorted)
    )
    check("agriculture_services_not_electric_peak", agriculture_unchanged, ["PHL_AGR_MOT", "PHL_AGR_PRO"])

    reserve = next(row for row in gen["osy-constraints"] if row["ConId"] == spec.RESERVE_CONSTRAINT_ID)
    rycn = keyed(read_json(candidate / "RYCn.json")["UCC"][spec.BASE], "ConId")
    rytcn = read_json(candidate / "RYTCn.json")
    multipliers = {
        key: keyed(rytcn[key][spec.BASE], "TechId", "ConId")
        for key in ("CCM", "CNCM", "CAM")
    }
    reserve_ok = reserve["Tag"] == 0 and all(abs(float(rycn[(spec.RESERVE_CONSTRAINT_ID,)][year])) < TOL for year in spec.YEARS)
    for name, credit in spec.CAPACITY_CREDIT.items():
        tid = tech_id[name]
        reserve_ok &= all(abs(float(multipliers["CCM"][(tid, spec.RESERVE_CONSTRAINT_ID)][year]) + credit) < TOL for year in spec.YEARS)
        reserve_ok &= all(abs(float(multipliers["CAM"][(tid, spec.RESERVE_CONSTRAINT_ID)][year])) < TOL for year in spec.YEARS)
    td = tech_id["PHL_POW_TD"]
    reserve_ok &= all(
        abs(float(multipliers["CAM"][(td, spec.RESERVE_CONSTRAINT_ID)][year]) - spec.RESERVE_ACTIVITY_COEFFICIENT) < TOL
        and abs(float(multipliers["CCM"][(td, spec.RESERVE_CONSTRAINT_ID)][year])) < TOL
        for year in spec.YEARS
    )
    check("reserve_margin_algebra", reserve_ok, f"-credited capacity + {spec.RESERVE_ACTIVITY_COEFFICIENT}*TD activity <= 0")

    generic_report_path = candidate / "documentation" / "package1_v23_generic_physical_gate.json"
    generic = read_json(generic_report_path) if generic_report_path.exists() else {}
    check(
        "generic_physical_gate",
        generic.get("status") == "passed_no_deterministic_contradiction"
        and generic.get("optimizer_runs") == 0
        and generic.get("failure_count") == 0,
        {key: generic.get(key) for key in ("status", "failure_count", "user_defined_constraint_years_checked")},
    )

    changed = sorted(
        path.name for path in candidate.glob("*.json")
        if not (parent / path.name).exists() or sha256(path) != sha256(parent / path.name)
    )
    expected_changed = sorted((
        "RT.json", "RYCTs.json", "RYCn.json", "RYT.json", "RYTCM.json",
        "RYTCn.json", "RYTM.json", "RYTTs.json", "genData.json",
    ))
    check("source_diff_allowlist", changed == expected_changed, changed)

    ledger = candidate / "data_sources"
    required_ledger = {
        "SOURCES.csv": "SRC_PHL_V23_PARENT",
        "ASSUMPTIONS.csv": "ASM_PHL_V23_NON_FORCING",
        "CALCULATIONS.csv": "CALC_PHL_V23_TD",
        "MODEL_MAP.csv": "MAP_PHL_V23_BIOFUEL",
        "GAPS.csv": "Plant-level cooling-system/source mapping",
        "CHANGES.csv": "CHG_PHL_V23_PACKAGE1_20260824",
    }
    ledger_ok = True
    for filename, expected in required_ledger.items():
        with (ledger / filename).open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            first = reader.fieldnames[0]
            ledger_ok &= expected in {row[first] for row in reader}
    check("six_table_schema_ledger", ledger_ok, sorted(required_ledger))

    failures = [row for row in checks if not row["passed"]]
    report = {
        "schema": "philippines-v23-package1-deterministic-gate-v1",
        "candidate": str(candidate),
        "parent": str(parent),
        "status": "passed" if not failures else "failed",
        "optimizer_runs": 0,
        "model_generation_runs": 0,
        "checks": checks,
        "failure_count": len(failures),
        "failures": failures,
        "next_step": "application generation and preprocessing" if not failures else "stop before generation",
    }
    payload = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

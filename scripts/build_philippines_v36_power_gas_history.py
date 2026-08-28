#!/usr/bin/env python3
"""Build the source-only Philippines v36 power/gas-history candidate from v33."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


YEARS = [str(year) for year in range(2020, 2054)]
HISTORY = [str(year) for year in range(2020, 2025)]
OLD_GAS = "PHL_POW_CHP_NG_OLD"
TD = "PHL_POW_TD"
GROSS_ELECTRICITY = "PHL_POW_ELE"
VOM = 0.7050283513976835
PROCESS_RAW_PER_DELIVERED = 1.056771911
BASE_FIXED_COST = 22.0
CONTRACT_RAW_PJ = {
    **{str(year): 64.5 for year in range(2020, 2026)},
    **{str(year): 21.5 for year in range(2026, 2028)},
}
GRID_SALES_GWH = {
    "2020": 81956.783, "2021": 87417.408, "2022": 91332.592,
    "2023": 95807.853, "2024": 103908.135,
}
GRID_CONSUMPTION_GWH = {
    "2020": 100274.720, "2021": 106114.713, "2022": 111515.669,
    "2023": 118003.909, "2024": 126940.827,
}
TD_IAR = {year: GRID_CONSUMPTION_GWH[year] / GRID_SALES_GWH[year] for year in HISTORY}
GAS_CAPACITY_2022_GW = 3.732
GAS_DEPENDABLE_2023_2024_GW = 3.281
GAS_AF_2022_ONWARD = GAS_DEPENDABLE_2023_2024_GW / GAS_CAPACITY_2022_GW
MTOE_TO_PJ = 41.868
DOE_GAS_GENERATION_PJ = {
    "2022": 64.3824, "2023": 60.0048, "2024": 64.9692,
}
# The situationer charts are the most granular public national fuel-input
# series currently available. Values below retain the published total and
# share before conversion rather than initializing from rounded PJ displays.
DOE_TOTAL_POWER_INPUT_MTOE = {"2022": 32.7, "2023": 36.7, "2024": 38.9}
DOE_GAS_INPUT_SHARE = {"2022": 0.077, "2023": 0.067, "2024": 0.072}
GAS_PLANT_IAR = {
    year: DOE_TOTAL_POWER_INPUT_MTOE[year] * DOE_GAS_INPUT_SHARE[year]
    * MTOE_TO_PJ / DOE_GAS_GENERATION_PJ[year]
    for year in ("2022", "2023", "2024")
}
EVIDENCE = {
    "doe_2024_electricity_consumption.pdf": (
        "6d91e685ec3acda7b07312af4a80a2ee8f3e7dbc0de849880c2d6efb88f3f862"
    ),
    "doe_2024_grid_capacity_summary.pdf": (
        "cb346d9a6997556a605f8852972f14ec10edbe56b5a655cf25577faed94d8801"
    ),
    "fph_2024_annual_report.pdf": (
        "27f61f82c473e3c4cc4eba471c6352a8c6551faa5b24b797c88fd3931314e79e"
    ),
    "doe_2023_energy_situationer.pdf": (
        "c9778141887e4e419530b96ed604700f43ae253db300649fcb8e675bea877655"
    ),
    "doe_2024_energy_situationer.pdf": (
        "441593caebef4ac55679eb248a1fca1c4273e12a7e882b877fc7781c6e179493"
    ),
}


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
        rows = list(reader)
    if not fieldnames:
        raise RuntimeError(f"Missing CSV header: {path}")
    incoming = {row[key] for row in values}
    duplicates = incoming & {row[key] for row in rows}
    if duplicates:
        raise RuntimeError(f"Duplicate provenance identifiers in {path}: {sorted(duplicates)}")
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows + [{field: row.get(field, "") for field in fieldnames} for row in values])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    args = parser.parse_args()
    case = args.case.resolve()
    evidence_dir = case / "data_sources/evidence/v36_power_gas"
    for filename, expected in EVIDENCE.items():
        actual = sha256(evidence_dir / filename)
        if actual != expected:
            raise RuntimeError(f"Evidence hash mismatch for {filename}: {actual}")

    tracked = ("genData.json", "RYT.json", "RYTM.json", "RYTCM.json", "RYTEM.json")
    parent_hashes = {name: sha256(case / name) for name in tracked}
    gen = json.loads((case / "genData.json").read_text())
    if gen.get("osy-casename") != "Philippines_v33":
        raise RuntimeError(f"Expected Philippines_v33 parent, found {gen.get('osy-casename')}")
    tech_ids = {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}
    comm_ids = {row["Comm"]: row["CommId"] for row in gen["osy-comm"]}
    old_gas_id = tech_ids[OLD_GAS]

    ryt = json.loads((case / "RYT.json").read_text())
    rytm = json.loads((case / "RYTM.json").read_text())
    rytcm = json.loads((case / "RYTCM.json").read_text())
    rytem = json.loads((case / "RYTEM.json").read_text())

    # Gross generation must cover metered sales, system loss, and plant own-use.
    td_row = one(
        rytcm["IAR"]["SC_0"], TechId=tech_ids[TD],
        CommId=comm_ids[GROSS_ELECTRICITY], MoId=1,
    )
    td_before = {year: float(td_row[year]) for year in YEARS}
    for year in HISTORY:
        td_row[year] = TD_IAR[year]
    for year in YEARS:
        if int(year) >= 2025:
            td_row[year] = TD_IAR["2024"]

    # Correct the reported nameplate stock while preserving inherited retirement years.
    rc = one(ryt["RC"]["SC_0"], TechId=old_gas_id)
    af = one(ryt["AF"]["SC_0"], TechId=old_gas_id)
    fc = one(ryt["FC"]["SC_0"], TechId=old_gas_id)
    rc_before = {year: float(rc[year]) for year in YEARS}
    scale = GAS_CAPACITY_2022_GW / rc_before["2022"]
    for year in YEARS:
        if int(year) >= 2022:
            rc[year] = rc_before[year] * scale
            af[year] = GAS_AF_2022_ONWARD

    # Mode 1 is a capped prepaid/take-or-pay contract tranche. Mode 2 is the
    # same physical plant at ordinary market cost. No lower activity bound exists.
    processed_gas_id = comm_ids["PHL_PRO_NG"]
    for parameter, table in (("IAR", rytcm), ("OAR", rytcm)):
        rows = table[parameter]["SC_0"]
        mode1_rows = [row for row in rows if row.get("TechId") == old_gas_id and row.get("MoId") == 1]
        for mode1 in mode1_rows:
            mode2 = one(rows, TechId=old_gas_id, CommId=mode1["CommId"], MoId=2)
            for year in YEARS:
                mode2[year] = mode1[year]
                if int(year) >= 2028:
                    mode1[year] = 0.0
    gas_iar1 = one(
        rytcm["IAR"]["SC_0"], TechId=old_gas_id,
        CommId=processed_gas_id, MoId=1,
    )
    gas_iar2 = one(
        rytcm["IAR"]["SC_0"], TechId=old_gas_id,
        CommId=processed_gas_id, MoId=2,
    )
    for year in YEARS:
        if int(year) >= 2022:
            plant_iar = GAS_PLANT_IAR.get(year, GAS_PLANT_IAR["2024"])
            gas_iar2[year] = plant_iar
            if int(year) <= 2027:
                gas_iar1[year] = plant_iar
    for mode1 in [row for row in rytem["EAR"]["SC_0"] if row.get("TechId") == old_gas_id and row.get("MoId") == 1]:
        mode2 = one(rytem["EAR"]["SC_0"], TechId=old_gas_id, EmisId=mode1["EmisId"], MoId=2)
        for year in YEARS:
            mode2[year] = mode1[year]
            if int(year) >= 2028:
                mode1[year] = 0.0

    vc1 = one(rytm["VC"]["SC_0"], TechId=old_gas_id, MoId=1)
    vc2 = one(rytm["VC"]["SC_0"], TechId=old_gas_id, MoId=2)
    tamul1 = one(rytm["TAMUL"]["SC_0"], TechId=old_gas_id, MoId=1)
    tamul2 = one(rytm["TAMUL"]["SC_0"], TechId=old_gas_id, MoId=2)
    gas_extraction_id = tech_ids["PHL_PRO_EXTR_NG"]
    gas_price = one(rytm["VC"]["SC_0"], TechId=gas_extraction_id, MoId=1)
    contract_audit = []
    for year in YEARS:
        raw_contract = CONTRACT_RAW_PJ.get(year, 0.0)
        plant_iar = (
            GAS_PLANT_IAR.get(year, GAS_PLANT_IAR["2024"])
            if int(year) >= 2022 else float(gas_iar1[year])
        )
        upstream_raw_per_power = PROCESS_RAW_PER_DELIVERED * plant_iar
        vc2[year] = VOM
        tamul2[year] = 99999
        if raw_contract:
            credit = float(gas_price[year]) * upstream_raw_per_power
            vc1[year] = VOM - credit
            tamul1[year] = raw_contract / plant_iar
            fc[year] = (
                BASE_FIXED_COST
                + raw_contract * PROCESS_RAW_PER_DELIVERED
                * float(gas_price[year]) / float(rc[year])
            )
        else:
            credit = 0.0
            vc1[year] = 0.0
            tamul1[year] = 99999
            fc[year] = BASE_FIXED_COST
        contract_audit.append({
            "year": int(year), "raw_contract_pj": raw_contract,
            "plant_gas_per_power_pj_per_pj": plant_iar,
            "upstream_raw_per_power_pj_per_pj": upstream_raw_per_power,
            "mode1_activity_upper_pj": raw_contract / plant_iar if raw_contract else 0.0,
            "variable_credit_musd_per_pj_activity": credit,
            "fixed_cost_musd_per_gw_year": float(fc[year]),
        })

    gen["osy-casename"] = "Philippines_v36"
    gen["osy-date"] = "2026-08-27"
    gen["osy-desc"] = (
        "Philippines v36: v33 plus a gross-to-meter electricity balance that includes "
        "system loss and plant own-use, a DOE-aligned legacy-gas stock, and separate capped "
        "contract and market dispatch modes. Observed generation remains benchmark-only."
    )
    for row in gen["osy-tech"]:
        if row["Tech"] == OLD_GAS:
            row["Desc"] = (
                "Legacy grid-connected gas fleet. Mode 1 is the capped prepaid/take-or-pay "
                "PPA tranche through disclosed contract expiries; mode 2 is market-priced."
            )

    for path, payload in (
        (case / "genData.json", gen), (case / "RYT.json", ryt),
        (case / "RYTM.json", rytm), (case / "RYTCM.json", rytcm),
        (case / "RYTEM.json", rytem),
    ):
        path.write_text(json.dumps(payload, indent=2) + "\n")

    ledgers = case / "data_sources"
    append_unique(ledgers / "SOURCES.csv", "source_id", [
        {
            "source_id": "SRC_PHL_V36_DOE_ELECTRICITY_BALANCE_2024", "provider": "Philippines Department of Energy",
            "product": "2024 Power Statistics: Electricity Sales and Consumption per Grid, by Sector", "edition": "updated 15 June 2025",
            "reference_period": "2020-2024", "geography": "Philippines", "variable": "Sales, own-use, system loss, total electricity consumption and off-grid boundary",
            "source_unit": "MWh", "exact_locator": "Philippines rows; note 1: off-grid consumption excluded starting 2021",
            "url": "https://prod-cms.doe.gov.ph/documents/d/guest/06_electricity-consumption-pdf", "access_date": "2026-08-27",
            "license": "Philippine government publication", "sha256": EVIDENCE["doe_2024_electricity_consumption.pdf"],
            "local_file": "evidence/v36_power_gas/doe_2024_electricity_consumption.pdf", "notes": "2020 grid values subtract the separately reported 1,286 GWh off-grid sales and 1,481 GWh off-grid consumption."
        },
        {
            "source_id": "SRC_PHL_V36_DOE_OFFGRID_2020", "provider": "Philippines Department of Energy",
            "product": "2020 Power Situation Report", "edition": "2021 release", "reference_period": "2020", "geography": "Philippines off-grid and missionary areas",
            "variable": "Off-grid electricity sales and consumption", "source_unit": "GWh", "exact_locator": "Off-grid and Missionary Electrification, Figure 17: 1,286 GWh sales; 1,481 GWh consumption",
            "url": "https://doe.gov.ph/sites/default/files/pdf/electric_power/2020_power-situation-report_as_of_09-september-2021.pdf", "access_date": "2026-08-27",
            "license": "Philippine government publication", "sha256": "", "local_file": "", "notes": "DOE legacy host was unavailable for local archiving; exact published totals are retained in the calculation record."
        },
        {
            "source_id": "SRC_PHL_V36_DOE_GAS_CAPACITY_2024", "provider": "Philippines Department of Energy",
            "product": "List of Existing Power Plants: capacity mix", "edition": "31 December 2024", "reference_period": "2024", "geography": "Philippines grid-connected",
            "variable": "Natural-gas installed and dependable capacity", "source_unit": "MW", "exact_locator": "Capacity Mix: Natural Gas = 3,732 MW installed; 3,281 MW dependable",
            "url": "https://prod-cms.doe.gov.ph/documents/d/epimb/04-lvm-summary-as-of-december-2024-pdf", "access_date": "2026-08-27",
            "license": "Philippine government publication", "sha256": EVIDENCE["doe_2024_grid_capacity_summary.pdf"],
            "local_file": "evidence/v36_power_gas/doe_2024_grid_capacity_summary.pdf", "notes": "The 2022 temporary dependable-capacity fall is treated as fuel unavailability, already represented by gas supply, not as a continuing plant AF."
        },
        {
            "source_id": "SRC_PHL_V36_FPH_GAS_CONTRACTS_2024", "provider": "First Philippine Holdings Corporation",
            "product": "SEC Form 17-A Annual Report", "edition": "2024", "reference_period": "2022-2024 and contract terms", "geography": "Luzon",
            "variable": "Santa Rita and San Lorenzo PPAs/GSPAs, take-or-pay quantities, expiries and new GSPA", "source_unit": "PJ; date; narrative",
            "exact_locator": "Significant contracts: Santa Rita 43.0 PJ/year; San Lorenzo terms; PPAs to 2025/2027; new GSPA 181.41 PJ remaining volume",
            "url": "https://www.fphc.com/storage/app/media/popup_2025/FPH%2017A.pdf", "access_date": "2026-08-27", "license": "Issuer publication",
            "sha256": EVIDENCE["fph_2024_annual_report.pdf"], "local_file": "evidence/v36_power_gas/fph_2024_annual_report.pdf",
            "notes": "Only the disclosed legacy PPA-equivalent 43.0 + 21.5 PJ annual tranche is represented; no LNG take-or-pay term is inferred."
        },
        {
            "source_id": "SRC_PHL_V36_DOE_POWER_INPUT_2023", "provider": "Philippines Department of Energy",
            "product": "2023 Philippine Energy Supply and Demand Situationer", "edition": "2025 publication",
            "reference_period": "2022-2023", "geography": "Philippines", "variable": "Total fuel input and natural-gas share for power generation",
            "source_unit": "MTOE; percent; TWh", "exact_locator": "Figure 15, page 16: 2022 32.7 MTOE and 7.7%; 2023 36.4 MTOE and 6.8%",
            "url": "https://prod-cms.doe.gov.ph/documents/d/eppb/2023-energy-supply-and-demand-situationer-pdf", "access_date": "2026-08-27",
            "license": "Philippine government publication", "sha256": EVIDENCE["doe_2023_energy_situationer.pdf"],
            "local_file": "evidence/v36_power_gas/doe_2023_energy_situationer.pdf", "notes": "Retained as an independent cross-check; the later 2024 situationer supplies the installed 2023 revision."
        },
        {
            "source_id": "SRC_PHL_V36_DOE_POWER_INPUT_2024", "provider": "Philippines Department of Energy",
            "product": "2024 Philippine Energy Situationer and Key Energy Statistics", "edition": "2025 publication",
            "reference_period": "2023-2024", "geography": "Philippines", "variable": "Total fuel input, natural-gas share and natural-gas gross generation",
            "source_unit": "MTOE; percent; TWh", "exact_locator": "Figure 13, page 16: 2023 36.7 MTOE, 6.7%, 14.1%; 2024 38.9 MTOE, 7.2%, 14.2%",
            "url": "https://prod-cms.doe.gov.ph/documents/d/guest/2024-philippine-energy-situationer-and-key-energy-statistics-pdf", "access_date": "2026-08-27",
            "license": "Philippine government publication", "sha256": EVIDENCE["doe_2024_energy_situationer.pdf"],
            "local_file": "evidence/v36_power_gas/doe_2024_energy_situationer.pdf", "notes": "The later publication revises the 2023 total and gas share and is authoritative for the installed 2023 coefficient."
        },
    ])
    append_unique(ledgers / "ASSUMPTIONS.csv", "assumption_id", [
        {
            "assumption_id": "ASM_PHL_V36_GRID_BALANCE_BOUNDARY", "statement": "PHL_POW_TD converts gross grid electricity to metered grid sales and therefore includes both plant own-use and system loss; off-grid remains separate.",
            "central_value": "annual DOE ratio; 2024 held after 2024", "unit": "PJ gross/PJ sales", "evidence_source_ids": "SRC_PHL_V36_DOE_ELECTRICITY_BALANCE_2024;SRC_PHL_V36_DOE_OFFGRID_2020",
            "lower_bound": "", "upper_bound": "", "rationale": "This is a physical boundary conversion, not a generation target.", "notes": "The 2024 measured coefficient is held as the continuing post-history efficiency assumption."
        },
        {
            "assumption_id": "ASM_PHL_V36_GAS_STOCK_REMEASUREMENT", "statement": "Scale the inherited post-2021 gas residual-capacity path to 3.732 GW while retaining its retirement years; use 3.281/3.732 as continuing physical availability.",
            "central_value": str(GAS_AF_2022_ONWARD), "unit": "availability fraction", "evidence_source_ids": "SRC_PHL_V36_DOE_GAS_CAPACITY_2024",
            "lower_bound": "", "upper_bound": "", "rationale": "Separates nameplate stock and dependable plant capability from temporary fuel unavailability.", "notes": "No historical activity or generation value is used."
        },
        {
            "assumption_id": "ASM_PHL_V36_CONTRACT_COST_RECLASSIFICATION", "statement": "Represent disclosed Santa Rita and San Lorenzo take-or-pay/PPA energy economics as a capped prepaid tranche plus an otherwise identical market mode; no minimum dispatch is imposed.",
            "central_value": "64.5 PJ raw gas through 2025; 21.5 PJ through 2027", "unit": "PJ raw gas/year", "evidence_source_ids": "SRC_PHL_V36_FPH_GAS_CONTRACTS_2024;SRC_PEZA_MALAMPAYA_PRICE_2020",
            "lower_bound": "0", "upper_bound": "disclosed tranche", "rationale": "A fixed payment and matching variable credit reproduce sunk contract economics without pinning plant output.", "notes": "The new 2024 GSPA and LNG route receive no inferred take-or-pay credit because no TOPQ was disclosed."
        },
        {
            "assumption_id": "ASM_PHL_V36_GAS_PLANT_EFFICIENCY", "statement": "Use the DOE aggregate natural-gas fuel-input-to-gross-generation ratio for the legacy gas fleet from 2022-2024 and hold the latest observed coefficient thereafter.",
            "central_value": ";".join(f"{year}:{GAS_PLANT_IAR[year]:.15g}" for year in GAS_PLANT_IAR), "unit": "PJ processed gas/PJ gross electricity",
            "evidence_source_ids": "SRC_PHL_V36_DOE_POWER_INPUT_2023;SRC_PHL_V36_DOE_POWER_INPUT_2024;SRC_PHL_DOE_2024_POWER_SUMMARY",
            "lower_bound": "0", "upper_bound": "", "rationale": "This calibrates a physical conversion efficiency; generation remains endogenous.",
            "notes": "2020-2021 retain the inherited coefficient; the 2024 value is held after 2024."
        },
    ])
    append_unique(ledgers / "CALCULATIONS.csv", "calculation_id", [
        {
            "calculation_id": "CALC_PHL_V36_TD_OWN_USE", "formula": "IAR[y] = (grid sales + plant own-use + system loss) / grid sales; 2020 subtracts separate off-grid sales and consumption",
            "source_ids": "SRC_PHL_V36_DOE_ELECTRICITY_BALANCE_2024;SRC_PHL_V36_DOE_OFFGRID_2020", "assumption_ids": "ASM_PHL_V36_GRID_BALANCE_BOUNDARY", "input_calculation_ids": "",
            "input_values": ";".join(f"{y}:{GRID_SALES_GWH[y]},{GRID_CONSUMPTION_GWH[y]}" for y in HISTORY), "input_units": "GWh sales,GWh consumption",
            "output_value": ";".join(f"{y}:{TD_IAR[y]:.15g}" for y in HISTORY), "output_unit": "PJ gross/PJ sales", "script_path": "scripts/build_philippines_v36_power_gas_history.py",
            "script_version": "2026-08-27", "notes": "2025-2053 use the 2024 coefficient."
        },
        {
            "calculation_id": "CALC_PHL_V36_GAS_CONTRACT_MODES", "formula": "contract activity cap = TOPQ / plant IAR; mode-1 VC = VOM - domestic gas price * processing IAR * plant IAR; fixed cost = 22 + TOPQ*processing IAR*price/RC; mode-2 VC = VOM",
            "source_ids": "SRC_PHL_V36_FPH_GAS_CONTRACTS_2024;SRC_PEZA_MALAMPAYA_PRICE_2020", "assumption_ids": "ASM_PHL_V36_CONTRACT_COST_RECLASSIFICATION", "input_calculation_ids": "",
            "input_values": "43.0;21.5;1.056771911;CALC_PHL_V36_GAS_PLANT_IAR;row-specific inherited gas price and RC", "input_units": "PJ delivered/year;PJ raw/PJ delivered;PJ delivered/PJ electricity;MUSD/PJ raw;GW",
            "output_value": "year-specific mode cap, VC and FC", "output_unit": "PJ electricity/year;MUSD/PJ electricity;MUSD/GW-year", "script_path": "scripts/build_philippines_v36_power_gas_history.py",
            "script_version": "2026-08-27", "notes": "Mode 1 has no output ratios after 2027; mode 2 remains physically identical and unbounded by the contract cap."
        },
        {
            "calculation_id": "CALC_PHL_V36_GAS_STOCK", "formula": "RC[y>=2022] = RC_v33[y] * 3.732/3.4525; AF[y>=2022] = 3.281/3.732",
            "source_ids": "SRC_PHL_V36_DOE_GAS_CAPACITY_2024", "assumption_ids": "ASM_PHL_V36_GAS_STOCK_REMEASUREMENT", "input_calculation_ids": "",
            "input_values": "3.4525;3.732;3.281;inherited RC retirement path", "input_units": "GW", "output_value": "year-specific", "output_unit": "GW;fraction",
            "script_path": "scripts/build_philippines_v36_power_gas_history.py", "script_version": "2026-08-27", "notes": "Retirement years 2031, 2032 and 2046 are unchanged."
        },
        {
            "calculation_id": "CALC_PHL_V36_GAS_PLANT_IAR", "formula": "plant IAR[y] = total power fuel input MTOE[y] * natural-gas input share[y] * 41.868 PJ/MTOE / natural-gas gross generation PJ[y]",
            "source_ids": "SRC_PHL_V36_DOE_POWER_INPUT_2023;SRC_PHL_V36_DOE_POWER_INPUT_2024;SRC_PHL_DOE_2024_POWER_SUMMARY",
            "assumption_ids": "ASM_PHL_V36_GAS_PLANT_EFFICIENCY", "input_calculation_ids": "",
            "input_values": "2022:32.7,0.077,64.3824;2023:36.7,0.067,60.0048;2024:38.9,0.072,64.9692;41.868",
            "input_units": "MTOE,fraction,PJ;PJ/MTOE", "output_value": ";".join(f"{year}:{GAS_PLANT_IAR[year]:.15g}" for year in GAS_PLANT_IAR),
            "output_unit": "PJ processed gas/PJ gross electricity", "script_path": "scripts/build_philippines_v36_power_gas_history.py",
            "script_version": "2026-08-27", "notes": "2025-2053 use the 2024 coefficient. The 2023 DOE situationer is retained as a cross-check; the later 2024 edition supplies the installed revision."
        },
    ])
    append_unique(ledgers / "MODEL_MAP.csv", "map_id", [
        {"map_id": "MAP_PHL_V36_TD_GROSS_TO_SALES", "model_file": "RYTCM.json", "parameter": "IAR", "entity": TD, "mode": "1", "scenario": "SC_0", "years": "2020-2053", "value_or_expression": "CALC_PHL_V36_TD_OWN_USE", "model_unit": "PJ gross/PJ sales", "evidence_ids": "CALC_PHL_V36_TD_OWN_USE", "superseded_by": "", "evidence_type": "source+calculation", "notes": "OAR remains one PJ PHL_POW_ELE1 per activity."},
        {"map_id": "MAP_PHL_V36_GAS_STOCK", "model_file": "RYT.json", "parameter": "RC;AF", "entity": OLD_GAS, "mode": "", "scenario": "SC_0", "years": "2022-2053", "value_or_expression": "CALC_PHL_V36_GAS_STOCK", "model_unit": "GW;fraction", "evidence_ids": "CALC_PHL_V36_GAS_STOCK", "superseded_by": "", "evidence_type": "source+calculation", "notes": "Physical stock; no dispatch target."},
        {"map_id": "MAP_PHL_V36_GAS_CONTRACT_MODE", "model_file": "RYTM.json;RYTCM.json;RYTEM.json;RYT.json", "parameter": "VC;TAMUL;IAR;OAR;EAR;FC", "entity": OLD_GAS, "mode": "1;2", "scenario": "SC_0", "years": "2020-2053", "value_or_expression": "CALC_PHL_V36_GAS_CONTRACT_MODES", "model_unit": "mixed parameter-native units", "evidence_ids": "CALC_PHL_V36_GAS_CONTRACT_MODES", "superseded_by": "", "evidence_type": "source+calculation+assumption", "notes": "Mode 1 is only an upper-bounded discounted tranche; mode 2 preserves unconstrained market dispatch."},
        {"map_id": "MAP_PHL_V36_GAS_PLANT_EFFICIENCY", "model_file": "RYTCM.json", "parameter": "IAR", "entity": OLD_GAS, "mode": "1;2", "scenario": "SC_0", "years": "2022-2053", "value_or_expression": "CALC_PHL_V36_GAS_PLANT_IAR", "model_unit": "PJ processed gas/PJ gross electricity", "evidence_ids": "CALC_PHL_V36_GAS_PLANT_IAR", "superseded_by": "", "evidence_type": "source+calculation", "notes": "Physical conversion coefficient; not an activity or share constraint."},
    ])
    append_unique(ledgers / "GAPS.csv", "item", [
        {"item": "PHL commercial-electricity demand decomposition", "why_absent": "DOE metered commercial sales combine appliance and electric-heat uses, while PHL_SER_ELEF excludes endogenous electric heat; overwriting it would double count an endogenous route.", "upgrade_source": "A sourced commercial end-use split or a structural total-meter electricity accounting commodity.", "priority": "high", "notes": "The v36 preflight reports the discrepancy but does not force the residual demand."},
        {"item": "PHL gas dispatch regional network and LNG contract detail", "why_absent": "The national copperplate has no Luzon/inter-island topology, and the new 2024 GSPA/LNG contracts disclose no take-or-pay quantity.", "upgrade_source": "Regional load and transfer limits plus public plant-level PPA/GSPA/LNG scheduling terms.", "priority": "high", "notes": "Observed gas generation remains a benchmark; only disclosed legacy contract economics are represented."},
    ])
    append_unique(ledgers / "CHANGES.csv", "change_id", [{
        "change_id": "CHG_PHL_V36_POWER_GAS_HISTORY", "date": "2026-08-27", "class": "B",
        "description": "Reconciled grid gross generation with sales, own-use and loss; aligned legacy gas stock; and separated capped contract and market gas dispatch modes without an activity floor.",
        "model_objects": "PHL_POW_TD IAR; PHL_POW_CHP_NG_OLD RC/AF/FC/VC/TAMUL/IAR/OAR/EAR modes 1-2",
        "evidence_path": "documentation/power_gas_history_source_change_v36.json", "map_rows_affected": "MAP_PHL_V36_TD_GROSS_TO_SALES;MAP_PHL_V36_GAS_STOCK;MAP_PHL_V36_GAS_CONTRACT_MODE",
        "resolve_status": "candidate_built", "author": "Codex", "commit": "", "notes": "No generation target, activity lower bound, share, TAL or TAU was added."
    }])

    audit = {
        "case": "Philippines_v36", "parent_case": "Philippines_v33", "status": "source_candidate_built",
        "non_forcing": True, "observed_generation_role": "benchmark_only",
        "td_iar": TD_IAR, "td_before": td_before, "grid_sales_gwh": GRID_SALES_GWH,
        "grid_consumption_gwh": GRID_CONSUMPTION_GWH, "gas_capacity_scale": scale,
        "gas_availability_factor": GAS_AF_2022_ONWARD, "gas_plant_iar": GAS_PLANT_IAR,
        "contract_modes": contract_audit,
        "parent_hashes": parent_hashes, "candidate_hashes": {name: sha256(case / name) for name in tracked},
    }
    (case / "documentation/power_gas_history_source_change_v36.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({key: value for key, value in audit.items() if key != "contract_modes"}, indent=2))


if __name__ == "__main__":
    main()

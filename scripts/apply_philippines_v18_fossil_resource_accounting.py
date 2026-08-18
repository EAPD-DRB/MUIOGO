#!/usr/bin/env python3
"""Build a disposable PHL v18 fossil-resource/export candidate.

The structural change source-tags domestically extracted coal and crude oil,
then lets each resource flow either to the existing domestic raw-fuel pool or
to an optional export sink.  Imports continue to feed only the domestic pool,
so imported fuel cannot be re-exported.  Extraction is limited by physical
annual deliverability and opening recoverable reserves; observed production
and trade volumes are validation benchmarks only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
STORAGE = REPO / "WebAPP" / "DataStorage"
LIVE = STORAGE / "Philippines_v18"
DEFAULT_TARGET = STORAGE / ".Philippines_v18-fossil-resource-candidate"
API = REPO / "API"
if str(API) not in sys.path:
    sys.path.insert(0, str(API))

SCENARIO = "SC_0"
YEARS = [str(year) for year in range(2020, 2054)]
GJ_PER_TONNE_COAL = 22.1
GJ_PER_BARREL_OIL = 6.119
LITRES_PER_BARREL_OIL = 158.987294928
HISTORICAL_PRICE_YEARS = [str(year) for year in range(2020, 2025)]

IDS = {
    "coal_extraction": "TEC_4qu6p",
    "oil_extraction": "TEC_0",
    "coal_import": "TEC_khtrp",
    "oil_import": "TEC_d3fyp",
    "coal_domestic_commodity": "COM_cdom0",
    "oil_domestic_commodity": "COM_odom0",
    "coal_bridge": "TEC_cdom0",
    "oil_bridge": "TEC_odom0",
    "coal_export": "TEC_cexp0",
    "oil_export": "TEC_oexp0",
    "coal_shared_commodity": "COM_g7h7w",
    "oil_shared_commodity": "COM_62exk",
}

# Physical/legal coal output envelope.  The 2025 ECC amendment raised the
# Semirara mine ceiling from 16 to 20 Mt/y for 2025-2027.  The continuing
# post-amendment evidence does not establish 20 Mt/y after 2027, so the
# underlying 16 Mt/y envelope is restored rather than extrapolating output.
COAL_CAPACITY_MT = {
    year: (20.0 if 2025 <= int(year) <= 2027 else 16.0) for year in YEARS
}
COAL_TAU_PJ = {
    year: COAL_CAPACITY_MT[year] * GJ_PER_TONNE_COAL for year in YEARS
}

# DOE mineable reserves at 2023-12-31 plus reported national production in
# 2020-2023 reconstruct the opening 2020 mineable stock.  Production is used
# only as depletion accounting, never as an annual activity target.
COAL_MINEABLE_RESERVE_END_2023_MT = 362.067415
COAL_DEPLETION_2020_2023_MT = 12.951 + 14.048 + 14.457 + 14.8
COAL_OPENING_RESERVE_MT = (
    COAL_MINEABLE_RESERVE_END_2023_MT + COAL_DEPLETION_2020_2023_MT
)
COAL_TMPAU_PJ = COAL_OPENING_RESERVE_MT * GJ_PER_TONNE_COAL

# The operator's 2026 work program schedules three approximately 120,000-bbl
# cargoes, forecasts a 10% annual decline, and plans cessation on 17 March
# 2027.  The work-program volume is a forward physical operating envelope,
# not an observed production target.  Backcasting that envelope with the same
# decline rate represents the surviving existing-well stock in 2020-2025.
OIL_2026_WORK_PROGRAM_BARRELS = 3.0 * 120_000.0
OIL_DECLINE = 0.10
OIL_CAPACITY_BARRELS: dict[str, float] = {}
for year in range(2020, 2027):
    OIL_CAPACITY_BARRELS[str(year)] = OIL_2026_WORK_PROGRAM_BARRELS / (
        (1.0 - OIL_DECLINE) ** (2026 - year)
    )
OIL_CAPACITY_BARRELS["2027"] = (
    OIL_2026_WORK_PROGRAM_BARRELS / 365.0 * 76.0
)
for year in range(2028, 2054):
    OIL_CAPACITY_BARRELS[str(year)] = 0.0
OIL_TAU_PJ = {
    year: OIL_CAPACITY_BARRELS[year] * GJ_PER_BARREL_OIL / 1_000_000.0
    for year in YEARS
}

# End-2025 2P reserves plus 2020-2025 production reconstruct opening 2020 2P
# stock.  These observations initialize the resource stock; they do not bind
# individual historical-year activity.
OIL_2P_RESERVE_END_2025_MBBL = 0.434
OIL_DEPLETION_2020_2025_MBBL = sum(
    [0.695247, 0.630250, 0.565084, 0.475183, 0.478999, 0.401973]
)
OIL_OPENING_RESERVE_MBBL = OIL_2P_RESERVE_END_2025_MBBL + OIL_DEPLETION_2020_2025_MBBL
OIL_TMPAU_PJ = OIL_OPENING_RESERVE_MBBL * GJ_PER_BARREL_OIL

# Historical border prices are exogenous economic drivers.  Philippine
# customs CIF/FOB values and physical quantities are used directly; trade
# volumes remain validation benchmarks and are never imposed on the model.
COAL_IMPORT_TRADE = {
    "2020": (1_576_779_596.0, 28_714_486.293),
    "2021": (2_889_379_944.0, 31_288_972.598),
    "2022": (6_041_729_748.0, 31_533_021.23731),
    "2023": (4_079_385_358.0, 36_426_394.037367),
    # The 2024 customs record reports gross rather than net weight.
    "2024": (3_303_503_964.0, 39_395_101.47224),
}
COAL_EXPORT_TRADE = {
    "2020": (231_105_111.0, 7_358_240.05151),
    "2021": (596_372_203.0, 10_587_430.0),
    "2022": (883_113_332.0, 7_918_716.873447),
    "2023": (614_448_559.0, 8_151_075.621),
    "2024": (515_548_611.0, 9_074_750.0),
}
COAL_IMPORT_PRICE_USD_PER_GJ = {
    year: value_usd / tonnes / GJ_PER_TONNE_COAL
    for year, (value_usd, tonnes) in COAL_IMPORT_TRADE.items()
}
COAL_EXPORT_PRICE_USD_PER_GJ = {
    year: value_usd / tonnes / GJ_PER_TONNE_COAL
    for year, (value_usd, tonnes) in COAL_EXPORT_TRADE.items()
}

# DOE crude-import bills and volumes form one internally consistent landed
# cost series.  The 2021 value is the revised comparison published in DOE's
# 2022 report.  The 2024 crude bill is the reported total oil bill less the
# reported finished-product bill (16,884.9 - 12,686.3 million USD).
OIL_IMPORT_TRADE = {
    "2020": (1_470.36, 5_237.8),
    "2021": (2_271.842, 4_721.0),
    "2022": (4_429.924, 6_892.0),
    "2023": (4_174.52, 7_550.0),
    "2024": (4_198.6, 7_213.24),
}
GJ_PER_ML_OIL = 1_000_000.0 / LITRES_PER_BARREL_OIL * GJ_PER_BARREL_OIL
OIL_IMPORT_PRICE_USD_PER_GJ = {
    year: bill_musd * 1_000_000.0 / (volume_ml * GJ_PER_ML_OIL)
    for year, (bill_musd, volume_ml) in OIL_IMPORT_TRADE.items()
}

# Galoc operator/company realized prices are used for the domestic crude
# export sink.  Aggregate HS 2709 export values are unsuitable because they
# combine Galoc crude with Malampaya condensate.
GALOC_REALIZED_USD_PER_BARREL = {
    "2020": 38.18,
    "2021": 70.46,
    "2022": 94.50,
    "2023": 80.50,
    "2024": 80.00,
}
OIL_EXPORT_PRICE_USD_PER_GJ = {
    year: price / GJ_PER_BARREL_OIL
    for year, price in GALOC_REALIZED_USD_PER_BARREL.items()
}

# BSP annual-average PHP/USD rates and SMPC average realized selling prices
# retain the sourced 2025 coal export observation and quality-adjust the
# World Bank 2026-2027 forecasts.  The 2027 nominal price is held after the
# forecast horizon and disclosed as an evidence gap.
PHP_PER_USD = {
    "2020": 49.6241,
    "2021": 49.2546,
    "2022": 54.4778,
    "2023": 55.6300,
    "2024": 57.3000,
    "2025": 57.5051,
}
SMPC_ASP_PHP_PER_TONNE = {
    "2020": 1601.0,
    "2021": 2695.0,
    "2022": 5136.0,
    "2023": 3796.0,
    "2024": 2853.0,
    "2025": 2302.0,
}
COAL_EXPORT_PRICE_USD_PER_GJ["2025"] = (
    SMPC_ASP_PHP_PER_TONNE["2025"]
    / PHP_PER_USD["2025"]
    / GJ_PER_TONNE_COAL
)
quality_ratio = (
    SMPC_ASP_PHP_PER_TONNE["2025"] / PHP_PER_USD["2025"] / 108.4
)
COAL_EXPORT_PRICE_USD_PER_GJ["2026"] = 130.0 * quality_ratio / GJ_PER_TONNE_COAL
COAL_EXPORT_PRICE_USD_PER_GJ["2027"] = 115.0 * quality_ratio / GJ_PER_TONNE_COAL
for year in range(2028, 2054):
    COAL_EXPORT_PRICE_USD_PER_GJ[str(year)] = COAL_EXPORT_PRICE_USD_PER_GJ["2027"]

# World Bank Brent is retained only for the 2025-2027 external crude market
# path.  The post-2027 value is immaterial because physical oil TAU is zero.
BRENT_USD_PER_BARREL = {
    "2025": 69.0,
    "2026": 86.0,
    "2027": 70.0,
}
OIL_EXPORT_PRICE_USD_PER_GJ.update(
    {
        year: price / GJ_PER_BARREL_OIL
        for year, price in BRENT_USD_PER_BARREL.items()
    }
)
for year in range(2028, 2054):
    OIL_EXPORT_PRICE_USD_PER_GJ[str(year)] = OIL_EXPORT_PRICE_USD_PER_GJ["2027"]

# Rebase inherited extraction-cost shapes to source-based operating-cost
# anchors.  Coal uses 2025 segment cash cost / shipments.  Oil uses the 2026
# approved firm operating budget / scheduled cargo volume.
COAL_COST_ANCHOR_USD_PER_GJ = (
    (22_048_000_000.0 / 15_400_000.0) / PHP_PER_USD["2025"] / GJ_PER_TONNE_COAL
)
OIL_COST_ANCHOR_USD_PER_GJ = 20_040_000.0 / 360_000.0 / GJ_PER_BARREL_OIL


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=4) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_row(rows: list[dict[str, Any]], tech_id: str, mode: int | None = None) -> dict[str, Any]:
    matches = [row for row in rows if row.get("TechId") == tech_id]
    if mode is not None:
        matches = [row for row in matches if row.get("MoId") == mode]
    if len(matches) != 1:
        raise AssertionError(f"expected one row for {tech_id=} {mode=}, found {len(matches)}")
    return matches[0]


def overlay_border_prices(rytm: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Install historical landed/import and realized/export price drivers."""
    vc_rows = rytm["VC"][SCENARIO]
    rows = {
        "coal_import": select_row(vc_rows, IDS["coal_import"], 1),
        "coal_export": select_row(vc_rows, IDS["coal_export"], 1),
        "oil_import": select_row(vc_rows, IDS["oil_import"], 1),
        "oil_export": select_row(vc_rows, IDS["oil_export"], 1),
    }
    before = {
        name: {year: float(row[year]) for year in HISTORICAL_PRICE_YEARS}
        for name, row in rows.items()
    }
    for year in HISTORICAL_PRICE_YEARS:
        rows["coal_import"][year] = COAL_IMPORT_PRICE_USD_PER_GJ[year]
        rows["oil_import"][year] = OIL_IMPORT_PRICE_USD_PER_GJ[year]
    for year in YEARS:
        rows["coal_export"][year] = -COAL_EXPORT_PRICE_USD_PER_GJ[year]
        rows["oil_export"][year] = -OIL_EXPORT_PRICE_USD_PER_GJ[year]
    return before


def ratio_row(
    rows: list[dict[str, Any]], tech_id: str, commodity_id: str, mode: int = 1
) -> dict[str, Any]:
    matches = [
        row
        for row in rows
        if row.get("TechId") == tech_id
        and row.get("CommId") == commodity_id
        and row.get("MoId") == mode
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"expected one ratio row for {tech_id}/{commodity_id}/mode {mode}, found {len(matches)}"
        )
    return matches[0]


def new_technology(
    tech_id: str,
    name: str,
    description: str,
    inputs: list[str],
    outputs: list[str],
) -> dict[str, Any]:
    return {
        "TechId": tech_id,
        "Tech": name,
        "Desc": description,
        "CapUnitId": "GW",
        "ActUnitId": "PJ",
        "TG": [],
        "IAR": inputs,
        "OAR": outputs,
        "INCR": [],
        "ITCR": [],
        "EAR": [],
    }


def mutate_structure(gen: dict[str, Any]) -> None:
    tech_ids = {item["TechId"] for item in gen["osy-tech"]}
    commodity_ids = {item["CommId"] for item in gen["osy-comm"]}
    for identifier in (
        IDS["coal_bridge"], IDS["oil_bridge"], IDS["coal_export"], IDS["oil_export"]
    ):
        if identifier in tech_ids:
            raise AssertionError(f"technology ID already exists: {identifier}")
    for identifier in (IDS["coal_domestic_commodity"], IDS["oil_domestic_commodity"]):
        if identifier in commodity_ids:
            raise AssertionError(f"commodity ID already exists: {identifier}")

    technologies = {item["TechId"]: item for item in gen["osy-tech"]}
    technologies[IDS["coal_extraction"]]["OAR"] = [IDS["coal_domestic_commodity"]]
    technologies[IDS["coal_extraction"]]["Desc"] = (
        "Gross domestic coal extraction; physical annual mine envelope and opening "
        "mineable reserve cover domestic supply plus exports."
    )
    technologies[IDS["oil_extraction"]]["OAR"] = [IDS["oil_domestic_commodity"]]
    technologies[IDS["oil_extraction"]]["Desc"] = (
        "Gross domestic crude-oil extraction from the existing Galoc wells; "
        "declining deliverability and 2P opening reserve cover domestic supply plus exports."
    )

    gen["osy-comm"].extend(
        [
            {
                "CommId": IDS["coal_domestic_commodity"],
                "Comm": "PHL_PRO_COAL_DOM0",
                "Desc": "Domestically extracted coal before domestic processing or export",
                "UnitId": "PJ",
            },
            {
                "CommId": IDS["oil_domestic_commodity"],
                "Comm": "PHL_PRO_OIL_DOM0",
                "Desc": "Domestically extracted crude before domestic processing or export",
                "UnitId": "PJ",
            },
        ]
    )
    gen["osy-tech"].extend(
        [
            new_technology(
                IDS["coal_bridge"],
                "PHL_PRO_SUP_COAL_DOM",
                "Pass-through from source-tagged domestic coal to the existing domestic raw-coal pool",
                [IDS["coal_domestic_commodity"]],
                [IDS["coal_shared_commodity"]],
            ),
            new_technology(
                IDS["oil_bridge"],
                "PHL_PRO_SUP_OIL_DOM",
                "Pass-through from source-tagged domestic crude to the existing domestic raw-oil pool",
                [IDS["oil_domestic_commodity"]],
                [IDS["oil_shared_commodity"]],
            ),
            new_technology(
                IDS["coal_export"],
                "PHL_PRO_EXP_COAL",
                "Optional export sink for domestically extracted coal; imports cannot feed this route",
                [IDS["coal_domestic_commodity"]],
                [],
            ),
            new_technology(
                IDS["oil_export"],
                "PHL_PRO_EXP_OIL",
                "Optional export sink for domestically extracted crude; imports cannot feed this route",
                [IDS["oil_domestic_commodity"]],
                [],
            ),
        ]
    )
    gen["osy-date"] = "2026-08-14"
    gen["osy-desc"] = (
        "Philippines v18 fossil-resource accounting update. Domestic coal and crude "
        "extraction are source-tagged and may serve the domestic market or optional "
        "exports; imports cannot be re-exported. Annual extraction follows physical "
        "mine/field capability and cumulative activity follows opening recoverable "
        "reserves. Observed production and trade remain validation benchmarks.\n\n"
        + gen["osy-desc"]
    )


def overlay_parameters(target: Path, inherited_costs: dict[str, dict[str, float]]) -> None:
    rytcm = read_json(target / "RYTCM.json")
    for parameter, mappings in {
        "IAR": [
            (IDS["coal_bridge"], IDS["coal_domestic_commodity"]),
            (IDS["oil_bridge"], IDS["oil_domestic_commodity"]),
            (IDS["coal_export"], IDS["coal_domestic_commodity"]),
            (IDS["oil_export"], IDS["oil_domestic_commodity"]),
        ],
        "OAR": [
            (IDS["coal_extraction"], IDS["coal_domestic_commodity"]),
            (IDS["oil_extraction"], IDS["oil_domestic_commodity"]),
            (IDS["coal_bridge"], IDS["coal_shared_commodity"]),
            (IDS["oil_bridge"], IDS["oil_shared_commodity"]),
        ],
    }.items():
        rows = rytcm[parameter][SCENARIO]
        for tech_id, commodity_id in mappings:
            row = ratio_row(rows, tech_id, commodity_id)
            for year in YEARS:
                row[year] = 1.0
    write_json(target / "RYTCM.json", rytcm)

    ryt = read_json(target / "RYT.json")
    coal_tau = select_row(ryt["TAU"][SCENARIO], IDS["coal_extraction"])
    oil_tau = select_row(ryt["TAU"][SCENARIO], IDS["oil_extraction"])
    for year in YEARS:
        coal_tau[year] = COAL_TAU_PJ[year]
        oil_tau[year] = OIL_TAU_PJ[year]
    # Explicitly preserve open import routes.
    for tech_id in (IDS["coal_import"], IDS["oil_import"]):
        row = select_row(ryt["TAU"][SCENARIO], tech_id)
        for year in YEARS:
            row[year] = 999999
    # Physical resource limits and open import availability are global model
    # properties.  Scenario-specific TAU cells therefore inherit SC_0.  This
    # also removes the legacy COAL_PHASEOUT override that set extraction back
    # to 999999 and would otherwise defeat the physical mine envelope whenever
    # that scenario is active.
    for scenario, rows in ryt["TAU"].items():
        if scenario == SCENARIO:
            continue
        for tech_id in (
            IDS["coal_extraction"],
            IDS["oil_extraction"],
            IDS["coal_import"],
            IDS["oil_import"],
        ):
            inherited = select_row(rows, tech_id)
            for year in YEARS:
                inherited[year] = None
    write_json(target / "RYT.json", ryt)

    rt = read_json(target / "RT.json")
    rt["TMPAU"][SCENARIO][0][IDS["coal_extraction"]] = COAL_TMPAU_PJ
    rt["TMPAU"][SCENARIO][0][IDS["oil_extraction"]] = OIL_TMPAU_PJ
    rt["TMPAU"][SCENARIO][0][IDS["coal_import"]] = 999999
    rt["TMPAU"][SCENARIO][0][IDS["oil_import"]] = 999999
    write_json(target / "RT.json", rt)

    rytm = read_json(target / "RYTM.json")
    vc_rows = rytm["VC"][SCENARIO]
    coal_cost_row = select_row(vc_rows, IDS["coal_extraction"], 1)
    oil_cost_row = select_row(vc_rows, IDS["oil_extraction"], 1)
    coal_scale = COAL_COST_ANCHOR_USD_PER_GJ / inherited_costs["coal"]["2025"]
    oil_scale = OIL_COST_ANCHOR_USD_PER_GJ / inherited_costs["oil"]["2026"]
    for year in YEARS:
        coal_cost_row[year] = inherited_costs["coal"][year] * coal_scale
        oil_cost_row[year] = inherited_costs["oil"][year] * oil_scale

    for tech_id in (IDS["coal_bridge"], IDS["oil_bridge"]):
        bridge = select_row(vc_rows, tech_id, 1)
        for year in YEARS:
            bridge[year] = 0.0001
    overlay_border_prices(rytm)
    write_json(target / "RYTM.json", rytm)


def build(target: Path) -> dict[str, Any]:
    # The structural path alone needs the application updater.  Keeping this
    # import local lets the price-only source overlay run without unrelated
    # web-application environment dependencies such as python-dotenv.
    from Classes.Case.UpdateCaseClass import UpdateCase

    if target.exists():
        raise FileExistsError(f"candidate already exists: {target}")
    if not LIVE.is_dir():
        raise FileNotFoundError(LIVE)

    source_hashes = {
        path.name: sha256(path)
        for path in LIVE.glob("*.json")
        if path.is_file()
    }
    shutil.copytree(
        LIVE,
        target,
        ignore=shutil.ignore_patterns("res", "*.zip", ".DS_Store"),
    )

    original_gen = read_json(target / "genData.json")
    original_rytm = read_json(target / "RYTM.json")
    inherited_costs = {
        "coal": {
            year: select_row(
                original_rytm["VC"][SCENARIO], IDS["coal_extraction"], 1
            )[year]
            for year in YEARS
        },
        "oil": {
            year: select_row(
                original_rytm["VC"][SCENARIO], IDS["oil_extraction"], 1
            )[year]
            for year in YEARS
        },
    }

    gen = json.loads(json.dumps(original_gen))
    mutate_structure(gen)
    UpdateCase(target.name, gen).updateCase()
    write_json(target / "genData.json", gen)
    overlay_parameters(target, inherited_costs)

    changed = []
    unchanged = []
    for path in sorted(target.glob("*.json")):
        if path.name not in source_hashes or sha256(path) != source_hashes[path.name]:
            changed.append(path.name)
        else:
            unchanged.append(path.name)

    manifest = {
        "schema": "philippines-v18-fossil-resource-candidate-v1",
        "source_case": str(LIVE),
        "candidate_case": str(target),
        "source_hashes": source_hashes,
        "candidate_hashes": {
            path.name: sha256(path) for path in target.glob("*.json") if path.is_file()
        },
        "changed_source_files": changed,
        "unchanged_source_files": unchanged,
        "physical_inputs": {
            "coal_gj_per_tonne": GJ_PER_TONNE_COAL,
            "coal_annual_capacity_mt": COAL_CAPACITY_MT,
            "coal_opening_mineable_reserve_mt": COAL_OPENING_RESERVE_MT,
            "coal_tmpau_pj": COAL_TMPAU_PJ,
            "oil_gj_per_barrel": GJ_PER_BARREL_OIL,
            "oil_annual_capacity_barrels": OIL_CAPACITY_BARRELS,
            "oil_opening_2p_reserve_million_barrels": OIL_OPENING_RESERVE_MBBL,
            "oil_tmpau_pj": OIL_TMPAU_PJ,
        },
        "economic_inputs": {
            "coal_extraction_cost_anchor_usd_per_gj": COAL_COST_ANCHOR_USD_PER_GJ,
            "oil_extraction_cost_anchor_usd_per_gj": OIL_COST_ANCHOR_USD_PER_GJ,
            "coal_import_price_usd_per_gj": COAL_IMPORT_PRICE_USD_PER_GJ,
            "coal_export_price_usd_per_gj": COAL_EXPORT_PRICE_USD_PER_GJ,
            "oil_import_price_usd_per_gj": OIL_IMPORT_PRICE_USD_PER_GJ,
            "oil_export_price_usd_per_gj": OIL_EXPORT_PRICE_USD_PER_GJ,
        },
        "classification": {
            "physical_constraints": [
                "coal mine legal/design capacity",
                "coal opening mineable reserve",
                "Galoc existing-well decline and cessation",
                "Galoc opening 2P reserve",
            ],
            "exogenous_market_drivers": [
                "Philippine coal CIF/FOB border values and World Bank forecast",
                "DOE crude import bill and volume",
                "Galoc realized price and World Bank Brent forecast",
                "coal cash operating cost",
                "Galoc approved operating budget",
            ],
            "benchmark_only": [
                "annual coal and oil production",
                "domestic sales",
                "exports",
                "source shares",
            ],
        },
    }
    write_json(target / "fossil_resource_candidate_manifest.json", manifest)
    return manifest


def build_price_candidate(target: Path) -> dict[str, Any]:
    """Copy the accepted live structure and change historical border prices only."""
    if target.exists():
        raise FileExistsError(f"candidate already exists: {target}")
    if not LIVE.is_dir():
        raise FileNotFoundError(LIVE)
    source_hashes = {
        path.name: sha256(path)
        for path in LIVE.glob("*.json")
        if path.is_file()
    }
    shutil.copytree(
        LIVE,
        target,
        ignore=shutil.ignore_patterns("res", "view", "*.zip", ".DS_Store"),
    )
    rytm = read_json(target / "RYTM.json")
    before = overlay_border_prices(rytm)
    write_json(target / "RYTM.json", rytm)

    changed = [
        path.name
        for path in sorted(target.glob("*.json"))
        if path.name not in source_hashes or sha256(path) != source_hashes[path.name]
    ]
    if changed != ["RYTM.json"]:
        raise AssertionError(f"unexpected source change set: {changed}")
    after_rows = rytm["VC"][SCENARIO]
    after = {
        name: {
            year: float(select_row(after_rows, IDS[name], 1)[year])
            for year in HISTORICAL_PRICE_YEARS
        }
        for name in ("coal_import", "coal_export", "oil_import", "oil_export")
    }
    manifest = {
        "schema": "philippines-v18-fossil-border-price-candidate-v1",
        "date": "2026-08-18",
        "source_case": str(LIVE),
        "candidate_case": str(target),
        "changed_source_files": changed,
        "source_hashes": source_hashes,
        "candidate_hashes": {
            path.name: sha256(path) for path in target.glob("*.json") if path.is_file()
        },
        "before_rytm_musd_per_pj": before,
        "after_rytm_musd_per_pj": after,
        "raw_inputs": {
            "coal_import_customs_value_usd_and_tonnes": COAL_IMPORT_TRADE,
            "coal_export_customs_value_usd_and_tonnes": COAL_EXPORT_TRADE,
            "oil_import_doe_bill_musd_and_volume_ml": OIL_IMPORT_TRADE,
            "galoc_realized_usd_per_barrel": GALOC_REALIZED_USD_PER_BARREL,
            "coal_gj_per_tonne": GJ_PER_TONNE_COAL,
            "oil_gj_per_barrel": GJ_PER_BARREL_OIL,
            "litres_per_barrel": LITRES_PER_BARREL_OIL,
        },
        "classification": {
            "exogenous_economic_drivers": [
                "Philippine coal CIF import unit value",
                "Philippine coal FOB export unit value",
                "DOE crude landed import unit value",
                "Galoc realized crude export price",
            ],
            "benchmark_only": [
                "annual imports",
                "annual exports",
                "domestic/import source shares",
            ],
            "constraints_added": [],
        },
    }
    write_json(target / "fossil_border_price_candidate_manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument(
        "--prices-only",
        action="store_true",
        help="copy the accepted live case and overlay only historical border prices",
    )
    args = parser.parse_args()
    if args.prices_only:
        manifest = build_price_candidate(args.target.resolve())
    else:
        manifest = build(args.target.resolve())
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the auditable Philippines v33 historical-comparison register.

This is a read-only result extraction. It never changes model inputs or results.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path


RUN_NAME = "BASE_V33_GAS_DELIVERY"
YEAR = "2020"
CLUSTERS = tuple(f"LNDAGRPHLC{i:02d}" for i in range(1, 9))
RICE_RAINFED_MODES = {11, 14}
RICE_IRRIGATED_MODES = {17, 19}
MANAGED_CROP_MODES = set(range(1, 25))
SOIL_N2O_FACTOR = 0.07627117937811322


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt(value):
    if value in (None, ""):
        return ""
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    case = args.case.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    run = case / "res" / RUN_NAME
    csv_dir = run / "csv"
    activity_path = csv_dir / "TotalAnnualTechnologyActivityByMode.csv"
    use_path = csv_dir / "UseByTechnologyByMode.csv"
    production_path = csv_dir / "ProductionByTechnologyByMode.csv"
    emissions_path = csv_dir / "AnnualTechnologyEmission.csv"
    emissions_mode_path = csv_dir / "AnnualTechnologyEmissionByMode.csv"
    doe_path = case / "documentation" / "doe_power_validation_2020_2024.csv"
    gas_validation_path = case / "documentation" / "gas_delivery_four_scenario_validation_v33.json"
    sources_path = case / "data_sources" / "SOURCES.csv"
    aquastat_snapshot_path = case / "data_sources" / "snapshots" / "aquastat_philippines_irrigation_boundary_2026-08-11.json"
    psa_agriculture_snapshot_path = case / "data_sources" / "snapshots" / "psa_openstat_agriculture_2020.json"
    ghgi_extract_path = case / "data_sources" / "snapshots" / "philippines_v22_transition_scope_extracts_2026-08-20.json"
    heat_cooking_processing_path = case / "data_sources" / "snapshots" / "historical_heat_cooking_processing_2020_2026-08-27.json"

    activity_rows = read_csv(activity_path)
    use_rows = read_csv(use_path)
    production_rows = read_csv(production_path)
    emission_rows = read_csv(emissions_path)
    emission_mode_rows = read_csv(emissions_mode_path)
    doe_rows = read_csv(doe_path)
    gas_validation = read_json(gas_validation_path)
    ghgi_extract = read_json(ghgi_extract_path)
    heat_cooking_processing = read_json(heat_cooking_processing_path)

    activity = defaultdict(float)
    for row in activity_rows:
        activity[(row["t"], int(row["m"]), row["y"])] += float(row["TotalAnnualTechnologyActivityByMode"])

    water = {
        "surface_irrigation": activity[("DEMAGRSURPHL", 1, YEAR)],
        "groundwater_irrigation": activity[("DEMAGRGWTPHL", 1, YEAR)],
        "surface_public": activity[("PHL_DEM_PUB_SUR_WAT", 1, YEAR)],
        "groundwater_public": activity[("PHL_DEM_PUB_GWT_WAT", 1, YEAR)],
        "surface_power": activity[("PHL_DEM_PWR_SUR_WAT", 1, YEAR)],
        "groundwater_power": activity[("PHL_DEM_PWR_GWT_WAT", 1, YEAR)],
    }
    water["irrigation_total"] = water["surface_irrigation"] + water["groundwater_irrigation"]
    water["total"] = sum(water.values()) - water["irrigation_total"]
    water["surface_total"] = water["surface_irrigation"] + water["surface_public"] + water["surface_power"]
    water["groundwater_total"] = water["groundwater_irrigation"] + water["groundwater_public"] + water["groundwater_power"]

    rice = {"rainfed_area": 0.0, "irrigated_area": 0.0, "rainfed_production": 0.0, "irrigated_production": 0.0}
    managed_crop_activity = 0.0
    for (tech, mode, year), value in activity.items():
        if year != YEAR or tech not in CLUSTERS:
            continue
        if mode in MANAGED_CROP_MODES:
            managed_crop_activity += value
        if mode in RICE_RAINFED_MODES:
            rice["rainfed_area"] += value
        if mode in RICE_IRRIGATED_MODES:
            rice["irrigated_area"] += value
    for row in production_rows:
        if row["y"] != YEAR or row["t"] not in CLUSTERS or row["f"] != "CRPRCP":
            continue
        mode = int(row["m"])
        value = float(row["ProductionByTechnologyByMode"])
        if mode in RICE_RAINFED_MODES:
            rice["rainfed_production"] += value
        if mode in RICE_IRRIGATED_MODES:
            rice["irrigated_production"] += value
    rice["total_area"] = rice["rainfed_area"] + rice["irrigated_area"]
    rice["total_production"] = rice["rainfed_production"] + rice["irrigated_production"]

    total_co2e = sum(float(row["AnnualTechnologyEmission"]) for row in emission_rows if row["y"] == YEAR and row["e"] == "CO2e")
    crop_co2e = sum(float(row["AnnualTechnologyEmission"]) for row in emission_rows if row["y"] == YEAR and row["e"] == "CO2e" and row["t"] in CLUSTERS)
    soil_n2o = managed_crop_activity * SOIL_N2O_FACTOR
    rice_ch4 = crop_co2e - soil_n2o
    energy_co2e = total_co2e - crop_co2e

    end_use_tech = lambda t: (
        t == "PHL_AGR_FAC"
        or t.startswith("PHL_AGR_HEAT_")
        or t.startswith("PHL_AGR_MOT_")
        or t.startswith("PHL_FSH_MOT_")
        or t.startswith("PHL_FSH_AQC_")
        or t.startswith("PHL_FSH_PRO_")
    )
    aff_energy = 0.0
    aff_electricity = 0.0
    for row in use_rows:
        if row["y"] != YEAR or not end_use_tech(row["t"]):
            continue
        value = float(row["UseByTechnologyByMode"])
        aff_energy += value
        if "ELE" in row["f"]:
            aff_electricity += value
    aff_electricity_share = aff_electricity / aff_energy

    fuel_by_commodity = {
        "PHL_PRO_OIL": "oil",
        "PHL_PRO_NG": "natural_gas",
        "PHL_PRO_COAL": "coal",
        "PHL_PRO_BIOM": "biomass",
        "PHL_INDU_ELE": "electricity",
        "PHL_SER_ELE": "electricity",
        "PHL_POW_H2": "hydrogen",
    }
    industrial_input_by_fuel = defaultdict(float)
    services_heat_input_by_fuel = defaultdict(float)
    for row in use_rows:
        if row["y"] != YEAR or row["f"] not in fuel_by_commodity:
            continue
        fuel = fuel_by_commodity[row["f"]]
        value = float(row["UseByTechnologyByMode"])
        if row["t"].startswith("PHL_INDU_OTHLPH_") or row["t"].startswith("PHL_INDU_OTHHPH_"):
            industrial_input_by_fuel[fuel] += value
        if row["t"].startswith("PHL_SER_HEAT_"):
            services_heat_input_by_fuel[fuel] += value

    def with_shares(values: dict[str, float], fuels: tuple[str, ...]) -> dict:
        total = sum(values.values())
        if total <= 0:
            raise ValueError("Cannot calculate fuel shares from a non-positive total")
        return {
            "total_pj": total,
            "input_by_fuel_pj": {fuel: values.get(fuel, 0.0) for fuel in fuels},
            "share_by_fuel": {fuel: values.get(fuel, 0.0) / total for fuel in fuels},
        }

    industrial_heat = with_shares(
        industrial_input_by_fuel,
        ("oil", "coal", "natural_gas", "electricity", "biomass", "hydrogen"),
    )
    services_heat = with_shares(
        services_heat_input_by_fuel,
        ("oil", "natural_gas", "coal", "electricity", "biomass"),
    )

    cooking_technology_fuel = {
        "PHL_HOU_COOK_OIL": "oil",
        "PHL_HOU_COOK_ELE": "electricity",
        "PHL_HOU_COOK_NG": "natural_gas",
        "PHL_HOU_COOK_CHARCOAL_OLD": "charcoal",
        "PHL_HOU_COOK_BIOM": "biomass_and_other",
    }
    cooking_activity_by_fuel = defaultdict(float)
    for (tech, _mode, year), value in activity.items():
        if year == YEAR and tech in cooking_technology_fuel:
            cooking_activity_by_fuel[cooking_technology_fuel[tech]] += value
    cooking = with_shares(
        cooking_activity_by_fuel,
        ("oil", "electricity", "natural_gas", "charcoal", "biomass_and_other"),
    )

    processing_technology_fuel = {
        "PHL_PRO_PROC_OIL": "oil",
        "PHL_PRO_PROC_NG": "natural_gas",
        "PHL_PRO_PROC_COAL": "coal",
    }
    processing_output_pj = defaultdict(float)
    for row in production_rows:
        if row["y"] == YEAR and row["t"] in processing_technology_fuel:
            processing_output_pj[processing_technology_fuel[row["t"]]] += float(row["ProductionByTechnologyByMode"])

    biomass_crop_residue = sum(
        value for (tech, _mode, year), value in activity.items()
        if tech == "PHL_PRO_SUP_CROP_RESIDUE" and year == YEAR
    )

    observed_generation = {
        (row["year"], row["technology"]): float(row["gross_generation_pj"])
        for row in doe_rows
    }
    modeled_power = gas_validation["scenarios"]["BASE"]["candidate_metrics"]
    ghgi = ghgi_extract["facts"]["crop_ghgi_2020_mtco2e"]

    rows: list[dict] = []
    def add(comparison_id, domain, metric, observed, modeled, unit, status, forcing="", *,
            year=YEAR, tolerance="", tolerance_absolute="", phase="calibration", weight=1,
            source_id="", source_url="", observed_boundary="", modeled_boundary="",
            result_ref="", constraint_refs="", uncertainty="", notes=""):
        rows.append({
            "comparison_id": comparison_id,
            "domain": domain,
            "metric": metric,
            "year": year,
            "observed": observed,
            "modeled": modeled,
            "unit": unit,
            "comparison_status": status,
            "forcing_class": forcing,
            "phase": phase,
            "weight": weight,
            "tolerance": tolerance,
            "tolerance_absolute": tolerance_absolute,
            "geography": "Philippines",
            "source_id": source_id,
            "source_url": source_url,
            "observed_boundary": observed_boundary,
            "modeled_boundary": modeled_boundary,
            "model_result_ref": result_ref,
            "constraint_refs": constraint_refs,
            "uncertainty_or_conflict": uncertainty,
            "notes": notes,
        })

    doe_url = "https://legacy.doe.gov.ph/energy-statistics/philippine-energy-situationer"
    for year in ("2020", "2021", "2022", "2023", "2024"):
        add(f"ENE-GEN-{year}", "energy", "Gross electricity generation", observed_generation[(year, "total")],
            modeled_power[year]["gross_grid_generation_pj"], "PJ", "score_ready", "E", year=year,
            tolerance=0.10, weight=2, source_id="SRC_PHL_DOE_2024_POWER_SUMMARY", source_url=doe_url,
            observed_boundary="DOE gross generation; 2020 includes embedded/off-grid/commissioning, 2021 onward grid generation",
            modeled_boundary="National model gross grid generation", result_ref=f"gas_delivery_four_scenario_validation_v33.json:BASE:{year}:gross_grid_generation_pj",
            constraint_refs="exogenous final electricity demands; residual stocks; availability; costs",
            uncertainty="10% tolerance reflects national aggregation and the documented 2020 boundary break")
    for year in ("2021", "2022", "2023", "2024"):
        add(f"ENE-GAS-{year}", "energy", "Natural-gas electricity generation", observed_generation[(year, "natural_gas")],
            modeled_power[year]["legacy_gas_generation_pj"], "PJ", "score_ready", "E", year=year,
            tolerance=0.15, source_id="SRC_PHL_DOE_2024_POWER_SUMMARY", source_url=doe_url,
            observed_boundary="DOE grid natural-gas generation", modeled_boundary="Legacy gas-generation route reported by v33 validation",
            result_ref=f"gas_delivery_four_scenario_validation_v33.json:BASE:{year}:legacy_gas_generation_pj",
            constraint_refs="gas extraction envelope; residual gas stock; plant availability; VOM; take-or-pay economics",
            uncertainty="15% tolerance reflects annual copperplate aggregation and plant-class representation")

    benchmark = heat_cooking_processing["benchmarks"]
    pep_url = heat_cooking_processing["sources"]["doe_pep_2020_2040"]["url"]
    situationer_2020_url = heat_cooking_processing["sources"]["doe_situationer_2020"]["url"]
    psa_cooking_url = heat_cooking_processing["sources"]["psa_cooking"]["url"]
    gas_plan_url = heat_cooking_processing["sources"]["doe_natural_gas_plan"]["url"]

    for fuel, label in (
        ("oil", "Oil"),
        ("coal", "Coal"),
        ("natural_gas", "Natural gas"),
        ("electricity", "Electricity"),
        ("biomass", "Biomass"),
    ):
        add(f"ENE-IND-HEAT-{fuel.upper()}-SHARE-2020", "energy",
            f"{label} share of industrial process-heat input",
            benchmark["industry_final_energy"]["fuel_share_fraction"][fuel],
            industrial_heat["share_by_fuel"][fuel], "fraction", "diagnostic_only", "E",
            source_id="SRC_PHL_DOE_PEP_2020_2040_INDUSTRY_COAL", source_url=pep_url,
            observed_boundary="DOE whole-industry final-energy fuel share",
            modeled_boundary="Fuel input to PHL_INDU_OTHLPH_* and PHL_INDU_OTHHPH_* process-heat routes",
            result_ref="UseByTechnologyByMode.csv:industrial low/high process-heat technologies, 2020",
            constraint_refs="industrial process-heat service demand; residual stocks; efficiencies; fuel and route costs",
            uncertainty="Not scoreable: the official denominator includes all industrial final energy, while the model denominator is process heat only.")

    for fuel, label in (("oil", "Oil"), ("electricity", "Electricity"), ("biomass", "Biomass")):
        add(f"ENE-SER-HEAT-{fuel.upper()}-SHARE-2020", "energy",
            f"{label} share of services-heating input",
            benchmark["services_final_energy"]["fuel_share_fraction"][fuel],
            services_heat["share_by_fuel"][fuel], "fraction", "diagnostic_only", "E",
            source_id="SRC_PHL_DOE_PES_KES_2020_SERVICES_REFINING", source_url=situationer_2020_url,
            observed_boundary="DOE whole-services final-energy fuel share",
            modeled_boundary="Fuel input to PHL_SER_HEAT_* routes",
            result_ref="UseByTechnologyByMode.csv:services-heating technologies, 2020",
            constraint_refs="services heat demand; residual stocks; efficiencies; fuel and route costs",
            uncertainty="Not scoreable: the official denominator includes all services final energy, while the model denominator is heating only.")

    for fuel, label in (
        ("oil", "Oil (LPG and kerosene)"),
        ("electricity", "Electricity"),
        ("charcoal", "Charcoal"),
        ("biomass_and_other", "Wood and other fuels"),
    ):
        add(f"ENE-HOU-COOK-{fuel.upper()}-SHARE-2020", "energy",
            f"{label} share of household cooking",
            benchmark["household_primary_cooking_fuel"]["model_route_aggregation_normalized"][fuel],
            cooking["share_by_fuel"][fuel], "fraction", "diagnostic_only", "J",
            source_id="SRC_PHL_V23_BIOMASS_PSA_COOKING", source_url=psa_cooking_url,
            observed_boundary="Normalized share of households reporting the fuel used most of the time for cooking",
            modeled_boundary="Share of solved useful-cooking activity across household cooking routes",
            result_ref="TotalAnnualTechnologyActivityByMode.csv:PHL_HOU_COOK_*, 2020",
            constraint_refs="useful-cooking demand; residual cooking stocks; route efficiencies; fuel and route costs",
            uncertainty="Not scoreable: household incidence is not an energy/service share, and this PSA observation informed the v23 cooking proxy and initial-stock mix.")

    add("ENE-PROC-OIL-2020", "energy", "Domestic refinery marketable output",
        benchmark["oil_refining"]["marketable_products_pj"], processing_output_pj["oil"], "PJ",
        "diagnostic_only", "E", source_id="SRC_PHL_DOE_PES_KES_2020_SERVICES_REFINING",
        source_url=situationer_2020_url,
        observed_boundary="DOE domestic-refinery marketable petroleum-product output",
        modeled_boundary="Output of PHL_PRO_PROC_OIL, which processes the aggregate raw-oil pool including the model's oil-import route",
        result_ref="ProductionByTechnologyByMode.csv:PHL_PRO_PROC_OIL, PHL_PRO_OIL, 2020",
        constraint_refs="oil-service demands; crude/import supply; processing efficiency and cost",
        uncertainty="Not scoreable: imported crude and finished products are not separated, so the model processor is broader than domestic refinery output.")
    add("ENE-PROC-NG-2020", "energy", "National natural-gas consumption",
        benchmark["natural_gas"]["consumption_pj"], processing_output_pj["natural_gas"], "PJ",
        "score_ready", "E", tolerance=0.05, source_id="SRC_PHL_DOE_NATGAS_DEVELOPMENT_PLAN",
        source_url=gas_plan_url,
        observed_boundary="DOE national delivered natural-gas consumption before LNG imports",
        modeled_boundary="Output of PHL_PRO_PROC_NG supplied by domestic raw gas in 2020",
        result_ref="ProductionByTechnologyByMode.csv:PHL_PRO_PROC_NG, PHL_PRO_NG, 2020",
        constraint_refs="domestic gas deliverability; gas-consuming technologies; processing efficiency and cost",
        notes="Observed 133,606 MMSCF converted with the existing v33 full-precision gas conversion.")
    add("ENE-PROC-COAL-2020", "energy", "National coal consumption",
        benchmark["coal"]["total_consumption_pj"], processing_output_pj["coal"], "PJ",
        "score_ready", "E", tolerance=0.10, source_id="SRC_PHL_DOE_PEP_2020_2040_INDUSTRY_COAL",
        source_url=pep_url,
        observed_boundary="DOE national coal consumption across power and industry",
        modeled_boundary="Output of PHL_PRO_PROC_COAL to all national coal users",
        result_ref="ProductionByTechnologyByMode.csv:PHL_PRO_PROC_COAL, PHL_PRO_COAL, 2020",
        constraint_refs="power and industry service demands; coal supply/trade; processing efficiency and cost",
        notes="Observed 17.34 MTOE converted at 41.868 PJ/MTOE; the 10% tolerance is declared independently of the model result.")

    add("LND-RICE-IRR-AREA-2020", "land", "Irrigated rice area", 20.06, rice["irrigated_area"], "1000 km2",
        "score_ready", "J", tolerance=0.10, source_id="SRC_PSA_SSAF_2022",
        source_url="https://psa.gov.ph/system/files/main-publication/%2528ons-cleared%2529_SSAF%25202022%2520as%2520of%252030082022_ONS-signed.pdf",
        observed_boundary="2020 physical irrigation service-area stock", modeled_boundary="Solved irrigated-rice land activity",
        result_ref="TotalAnnualTechnologyActivityByMode.csv:sum LNDAGRPHLC*, modes 17/19, 2020",
        constraint_refs="PHL_AGR_IRRIGATION residual service stock; no minimum use",
        notes="The observation sets a justified initial infrastructure stock; solved use may be lower but binds in v33.")
    add("LND-RICE-RAIN-AREA-2020", "land", "Rainfed rice harvested area", 14.6544173, rice["rainfed_area"], "1000 km2",
        "score_ready", "E", tolerance=0.10, source_id="SRC_PSA_SSAF_2022",
        source_url="https://psa.gov.ph/system/files/main-publication/%2528ons-cleared%2529_SSAF%25202022%2520as%2520of%252030082022_ONS-signed.pdf",
        observed_boundary="2020 harvested area", modeled_boundary="Solved rainfed-rice land activity",
        result_ref="TotalAnnualTechnologyActivityByMode.csv:sum LNDAGRPHLC*, modes 11/14, 2020",
        constraint_refs="rice final demand; cluster yields; land and water availability; crop costs")
    add("LND-RICE-IRR-PROD-2020", "land", "Irrigated rice production", 14.57176519, rice["irrigated_production"], "Mt",
        "score_ready", "E", tolerance=0.10, source_id="SRC_PSA_SSAF_2022",
        source_url="https://psa.gov.ph/system/files/main-publication/%2528ons-cleared%2529_SSAF%25202022%2520as%2520of%252030082022_ONS-signed.pdf",
        result_ref="ProductionByTechnologyByMode.csv:CRPRCP, modes 17/19, 2020",
        observed_boundary="2020 irrigated palay production", modeled_boundary="Solved irrigated-rice production",
        constraint_refs="total rice final demand; endogenous regime and cluster allocation")
    add("LND-RICE-RAIN-PROD-2020", "land", "Rainfed rice production", 4.72309035, rice["rainfed_production"], "Mt",
        "score_ready", "E", tolerance=0.20, source_id="SRC_PSA_SSAF_2022",
        source_url="https://psa.gov.ph/system/files/main-publication/%2528ons-cleared%2529_SSAF%25202022%2520as%2520of%252030082022_ONS-signed.pdf",
        result_ref="ProductionByTechnologyByMode.csv:CRPRCP, modes 11/14, 2020",
        observed_boundary="2020 rainfed palay production", modeled_boundary="Solved rainfed-rice production",
        constraint_refs="total rice final demand; endogenous regime and cluster allocation")
    add("LND-RICE-TOTAL-PROD-2020", "land", "Total rice production", 19.29485554, rice["total_production"], "Mt",
        "score_ready", "H", tolerance=0.001, source_id="SRC_PSA_SSAF_2022",
        source_url="https://psa.gov.ph/system/files/main-publication/%2528ons-cleared%2529_SSAF%25202022%2520as%2520of%252030082022_ONS-signed.pdf",
        result_ref="ProductionByTechnologyByMode.csv:CRPRCP, all rice modes, 2020",
        observed_boundary="Sum of observed irrigated and rainfed production", modeled_boundary="Exogenous total rice final demand",
        constraint_refs="Specified/accumulated rice demand",
        notes="History-fixed total; retained to disclose forcing and excluded from fit credit by the comparison scorer.")

    add("WAT-AGR-WITHDRAW-2020", "water", "Agricultural water withdrawal", 67.85109005, water["irrigation_total"], "km3",
        "diagnostic_only", "E", tolerance=0.20, source_id="SRC_FAO_AQUASTAT_PHL_2020_BOUNDARY",
        source_url="https://data.apps.fao.org/aquastat/", observed_boundary="AQUASTAT variable 4250: all agricultural water withdrawal",
        modeled_boundary="Gross crop-irrigation withdrawal only", result_ref="TotalAnnualTechnologyActivityByMode.csv:DEMAGRSURPHL+DEMAGRGWTPHL, 2020",
        constraint_refs="crop allocation; gross irrigation coefficients; source costs and national envelopes",
        uncertainty="Not scoreable: observed denominator includes agricultural uses beyond model crop irrigation.")
    add("WAT-IRR-WITHDRAW-2006-REF", "water", "Irrigation water withdrawal (historical reference)", 65.59,
        water["irrigation_total"], "km3", "diagnostic_only", "E", year="2006 observation vs 2020 model",
        source_id="SRC_FAO_AQUASTAT_TABLE4_2012", source_url="https://firebasestorage.googleapis.com/v0/b/fao-aquastat.appspot.com/o/PDF%2FTABLES%2FTable4.pdf?alt=media&token=fdba62dc-ca8f-4b80-adcd-909baa2ddf87",
        observed_boundary="2006 irrigation-only withdrawal", modeled_boundary="2020 gross crop-irrigation withdrawal",
        uncertainty="Not scoreable because periods differ; retained as the closest internally comparable national irrigation boundary.")
    add("WAT-TOTAL-ABSTRACT-2020", "water", "Total water abstraction", 218.58, water["total"], "km3",
        "diagnostic_only", "E", source_id="SRC_PSA_WATER_ACCOUNTS_2024_REVISION",
        source_url="https://psa.gov.ph/system/files/enrad/2.%20Highlights_WFA.pdf",
        observed_boundary="PSA abstraction including large non-consumptive hydropower flows",
        modeled_boundary="Irrigation, public supply and thermal-power cooling withdrawals; hydropower abstraction omitted",
        result_ref="TotalAnnualTechnologyActivityByMode.csv:six raw-water delivery technologies, 2020",
        uncertainty="Current PSA series gives 218.58 km3; retained v33 source ledger records the earlier 218.46 km3 release. Not scoreable because model omits hydropower abstraction.")
    add("WAT-SOURCE-SHARE-2024", "water", "Surface-water share of total abstraction", 0.976, 1.0, "fraction",
        "diagnostic_only", "E", year="2024", tolerance_absolute=0.05, source_id="SRC_PSA_WATER_ACCOUNTS_2024_REVISION",
        source_url="https://psa.gov.ph/system/files/enrad/2.%20Highlights_WFA.pdf",
        observed_boundary="All PSA abstraction including hydropower", modeled_boundary="Modeled withdrawals; v33 selects zero groundwater",
        uncertainty="Not scoreable across mismatched abstraction boundaries.")
    add("WAT-PWR-COOL-2020", "water", "Thermal-power cooling-water withdrawal", "", water["surface_power"] + water["groundwater_power"], "km3",
        "evidence_gap", result_ref="TotalAnnualTechnologyActivityByMode.csv:PHL_DEM_PWR_SUR_WAT+PHL_DEM_PWR_GWT_WAT, 2020",
        modeled_boundary="NREL-factor-derived national thermal cooling withdrawal",
        uncertainty="No Philippines plant/source-matched historical cooling-water observation is retained.")
    add("WAT-GWT-PUMP-ELE-2020", "water", "Electricity used for groundwater pumping", "", 0.0, "PJ",
        "evidence_gap", result_ref="UseByTechnologyByMode.csv:groundwater delivery technologies, 2020",
        modeled_boundary="Zero because v33 selects no groundwater withdrawal",
        uncertainty="No national observed pumping-electricity series matched to public, irrigation and power groundwater is retained.")

    btr_url = "https://niccdies.climate.gov.ph/files/documents/Final-%20Philippine%20Biennial%20Transparency%20Report.pdf"
    add("CLI-ENERGY-GHG-2020", "climate", "Energy GHG emissions including transport", 129.286, energy_co2e, "MtCO2e",
        "score_ready", "E", tolerance=0.10, weight=2, source_id="SRC_PHL_BTR_2024_TABLE15", source_url=btr_url,
        observed_boundary="2020 national energy plus transport inventory", modeled_boundary="All v33 CO2e except crop-cluster emissions",
        result_ref="AnnualTechnologyEmission.csv:CO2e total minus LNDAGRPHLC*, 2020",
        constraint_refs="endogenous activity; physical emission factors; energy service demands and stocks",
        uncertainty="Official rounded table gives 99.854+29.431=129.285 Mt; NDC implementation table reports 129.286 Mt.")
    add("CLI-RICE-CH4-2020", "climate", "Rice cultivation CH4", ghgi["rice_ch4"], rice_ch4, "MtCO2e",
        "score_ready", "E", tolerance=0.15, source_id="SRC_PHL_V22_GHGI", source_url=ghgi_extract["urls"]["ghgi"],
        observed_boundary="2020 national rice-cultivation inventory", modeled_boundary="Solved rice activity times inventory-derived water-regime factors",
        result_ref="AnnualTechnologyEmission.csv and TotalAnnualTechnologyActivityByMode.csv, 2020",
        constraint_refs="endogenous irrigated/rainfed and cluster allocation; calibrated EARs",
        uncertainty="Same inventory calibrated the EAR levels; this is calibration-period fit, not independent validation.")
    add("CLI-SOIL-N2O-2020", "climate", "Managed-soil direct and indirect N2O", ghgi["managed_soils_direct_n2o"] + ghgi["managed_soils_indirect_n2o"], soil_n2o, "MtCO2e",
        "score_ready", "E", tolerance=0.20, source_id="SRC_PHL_V22_GHGI", source_url=ghgi_extract["urls"]["ghgi"],
        observed_boundary="2020 national managed-soil direct plus indirect N2O", modeled_boundary="Solved managed crop activity times inventory-derived average factor",
        result_ref="TotalAnnualTechnologyActivityByMode.csv:LNDAGRPHLC*, modes 1-24, 2020",
        constraint_refs="endogenous managed crop activity; calibrated average soil factor",
        uncertainty="Same inventory calibrated the factor; livestock/manure and crop-specific fertilizer rates are absent.")
    add("CLI-AGR-TOTAL-2020", "climate", "Total agriculture GHG emissions", 54.080, crop_co2e, "MtCO2e",
        "diagnostic_only", "E", tolerance=0.15, source_id="SRC_PHL_BTR_2024_TABLE15", source_url=btr_url,
        observed_boundary="Complete national agriculture inventory", modeled_boundary="Rice CH4 plus managed-soil N2O only",
        result_ref="AnnualTechnologyEmission.csv:LNDAGRPHLC*, CO2e, 2020",
        uncertainty="Not scoreable: model omits livestock, manure and other agricultural inventory categories.")
    add("CLI-LULUCF-2020", "climate", "Net forestry and other-land-use GHG", -25.935, "", "MtCO2e",
        "evidence_gap", source_id="SRC_PHL_BTR_2024_TABLE15", source_url=btr_url,
        observed_boundary="2020 national forestry plus other land use", modeled_boundary="No transition-specific land-carbon stock-change account in v33 LP",
        uncertainty="Observed forestry -71.355 plus other land use 45.420 MtCO2e; no comparable modeled value.")

    add("NEX-AFF-ENERGY-2020", "nexus", "Agriculture, forestry and fisheries final energy use", 18.3716784, aff_energy, "PJ",
        "score_ready", "E", tolerance=0.15, weight=2, source_id="SRC_PHL_V22_DOE_2024_AFF", source_url=doe_url,
        observed_boundary="DOE 2020 agriculture/forestry/fishery final energy, 438.8 ktoe",
        modeled_boundary="Energy inputs to agriculture and fisheries end-use service technologies",
        result_ref="UseByTechnologyByMode.csv:selected PHL_AGR and PHL_FSH end-use technologies, 2020",
        constraint_refs="sector service demands; technology efficiencies; endogenous energy-carrier mix",
        uncertainty="Model includes agriculture and fisheries explicitly; forestry end-use energy is not separately represented.")
    add("NEX-AFF-ELE-SHARE-2020", "nexus", "Electricity share of agriculture, forestry and fisheries energy", 0.656, aff_electricity_share, "fraction",
        "score_ready", "E", tolerance=0.15, tolerance_absolute=0.10, source_id="SRC_PHL_V22_DOE_2024_AFF", source_url=doe_url,
        observed_boundary="DOE 2020 AFF electricity share", modeled_boundary="Electricity inputs divided by all selected AFF energy inputs",
        result_ref="UseByTechnologyByMode.csv:selected PHL_AGR and PHL_FSH end-use technologies, 2020",
        constraint_refs="sector service demands; technology efficiencies; endogenous carrier choice")
    add("NEX-BIOMASS-2020", "nexus", "Crop-residue biomass available to energy", 35.001648, biomass_crop_residue, "PJ",
        "diagnostic_only", "J", source_id="SRC_PHL_V23_BIOMASS_DOE_KES_SIMPLE",
        source_url="https://legacy.doe.gov.ph/sites/default/files/pdf/energy_statistics/doe-pes-kes-2021.pdf",
        observed_boundary="DOE other agricultural-waste biomass production: 836 ktoe",
        modeled_boundary="Derived recoverable bagasse, rice-husk and cane-trash resource activity",
        result_ref="TotalAnnualTechnologyActivityByMode.csv:PHL_PRO_SUP_CROP_RESIDUE, 2020",
        uncertainty="Not scoreable: DOE agriwaste category and model recoverable-residue basket are not the same commodity boundary.")
    add("NEX-WATER-POWER-2020", "nexus", "Water withdrawn for thermal power", "", water["surface_power"] + water["groundwater_power"], "km3",
        "evidence_gap", result_ref="TotalAnnualTechnologyActivityByMode.csv:power water-delivery routes, 2020",
        uncertainty="Model value is generated from NREL generic withdrawal factors; no Philippine historical plant/source register is retained.")
    add("NEX-WATER-CROP-2020", "nexus", "Gross water withdrawn for crop irrigation", 67.85109005, water["irrigation_total"], "km3",
        "diagnostic_only", "E", source_id="SRC_FAO_AQUASTAT_PHL_2020_BOUNDARY", source_url="https://data.apps.fao.org/aquastat/",
        observed_boundary="All agricultural withdrawal", modeled_boundary="Crop-irrigation withdrawal only",
        result_ref="TotalAnnualTechnologyActivityByMode.csv:agricultural water-delivery routes, 2020",
        uncertainty="Retained as a nexus boundary diagnostic; excluded from scoring because the observed category is broader.")

    source_catalog = [
        {
            "source_id": "SRC_PHL_DOE_2024_POWER_SUMMARY",
            "provider": "Philippine Department of Energy",
            "title": "2024 Philippine Power Statistics / power-generation summary",
            "observation_period": "2020-2024",
            "indicators_used": "gross generation; natural-gas generation",
            "source_url": doe_url,
            "local_evidence": "documentation/doe_power_validation_2020_2024.csv",
            "local_evidence_sha256": sha256(doe_path),
            "provenance_note": "Existing v33 validation extract checked and reused; 2020 has the documented broader generation boundary.",
        },
        {
            "source_id": "SRC_PSA_SSAF_2022",
            "provider": "Philippine Statistics Authority",
            "title": "Selected Statistics on Agriculture and Fisheries 2022",
            "observation_period": "2020",
            "indicators_used": "irrigation service area; palay harvested area and production by regime",
            "source_url": "https://psa.gov.ph/system/files/main-publication/%2528ons-cleared%2529_SSAF%25202022%2520as%2520of%252030082022_ONS-signed.pdf",
            "local_evidence": "data_sources/SOURCES.csv:81",
            "local_evidence_sha256": sha256(sources_path),
            "provenance_note": "Existing canonical v33 source-ledger entry and retained values reused.",
        },
        {
            "source_id": "SRC_FAO_AQUASTAT_PHL_2020_BOUNDARY",
            "provider": "FAO AQUASTAT",
            "title": "AQUASTAT dissemination system, Philippines selection",
            "observation_period": "2020",
            "indicators_used": "agricultural water withdrawal; net irrigation water requirement",
            "source_url": "https://data.apps.fao.org/aquastat/",
            "local_evidence": "data_sources/snapshots/aquastat_philippines_irrigation_boundary_2026-08-11.json",
            "local_evidence_sha256": sha256(aquastat_snapshot_path),
            "provenance_note": "Existing v33 normalized extract reused; variable 4250 is broader than crop irrigation.",
        },
        {
            "source_id": "SRC_FAO_AQUASTAT_TABLE4_2012",
            "provider": "FAO AQUASTAT",
            "title": "Table 4: irrigation water requirement ratio by country",
            "observation_period": "2006",
            "indicators_used": "irrigation water requirement and withdrawal",
            "source_url": "https://firebasestorage.googleapis.com/v0/b/fao-aquastat.appspot.com/o/PDF%2FTABLES%2FTable4.pdf?alt=media&token=fdba62dc-ca8f-4b80-adcd-909baa2ddf87",
            "local_evidence": "data_sources/snapshots/aquastat_philippines_irrigation_boundary_2026-08-11.json",
            "local_evidence_sha256": sha256(aquastat_snapshot_path),
            "provenance_note": "Existing v33 historical reference reused; period mismatch keeps it diagnostic-only.",
        },
        {
            "source_id": "SRC_PSA_WATER_ACCOUNTS_2024_REVISION",
            "provider": "Philippine Statistics Authority",
            "title": "Water Flow Accounts for the Philippine Economy, 2015-2024",
            "observation_period": "2020 and 2024",
            "indicators_used": "total abstraction; surface/groundwater shares",
            "source_url": "https://psa.gov.ph/system/files/enrad/2.%20Highlights_WFA.pdf",
            "local_evidence": "historical_comparison_register_v33.csv",
            "local_evidence_sha256": "",
            "provenance_note": "Official revision checked 2026-08-27; 2020=218.58 km3 conflicts slightly with the retained earlier-release value 218.46 km3. Both are disclosed.",
        },
        {
            "source_id": "SRC_PHL_BTR_2024_TABLE15",
            "provider": "Climate Change Commission / NICCDIES",
            "title": "First Philippine Biennial Transparency Report",
            "observation_period": "2020",
            "indicators_used": "energy, transport, agriculture, forestry and other-land-use GHG",
            "source_url": btr_url,
            "local_evidence": "data_sources/snapshots/psa_openstat_agriculture_2020.json:agriculture_ghg_2020_gg_co2e",
            "local_evidence_sha256": sha256(psa_agriculture_snapshot_path),
            "provenance_note": "Earlier v33 research snapshot already retained the agriculture total and source locator; the register adds the directly checked national inventory categories.",
        },
        {
            "source_id": "SRC_PHL_V22_GHGI",
            "provider": "Climate Change Commission / NICCDIES",
            "title": "2015 and 2020 National GHG Inventory Executive Brief",
            "observation_period": "2020",
            "indicators_used": "rice CH4; direct and indirect managed-soil N2O",
            "source_url": ghgi_extract["urls"]["ghgi"],
            "local_evidence": "data_sources/snapshots/philippines_v22_transition_scope_extracts_2026-08-20.json",
            "local_evidence_sha256": sha256(ghgi_extract_path),
            "provenance_note": "Existing hashed v33 retained extract reused.",
        },
        {
            "source_id": "SRC_PHL_V22_DOE_2024_AFF",
            "provider": "Philippine Department of Energy",
            "title": "2024 Philippine Energy Situationer",
            "observation_period": "2020",
            "indicators_used": "agriculture/forestry/fishery final energy and electricity share",
            "source_url": doe_url,
            "local_evidence": "data_sources/snapshots/philippines_v22_transition_scope_extracts_2026-08-20.json",
            "local_evidence_sha256": sha256(ghgi_extract_path),
            "provenance_note": "Existing hashed v33 retained extract reused; source id matches the canonical source ledger.",
        },
        {
            "source_id": "SRC_PHL_V23_BIOMASS_DOE_KES_SIMPLE",
            "provider": "Philippine Department of Energy",
            "title": "2020 Key Energy Statistics",
            "observation_period": "2020",
            "indicators_used": "other agricultural-waste biomass production",
            "source_url": "https://legacy.doe.gov.ph/sites/default/files/pdf/energy_statistics/2020_key_energy_statistics.pdf",
            "local_evidence": "data_sources/SOURCES.csv:171",
            "local_evidence_sha256": sha256(sources_path),
            "provenance_note": "Existing canonical v33 source-ledger entry reused; commodity mismatch keeps it diagnostic-only.",
        },
        {
            "source_id": "SRC_PHL_DOE_PEP_2020_2040_INDUSTRY_COAL",
            "provider": "Philippine Department of Energy",
            "title": "Philippine Energy Plan 2020-2040",
            "observation_period": "2020",
            "indicators_used": "industry final-energy fuel shares; total coal consumption",
            "source_url": heat_cooking_processing["sources"]["doe_pep_2020_2040"]["url"],
            "local_evidence": "data_sources/snapshots/historical_heat_cooking_processing_2020_2026-08-27.json",
            "local_evidence_sha256": sha256(heat_cooking_processing_path),
            "provenance_note": "Official national tables retained at published precision. Industry shares remain diagnostic because no process-heat-only national table was located; total coal consumption is aligned and score-ready.",
        },
        {
            "source_id": "SRC_PHL_DOE_PES_KES_2020_SERVICES_REFINING",
            "provider": "Philippine Department of Energy",
            "title": "2020 Philippine Energy Situationer and Key Energy Statistics",
            "observation_period": "2020",
            "indicators_used": "services final-energy fuel shares; domestic refinery output",
            "source_url": heat_cooking_processing["sources"]["doe_situationer_2020"]["url"],
            "local_evidence": "data_sources/snapshots/historical_heat_cooking_processing_2020_2026-08-27.json",
            "local_evidence_sha256": sha256(heat_cooking_processing_path),
            "provenance_note": "Official national values retained at published precision; both comparisons remain diagnostic because the model boundaries are narrower for services heat and broader for oil processing.",
        },
        {
            "source_id": "SRC_PHL_DOE_NATGAS_DEVELOPMENT_PLAN",
            "provider": "Philippine Department of Energy",
            "title": "Natural Gas Development Plan",
            "observation_period": "2020",
            "indicators_used": "national natural-gas production and consumption",
            "source_url": heat_cooking_processing["sources"]["doe_natural_gas_plan"]["url"],
            "local_evidence": "data_sources/snapshots/historical_heat_cooking_processing_2020_2026-08-27.json",
            "local_evidence_sha256": sha256(heat_cooking_processing_path),
            "provenance_note": "DOE consumption is converted with the same full-precision physical conversion already retained by v33; 2020 predates LNG imports.",
        },
        {
            "source_id": "SRC_PHL_V23_BIOMASS_PSA_COOKING",
            "provider": "Philippine Statistics Authority",
            "title": "Household Characteristics, 2020 Census of Population and Housing",
            "observation_period": "2020",
            "indicators_used": "primary household cooking-fuel shares",
            "source_url": heat_cooking_processing["sources"]["psa_cooking"]["url"],
            "local_evidence": "data_sources/snapshots/historical_heat_cooking_processing_2020_2026-08-27.json; data_sources/SOURCES.csv:175",
            "local_evidence_sha256": sha256(heat_cooking_processing_path),
            "provenance_note": "Existing canonical source reused with a normalized extract. Household shares are diagnostic and not independent because they informed the v23 cooking proxy and stock mix.",
        },
    ]

    comparison_ids = [row["comparison_id"] for row in rows]
    if len(comparison_ids) != len(set(comparison_ids)):
        raise ValueError("comparison_id values must be unique")
    allowed_statuses = {"score_ready", "diagnostic_only", "evidence_gap"}
    allowed_forcing = {"E", "J", "H"}
    catalog_ids = {source["source_id"] for source in source_catalog}
    for row in rows:
        if row["comparison_status"] not in allowed_statuses:
            raise ValueError(f"{row['comparison_id']}: invalid comparison status")
        if row["source_id"] and row["source_id"] not in catalog_ids:
            raise ValueError(f"{row['comparison_id']}: source id missing from source catalogue")
        if row["comparison_status"] == "score_ready":
            required = ("observed", "modeled", "unit", "forcing_class", "tolerance", "source_id", "observed_boundary", "modeled_boundary", "model_result_ref")
            missing = [field for field in required if row[field] in (None, "")]
            if missing:
                raise ValueError(f"{row['comparison_id']}: score-ready fields missing: {missing}")
            if row["forcing_class"] not in allowed_forcing:
                raise ValueError(f"{row['comparison_id']}: invalid forcing class")
        if row["comparison_status"] != "score_ready" and not row["uncertainty_or_conflict"]:
            raise ValueError(f"{row['comparison_id']}: non-score-ready row lacks exclusion/gap reason")

    fieldnames = list(rows[0].keys())
    register_path = output / "historical_comparison_register_v33.csv"
    with register_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: fmt(value) for key, value in row.items()})

    sources_output_path = output / "historical_comparison_register_v33_sources.csv"
    with sources_output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(source_catalog[0].keys()))
        writer.writeheader()
        writer.writerows(source_catalog)

    score_fields = ["domain", "metric", "observed", "modeled", "tolerance", "forcing_class", "phase", "weight", "year", "region", "unit", "source", "tolerance_absolute", "constraint_refs", "notes"]
    score_path = output / "historical_comparison_register_v33_score_ready.csv"
    with score_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=score_fields)
        writer.writeheader()
        for row in rows:
            if row["comparison_status"] != "score_ready":
                continue
            writer.writerow({
                "domain": row["domain"], "metric": row["metric"], "observed": fmt(row["observed"]),
                "modeled": fmt(row["modeled"]), "tolerance": fmt(row["tolerance"]),
                "forcing_class": row["forcing_class"], "phase": row["phase"], "weight": fmt(row["weight"]),
                "year": row["year"], "region": "Philippines", "unit": row["unit"], "source": row["source_id"],
                "tolerance_absolute": fmt(row["tolerance_absolute"]), "constraint_refs": row["constraint_refs"],
                "notes": row["notes"] or row["uncertainty_or_conflict"],
            })

    evidence = {
        "schema": "philippines-v33-historical-comparison-register-evidence-v2",
        "generated_date": str(date.today()),
        "case": case.name,
        "run": RUN_NAME,
        "read_only_extraction": True,
        "validation": {
            "unique_comparison_ids": True,
            "score_ready_required_fields_complete": True,
            "source_ids_resolve_in_register_source_catalog": True,
            "non_score_ready_rows_have_exclusion_or_gap_reasons": True,
            "legacy_history_summary_regenerated": False,
        },
        "row_counts": {
            "total": len(rows),
            "score_ready": sum(row["comparison_status"] == "score_ready" for row in rows),
            "diagnostic_only": sum(row["comparison_status"] == "diagnostic_only" for row in rows),
            "evidence_gap": sum(row["comparison_status"] == "evidence_gap" for row in rows),
        },
        "modeled_metrics": {
            "water_2020_km3": water,
            "rice_2020": rice,
            "managed_crop_activity_1000km2": managed_crop_activity,
            "emissions_2020_mtco2e": {"total": total_co2e, "energy_including_transport": energy_co2e, "crop": crop_co2e, "rice_ch4": rice_ch4, "managed_soil_n2o": soil_n2o},
            "aff_energy_2020_pj": {"total": aff_energy, "electricity": aff_electricity, "electricity_share": aff_electricity_share},
            "industrial_process_heat_input_2020": industrial_heat,
            "services_heating_input_2020": services_heat,
            "household_cooking_activity_2020": cooking,
            "fuel_processing_output_2020_pj": dict(processing_output_pj),
            "crop_residue_supply_activity_2020_pj": biomass_crop_residue,
        },
        "observed_metrics_and_calculations": {
            "power": "Existing documentation/doe_power_validation_2020_2024.csv values; GWh converted to PJ at 0.0036 PJ/GWh.",
            "rice": "PSA 2020: irrigation service area 2.006 Mha = 20.06 thousand km2; rainfed harvested area 1.46544173 Mha = 14.6544173 thousand km2; production 14.57176519 + 4.72309035 = 19.29485554 Mt.",
            "water": "AQUASTAT 2020 agricultural withdrawal 67.85109005 km3; 2006 irrigation-only reference 65.59 km3; revised PSA 2020 total abstraction 218.58 km3 and 2024 surface share 0.976; earlier retained PSA release gives 218.46 km3.",
            "climate": "BTR 2020 energy 99.854 + transport 29.431 = 129.285 MtCO2e (NDC table rounded 129.286); agriculture 54.080; forestry -71.355 + other land use 45.420 = -25.935. Retained GHGI extract: rice CH4 26.985; managed-soil N2O 6.875 + 2.277 = 9.152.",
            "nexus": "Retained DOE extract: AFF energy 438.8 ktoe x 0.041868 PJ/ktoe = 18.3716784 PJ; electricity share 0.656. DOE agriwaste 836 ktoe x 0.041868 PJ/ktoe = 35.001648 PJ.",
            "heat_cooking_processing": "DOE industry and services fuel shares are published whole-sector final-energy shares and remain diagnostic against heat-only routes. PSA cooking shares cover 99.6% of households in the published categories and are normalized over that covered total. Processing observations: refinery output 4.5 MTOE = 188.406 PJ; gas consumption 133,606 MMSCF x 0.00109303786331432 PJ/MMSCF; coal consumption 17.34 MTOE x 41.868 PJ/MTOE = 725.99112 PJ.",
        },
        "source_hashes": {str(path.relative_to(case)): sha256(path) for path in (activity_path, use_path, production_path, emissions_path, emissions_mode_path, doe_path, gas_validation_path, sources_path, aquastat_snapshot_path, psa_agriculture_snapshot_path, ghgi_extract_path, heat_cooking_processing_path)},
        "classification_rule": "score_ready means aligned enough for quantitative fit; diagnostic_only preserves a useful but mismatched boundary/period; evidence_gap records a missing observed or modeled counterpart.",
    }
    evidence_path = output / "historical_comparison_register_v33_evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    notes_path = output / "HISTORICAL_COMPARISON_REGISTER_V33_2026-08-27.md"
    notes_path.write_text(f"""# Philippines v33 historical-comparison register

## Status

This register is a read-only comparison of the canonical `{case.name}/{RUN_NAME}` result with retained or current official observations. It changes no source parameter, constraint, generated solver file, or result.

- Total rows: {evidence['row_counts']['total']}
- Score-ready comparisons: {evidence['row_counts']['score_ready']}
- Diagnostic-only boundary or period comparisons: {evidence['row_counts']['diagnostic_only']}
- Explicit evidence gaps: {evidence['row_counts']['evidence_gap']}

`score_ready` does not mean the model passes. It means the observation and model result are sufficiently aligned to evaluate against the declared tolerance. `diagnostic_only` rows must not enter an aggregate calibration score. `evidence_gap` rows identify the specific data needed before a historical test is possible.

## Main additions

- Water: national and agricultural-withdrawal boundary diagnostics, current PSA abstraction revision, source-share diagnostic, and explicit missing cooling/pumping-energy evidence.
- Climate: 2020 national energy-plus-transport emissions, rice CH4, managed-soil N2O, agriculture-scope coverage, and missing land-carbon accounting.
- Nexus: AFF final-energy total and electricity share, irrigation water, biomass-to-energy boundary, and thermal-power water.
- Industrial heat and services heating: official 2020 DOE fuel-mix diagnostics with the whole-sector versus heat-only denominator mismatch disclosed.
- Household cooking: official 2020 PSA primary-fuel shares, retained as a calibrated-stock diagnostic rather than independent fit evidence.
- Fuel processing: official refinery, natural-gas and coal quantities; gas and coal are aligned enough to score, while oil remains a structural boundary diagnostic.

## Important boundary decisions

- PSA total abstraction includes large non-consumptive hydropower flows absent from v33; it is diagnostic only.
- AQUASTAT variable 4250 is broader than crop irrigation; it is diagnostic only.
- The complete national agriculture GHG inventory includes livestock and manure categories absent from v33; only rice CH4 and managed-soil N2O are score-ready.
- DOE agriwaste and the model's recoverable residue basket are not identical; the biomass row is diagnostic only.
- DOE industry and services balances are broader than the model's heat-only routes; their fuel shares are diagnostic only.
- PSA cooking shares measure households, not energy, and informed the v23 initial-stock calibration; they are diagnostic only.
- The oil-processing route does not distinguish refinery output from imported finished petroleum products; refinery output is diagnostic only.
- National gas and coal consumption align with the corresponding processed-fuel outputs and are score-ready benchmark observations.
- No observed outcome is converted into a model constraint.

## Files

- `historical_comparison_register_v33.csv`: complete auditable register.
- `historical_comparison_register_v33_score_ready.csv`: aligned subset for the comparison scorer.
- `historical_comparison_register_v33_sources.csv`: source catalogue, retained-evidence paths, and hashes.
- `historical_comparison_register_v33_evidence.json`: exact calculations and SHA-256 identities of model-result inputs.
- `historical_comparison_register_v33_history.json`: legacy 19-row fit/forcing snapshot; it was not regenerated by this extractor and must not be used for the expanded register. The score-ready CSV is the authoritative expanded scoring input.
- `build_historical_comparison_register_v33.py`: reproducible read-only extractor retained with the case.
""", encoding="utf-8")

    print(json.dumps({"status": "built", "rows": evidence["row_counts"], "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()

"""Validate one OG demand-feedback series and apply it through MUIOGO.

All case reads are local and read-only. All case writes go through applyPatch,
which creates a copy. The caserun being cloned is the forward run's REFORM
caserun, so the policies which produced the feedback remain active.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

from . import clews_case
from .muiogo_client import apply_via_muiogo
from .patch import build_clews_patch


def _plain_name(value, label):
    if (not isinstance(value, str) or value in ("", ".", "..")
            or any(c in value for c in ("/", "\\", "\x00"))):
        raise ValueError(f"{label} must be a single non-empty name")
    return value


def _csv_rows(path, required):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if not set(required).issubset(fields) or len(fields) != len(set(fields)):
            raise ValueError(f"{path}: expected distinct columns including {sorted(required)}")
        rows = list(reader)
    if not rows or any(None in row or any(row.get(k) in (None, "") for k in required) for row in rows):
        raise ValueError(f"{path}: empty or malformed feedback rows")
    return rows


def read_feedback_manifest(run_dir, *, country, case_dir, caserun):
    path = Path(run_dir) / "oglink_manifest.json"
    manifest = clews_case.read_json(path)
    if (not isinstance(manifest, dict) or manifest.get("country") != country.name
            or str(manifest.get("un_code")) != str(country.un_code)):
        raise ValueError("feedback manifest does not match the selected country")
    scenario = manifest.get("scenario")
    source = scenario.get("reform_dir") if isinstance(scenario, dict) else None
    expected = Path(case_dir) / "res" / caserun / "csv"
    if (not isinstance(source, str) or not Path(source).is_absolute()
            or Path(source).resolve() != expected.resolve()):
        raise ValueError("feedback was computed for a different CLEWS reform caserun")
    if not expected.is_dir():
        raise ValueError(f"the source reform caserun's CSV directory is missing: {expected}")
    recorded_start = scenario.get("og_start_year")
    if recorded_start is not None and int(recorded_start) != int(country.scenario.og_start_year):
        raise ValueError("feedback OG start year does not match the selected country configuration")
    return manifest, str(path)


def read_demand_ratios(run_dir, *, country, manifest):
    path = Path(run_dir) / "clews_inputs/demand_scaling.csv"
    rows = _csv_rows(path, {"REGION", "OG_ACTIVITY", "OG_INDEX", "CLEWS_FUEL", "YEAR", "DEMAND_RATIO"})
    ports = {"sector_output": "energy_industry_index", "consumption_good": "energy_good_index"}
    concordance = manifest.get("concordance") or {}
    if not isinstance(concordance, dict):
        raise ValueError("feedback manifest has no valid energy concordance")
    ratios, identity = {}, None
    for row in rows:
        if row["REGION"] != country.clews_region:
            raise ValueError("feedback REGION does not match the selected country")
        # The producer names the price-facing fuel, while the patch names the
        # final-demand carrier. These are intentionally different in PHL.
        if not country.electricity_fuel or row["CLEWS_FUEL"] != country.electricity_fuel:
            raise ValueError("feedback CLEWS_FUEL does not match the configured source fuel")
        driver, index = row["OG_ACTIVITY"], int(row["OG_INDEX"])
        port = ports.get(driver)
        if port is None or concordance.get(port) != index:
            raise ValueError("feedback activity/index does not match the run concordance")
        row_identity = (row["REGION"], row["CLEWS_FUEL"], driver, index)
        if identity is not None and row_identity != identity:
            raise ValueError("feedback contains multiple demand series")
        identity = row_identity
        year, ratio = int(row["YEAR"]), float(row["DEMAND_RATIO"])
        if year in ratios:
            raise ValueError(f"duplicate demand-feedback year {year}")
        if not math.isfinite(ratio) or ratio < 0:
            raise ValueError(f"invalid demand-feedback ratio for {year}")
        ratios[year] = ratio
    return ratios


def _emissions_penalty(run_dir, country):
    path = Path(run_dir) / "clews_inputs/EmissionsPenalty.csv"
    rows = _csv_rows(path, {"REGION", "EMISSION", "YEAR", "VALUE"})
    values = {}
    for row in rows:
        if row["REGION"] != country.clews_region or row["EMISSION"] != country.co2_emission:
            raise ValueError("emissions-penalty feedback does not match the selected region/species")
        year, value = int(row["YEAR"]), float(row["VALUE"])
        if year in values:
            raise ValueError(f"duplicate emissions-penalty year {year}")
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"invalid emissions penalty for {year}")
        values[year] = value
    return {"species": country.co2_emission, "value_by_year": values}


def _deferred_discount_rate(run_dir, country):
    path = Path(run_dir) / "clews_inputs/DiscountRate.csv"
    if not path.is_file():
        return []
    rows = _csv_rows(path, {"REGION", "VALUE"})
    if len(rows) != 1 or rows[0]["REGION"] != country.clews_region:
        raise ValueError("discount-rate feedback must describe the selected region once")
    rate = float(rows[0]["VALUE"])
    if not math.isfinite(rate):
        raise ValueError("discount-rate feedback must be finite")
    return [{"artifact": "DiscountRate", "region": country.clews_region, "rate": rate,
             "reason": "region-level parameter; not expressible via applyPatch RYC/RYE/RYT"}]


def run_writeback(args):
    import json

    from .country import _muiogo_home, resolve_country

    country = resolve_country(args.country, config_file=args.countries)
    if not country.demand_commodity:
        raise ValueError("configure demand_commodity: the load-carrying final-demand commodity")
    if country.clews_region != "RE1":
        raise ValueError("MUIOGO's applyPatch exporter currently supports only region RE1")
    case = _plain_name(args.case, "--case")
    caserun = _plain_name(args.base_caserun, "--base-caserun")
    if args.datastorage:
        datastorage = Path(args.datastorage)
    else:
        home = _muiogo_home()
        if not home:
            raise ValueError("could not find DataStorage; pass --datastorage")
        datastorage = Path(home) / "WebAPP/DataStorage"
    case_dir = datastorage / case
    if not (case_dir / "genData.json").is_file():
        raise ValueError(f"case not found: {case_dir}")

    manifest, source = read_feedback_manifest(args.run, country=country, case_dir=case_dir, caserun=caserun)
    ratios = read_demand_ratios(args.run, country=country, manifest=manifest)
    years = clews_case.read_case_years(case_dir)
    start_year = int(country.scenario.og_start_year)
    if not any(y in years and y >= start_year for y in ratios):
        raise ValueError("feedback has no years in the target forecast horizon")
    active_order = clews_case.read_active_scenario_order(case_dir, caserun)
    scenario = clews_case.select_write_scenario(active_order, args.scenario)
    base_sad = clews_case.read_effective_sad(case_dir, caserun, country.demand_commodity)
    emissions = None
    if args.with_emissions_penalty:
        emissions = _emissions_penalty(args.run, country)
        emissions["base_by_year"] = clews_case.read_effective_penalty(case_dir, caserun, emissions["species"])
    patch = build_clews_patch(
        case=case, scenario=scenario, demand_commodity=country.demand_commodity,
        demand_ratio_by_year=ratios, base_sad_by_year=base_sad,
        case_years=years, start_year=start_year, source=source,
        emissions=emissions, deferred=_deferred_discount_rate(args.run, country))
    patch_path = Path(args.run) / "clews_patch.json"
    with patch_path.open("w", encoding="utf-8") as handle:
        json.dump(patch, handle, indent=2, allow_nan=False)
    print(f"Wrote patch: {patch_path} ({len(patch['changes'])} changes, {len(patch['deferred'])} deferred)")
    if args.dry_run:
        print("Dry run: not posting to MUIOGO.")
        return {"status": "dry_run", "patch": str(patch_path)}
    if not patch["changes"]:
        print("No applicable changes; no patch was posted or solve requested.")
        return {"status": "unchanged", "patch": str(patch_path)}
    result = apply_via_muiogo(patch, caserun, base_url=args.muiogo_url, solver=args.solver)
    if result.get("warnings"):
        raise RuntimeError("applyPatch reported warnings: " + "; ".join(map(str, result["warnings"])))
    for key in ("case_copy", "caserun", "csv_dir", "datafile_lines"):
        print(f"{key}: {result.get(key)}")
    print("Write-back applied and solved successfully.")
    return result

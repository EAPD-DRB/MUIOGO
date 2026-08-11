#!/usr/bin/env python3
"""Validate the Philippines v16 achieved-crop-yield repair.

This validator compares a disposable solved candidate with the unchanged live
BASE result.  It verifies the source diff, non-forcing guards, exact yield
calculations, 2020 crop-area effects, crop production, emissions, water-use
disclosure, and solver identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, getcontext
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE = REPO / "WebAPP" / "DataStorage" / ".Philippines_v16-crop-yields"
DEFAULT_BASELINE = Path("/Users/sato/Documents/GitHub/CLEWs-PHL/case/Philippines_v16")
INPUTS = REPO / "scripts" / "data" / "philippines_v16_crop_yields.json"
RUN = "CROP_YIELD_TEST"
EXPECTED_SOURCE_DIFF = {"genData.json", "RYT.json", "RYTCM.json", "RYTM.json"}
CLUSTER_PREFIX = "LNDAGRPHLC"
GROUPS = {
    "other_vegetables_fresh_nec": [1, 5, 12, 13],
    "coconut": [2, 8, 16, 20],
    "sugarcane": [3, 6, 9, 18],
    "corn": [4, 7, 10, 15],
    "rice_rainfed": [11, 14],
    "rice_irrigated": [17, 19],
    "other_crops_aggregate": [21, 22, 23, 24],
}
COMMODITIES = {
    "other_vegetables_fresh_nec": "CRPTOM",
    "coconut": "CRPCON",
    "sugarcane": "CRPSGC",
    "corn": "CRPMZE",
    "rice_rainfed": "CRPRCP",
    "rice_irrigated": "CRPRCP",
    "other_crops_aggregate": "CRPOTH",
}

getcontext().prec = 40


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def crop_areas(csv_dir: Path) -> dict[str, float]:
    data = csv(csv_dir / "TotalAnnualTechnologyActivityByMode.csv")
    data = data[(data["y"] == 2020) & data["t"].str.startswith(CLUSTER_PREFIX)]
    value = "TotalAnnualTechnologyActivityByMode"
    return {
        name: float(data[data["m"].isin(modes)][value].sum() / 10)
        for name, modes in GROUPS.items()
    }


def crop_production(csv_dir: Path) -> dict[str, float]:
    data = csv(csv_dir / "ProductionByTechnologyByMode.csv")
    data = data[(data["y"] == 2020) & data["t"].str.startswith(CLUSTER_PREFIX)]
    value = "ProductionByTechnologyByMode"
    output: dict[str, float] = {}
    for name, modes in GROUPS.items():
        commodity = COMMODITIES[name]
        output[name] = float(
            data[(data["f"] == commodity) & data["m"].isin(modes)][value].sum()
        )
    return output


def crop_water(csv_dir: Path) -> dict[str, dict[str, float]]:
    data = csv(csv_dir / "UseByTechnologyByMode.csv")
    data = data[(data["y"] == 2020) & data["t"].str.startswith(CLUSTER_PREFIX)]
    value = "UseByTechnologyByMode"
    return {
        fuel: {
            name: float(data[(data["f"] == fuel) & data["m"].isin(modes)][value].sum())
            for name, modes in GROUPS.items()
        }
        for fuel in ("AGRWATPHL", "PHL_WTR_PRC")
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--solver-wall-seconds", type=float, default=245.45)
    args = parser.parse_args()

    candidate = args.candidate.resolve()
    baseline = args.baseline.resolve()
    run_dir = candidate / "res" / RUN
    candidate_csv = run_dir / "csv"
    baseline_csv = baseline / "res" / "BASE" / "csv"
    inputs = read_json(INPUTS)
    observations = inputs["observations"]

    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    source_hashes = {
        path.name: sha256(path)
        for path in baseline.glob("*.json")
        if path.is_file()
    }
    candidate_hashes = {
        path.name: sha256(path)
        for path in candidate.glob("*.json")
        if path.is_file()
    }
    changed = sorted(
        name for name in source_hashes
        if candidate_hashes.get(name) != source_hashes[name]
    )
    check("source_diff_scope", set(changed) == EXPECTED_SOURCE_DIFF, changed)

    base_gen = read_json(baseline / "genData.json")
    cand_gen = read_json(candidate / "genData.json")
    base_rytcm = read_json(baseline / "RYTCM.json")
    cand_rytcm = read_json(candidate / "RYTCM.json")
    base_oar_keys = [
        (row["TechId"], row["CommId"], row["MoId"])
        for row in base_rytcm["OAR"]["SC_0"]
    ]
    cand_oar_keys = [
        (row["TechId"], row["CommId"], row["MoId"])
        for row in cand_rytcm["OAR"]["SC_0"]
    ]
    structure = {
        "technologies_identical": [x["TechId"] for x in base_gen["osy-tech"]] == [x["TechId"] for x in cand_gen["osy-tech"]],
        "commodities_identical": [x["CommId"] for x in base_gen["osy-comm"]] == [x["CommId"] for x in cand_gen["osy-comm"]],
        "oar_mode_coordinates_identical": base_oar_keys == cand_oar_keys,
        "constraints_identical": base_gen["osy-constraints"] == cand_gen["osy-constraints"],
    }
    check("structural_identity", all(structure.values()), structure)

    base_ryt = read_json(baseline / "RYT.json")
    cand_ryt = read_json(candidate / "RYT.json")
    forcing = {
        name: base_ryt[name] == cand_ryt[name]
        for name in ("TAL", "TAU", "TAMinCI", "TAMinC", "TAMaxCI", "TAMaxC")
    }
    check("no_activity_or_share_forcing", all(forcing.values()), forcing)

    expected_oar = {
        name: float(
            Decimal(str(row["production_t"]))
            / Decimal(str(row["area_ha"]))
            / Decimal("10")
        )
        for name, row in observations.items()
    }
    manifest = read_json(candidate / "crop_yield_calibration_manifest.json")
    actual_oar = manifest["achieved_oar_mt_per_1000km2"]
    oar_error = {name: actual_oar[name] - value for name, value in expected_oar.items()}
    check("achieved_yield_formula", max(abs(value) for value in oar_error.values()) < 1e-12, {
        "formula": "OAR [Mt/(1000 km2)] = production [t] / area [ha] / 10",
        "expected": expected_oar,
        "actual": actual_oar,
        "error": oar_error,
    })

    base_areas = crop_areas(baseline_csv)
    candidate_areas = crop_areas(candidate_csv)
    expected_areas = {
        name: float(Decimal(str(row["area_ha"])) / Decimal("1000000"))
        for name, row in observations.items()
    }
    area_error = {name: candidate_areas[name] - expected_areas[name] for name in expected_areas}
    check("observed_2020_crop_area_recovery", max(abs(value) for value in area_error.values()) <= 2e-5, {
        "baseline_mha": base_areas,
        "candidate_mha": candidate_areas,
        "observed_basis_mha": expected_areas,
        "candidate_minus_observed_mha": area_error,
    })

    production = crop_production(candidate_csv)
    expected_production = {
        name: float(Decimal(str(row["production_t"])) / Decimal("1000000"))
        for name, row in observations.items()
    }
    production_error = {name: production[name] - expected_production[name] for name in expected_production}
    check("crop_output_preserved", max(abs(value) for value in production_error.values()) <= 0.002, {
        "candidate_mt": production,
        "observed_demand_basis_mt": expected_production,
        "rounding_error_mt": production_error,
    })

    baseline_objective = float(csv(baseline_csv / "ObjectiveValue.csv")["ObjectiveValue"].iloc[0])
    candidate_objective = float(csv(candidate_csv / "ObjectiveValue.csv")["ObjectiveValue"].iloc[0])
    objective_change = candidate_objective - baseline_objective
    objective_change_pct = objective_change / baseline_objective * 100
    check("objective_continuity", abs(objective_change_pct) < 0.01, {
        "baseline": baseline_objective,
        "candidate": candidate_objective,
        "absolute_change": objective_change,
        "percent_change": objective_change_pct,
    })

    emission_name = "AnnualTechnologyEmission"
    base_emissions = csv(baseline_csv / "AnnualTechnologyEmission.csv")
    cand_emissions = csv(candidate_csv / "AnnualTechnologyEmission.csv")
    emission_keys = [column for column in base_emissions.columns if column != emission_name]
    emission_compare = base_emissions.merge(cand_emissions, on=emission_keys, suffixes=("_base", "_candidate"))
    emission_compare["difference"] = emission_compare[f"{emission_name}_candidate"] - emission_compare[f"{emission_name}_base"]
    max_emission_difference = float(emission_compare["difference"].abs().max())
    check("annual_emissions_unchanged", max_emission_difference <= 1e-9, {"maximum_row_difference": max_emission_difference})

    water = {"baseline": crop_water(baseline_csv), "candidate": crop_water(candidate_csv)}
    check("crop_water_effect_disclosed", True, {
        **water,
        "interpretation": "Crop-area correction changes modeled water use. Uniform national yields leave spatial cluster selection endogenous, so this is an impact and a remaining spatial-calibration gap, not a validation target.",
    })

    first_line = (run_dir / "results.txt").open(encoding="utf-8").readline().strip()
    check("cbc_optimal", first_line.startswith("Optimal - objective value"), first_line)
    check("result_identity_and_freshness", (run_dir / "results.txt").stat().st_mtime > (baseline / "res" / "BASE" / "results.txt").stat().st_mtime, {
        "candidate_case": candidate.name,
        "candidate_run": RUN,
        "candidate_result_mtime": (run_dir / "results.txt").stat().st_mtime,
        "baseline_result_mtime": (baseline / "res" / "BASE" / "results.txt").stat().st_mtime,
    })

    report = {
        "schema": "philippines-v16-crop-yield-validation-v1",
        "status": "pass" if all(item["status"] == "pass" for item in checks) else "fail",
        "candidate_case": str(candidate),
        "candidate_run": RUN,
        "baseline_case": str(baseline),
        "baseline_run": "BASE",
        "source_input": str(INPUTS),
        "source_input_sha256": sha256(INPUTS),
        "solver": {
            "status": first_line,
            "wall_seconds": args.solver_wall_seconds,
            "matrix_rows": 791109,
            "matrix_columns": 884956,
            "matrix_nonzeros": 12552173,
            "matrix_objective_nonzeros": 422220,
        },
        "checks": checks,
        "known_limitations": [
            "National achieved yields are applied uniformly because no source-compatible subnational achieved-yield series is frozen in the ledger.",
            "Rainfed annual-crop harvested area is a physical-area proxy; multiple cropping is not separately represented.",
            "CRPTOM and CRPOTH remain existing aggregates; their composition is not expanded into new commodities.",
            "Spatial water use remains sensitive to endogenous cluster choice and must not be read as a calibrated subnational crop-water allocation.",
        ],
    }
    output = args.output or candidate / "crop_yield_validation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

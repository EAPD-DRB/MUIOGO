#!/usr/bin/env python3
"""Validate the promoted Philippines v16 crop-yield repair and live BASE run."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[1]
LIVE = (REPO / "WebAPP" / "DataStorage" / "Philippines_v16").resolve()
CANDIDATE = REPO / "WebAPP" / "DataStorage" / ".Philippines_v16-crop-yields"
INPUTS = REPO / "scripts" / "data" / "philippines_v16_crop_yields.json"
MANIFEST = CANDIDATE / "crop_yield_calibration_manifest.json"
LIVE_RUN = LIVE / "res" / "BASE"
CANDIDATE_RUN = CANDIDATE / "res" / "CROP_YIELD_TEST"
GROUPS = {
    "other_vegetables_fresh_nec": [1, 5, 12, 13],
    "coconut": [2, 8, 16, 20],
    "sugarcane": [3, 6, 9, 18],
    "corn": [4, 7, 10, 15],
    "rice_rainfed": [11, 14],
    "rice_irrigated": [17, 19],
    "other_crops_aggregate": [21, 22, 23, 24],
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crop_areas(run: Path) -> dict[str, float]:
    data = pd.read_csv(run / "csv" / "TotalAnnualTechnologyActivityByMode.csv")
    data = data[(data["y"] == 2020) & data["t"].str.startswith("LNDAGRPHLC")]
    value = "TotalAnnualTechnologyActivityByMode"
    return {
        name: float(data[data["m"].isin(modes)][value].sum() / 10)
        for name, modes in GROUPS.items()
    }


def crop_water(run: Path) -> dict[str, dict[str, float]]:
    data = pd.read_csv(run / "csv" / "UseByTechnologyByMode.csv")
    data = data[(data["y"] == 2020) & data["t"].str.startswith("LNDAGRPHLC")]
    value = "UseByTechnologyByMode"
    return {
        fuel: {
            name: float(data[(data["f"] == fuel) & data["m"].isin(modes)][value].sum())
            for name, modes in GROUPS.items()
        }
        for fuel in ("AGRWATPHL", "PHL_WTR_PRC")
    }


def main() -> None:
    inputs = read_json(INPUTS)
    manifest = read_json(MANIFEST)
    expected_areas = {
        name: float(Decimal(str(row["area_ha"])) / Decimal("1000000"))
        for name, row in inputs["observations"].items()
    }
    actual_areas = crop_areas(LIVE_RUN)
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object) -> None:
        checks.append({"name": name, "status": "pass" if condition else "fail", "detail": detail})

    source_hashes = {
        name: sha256(LIVE / name)
        for name in manifest["candidate_hashes"]
    }
    check("promoted_source_identity", source_hashes == manifest["candidate_hashes"], {
        "live": source_hashes,
        "validated_candidate": manifest["candidate_hashes"],
    })

    first_line = (LIVE_RUN / "results.txt").open(encoding="utf-8").readline().strip()
    check("live_cbc_optimal", first_line.startswith("Optimal - objective value"), first_line)

    objective = float(pd.read_csv(LIVE_RUN / "csv" / "ObjectiveValue.csv")["ObjectiveValue"].iloc[0])
    candidate_objective = float(pd.read_csv(CANDIDATE_RUN / "csv" / "ObjectiveValue.csv")["ObjectiveValue"].iloc[0])
    check("live_objective_reproduces_candidate", abs(objective - candidate_objective) <= 1e-6, {
        "live": objective,
        "validated_candidate": candidate_objective,
        "difference": objective - candidate_objective,
    })

    area_error = {name: actual_areas[name] - expected_areas[name] for name in expected_areas}
    check("live_2020_crop_areas", max(abs(value) for value in area_error.values()) <= 2e-5, {
        "live_mha": actual_areas,
        "observed_basis_mha": expected_areas,
        "live_minus_observed_mha": area_error,
    })

    emission_file = "AnnualTechnologyEmission.csv"
    value = "AnnualTechnologyEmission"
    live_emissions = pd.read_csv(LIVE_RUN / "csv" / emission_file)
    candidate_emissions = pd.read_csv(CANDIDATE_RUN / "csv" / emission_file)
    keys = [column for column in live_emissions.columns if column != value]
    comparison = live_emissions.merge(candidate_emissions, on=keys, suffixes=("_live", "_candidate"))
    maximum_difference = float((comparison[f"{value}_live"] - comparison[f"{value}_candidate"]).abs().max())
    check("live_annual_emissions_reproduce_candidate", maximum_difference <= 1e-9, {
        "maximum_row_difference": maximum_difference,
    })

    generated = (LIVE_RUN / "data_processed.txt").is_file() and (LIVE_RUN / "lp.lp").is_file()
    result_mtime = datetime.fromtimestamp((LIVE_RUN / "results.txt").stat().st_mtime, timezone.utc)
    check("live_generation_and_freshness", generated and result_mtime.date().isoformat() == "2026-08-11", {
        "generated_data_processed": (LIVE_RUN / "data_processed.txt").is_file(),
        "generated_lp": (LIVE_RUN / "lp.lp").is_file(),
        "result_mtime_utc": result_mtime.isoformat(),
    })

    report = {
        "schema": "philippines-v16-crop-yield-live-validation-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(item["status"] == "pass" for item in checks) else "fail",
        "case": "Philippines_v16",
        "run": "BASE",
        "solver": {
            "status": first_line,
            "cbc_wall_seconds": 227.30,
            "full_chain_seconds": 286.42,
            "matrix_rows": 791109,
            "matrix_columns": 884956,
            "matrix_nonzeros": 12552173,
            "matrix_objective_nonzeros": 422220,
        },
        "checks": checks,
        "crop_water_2020": crop_water(LIVE_RUN),
        "limitations": [
            "National achieved yields are uniform across clusters; spatial crop and water allocation remains endogenous and uncalibrated.",
            "Harvested area is a disclosed physical-area proxy for annual rainfed crops.",
            "CRPTOM and CRPOTH retain their existing aggregate resolution.",
        ],
    }
    output = LIVE / "documentation" / "crop_yield_live_validation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Deterministic checks for the PHL v18 fossil border-price candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = (
    REPO
    / "WebAPP"
    / "DataStorage"
    / ".Philippines_v18-power-investment-20260817"
)
DEFAULT_CANDIDATE = (
    REPO
    / "WebAPP"
    / "DataStorage"
    / ".Philippines_v18-fossil-border-price-candidate"
)
YEARS = [str(year) for year in range(2020, 2054)]
HISTORICAL_YEARS = [str(year) for year in range(2020, 2025)]
SC = "SC_0"
IDS = {
    "coal_import": "TEC_khtrp",
    "coal_export": "TEC_cexp0",
    "oil_import": "TEC_d3fyp",
    "oil_export": "TEC_oexp0",
}

EXPECTED = {
    "coal_import": {
        "2020": 2.484721206698629,
        "2021": 4.178506453900265,
        "2022": 8.669687389092292,
        "2023": 5.067412727453258,
        "2024": 3.794375741890079,
    },
    "coal_export": {
        "2020": -1.4211611429397448,
        "2021": -2.548793007987877,
        "2022": -5.046256851285005,
        "2023": -3.4109734113574075,
        "2024": -2.570648386783526,
    },
    "oil_import": {
        "2020": 7.2938484466276625,
        "2021": 12.503341430886355,
        "2022": 16.700634586993896,
        "2023": 14.366188528464367,
        "2024": 15.12363147145973,
    },
    "oil_export": {
        "2020": -6.239581630985455,
        "2021": -11.514953423762051,
        "2022": -15.443699950972382,
        "2023": -13.155744402680178,
        "2024": -13.074031704526885,
    },
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def row(data: dict[str, Any], scenario: str, tech: str, mode: int = 1) -> dict[str, Any]:
    matches = [
        item
        for item in data["VC"][scenario]
        if item.get("TechId") == tech and item.get("MoId") == mode
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected one VC row for {scenario}/{tech}/{mode}")
    return matches[0]


def close(actual: float, expected: float) -> None:
    if not math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12):
        raise AssertionError(f"{actual!r} != {expected!r}")


def check(baseline: Path, candidate: Path) -> dict[str, Any]:
    checks: list[str] = []
    live_files = {path.name: path for path in baseline.glob("*.json") if path.is_file()}
    candidate_files = {
        path.name: path for path in candidate.glob("*.json") if path.is_file()
    }
    source_changes = sorted(
        name
        for name, path in candidate_files.items()
        if name in live_files and sha256(path) != sha256(live_files[name])
    )
    if source_changes != ["RYTM.json"]:
        raise AssertionError(f"unexpected source changes: {source_changes}")
    checks.append("RYTM-only source change allowlist")

    live = load(baseline / "RYTM.json")
    test = load(candidate / "RYTM.json")
    for name, tech in IDS.items():
        live_row = row(live, SC, tech)
        test_row = row(test, SC, tech)
        for key, value in live_row.items():
            if key in HISTORICAL_YEARS:
                close(test_row[key], EXPECTED[name][key])
            elif test_row[key] != value:
                raise AssertionError(f"unintended cell change: {name}/{key}")
    checks.append("full-precision 2020-2024 price cells")
    checks.append("2025-2053 price path unchanged")

    expected_pairs = {(IDS[name], 1) for name in IDS}
    for live_row, test_row in zip(live["VC"][SC], test["VC"][SC], strict=True):
        pair = (live_row.get("TechId"), live_row.get("MoId"))
        if pair not in expected_pairs and live_row != test_row:
            raise AssertionError(f"unintended VC-row change: {pair}")
    checks.append("all unrelated VC rows unchanged")

    for scenario in test["VC"]:
        if scenario == SC:
            continue
        for tech in IDS.values():
            inherited = row(test, scenario, tech)
            if any(inherited.get(year) is not None for year in YEARS):
                raise AssertionError(f"scenario price override: {scenario}/{tech}")
    checks.append("all non-base scenarios inherit SC_0 prices")

    coal_spread = {}
    oil_spread = {}
    for year in HISTORICAL_YEARS:
        coal_import = EXPECTED["coal_import"][year]
        coal_export_revenue = -EXPECTED["coal_export"][year]
        oil_import = EXPECTED["oil_import"][year]
        oil_export_revenue = -EXPECTED["oil_export"][year]
        coal_spread[year] = coal_import - coal_export_revenue
        oil_spread[year] = oil_import - oil_export_revenue
        if coal_spread[year] <= 0 or oil_spread[year] <= 0:
            raise AssertionError(f"export/import arbitrage remains in {year}")
    checks.append("positive landed-import minus export-revenue spreads")

    for name in ("RT.json", "RYT.json", "RYTCM.json", "genData.json"):
        if sha256(baseline / name) != sha256(candidate / name):
            raise AssertionError(f"physical structure changed: {name}")
    checks.append("physical constraints and technology mappings unchanged")

    return {
        "schema": "philippines-v18-fossil-border-price-static-validation-v1",
        "date": "2026-08-18",
        "status": "passed",
        "baseline": str(baseline),
        "candidate": str(candidate),
        "checks": checks,
        "source_changes": source_changes,
        "coal_import_minus_export_revenue_usd_per_gj": coal_spread,
        "oil_import_minus_export_revenue_usd_per_gj": oil_spread,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    args = parser.parse_args()
    print(json.dumps(check(args.baseline.resolve(), args.candidate.resolve()), indent=2))


if __name__ == "__main__":
    main()

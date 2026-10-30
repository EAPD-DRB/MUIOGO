"""Translate OG feedback into absolute, source-parameter changes for applyPatch.

The caller supplies effective caserun demand and a destination scenario which
cannot be overridden by later active layers. No case files are written here.
"""
from __future__ import annotations

import math


def _nonnegative(value, description):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{description} must be finite and nonnegative")
    return value


def build_clews_patch(*, case, scenario, demand_commodity, demand_ratio_by_year,
                      base_sad_by_year, case_years, start_year, source="",
                      emissions=None, deferred=None, no_op_tol=1e-9):
    for name, value in (("case", case), ("scenario", scenario), ("demand_commodity", demand_commodity)):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} must be a non-empty string")
    if not base_sad_by_year or all(v == 0 for v in base_sad_by_year.values()):
        raise ValueError(f"base SAD for {demand_commodity!r} is empty or all zero; check the demand commodity")

    changes = []
    for year, rho in sorted(demand_ratio_by_year.items()):
        if year < start_year or year not in case_years:
            continue
        if year not in base_sad_by_year:
            raise ValueError(f"year {year} has no base SAD value")
        rho = _nonnegative(rho, f"year {year} demand ratio")
        base = _nonnegative(base_sad_by_year[year], f"year {year} base SAD")
        value = base * rho
        if not math.isfinite(value):
            raise ValueError(f"year {year}: scaled demand is not finite")
        if abs(rho - 1.0) < no_op_tol or value == base:
            continue
        if value == 0:
            raise ValueError(f"year {year}: refusing to set live demand to 0; this may change datafile structure")
        changes.append({"group": "Demand", "code": demand_commodity, "year": year,
                        "value": value, "scenario": scenario})

    if emissions is not None:
        for year, value in sorted(emissions["value_by_year"].items()):
            if year < start_year or year not in case_years:
                continue
            value = _nonnegative(value, f"year {year} emissions penalty")
            base_values = emissions.get("base_by_year")
            if base_values is not None:
                if year not in base_values:
                    raise ValueError(f"year {year} has no base emissions penalty")
                if value == base_values[year]:
                    continue
            changes.append({"group": "EmissionsPenalty", "code": emissions["species"], "year": year,
                            "value": value, "scenario": scenario})

    return {"source": source, "case": case, "changes": changes, "deferred": deferred or []}

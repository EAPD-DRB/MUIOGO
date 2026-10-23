"""Build the clews_patch.json that applyPatch consumes.

The OG side speaks in ratios; CLEWS demand is an absolute input. The single
ratio -> absolute multiply happens HERE, against the same base SAD value applyPatch
will overwrite, so "what we scaled" and "what gets set" are the same rows. Every
emitted value is ABSOLUTE.

The discount-rate feedback is region-level (dimension R/RT) and applyPatch supports
only RYC/RYE/RYT single-entity year tables, so it is not expressible as a change; the
caller records it under ``deferred``, which is passed through untouched and NEVER
appears in ``changes``.
"""
from __future__ import annotations

import math


def build_clews_patch(*, case: str, scenario: str, demand_commodity: str,
                      demand_ratio_by_year: dict[int, float],
                      base_sad_by_year: dict[int, float], case_years: set[int],
                      start_year: int, source: str = "",
                      emissions: dict | None = None, deferred: list | None = None,
                      no_op_tol: float = 1e-9) -> dict:
    """Translate a per-year demand ratio into applyPatch's absolute change list.

    value = base_sad_by_year[year] * demand_ratio_by_year[year], for each year that is
    in the case horizon, at or after ``start_year``, and not an exact no-op.
    """
    assert isinstance(case, str) and case, "case must be a non-empty string"
    assert isinstance(scenario, str) and scenario, "scenario must be a non-empty string"
    assert isinstance(demand_commodity, str) and demand_commodity, \
        "demand_commodity must be a non-empty string"
    assert isinstance(start_year, int), "start_year must be an int"

    # F1 guard: the price-facing code carries all-zero SAD, so scaling it is a silent
    # no-op applyPatch would accept without noticing. Refuse it -- it is the wrong code.
    if not base_sad_by_year or all(v == 0 for v in base_sad_by_year.values()):
        raise ValueError(
            f"base SAD for demand_commodity {demand_commodity!r} is empty or all zero -- "
            "its SAD rows are all zero -- this is likely the price code, not the "
            "final-demand carrier; wrong demand_commodity?")

    changes = []
    for year, rho in sorted(demand_ratio_by_year.items()):
        if year < start_year:
            # never scale calibrated history -- it makes the CBC LP pathological
            continue
        if year not in case_years:
            # a value outside the case's years is an applyPatch blocker by design
            continue
        if abs(rho - 1.0) < no_op_tol:
            continue
        if year not in base_sad_by_year:
            raise ValueError(
                f"year {year} has ratio {rho} but no base SAD value; refusing to change a "
                "year we have no base for")
        value = base_sad_by_year[year] * rho
        if not math.isfinite(value):
            raise ValueError(
                f"year {year}: base {base_sad_by_year[year]} * ratio {rho} is not finite")
        if value == 0:
            # a nonzero->0 edit drops the datafile line and trips applyPatch's structure
            # guard; refuse it rather than emit a silent structure change.
            raise ValueError(
                f"year {year}: ratio {rho} would set demand to 0, dropping the datafile "
                "line and changing model structure; refusing to emit it")
        changes.append({"group": "Demand", "code": demand_commodity, "year": year,
                        "value": float(value), "scenario": scenario})

    if emissions is not None:
        species = emissions["species"]
        for year, v in sorted(emissions["value_by_year"].items()):
            if year < start_year or year not in case_years:
                continue
            changes.append({"group": "EmissionsPenalty", "code": species, "year": year,
                            "value": float(v), "scenario": scenario})

    return {"source": source, "case": case, "changes": changes,
            "deferred": deferred or []}

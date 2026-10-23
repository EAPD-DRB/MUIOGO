"""Serialize the OG->CLEWS artifacts a run produces (demand scaling, EmissionsPenalty,
DiscountRate) to CSV files that a CLEWS re-run consumes. This is the producer side of the
loop-closure seam: writing these is implemented; invoking OSeMOSYS on them is the external
step (MUIOGO / the solver).
"""
from __future__ import annotations

import csv
import os


def _years(start_year, n):
    return list(range(start_year, start_year + n))


def write_demand(spec: dict, out_dir: str, region=None) -> str:
    """Demand-scaling artifact: per-year multiplier on the base CLEWS SpecifiedAnnualDemand.
    (A full writer would multiply the country's base demand file by this; the multiplier +
    its concordance target are written so the CLEWS side can apply it deterministically.)
    ``region`` defaults to the spec's own (the country's clews_region, put there by
    emit_energy_demand) so the artifact addresses the case's real OSeMOSYS region."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "demand_scaling.csv")
    ratio = spec["ratio_by_period"]
    years = _years(spec["start_year"], len(ratio))
    region = region or spec.get("region", "RE1")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["REGION", "OG_ACTIVITY", "OG_INDEX", "CLEWS_FUEL", "YEAR", "DEMAND_RATIO"])
        for y, x in zip(years, ratio):
            w.writerow([region, spec["og_activity"], spec["og_index"], spec.get("clews_fuel", ""), y, f"{x:.6f}"])
    return path


def write_emissions_penalty(spec: dict, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "EmissionsPenalty.csv")
    vals = spec["value_by_period"]
    years = _years(spec["start_year"], len(vals))
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["REGION", "EMISSION", "YEAR", "VALUE"])
        for y, v in zip(years, vals):
            w.writerow([spec["region"], spec["emission"], y, f"{v:.6f}"])
    return path


def write_discount_rate(spec: dict, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "DiscountRate.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["REGION", "VALUE", "NOTE"])
        rate = spec["rate"]
        if isinstance(rate, list):
            w.writerow([spec["region"], rate[0], spec["convention"] + " (period-0; path available)"])
        else:
            w.writerow([spec["region"], f"{rate:.6f}", spec["convention"]])
    return path


_WRITERS = {"Demand": write_demand, "EmissionsPenalty": write_emissions_penalty,
            "DiscountRate": write_discount_rate}


def write_all(ctx, out_dir: str) -> dict:
    """Serialize every OG->CLEWS artifact accumulated on the context."""
    written = {}
    for key, spec in ctx.clews_inputs.items():
        writer = _WRITERS.get(key)
        if writer:
            written[key] = writer(spec, out_dir)
    return written

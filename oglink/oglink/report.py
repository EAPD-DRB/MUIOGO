"""Reporting: turn a finished ExperimentContext into macro, demand, and incidence
read-outs. Import-light (numpy only) so it is testable on array fixtures without ogcore.
"""
from __future__ import annotations

import numpy as np

from . import og_wedge


def macro_pct_diff(base_tpi, reform_tpi, var_list=("Y", "C", "K", "L", "r", "w"), n=10):
    """% change reform vs base for aggregate paths, first n periods (r/w shown as level diff)."""
    out = {}
    for v in var_list:
        if v not in base_tpi:
            continue
        b, r = np.asarray(base_tpi[v]), np.asarray(reform_tpi[v])
        T = min(len(b), len(r), n)
        if v in ("r", "w", "r_p", "r_gov"):
            out[v] = (r[:T] - b[:T])  # level difference for rates
        else:
            out[v] = 100.0 * (r[:T] - b[:T]) / np.where(b[:T] == 0, np.nan, b[:T])
    return out


def macro_table(base_tpi, reform_tpi, start_year, var_list=("Y", "C", "K", "L", "r", "w"), num_years=10):
    """A headline macro table mirroring ``ogcore.output_tables.macro_table`` (the standard OG run report):
    % difference reform vs baseline, ((reform-base)/base)*100, by year for the first ``num_years``, plus a
    window-overall column and the steady state. Returns a pandas DataFrame indexed by Year (rows = years,
    then the window, then SS; columns = the macro variables). r/w are %-of-rate differences, as in OG-Core.
    Built link-side from the exported TPI paths -- no ogcore needed."""
    import pandas as pd

    years = list(range(int(start_year), int(start_year) + num_years))
    index = [str(y) for y in years] + [f"{years[0]}-{years[-1]}", "SS"]
    cols = {}
    for v in var_list:
        if v not in base_tpi or v not in reform_tpi:
            continue
        b = np.asarray(base_tpi[v], dtype=float).ravel()
        r = np.asarray(reform_tpi[v], dtype=float).ravel()
        n = min(num_years, b.size, r.size)
        with np.errstate(divide="ignore", invalid="ignore"):
            pct = (r - b) / np.where(b == 0, np.nan, b) * 100.0
        bw = b[:n].sum()
        overall = float((r[:n].sum() - bw) / bw * 100.0) if bw else float("nan")
        cols[v] = [float(pct[i]) if i < n else float("nan") for i in range(num_years)] + [overall, float(pct[-1])]
    df = pd.DataFrame(cols, index=index).round(3)
    df.index.name = "Year"
    return df


def demand_response(base_tpi, reform_tpi, i_energy):
    """% change in aggregate energy-good consumption, by period."""
    return og_wedge.energy_demand_response(base_tpi["C_i"], reform_tpi["C_i"], i_energy)


def incidence(base_tpi, reform_tpi, i_energy, n=10):
    """Energy-consumption and composite-consumption % change by lifetime-income group J.

    NB: ``consumption_by_J`` is the % change in average composite CONSUMPTION (the TPI ``c`` array,
    averaged over the first ``n`` periods and all ages) -- NOT a lifetime-utility / equivalent-
    variation welfare measure. The thinnest top-income group is the most GE-sensitive, so read its
    swings as consumption incidence, not utility."""
    eJ = og_wedge.energy_demand_response_by_group(base_tpi["c_i"], reform_tpi["c_i"], i_energy, n)
    cb, cr = np.asarray(base_tpi["c"]), np.asarray(reform_tpi["c"])  # (T, S, J)
    cJ = 100.0 * (cr[:n].mean(axis=(0, 1)) - cb[:n].mean(axis=(0, 1))) / cb[:n].mean(axis=(0, 1))
    return {"energy_by_J": np.round(eJ, 2), "consumption_by_J": np.round(cJ, 2)}


def fiscal_check(base_tpi, reform_tpi, n=10):
    """Consumption-tax revenue change (revenue accruing to government as G/debt absent recycling) + resource-constraint error."""
    out = {}
    if "cons_tax_revenue" in base_tpi:
        b, r = np.asarray(base_tpi["cons_tax_revenue"]), np.asarray(reform_tpi["cons_tax_revenue"])
        out["cons_tax_revenue_pct"] = float(100 * np.nanmean((r[:n] - b[:n]) / b[:n]))
    for tag, tpi in (("base", base_tpi), ("reform", reform_tpi)):
        if "resource_constraint_error" in tpi:
            out[f"rc_error_{tag}"] = float(np.max(np.abs(tpi["resource_constraint_error"])))
    return out


def layered_entry(label, base_tpi, reform_tpi, *, energy_good_index=None, channels=None):
    """Build one entry of the ``layered_results`` list the viz deck consumes, from a solved
    ``(base_tpi, reform_tpi)`` pair. Model-agnostic: every number comes from the report.* path
    math on the TPI dicts, so it works for any country/model. The energy-good rows are added
    only when an energy good is isolated (``energy_good_index`` is not None); ``channels`` is the
    list of applied channel ids. Used by the across-steps driver AND the coupled-run viz bridge."""
    macro = macro_pct_diff(base_tpi, reform_tpi)
    fc = fiscal_check(base_tpi, reform_tpi)
    row = {
        "step": label,
        "macro": {k: round(float(np.nanmean(v)), 3) for k, v in macro.items()},
        "fiscal": {k: round(float(v), 4) for k, v in fc.items()},
        "channels": list(channels or []),
    }
    if energy_good_index is not None:
        inc = incidence(base_tpi, reform_tpi, energy_good_index)
        dC = demand_response(base_tpi, reform_tpi, energy_good_index)
        row["energy_demand_pct"] = round(float(np.nanmean(dC[:10])), 2)
        row["consumption_by_J"] = [round(float(x), 2) for x in inc["consumption_by_J"]]
        row["energy_by_J"] = [round(float(x), 2) for x in inc["energy_by_J"]]
    return row


def print_report(ctx):
    """Human-readable summary of a finished run."""
    con = ctx.concordance
    i_e = con.energy_good_index if con is not None else None
    b, r = ctx.base_tpi, ctx.reform_tpi
    n_channels = sum(1 for pr in ctx.provenance if not pr.get("provenance_only"))
    print("\n" + "=" * 70)
    print(f"REPORT: {ctx.country.name}  ({n_channels} channel(s) applied)")
    print("=" * 70)
    print("\nChannels + provenance:")
    for rec in ctx.provenance:
        print(f"  - {rec}")
    if b is None or r is None:
        print("\n(no solve results in context)")
        return
    print("\nMacro aggregates -- % difference, reform vs baseline (OG-Core macro_table style):")
    start_year = int(getattr(getattr(ctx.country, "scenario", None), "og_start_year", 2026))
    try:
        import pandas as pd
        with pd.option_context("display.width", 140, "display.max_columns", 20,
                               "display.float_format", lambda x: f"{x:7.3f}"):
            print(macro_table(b, r, start_year).to_string())
    except Exception as e:  # noqa: BLE001 -- fall back to the one-line summary if pandas/format hiccups
        print(f"  (macro table unavailable: {type(e).__name__}); first-10-yr means:")
        for k, v in macro_pct_diff(b, r).items():
            unit = "pp" if k in ("r", "w", "r_p", "r_gov") else "%"
            print(f"  {k:4} {np.round(v.mean(), 3)} {unit}")
    if i_e is not None:
        print(f"\nEnergy-good demand response: {np.nanmean(demand_response(b, r, i_e)[:10]):.2f}%")
        inc = incidence(b, r, i_e)
        print("Incidence by income group J (j0 low .. high):")
        print("  energy %chg     :", inc["energy_by_J"])
        print("  consumption %chg:", inc["consumption_by_J"])
    else:
        print("\n(energy good not isolated for this country -- energy demand/incidence omitted; the "
              "energy channels skipped)")
    fc = fiscal_check(b, r)
    if fc:
        print("\nFiscal/solve checks:", {k: round(v, 4) for k, v in fc.items()})
    if ctx.clews_inputs:
        print("\nCLEWS inputs produced (for the loop-closure / re-run):", list(ctx.clews_inputs))

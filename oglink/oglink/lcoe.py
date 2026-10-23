"""Levelized Cost of Electricity (LCOE) price signal from a MUIOGO/OSeMOSYS CLEWS export.

Reconstructs a smooth, dense electricity-price index from the raw per-technology cost and
activity CSVs when no curated 'Cost of electricity' workbook ships (the pure-MUIOGO/v9 case).
Only the reform/base RATIO of this LCOE is meaningful and enters OG-Core; the absolute level is
an index in the model's native money units, not a $/MWh price.

Numerator (per year) = generation techs' own annualized cost (Inv + FixedO&M + VarO&M)
                       + the upstream fuel-supply chain cost, allocated to electricity by the
                         share of each supply tech's output that FLOWS to generation.
Denominator (per year) = busbar electricity generation (ProductionByTechnologyByMode where the
                         output commodity is the busbar electricity code, pre-T&D).

Validated against PHL v9 (Base_v9 vs PEP_v9): reform/base ratio mean 1.0539, min 1.0000 (2022),
max 1.1625 (2030). Prototype/internally-validated: the ratio is robust across defensible internal
choices (generalized flow-allocation vs whole-chain-by-finished-fuel-share vs a namespace filter
all agree to ~1e-4), but with no same-vintage workbook the absolute magnitude is prototype-grade.

Design (hardened for CLEWS-generality; no country literal in the default path):
  * Fuel allocation is a generalized downstream-FLOW share (power_share fixed point), which
    subsumes the exact single-path allocation (identical when every intermediate is single-
    producer/single-consumer, as in PHL v9) and stays correct if a chain branches.
  * Net-negative-cost guard: a tech whose total cost < cost_floor is a sequestration/land credit
    (e.g. PHL_LND_FOR = -85,076), never a fuel-supply cost, so it is excluded. This neutralizes
    the cooling-water -> land-subsystem trap portably, WITHOUT any namespace string.
  * CHP / co-generation guard: a gen tech's own+fuel cost is split by electricity's share of its
    USEFUL output; a dumped byproduct (zero consumers, e.g. GEO's PHL_POW_HEAT) does not dilute
    (elec_frac == 1). Activates only if a case co-produces a USED non-electricity output.
  * Per-run discovery: generation techs and fuels are discovered independently for each scenario
    dir, so the reform's new topology (PEP adds nuclear PHL_POW_PP_NUSMR + uranium PHL_PRO_UR ->
    PHL_PRO_IMP_UR) is captured, never inherited from the baseline.
  * Optional supply_predicate tightens the allocation base and asserts completeness (no MATERIAL
    fuel producer silently dropped) for callers who want a namespace guard on top of the flow logic.

Reads (raw long CSVs, NOT signals.read_clews_matrix which loses the fuel dim):
  ProductionByTechnologyByMode.csv, UseByTechnologyByMode.csv (cols r_x,f,t,y,m,...,value),
  AnnualizedInvestmentCost.csv, AnnualFixedOperatingCost.csv, AnnualVariableOperatingCost.csv
  (cols r,t,y,value).
"""
from __future__ import annotations

import glob
import os
import re

import pandas as pd

# Stem == value-column name for each CLEWS CSV the reconstruction reads.
COST_STEMS = ("AnnualizedInvestmentCost", "AnnualFixedOperatingCost", "AnnualVariableOperatingCost")
PROD_STEM = "ProductionByTechnologyByMode"
USE_STEM = "UseByTechnologyByMode"
INPUT_STEMS = (PROD_STEM, USE_STEM) + COST_STEMS


def _find(csv_dir: str, stem: str) -> str | None:
    """Path to the CLEWS CSV for ``stem``, tolerating region/year decoration (``RE1_<stem>_2050.csv``)
    the way the rest of the link's readers glob -- but WITHOUT matching a longer sibling that merely
    contains the stem (e.g. ``RateOfProductionByTechnologyByMode`` for ``ProductionByTechnologyByMode``,
    or ``RateOfUseByTechnologyByMode`` for ``UseByTechnologyByMode`` -- which would silently read the
    rate variable instead of the level). Returns None if absent. The anchored pattern allows only a
    leading ``<REGION>_`` and a trailing ``_<year>`` around the exact stem."""
    pat = re.compile(rf"^(?:[A-Za-z0-9]+_)?{re.escape(stem)}(?:_\d{{4}})?\.csv$")
    hits = sorted(h for h in glob.glob(os.path.join(csv_dir, f"*{stem}*.csv"))
                  if pat.match(os.path.basename(h)))
    return hits[0] if hits else None


def _require(csv_dir: str, stem: str) -> str:
    path = _find(csv_dir, stem)
    if path is None:
        raise FileNotFoundError(f"lcoe: no '{stem}(.csv)' in {csv_dir}")
    return path


def _load_costs(csv_dir: str) -> pd.DataFrame:
    """tech x year cost = Inv + FixedO&M + VarO&M (all annual $-flows on the same basis)."""
    frames = []
    for stem in COST_STEMS:
        df = pd.read_csv(_require(csv_dir, stem))[["t", "y", stem]].rename(columns={stem: "cost"})
        frames.append(df)
    return pd.concat(frames, ignore_index=True).groupby(["t", "y"], as_index=False)["cost"].sum()


def _read_long(csv_dir: str, stem: str) -> pd.DataFrame:
    return pd.read_csv(_require(csv_dir, stem)).rename(columns={stem: "v"})


def has_inputs(csv_dir: str) -> bool:
    """Whether this scenario dir ships all CSVs the LCOE reconstruction reads (glob-resolved, so it
    agrees with the sibling readers and the preflight checklist rather than demanding exact names)."""
    return all(_find(csv_dir, s) is not None for s in INPUT_STEMS)


def has_busbar_producers(csv_dir: str, busbar: str) -> bool:
    """Whether ``busbar`` actually appears as a produced commodity in this scenario's production export
    -- a cheap pre-solve check that the configured busbar code identifies a real generation fleet (a
    present-but-wrong code otherwise fails only after the multi-minute baseline solve)."""
    path = _find(csv_dir, PROD_STEM)
    if path is None:
        return False
    try:
        return busbar in set(pd.read_csv(path, usecols=["f"])["f"].unique())
    except (ValueError, KeyError):
        return False


def lcoe_by_year(csv_dir: str, busbar: str, *, supply_predicate=None,
                 cost_floor: float = 0.0, n_iter: int = 64, tol: float = 1e-12) -> dict:
    """LCOE index by int year for one scenario dir. ``busbar`` = the busbar electricity commodity
    (generation output, pre-T&D; e.g. 'PHL_POW_ELE'). ``supply_predicate(tech)->bool`` optionally
    restricts which non-generation techs may carry allocated fuel cost (default: any positive-cost
    tech whose output flows to generation). ``cost_floor``: techs with total cost below this are
    dropped as credits (default 0.0 -> drop net-negative)."""
    prod = _read_long(csv_dir, PROD_STEM)
    use = _read_long(csv_dir, USE_STEM)
    costs = _load_costs(csv_dir)
    cost_ty = {(t, y): c for t, y, c in costs.itertuples(index=False)}
    cost_total = costs.groupby("t")["cost"].sum().to_dict()

    # (A) generation = producers of the busbar commodity (discovered per run)
    gen = set(prod.loc[prod.f == busbar, "t"].unique())
    if not gen:
        raise ValueError(f"lcoe_by_year: no producers of busbar {busbar!r} in {csv_dir}")

    # (B) CHP / co-gen: electricity's share of each gen tech's USEFUL output (dumped byproduct -> 1)
    consumed = use.groupby("f")["v"].sum()
    used_commodities = set(consumed[consumed > 0].index)
    gen_prod = prod[prod.t.isin(gen)].groupby(["t", "f"])["v"].sum()
    elec_frac = {}
    for t in gen:
        outs = gen_prod.xs(t, level="t") if t in gen_prod.index.get_level_values("t") else pd.Series(dtype=float)
        useful = {g: v for g, v in outs.items() if g == busbar or g in used_commodities}
        tot = sum(useful.values())
        elec_frac[t] = (useful.get(busbar, 0.0) / tot) if tot > 0 else 1.0

    # (C) topology, per year, for the power_share downstream-flow fixed point
    total_use = use.groupby(["f", "y"])["v"].sum()
    ug = use[use.t.isin(gen)].copy()
    ug["w"] = ug["v"] * ug["t"].map(elec_frac)          # electricity-weighted gen use
    gen_use = ug.groupby(["f", "y"])["w"].sum()
    nongen_use = use[~use.t.isin(gen)]
    ng_rows = nongen_use.groupby(["t", "f", "y"])["v"].sum().reset_index()
    prod_ty = prod.groupby(["t", "y", "f"])["v"].sum()
    prod_ty_tot = prod.groupby(["t", "y"])["v"].sum().to_dict()
    all_commodities = set(prod.f) | set(use.f)
    gen_out = prod[prod.f == busbar].groupby("y")["v"].sum()

    # completeness assertion for an explicit supply_predicate: every DIRECT producer of a
    # generation-consumed commodity that carries MATERIAL cost must satisfy the predicate, else the
    # predicate would silently drop real fuel supply. A negligible carrier (cooling water's supplier,
    # ~0.09 vs fuel ~3e5) is what the predicate is MEANT to drop, so it must not trip the guard.
    if supply_predicate is not None:
        supply_scale = sum(c for t, c in cost_total.items() if t not in gen and c > 0)
        mat_eps = max(cost_floor, 1e-4 * supply_scale)
        for f in set(use.loc[use.t.isin(gen), "f"].unique()):
            for p in prod.loc[prod.f == f, "t"].unique():
                if p in gen or cost_total.get(p, 0.0) <= mat_eps:
                    continue
                if not supply_predicate(p):
                    raise AssertionError(
                        f"lcoe_by_year: supply_predicate excludes MATERIAL fuel producer {p!r} of "
                        f"{f!r} (cost {cost_total.get(p, 0.0):.1f}) -- it would drop real fuel cost.")

    def _allowed(t):
        return (t not in gen) and (cost_total.get(t, 0.0) >= cost_floor) and \
               (supply_predicate is None or supply_predicate(t))

    years = sorted({y for (_, y) in cost_ty})
    lcoe = {}
    for y in years:
        tu = {f: v for (f, yy), v in total_use.items() if yy == y}
        gu = {f: v for (f, yy), v in gen_use.items() if yy == y}
        ng_y = ng_rows[ng_rows.y == y]
        ng_by_t = {t: grp[["f", "v"]].values.tolist() for t, grp in ng_y.groupby("t")}
        outs_y, tot_out_y = {}, {}
        for (t, yy, f), v in prod_ty.items():
            if yy == y:
                outs_y.setdefault(t, {})[f] = v
        for (t, yy), v in prod_ty_tot.items():
            if yy == y:
                tot_out_y[t] = v

        def out_frac(t, ps):
            to = tot_out_y.get(t, 0.0)                       # noqa: B023 -- consumed within this y-iteration only
            if to <= 0:
                return 0.0
            return sum((pv / to) * ps.get(g, 0.0) for g, pv in outs_y.get(t, {}).items())  # noqa: B023

        # power_share fixed point: fraction of each commodity's use that flows to generation.
        # Downstream (finished fuel) -> upstream; a DAG converges in a few passes.
        ps = {f: 0.0 for f in all_commodities}
        for _ in range(n_iter):
            toward = {f: gu.get(f, 0.0) for f in all_commodities}
            for t, rows in ng_by_t.items():
                of = out_frac(t, ps)
                if of == 0.0:
                    continue
                for f, uv in rows:
                    toward[f] = toward.get(f, 0.0) + uv * of
            maxd = 0.0
            new = {}
            for f in all_commodities:
                d = tu.get(f, 0.0)
                val = min(toward.get(f, 0.0) / d, 1.0) if d > 0 else 0.0
                maxd = max(maxd, abs(val - ps[f]))
                new[f] = val
            ps = new
            if maxd < tol:
                break

        own = sum(cost_ty.get((t, y), 0.0) * elec_frac[t] for t in gen)         # (1) power own cost
        alloc = 0.0                                                             # (2) allocated fuel chain
        for t in set(ng_by_t) | set(outs_y):
            if not _allowed(t):
                continue
            c = cost_ty.get((t, y), 0.0)
            if c:
                alloc += c * out_frac(t, ps)
        g = float(gen_out.get(y, 0.0))                                          # (3) busbar generation
        if g > 0:
            lcoe[int(y)] = (own + alloc) / g
    return dict(sorted(lcoe.items()))


def lcoe_ratio(base_dir: str, reform_dir: str, busbar: str, **kw) -> pd.Series:
    """Reform/base LCOE ratio by int year over the years both scenarios share (0 base -> dropped).
    This is the object that enters OG (via signals.energy_price_ratio, kind='lcoe'); the absolute
    level is NOT exposed as a price. base_dir and reform_dir are discovered independently -> the
    reform's new nuclear/uranium chain is captured, never inherited from the baseline."""
    b = pd.Series(lcoe_by_year(base_dir, busbar, **kw))
    r = pd.Series(lcoe_by_year(reform_dir, busbar, **kw))
    years = sorted(set(b.index) & set(r.index))
    denom = b.loc[years].replace(0.0, pd.NA)
    return (r.loc[years] / denom).dropna().sort_index()


if __name__ == "__main__":
    import sys
    # usage: python -m oglink.lcoe <base_csv_dir> <reform_csv_dir> <busbar_commodity>
    base_dir, reform_dir, busbar = sys.argv[1], sys.argv[2], sys.argv[3]
    ratio = lcoe_ratio(base_dir, reform_dir, busbar)
    print(f"mean={ratio.mean():.4f} min={ratio.min():.4f}({int(ratio.idxmin())}) "
          f"max={ratio.max():.4f}({int(ratio.idxmax())})")
    print(" ".join(f"{y}:{ratio[y]:.3f}" for y in ratio.index))

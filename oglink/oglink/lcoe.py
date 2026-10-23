"""Levelized Cost of Electricity (LCOE) price signal from a MUIOGO/OSeMOSYS CLEWS export.

A smooth, dense electricity-price index for when no curated 'Cost of electricity' workbook ships.
Only the reform/base RATIO enters OG-Core; the level is an index in the model's money units.

Per year:
    LCOE = (generation techs' own annualized cost (Inv + FixedO&M + VarO&M)
            + every input they use, valued at the model's own price for that commodity)
           / busbar electricity generation (pre-T&D).

The input prices are MUIOGO's yearly commodity prices (CommodityMarginalPrice.csv, the marginal
cost of each commodity from the solve's balance-row shadow prices). Valuing inputs at the model's
prices instead of tracing supplier costs back through the system keeps the method general:
  * any input counts at its real cost, whatever unit a country uses for it -- coal or gas in PJ,
    biomass in tonnes, cooling water that is costly to supply;
  * a cost-free input (surplus water, an accounting flow, a by-product) is priced at zero, so how
    equally cheap solutions happen to split it cannot move the price. The earlier tracing method
    split supplier costs by quantity shares and leaked land and water accounting into electricity:
    on the Philippines GOLD case two solves with the same total cost gave 14.7 and 10.9.

  * CHP / co-generation: a gen tech's own and input cost is split by electricity's share of its
    USEFUL output; a dumped byproduct (no consumers) does not dilute (elec_frac == 1).
  * Per-run discovery: generation techs are discovered independently for each scenario dir, so a
    reform's new technologies (e.g. PEP's nuclear plant) are captured, never inherited.
  * Regions: each region's plant inputs are valued at that region's prices.
  * Spikes: a shadow price can jump in a year where a constraint binds. input_price_spikes() reports
    years where that moves the electricity price; it is a flag for review, not a correction.

Reads (raw long CSVs): ProductionByTechnologyByMode, UseByTechnologyByMode (t, f, y, value),
AnnualizedInvestmentCost, AnnualFixedOperatingCost, AnnualVariableOperatingCost (t, y, value),
CommodityMarginalPrice (r, f, y, value).
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
PRICE_STEM = "CommodityMarginalPrice"
INPUT_STEMS = (PROD_STEM, USE_STEM, PRICE_STEM) + COST_STEMS

PRICE_MISSING_HELP = (
    "The levelized electricity price values the power plants' inputs at the model's own commodity "
    "prices, which MUIOGO writes as CommodityMarginalPrice.csv. Solve the case with a MUIOGO version "
    "that writes it, or regenerate the run's result files (no new solve needed).")


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


def _lcoe_parts(csv_dir: str, busbar: str) -> pd.DataFrame:
    """Per-year pieces of the LCOE: plant ``own`` cost, ``inputs`` (their use at model prices),
    busbar ``gen``eration, ``lcoe``, and the ``top_input`` commodity by value. Indexed by int year,
    years with generation only."""
    if _find(csv_dir, PRICE_STEM) is None:
        raise FileNotFoundError(f"lcoe: no {PRICE_STEM}.csv in {csv_dir}. {PRICE_MISSING_HELP}")
    prod = _read_long(csv_dir, PROD_STEM)
    use = _read_long(csv_dir, USE_STEM)
    costs = _load_costs(csv_dir)
    price = _read_long(csv_dir, PRICE_STEM)

    # generation = producers of the busbar commodity (discovered per run)
    gen = set(prod.loc[prod.f == busbar, "t"].unique())
    if not gen:
        raise ValueError(f"lcoe_by_year: no producers of busbar {busbar!r} in {csv_dir}")

    # CHP / co-gen: electricity's share of each gen tech's USEFUL output (dumped byproduct -> 1)
    consumed = use.groupby("f")["v"].sum()
    used_commodities = set(consumed[consumed > 0].index)
    gen_prod = prod[prod.t.isin(gen)].groupby(["t", "f"])["v"].sum()
    elec_frac = {}
    for t in gen:
        outs = gen_prod.xs(t, level="t") if t in gen_prod.index.get_level_values("t") else pd.Series(dtype=float)
        useful = {g: v for g, v in outs.items() if g == busbar or g in used_commodities}
        tot = sum(useful.values())
        elec_frac[t] = (useful.get(busbar, 0.0) / tot) if tot > 0 else 1.0

    own = costs[costs.t.isin(gen)].copy()
    own["w"] = own["cost"] * own["t"].map(elec_frac)
    own_y = own.groupby("y")["w"].sum()

    # Each region's plant inputs at that region's prices. Without a region column in the use file
    # the prices must be one region's, or there is no way to know which price applies.
    inputs = use[use.t.isin(gen)].copy()
    keys = ["f", "y"]
    if "r" in inputs.columns and "r" in price.columns:
        keys = ["r", "f", "y"]
        inputs["r"] = inputs["r"].astype(str)
        price = price.assign(r=price["r"].astype(str))
    elif "r" in price.columns and price["r"].nunique() > 1:
        raise ValueError(
            f"lcoe: {PRICE_STEM}.csv in {csv_dir} has prices for {price['r'].nunique()} regions but "
            f"{USE_STEM}.csv has no region column, so the plants' inputs cannot be matched to their "
            "region's prices.")
    p = price.groupby(keys, as_index=False)["v"].mean().rename(columns={"v": "p"})
    inputs = inputs.merge(p, on=keys, how="left")
    inputs["p"] = inputs["p"].fillna(0.0)                 # an unpriced input is free
    inputs["w"] = inputs["v"] * inputs["p"] * inputs["t"].map(elec_frac)
    input_y = inputs.groupby("y")["w"].sum()
    top = inputs.groupby(["y", "f"])["w"].sum().reset_index().sort_values("w").groupby("y").tail(1)
    top_y = dict(zip(top["y"], top["f"]))

    gen_out = prod[prod.f == busbar].groupby("y")["v"].sum()
    rows = {}
    for y, g in gen_out.items():
        if g > 0:
            o, i = float(own_y.get(y, 0.0)), float(input_y.get(y, 0.0))
            rows[int(y)] = {"own": o, "inputs": i, "gen": float(g), "lcoe": (o + i) / float(g),
                            "top_input": top_y.get(y)}
    return pd.DataFrame.from_dict(rows, orient="index").sort_index()


def lcoe_by_year(csv_dir: str, busbar: str) -> dict:
    """LCOE index by int year for one scenario dir. ``busbar`` = the busbar electricity commodity
    (generation output, pre-T&D; e.g. 'PHL_POW_ELE')."""
    parts = _lcoe_parts(csv_dir, busbar)
    return {int(y): float(v) for y, v in parts["lcoe"].items()}


def input_price_spikes(csv_dir: str, busbar: str, *, factor: float = 5.0,
                       min_share: float = 0.1) -> list:
    """Years where the plants' input cost per unit of electricity is more than ``factor`` times its
    median over the years AND is more than ``min_share`` of that year's price -- typically a
    shadow-price spike where a constraint binds in one year. Informational: it can be real scarcity,
    so the price is not changed; the caller reports it."""
    parts = _lcoe_parts(csv_dir, busbar)
    if parts.empty:
        return []
    per_unit = parts["inputs"] / parts["gen"]
    share = parts["inputs"] / (parts["own"] + parts["inputs"]).where(lambda x: x != 0)
    med = float(per_unit.median())
    flagged = []
    for y in parts.index:
        if not share.get(y, 0.0) > min_share:          # also skips NaN (no cost at all)
            continue
        if med > 0 and per_unit[y] > factor * med:
            flagged.append({"year": int(y), "times_usual": round(float(per_unit[y] / med), 1),
                            "share_of_price": round(float(share[y]), 3), "top_input": parts.at[y, "top_input"]})
        elif med == 0 and per_unit[y] > 0:
            flagged.append({"year": int(y), "times_usual": None,
                            "share_of_price": round(float(share[y]), 3), "top_input": parts.at[y, "top_input"]})
    return flagged


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

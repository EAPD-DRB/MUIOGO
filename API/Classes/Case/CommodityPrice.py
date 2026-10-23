"""One annual marginal price per commodity, rebuilt from the balance-row shadow prices.

MUIO 5.7 balances each commodity per timeslice, per season or once a year, so
its marginal cost is spread over several balance rows: one per timeslice or
season, plus a yearly row carrying yearly demand and capacity inputs. No single
row's shadow price is "the" commodity price any more. This combines them:

- Annual commodities: the shadow price of their yearly balance row(s).
- Timeslice and season commodities: the shadow prices of the timeslice (or
  season) rows, weighted by
    * the commodity's demand profile where it has one: the cost of one more
      unit of its specified demand; otherwise
    * when the commodity is used that year: the cost of one more unit used the
      way it is used now. A commodity not used at all that year falls back to
      the length of each timeslice.
  A use also enters the yearly balance row(s), so their shadow prices are added
  for use-weighted prices.

The yearly rows differ between model files (MUIOGO's keeps one per commodity,
MUIO's carry duplicates or a roll-up row), so the shadow prices of every yearly
row present for a commodity are added up; duplicates split one price between
them, and the sum puts it back together.

The rows' shadow prices are discounted, as the solver reports them; the price is
undiscounted the same way as MUIOGO's other shadow-price outputs. For a case
whose commodities are all balanced per timeslice this reproduces the old annual
shadow price for commodities with a demand profile.

This is MUIOGO code: MUIO has no equivalent. DataFileClass calls write_csv once
after a solve.
"""

import logging
from pathlib import Path

import pandas as pd

from Classes.Base import Config

logger = logging.getLogger(__name__)

OUTPUT_NAME = "CommodityMarginalPrice"

# The timeslice balance row: its 5.7 name, then the identical row of the 5.4 model, so results
# solved before 5.7 get a price too when their result files are regenerated.
_TS_BALANCES = ("EB_TimesliceBalance", "EBa11_EnergyBalanceEachTS5")
_SEASON_BALANCE = "EB_SeasonalBalance"
# Every yearly balance row any 5.x model file uses; whichever exist are added up. The plain
# EBb4 row is the 5.4 model's duplicate of EBb4_..._ICR that #530 removed.
_YEARLY_ROWS = (
    "EBb4_EnergyBalanceEachYear4_ICR",
    "EBb4_EnergyBalanceEachYear4",
    "EB_TimesliceAnnualBalance",
    "EB_AnnualBalance",
    "EB_AnnualRollup",
)


def _concat(frames, columns):
    """Concatenate the non-empty frames (an empty one would blur the dtypes)."""
    frames = [f for f in frames if f is not None and not f.empty]
    if not frames:
        return pd.DataFrame(columns=columns)
    return pd.concat(frames, ignore_index=True)


def _weighted_price(duals, key, profile, use, length):
    """Price per (r, f, y) from per-period shadow prices.

    ``duals`` has r, <key>, f, y, dual. ``profile``, ``use`` and ``length`` give
    the candidate weights per period (columns r, <key>, f, y, w; ``length`` has
    no f). Returns r, f, y, price, kind ('demand' or 'use').
    """
    cells = duals[["r", "f", "y"]].drop_duplicates()
    if cells.empty:
        return pd.DataFrame(columns=["r", "f", "y", "price", "kind"])

    def normalised(df):
        df = df[df["w"] > 0]
        total = df.groupby(["r", "f", "y"])["w"].transform("sum")
        return df.assign(w=df["w"] / total)

    by_profile = normalised(profile.merge(cells, on=["r", "f", "y"]))
    rest = cells.merge(by_profile[["r", "f", "y"]].drop_duplicates(),
                       on=["r", "f", "y"], how="left", indicator=True)
    rest = rest[rest["_merge"] == "left_only"].drop(columns="_merge")
    by_use = normalised(use.merge(rest, on=["r", "f", "y"]))
    unused = rest.merge(by_use[["r", "f", "y"]].drop_duplicates(),
                        on=["r", "f", "y"], how="left", indicator=True)
    unused = unused[unused["_merge"] == "left_only"].drop(columns="_merge")
    by_length = normalised(unused.merge(length, on=["r", "y"]))

    weights = _concat([
        by_profile.assign(kind="demand"),
        by_use.assign(kind="use"),
        by_length.assign(kind="use"),
    ], ["r", key, "f", "y", "w", "kind"])
    merged = weights.merge(duals, on=["r", key, "f", "y"], how="left")
    merged["dual"] = pd.to_numeric(merged["dual"], errors="coerce").fillna(0.0)
    merged["price"] = merged["w"] * merged["dual"]
    return merged.groupby(["r", "f", "y", "kind"], as_index=False)["price"].sum()


def annual_commodity_price(levels, ts_duals, season_duals, yearly_duals,
                           year_split, ts_season, demand_profile, use_ts, use_season):
    """Discounted annual price per (r, f, y).

    levels: {commodity: 'Ts' | 'Se' | 'An'}.
    ts_duals: r, l, f, y, dual. season_duals: r, ls, f, y, dual.
    yearly_duals: r, f, y, dual -- all yearly balance rows of a commodity, added up.
    year_split: r, y, l, YearSplit. ts_season: {timeslice: season}.
    demand_profile: r, f, y, l, SpecifiedDemandProfile.
    use_ts: r, l, f, y, use (use by timeslice-resolved technologies).
    use_season: r, ls, f, y, use (use by season-resolved technologies).
    """
    def as_text(df, cols):
        return df.astype({c: str for c in cols if c in df.columns})

    keys = ["r", "l", "ls", "f", "y"]
    ts_duals, season_duals, yearly_duals = (as_text(d, keys) for d in (ts_duals, season_duals, yearly_duals))
    year_split, demand_profile, use_ts, use_season = (
        as_text(d, keys) for d in (year_split, demand_profile, use_ts, use_season))
    ts_season = {str(k): (None if v is None else str(v)) for k, v in ts_season.items()}

    ts_comms = {f for f, lv in levels.items() if lv == "Ts"}
    se_comms = {f for f, lv in levels.items() if lv == "Se"}
    an_comms = {f for f, lv in levels.items() if lv == "An"}

    profile_ts = demand_profile.rename(columns={"SpecifiedDemandProfile": "w"})
    use_ts_w = use_ts.rename(columns={"use": "w"})
    length_ts = year_split.rename(columns={"YearSplit": "w"})

    parts = []

    ts = _weighted_price(
        ts_duals[ts_duals["f"].isin(ts_comms)], "l",
        profile_ts[profile_ts["f"].isin(ts_comms)],
        use_ts_w[use_ts_w["f"].isin(ts_comms)],
        length_ts)
    parts.append(ts)

    if se_comms:
        def to_season(df, keys):
            df = df.assign(ls=df["l"].map(ts_season)).dropna(subset=["ls"])
            return df.groupby(keys, as_index=False)["w"].sum()

        profile_se = to_season(profile_ts[profile_ts["f"].isin(se_comms)], ["r", "ls", "f", "y"])
        use_se = _concat([
            to_season(use_ts_w[use_ts_w["f"].isin(se_comms)], ["r", "ls", "f", "y"]),
            use_season.rename(columns={"use": "w"}),
        ], ["r", "ls", "f", "y", "w"]).groupby(["r", "ls", "f", "y"], as_index=False)["w"].sum()
        length_se = to_season(length_ts, ["r", "ls", "y"])
        parts.append(_weighted_price(
            season_duals[season_duals["f"].isin(se_comms)], "ls",
            profile_se, use_se[use_se["f"].isin(se_comms)], length_se))

    weighted = _concat(parts, ["r", "f", "y", "kind", "price"])
    if not weighted.empty:
        yearly = yearly_duals.rename(columns={"dual": "yearly"})
        weighted = weighted.merge(yearly, on=["r", "f", "y"], how="left")
        weighted["yearly"] = pd.to_numeric(weighted["yearly"], errors="coerce").fillna(0.0)
        is_use = weighted["kind"] == "use"
        weighted.loc[is_use, "price"] += weighted.loc[is_use, "yearly"]

    annual = yearly_duals[yearly_duals["f"].isin(an_comms)].rename(columns={"dual": "price"})

    out = _concat([weighted[["r", "f", "y", "price"]], annual[["r", "f", "y", "price"]]],
                  ["r", "f", "y", "price"])
    return out.sort_values(["r", "f", "y"]).reset_index(drop=True)


def _rows(results, name, columns):
    """Shadow prices of one constraint family from the parsed results table."""
    rows = results[results["parameter"] == name]
    if rows.empty:
        return pd.DataFrame(columns=columns + ["dual"])
    out = rows["id"].str.split(",", expand=True)
    out.columns = columns
    # the unrounded shadow price where the parser kept it (see generateCSVfromCBC)
    out["dual"] = rows["dual_raw" if "dual_raw" in rows.columns else "dual"].astype(float).values
    return out


def _activity_rows(results, name, columns):
    rows = results[results["parameter"] == name]
    if rows.empty:
        return pd.DataFrame(columns=columns + ["value"])
    out = rows["id"].str.split(",", expand=True)
    out.columns = columns
    out["value"] = rows["value"].astype(float).values
    return out


def write_csv(results, data, genData, start_year, csv_dir):
    """Build the price from one solve's parsed results and write it next to
    the other result CSVs. ``results`` is the table generateCSVfromCBC parses
    from results.txt (parameter, id, value, dual)."""
    # Names as text: a case may name its seasons 1, 2, ... while the solver output is text.
    seasons = {se["SeId"]: str(se["Se"]) for se in genData.get("osy-se", [])}
    ts_season = {str(ts["Ts"]): seasons.get(ts.get("SE")) for ts in genData.get("osy-ts", [])}
    levels = {c["Comm"]: (c.get("BalanceLevel") or "Ts") for c in genData.get("osy-comm", [])}

    year_split = pd.DataFrame(data["YearSplit"], columns=Config.PARAMETERS_C_full["YearSplit"])
    year_split["YearSplit"] = year_split["YearSplit"].astype(float)
    profile = pd.DataFrame(data.get("SpecifiedDemandProfile", []),
                           columns=Config.PARAMETERS_C_full["SpecifiedDemandProfile"])
    profile["SpecifiedDemandProfile"] = profile["SpecifiedDemandProfile"].astype(float)
    iar = pd.DataFrame(data["InputActivityRatio"], columns=Config.PARAMETERS_C_full["InputActivityRatio"])
    iar["InputActivityRatio"] = iar["InputActivityRatio"].astype(float)

    roa = _activity_rows(results, "RateOfActivity", ["r", "l", "t", "m", "y"])
    use_ts = (roa.merge(iar, on=["r", "t", "m", "y"])
                 .merge(year_split, on=["r", "y", "l"]))
    use_ts["use"] = use_ts["value"] * use_ts["InputActivityRatio"] * use_ts["YearSplit"]
    use_ts = use_ts.groupby(["r", "l", "f", "y"], as_index=False)["use"].sum()

    sra = _activity_rows(results, "SeasonalRateOfActivity", ["r", "ls", "t", "m", "y"])
    season_length = (year_split.assign(ls=year_split["l"].map(ts_season))
                     .groupby(["r", "ls", "y"], as_index=False)["YearSplit"].sum())
    use_season = (sra.merge(iar, on=["r", "t", "m", "y"])
                     .merge(season_length, on=["r", "ls", "y"]))
    use_season["use"] = use_season["value"] * use_season["InputActivityRatio"] * use_season["YearSplit"]
    use_season = use_season.groupby(["r", "ls", "f", "y"], as_index=False)["use"].sum()

    yearly = _concat([_rows(results, name, ["r", "f", "y"]) for name in _YEARLY_ROWS],
                     ["r", "f", "y", "dual"])
    yearly = yearly.groupby(["r", "f", "y"], as_index=False)["dual"].sum()

    price = annual_commodity_price(
        levels,
        _concat([_rows(results, name, ["r", "l", "f", "y"]) for name in _TS_BALANCES],
                ["r", "l", "f", "y", "dual"]),
        _rows(results, _SEASON_BALANCE, ["r", "ls", "f", "y"]),
        yearly,
        year_split, ts_season, profile, use_ts, use_season)

    discount = pd.DataFrame(data["DiscountRate"], columns=Config.PARAMETERS_C_full["DiscountRate"])
    discount["DiscountRate"] = discount["DiscountRate"].astype(float)
    price = price.merge(discount, on="r", how="left")
    years = price["y"].astype(int)
    price[OUTPUT_NAME] = price["price"] * (1 + price["DiscountRate"]) ** (years - int(start_year) + 0.5)
    price = price[["r", "f", "y", OUTPUT_NAME]]
    price.to_csv(Path(csv_dir) / f"{OUTPUT_NAME}.csv", index=None)
    return price

"""Signal extraction: turn CLEWS run outputs (and OG-Core results) into the series the
channels consume. Handles the two CLEWS CSV layouts (the 'Sum of ...' pivot and plain
long r,t,*,y,value) and the 999999 sentinel.

Three energy-price signals live here (all consumed as a reform/base RATIO on the electricity
unit-cost/retail-price the OG channels scale): the curated cost-index workbook PROXY
(cost_of_electricity_ratio); the LEVELIZED cost reconstructed from the raw CLEWS cost/production
CSVs (oglink.lcoe, the dense workbook-less default); and the MARGINAL price -- the shadow
price (LP dual) of the OSeMOSYS commodity-balance constraint. MUIOGO's CBC solve (`-printing all`)
exports that marginal to `res/<run>/csv/EBb4_EnergyBalanceEachYear4_ICR.csv` (columns
r,f,y,dual,DiscountRate); read it via commodity_shadow_price() / commodity_shadow_price_ratio().
The marginal is a short-run scarcity price and is degenerate in OSeMOSYS (it binds in scattered,
scenario-specific years), so it is an EXPLICIT opt-in (kind='marginal'), never the auto default --
see energy_price_ratio.
"""
from __future__ import annotations

import glob
import os
import re

import numpy as np
import pandas as pd

from oglink import lcoe

# cost_of_electricity_ratio + _ratio_over_common are defined below (moved from clews_signal.py)

SENTINEL = 999999.0
__all__ = [
    "activity_ratio",
    "capital_cost_share",
    "capital_intensity_ratio",
    "commodity_shadow_price",
    "commodity_shadow_price_ratio",
    "cost_of_electricity_ratio",
    "emissions_by_year",
    "emissions_ratio",
    "energy_price_ratio",
    "og_consumption_good",
    "og_interest_rate",
    "og_sector_output",
    "pm25_dose_response",
    "power_capex_increment",
    "public_capex_pct_gdp",
    "read_clews_long",
    "read_clews_matrix",
]


def _find(scenario_dir: str, metric: str, exclude: str = "") -> str:
    """Path to the CLEWS CSV for the EXACT stem ``metric``, tolerating only a leading ``<REGION>_`` and a
    trailing ``_<year>`` around it -- so a longer sibling that merely CONTAINS the stem is never silently
    read instead: ``DiscountedCapitalInvestment`` / ``CapitalInvestmentStorage`` for ``CapitalInvestment``,
    ``RateOfProductionByTechnologyByMode`` for ``ProductionByTechnologyByMode``,
    ``AnnualTechnologyEmissionByMode`` for ``AnnualTechnologyEmission``. Mirrors lcoe._find's anchored
    matcher (callers that WANT the ByMode variant ask for that exact stem). ``exclude`` still drops
    basenames containing that substring (kept for back-compat; the anchor makes it rarely needed).
    Raises FileNotFoundError if absent."""
    pat = re.compile(rf"^(?:[A-Za-z0-9]+_)?{re.escape(metric)}(?:_\d{{4}})?\.csv$", re.IGNORECASE)
    hits = sorted(h for h in glob.glob(os.path.join(scenario_dir, f"*{metric}*.csv"))
                  if pat.match(os.path.basename(h)))
    if exclude:
        hits = [h for h in hits if exclude.lower() not in os.path.basename(h).lower()] or hits
    if hits:
        return hits[0]
    raise FileNotFoundError(f"no '{metric}(.csv)' (anchored: <region>_{metric}_<year>.csv) in {scenario_dir}")


def read_clews_matrix(path: str) -> pd.DataFrame:
    """CLEWS per-technology x year export -> DataFrame indexed by technology, int YEAR
    columns, sentinels zeroed. Handles the 'Sum of ...' pivot banner; falls back to a
    long r,t,y,value file (pivoted to tech x year)."""
    raw = pd.read_csv(path, header=None, dtype=str)

    def yr_cells(row):
        return sum(1 for x in row if str(x).strip().isdigit() and 2000 <= int(str(x).strip()) <= 2100)

    hdr = max(range(min(len(raw), 6)), key=lambda i: yr_cells(raw.iloc[i]))
    if yr_cells(raw.iloc[hdr]) >= 3:  # pivot: years across the header row
        cols = [str(x).strip() for x in raw.iloc[hdr]]
        body = raw.iloc[hdr + 1:].copy()
        body.columns = cols
        year_cols = [c for c in cols if c.isdigit() and 2000 <= int(c) <= 2100]
        label_col = cols[0]
        body = body[[label_col] + year_cols].dropna(subset=[label_col])
        body = body[~body[label_col].astype(str).str.lower().str.contains("grand total|sum of", na=False)]
        df = body.set_index(label_col)
        df.columns = [int(c) for c in year_cols]
    else:  # long: region, tech, year, value
        long = pd.read_csv(path)
        cols = list(long.columns)
        lower = [c.lower() for c in cols]
        ycol = next(c for c in cols if long[c].astype(str).str.fullmatch(r"\d{4}").all())
        vcol = cols[-1]
        tcol = cols[1] if len(cols) >= 4 else cols[0]
        # if multiple emission species / modes are present, keep the first emission so the
        # pivot does not silently sum CO2e + PM2.5 (or across modes) into one number
        for disc in ("e", "emission"):
            if disc in lower:
                ec = cols[lower.index(disc)]
                long = long[long[ec] == long[ec].iloc[0]]
                break
        df = long.pivot_table(index=tcol, columns=ycol, values=vcol, aggfunc="sum")
        df.columns = [int(c) for c in df.columns]
    df = df.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    df[df >= SENTINEL] = 0.0
    return df


def read_clews_long(path: str, value_col: str | None = None) -> pd.DataFrame:
    """Plain long CLEWS file (e.g. r,t,e,y,value or r,l,f,y,Demand) as a DataFrame."""
    df = pd.read_csv(path)
    if value_col is None:
        value_col = df.columns[-1]
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0.0)
    return df


def power_capex_increment(base_dir, reform_dir, country, public_only=False) -> pd.Series:
    """Reform-minus-base CLEWS CapitalInvestment summed over power technologies, by year.
    This is the extra capital the transition requires -- the investment-channel signal.

    GUARDRAIL: zero technologies matching ``country.power_prefix`` is a CONFIG mismatch, not an
    economics fact -- summing an empty set would report a plausible-looking zero capex delta -- so it
    raises, naming the prefix and the technology codes actually present. When the prefix DOES match but
    none of the matched techs carries a ``public_power_markers`` marker (``public_only=True``), that may
    be a real case shape (no grid/T&D techs), so it warns loudly and returns zeros instead."""
    def _sum(folder):
        m = read_clews_matrix(_find(folder, "CapitalInvestment"))
        power = [t for t in m.index if country.is_power(t)]
        if not power:
            sample = list(map(str, m.index[:12]))
            raise ValueError(
                f"power_capex_increment: NO technology in {folder!r} matches "
                f"CountryConfig({country.name!r}).power_prefix={country.power_prefix!r} -- a config "
                f"mismatch, not a zero capex delta. Technology codes present include: {sample}"
                f"{'...' if len(m.index) > 12 else ''}. Set power_prefix to your CLEWS power-tech prefix.")
        keep = [t for t in power if country.is_public(t)] if public_only else power
        if public_only and not keep:
            print(f"[guardrail] power_capex_increment: {len(power)} techs match power_prefix="
                  f"{country.power_prefix!r} but NONE carries a public marker "
                  f"{country.public_power_markers!r} in {folder!r} -- treating PUBLIC (grid/T&D) capex "
                  "as zero. If your grid techs use different markers, set "
                  "CountryConfig.public_power_markers.")
            return pd.Series(0.0, index=m.columns)
        return m.loc[keep].sum(axis=0)
    base, reform = _sum(base_dir), _sum(reform_dir)
    years = sorted(set(base.index) & set(reform.index))
    return (reform.loc[years] - base.loc[years]).sort_index()


def _power_cost_sum(scenario_dir, country, metric, years) -> float:
    """Sum a CLEWS per-technology annual cost (``metric``) over the country's POWER technologies
    and over ``years``. Used to decompose the power fleet's annual cost into capital vs O&M."""
    m = read_clews_matrix(_find(scenario_dir, metric))
    keep = [t for t in m.index if country.is_power(t)]
    cols = [y for y in years if y in m.columns]
    if not keep or not cols:
        return 0.0
    return float(m.loc[keep, cols].values.sum())


def capital_cost_share(scenario_dir, country, window=(2026, 2035)) -> float:
    """Capital's share of the power fleet's annualized OWN cost over ``window``:

        sum(AnnualizedInvestmentCost) /
            sum(AnnualizedInvestmentCost + AnnualFixedOperatingCost + AnnualVariableOperatingCost)

    summed over the country's power technologies and the years in ``window`` (inclusive). This is
    the capital-intensity of the generation mix in cost-share terms -- renewables/CCS are nearly all
    capital recovery (no fuel), so a cleaner mix raises this share.

    NOTE: in this CLEWS/OSeMOSYS build FUEL is carried by upstream supply technologies, NOT the
    PHL_POW power plants (their AnnualVariableOperatingCost is ~0), so fuel is EXCLUDED here. This is
    therefore capital's share of the plants' OWN (capacity-related) cost -- a CONSERVATIVE proxy for
    the mix's capital intensity (including fossil fuel OPEX in the denominator would make the
    base-vs-reform contrast larger, not smaller)."""
    years = list(range(int(window[0]), int(window[1]) + 1))
    inv = _power_cost_sum(scenario_dir, country, "AnnualizedInvestmentCost", years)
    fix = _power_cost_sum(scenario_dir, country, "AnnualFixedOperatingCost", years)
    var = _power_cost_sum(scenario_dir, country, "AnnualVariableOperatingCost", years)
    denom = inv + fix + var
    if denom <= 0:
        raise ValueError(f"capital_cost_share: zero/empty total power cost in {scenario_dir} over "
                         f"{window} (no power techs matched, or years absent in the cost files).")
    return inv / denom


def capital_intensity_ratio(base_dir, reform_dir, country, window=(2026, 2035)) -> dict:
    """Reform/base ratio of the power fleet's capital cost share (``capital_cost_share``) -- the
    multiplicative ``gamma_scale`` for ``policy_levers.set_capital_intensity``. The reform/base
    RATIO (not the level) is the calibration object, mirroring every other channel here: it uses
    CLEWS only for the transition CHANGE and is robust to the (uncalibrated) money units. Returns
    provenance: ``{base_share, reform_share, ratio, window, note}``."""
    sb = capital_cost_share(base_dir, country, window)
    sr = capital_cost_share(reform_dir, country, window)
    return {"base_share": sb, "reform_share": sr, "ratio": float(sr / sb), "window": tuple(window),
            "note": "ratio of capital's share of the power fleet's own annualized cost (capex "
                    "recovery + fixed + variable O&M); fuel sits on upstream techs and is excluded "
                    "-> conservative. gamma is time-invariant in OG-Core, so a single window is "
                    "frozen into the permanent shift; this share is window-sensitive (verify)."}


def _ratio_over_common(base: pd.Series, reform: pd.Series) -> pd.Series:
    """Reform/base ratio over the years both series share; a 0 baseline -> NaN (no inf /
    0-division), sorted by year. The shared shape of every reform/base ratio signal here."""
    years = sorted(set(base.index) & set(reform.index))
    denom = base.loc[years].replace(0.0, np.nan)
    return (reform.loc[years] / denom).sort_index()


def cost_of_electricity_ratio(base_xlsx: str, reform_xlsx: str, *, sheet=0,
                              row_match="average electricity cost") -> pd.Series:
    """Reform/base ratio of the electricity cost index, by year (the cost-index PROXY price
    signal). The CLEWS 'Cost of electricity generation' workbook is a metrics x years grid; the
    cost lives in a labeled ROW with calendar years as integer column headers, e.g. 1.10 ==
    reform electricity is 10% costlier that year. (Moved here from the former clews_signal.py.)"""
    def _read(path):
        df = pd.read_excel(path, sheet_name=sheet)
        label_col = df.columns[0]
        mask = df[label_col].astype(str).str.lower().str.contains(row_match)
        if not mask.any():
            raise ValueError(f"no row matching {row_match!r} in {path}")
        row = df[mask].iloc[0]
        year_cols = [c for c in df.columns if str(c).strip().isdigit()]
        years = [int(str(c)) for c in year_cols]
        vals = pd.to_numeric(pd.Series(row[year_cols].values), errors="coerce")
        return pd.Series(vals.values, index=years, dtype=float).dropna()
    return _ratio_over_common(_read(base_xlsx), _read(reform_xlsx))


class EmissionsSpeciesAbsent(ValueError):
    """The CLEWS case cannot supply the requested emission species: the export lacks it (or lacks a
    species column entirely). Distinct from a PARSE failure of a present file (which stays a raw
    pandas error) so callers -- the health channel -- can SKIP on absence without swallowing
    corruption."""


def emission_species(scenario_dir) -> list | None:
    """The species codes present in the scenario's AnnualTechnologyEmission* export, or None when the
    export / its species column is unavailable. Best-effort (never raises) -- a validation/provenance
    helper for the write-back artifacts, not a data path."""
    try:
        try:
            path = _find(scenario_dir, "AnnualTechnologyEmissionByMode")
        except FileNotFoundError:
            path = _find(scenario_dir, "AnnualTechnologyEmission")
        df = pd.read_csv(path)
        cols = {c.lower(): c for c in df.columns}
        ecol = next((cols[k] for k in ("e", "emission") if k in cols), None)
        if ecol is None:
            return None
        return sorted(df[ecol].dropna().astype(str).unique())
    except Exception:  # noqa: BLE001 -- advisory helper; the read paths do their own loud failing
        return None


def emissions_by_year(scenario_dir, country, species=None) -> pd.Series:
    """Total emissions of `species` (default ``country.co2_emission``, e.g. CO2e; the health channel
    passes ``country.health_emission`` = PM2.5) by year. Prefers the *ByMode variant, which is present
    for BOTH base and reform here, so the two sides are aggregated identically (avoids a
    base=ByMode / reform=plain mismatch); summing over modes recovers the total."""
    try:
        path = _find(scenario_dir, "AnnualTechnologyEmissionByMode")
    except FileNotFoundError:
        path = _find(scenario_dir, "AnnualTechnologyEmission")
    df = read_clews_long(path)
    cols = {c.lower(): c for c in df.columns}
    ycol = cols.get("y") or next(c for c in df.columns if df[c].astype(str).str.fullmatch(r"\d{4}").all())
    ecol = next((cols[k] for k in ("e", "emission") if k in cols), None)   # same names read_clews_matrix accepts
    vcol = df.columns[-1]
    want = species or country.co2_emission
    if ecol is None:
        # No species column at all: summing every species would misattribute (e.g. an all-GHG total fed
        # to the PM2.5 health channel), so this is ABSENCE, not a default -- callers skip or configure.
        raise EmissionsSpeciesAbsent(
            f"emissions_by_year: {path} has no species column (looked for 'e'/'emission'; columns: "
            f"{list(df.columns)}); cannot select species {want!r}.")
    # EXACT species code (case-insensitive) -- a substring match would silently SUM overlapping
    # codes (e.g. 'CO2' + 'CO2EQ') into one number. A zero match is a config/export mismatch: say
    # which species ARE present rather than return an empty series.
    matched = df[df[ecol].astype(str).str.upper() == str(want).upper()]
    if matched.empty:
        present = sorted(df[ecol].dropna().astype(str).unique())   # dropna: a blank cell must not
        raise EmissionsSpeciesAbsent(                              # TypeError the diagnostic itself
            f"emissions_by_year: species {want!r} not in {path}; species present: {present}. "
            "Set CountryConfig.co2_emission / health_emission to the exact code your CLEWS "
            "model exports.")
    return matched.groupby(ycol)[vcol].sum().sort_index()


def emissions_ratio(base_dir, reform_dir, country, species=None) -> pd.Series:
    return _ratio_over_common(emissions_by_year(base_dir, country, species),
                              emissions_by_year(reform_dir, country, species))


# --- OG-Core output extractors (for og->clews and recycling channels) -----------

def og_sector_output(tpi: dict, m: int) -> np.ndarray:
    return np.asarray(tpi["Y_m"])[:, m]


def og_consumption_good(tpi: dict, i: int) -> np.ndarray:
    return np.asarray(tpi["C_i"])[:, i]


def og_interest_rate(tpi: dict, key: str = "r_p") -> np.ndarray:
    return np.asarray(tpi[key])


# --- path primitives (moved here from channels.py; the sourcing helpers below use them) ---

def _fit(value, n: int) -> np.ndarray:
    """Broadcast/forward-fill to length n; an empty input yields zeros (no crash)."""
    arr = np.atleast_1d(np.asarray(value, dtype=float))
    if arr.size == 0:
        return np.zeros(n)
    if arr.shape[0] == 1:
        return np.full(n, arr[0])
    if arr.shape[0] >= n:
        return arr[:n]
    out = np.empty(n)
    out[: arr.shape[0]] = arr
    out[arr.shape[0]:] = arr[-1]
    return out


def _align_to_start(series, start_year: int, n: int) -> np.ndarray:
    """Align a PERMANENT signal (a standing price level): real values during the data horizon,
    then the last value carried forward (it persists). Period 0 == start_year."""
    hi = int(series.index.max())
    if start_year > hi:
        return np.zeros(n)
    s = series.reindex(range(start_year, hi + 1)).ffill().bfill()
    return _fit(s.values, n)


def _align_finite(series, start_year: int, n: int) -> np.ndarray:
    """Align a FINITE flow (e.g. transition capex): real values during the data horizon, then ZERO
    -- the flow ends, not carried forward (forward-filling would break TPI's terminal condition)."""
    hi = int(series.index.max())
    if start_year > hi:
        return np.zeros(n)
    vals = series.reindex(range(start_year, hi + 1)).fillna(0.0).values
    out = np.zeros(n)
    out[: min(len(vals), n)] = vals[:n]
    return out


def _cost_xlsx(scenario_dir: str) -> str:
    hits = [h for h in glob.glob(os.path.join(scenario_dir, "*Cost of electricity*.xlsx"))
            if not os.path.basename(h).startswith("~$")]
    return min(hits)


def _has_cost_xlsx(scenario_dir: str) -> bool:
    """Whether a scenario dir ships the curated 'Cost of electricity' workbook (a curated artifact;
    MUIOGO's raw OSeMOSYS export does not ship one)."""
    return bool([h for h in glob.glob(os.path.join(scenario_dir, "*Cost of electricity*.xlsx"))
                 if not os.path.basename(h).startswith("~$")])


def _has_lcoe_inputs(scenario_dir: str) -> bool:
    """Whether a scenario dir ships the raw CSVs the LCOE reconstruction reads (the production/use
    topology + the three annual cost files). Present in every real MUIOGO/OSeMOSYS export -- the same
    CBC solve that emits the EBb4 marginal co-produces these, so 'lcoe' is available whenever the
    'marginal' would be, and denser. Glob-resolved (via lcoe.has_inputs) so it agrees with the sibling
    readers and the preflight checklist rather than demanding exact, un-decorated filenames."""
    return lcoe.has_inputs(scenario_dir)


# --- channel sourcing helpers: turn a CLEWS source choice into the ready value a channel applies ---

def energy_price_ratio(kind, *, base_dir, reform_dir, share, og_start_year, n, fuel=None,
                       busbar=None, resolved=None) -> np.ndarray:
    """The energy GOOD's reform/base price-ratio path from CLEWS, diluted by electricity's value-share
    of the OG energy good and aligned to og_start_year (length n). ``kind``:
      'cost_index' -- the curated cost-of-electricity index PROXY (a curated workbook);
      'lcoe'       -- the LEVELIZED cost of electricity reconstructed from the raw CLEWS cost/production
                      CSVs (dense + smooth; works on pure-MUIOGO output that ships no workbook), for the
                      busbar electricity commodity ``busbar`` (the country's generation-output code);
      'marginal'   -- the OSeMOSYS commodity-balance shadow price (the LP dual of EBb4) for the commodity
                      ``fuel`` (the country's household electricity code). A SHORT-RUN scarcity price,
                      degenerate in OSeMOSYS (it binds in scattered, scenario-specific years), so it is an
                      EXPLICIT opt-in, guarded against broadcasting a single binding year (see below). The
                      right object for a marginal/scarcity study (welfare cost, a binding cap/RPS), NOT the
                      retail tariff the OG channels actually scale.
      'auto'       -- 'cost_index' when both scenario dirs ship the workbook, else 'lcoe' when a busbar code
                      is set and the cost/production CSVs are present (the pure-MUIOGO case). The marginal
                      is NEVER selected automatically -- a levelized price is a better fit for OG's unit-
                      cost/retail-price channels and is computable whenever the marginal is; if no levelized
                      source is available 'auto' fails loudly rather than fall to the degenerate marginal.
    The controlled +20% case does NOT go through here -- a caller passes that scalar straight to
    energy_price(), undiluted. ``share is None`` (the country can't isolate electricity's value-share)
    returns None -- the dependent energy_price channel then skips, so this path is never consumed.

    ``resolved`` (optional dict) is filled with the price-source PROVENANCE -- the resolved kind and the
    files it read -- so the run can record WHICH source drove the result; with 'auto' the choice is
    otherwise invisible."""
    if share is None:
        return None
    requested = kind
    if kind == "auto":
        if _has_cost_xlsx(base_dir) and _has_cost_xlsx(reform_dir):
            kind, why = "cost_index", "cost-of-electricity workbook found in both scenario dirs"
        elif busbar and _has_lcoe_inputs(base_dir) and _has_lcoe_inputs(reform_dir):
            kind, why = "lcoe", "no workbook -> levelized cost from the CLEWS cost/production CSVs"
        else:
            raise ValueError(
                "energy_price_ratio kind='auto': no levelized price source is available -- neither a "
                "cost-of-electricity workbook (in both scenario dirs) nor the LCOE inputs (a busbar "
                "electricity code AND the ProductionByTechnologyByMode / UseByTechnologyByMode / cost "
                "CSVs). Set CountryConfig.busbar_electricity to enable the 'lcoe' source, ship a workbook, "
                "or request kind='marginal' explicitly (the marginal/shadow-price source is degenerate and "
                "is never selected automatically).")
        print(f"[provenance] energy price source: 'auto' resolved to '{kind}' ({why})")
    if kind == "marginal":
        ratio = commodity_shadow_price_ratio(base_dir, reform_dir, fuel=fuel)
        files = {"base": _MARGINAL_CONSTRAINT, "reform": _MARGINAL_CONSTRAINT, "fuel": fuel}
        if ratio.dropna().empty:
            raise ValueError(
                "energy_price_ratio kind='marginal': commodity-balance shadow-price ratio is empty / "
                "all-NaN -- no overlapping base/reform years, or a zero baseline shadow price for the "
                "matched fuel. Check the EBb4 export, the fuel code, and the run years.")
        # GUARDRAIL: the marginal is a SHORT-RUN scarcity price that is degenerate/sparse -- it binds
        # (nonzero) in scattered years that differ between base and reform, so the base/reform overlap can
        # collapse to a single year. _align_to_start would then BROADCAST that one point into a permanent
        # economy-wide price shock (observed on PHL: one 2029 point = +32%). A single/near-single overlap is
        # not a credible price PATH, so refuse it loudly rather than ship a spurious permanent shock. The
        # fix is a levelized price: kind='cost_index' (workbook) or kind='lcoe' -- both dense + smooth.
        n_overlap = int(ratio.dropna().shape[0])
        if n_overlap < _MARGINAL_MIN_OVERLAP_YEARS:
            raise ValueError(
                f"energy_price_ratio kind='marginal': the commodity-balance shadow price for fuel={fuel!r} "
                f"overlaps in only {n_overlap} year(s) between base and reform (need >= "
                f"{_MARGINAL_MIN_OVERLAP_YEARS}). The marginal is a sparse/degenerate short-run price (it "
                "binds in different years per scenario), so a single overlapping year would broadcast to a "
                "spurious PERMANENT price shock. Use a levelized price instead: a cost-of-electricity "
                "workbook (kind='cost_index') or kind='lcoe' (levelized cost from the CLEWS cost/production "
                "CSVs).")
    elif kind == "lcoe":
        if not busbar:
            raise ValueError(
                "energy_price_ratio kind='lcoe' needs the busbar electricity commodity code -- set "
                "CountryConfig.busbar_electricity (e.g. 'PHL_POW_ELE') or pass busbar=...; it is the LCOE "
                "denominator and identifies the generation fleet (the producers of that commodity).")
        ratio = lcoe.lcoe_ratio(base_dir, reform_dir, busbar)
        files = {"base": lcoe.PROD_STEM, "reform": lcoe.PROD_STEM, "busbar": busbar}
        if ratio.dropna().empty:
            raise ValueError(
                f"energy_price_ratio kind='lcoe': the levelized-cost ratio for busbar={busbar!r} is empty "
                "-- no overlapping base/reform years with nonzero generation. Check the busbar code and that "
                "ProductionByTechnologyByMode + the cost CSVs are present in both scenario dirs.")
    elif kind == "cost_index":
        bx, rx = _cost_xlsx(base_dir), _cost_xlsx(reform_dir)
        ratio = cost_of_electricity_ratio(bx, rx)
        files = {"base": os.path.basename(bx), "reform": os.path.basename(rx)}
    else:
        raise ValueError(
            f"energy_price_ratio: unknown kind {kind!r} (use 'cost_index', 'lcoe', 'marginal', or 'auto')")
    if resolved is not None:
        resolved.update({"requested": requested, "kind": kind, **files})
    return _align_to_start(1.0 + share * (ratio - 1.0), og_start_year, n)


def activity_ratio(base_tpi, reform_tpi, *, driver="Y_m", og_index, elasticity=1.0) -> np.ndarray:
    """Reform/base ratio of OG activity (Y_m sector output, or C_i consumption good) at og_index,
    raised to elasticity -- the forward demand-scaling signal for emit_energy_demand."""
    get = og_sector_output if driver == "Y_m" else og_consumption_good
    yb, yr = get(base_tpi, og_index), get(reform_tpi, og_index)
    T = min(len(yb), len(yr))
    return (yr[:T] / np.maximum(yb[:T], 1e-12)) ** elasticity


def public_capex_pct_gdp(base_dir, reform_dir, country, *, og_start_year, T, scale=1.0,
                         smooth_years=1) -> np.ndarray:
    """Reform-minus-base PUBLIC-infrastructure (grid/T&D) capex as a finite %-of-GDP flow path
    (length T, zero after the CLEWS horizon -- a transition flow, not a permanent shift). The
    public-investment channel's input. units.deflator (=1.0, uncalibrated) is the CLEWS-money<->GDP
    bridge, made explicit."""
    inc = power_capex_increment(base_dir, reform_dir, country, public_only=True)
    pct_gdp = scale * inc * float(getattr(country.units, "deflator", 1.0)) / country.gdp_musd
    if smooth_years > 1:
        pct_gdp = pct_gdp.rolling(smooth_years, center=True, min_periods=1).mean()
    return _align_finite(pct_gdp, og_start_year, T)


def pm25_dose_response(country, *, override=None) -> float:
    """The emissions->deaths multiplier M (energy mass share x CRF elasticity; PHL ~0.082). Precedence:
    override > country.pm25_dose_response > 1.0 (the naive 1:1, with a loud guardrail -- power is only
    ~10% of ambient PM2.5, so 1.0 overstates the health effect ~12x)."""
    M = override if override is not None else getattr(country, "pm25_dose_response", None)
    if M is None:
        print(f"[guardrail] health: no calibrated emissions->deaths dose-response (M) for "
              f"{getattr(country, 'name', 'country')}; using M=1.0 (naive 1:1, overstates the effect). "
              "Add a row to oglink/data/pm25_health.json.")
        return 1.0
    return float(M)


_MARGINAL_CONSTRAINT = "EBb4_EnergyBalanceEachYear4_ICR"  # OSeMOSYS annual commodity balance


_MARGINAL_ZERO_ATOL = 1e-3   # CBC dual reporting resolution: |dual| at/below this is slack/noise, not a price

# Minimum base/reform overlapping years for the sparse marginal (EBb4 shadow price) to be a credible price
# PATH. Below this, _align_to_start would broadcast a near-single point into a spurious permanent shock (see
# the guardrail in energy_price_ratio); the levelized 'cost_index'/'lcoe' sources are dense and preferred.
_MARGINAL_MIN_OVERLAP_YEARS = 3


def commodity_shadow_price(source, *, fuel=None, undiscount=True, start_year=None,
                           drop_zero=True, zero_atol=_MARGINAL_ZERO_ATOL,
                           constraint=_MARGINAL_CONSTRAINT) -> pd.Series:
    """The rigorous energy price: the annual dual of the OSeMOSYS commodity-balance
    constraint, as exported by a MUIOGO CBC solve to
    `res/<run>/csv/EBb4_EnergyBalanceEachYear4_ICR.csv` (columns r,f,y,<dual>,DiscountRate).
    Returns a Series indexed by int year for the chosen fuel(s).

    ``source`` is that CSV file, or a run/csv directory containing it. ``fuel`` selects the
    commodity good households face: a code (e.g. 'ELC001') or list of codes; default matches
    electricity codes (prefix 'ELC'). MUIOGO writes the dual *discounted* to start-year PV
    (raw x (1+DR)^(y-start_year+0.5)); ``undiscount=True`` recovers the raw per-year marginal
    (the genuine shadow price in that year). ``start_year`` defaults to the first year present.

    ``drop_zero=True`` (the default) drops years whose dual is at/below ``zero_atol`` (slack): in a real
    CBC export the commodity balance for household electricity is binding most years, so a reported 0 --
    or a sub-resolution near-zero like 1e-4 against genuine duals of O(1-10) -- means the constraint was
    slack/unreported that year: MISSING data, not a true zero price. Keeping such a value would let it
    form an absurd ratio against a nonzero counterpart -- a reform-side zero -> ~100% price collapse, a
    base-side 1e-4 -> a 10,000x spike (both observed on PHL's PHL_HOU_ELE). After the drop the ratio only
    spans years where BOTH scenarios carry a genuine dual. (On PHL the surviving years barely move
    between Base/PEP, so the dual is near-flat there -- the curated cost-of-electricity workbook stays
    the meaningful PHL source; the dual is the fallback for runs that ship no workbook.)
    """
    path = source if os.path.isfile(source) else _find(source, constraint.split("_", 1)[0])
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    low = {c.lower(): c for c in df.columns}
    rcol, fcol, ycol = low["r"], low["f"], low["y"]
    dr_col = low.get("discountrate")
    val_col = next((c for c in df.columns if "energybalance" in c.lower()), None)
    if val_col is None:  # fall back to the lone remaining numeric column
        val_col = next(c for c in df.columns if c not in (rcol, fcol, ycol, dr_col))
    df[ycol] = pd.to_numeric(df[ycol], errors="coerce")
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")

    if fuel is None:
        mask = df[fcol].astype(str).str.upper().str.startswith("ELC")
    else:
        codes = [fuel] if isinstance(fuel, str) else list(fuel)
        mask = df[fcol].astype(str).isin(codes)
    sub = df[mask].dropna(subset=[ycol, val_col]).copy()
    if sub.empty:
        present = sorted(df[fcol].astype(str).unique())
        raise ValueError(f"commodity_shadow_price: no rows for fuel={fuel!r} in {path}; "
                         f"fuels present: {present[:15]}{'...' if len(present) > 15 else ''}")
    matched = sorted(sub[fcol].dropna().astype(str).unique())
    if fuel is None and len(matched) > 1:
        # Averaging DISTINCT commodities' duals (e.g. ELC001 transmission + ELC002 distribution) would
        # silently blend different prices into "the" electricity price -- an economically material
        # choice the user must make, not a default.
        raise ValueError(
            f"commodity_shadow_price: the generic 'ELC*' fallback matched {len(matched)} distinct "
            f"commodities in {path}: {matched}. Averaging their duals would blend different prices. "
            "Set CountryConfig.electricity_fuel to the commodity households face (or pass fuel=...).")
    regions = sorted(sub[rcol].dropna().astype(str).unique())
    if len(regions) > 1:
        print(f"[guardrail] commodity_shadow_price: {len(regions)} regions {regions} present for "
              f"fuel(s) {matched} in {path} -- the dual is AVERAGED across regions (year-level mean). "
              "For a region-specific price, filter the EBb4 export to one region first.")
    if undiscount and dr_col is not None:
        dr = pd.to_numeric(sub[dr_col], errors="coerce").fillna(0.0)
        sy = int(start_year) if start_year is not None else int(sub[ycol].min())
        sub[val_col] = sub[val_col] / (1.0 + dr) ** (sub[ycol].astype(float) - sy + 0.5)
    s = sub.groupby(ycol)[val_col].mean().sort_index()   # mean across matched fuels (usually one)
    s.index = s.index.astype(int)
    if drop_zero:
        s = s[s.abs() > zero_atol]                        # slack/sub-resolution year -> missing, not free
    return s.rename("shadow_price")


def commodity_shadow_price_ratio(base_source, reform_source, *, fuel=None,
                                 undiscount=True, start_year=None) -> pd.Series:
    """Reform/baseline annual energy shadow-price ratio -- the rigorous analogue of
    cost_of_electricity_ratio(), to drive the energy_price channel from the true LP dual
    instead of the cost-index proxy. Ratio by year (reform shadow price / baseline)."""
    b = commodity_shadow_price(base_source, fuel=fuel, undiscount=undiscount, start_year=start_year)
    r = commodity_shadow_price(reform_source, fuel=fuel, undiscount=undiscount, start_year=start_year)
    return _ratio_over_common(b, r)

"""Adapt a MUIOGO run-output directory into the sources the channels/signals consume.

MUIOGO's CBC solve writes per-variable CSVs (and the EBb4 commodity-balance shadow price) under
``<DataStorage>/<case>/res/<caserun>/csv/``. This module locates that csv dir, lists the
electricity commodity codes present in the marginal export, and checks the expected files are
there -- so ``signals.commodity_shadow_price`` (the energy_price ``kind="marginal"`` opt-in source)
can be pointed straight at a real run. It does NOT re-extract the marginal; reading the EBb4 shadow
price is ``signals.commodity_shadow_price``'s job. This is the discovery/validation seam between a
MUIOGO run on disk and the OG-side channels.
"""
from __future__ import annotations

import glob
import os

import pandas as pd

_EBB4 = "EBb4_EnergyBalanceEachYear4_ICR"   # the OSeMOSYS annual commodity-balance dual export


def find_run_csv_dir(path: str) -> str:
    """Return the absolute ``csv/`` dir of a MUIOGO run.

    Accepts the csv dir itself, the enclosing ``res/<caserun>`` dir, or a parent that
    contains ``res/<caserun>/csv``. Raises FileNotFoundError if no run csv dir is found.
    """
    path = os.path.abspath(path)
    if os.path.basename(os.path.normpath(path)) == "csv" and os.path.isdir(path):
        return path
    direct = os.path.join(path, "csv")
    if os.path.isdir(direct):
        return direct
    hits = sorted(glob.glob(os.path.join(path, "res", "*", "csv")))
    if hits:
        if len(hits) > 1:  # don't silently pick a caserun -- provenance must be unambiguous
            others = [os.path.basename(os.path.dirname(os.path.dirname(h))) for h in hits[1:]]
            print(f"[guardrail] muiogo_run: {len(hits)} run csv dirs under {path!r}; using "
                  f"{hits[0]!r} (others: {others}). Pass a specific res/<caserun> to disambiguate.")
        return os.path.abspath(hits[0])
    raise FileNotFoundError(
        f"no MUIOGO run csv dir under {path!r} (looked for ./csv and ./res/*/csv)")


def _ebb4_path(csv_dir: str) -> str:
    hits = sorted(glob.glob(os.path.join(csv_dir, f"*{_EBB4}*.csv")))
    if not hits:
        raise FileNotFoundError(
            f"no {_EBB4}*.csv (the commodity-balance dual) in {csv_dir!r}")
    return hits[0]


def electricity_fuels(csv_dir: str, prefix: str = "ELC") -> list[str]:
    """The electricity commodity codes present in the EBb4 dual export (e.g. ['ELC001', ...]).

    These are the household-facing energy commodity; the concordance maps them to the OG
    energy good. Raises ValueError (listing what *is* present) if none match the prefix.
    """
    path = _ebb4_path(csv_dir)
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    cols = {c.lower(): c for c in df.columns}
    if "f" not in cols:
        raise ValueError(f"EBb4 export {path!r} has no 'f' (fuel) column; columns: {list(df.columns)}")
    fcol = cols["f"]
    fuels = sorted({str(x) for x in df[fcol] if str(x).upper().startswith(prefix.upper())})
    if not fuels:
        present = sorted({str(x) for x in df[fcol]})
        raise ValueError(f"no {prefix}* fuels in {csv_dir!r}; present: {present[:15]}"
                         f"{'...' if len(present) > 15 else ''}")
    return fuels


def verify_run(csv_dir: str, required=(_EBB4, "Demand")) -> dict:
    """Map each required CSV *stem* -> present? Glob-based (``*<stem>*.csv``) so region/year-
    prefixed OSeMOSYS exports (e.g. ``RE1_EBb4_..._2050.csv``) still register as present --
    consistent with how _ebb4_path locates the dual."""
    return {stem: bool(glob.glob(os.path.join(csv_dir, f"*{stem}*.csv"))) for stem in required}


# The MUIOGO export contract the channels consume -- stem -> which channel needs it. The LCOE 'auto'
# price is reconstructed from the production/use topology + the annual cost CSVs (all standard MUIOGO
# result CSVs); the EBb4 marginal only exists when the case was solved with CBC and '-printing all', and
# is the opt-in 'marginal' source only (NOT used by 'auto').
PREFLIGHT_STEMS = {
    "ProductionByTechnologyByMode": "energy price 'auto' (LCOE denominator: busbar generation)",
    "UseByTechnologyByMode": "energy price 'auto' (LCOE fuel-chain allocation)",
    "AnnualizedInvestmentCost": "capital-intensity channel + LCOE 'auto' (annualized capex)",
    "AnnualFixedOperatingCost": "capital-intensity channel + LCOE 'auto' (fixed O&M)",
    "AnnualVariableOperatingCost": "capital-intensity channel + LCOE 'auto' (variable O&M / fuel)",
    "Demand": "demand write-back baseline (emit_energy_demand)",
    "CapitalInvestment": "public-investment channel (power capex delta)",
    "AnnualTechnologyEmission": "carbon + health channels (matches the ...ByMode variant too)",
    _EBB4: "energy price 'marginal' OPT-IN only (a CBC '-printing all' export; NOT used by 'auto')",
}


def preflight(scenario_dir: str, *, label: str = "", out=print) -> dict:
    """Loud pre-run checklist of the MUIOGO export contract for one scenario dir, BEFORE any expensive
    OG solve: report which expected CSV stems are present and what each missing one disables. Missing
    stems are a WARNING, not an error -- experiments differ in which exports they need, and the channels
    themselves fail/skip loudly at the point of use."""
    found = verify_run(scenario_dir, required=tuple(PREFLIGHT_STEMS))
    missing = [s for s, ok in found.items() if not ok]
    tag = f" ({label})" if label else ""
    if not missing:
        out(f"  CLEWS export check{tag}: all {len(found)} expected CSV stems present")
    else:
        out(f"  CLEWS export check{tag}: {len(found) - len(missing)}/{len(found)} expected stems present; missing:")
        for s in missing:
            out(f"    - {s}  [{PREFLIGHT_STEMS[s]}]")
        out("    channels that need a missing export will skip or fail loudly at that point.")
    return found


# CLEWS export stems the figure DECK reads (emissions, capex, cost, the dual). Staged into a run's
# clews_source/ so a rebuilt deck is self-contained -- glob '*<stem>*' catches region/year-prefixed
# OSeMOSYS names and the .xlsx cost workbook.
_DECK_CLEWS_STEMS = ("AnnualTechnologyEmission", "CapitalInvestment", "AnnualizedInvestmentCost",
                     "AnnualFixedOperatingCost", "AnnualVariableOperatingCost", _EBB4,
                     "Cost of electricity")


def stage_clews_source(base_dir, reform_dir, dest_root) -> int:
    """Copy the CLEWS export files the deck reads from the base/reform scenario dirs into
    ``dest_root/{base,reform}/``, so a run's figure deck can be rebuilt WITHOUT the original MUIOGO case
    (self-contained; the deck falls back to the external dirs when this is absent). Best-effort per file;
    returns the number copied. A source dir that is unset/missing is skipped (no error)."""
    import shutil
    copied = 0
    for side, src in (("base", base_dir), ("reform", reform_dir)):
        if not (src and os.path.isdir(src)):
            continue
        dst = os.path.join(dest_root, side)
        os.makedirs(dst, exist_ok=True)
        for stem in _DECK_CLEWS_STEMS:
            for hit in glob.glob(os.path.join(src, f"*{stem}*")):
                if os.path.isfile(hit) and not os.path.basename(hit).startswith("~$"):
                    try:
                        shutil.copy2(hit, os.path.join(dst, os.path.basename(hit)))
                        copied += 1
                    except OSError:
                        pass
    return copied

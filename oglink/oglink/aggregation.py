"""Target a scenario at a SUB-GOOD inside an aggregated industry / consumption group --
generically, from whatever OG country package is installed.

A multi-industry OG calibration aggregates fine SAM sectors into M production industries
(its ``PROD_DICT``) and fine commodities into I consumption goods (its ``CONS_DICT``). The
model then runs at THAT resolution: one productivity/price/output per group, with no
within-group detail and no substitution between a group's members. The SAM, however, still
carries the fine detail. So a scenario can be TARGETED at a sub-good (electricity, water,
...) even when the calibration joins it with others -- by weighting a shock to the group
that contains the sub-good by the sub-good's SHARE of that group::

    weighted_shock = (sub-good's share of the group) x (requested sub-good shock)

This is the first-order pass-through of a sub-good price/productivity change to the
composite (the composite-commodity / two-stage-budgeting result). The model still RESPONDS
at the group's resolution; that response is interpretable as the sub-good's own only insofar
as the sub-good DOMINATES the group. When it does not -- a small sub-good in a big group, or
a sub-good split across several groups -- the result is dominated by aggregation error, so
this module flags that explicitly rather than letting a diluted number look clean.

Nothing here is country-specific. Groups come from the installed package's ``PROD_DICT`` /
``CONS_DICT`` (or any dict you pass); shares come from its SAM; the sub-good is named by SAM
code(s) or a regex. A future calibration with different sectors, a different M, or a
different ordering just works -- there are no hardcoded names, indices, or carriers. Where a
calibration already isolates the sub-good (a standalone "Energy" industry, say), the share is
~1 and the shock passes through clean -- the same call, no warning.

The bright line this module respects: it WEIGHTS A SHOCK to an EXISTING aggregate (a
scenario-layer act -- the calibration's Z/gamma/io_matrix are untouched). It never SPLITS an
industry into finer ones; that is a recalibration and belongs to the country model.

``locate``/``weighted_shock`` also return the group's INDEX, so this doubles as the
"which industry is energy" discovery: ``locate(PROD_DICT, "electricity")[0][0]``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

__all__ = [
    "CARRIERS",
    "GroupShare",
    "ShockPlan",
    "ShockTarget",
    "SubgoodShares",
    "aggregation_groups",
    "apply_productivity_haircut",
    "from_package",
    "input_intensity",
    "locate",
    "shares",
    "weighted_shock",
]

# Convenience regexes for the common IFPRI-SAM carriers. Axis-agnostic: they match an activity
# ('a*') OR a commodity ('c*') code, so the same name works on PROD_DICT and CONS_DICT
# (electricity = aelec/aelcg/celec/celcg/celcm/celcd; water = awatr/awatd/cwatr). These are
# only a shortcut -- pass an explicit list of codes, or your own regex, for anything else.
CARRIERS = {
    "electricity": r"^[ac]el",
    "water": r"^[ac]wat",
}


# --- SAM magnitude helpers (careful with the 'total' aggregate, which equals the primary sum) ----

def _drop_total(labels):
    """Labels with any 'total' aggregate row/column removed (it equals the primary sum and
    would double-count). Share ratios are invariant to it, but we drop it to be safe."""
    return [x for x in labels if str(x).strip().lower() != "total"]


def _activity_gross(sam, cols):
    """Gross output of activity COLUMNS = their column total over primary (non-'total') rows."""
    cols = [c for c in cols if c in sam.columns]
    if not cols:
        return 0.0
    block = sam.loc[_drop_total(sam.index), cols].apply(pd.to_numeric, errors="coerce")
    return float(np.nansum(block.values))


def _commodity_absorption(sam, rows, weight_cols=None):
    """Total absorption of commodity ROWS over ``weight_cols`` (default: all non-'total'
    columns = intermediate + final use). Pass household columns for a consumption-tax base."""
    rows = [r for r in rows if r in sam.index]
    if not rows:
        return 0.0
    cols = weight_cols if weight_cols is not None else _drop_total(sam.columns)
    cols = [c for c in cols if c in sam.columns]
    if not cols:
        return 0.0
    block = sam.loc[rows, cols].apply(pd.to_numeric, errors="coerce")
    return float(np.nansum(block.values))


# --- inter-industry input intensity (the cost-push weights OG-Core's production lacks) ------

def input_intensity(sam, prod_dict, carrier="electricity"):
    """Per-industry intensity of ``carrier`` as an intermediate INPUT, aligned to ``prod_dict`` order
    (an M-vector ``phi``). For each industry j: (``carrier`` commodity absorbed by j's activity columns)
    / (j's gross output) -- the COST-PUSH weight: a 1% rise in the carrier's price raises industry j's
    unit cost by ~``phi_j``%. This reads the SAM's intermediate-use block -- the inter-industry flows
    OG-Core's value-added-only production function does NOT carry -- so it is the data behind the
    Option-A' cost-push proxy. Nothing country-specific: rows/cols come from the SAM and ``prod_dict``.
    Returns 0 for an industry the SAM lacks output for or that uses none of the carrier.

    ``carrier`` is a CARRIERS key (e.g. 'electricity'), an explicit regex, or a list of SAM codes; the
    INPUT-use rows are the carrier's COMMODITY rows ('c*'), falling back to any carrier match."""
    if isinstance(carrier, (list, tuple, set)):
        wanted = set(map(str, carrier))
        rows = [r for r in sam.index if str(r) in wanted]
    else:
        rx = re.compile(CARRIERS.get(carrier, carrier))
        rows = [r for r in sam.index if rx.search(str(r))]
    crows = [r for r in rows if str(r).lower().startswith("c")] or rows   # commodity rows = input use
    out = []
    for codes in prod_dict.values():
        cols = list(dict.fromkeys(codes))
        gross = _activity_gross(sam, cols)
        absorbed = _commodity_absorption(sam, crows, weight_cols=cols)
        out.append((absorbed / gross) if gross > 0 else 0.0)
    return np.array(out, dtype=float)


# --- aggregation introspection (no country knowledge; just the dict you hand it) ------------

def aggregation_groups(group_dict):
    """The aggregation as an ordered list of ``(index, name, codes)``. The index is the model
    column for that group (io_matrix / Z are built in ``PROD_DICT`` key order)."""
    return [(i, name, list(codes)) for i, (name, codes) in enumerate(group_dict.items())]


def _all_codes(group_dict):
    seen = []
    for codes in group_dict.values():
        for c in codes:
            if c not in seen:
                seen.append(c)
    return seen


def _match_codes(group_dict, subgood):
    """Resolve ``subgood`` to the codes actually present in this aggregation.
    ``subgood`` is a list of SAM codes (kept where present) or a regex string -- a ``CARRIERS``
    key (e.g. ``"electricity"``) is expanded to its pattern; anything else is used as-is."""
    universe = _all_codes(group_dict)
    if isinstance(subgood, str):
        rx = re.compile(CARRIERS.get(subgood, subgood))
        return [c for c in universe if rx.search(str(c))]
    wanted = list(subgood)
    return [c for c in universe if c in wanted]


def locate(group_dict, subgood):
    """The groups whose members include the sub-good, as ``(index, name, matched_codes)``.
    May be more than one (a sub-good split across groups, e.g. ZAF electricity) or empty."""
    codes = set(_match_codes(group_dict, subgood))
    out = []
    for i, (name, members) in enumerate(group_dict.items()):
        hit = [c for c in members if c in codes]
        if hit:
            out.append((i, name, hit))
    return out


# --- shares + weighted shock ----------------------------------------------------------------

@dataclass
class GroupShare:
    index: int            # model column for this aggregate (PROD_DICT/CONS_DICT order)
    name: str             # the aggregate's name (e.g. "Utilities")
    matched_codes: list   # sub-good codes found in this group (e.g. ["aelec"])
    subgood_size: float   # SAM magnitude of the sub-good within this group
    group_size: float     # SAM magnitude of the whole group
    share: float          # subgood_size / group_size in [0, 1]


@dataclass
class SubgoodShares:
    axis: str
    subgood: object
    matched_codes: list
    groups: list          # list[GroupShare]

    @property
    def split(self):
        return len(self.groups) > 1


def shares(sam, group_dict, subgood, *, axis="production", weight_cols=None):
    """The sub-good's share of each aggregate that contains it, from the SAM.

    ``axis="production"`` weights by activity gross output (PROD_DICT, for a supply-side Z
    shock); ``axis="consumption"`` weights by commodity absorption (CONS_DICT, for a tax on a
    consumption good) -- pass ``weight_cols`` (e.g. household columns) for a precise tax base.
    Raises if the sub-good matches no code in this aggregation."""
    if axis not in ("production", "consumption"):
        raise ValueError("axis must be 'production' or 'consumption'")
    hits = locate(group_dict, subgood)
    if not hits:
        raise ValueError(
            f"sub-good {subgood!r} matched no codes in this aggregation. "
            f"Available codes: {_all_codes(group_dict)}")
    on_cols = axis == "production"
    present = (lambda c: c in sam.columns) if on_cols else (lambda c: c in sam.index)
    size = (lambda members: _activity_gross(sam, members)) if on_cols else \
           (lambda members: _commodity_absorption(sam, members, weight_cols))
    groups = []
    for i, name, hit in hits:
        members = [c for c in dict.fromkeys(group_dict[name]) if present(c)]
        sub_codes = [c for c in hit if present(c)]
        grp_size = size(members)
        sub_size = size(sub_codes)
        share = (sub_size / grp_size) if grp_size > 0 else 0.0
        groups.append(GroupShare(i, name, sub_codes, sub_size, grp_size, share))
    matched_all = sorted({c for _, _, h in hits for c in h})
    return SubgoodShares(axis, subgood, matched_all, groups)


@dataclass
class ShockTarget:
    index: int            # model column to shock
    group: str            # the aggregate's name
    share: float          # sub-good share of the aggregate
    weighted_shock: float # share * requested shock (first-order pass-through)
    diluted: bool         # share < warn_threshold
    note: str             # human-readable interpretation


@dataclass
class ShockPlan:
    axis: str
    subgood: object
    matched_codes: list
    requested_shock: float
    targets: list         # list[ShockTarget]
    split: bool
    warnings: list        # honesty warnings to surface to the user


def _label(sh):
    return sh.subgood if isinstance(sh.subgood, str) else "+".join(map(str, sh.matched_codes))


def weighted_shock(sam, group_dict, subgood, shock, *, axis="production", weight_cols=None,
                   warn_threshold=0.5, model_m=None):
    """A share-weighted shock plan for a sub-good inside an aggregated group.

    For every aggregate that contains the sub-good, returns a target with
    ``weighted_shock = share * shock`` -- the magnitude to apply to that aggregate's column.
    Emits warnings when the approximation is weak: ``share < warn_threshold`` (the aggregate
    response cannot be read as the sub-good alone) or the sub-good is split across groups.
    ``model_m`` (the M the model actually runs) is validated against the aggregation if given.
    The calibration is never modified -- this only describes a scenario-layer shock."""
    sh = shares(sam, group_dict, subgood, axis=axis, weight_cols=weight_cols)
    label = _label(sh)
    warnings = []
    targets = []
    for g in sh.groups:
        diluted = g.share < warn_threshold
        if g.share >= 0.999:
            note = f"'{g.name}' is essentially all {label} ({g.share:.0%}); clean pass-through."
        else:
            rest = 1.0 - g.share
            note = (f"{label} is {g.share:.0%} of '{g.name}'; the other {rest:.0%} moves with it"
                    + (" -- the aggregate response cannot be read as " + str(label) + " alone."
                       if diluted else f" ({rest:.0%} contamination)."))
            if diluted:
                warnings.append(note)
        targets.append(ShockTarget(g.index, g.name, g.share, g.share * float(shock), diluted, note))
    if sh.split:
        warnings.insert(0, f"{label} is split across {len(sh.groups)} groups "
                           f"{[t.group for t in targets]}; no single aggregate represents it -- "
                           f"applying a weighted shock to each.")
    if model_m is not None:
        model_m = int(model_m)
        if len(group_dict) != model_m:
            warnings.append(
                f"this aggregation has {len(group_dict)} groups but the model runs M={model_m}; "
                "indices align only if the model is run at this aggregation.")
        out_of_range = [t.index for t in targets if t.index >= model_m]
        if out_of_range:
            raise ValueError(f"target index/es {out_of_range} out of range for M={model_m} "
                             "(run the model at this aggregation, or target a valid index)")
    return ShockPlan(axis, subgood, sh.matched_codes, float(shock), targets, sh.split, warnings)


def apply_productivity_haircut(p, plan):
    """Apply a production-axis ``ShockPlan`` as a TFP haircut: ``Z[:, idx] *= (1 - weighted)``
    for each target (the supply-side / route-B use). Pure mutation of a duck-typed ``p``; the
    caller is responsible for surfacing ``plan.warnings``. Returns provenance."""
    if plan.axis != "production":
        raise ValueError("apply_productivity_haircut expects a production-axis plan")
    Z = np.array(p.Z, dtype=float)   # copy: never mutate the caller's array in place
    M = Z.shape[1]
    for t in plan.targets:
        if not 0 <= t.index < M:
            raise ValueError(f"target index {t.index} out of range for M={M}")
        Z[:, t.index] = Z[:, t.index] * (1.0 - t.weighted_shock)
    p.Z = Z
    return {"applied": [(t.index, t.weighted_shock) for t in plan.targets],
            "warnings": list(plan.warnings)}


# --- loader: pull the aggregation + SAM from the installed country package by NAME ----------

def from_package(pkg_name):
    """Load ``(sam, PROD_DICT, CONS_DICT)`` from an installed OG country package by name, via
    the OG-template convention (``<pkg>.input_output.read_SAM``, ``<pkg>.constants``). The
    package is whatever MUIOGO installed for the chosen country; this never modifies it."""
    import importlib
    try:
        io = importlib.import_module(f"{pkg_name}.input_output")
        const = importlib.import_module(f"{pkg_name}.constants")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            f"could not import '{pkg_name}'; install the country OG model first "
            "(MUIOGO does this on country selection).") from exc
    sam = io.read_SAM()
    if sam is None:
        raise RuntimeError(f"{pkg_name}.input_output.read_SAM() returned None (SAM unavailable).")
    return sam, getattr(const, "PROD_DICT", None), getattr(const, "CONS_DICT", None)


if __name__ == "__main__":
    import sys
    pkg = sys.argv[1] if len(sys.argv) > 1 else "ogphl"
    sam, prod, cons = from_package(pkg)
    print(f"== {pkg}: sub-good shares (discovered from PROD_DICT/CONS_DICT + SAM) ==")
    for carrier in ("electricity", "water"):
        for axis, d in (("production", prod), ("consumption", cons)):
            if d is None:
                continue
            try:
                plan = weighted_shock(sam, d, carrier, 0.20, axis=axis)
            except ValueError as exc:
                print(f"  [{axis:11s}] {carrier:11s}: {exc}")
                continue
            for t in plan.targets:
                flag = "  [DILUTED]" if t.diluted else ""
                print(f"  [{axis:11s}] {carrier:11s} in '{t.group}' (idx {t.index}): "
                      f"share {t.share:5.0%} -> +20% sub-good = +{t.weighted_shock:.1%} on aggregate{flag}")
            for w in plan.warnings:
                print(f"      ! {w}")

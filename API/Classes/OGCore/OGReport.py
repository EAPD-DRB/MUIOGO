"""Economically consistent result comparisons for the OG-Core Results page.

Owns the single definition of how every OG-Core output is labelled, which unit it
is reported in, and how a baseline and reform are compared. The Results report
and the Explore view both read these rules from the payload built here, so a
variable can never be shown as a relative change in one panel and in percentage
points in another.

Comparison rules, by variable kind:
  level  -> percent change; a baseline at or below zero is flagged and only the
            difference is reported (a percent change of a negative base misleads)
  rate   -> shown in percent, compared in percentage points
  fiscal -> shown as a share of the same run's GDP, compared in percentage points
            of GDP; a negative baseline level is flagged

Household outputs (age x income group) are aggregated with the run's own
steady-state population weights (omega_SS) and income-group shares (lambdas),
taken from results_meta.json. When that metadata is missing the household blocks
are left out with a reason instead of being labelled with invented groups.

Pure standard library: like the rest of MUIOGO this never imports ogcore.
"""

from __future__ import annotations

import math

META_VERSION = 2
META_FIELDS = ("S", "J", "ages", "lambdas", "group_labels", "omega_SS")
# Transition charts cover this many years; the budget window is marked inside it.
PATH_YEARS = 40
BUDGET_WINDOW = 10
# Steady-state residuals above this are surfaced as "check solution".
CONVERGENCE_TOLERANCE = 1e-6

# Units carried in the payload; the frontend formats values by these names.
PERCENT = "%"
PERCENT_POINTS = "pp"
SHARE_OF_GDP = "% of GDP"
POINTS_OF_GDP = "pp of GDP"
MODEL_UNITS = "model units"
DIFFERENCE = "difference"

# name -> (label, short label, category, kind)
_CATALOG = {
    "Y": ("Gross domestic product", "GDP", "Output", "level"),
    "C": ("Aggregate consumption", "Consumption", "Output", "level"),
    "I": ("Investment", "Investment", "Output", "level"),
    "I_total": ("Total investment", "Total investment", "Output", "level"),
    "I_d": ("Domestic investment", "Domestic investment", "Output", "level"),
    "I_g": ("Public investment", "Public investment", "Output", "level"),
    "K": ("Capital stock", "Capital", "Output", "level"),
    "K_d": ("Domestically owned capital", "Domestic capital", "Output", "level"),
    "K_f": ("Foreign-owned capital", "Foreign capital", "Output", "level"),
    "K_g": ("Public capital stock", "Public capital", "Output", "level"),
    "L": ("Aggregate labor", "Labor", "Output", "level"),
    "B": ("Household savings", "Savings", "Output", "level"),
    "RM": ("Remittances", "Remittances", "Output", "level"),
    "BQ": ("Aggregate bequests by income group", "Bequests", "Households", "level"),
    "Y_m": ("Output by industry", "Industry output", "Output", "level"),
    "K_m": ("Capital by industry", "Industry capital", "Output", "level"),
    "L_m": ("Labor by industry", "Industry labor", "Output", "level"),
    "C_i": ("Consumption by good", "Consumption by good", "Output", "level"),
    "c_i": ("Household consumption by good", "Consumption by good", "Households", "level"),
    "p_m": ("Industry output prices", "Industry prices", "Prices", "level"),
    "p_i": ("Consumption good prices", "Good prices", "Prices", "level"),
    "theta": ("Pension replacement rate by income group", "Replacement rate", "Government", "rate"),
    "factor": ("Model-to-currency scaling factor", "Scaling factor", "Other", "level"),
    "w": ("Wage rate", "Wage", "Prices", "level"),
    "p_tilde": ("Composite consumption price", "Consumer price", "Prices", "level"),
    "r": ("Real interest rate", "Interest rate", "Prices", "rate"),
    "r_gov": ("Government interest rate", "Govt. interest rate", "Prices", "rate"),
    "r_p": ("Household portfolio return", "Portfolio return", "Prices", "rate"),
    "D": ("Government debt", "Debt", "Government", "fiscal"),
    "D_d": ("Domestically held debt", "Domestic debt", "Government", "fiscal"),
    "D_f": ("Foreign-held debt", "Foreign debt", "Government", "fiscal"),
    "G": ("Government consumption", "Govt. consumption", "Government", "fiscal"),
    "TR": ("Government transfers", "Transfers", "Government", "fiscal"),
    "UBI": ("Universal basic income", "UBI", "Government", "fiscal"),
    "agg_pension_outlays": ("Pension outlays", "Pensions", "Government", "fiscal"),
    "total_tax_revenue": ("Total tax revenue", "Tax revenue", "Government", "fiscal"),
    "business_tax_revenue": ("Business tax revenue", "Business tax", "Government", "fiscal"),
    "iit_payroll_tax_revenue": ("Income and payroll tax revenue", "Income + payroll tax", "Government", "fiscal"),
    "iit_revenue": ("Individual income tax revenue", "Income tax", "Government", "fiscal"),
    "payroll_tax_revenue": ("Payroll tax revenue", "Payroll tax", "Government", "fiscal"),
    "cons_tax_revenue": ("Consumption tax revenue", "Consumption tax", "Government", "fiscal"),
    "bequest_tax_revenue": ("Bequest tax revenue", "Bequest tax", "Government", "fiscal"),
    "wealth_tax_revenue": ("Wealth tax revenue", "Wealth tax", "Government", "fiscal"),
    "total_government_outlays": ("Total government outlays", "Total outlays", "Government", "fiscal"),
    "total_primary_government_outlays": ("Primary government outlays", "Primary outlays", "Government", "fiscal"),
    "debt_service": ("Debt service", "Debt service", "Government", "fiscal"),
    "debt_service_f": ("Debt service to foreigners", "Foreign debt service", "Government", "fiscal"),
    "new_borrowing": ("New borrowing", "New borrowing", "Government", "fiscal"),
    "new_borrowing_f": ("New borrowing from foreigners", "Foreign borrowing", "Government", "fiscal"),
    "c": ("Household consumption", "Consumption", "Households", "level"),
    "n": ("Labor supply", "Labor supply", "Households", "level"),
    "b_s": ("Wealth at start of age", "Wealth", "Households", "level"),
    "b_sp1": ("Savings carried to next age", "Savings", "Households", "level"),
    "before_tax_income": ("Before-tax income", "Before-tax income", "Households", "level"),
    "labor_income": ("Labor income", "Labor income", "Households", "level"),
    "capital_income": ("Capital income", "Capital income", "Households", "level"),
    "hh_net_taxes": ("Net taxes paid", "Net taxes", "Households", "level"),
    "income_payroll_taxes": ("Income and payroll taxes paid", "Income + payroll taxes", "Households", "level"),
    "sales_tax": ("Consumption taxes paid", "Consumption taxes", "Households", "level"),
    "wealth_tax": ("Wealth taxes paid", "Wealth taxes", "Households", "level"),
    "bequest_tax": ("Bequest taxes paid", "Bequest taxes", "Households", "level"),
    "bq": ("Bequests received", "Bequests", "Households", "level"),
    "tr": ("Transfers received", "Transfers", "Households", "level"),
    "ubi": ("UBI received", "UBI", "Households", "level"),
    "rm": ("Remittances received", "Remittances", "Households", "level"),
    "pension_benefits": ("Pension benefits", "Pensions", "Households", "level"),
    "etr": ("Effective tax rate", "Effective tax rate", "Households", "rate"),
    "mtrx": ("Marginal tax rate on labor income", "Labor MTR", "Households", "rate"),
    "mtry": ("Marginal tax rate on capital income", "Capital MTR", "Households", "rate"),
    "euler_savings": ("Savings Euler error", "Savings Euler error", "Diagnostics", "diagnostic"),
    "euler_labor_leisure": ("Labor-leisure Euler error", "Labor Euler error", "Diagnostics", "diagnostic"),
    "resource_constraint_error": ("Resource constraint error", "Resource error", "Diagnostics", "diagnostic"),
}

SUMMARY_VARS = ("Y", "C", "I", "K", "L", "w", "r", "D", "total_tax_revenue")
MACRO_VARS = ("Y", "C", "I", "K", "L", "w", "B")
PRICE_VARS = ("r", "r_gov", "r_p")
FISCAL_VARS = (
    "D", "total_tax_revenue", "iit_revenue", "payroll_tax_revenue", "business_tax_revenue",
    "cons_tax_revenue", "G", "TR", "total_government_outlays", "debt_service", "new_borrowing",
)
PATH_VARS = ("Y", "C", "I", "K", "L", "w", "r", "D", "total_tax_revenue", "G")
HOUSEHOLD_VARS = (
    "c", "n", "b_sp1", "before_tax_income", "labor_income", "hh_net_taxes", "etr", "mtrx", "mtry",
)
DIAGNOSTIC_VARS = ("euler_savings", "euler_labor_leisure", "resource_constraint_error")

_OTHER_CATEGORY_HINTS = (
    ("Government", ("tax", "revenue", "debt", "borrowing", "government", "pension", "outlay")),
    ("Diagnostics", ("error", "euler")),
    ("Prices", ("p_",)),
)


# ── catalog ──────────────────────────────────────────────────────────────────
def describe(name):
    """Label, short label, category and kind for any OG-Core output name."""
    if name in _CATALOG:
        label, short, category, kind = _CATALOG[name]
    else:
        label = short = name.replace("_", " ").strip().capitalize()
        category, kind = "Other", "level"
        for cat, hints in _OTHER_CATEGORY_HINTS:
            if any(h in name.lower() for h in hints):
                category = cat
                break
        if category == "Diagnostics":
            kind = "diagnostic"
    return {"label": label, "short": short, "category": category, "kind": kind}


def _shape(value):
    """Nested-list shape; a one-element vector counts as a scalar ([] shape)."""
    if isinstance(value, list) and len(value) == 1 and not isinstance(value[0], list):
        return []
    shape = []
    while isinstance(value, list):
        shape.append(len(value))
        value = value[0] if value else None
    return shape


def dims_of(value, meta):
    """Name the shape of a steady-state output: scalar, age_group, group, age, ..."""
    shape = _shape(value)
    if not shape:
        return "scalar"
    s_count = (meta or {}).get("S")
    j_count = (meta or {}).get("J")
    if len(shape) == 1:
        if shape[0] == j_count:
            return "group"
        if shape[0] == s_count:
            return "age"
        return "vector"
    if len(shape) == 2 and shape == [s_count, j_count]:
        return "age_group"
    return "matrix"


def catalog(names, sample, meta):
    """Catalog entries (with dims) for the variables present in ``sample``."""
    out = {}
    for name in names:
        entry = describe(name)
        entry["dims"] = dims_of(sample.get(name), meta)
        out[name] = entry
    return out


# ── numbers ─────────────────────────────────────────────────────────────────
def _num(value):
    """A finite float from a number or a one-element nested list, else None."""
    while isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _max_abs(value):
    if isinstance(value, list):
        return max((_max_abs(v) for v in value), default=0.0)
    number = _num(value)
    return abs(number) if number is not None else 0.0


def _path(value, count):
    """The first ``count`` points of a 1-D path, as floats or None."""
    if not isinstance(value, list):
        return None
    out = []
    for item in value[:count]:
        if isinstance(item, list) and len(item) != 1:
            return None
        out.append(_num(item))
    return out if any(v is not None for v in out) else None


def _share(value, gdp):
    if value is None or gdp is None or gdp == 0:
        return None
    return value / gdp * 100


def compare(kind, base, reform=None, base_gdp=None, reform_gdp=None):
    """Compare one scalar under the variable kind's rule.

    Returns display values (``baseline``/``reform`` in ``value_unit``), ``change``
    in ``change_unit`` and a ``negative_baseline`` flag. In a single-run view
    (reform None) only the baseline display value is filled.
    """
    out = {"baseline": None, "reform": None, "change": None, "change_unit": None,
           "value_unit": None, "negative_baseline": False}
    if kind == "rate":
        out["value_unit"] = PERCENT
        out["change_unit"] = PERCENT_POINTS
        out["baseline"] = base * 100 if base is not None else None
        out["reform"] = reform * 100 if reform is not None else None
        if base is not None and reform is not None:
            out["change"] = (reform - base) * 100
        return out
    if kind == "fiscal":
        out["value_unit"] = SHARE_OF_GDP
        out["change_unit"] = POINTS_OF_GDP
        out["baseline"] = _share(base, base_gdp)
        out["reform"] = _share(reform, reform_gdp)
        out["negative_baseline"] = base is not None and base < 0
        if out["baseline"] is not None and out["reform"] is not None:
            out["change"] = out["reform"] - out["baseline"]
        return out
    out["value_unit"] = MODEL_UNITS
    out["baseline"] = base
    out["reform"] = reform
    if base is None or reform is None:
        return out
    if base > 0:
        out["change"] = (reform / base - 1) * 100
        out["change_unit"] = PERCENT
    else:
        out["negative_baseline"] = base < 0
        out["change"] = reform - base
        out["change_unit"] = DIFFERENCE
    return out


# ── metadata ────────────────────────────────────────────────────────────────
def meta_complete(meta):
    """True when a results_meta dict carries everything the page labels from."""
    if not isinstance(meta, dict):
        return False
    try:
        version = int(meta.get("meta_version") or 0)
    except (TypeError, ValueError):
        return False
    return version >= META_VERSION and all(meta.get(k) is not None for k in META_FIELDS)


def household_weights(meta):
    """Population weights by age and group, W[s][j], summing to 1; None if unusable.

    omega_SS arrives by age (S,) or by age and group (S, J). The 1-D form is
    combined with the income-group shares, as ogcore's own ability charts do.
    """
    if not meta_complete(meta):
        return None
    s_count, j_count = int(meta["S"]), int(meta["J"])
    lambdas = [_num(x) for x in meta["lambdas"]]
    omega = meta["omega_SS"]
    if len(lambdas) != j_count or any(x is None for x in lambdas) or not isinstance(omega, list):
        return None
    if len(omega) != s_count:
        return None
    if isinstance(omega[0], list) and len(omega[0]) == j_count:
        grid = [[_num(x) for x in row] for row in omega]
    elif isinstance(omega[0], list) and len(omega[0]) != 1:
        return None
    else:
        grid = []
        for w in omega:
            weight = _num(w)
            if weight is None:
                return None
            grid.append([weight * lam for lam in lambdas])
    if any(x is None or x < 0 for row in grid for x in row):
        return None
    total = sum(sum(row) for row in grid)
    if total <= 0:
        return None
    return [[x / total for x in row] for row in grid]


def _age_group(value, s_count, j_count):
    if (isinstance(value, list) and len(value) == s_count
            and all(isinstance(r, list) and len(r) == j_count for r in value)):
        rows = [[_num(x) for x in row] for row in value]
        if all(x is not None for row in rows for x in row):
            return rows
    return None


def weighted_profiles(matrix, weights):
    """Population-weighted views of an age x group matrix.

    Returns (by_age, by_group, overall): the across-group average at each age,
    the across-age average within each group, and the population average.
    """
    s_count, j_count = len(weights), len(weights[0])
    by_age = []
    for s in range(s_count):
        mass = sum(weights[s])
        by_age.append(sum(weights[s][j] * matrix[s][j] for j in range(j_count)) / mass if mass else None)
    by_group = []
    for j in range(j_count):
        mass = sum(weights[s][j] for s in range(s_count))
        by_group.append(sum(weights[s][j] * matrix[s][j] for s in range(s_count)) / mass if mass else None)
    overall = sum(weights[s][j] * matrix[s][j] for s in range(s_count) for j in range(j_count))
    return by_age, by_group, overall


def compatible_meta(base_meta, reform_meta):
    """Reason the two runs' households cannot be compared, or None if they can."""
    if reform_meta is None:
        return None
    for key in ("S", "J", "starting_age", "ages", "lambdas"):
        if base_meta.get(key) != reform_meta.get(key):
            return ("The baseline and reform use different age or income-group definitions, "
                    "so household outcomes are not compared.")
    return None


# ── report ──────────────────────────────────────────────────────────────────
def _block(names, base, reform, base_gdp, reform_gdp):
    rows = []
    for name in names:
        b = _num(base.get(name))
        if b is None:
            continue
        r = _num(reform.get(name)) if reform is not None else None
        info = describe(name)
        row = {"name": name, "label": info["label"], "short": info["short"], "kind": info["kind"]}
        row.update(compare(info["kind"], b, r, base_gdp, reform_gdp))
        rows.append(row)
    return rows


def _paths(base_tpi, reform_tpi, base_ss, reform_ss, meta):
    count = min(PATH_YEARS, int(meta.get("T") or PATH_YEARS))
    start = int(meta.get("start_year") or 0)
    base_y = _path(base_tpi.get("Y"), count)
    reform_y = _path(reform_tpi.get("Y"), count) if reform_tpi is not None else None
    series = {}
    for name in PATH_VARS:
        b_path = _path(base_tpi.get(name), count)
        if b_path is None:
            continue
        r_path = _path(reform_tpi.get(name), count) if reform_tpi is not None else None
        info = describe(name)
        kind = info["kind"]
        points = [
            compare(kind, b_path[t], r_path[t] if r_path else None,
                    base_y[t] if base_y else None, reform_y[t] if reform_y else None)
            for t in range(len(b_path))
        ]
        steady = compare(kind, _num(base_ss.get(name)),
                         _num(reform_ss.get(name)) if reform_ss is not None else None,
                         _num(base_ss.get("Y")), _num(reform_ss.get("Y")) if reform_ss is not None else None)
        series[name] = {
            "label": info["label"], "short": info["short"], "kind": kind,
            "value_unit": steady["value_unit"], "change_unit": steady["change_unit"],
            "baseline": [p["baseline"] for p in points],
            "reform": [p["reform"] for p in points] if r_path else None,
            "change": [p["change"] for p in points] if r_path else None,
            "negative_baseline": any(p["negative_baseline"] for p in points) or steady["negative_baseline"],
            "steady": steady,
        }
    return {"years": [start + t for t in range(count)], "budget_window": BUDGET_WINDOW, "series": series}


_MISSING_META = ("{run} was solved without the age and income-group metadata the household "
                 "charts need. Run it again to see household outcomes.")


def _household_weights_for(base_meta, reform_meta, comparing):
    """(base_weights, reform_weights, reason): population weights for both runs.

    ``reason`` is a user-facing explanation, and both weights are None, whenever
    the household views cannot be built honestly.
    """
    weights = household_weights(base_meta)
    if weights is None:
        return None, None, _MISSING_META.format(run="This run")
    if not comparing:
        return weights, None, None
    reason = compatible_meta(base_meta, reform_meta)
    if reason:
        return None, None, reason
    reform_weights = household_weights(reform_meta)
    if reform_weights is None:
        return None, None, _MISSING_META.format(run="The reform run")
    return weights, reform_weights, None


def _scenario_views(matrix, weights, scale):
    """The three weighted views of one run's age x group matrix, in display units."""
    by_age, by_group, overall = weighted_profiles(matrix, weights)
    s_count, j_count = len(matrix), len(matrix[0])
    return {
        "by_age": [v * scale for v in by_age],
        "by_age_group": [[matrix[s][j] * scale for s in range(s_count)] for j in range(j_count)],
        "by_group": [v * scale for v in by_group],
        "raw_by_group": by_group,
        "raw_overall": overall,
    }


def _household_entry(name, base_m, reform_m, weights, reform_weights):
    """Report entry for one household variable: profiles, group changes, overall."""
    info = describe(name)
    kind = info["kind"]
    scale = 100.0 if kind == "rate" else 1.0
    base_v = _scenario_views(base_m, weights, scale)
    entry = {"label": info["label"], "short": info["short"], "kind": kind,
             "value_unit": PERCENT if kind == "rate" else MODEL_UNITS}
    for view in ("by_age", "by_age_group", "by_group"):
        entry[view] = {"baseline": base_v[view]}
    if reform_m is None:
        entry["overall"] = compare(kind, base_v["raw_overall"])
        return entry
    reform_v = _scenario_views(reform_m, reform_weights, scale)
    for view in ("by_age", "by_age_group", "by_group"):
        entry[view]["reform"] = reform_v[view]
    entry["group_change"] = [compare(kind, b, r) for b, r in zip(base_v["raw_by_group"], reform_v["raw_by_group"])]
    entry["overall"] = compare(kind, base_v["raw_overall"], reform_v["raw_overall"])
    return entry


def _households(base_ss, reform_ss, base_meta, reform_meta):
    """(entries, reason): weighted household views, or None with the reason why not."""
    comparing = reform_ss is not None
    weights, reform_weights, reason = _household_weights_for(base_meta, reform_meta, comparing)
    if reason:
        return None, reason
    s_count, j_count = int(base_meta["S"]), int(base_meta["J"])
    out = {}
    for name in HOUSEHOLD_VARS:
        base_m = _age_group(base_ss.get(name), s_count, j_count)
        reform_m = _age_group(reform_ss.get(name), s_count, j_count) if comparing else None
        if base_m is None or (comparing and reform_m is None):
            continue
        out[name] = _household_entry(name, base_m, reform_m, weights, reform_weights)
    return out, None


def _diagnostics(ss):
    values = {name: _max_abs(ss.get(name)) for name in DIAGNOSTIC_VARS if name in ss}
    if not values:
        return None
    return {
        "values": values,
        "tolerance": CONVERGENCE_TOLERANCE,
        "converged": all(v <= CONVERGENCE_TOLERANCE for v in values.values()),
    }


def build_report(base, reform=None):
    """Assemble the Results payload from one or two loaded runs.

    ``base``/``reform`` are dicts with keys ss, tpi (or None) and meta (or None).
    """
    base_ss, base_meta = base["ss"], base.get("meta") or {}
    reform_ss = reform["ss"] if reform else None
    reform_meta = (reform.get("meta") or {}) if reform else None
    base_gdp = _num(base_ss.get("Y"))
    reform_gdp = _num(reform_ss.get("Y")) if reform_ss is not None else None
    has_path = base.get("tpi") is not None and (reform is None or reform.get("tpi") is not None)

    report = {
        "mode": "compare" if reform else "single",
        "analysis": "transition" if has_path else "steady",
        "meta": {
            "complete": meta_complete(base_meta) and (reform is None or meta_complete(reform_meta)),
            "start_year": base_meta.get("start_year"),
            "T": base_meta.get("T"),
            "S": base_meta.get("S"),
            "J": base_meta.get("J"),
            "ages": base_meta.get("ages"),
            "group_labels": base_meta.get("group_labels"),
            "lambdas": base_meta.get("lambdas"),
            # the same S x J population weights the household blocks use, so the
            # Explore view aggregates exactly as the report does
            "weights": {
                "baseline": household_weights(base_meta),
                "reform": household_weights(reform_meta) if reform else None,
            },
        },
        "catalog": catalog(sorted(base_ss.keys()), base_ss, base_meta),
        "summary": _block(SUMMARY_VARS, base_ss, reform_ss, base_gdp, reform_gdp),
        "macro": _block(MACRO_VARS, base_ss, reform_ss, base_gdp, reform_gdp),
        "prices": _block(PRICE_VARS, base_ss, reform_ss, base_gdp, reform_gdp),
        "fiscal": _block(FISCAL_VARS, base_ss, reform_ss, base_gdp, reform_gdp),
        "diagnostics": {"baseline": _diagnostics(base_ss),
                        "reform": _diagnostics(reform_ss) if reform_ss is not None else None},
        "transition": None,
    }
    if has_path:
        report["transition"] = _paths(base["tpi"], reform["tpi"] if reform else None,
                                      base_ss, reform_ss, base_meta)
    households, reason = _households(base_ss, reform_ss, base_meta, reform_meta)
    report["households"] = households
    report["households_reason"] = reason
    return report

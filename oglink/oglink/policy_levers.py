"""Generic, resource/industry-agnostic policy levers for OG-Core scenarios.

Built energy-first but designed to generalize to other CLEWS resources (agriculture, land, water, ...)
AND to any onboarded OG model — single-industry or multi-industry, any count, any ordering, any country.
Two families, both using EXISTING OG-Core params (NO model change):

  * `set_investment_incentive` — bias PRIVATE capex in an industry (by INDEX) by lowering its cost of
    capital (investment tax credit `inv_tax_credit`, accelerated tax depreciation `delta_tau`, and/or a
    corporate-tax `tau_b` multiplier).
  * `route_revenue` — direct a revenue stream (%-GDP path) to transfers / public investment / govt
    consumption / deficit.

Industry identity is NOT hardcoded. OG-Core carries only `p.M` (the industry COUNT) — no names, no
resource tags. Names come from the country's calibration (its PROD_DICT ordering); resource->index tags
are DECLARED by the country config (e.g. `contract.Concordance.energy_industry_index`). So the catalog
is built per-onboarded-model by `industry_registry(p, names=, resource_index=)`, and the levers act on
an integer index validated against `p.M`. Single-industry (M=1) models have no separable sectors:
resource targeting is unavailable there (energy etc. must enter as a consumption good or an economy-wide
TFP/tax wedge on the one aggregate).
"""
from __future__ import annotations

import numpy as np


def _n_industries(p):
    return int(getattr(p, "M", np.asarray(p.Z).shape[1]))


def industry_registry(p, *, names=None, resource_index=None):
    """Build the industry registry from the ONBOARDED model (derived, not hardcoded).

    `names`: ordered industry names of length p.M (e.g. the country's ``list(PROD_DICT)``); defaults to
    ``industry_0..M-1`` if the model doesn't declare them. `resource_index`: a ``{resource: index}`` map
    the country DECLARES (e.g. ``{"energy": concordance.energy_industry_index}``) — because OG-Core has
    no resource concept of its own. Returns a dict describing this model's industry structure; a
    single-industry model reports ``single_industry=True`` and no targetable resources.
    """
    n = _n_industries(p)
    names = list(names) if names is not None else [f"industry_{i}" for i in range(n)]
    if len(names) != n:
        raise ValueError(f"names has length {len(names)} but the model has M={n} industries")
    resource_index = {k: int(v) for k, v in dict(resource_index or {}).items() if 0 <= int(v) < n}
    return {
        "n": n,
        "single_industry": n == 1,
        "names": names,
        "name_to_index": {nm: i for i, nm in enumerate(names)},
        "resource_index": resource_index,
        "targetable_resources": ([] if n == 1 else sorted(resource_index)),
    }


def resolve_industry(industry, registry):
    """Resolve an int index or a name/resource string to a column index, using a model-derived
    `industry_registry`. Raises with an actionable message for a single-industry model or an
    undeclared resource."""
    n = registry["n"]
    if isinstance(industry, (int, np.integer)):
        if not 0 <= int(industry) < n:
            raise ValueError(f"industry index {industry} out of range [0,{n}) for this model")
        return int(industry)
    if industry in registry["name_to_index"]:
        return registry["name_to_index"][industry]
    if industry in registry["resource_index"]:
        return registry["resource_index"][industry]
    if registry["single_industry"]:
        raise ValueError(
            f"single-industry (M=1) model has no separate '{industry}' sector to target; represent "
            "this resource as a consumption good or an economy-wide TFP/tax wedge instead.")
    raise ValueError(
        f"'{industry}' is not a known industry/resource for this model. Industries: {registry['names']}; "
        f"declared resources: {sorted(registry['resource_index'])}. Declare it in the country config "
        "(e.g. concordance.energy_industry_index) or pass its index.")


def _as_TS_M(arr, TpS, M):
    a = np.array(arr, dtype=float)
    if a.shape == (TpS, M):
        return a
    return np.broadcast_to(np.atleast_2d(a), (TpS, M)).copy()


def set_investment_incentive(p, industry_index, *, inv_tax_credit=None, delta_tau=None,
                             tau_b_mult=None, phase_years=None):
    """Bias PRIVATE capex in industry ``industry_index`` (an int; resolve names via
    `resolve_industry`/`industry_registry` first) by lowering its cost of capital, over the first
    ``phase_years`` periods (or all if None). Sets existing per-industry (T+S, M) firm-tax params:
    inv_tax_credit (subsidy), delta_tau (accelerated depreciation), tau_b_mult (scale the CIT).
    Pure param mutation (duck-typed p)."""
    Z = np.asarray(p.Z)
    TpS, M = Z.shape[0], Z.shape[1]
    m = int(industry_index)
    if not 0 <= m < M:
        raise ValueError(f"industry_index {m} out of range [0,{M}); resolve a name to an index first")
    end = TpS if phase_years is None else min(int(phase_years), TpS)
    prov = {"m": m, "phase_years": end}
    if inv_tax_credit is not None:
        itc = _as_TS_M(p.inv_tax_credit, TpS, M); itc[:end, m] = float(inv_tax_credit)
        p.inv_tax_credit = itc; prov["inv_tax_credit"] = float(inv_tax_credit)
    if delta_tau is not None:
        dt = _as_TS_M(p.delta_tau, TpS, M); dt[:end, m] = float(delta_tau)
        p.delta_tau = dt; prov["delta_tau"] = float(delta_tau)
    if tau_b_mult is not None:
        tb = _as_TS_M(p.tau_b, TpS, M); tb[:end, m] = tb[:end, m] * float(tau_b_mult)
        p.tau_b = tb; prov["tau_b_mult"] = float(tau_b_mult)
    return prov


def set_capital_intensity(p, industry_index, *, gamma_target=None, gamma_scale=None,
                          labor_share_floor=0.05):
    """Raise (or set) industry ``industry_index``'s capital share ``gamma[m]`` -- a PERMANENT,
    time-invariant STRUCTURAL shift (OG-Core's ``gamma`` is a length-M vector, NOT time-varying).

    This is a factor-SHARE / production-technology shock -- it raises the share of industry m's value
    added paid to capital and lowers labor's residual share. It is NOT an "inject/attract capital" dial.
    Because gamma is a Cobb-Douglas exponent (epsilon=1), raising it re-weights the industry toward
    capital; for a small, demand-inelastic energy good that LOWERS its unit cost, and via the firm
    identity K_m = gamma_m * p_m * Y_m / rho (capital's revenue share = gamma) the energy CAPITAL stock
    can FALL even as the share rises, with the economy-wide cost of capital rho ~unchanged. So this lever
    does NOT pull capital into energy and does NOT raise r; its real effects are
    on the energy PRICE and the capital/labor income split. To draw capital INTO energy (the capex-heavy-
    generation "crowding-out" story), use ``set_investment_incentive``: an ITC lowers the cost of capital
    rho (gamma is ABSENT from ``firm.get_cost_of_capital``), shifting capital demand out at the going r.

    Pass exactly one of:
      * ``gamma_target`` -- the new absolute capital share for industry m;
      * ``gamma_scale``  -- a multiplier on the current ``gamma[m]`` (e.g. a CLEWS-derived
        reform/base capital-cost-share ratio; see ``signals.capital_intensity_ratio``).

    Labor's share is the RESIDUAL ``1 - gamma - gamma_g`` in OG-Core's CES/Cobb-Douglas production
    function -- it is NOT a separate parameter -- so raising ``gamma[m]`` lowers labor's share
    automatically; there is nothing else to set. OG-Core only range-checks each ``gamma`` element in
    [0, 1]; it does NOT enforce ``gamma + gamma_g <= 1``, so an over-large shift would silently drive
    the labor exponent ``1 - gamma - gamma_g`` to <= 0 and break the production function. This
    HARD-BLOCKS any shift that would leave the residual labor share below ``labor_share_floor``
    (default 0.05). Pure param mutation (duck-typed ``p``); returns provenance."""
    if (gamma_target is None) == (gamma_scale is None):
        raise ValueError("set_capital_intensity: pass exactly one of gamma_target / gamma_scale")
    g = np.array(p.gamma, dtype=float)                 # 1-D length M (firm.py indexes p.gamma[m])
    M = g.shape[0]
    m = int(industry_index)
    if not 0 <= m < M:
        raise ValueError(f"industry_index {m} out of range [0,{M}); resolve a name to an index first")
    gamma_old = float(g[m])
    gamma_g_m = float(np.asarray(p.gamma_g, dtype=float)[m])
    gamma_new = float(gamma_target) if gamma_target is not None else gamma_old * float(gamma_scale)
    if not 0.0 <= gamma_new <= 1.0:
        raise ValueError(f"set_capital_intensity: gamma_new={gamma_new:.4f} outside [0,1]")
    labor_new = 1.0 - gamma_new - gamma_g_m
    if labor_new < labor_share_floor:
        raise ValueError(
            f"set_capital_intensity: gamma_new={gamma_new:.4f} + gamma_g={gamma_g_m:.4f} would leave a "
            f"residual labor share {labor_new:.4f} < floor {labor_share_floor} (OG-Core does NOT guard "
            f"this; a <=0 labor exponent breaks the production function). Lower the shift, or pass a "
            f"smaller labor_share_floor only if you mean it.")
    g[m] = gamma_new
    p.gamma = g
    return {"m": m, "gamma_old": gamma_old, "gamma_new": gamma_new, "gamma_g": gamma_g_m,
            "labor_share_old": 1.0 - gamma_old - gamma_g_m, "labor_share_new": labor_new,
            "mode": "target" if gamma_target is not None else "scale"}


def route_revenue(p, pct_gdp_path, *, to="transfers", fill_ss_tail=True):
    """Add an EXOGENOUS (caller-supplied) %-of-GDP spending path to a fiscal destination: 'transfers'
    (alpha_T), 'public_investment' (alpha_I -> K_g), 'government_consumption' (alpha_G), or 'deficit'
    (no-op -> the budget closure / debt-ratio rule absorbs it). Industry-agnostic. Returns provenance.

    NOT a revenue recycle. Under OG-Core's default closure (budget_balance=False) alpha_T/alpha_I/alpha_G
    drive SPENDING, and this path has NO link to collected revenue (total_tax_revenue), so a positive
    bump is a DEBT-FINANCED spending increase, not a neutral recycle. For a revenue-neutral transfer
    recycle, use ``channels.recycle_via_transfers`` (which estimates the revenue base). The 'deficit'
    destination is the one neutral option here: no param change, the debt-ratio rule absorbs the stream.
    """
    valid = {"transfers": "alpha_T", "public_investment": "alpha_I",
             "government_consumption": "alpha_G", "deficit": None}
    if to not in valid:
        raise ValueError(f"unknown revenue destination '{to}'; choose from {sorted(valid)}")
    attr = valid[to]
    if attr is None:
        return {"to": to, "param": None, "note": "budget closure absorbs revenue (debt-ratio rule applies)"}
    base = np.array(getattr(p, attr), dtype=float)
    n = base.shape[0]
    bump = np.array(pct_gdp_path, dtype=float)
    if bump.shape[0] < n:
        bump = np.concatenate([bump, np.full(n - bump.shape[0], bump[-1] if fill_ss_tail else 0.0)])
    setattr(p, attr, base + bump[:n])
    return {"to": to, "param": attr, "mean_pct_gdp": float(np.mean(bump[:10]))}

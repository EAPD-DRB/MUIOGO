"""Inject a CLEWS energy-price signal into an OG-Core ``Specifications`` object,
and read back the household demand response.

Theory anchor (OG-Core ``households.md``, EqHH_ciDem2)::

    c_{i,j,s,t} = alpha_i * ( (1 + tau_c_{i,t}) p_{i,t} / p_t )^{-1} * c_{j,s,t} + c_min_i

Households already respond to the *effective* price ``(1 + tau_c_i) p_i`` of the
energy consumption good -- unit-elastic above a Stone-Geary subsistence floor.
The energy good's price ``p_i = sum_m pi_{i,m} p_m`` is built from the energy
*industry's* output price, which is its unit cost and moves only through the
industry TFP ``Z_m`` (``firms.md``, EqFirmFOC_K/L). Three ways to move the
effective energy price the household faces, in increasing rigor:

  (A) tau_c route  [available now, demand-side, cleanest price wedge]:
      raise tau_c on the energy consumption good so the consumer price rises by
      the CLEWS-implied ratio. Routes through government revenue -> must be
      recycled (revenue-neutral) or it becomes a de-facto energy tax.

  (B) Z route  [available now, supply-side]:
      lower the energy *industry* TFP Z_m so its equilibrium price p_m (hence p_i)
      rises. Conflates "costlier" with "less productive"; use deliberately.

  (C) energy-as-CES-input  [structural extension, NOT in shipped OG-Core]:
      add energy as a priced production input so cost passes through endogenously
      without a TFP or tax proxy. The rigor endpoint -- a separate OG-Core PR.

These functions mutate and return ``p`` (duck-typed: anything with ``.tau_c``,
``.Z``, ``.alpha_T`` array attributes). They do NOT run the model, so they are
unit-testable without ogcore. Read-back helpers take TPI output arrays so they
stay decoupled from the solver.
"""
from __future__ import annotations

import numpy as np


def _as_path(value, T: int) -> np.ndarray:
    """Broadcast a scalar or 1-D series to a length-T path (forward-filling short input)."""
    arr = np.atleast_1d(np.asarray(value, dtype=float))
    if arr.shape[0] == 1:
        return np.full(T, arr[0])
    if arr.shape[0] >= T:
        return arr[:T]
    out = np.empty(T)
    out[: arr.shape[0]] = arr
    out[arr.shape[0] :] = arr[-1]  # forward-fill, matching OG-Core's extrapolation convention
    return out


# --- Route (A): consumer price wedge via tau_c -----------------------------------

def effective_price_to_tau_c(price_ratio, tau_c_base):
    """tau_c that scales the *effective* consumer price by ``price_ratio``.

    (1 + tau_c_new) = price_ratio * (1 + tau_c_base); ratio 1.10 == +10% energy price.
    """
    return price_ratio * (1.0 + tau_c_base) - 1.0


def set_energy_consumption_wedge(p, i_energy: int, price_ratio_by_t, *, recycle: bool = False):
    """Make households face a higher energy price via tau_c on good ``i_energy``.

    ``p.tau_c`` is (T, I); ``price_ratio_by_t`` is the reform/base effective-price
    ratio over time (scalar or path). Returns (p, diagnostics).

    The induced consumption-tax revenue is REAL modeled revenue that, absent recycling,
    accrues to government (funds G / reduces debt under the default closure) -- so for a
    pure price signal it should be recycled, or it acts as a de-facto energy tax.
    Revenue-neutral recycling uses ``channels.recycle_via_transfers`` (a first-order,
    baseline-quantity estimate); ``recycle`` here only records intent.
    """
    tau_c = np.array(p.tau_c, dtype=float)
    T = tau_c.shape[0]
    ratio = _as_path(price_ratio_by_t, T)
    base = tau_c[:, i_energy].copy()
    tau_c[:, i_energy] = effective_price_to_tau_c(ratio, base)
    p.tau_c = tau_c
    return p, {
        "route": "tau_c",
        "i_energy": i_energy,
        "tau_c_base": base,
        "tau_c_new": tau_c[:, i_energy].copy(),
        "price_ratio": ratio,
        "recycle_intent": recycle,
    }


# --- Route (B): supply-side via energy-industry TFP ------------------------------

def set_energy_industry_tfp(p, m_energy: int, cost_ratio_by_t):
    """Raise the energy *industry* output price by lowering its TFP Z_m.

    ``p.Z`` is (T+S, M). ``cost_ratio`` > 1 (energy costlier) divides Z[:, m_energy]
    so the firm's unit cost / price p_m rises. First-order: the equilibrium p_m move
    is not exactly the Z move (it is a GE outcome), so calibrate against the realized
    p_i after a solve. Returns (p, diagnostics).
    """
    Z = np.array(p.Z, dtype=float)
    TpS = Z.shape[0]
    ratio = _as_path(cost_ratio_by_t, TpS)
    base = Z[:, m_energy].copy()
    Z[:, m_energy] = base / ratio
    p.Z = Z
    return p, {"route": "Z", "m_energy": m_energy, "Z_base": base, "Z_new": Z[:, m_energy].copy(),
               "cost_ratio": ratio}


# --- Read-back: the demand response and its incidence ---------------------------

def energy_demand_response(base_C_i, reform_C_i, i_energy: int):
    """Percent change in aggregate energy-good consumption, base -> reform.

    ``*_C_i`` are (T, I) aggregate consumption-by-good arrays (OG-Core TPI ``C_i``).
    Returns a length-T array of percent differences for the energy good.
    """
    b = np.asarray(base_C_i, dtype=float)[:, i_energy]
    r = np.asarray(reform_C_i, dtype=float)[:, i_energy]
    b = np.where(b == 0, np.nan, b)  # guard divide-by-zero (nan, not inf, so np.nanmean tolerates it)
    return 100.0 * (r - b) / b


def energy_demand_response_by_group(c_i_base, c_i_reform, i_energy: int, n_periods: int = 10):
    """% change in energy-good consumption by lifetime-income group J.

    ogcore TPI ``c_i`` is (T, I, S, J). Averages over the first ``n_periods`` periods
    and over ages S, returning a length-J array. This is the incidence read-out only
    OG-Core can give -- even with homothetic preferences it varies across J through the
    general-equilibrium and fiscal channels.
    """
    b = np.asarray(c_i_base, dtype=float)[:n_periods, i_energy]    # (n, S, J)
    r = np.asarray(c_i_reform, dtype=float)[:n_periods, i_energy]
    bm, rm = b.mean(axis=(0, 1)), r.mean(axis=(0, 1))             # (J,)
    return 100.0 * (rm - bm) / bm


def energy_budget_share_by_group(c_i_base, p_i_base, tau_c, i_energy: int, t: int = 0):
    """Energy's share of consumption expenditure by income group J at period ``t``.

    ``c_i_base`` is (T, I, S, J); ``p_i_base`` is (T, I) good prices; ``tau_c`` is
    (T, I) consumption-tax rates. Returns a length-J array (averaged over ages S).
    Under Cobb-Douglas (c_min=0) this is ~uniform == alpha_energy; a nonzero energy
    c_min makes it fall with income, which is the differential-exposure incidence
    channel (energy as a necessity).
    """
    ci = np.asarray(c_i_base, dtype=float)[t]                      # (I, S, J)
    pi = np.asarray(p_i_base, dtype=float)[t]                      # (I,)
    tc = np.asarray(tau_c, dtype=float)[t]                         # (I,)
    spend = (1.0 + tc)[:, None, None] * pi[:, None, None] * ci     # (I, S, J)
    share = spend[i_energy] / spend.sum(axis=0)                    # (S, J)
    return share.mean(axis=0)                                      # (J,)

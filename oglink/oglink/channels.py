"""The integration channels: plain functions, one per economically-grounded transform. Each takes the
coupling context ``ctx`` first (the mutable analogue of OG-Core's ``p``), then explicit keyword levers
with self-describing names, reads/mutates ``ctx``, and records its own provenance via ``ctx.log``. All
transforms operate on a duck-typed Specifications (numpy attributes), so they are unit-testable without
ogcore. A channel takes the ALREADY-SOURCED value it needs (e.g. a price ratio); WHERE that value comes
from is the caller's choice, via the signals.* helpers. og->clews channels carry an ``emit_`` prefix and
run AFTER the reform solve.

Verified OG-Core mechanics (ogcore 0.16.x): G=alpha_G*Y, TR=alpha_T*Y, I_g=alpha_I*Y -> K_g -> CES
production; the consumption-tax wedge (1+tau_c_i)p_i enters the demand FOC, the budget, the composite
price, and books cons_tax_revenue. Tail convention: parameters are length (T+S); indices T:T+S are the
STEADY STATE anchoring TPI's terminal condition -- a PERMANENT policy fills the SS tail, a TEMPORARY
transition tapers to baseline.
"""
from __future__ import annotations

import numpy as np

from . import health_profile, policy_levers, signals
from .signals import _fit


def _recycle_via_transfers(ctx, i_good: int, dtau_path) -> float | None:
    """Return the energy-tax revenue to households as a lump-sum transfer (TR=alpha_T*Y), isolating the
    price/substitution effect from the fiscal effect. First-order: revenue is estimated on BASELINE
    quantities, slightly overstating reform revenue. Fills the SS tail. A sign-flipping recycle is
    floored at alpha_T>=0 (a transfer, not a tax).

    Args:
        ctx (CouplingState): reads base_tpi; mutates og_reform.alpha_T.
        i_good (int): the energy good's index.
        dtau_path (array_like): the per-period tau_c change to recycle.
    Returns:
        float or None: realized recycle (post-floor), as a share of GDP; None if no baseline.
    """
    b = ctx.base_tpi
    if b is None:
        return None
    p = ctx.og_reform
    T = p.T
    Ci = np.asarray(b["C_i"])[:T, i_good]
    pi = np.asarray(b["p_i"])[:T, i_good]
    Y = np.asarray(b["Y"])[:T]
    bump = (_fit(dtau_path, T) * pi * Ci) / np.maximum(Y, 1e-12)
    aT = np.asarray(p.alpha_T, dtype=float)
    new_aT = aT + _fit(bump, aT.shape[0])
    if np.any(new_aT < 0):
        print("[guardrail] recycle: bump would push alpha_T < 0 (a lump-sum tax on households); floored "
              "at 0. A negative recycle implies the closure instrument should change.")
        new_aT = np.maximum(new_aT, 0.0)
    p.alpha_T = new_aT
    return float(np.mean((new_aT - aT)[:10]))


def _skip_if_unavailable(ctx, channel: str, *required_ports):
    """Guard for channels that need an energy port (electricity's OG industry/good index). If the
    country's OG aggregation can't isolate the carrier (the concordance left a required port ``None`` --
    e.g. electricity fused with water in one group), record a SKIP in provenance and return that record;
    the caller returns it immediately and mutates nothing. Returns None when all required ports resolve
    (the channel proceeds normally). The concordance is the PER-RUN one discovered in the OG env and
    exported via baseline_meta.json (ctx.concordance) -- it is unavailable whenever the country's solved
    baseline can't isolate electricity as its own industry (e.g. a single-industry calibration, or
    electricity fused with water), so those channels skip."""
    con = ctx.concordance
    if con is None:                          # no baseline exported a concordance -> nothing to couple to
        reason = "no concordance for this run (baseline did not export one)"
        print(f"[skip] {channel}: {reason}")
        return ctx.log(channel, skipped=True, reason=reason)
    missing = {p: con.unavailable.get(p, "unresolved") for p in required_ports
               if getattr(con, p, None) is None}
    if missing:
        reason = "; ".join(f"{p}: {why}" for p, why in missing.items())
        print(f"[skip] {channel}: {reason}")
        return ctx.log(channel, skipped=True, reason=reason)
    return None


# --- #1 energy price -> household demand (+ incidence) · clews->og ---------------

def energy_price(ctx, price_ratio, *, energy_subsistence_floor=0.0, recycle_revenue_to_transfers=False):
    r"""Energy price -> household demand + incidence (clews->og).

    A higher energy price reaches households as a consumption-tax wedge on the energy good; demand
    falls, the cost of living rises, and with a subsistence floor the incidence is regressive -- OG has
    no energy in production, so this is the only door.

    .. math:: 1 + \tau^{c,new}_{t,e} = r_t \,(1 + \tau^{c,base}_{t,e})

    where :math:`r_t` is ``price_ratio``. Mutates tau_c[:, energy] always; c_min[energy] if a floor is
    set; alpha_T if revenue is recycled.

    Args:
        ctx (CouplingState): mutates og_reform; reads base_tpi for the floor guard / recycling.
        price_ratio (float or array_like): the ALREADY-SOURCED reform/base price ratio of the energy
            good -- a scalar (e.g. 1.20 for a controlled +20%, applied undiluted) or a per-period path
            from ``signals.energy_price_ratio`` (which dilutes by electricity's share of the good).
        energy_subsistence_floor (float): if >0, sets c_min[energy] so energy is a necessity (drives
            the regressive incidence). Must be below every group's baseline energy consumption.
        recycle_revenue_to_transfers (bool): rebate the tau_c revenue lump-sum via alpha_T.
    Returns:
        dict: provenance -- tau_c_energy_0, dtau_mean, energy_subsistence_floor, recycled_pct_gdp.
    """
    if (skip := _skip_if_unavailable(ctx, "energy_price", "energy_good_index")) is not None:
        return skip
    if price_ratio is None:                      # no ratio sourced -- e.g. energy_price_ratio returned None
        reason = "no energy price ratio sourced (electricity's value-share of the energy good unresolved)"
        print(f"[skip] energy_price: {reason}")
        return ctx.log("energy_price", skipped=True, reason=reason)
    i_e = ctx.concordance.energy_good_index
    p = ctx.og_reform
    tau = np.array(p.tau_c, dtype=float)
    before = tau[:, i_e].copy()
    r = _fit(price_ratio, tau.shape[0])
    if not np.all(r > 0):                        # r<=0 inverts the wedge to <= -100% (free/negative gross
        raise ValueError(                        # price): a degenerate source, not a real price signal.
            f"energy_price: price ratio has non-positive entries (min={float(np.min(r)):.4g}); "
            "r*(1+tau)-1 would set a <= -100% consumption wedge on the energy good. This means a degenerate "
            "price source (an all-slack/empty marginal, or a CLEWS horizon ending before og_start_year so "
            "the aligned path is all-zero). Check the energy-price source and alignment.")
    tau[:, i_e] = r * (1.0 + tau[:, i_e]) - 1.0  # permanent: full tail
    p.tau_c = tau
    dtau = tau[:, i_e] - before
    if energy_subsistence_floor > 0:
        if ctx.base_tpi is not None:
            base_min = float(np.asarray(ctx.base_tpi["c_i"])[:, i_e].min())
            if energy_subsistence_floor > 0.5 * base_min:
                print(f"[guardrail] energy_subsistence_floor={energy_subsistence_floor} exceeds 50% of the "
                      f"minimum baseline per-household energy consumption ({base_min:.4f}); risks negative "
                      f"consumption / a broken solve. Calibrate it lower.")
        cm = np.array(p.c_min, dtype=float)
        cm[i_e] = energy_subsistence_floor
        p.c_min = cm
    recycled = (_recycle_via_transfers(ctx, i_e, dtau[:p.T]) if recycle_revenue_to_transfers else None)
    return ctx.log("energy_price", tau_c_energy_0=float(tau[0, i_e]),
                   dtau_mean=float(dtau[:10].mean()), energy_subsistence_floor=energy_subsistence_floor,
                   recycled_pct_gdp=recycled)


# --- #1b energy price via the electricity industry's TFP (Option A) · clews->og ---

def energy_price_tfp(ctx, price_ratio):
    r"""Energy price via electricity's TFP (clews->og; Option A -- the structural alternative to the
    ``energy_price`` ``tau_c`` wedge).

    Rather than hand-applying the price to a consumption-tax wedge, lower the electricity INDUSTRY's TFP
    ``Z`` so OG-Core *produces* a higher electricity price ``p_m`` endogenously. The model's own Leontief
    ``io_matrix`` then carries ``p_m`` into the energy consumption good's price -- WITH the general-
    equilibrium feedback (``r``, ``w``, and electricity's own ``K``/``L``/``Y``) that the ``tau_c`` wedge
    discards. Since ``p_m`` is proportional to ``1/Z`` (holding factor prices), ``Z[:, e] /= price_ratio``
    targets a ``price_ratio`` rise in the electricity producer price; the REALIZED price differs slightly
    via GE, so report it from the solve. Like ``tau_c`` this still reaches households via CONSUMPTION only
    (OG-Core has no inter-industry intermediates); for a cost-push to OTHER industries see
    ``energy_cost_push``.

    Args:
        ctx (CouplingState): mutates the energy industry's column of ``og_reform.Z``.
        price_ratio (float or array_like): the ALREADY-SOURCED reform/base electricity price ratio.
    Returns:
        dict: provenance -- target_price_ratio_0, z_multiplier_0, industry_index (or a skip record).
    """
    if (skip := _skip_if_unavailable(ctx, "energy_price_tfp", "energy_industry_index")) is not None:
        return skip
    if price_ratio is None:
        reason = "no energy price ratio sourced (electricity's value-share of the energy good unresolved)"
        print(f"[skip] energy_price_tfp: {reason}")
        return ctx.log("energy_price_tfp", skipped=True, reason=reason)
    m = ctx.concordance.energy_industry_index
    p = ctx.og_reform
    Z = np.array(p.Z, dtype=float)
    r = _fit(price_ratio, Z.shape[0])
    if not np.all(r > 0):
        raise ValueError(
            f"energy_price_tfp: price ratio has non-positive entries (min={float(np.min(r)):.4g}); "
            "Z /= ratio would be non-positive (negative TFP). Check the energy-price source/alignment.")
    Z[:, m] = Z[:, m] / r                        # lower TFP -> higher p_m (p_m ~ 1/Z); permanent: full tail
    p.Z = Z
    return ctx.log("energy_price_tfp", target_price_ratio_0=float(r[0]),
                   z_multiplier_0=float(1.0 / r[0]), industry_index=int(m))


# --- #1c electricity cost-push across industries (Option A', a reduced-form proxy) · clews->og ---

def energy_cost_push(ctx, price_ratio, electricity_intensity):
    r"""Electricity cost-push across industries (clews->og; Option A' -- a reduced-form PROXY for the
    inter-industry intermediate-input channel OG-Core's value-added production lacks).

    A higher electricity price raises every electricity-USING industry j's unit cost by ~``phi_j (r-1)``,
    where ``phi_j`` is electricity's share of j's input costs (from the country SAM, via
    ``aggregation.input_intensity``). Injected as a per-industry TFP haircut ``Z[:, j] /= (1 +
    phi_j (r-1))`` -- since ``p_j ~ 1/Z_j``, this raises ``p_j`` by ~``phi_j (r-1)``. It reaches households
    through the higher price of EVERY electricity-intensive good, so it is the broadest-footprint of the
    three transmissions. ILLUSTRATIVE: ``phi_j`` and the unit pass-through are calibrated weights, not a
    structural equation in OG-Core (that is Option B -- a real M x M use matrix + a firm-side rewrite).

    Args:
        ctx (CouplingState): mutates ``og_reform.Z`` for every industry with ``phi_j > 0``.
        price_ratio (float or array_like): the ALREADY-SOURCED reform/base electricity price ratio.
        electricity_intensity (array_like or None): the M-vector ``phi_j`` (PROD_DICT order). None -> skip.
    Returns:
        dict: provenance -- phi, max_haircut_0, n_industries_hit (or a skip record).
    """
    if electricity_intensity is None:
        reason = "no electricity input-intensity vector (SAM/PROD_DICT unavailable for this country)"
        print(f"[skip] energy_cost_push: {reason}")
        return ctx.log("energy_cost_push", skipped=True, reason=reason)
    p = ctx.og_reform
    Z = np.array(p.Z, dtype=float)
    M = Z.shape[1]
    phi = np.asarray(electricity_intensity, dtype=float)
    if phi.shape != (M,):
        raise ValueError(f"energy_cost_push: electricity_intensity has shape {phi.shape}, expected ({M},) "
                         "-- it must align to the model's M industries (PROD_DICT order).")
    r = _fit(price_ratio, Z.shape[0])
    if not np.all(r > 0):
        raise ValueError(
            f"energy_cost_push: price ratio has non-positive entries (min={float(np.min(r)):.4g}). "
            "Check the energy-price source/alignment.")
    push = 1.0 + np.outer(r - 1.0, phi)          # (T+S, M): per-industry cost-push factor 1 + phi_j (r-1)
    if not np.all(push > 0):
        raise ValueError("energy_cost_push: a cost-push factor went non-positive (phi*(r-1) <= -1); "
                         "the price drop is too large for these intensities.")
    p.Z = Z / push                               # Z[:, j] /= (1 + phi_j (r-1)); permanent: full tail
    haircut0 = 1.0 - 1.0 / push[0]
    return ctx.log("energy_cost_push", phi=phi.tolist(), max_haircut_0=float(np.max(haircut0)),
                   n_industries_hit=int(np.count_nonzero(phi > 0)))


# --- #2 public-infrastructure capex -> public capital (alpha_I -> K_g) · clews->og ---

def investment(ctx, capex_pct_gdp, *, use_baseline_spending=False, persist_into_steady_state=False):
    """Public-infrastructure (grid/T&D) capex -> public investment (clews->og).

    alpha_I -> K_g lifts every industry's productivity via gamma_g, so only genuinely public infra
    belongs here. Private generation capex is NOT this channel -- its macro effect is the energy
    cost-push, and a capex subsidy is ``energy_capex``.

    Args:
        ctx (CouplingState): mutates og_reform.alpha_I (or alpha_bs_I).
        capex_pct_gdp (array_like): the ALREADY-SOURCED finite %-of-GDP capex flow path
            (``signals.public_capex_pct_gdp``), zero after the CLEWS horizon.
        use_baseline_spending (bool): if True, write alpha_bs_I instead of alpha_I -- a no-op unless
            OG-Core's baseline_spending=True, so the default (False) is the live path.
        persist_into_steady_state (bool): carry the flow into the SS tail (rare; permanent infra).
            Default False -- a transition build must taper to baseline in the SS.
    Returns:
        dict: provenance -- target, scope, persist, cumulative_pct_gdp, peak_pct_gdp.
    """
    p = ctx.og_reform
    path = np.asarray(capex_pct_gdp, dtype=float)
    if not np.any(np.abs(path) > 1e-12):
        print("[guardrail] investment: no PUBLIC-infrastructure (grid/T&D) capex delta in this scenario "
              "-- the public-investment channel contributes ~0. Private generation capex is NOT routed "
              "here; its effect belongs to the energy cost-push channel.")
    full = np.zeros(np.asarray(p.alpha_I).shape[0])
    full[:p.T] = path[:p.T]
    if persist_into_steady_state:
        full = _fit(path[:p.T], full.shape[0])
    if np.max(path) > float(np.asarray(p.alpha_I)[0]):
        print(f"[guardrail] investment: peak alpha_I increment {np.max(path):.3f} > baseline alpha_I "
              f"{float(np.asarray(p.alpha_I)[0]):.3f} -- large public-investment shock; check the capex "
              f"source's units.deflator and smoothing.")
    if not use_baseline_spending:
        p.alpha_I = np.asarray(p.alpha_I, dtype=float) + full
        target = "alpha_I"
    else:
        if not bool(getattr(p, "baseline_spending", False)):
            print("[guardrail] investment use_baseline_spending=True writes alpha_bs_I, which OG-Core "
                  "ignores unless baseline_spending=True (currently False) -- this shock will have NO effect.")
        p.alpha_bs_I = np.asarray(p.alpha_bs_I, dtype=float) * (1.0 + full)
        target = "alpha_bs_I"
    return ctx.log("investment", target=target, scope="public_infrastructure",
                   persist=persist_into_steady_state, cumulative_pct_gdp=float(path.sum()),
                   peak_pct_gdp=float(np.max(path)))


# --- #2b generation-mix capital intensity -> energy industry capital share · clews->og ---

def capital_intensity(ctx, energy_capital_share_multiplier=None, *, energy_capital_share_target=None,
                      min_labor_share=0.05):
    """Energy industry's capital share -- a factor-SHARE / production-technology lever (clews->og).

    Raises the energy industry's capital exponent (a permanent, time-invariant shift; labor's share is
    the residual, which falls). This is a factor-share/price lever, NOT crowding-out: for a small,
    demand-inelastic energy good a higher capital share lowers electricity's unit cost, so energy CAPITAL
    need not rise. The capital-DEMAND story is ``energy_capex`` (the ITC), which acts on the cost of
    capital instead. (On PHL's M=8 calibration electricity's capital share is already high, so this
    reform is solved by continuation from the baseline SS -- a cold solve would diverge.)

    Args:
        ctx (CouplingState): mutates the energy industry's capital exponent.
        energy_capital_share_multiplier (float or None): the ALREADY-SOURCED multiplicative shift
            (caller passes ``signals.capital_intensity_ratio(...)['ratio']``).
        energy_capital_share_target (float or None): an absolute new capital share in [0,1]
            (mutually exclusive with the multiplier).
        min_labor_share (float): guardrail -- reject a shift driving the residual labor exponent below this.
    Returns:
        dict: provenance from ``policy_levers.set_capital_intensity`` (gamma_old, gamma_new, labor_share_new).
    """
    if (skip := _skip_if_unavailable(ctx, "capital_intensity", "energy_industry_index")) is not None:
        return skip
    p = ctx.og_reform
    m = ctx.concordance.energy_industry_index
    prov = policy_levers.set_capital_intensity(
        p, m, gamma_target=energy_capital_share_target, gamma_scale=energy_capital_share_multiplier,
        labor_share_floor=min_labor_share)
    if abs(prov["gamma_new"] - prov["gamma_old"]) < 1e-6:
        print("[guardrail] capital_intensity: share shift ~0 -- the reform generation mix is no more "
              "capital-intensive than baseline, so the channel is inert.")
    return ctx.log("capital_intensity", **prov)


# --- #2c energy capex incentive (ITC): cost-of-capital subsidy · policy ----------

def energy_capex(ctx, *, investment_tax_credit_rate=0.20, accelerated_depreciation=None,
                 cit_rate_multiplier=None, phase_in_periods=None):
    """Energy capex incentive (ITC) -> energy capital demand (policy).

    The capital-DEMAND counterpart to ``capital_intensity``: an ITC lowers the energy industry's COST OF
    CAPITAL (it enters firm.get_cost_of_capital; the capital share does not), drawing capital INTO
    energy -- capital REALLOCATION into the energy industry (at a small electricity scale, not
    economy-wide crowding-out), funded via the public budget.

    Args:
        ctx (CouplingState): mutates the energy industry's firm-tax instruments.
        investment_tax_credit_rate (float): the ITC as a fraction of capex; None suppresses it.
        accelerated_depreciation (float or None): a second firm-tax lever (delta_tau); off by default.
        cit_rate_multiplier (float or None): a third lever scaling the energy CIT rate (tau_b); off by default.
        phase_in_periods (int or None): MODEL periods to phase the incentive over; None = permanent.
    Returns:
        dict: provenance from ``policy_levers.set_investment_incentive`` plus the lever label.
    """
    if (skip := _skip_if_unavailable(ctx, "energy_capex", "energy_industry_index")) is not None:
        return skip
    p = ctx.og_reform
    m = ctx.concordance.energy_industry_index
    prov = policy_levers.set_investment_incentive(
        p, m, inv_tax_credit=investment_tax_credit_rate, delta_tau=accelerated_depreciation,
        tau_b_mult=cit_rate_multiplier, phase_years=phase_in_periods)
    prov["lever"] = "investment_tax_credit (cost-of-capital subsidy)"
    return ctx.log("energy_capex", **prov)


# --- #3 carbon price · policy (split: OG tax + CLEWS penalty) --------------------

def carbon_tax(ctx, *, carbon_price_usd_per_tco2=50.0, carbon_per_energy_unit=0.002,
               recycle_revenue_to_transfers=False, allow_illustrative_magnitude=False):
    """Carbon price as an OG consumption-side tax on the household energy good (policy).

    The ad-valorem tau_c add-on = carbon-cost-per-unit-good / price-per-unit-good. The price (USD/tCO2)
    is converted to the OG numeraire via units.deflator; at the default deflator=1.0 the MAGNITUDE is
    illustrative until calibrated. OG has no energy in PRODUCTION, so this prices only HOUSEHOLD energy
    (~1.4% of consumption). The CLEWS-side penalty is ``emit_carbon_penalty`` -- set the price ONCE and
    feed both.

    Args:
        ctx (CouplingState): mutates og_reform.tau_c[:, energy]; reads base_tpi for the good's price.
        carbon_price_usd_per_tco2 (float): the carbon price in USD per tonne CO2.
        carbon_per_energy_unit (float): emission intensity, tCO2 per unit of the OG energy good.
        recycle_revenue_to_transfers (bool): rebate the carbon-tax revenue lump-sum via alpha_T.
        allow_illustrative_magnitude (bool): proceed past the >100% tau_c add-on guard with an
            explicitly illustrative (uncalibrated-deflator) magnitude.
    Returns:
        dict: provenance -- carbon_price_mean, og_base_note, recycled_pct_gdp (if recycled).
    """
    if (skip := _skip_if_unavailable(ctx, "carbon_tax", "energy_good_index")) is not None:
        return skip
    c = ctx.country
    i_e = ctx.concordance.energy_good_index
    p = ctx.og_reform
    cp = _fit(carbon_price_usd_per_tco2, p.T)
    base_pi = (np.asarray(ctx.base_tpi["p_i"])[:p.T, i_e] if ctx.base_tpi is not None
               else np.ones(p.T))
    cp_num = cp * float(getattr(c.units, "deflator", 1.0))      # USD/tCO2 -> numeraire/tCO2
    dtau = cp_num * carbon_per_energy_unit / np.maximum(base_pi, 1e-9)
    if float(dtau.mean()) > 1.0 and not allow_illustrative_magnitude:
        raise ValueError(
            f"carbon_tax: implied mean tau_c add-on {dtau.mean():.2f} (>100%) on the energy good -- the "
            "USD->numeraire deflator (units.deflator) and/or carbon_per_energy_unit are uncalibrated, so "
            "this is not a real ad-valorem rate. Calibrate them, or pass allow_illustrative_magnitude=True.")
    tau = np.array(p.tau_c, dtype=float)
    tau[:, i_e] = tau[:, i_e] + _fit(dtau, tau.shape[0])         # permanent policy: full tail
    p.tau_c = tau
    prov = {"carbon_price_mean": float(cp.mean()),
            "og_base_note": "OG taxes household energy only (~1.4% of consumption); industrial carbon unpriced"}
    if recycle_revenue_to_transfers:
        prov["recycled_pct_gdp"] = _recycle_via_transfers(ctx, i_e, dtau)
    return ctx.log("carbon_tax", **prov)


def emit_carbon_penalty(ctx, *, carbon_price_usd_per_tco2=50.0):
    """Carbon price as a CLEWS EmissionsPenalty artifact (policy; og->clews-style emit).

    The energy-system side of the same carbon price ``carbon_tax`` applies to OG -- set the price ONCE
    and feed both; do not also infer a carbon price from a CLEWS dual back into OG.

    Args:
        ctx (CouplingState): writes clews_inputs['EmissionsPenalty'].
        carbon_price_usd_per_tco2 (float): the carbon price in USD per tonne CO2.
    Returns:
        dict: provenance -- carbon_price_mean.
    """
    c = ctx.country
    p = ctx.og_reform
    cp = _fit(carbon_price_usd_per_tco2, p.T)
    # Validate the species the artifact will name against what the case actually exports (best-effort:
    # None when the export is unreadable). The read path fails loudly on a species mismatch; this WRITE
    # path otherwise wouldn't -- a wrong code would merge into CLEWS as a penalty on a nonexistent
    # species and silently no-op.
    present = signals.emission_species(c.scenario.base_dir) if getattr(c.scenario, "base_dir", "") else None
    known = None if present is None else any(str(s).upper() == str(c.co2_emission).upper() for s in present)
    if known is False:
        print(f"[guardrail] emit_carbon_penalty: species {c.co2_emission!r} is not in the CLEWS "
              f"emissions export (present: {present}) -- the EmissionsPenalty artifact would target a "
              "nonexistent species when merged. Set CountryConfig.co2_emission.")
    ctx.clews_inputs["EmissionsPenalty"] = {
        "region": getattr(c, "clews_region", "RE1"), "emission": c.co2_emission,
        "start_year": c.scenario.og_start_year, "value_by_period": cp.tolist()}
    return ctx.log("emit_carbon_penalty", carbon_price_mean=float(cp.mean()),
                   species_in_export=known)


# --- #4 OG equilibrium rate -> CLEWS DiscountRate · og->clews (post-solve) -------

_OG_RATE_SERIES = {"market_return": "r_p", "firm_rate": "r"}


def emit_discount_rate(ctx, *, og_rate_series="market_return", rate_form="first_decade_mean",
                       clews_region=None):
    """OG equilibrium rate -> CLEWS DiscountRate (og->clews; run AFTER the reform solve).

    Harmonizes the energy model's discount rate to OG's market cost of capital -- not a separate social
    rate.

    Args:
        ctx (CouplingState): reads reform_tpi (REQUIRED, post-solve); writes clews_inputs['DiscountRate'].
        og_rate_series (str): 'market_return' (the household portfolio return r_p) or 'firm_rate' (r).
        rate_form (str): 'first_decade_mean' (a scalar) or 'full_path' (the per-period series).
        clews_region (str or None): the CLEWS region the rate is written for; None -> the country's
            ``clews_region`` (the case's OSeMOSYS region code).
    Returns:
        dict: provenance -- og_rate_series, clews_discount_rate (scalar) or 'path'.
    """
    if ctx.reform_tpi is None:
        raise ValueError("emit_discount_rate is post-solve and needs ctx.reform_tpi (the reform "
                         "equilibrium rate); it was None -- call it after the reform solve.")
    if clews_region is None:
        clews_region = getattr(ctx.country, "clews_region", "RE1")
    rate_key = _OG_RATE_SERIES.get(og_rate_series, og_rate_series)
    r = signals.og_interest_rate(ctx.reform_tpi, rate_key)
    scalar = (rate_form == "first_decade_mean")
    rate = float(np.mean(r[:10])) if scalar else r.tolist()
    ctx.clews_inputs["DiscountRate"] = {"region": clews_region, "rate": rate, "key": rate_key,
                                        "convention": "real; OG market cost of capital; period~annual if S=80"}
    return ctx.log("emit_discount_rate", og_rate_series=og_rate_series,
                   clews_discount_rate=rate if scalar else "path")


# --- #5 CLEWS emissions -> health -> demographics · clews->og --------------------

def health(ctx, *, enable_mortality=True, enable_morbidity=True, mortality_target_deaths=None,
           total_attributable_deaths=None, emissions_to_deaths_multiplier=None,
           morbidity_productivity_elasticity=0.01, mortality_profile_path=None, morbidity_profile=None,
           phase_in_periods=5, n_working_age_ability_types=7):
    r"""CLEWS PM2.5 emissions change -> calibrated dose-response -> OG mortality/morbidity (clews->og).

    Scales by the PM2.5 (not CO2e) reform/base emission ratio and the per-country multiplier
    :math:`M` = energy mass share x CRF elasticity (``country.pm25_dose_response``; PHL ~0.082):

    .. math:: \Delta\text{deaths} = \text{total\_attributable\_deaths}\;\times\;M\;\times\;\Delta\text{emissions}

    Mortality drives the disease_pop demographic re-solve (age profile from GBD; negative target = lives
    saved); morbidity scales the effective-labour path e (the main output gain). Totals come from the
    country's GBD export -- no fabricated number is used.

    Args:
        ctx (CouplingState): reads the CLEWS emissions + country GBD; stages extras['health_shock'];
            mutates og_reform.e (morbidity).
        enable_mortality (bool): apply the mortality (demographic) channel.
        enable_morbidity (bool): apply the morbidity (effective-labour) channel.
        mortality_target_deaths (float or None): an explicit signed deaths target (overrides the
            total x M x emissions calculation; negative = lives saved).
        total_attributable_deaths (float or None): the ambient-PM2.5 deaths total to scale; None ->
            sourced from the country's GBD export.
        emissions_to_deaths_multiplier (float or None): the multiplier M; None -> country.pm25_dose_response.
        morbidity_productivity_elasticity (float): peak per-person productivity haircut; GBD overrides it.
        mortality_profile_path (str or None): a file with the mortality age profile (else GBD/placeholder).
        morbidity_profile (array_like or None): the morbidity age shape (else GBD/uniform).
        phase_in_periods (int): MODEL periods to ramp the effect over.
        n_working_age_ability_types (int): leading J columns of the (T,S,J) e-array treated as working-age.
    Returns:
        dict: provenance -- emissions_change, dose_response_M, mortality_excess_deaths, morbidity_benefit, ...
    """
    c = ctx.country
    p = ctx.og_reform
    species = getattr(c, "health_emission", None)
    # SKIP (recorded, loud), don't crash, when this CLEWS case cannot drive the health channel at all:
    # no emissions export (FileNotFoundError), or no species matching country.health_emission
    # (EmissionsSpeciesAbsent -- e.g. a case that tracks only GHGs and no PM2.5-type pollutant).
    # Mirrors _skip_if_unavailable -- `coupled` then still runs the other channels. ONLY absence is
    # caught: a file that exists but is malformed/truncated still raises (corruption, not absence).
    try:
        er = signals.emissions_ratio(c.scenario.base_dir, c.scenario.reform_dir, c, species=species)
    except (FileNotFoundError, signals.EmissionsSpeciesAbsent) as e:
        reason = (f"health-emissions source unavailable (species {species!r}): {e}")
        print(f"[skip] health: {reason}")
        return ctx.log("health", skipped=True, reason=reason)
    demis = float(np.nanmean(er.values[:10])) - 1.0       # <0 == reform is cleaner
    if not np.isfinite(demis):
        raise ValueError(f"health: emissions_ratio gave a non-finite change ({demis}); "
                         "check the CLEWS emissions files.")
    M = signals.pm25_dose_response(c, override=emissions_to_deaths_multiplier)
    gbd = getattr(c, "gbd_burden_csv", None)
    gloc = getattr(c, "name", None)
    gyr = int(getattr(c, "gbd_year", 2023))
    prov = {"emissions_change": demis, "emissions_species": species or c.co2_emission,
            "dose_response_M": M, "gbd_source": bool(gbd)}
    # No GBD export and no explicit deaths target -> nothing real to drive mortality. Skip the whole
    # channel cleanly (honest: no data -> no effect) rather than erroring or fabricating -- placed AFTER
    # the emissions read above so a CORRUPT emissions file still raises and an ABSENT one still skips with
    # its own reason (GBD-absence must not mask those). Supply gbd_burden_csv or an explicit target.
    if enable_mortality and gbd is None and mortality_target_deaths is None and total_attributable_deaths is None:
        reason = "no GBD export on disk (country.gbd_burden_csv is None; see DATA.md) -- health channel skipped"
        print(f"[skip] health: {reason}")
        return ctx.log("health", skipped=True, reason=reason)
    if enable_mortality:
        if gbd and mortality_profile_path is None:
            profile = health_profile.build_profile_from_gbd(
                gbd, gloc, gyr, key_col="cause_name", key_value="All causes")
            if mortality_target_deaths is None and total_attributable_deaths is None:
                total_attributable_deaths = health_profile.total_deaths_from_gbd(
                    gbd, gloc, gyr, key_col="cause_name", key_value="All causes")
            psrc = "GBD ambient-PM2.5 deaths-by-age"
        elif mortality_profile_path:
            profile = health_profile.load_profile(mortality_profile_path); psrc = "file"
        else:
            profile = health_profile.placeholder_profile()
            psrc = "PLACEHOLDER (no GBD profile; see DATA.md)"
        if mortality_target_deaths is not None:
            excess_deaths = float(mortality_target_deaths)
            target_src = "explicit mortality_target_deaths"
        elif total_attributable_deaths is not None:
            excess_deaths = float(total_attributable_deaths) * M * demis    # total x dose-response x emissions
            target_src = ("GBD total x M x emissions change" if gbd else "explicit total x M x emissions change")
        else:
            raise ValueError("health mortality: no mortality_target_deaths, no total_attributable_deaths, "
                             "and no GBD export to source the ambient-PM2.5 deaths total -- supply a GBD "
                             "file (country.gbd_burden_csv) or an explicit total. No fabricated default is used.")
        ctx.extras["health_shock"] = {"excess_deaths": float(excess_deaths), "profile": profile,
                                      "phase_years": phase_in_periods, "rc_ss": c.rc_ss}
        prov["mortality_excess_deaths"] = float(excess_deaths)
        prov["target_source"] = target_src
        prov["profile_source"] = psrc
    if enable_morbidity:
        morbidity_response = morbidity_productivity_elasticity
        if gbd and morbidity_profile is None:
            morbidity_profile = health_profile.build_morbidity_profile_from_gbd(gbd, gloc, gyr)
            morbidity_response = health_profile.morbidity_yld_rate_from_gbd(gbd, gloc, gyr)
            msrc = "GBD YLD-by-age (working-age causes)"
        else:
            msrc = ("custom age shape" if morbidity_profile is not None else "uniform (all active ages)")
        benefit = -morbidity_response * M * demis          # cleaner (demis<0) -> higher productivity; M scales
        e = np.array(p.e, dtype=float)
        S = e.shape[1]
        g = (health_profile.morbidity_shape_to_S(morbidity_profile, S, getattr(p, "E", 0))
             if morbidity_profile is not None else np.ones(S))
        gcol = g[:, None]
        ramp = np.linspace(0.0, benefit, phase_in_periods)
        for t, b in enumerate(ramp):
            e[t, :, :n_working_age_ability_types] *= (1.0 + b * gcol)
        e[phase_in_periods:, :, :n_working_age_ability_types] *= (1.0 + benefit * gcol)
        p.e = e
        prov["morbidity_benefit"] = benefit
        prov["morbidity_response"] = float(morbidity_response)
        prov["morbidity_profile_source"] = msrc
    return ctx.log("health", **prov)


# --- #6 OG activity -> CLEWS energy-service demand · og->clews (post-solve) ------

def emit_energy_demand(ctx, activity_ratio, *, og_activity="sector_output", og_index_override=None,
                       clews_fuel=None):
    """OG activity -> CLEWS energy-service demand (og->clews; run AFTER the reform solve).

    Writes the Demand artifact scaling baseline CLEWS demand by the reform/base activity ratio -- the
    producer side of loop closure.

    Args:
        ctx (CouplingState): reads base_tpi/reform_tpi (via the caller's ratio); writes clews_inputs['Demand'].
        activity_ratio (array_like): the ALREADY-SOURCED reform/base activity ratio path
            (``signals.activity_ratio``).
        og_activity (str): which OG series drives demand -- 'sector_output' (Y_m) or 'consumption_good' (C_i).
        og_index_override (int or None): override the sliced OG index; None -> the energy index per the concordance.
        clews_fuel (str or None): the CLEWS fuel code the demand maps to (recorded on the artifact);
            None -> the country's ``electricity_fuel`` -- the artifact must name its target commodity
            or the CLEWS-side merge cannot apply it.
    Returns:
        dict: provenance -- og_activity, mean_ratio (plus a note if inert).
    """
    c = ctx.country
    driver = "Y_m" if og_activity == "sector_output" else "C_i"
    # only the discovered (non-override) path needs the port; an explicit override bypasses discovery
    if og_index_override is None:
        port = "energy_industry_index" if driver == "Y_m" else "energy_good_index"
        if (skip := _skip_if_unavailable(ctx, "emit_energy_demand", port)) is not None:
            return skip
    # only consult the concordance when no explicit override -- the override path is documented to
    # bypass discovery entirely (and must not require a concordance to exist)
    idx = og_index_override if og_index_override is not None else (
        ctx.concordance.energy_industry_index if driver == "Y_m"
        else ctx.concordance.energy_good_index)
    if clews_fuel is None:
        clews_fuel = getattr(c, "electricity_fuel", None)
    if clews_fuel is None:
        print("[guardrail] emit_energy_demand: no CLEWS fuel code (clews_fuel arg and "
              "CountryConfig.electricity_fuel both unset) -- the demand artifact names NO target "
              "commodity, so a CLEWS-side merge cannot apply it. Set electricity_fuel.")
    ratio = np.asarray(activity_ratio, dtype=float)
    mr = float(ratio[:10].mean())
    ctx.clews_inputs["Demand"] = {
        "og_activity": og_activity, "og_index": idx, "clews_fuel": clews_fuel,
        "region": getattr(c, "clews_region", "RE1"),
        "start_year": c.scenario.og_start_year, "ratio_by_period": ratio.tolist()}
    prov = {"og_activity": og_activity, "mean_ratio": mr}
    if abs(mr - 1.0) < 1e-3:
        prov["note"] = ("ratio ~= 1: the forward demand channel is INERT in a single CLEWS->OG pass; "
                        "it becomes a real driver only inside the iterated loop.")
    return ctx.log("emit_energy_demand", **prov)

"""Named experiments: each is a plain function ``exp(ctx, solve)`` that calls channels in order and
calls ``solve(ctx)`` at the point the reform is solved. Pre-solve channels (clews->og, policy) run
before solve(ctx); og->clews ``emit_`` channels run after. Run one with:
    python -m oglink run <name>     (see `python -m oglink list`).
The data SOURCE for each channel (a controlled number, the CLEWS cost index / levelized cost, GBD) is visible
right here in the call -- not encoded in the name.
"""
from __future__ import annotations

import numpy as np

from . import channels, signals


def _energy_share(ctx):
    """Electricity's value-share of the OG energy good (io_matrix[energy_good, energy_industry]).
    None if the country can't isolate electricity (a required port is unresolved) -- the dependent
    energy_price channel will then skip, so the None is never consumed."""
    p = ctx.og_reform
    con = ctx.concordance
    if con is None or con.energy_good_index is None or con.energy_industry_index is None:
        return None
    return float(np.asarray(p.io_matrix)[con.energy_good_index, con.energy_industry_index])


def _electricity_intensity(ctx):
    """The M-vector phi_j (electricity's input-cost share per industry) for the Option-A' cost-push,
    read LINK-SIDE from the country package's SAM + PROD_DICT (no package import). None if the registry,
    SAM, or PROD_DICT is unavailable, or the vector does not align to the model's M -> the cost_push
    channel then skips. Degrades to None rather than breaking the run -- but an UNEXPECTED failure (as
    opposed to a plain absence) is recorded to provenance first: the intermediate cost-push carries ~73%
    of the electricity-price transmission, so a silent loss of it (e.g. a registry/SAM path that broke on
    the port) must show up in the manifest, not quietly understate the result."""
    from . import aggregation, discovery, registry
    try:
        src = registry.package_source_dir(registry.lookup(ctx.country, require_env=False))
        sam = discovery._read_sam(src)
        prod, _cons = discovery.read_package_dicts(src)
    except Exception as e:  # noqa: BLE001 -- resolution broke; keep the run alive, but SAY the leg was lost
        ctx.log("electricity_intensity_unavailable", provenance_only=True,
                reason=f"{type(e).__name__}: {e}",
                note="cost-push phi source failed to resolve -- intermediate leg SKIPPED (result understated)")
        return None
    if sam is None or not prod:                  # genuine absence (no SAM / no PROD_DICT): expected clean skip
        return None
    try:
        phi = aggregation.input_intensity(sam, prod)
    except Exception as e:  # noqa: BLE001 -- an odd SAM must not break the run, but must not vanish silently
        ctx.log("electricity_intensity_unavailable", provenance_only=True,
                reason=f"{type(e).__name__}: {e}",
                note="cost-push phi could not be computed from the SAM -- intermediate leg SKIPPED")
        return None
    return phi if phi.shape == (int(ctx.og_reform.M),) else None


def _activity(ctx, driver="Y_m"):
    con = ctx.concordance
    idx = None if con is None else (
        con.energy_industry_index if driver == "Y_m" else con.energy_good_index)
    if idx is None:                      # electricity not isolable -> emit_energy_demand will skip
        return None
    return signals.activity_ratio(ctx.base_tpi, ctx.reform_tpi, driver=driver, og_index=idx)


def _public_capex(ctx, *, scale=1.0, smooth_years=1):
    c, p = ctx.country, ctx.og_reform
    return signals.public_capex_pct_gdp(c.scenario.base_dir, c.scenario.reform_dir, c,
                                        og_start_year=c.scenario.og_start_year, T=p.T,
                                        scale=scale, smooth_years=smooth_years)


def _apply_energy_composite(ctx, elec_price_ratio):
    """Apply BOTH halves of an electricity-price change -- the ``energy_full`` transmission shared by the
    controlled comparison and the live ``coupled`` run:
      - INTERMEDIATE cost-push: ``energy_cost_push`` weighted by SAM input-share phi_j, with electricity's
        OWN self-use ZEROED so it doesn't double-count the wedge below;
      - FINAL consumption: a RECYCLED ``energy_price`` wedge on the energy good, diluted to electricity's
        value-share of it (1 + share*(ratio-1)).
    ``elec_price_ratio`` is the UN-diluted electricity reform/base price ratio -- a scalar (controlled +20%)
    or a per-period path (the CLEWS 'auto' source). COUPLABILITY-GATED: when the country can't isolate
    electricity as its own industry AND good, both legs are ill-defined, so the composite skips cleanly."""
    con = ctx.concordance
    if con is None or con.energy_industry_index is None or con.energy_good_index is None:
        return ctx.log("energy_price_composite", skipped=True, reason="electricity not isolable -- skipped")
    phi = _electricity_intensity(ctx)                 # None (no SAM) -> cost-push leg skips; wedge still fires
    if phi is not None:
        phi = np.array(phi, dtype=float)
        phi[con.energy_industry_index] = 0.0          # self-use carried by the final wedge, not here
    channels.energy_cost_push(ctx, price_ratio=elec_price_ratio, electricity_intensity=phi)
    wedge = 1.0 + _energy_share(ctx) * (np.asarray(elec_price_ratio, dtype=float) - 1.0)
    channels.energy_price(ctx, price_ratio=wedge, recycle_revenue_to_transfers=True)
    return None


def _auto_price_ratio(ctx):
    """The country's ACTUAL electricity reform/base price-ratio path from CLEWS ('auto': the
    cost-of-electricity workbook if present, else the LEVELIZED cost reconstructed from the raw MUIOGO
    cost/production CSVs). UN-diluted (share=1.0). This is the real price change, NOT an illustrative
    stimulus -- the single source of the electricity price used by ``coupled`` and every real energy
    result here. The marginal (shadow-price) source is NEVER auto-selected (it is degenerate); it is an
    explicit opt-in. The RESOLVED source (workbook vs lcoe, and which files) is logged into the run's
    provenance/manifest -- 'auto' must never leave the choice invisible."""
    con = ctx.concordance
    if con is None or con.energy_good_index is None:
        # Electricity not isolable for this country -> every consumer of this ratio skips anyway, so do
        # NOT read the CLEWS price source at all: it is evaluated EAGERLY at the call sites (before the
        # channels' own gates), and a messy-but-irrelevant EBb4 (e.g. several ELC* commodities with
        # electricity_fuel unset) must not crash a run whose energy legs are skipping.
        return None
    c, p = ctx.country, ctx.og_reform
    resolved = {}
    ratio = signals.energy_price_ratio("auto", base_dir=c.scenario.base_dir, reform_dir=c.scenario.reform_dir,
                                       share=1.0, og_start_year=c.scenario.og_start_year,
                                       n=np.asarray(p.tau_c).shape[0], fuel=c.electricity_fuel,
                                       busbar=getattr(c, "busbar_electricity", None), resolved=resolved)
    if resolved:
        ctx.log("energy_price_source", provenance_only=True,
                note="price-source resolution (provenance, not a channel)", **resolved)
    return ratio


# --- single-channel experiments -------------------------------------------------

def energy_price(ctx, solve):
    """The energy-price demand-response channel at PHL's REAL electricity price (CLEWS 'auto' levelized), via
    the consumption-tax wedge (no recycling, c_min=0). PHL's real price is near-flat, so a small effect."""
    channels.energy_price(ctx, price_ratio=_auto_price_ratio(ctx))
    solve(ctx)


# --- the three energy-price TRANSMISSIONS, same controlled +20% stimulus (for the comparison) -----
# tau_c wedge = ``energy_price`` above (consumption-tax wedge); the two below route the SAME +20%
# electricity-price change through PRODUCTION instead. See experiments/run_energy_price_comparison.py.

def energy_price_tfp(ctx, solve):
    """Option A: a controlled +20% electricity price via the electricity industry's TFP (Z), so OG-Core
    produces the price endogenously and propagates it through its own Leontief io_matrix + GE feedback."""
    channels.energy_price_tfp(ctx, price_ratio=1.20)
    solve(ctx)


def energy_cost_push(ctx, solve):
    """Option A': a controlled +20% electricity price as an inter-industry cost-push -- a per-industry
    TFP haircut weighted by electricity's input-cost share phi_j (from the SAM). Reduced-form proxy."""
    channels.energy_cost_push(ctx, price_ratio=1.20, electricity_intensity=_electricity_intensity(ctx))
    solve(ctx)


def energy_full(ctx, solve):
    """Composite (A' cost-push + recycled final-good wedge): BOTH halves of the same +20% electricity
    price that the single mechanisms each miss. The PHL SAM splits electricity ~73% intermediate / 25%
    final, so the true response needs both:
      - INTERMEDIATE (cost-push): energy_cost_push with phi_j, but electricity's OWN self-use is ZEROED
        so it does not double-count the household wedge below. This is the contractionary, wage-bearing
        macro channel (the correct GDP sign).
      - FINAL (consumption): the recycled energy_price wedge raises the energy consumption good by
        electricity's value-share of it (the regressive cost-of-living incidence).
    Reduced-form -- two stacked proxies for the inter-industry channel OG-Core lacks; the exact version
    is a real use matrix (built from the SAM's observable inter-industry electricity column). The shared
    composite logic (gate, self-use zeroing, recycled wedge) lives in ``_apply_energy_composite``; the
    live ``coupled`` run applies the SAME transmission at the real CLEWS price."""
    _apply_energy_composite(ctx, 1.20)                # controlled +20% (the comparison stimulus)
    solve(ctx)


def clean_incidence(ctx, solve):
    """The regressive incidence of PHL's REAL electricity price (CLEWS 'auto' levelized): revenue recycled +
    energy a necessity (c_min>0). NB energy_cmin must be below every group's baseline energy consumption."""
    channels.energy_price(ctx, price_ratio=_auto_price_ratio(ctx), recycle_revenue_to_transfers=True,
                          energy_subsistence_floor=0.005)
    solve(ctx)


def investment(ctx, solve):
    """PUBLIC-infrastructure (grid/T&D) capex -> alpha_I -> K_g. PHL/PEP has ~0 grid-capex delta, so
    this contributes ~nothing here (the transition is generation-side)."""
    channels.investment(ctx, _public_capex(ctx))
    solve(ctx)


def capital_intensity(ctx, solve):
    """A factor-SHARE / energy-PRICE lever: a permanent rise in the energy industry's capital exponent
    gamma, calibrated from the CLEWS reform/base power-fleet capital-cost-share ratio (first decade)."""
    c = ctx.country
    win = (c.scenario.og_start_year, c.scenario.og_start_year + 9)
    cal = signals.capital_intensity_ratio(c.scenario.base_dir, c.scenario.reform_dir, c, window=win)
    channels.capital_intensity(ctx, energy_capital_share_multiplier=cal["ratio"])
    solve(ctx)


def energy_capex(ctx, solve):
    """The capex-heavy generation buildout financed by an investment tax credit: lowers the energy
    industry's cost of capital, drawing private capital INTO energy (the capital-DEMAND lever)."""
    channels.energy_capex(ctx, investment_tax_credit_rate=0.20)
    solve(ctx)


def carbon(ctx, solve):
    """Carbon price as a shared lever: OG consumption-side tax (recycled) + CLEWS EmissionsPenalty."""
    channels.carbon_tax(ctx, carbon_price_usd_per_tco2=50.0, recycle_revenue_to_transfers=True)
    channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)
    solve(ctx)


def health(ctx, solve):
    """CLEWS PM2.5 emissions change -> calibrated per-country dose-response (M; PHL ~0.08, not 1:1)
    -> OG mortality/morbidity."""
    channels.health(ctx)
    solve(ctx)


# --- forward (og->clews) plumbing, in isolation ---------------------------------

def discount_rate(ctx, solve):
    """Forward (OG->CLEWS) in isolation: OG interest rate -> CLEWS DiscountRate. Tests the emit
    plumbing on the (unmodified-reform) solve; the reform delta is exercised in 'forward'/'coupled'."""
    solve(ctx)
    channels.emit_discount_rate(ctx)


def demand(ctx, solve):
    """Forward (OG->CLEWS) in isolation: OG industry output Y_m -> CLEWS demand scaling. Tests the emit
    plumbing/format; the reform delta is exercised in 'forward'/'coupled'."""
    solve(ctx)
    channels.emit_energy_demand(ctx, _activity(ctx, "Y_m"), og_activity="sector_output")


# --- composed -------------------------------------------------------------------

def forward(ctx, solve):
    """An energy-price reform that also emits CLEWS inputs: OG rate -> DiscountRate, OG activity ->
    demand scaling (the producer side of loop closure)."""
    channels.energy_price(ctx, price_ratio=1.20)
    solve(ctx)
    channels.emit_discount_rate(ctx)
    channels.emit_energy_demand(ctx, _activity(ctx, "Y_m"), og_activity="sector_output")


def coupled(ctx, solve):
    """The full coupled soft-link: the electricity price from CLEWS ('auto' -- the cost-of-electricity
    index if the curated workbook is present, else the LEVELIZED cost reconstructed from raw MUIOGO
    cost/production CSVs) transmitted via the ENERGY_FULL COMPOSITE (inter-industry cost-push + recycled
    household wedge -- the defensible transmission) +
    public investment + carbon on the CLEWS side + GBD health, then OG rate/activity emitted back."""
    _apply_energy_composite(ctx, _auto_price_ratio(ctx))    # the country's real CLEWS electricity price
    channels.investment(ctx, _public_capex(ctx))
    channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)    # carbon priced on the CLEWS side only here
    channels.health(ctx)
    solve(ctx)
    channels.emit_discount_rate(ctx)
    channels.emit_energy_demand(ctx, _activity(ctx, "Y_m"), og_activity="sector_output")


# --- cumulative "across steps": each step adds one channel on top of the last ----
# The layers REPRODUCE the real ``coupled`` run cumulatively -- identical channel treatments (real CLEWS
# 'auto' electricity price via the composite, real public investment, the $50 CLEWS-side carbon penalty,
# GBD health) -- so the top layer EQUALS ``coupled`` and the decomposition attributes the ACTUAL PHL result.

def _across_energy(ctx, solve):
    _apply_energy_composite(ctx, _auto_price_ratio(ctx))
    solve(ctx)


def _across_investment(ctx, solve):
    _apply_energy_composite(ctx, _auto_price_ratio(ctx))
    channels.investment(ctx, _public_capex(ctx))
    solve(ctx)


def _across_carbon(ctx, solve):
    _apply_energy_composite(ctx, _auto_price_ratio(ctx))
    channels.investment(ctx, _public_capex(ctx))
    channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)
    solve(ctx)


def _across_health(ctx, solve):
    _apply_energy_composite(ctx, _auto_price_ratio(ctx))
    channels.investment(ctx, _public_capex(ctx))
    channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)
    channels.health(ctx)
    solve(ctx)


ACROSS_STEPS = [
    ("energy price", _across_energy),
    ("+ investment", _across_investment),
    ("+ carbon", _across_carbon),
    ("+ health", _across_health),
]


# --- registry of runnable experiments (names for the CLI / battery dispatch) -----

_EXPERIMENTS = [energy_price, energy_price_tfp, energy_cost_push, energy_full, clean_incidence,
                investment, capital_intensity, energy_capex, carbon, health, discount_rate, demand,
                forward, coupled]


def names() -> list[str]:
    return [fn.__name__ for fn in _EXPERIMENTS]


def get(name):
    for fn in _EXPERIMENTS:
        if fn.__name__ == name:
            return fn
    raise KeyError(f"no experiment {name!r}; available: {names()}")

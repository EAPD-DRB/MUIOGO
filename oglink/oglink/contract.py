"""The interface contract between OG-Core and CLEWS/OSeMOSYS.

Everything that must be agreed for a coupling to be reproducible lives here, as
explicit, reviewable data -- not buried in a run script. See the de novo analysis
(docs/design/og-clews-denovo-analysis.md), section 5/6.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ScenarioPair:
    """A baseline/reform pairing -- the unit of every coupled run."""
    name: str
    base_dir: str          # CLEWS baseline output folder
    reform_dir: str        # CLEWS reform output folder
    years: tuple           # calendar years present in the CLEWS export
    og_start_year: int     # OG-Core start_year, for time-grid alignment


@dataclass
class Concordance:
    """Maps CLEWS objects to OG-Core indices, and pins the energy ports.

    ``energy_industry_index`` is the OG industry m whose output price carries the energy cost (route B).
    ``energy_good_index`` is the OG consumption good i that households buy and react to (route A). Either
    is ``None`` when the country's OG aggregation cannot isolate the carrier (e.g. electricity is fused
    with water in a single group) -- ``unavailable`` records why. Channels that need an unavailable port
    SKIP themselves (recording the reason); channels that don't (health off CLEWS emissions, public
    investment, the discount-rate emit) still run.
    """
    energy_industry_index: int | None
    energy_good_index: int | None
    unavailable: dict = field(default_factory=dict)   # port name -> why it couldn't be resolved

    @classmethod
    def from_dicts(cls, prod_dict, cons_dict, carrier="electricity"):
        """Discover the energy ports from a calibration's aggregation dicts -- the indices track whatever
        aggregation the model is built with, no hand-set literals. The COUPLING-CAPABILITY GATE is the
        PRODUCTION side: electricity must be ISOLATED as its own industry -- in exactly one PROD_DICT
        group, and that group PURE electricity (no other carriers like water). A standalone ``aelcg``
        passes; a fused ``Utilities: [aelec, awatr]`` does not. If electricity is not isolated in
        production, BOTH ports come back ``None`` with a reason (the country can't be coupled on energy --
        every energy channel skips). When it is isolated, the good index is the CONS_DICT group that holds
        electricity (the household energy good, which may be broader). ``carrier`` is an
        ``aggregation.CARRIERS`` key (e.g. 'electricity'), a regex, or a list of SAM codes."""
        from . import aggregation as ag

        prod_hits = ag.locate(prod_dict, carrier)
        if not prod_hits:
            why = f"carrier {carrier!r} not found in the production aggregation (groups: {list(prod_dict)})"
            return cls(None, None, {"energy_industry_index": why, "energy_good_index": why})
        if len(prod_hits) > 1:
            why = (f"carrier {carrier!r} is split across production groups {[h[1] for h in prod_hits]} "
                   "-- cannot isolate a single electricity industry")
            return cls(None, None, {"energy_industry_index": why, "energy_good_index": why})
        ind, name, matched = prod_hits[0]
        others = [c for c in prod_dict[name] if c not in matched]
        if others:                                  # the group also holds other (non-carrier) sectors
            why = (f"{carrier!r} is not isolated: production group {name!r} also contains {others} -- not a "
                   "standalone industry, so the energy coupling can't attach cleanly")
            return cls(None, None, {"energy_industry_index": why, "energy_good_index": why})
        # production isolates electricity -> coupling-capable. The household energy good is the CONS group
        # holding electricity (broader is fine: it is the consumption composite, not the industry).
        cons_hits = ag.locate(cons_dict, carrier)
        if len(cons_hits) == 1:
            good, good_why = cons_hits[0][0], None
        else:
            # the broad carrier pattern can match electricity embodied in OTHER goods across several
            # consumption groups (e.g. ZAF's 'celcm' electrical machinery in Durables and 'celcd'
            # distribution in Services, alongside the actual household energy code 'celcg'). Disambiguate
            # to the energy good via the COMMODITY ANALOGUE of the resolved production carrier code (the
            # SAM activity a<x> <-> commodity c<x> convention), which points at the one true energy good.
            analogues = {c for c in matched}
            analogues |= {"c" + c[1:] for c in matched if isinstance(c, str) and c[:1] == "a"}
            anchor_hits = ag.locate(cons_dict, list(analogues)) if analogues else []
            if len(anchor_hits) == 1:
                good, good_why = anchor_hits[0][0], None
            else:
                good, good_why = None, (
                    f"carrier {carrier!r} not isolable to one consumption good (carrier matched groups "
                    f"{[h[1] for h in cons_hits]}; commodity analogue {sorted(analogues)} matched "
                    f"{[h[1] for h in anchor_hits]})")
        unavailable = {"energy_good_index": good_why} if good_why else {}
        return cls(energy_industry_index=ind, energy_good_index=good, unavailable=unavailable)

    @classmethod
    def from_package(cls, pkg, carrier="electricity"):
        """Discover the energy ports from an installed OG country package's real PROD_DICT/
        CONS_DICT. For a model run at a *different* aggregation (e.g. a bespoke custom build), use
        ``from_dicts`` with that build's dicts so the index matches the model's columns."""
        from . import aggregation as ag
        _, prod, cons = ag.from_package(pkg)
        if prod is None or cons is None:
            raise ValueError(f"{pkg} does not expose PROD_DICT/CONS_DICT")
        return cls.from_dicts(prod, cons, carrier=carrier)


# The energy-port concordance is DISCOVERED PER RUN in the OG env (it needs the country package's real
# PROD_DICT/CONS_DICT, which the link env can't import) and exported via baseline_meta.json -- see
# og_runner._discover_concordance + framework._load_concordance. There is no link-vendored country
# concordance: a single-industry baseline reports the ports unavailable, so the energy channels skip.


@dataclass
class UnitMap:
    """The unit/currency bridge. CLEWS stores bare numbers; OG is real, numeraire =
    industry-M output, with ``factor`` (a steady-state object) as the only currency
    bridge. Pin every conversion explicitly -- there is no internal guard on either side.
    """
    clews_money_unit: str = "model"     # e.g. 'MUSD_2020'
    clews_energy_unit: str = "PJ"
    base_year: int = 2020
    deflator: float = 1.0               # to OG numeraire / base year
    notes: str = ""

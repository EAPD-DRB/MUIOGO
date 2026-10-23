"""Country configuration -- the one place country-specific assumptions live, so the
channels and framework stay country-agnostic. PHL is the worked instance.
"""
from __future__ import annotations

import glob
import json
import os
from dataclasses import dataclass

from .contract import ScenarioPair, UnitMap


@dataclass
class CountryConfig:
    name: str
    un_code: str
    og_repo: str                            # OG-model registry/repo key (e.g. "og-phl"); how the link
                                            # finds this country's installed OG model. The UN code is the
                                            # OG package's own (ogphl.UN_COUNTRY_CODE), not used for lookup.
    gdp_musd: float                         # nominal GDP, base year, for %GDP conversions
    # NB: the energy-port concordance is NOT a country-config literal -- it is discovered per run in the
    # OG env from the country package's real PROD_DICT/CONS_DICT and exported via baseline_meta.json
    # (see og_runner._discover_concordance / framework._load_concordance), so it tracks the calibration
    # the baseline actually solved at rather than a hand-set assumption.
    units: UnitMap
    scenario: ScenarioPair
    # Prefix identifying ALL power-sector technology codes in the CLEWS export (e.g. "PHL_POW").
    # REQUIRED for the investment / capital-intensity channels: None (unset) fails loudly at first use
    # rather than silently matching zero technologies and reporting a zero capex delta as an economics fact.
    power_prefix: str | None = None
    public_power_markers: tuple = ("_TD",)  # techs treated as public infrastructure (T&D)
    # the CLEWS commodity code whose OSeMOSYS commodity-balance marginal (shadow price) is the household
    # electricity price (drives the energy_price channel's 'marginal' source). None -> the marginal's
    # generic 'ELC*' default, which is wrong for country-prefixed fuels (PHL uses PHL_*_ELE), so set it.
    electricity_fuel: str | None = None
    # the FINAL-demand commodity the OG-activity demand write-back scales (value = base_SAD x ratio).
    # Distinct from electricity_fuel: that is the price-facing code whose SAD rows are all zero, so
    # scaling it changes nothing; the load-carrying final-demand carrier is a separate commodity.
    demand_commodity: str | None = None
    # the BUSBAR electricity commodity code -- generation output, pre-T&D (e.g. PHL uses "PHL_POW_ELE").
    # Distinct from electricity_fuel (the household/retail code): this is the LCOE denominator and the
    # commodity whose producers ARE the generation fleet. Drives the energy_price channel's 'lcoe' source
    # (the workbook-less levelized price). None -> the 'lcoe' source is unavailable for the country.
    busbar_electricity: str | None = None
    # the OSeMOSYS region code of the CLEWS case -- addressed by every OG->CLEWS write-back artifact
    # (EmissionsPenalty / DiscountRate / demand scaling), which MUIOGO merges back into the case's
    # inputs. "RE1" is MUIOGO's single-region convention; a differently-named or multi-region case must
    # set it or the merged artifacts would target a nonexistent region.
    clews_region: str = "RE1"
    co2_emission: str = "CO2e"        # carbon-policy / climate species (carbon channel + emissions chart)
    health_emission: str = "PM2_5"    # the ambient pollutant the GBD health burden is attributed to; the
                                      # health channel scales its PM2.5 dose-response by THIS species'
                                      # reform/base emission ratio -- NOT CO2e (climate != air-pollution health)
    mindist_tpi: float = 1e-5
    # SS aggregate-resource-constraint gate for the LIVES-SAVED (mortality-down) health reform only:
    # apply_health_shock sets p.RC_SS to this when the target is negative; every other solve (baseline,
    # deaths-added, energy/investment/carbon) keeps ogcore's tight 1e-8 default. The lives-saved solve
    # leaves an intrinsic ~5e-7 Walras residual on the production good that is INVARIANT to a fresh
    # re-solve and to a 100-10000x tighter fixed-point tolerance (verified: mindist_SS 1e-11/1e-13 both
    # give 5.089e-7) -- a structural identity gap of the converged demographic equilibrium, not solver
    # slop, so only the post-solve RC_SS assertion can clear it. Testing found the residual
    # SCALES with the lives-saved target: the real emissions-derived target (-3,406) leaves |RC|~4.3e-6 on
    # Manufacturing, which the prior 1e-6 gate (calibrated for a ~1.7e-7 residual) wrongly tripped. Set to
    # 1e-5: clears ~4.3e-6 with headroom, still ~10x tighter than ogcore's RC_TPI=1e-4 default (COD runs
    # RC_TPI=0.0075) and economically negligible (~1e-6 relative to sector output). Realized |RC| is logged.
    rc_ss: float = 1e-5
    # GBD ambient-PM2.5 burden export (Deaths + YLDs by age/cause). Feeds the health channel's real
    # mortality h(s) + excess_deaths and morbidity g(s) + YLD-rate magnitude. None -> placeholders.
    gbd_burden_csv: str | None = None
    gbd_year: int = 2023
    # Emissions->deaths dose-response multiplier M = (energy sector's share of ambient PM2.5 MASS) x
    # (CRF elasticity at the country's exposure). The health channel maps a power-sector PM2.5 emissions
    # change to an ambient-PM2.5 deaths change by total_deaths x M x emissions_change, NOT 1:1 (M=1) --
    # power is only ~10% of ambient PM2.5 and the CRF is concave. Per-country, from McDuffie 2021; see
    # data/pm25_health.json. None -> channel warns and
    # falls back to M=1.0 (naive 1:1).
    pm25_dose_response: float | None = None

    def is_power(self, tech: str) -> bool:
        if not self.power_prefix:
            raise ValueError(
                f"CountryConfig({self.name!r}).power_prefix is unset -- the link cannot identify this "
                "country's power-sector technologies in the CLEWS export. Set power_prefix to the "
                "technology-code prefix your CLEWS model uses (e.g. 'PHL_POW').")
        return tech.startswith(self.power_prefix)

    def is_public(self, tech: str) -> bool:
        return self.is_power(tech) and any(m in tech for m in self.public_power_markers)


# --- CLEWS scenario location: from the user's MUIOGO installation, NOT a hardcoded machine path ------
# Each scenario side ('base'/'reform') resolves by first match:
#   1. an explicit dir -- $OGLINK_CLEWS_BASE / $OGLINK_CLEWS_REFORM (or CLI --clews-base/--clews-reform)
#   2. the MUIOGO install -- <MUIOGO>/WebAPP/DataStorage/<case>/res/<run>/csv, where
#        MUIOGO = $OGLINK_MUIOGO_HOME (or a sibling ../MUIOGO next to this repo),
#        case   = $OGLINK_CLEWS_CASE,  run = $OGLINK_CLEWS_BASE_RUN / $OGLINK_CLEWS_REFORM_RUN
#   3. "" -- unresolved; the CLEWS-reading channels then fail with CLEWS_SCENARIO_HELP. No machine default.
CLEWS_SCENARIO_HELP = (
    "CLEWS scenario directory is unset. Point the link at your MUIOGO installation: set "
    "$OGLINK_MUIOGO_HOME (or place MUIOGO at ../MUIOGO), $OGLINK_CLEWS_CASE, and "
    "$OGLINK_CLEWS_BASE_RUN/$OGLINK_CLEWS_REFORM_RUN; or give explicit dirs via "
    "$OGLINK_CLEWS_BASE/$OGLINK_CLEWS_REFORM, or `oglink run ... --clews-base <dir> --clews-reform <dir>`.")


def _muiogo_home():
    """The MUIOGO installation dir. Resolution: $OGLINK_MUIOGO_HOME; else the MUIOGO checkout this package
    is installed INSIDE (our layout -- oglink lives at <MUIOGO>/oglink/oglink, so walk up for a dir that
    holds both API/ and WebAPP/DataStorage); else a sibling ../MUIOGO (the standalone-checkout layout).
    None if nothing resolves."""
    env = os.environ.get("OGLINK_MUIOGO_HOME")
    if env:
        return env
    home = _find_muiogo_root(os.path.dirname(os.path.abspath(__file__)))
    if home:
        return home
    sibling = os.path.normpath(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.pardir, "MUIOGO"))
    return sibling if os.path.isdir(sibling) else None


def _find_muiogo_root(start):
    """Walk up from ``start`` for a MUIOGO checkout root -- a dir holding both API/ and WebAPP/DataStorage.
    Bounded; returns the dir or None. Lets an oglink nested inside MUIOGO find its host without config."""
    cur = start
    for _ in range(6):
        if os.path.isdir(os.path.join(cur, "API")) and \
           os.path.isdir(os.path.join(cur, "WebAPP", "DataStorage")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None


def clews_scenario_dir(which):
    """The CLEWS scenario dir for ``which`` in {'base','reform'}, resolved from config / the MUIOGO
    install (see the note above); '' if unresolved. Reads MUIOGO's WebAPP/DataStorage/<case>/res/<run>/csv
    layout, so the link uses whatever is installed there rather than a baked-in path."""
    w = which.upper()
    direct = os.environ.get(f"OGLINK_CLEWS_{w}")
    if direct:
        return direct
    home, case = _muiogo_home(), os.environ.get("OGLINK_CLEWS_CASE")
    run = os.environ.get(f"OGLINK_CLEWS_{w}_RUN")
    if home and case and run:
        return os.path.join(home, "WebAPP", "DataStorage", case, "res", run, "csv")
    return ""


def _resolve_gbd_csv():
    """The GBD burden CSV under the repo's IHME-GBD_2023_DATA/ (multi-country export), or None."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = [h for h in glob.glob(os.path.join(root, "IHME-GBD_2023_DATA", "*.csv"))
            if "citation" not in os.path.basename(h).lower()]
    return min(hits) if hits else None


def _resolve_dose_response(name: str):
    """Per-country emissions->deaths multiplier M from data/pm25_health.json, or None if absent."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "pm25_health.json")
    try:
        with open(path, encoding="utf-8-sig") as f:
            row = json.load(f).get("countries", {}).get(name)
        return float(row["multiplier_M"]) if row and row.get("multiplier_M") is not None else None
    except (OSError, ValueError, KeyError):
        return None


PHL = CountryConfig(
    name="Philippines",
    un_code="608",
    og_repo="og-phl",
    power_prefix="PHL_POW",           # all PHL power-sector technology codes in the CLEWS export
    electricity_fuel="PHL_HOU_ELE",   # household electricity commodity (its marginal = the price route A faces)
    demand_commodity="PHL_HOU_ELEF",  # load-carrying final-demand carrier scaled by the OG demand ratio
    busbar_electricity="PHL_POW_ELE", # busbar generation output (pre-T&D) -- the LCOE denominator
    gdp_musd=461_600.0,  # 2024 nominal GDP, USD millions (World Bank)
    units=UnitMap(clews_money_unit="MUSD", clews_energy_unit="PJ", base_year=2020,
                  notes="CLEWS monetary outputs are model MUSD; convert vs baseline ratios where possible"),
    scenario=ScenarioPair(
        name="PEP_vs_Base",
        base_dir=clews_scenario_dir("base"),       # from the MUIOGO install / config, not hardcoded
        reform_dir=clews_scenario_dir("reform"),
        years=tuple(range(2020, 2054)),
        og_start_year=2026,
    ),
    gbd_burden_csv=_resolve_gbd_csv(),  # IHME-GBD_2023_DATA/*.csv if present, else None (placeholders)
    pm25_dose_response=_resolve_dose_response("Philippines"),  # M ~= 0.082 (energy 9.8% x CRF elast 0.84)
)


# --- declarative country onboarding: define YOUR country as data, not a source edit -------------------
# A countries JSON file holds one entry per country/case (see oglink_countries.example.json at the repo
# root). Resolution order mirrors the OG-model registry: explicit file arg > $OGLINK_COUNTRIES >
# ./oglink_countries.json (cwd). Code-defined instances in this module (PHL, the worked example) are
# always available; JSON entries ADD to them (and may shadow by key).

COUNTRY_CONFIG_HELP = (
    "Define your country in a countries JSON file (see oglink_countries.example.json): pass "
    "--countries <file>, set $OGLINK_COUNTRIES, or place oglink_countries.json in the working "
    "directory. Select it with --country <name|un-code|og-repo> or $OGLINK_COUNTRY.")

_REQUIRED_COUNTRY_KEYS = ("name", "un_code", "og_repo", "gdp_musd", "og_start_year", "power_prefix")


def config_from_dict(d: dict) -> CountryConfig:
    """Build a CountryConfig from one countries-JSON entry. Required keys: name, un_code, og_repo,
    gdp_musd, og_start_year, power_prefix (the silent-zero trap fields are deliberately NOT defaultable
    from JSON). Scenario dirs default to the MUIOGO-install resolution (env vars / --clews-* flags),
    exactly like the packaged PHL; explicit base_dir/reform_dir entries override. gbd_burden_csv and
    pm25_dose_response default to the repo's shared data resolved by country name."""
    d = dict(d)
    missing = [k for k in _REQUIRED_COUNTRY_KEYS if d.get(k) in (None, "")]
    if missing:
        raise ValueError(f"country entry {d.get('name') or d.get('og_repo') or '?'!r} is missing "
                         f"required key(s) {missing}; required: {list(_REQUIRED_COUNTRY_KEYS)}. "
                         f"{COUNTRY_CONFIG_HELP}")
    units_d = d.pop("units", {}) or {}
    _unit_keys = {"clews_money_unit", "clews_energy_unit", "base_year", "deflator", "notes"}
    if set(units_d) - _unit_keys:   # a typo'd nested key must not be silently dropped
        raise ValueError(f"country entry {d.get('name')!r}: unknown units key(s) "
                         f"{sorted(set(units_d) - _unit_keys)}; valid: {sorted(_unit_keys)}")
    units = UnitMap(clews_money_unit=units_d.get("clews_money_unit", "MUSD"),
                    clews_energy_unit=units_d.get("clews_energy_unit", "PJ"),
                    base_year=int(units_d.get("base_year", 2020)),
                    deflator=float(units_d.get("deflator", 1.0)),
                    notes=units_d.get("notes", ""))
    scen_d = d.pop("scenario", {}) or {}
    _scen_keys = {"name", "base_dir", "reform_dir", "years"}
    if set(scen_d) - _scen_keys:
        raise ValueError(f"country entry {d.get('name')!r}: unknown scenario key(s) "
                         f"{sorted(set(scen_d) - _scen_keys)}; valid: {sorted(_scen_keys)} "
                         "(og_start_year is a TOP-LEVEL key)")
    y = scen_d.get("years")     # optional [first, last] (informational; not consumed by the channels)
    scenario = ScenarioPair(
        name=scen_d.get("name", f"{d['name']} reform_vs_base"),
        base_dir=scen_d.get("base_dir") or clews_scenario_dir("base"),
        reform_dir=scen_d.get("reform_dir") or clews_scenario_dir("reform"),
        years=tuple(range(int(y[0]), int(y[1]) + 1)) if y else (),
        og_start_year=int(d.pop("og_start_year")))
    name = d["name"]
    known = {f for f in CountryConfig.__dataclass_fields__}
    unknown = [k for k in d if k not in known]
    if unknown:
        raise ValueError(f"country entry {name!r} has unknown key(s) {unknown}; "
                         f"valid fields: {sorted(known - {'units', 'scenario'})}")
    if "public_power_markers" in d:
        d["public_power_markers"] = tuple(d["public_power_markers"])
    d.setdefault("gbd_burden_csv", _resolve_gbd_csv())
    d.setdefault("pm25_dose_response", _resolve_dose_response(name))
    d["gdp_musd"] = float(d["gdp_musd"])
    return CountryConfig(units=units, scenario=scenario, **d)


def _countries_file(config_file=None):
    """The countries JSON to load: explicit arg > $OGLINK_COUNTRIES > ./oglink_countries.json; None
    when nothing resolves (code-defined countries are still available). Returns ``(path, explicit)``.
    A file the user NAMED (arg or env var) that does not exist raises -- a typo'd path must not silently
    fall through to a different file; only the implicit cwd default may be absent."""
    for cand, src in ((config_file, "--countries"), (os.environ.get("OGLINK_COUNTRIES"), "$OGLINK_COUNTRIES")):
        if cand:
            cand = os.path.expanduser(cand)
            if not os.path.isfile(cand):
                raise FileNotFoundError(f"countries file {cand!r} (from {src}) not found")
            return cand, True
    cwd_default = os.path.join(os.getcwd(), "oglink_countries.json")
    return (cwd_default, False) if os.path.isfile(cwd_default) else (None, False)


def country_registry(config_file=None) -> dict:
    """Every available CountryConfig, keyed (lowercased) by module attribute, .name, .un_code and
    .og_repo -- so 'phl'/'Philippines'/'608'/'og-phl' all resolve to the same instance. Code-defined
    instances in this module first, then countries-JSON entries (which may shadow).

    Error posture: a file the user NAMED (--countries / $OGLINK_COUNTRIES) fails HARD on any bad
    entry; the implicit ./oglink_countries.json cwd fallback fails SOFT (loud [guardrail] print, bad
    entry skipped) -- a half-drafted or foreign file in the working directory must not take down the
    code-defined countries (e.g. the packaged PHL default)."""
    reg = {}
    def _add(keys, obj):
        for k in keys:
            if k:
                reg[str(k).lower()] = obj
    for attr, obj in list(globals().items()):
        if isinstance(obj, CountryConfig):
            _add((attr, obj.name, obj.un_code, obj.og_repo), obj)
    path, explicit = _countries_file(config_file)
    if path:
        def _bad(msg, cause=None):
            if explicit:
                raise ValueError(msg) from cause
            print(f"[guardrail] {msg} -- skipped")
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            _bad(f"countries file {path!r} is not valid JSON: {e}", e)
            return reg
        if isinstance(data, dict):
            entries = data.get("countries")
            if entries is None:
                _bad(f"countries file {path!r} has no 'countries' list (expected "
                     "{'countries': [...]} or a bare list of entries)")
                entries = []
        else:
            entries = data
        for entry in entries if isinstance(entries, list) else []:
            try:
                if not isinstance(entry, dict):
                    raise ValueError(f"entry {entry!r} is not an object")  # noqa: TRY004 -- funneled into the ValueError handler below
                obj = config_from_dict(entry)
            except ValueError as e:
                _bad(f"countries file {path!r}: {e}", e)
                continue
            # Shadowing: re-point EVERY key that resolves to a config this entry identifies with, so a
            # user's own 'Philippines' entry also captures the module-attribute key 'phl' (the CLI's
            # default selector) -- shadowing by name/code/og-repo must be total, not partial.
            ident = {str(k).lower() for k in (obj.name, obj.un_code, obj.og_repo)}
            for k, v in list(reg.items()):
                if {str(v.name).lower(), str(v.un_code).lower(), str(v.og_repo).lower()} & ident:
                    reg[k] = obj
            _add((obj.name, obj.un_code, obj.og_repo), obj)
        if not isinstance(entries, list):
            _bad(f"countries file {path!r}: 'countries' must be a LIST of entries, got "
                 f"{type(entries).__name__}")
    return reg


def resolve_country(selector, config_file=None) -> CountryConfig:
    """The CountryConfig for ``selector`` (name / UN code / og-repo key, case-insensitive)."""
    reg = country_registry(config_file)
    obj = reg.get(str(selector).lower())
    if obj is None:
        avail = sorted({c.name for c in reg.values()})
        raise SystemExit(f"unknown country {selector!r}; available: {avail}. {COUNTRY_CONFIG_HELP}")
    return obj

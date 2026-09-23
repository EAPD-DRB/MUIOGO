"""Share-readiness surface: declarative country onboarding, the loud config-trap guardrails, the
health-channel skip path, the MUIOGO export preflight, and the write-back region/commodity threading.
All numpy/pandas-only (no ogcore) -- runs in the link env."""
import json
import os
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from oglink import channels, clews_io, muiogo_run, signals
from oglink.country import (
    PHL,
    config_from_dict,
    country_registry,
    resolve_country,
)

# --- fixtures -------------------------------------------------------------------

ENTRY = {"name": "Testland", "un_code": "999", "og_repo": "og-tst", "gdp_musd": 100000.0,
         "og_start_year": 2026, "power_prefix": "TST_POW", "electricity_fuel": "TST_HOU_ELE",
         "clews_region": "REGA", "co2_emission": "CO2EQ",
         "units": {"base_year": 2021, "deflator": 2.0}, "scenario": {"years": [2020, 2050]}}


def _write_capex(d, rows):
    """A long-format CapitalInvestment CSV: r,t,y,v."""
    path = os.path.join(d, "CapitalInvestment.csv")
    pd.DataFrame(rows, columns=["r", "t", "y", "v"]).to_csv(path, index=False)
    return path


def _write_ebb4(d, fuels=("TST_HOU_ELE",), regions=("RE1",), years=range(2026, 2031), value=5.0):
    rows = [{"r": r, "f": f, "y": y, "EnergyBalanceEachYear4": value, "DiscountRate": 0.0}
            for r in regions for f in fuels for y in years]
    path = os.path.join(d, "EBb4_EnergyBalanceEachYear4_ICR.csv")
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _write_emissions(d, species=(("CO2", 10.0), ("CO2EQ", 100.0)), years=range(2026, 2031)):
    rows = [{"r": "RE1", "t": "TST_POW_X", "e": e, "m": 1, "y": y, "v": v}
            for e, v in species for y in years]
    path = os.path.join(d, "AnnualTechnologyEmissionByMode.csv")
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


# --- declarative country config ---------------------------------------------------

def test_phl_resolves_by_every_key():
    for sel in ("phl", "Philippines", "608", "og-phl"):
        assert resolve_country(sel) is PHL


def test_json_country_loads_and_resolves(tmp_path):
    f = tmp_path / "countries.json"
    f.write_text(json.dumps({"countries": [ENTRY]}))
    cc = resolve_country("og-tst", config_file=str(f))
    assert cc.name == "Testland" and cc.power_prefix == "TST_POW"
    assert cc.clews_region == "REGA" and cc.co2_emission == "CO2EQ"
    assert cc.units.base_year == 2021 and cc.units.deflator == 2.0
    assert cc.scenario.og_start_year == 2026 and cc.scenario.years[-1] == 2050
    # and by name / code too
    assert resolve_country("testland", config_file=str(f)).og_repo == "og-tst"
    assert resolve_country("999", config_file=str(f)).og_repo == "og-tst"


def test_bare_list_countries_file(tmp_path):
    f = tmp_path / "countries.json"
    f.write_text(json.dumps([ENTRY]))
    assert resolve_country("og-tst", config_file=str(f)).name == "Testland"


def test_required_keys_enforced():
    with pytest.raises(ValueError, match="power_prefix"):
        config_from_dict({k: v for k, v in ENTRY.items() if k != "power_prefix"})


def test_unknown_key_rejected():
    with pytest.raises(ValueError, match="power_prefx"):
        config_from_dict({**ENTRY, "power_prefx": "TYPO"})


def test_explicit_missing_countries_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        country_registry(config_file=str(tmp_path / "nope.json"))


def test_unknown_selector_lists_available():
    with pytest.raises(SystemExit, match="available"):
        resolve_country("atlantis")


def test_unset_power_prefix_fails_loud():
    cc = config_from_dict(ENTRY)
    object.__setattr__(cc, "power_prefix", None)
    with pytest.raises(ValueError, match="power_prefix"):
        cc.is_power("TST_POW_PP_SOL")


def test_example_countries_file_is_valid():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "oglink_countries.example.json")) as f:
        data = json.load(f)
    cc = config_from_dict(data["countries"][0])
    assert cc.power_prefix and cc.og_repo and cc.scenario.og_start_year


# --- guardrail: power_prefix zero-match -------------------------------------------

def test_capex_wrong_prefix_raises_naming_codes(tmp_path):
    base, reform = tmp_path / "b", tmp_path / "r"
    for d in (base, reform):
        d.mkdir()
        _write_capex(str(d), [("RE1", "OTHER_POW_PP", 2026, 1.0)])
    cc = config_from_dict(ENTRY)
    with pytest.raises(ValueError) as e:
        signals.power_capex_increment(str(base), str(reform), cc)
    assert "TST_POW" in str(e.value) and "OTHER_POW_PP" in str(e.value)


def test_capex_public_only_no_markers_warns_and_zeroes(tmp_path, capsys):
    base, reform = tmp_path / "b", tmp_path / "r"
    for d, v in ((base, 1.0), (reform, 3.0)):
        d.mkdir()
        _write_capex(str(d), [("RE1", "TST_POW_PP_SOL", 2026, v)])   # power, but no _TD tech
    cc = config_from_dict(ENTRY)
    inc = signals.power_capex_increment(str(base), str(reform), cc, public_only=True)
    assert float(inc.sum()) == 0.0
    assert "public marker" in capsys.readouterr().out


def test_capex_matching_prefix_gives_delta(tmp_path):
    base, reform = tmp_path / "b", tmp_path / "r"
    for d, v in ((base, 1.0), (reform, 3.0)):
        d.mkdir()
        _write_capex(str(d), [("RE1", "TST_POW_PP_SOL", 2026, v)])
    cc = config_from_dict(ENTRY)
    inc = signals.power_capex_increment(str(base), str(reform), cc)
    assert float(inc.loc[2026]) == pytest.approx(2.0)


# --- guardrail: exact emission species --------------------------------------------

def test_emissions_exact_species_no_substring_sum(tmp_path):
    d = tmp_path / "s"; d.mkdir()
    _write_emissions(str(d))
    cc = config_from_dict({**ENTRY, "co2_emission": "CO2"})
    s = signals.emissions_by_year(str(d), cc)
    assert float(s.loc[2026]) == pytest.approx(10.0)     # CO2 only -- NOT 110 (CO2 + CO2EQ)


def test_emissions_missing_species_raises_listing_present(tmp_path):
    d = tmp_path / "s"; d.mkdir()
    _write_emissions(str(d))
    cc = config_from_dict(ENTRY)                          # co2_emission = CO2EQ (present)
    with pytest.raises(ValueError) as e:
        signals.emissions_by_year(str(d), cc, species="PM2_5")
    assert "PM2_5" in str(e.value) and "CO2EQ" in str(e.value)


# --- guardrail: electricity dual fuel/region --------------------------------------

def test_dual_generic_elc_multimatch_raises(tmp_path):
    d = tmp_path / "s"; d.mkdir()
    _write_ebb4(str(d), fuels=("ELC001", "ELC002"))
    with pytest.raises(ValueError, match="electricity_fuel"):
        signals.commodity_shadow_price(str(d))
    # a single ELC commodity still resolves via the generic fallback
    d2 = tmp_path / "s2"; d2.mkdir()
    _write_ebb4(str(d2), fuels=("ELC001",))
    assert not signals.commodity_shadow_price(str(d2)).empty


def test_dual_multi_region_warns_but_works(tmp_path, capsys):
    d = tmp_path / "s"; d.mkdir()
    _write_ebb4(str(d), fuels=("TST_HOU_ELE",), regions=("RE1", "RE2"))
    s = signals.commodity_shadow_price(str(d), fuel="TST_HOU_ELE")
    assert not s.empty
    assert "AVERAGED across regions" in capsys.readouterr().out


# --- price-source provenance -------------------------------------------------------

def test_energy_price_ratio_records_resolved_source(tmp_path):
    # 'auto' on a pure-MUIOGO export (no workbook) resolves to the levelized 'lcoe' source and records
    # its provenance (resolved kind + busbar) so the run's manifest shows WHICH source drove the price.
    def _write_lcoe(d):
        for fname, col, tech, val in (
                ("AnnualizedInvestmentCost.csv", "AnnualizedInvestmentCost", "GEN", 100.0),
                ("AnnualFixedOperatingCost.csv", "AnnualFixedOperatingCost", "GEN", 0.0),
                ("AnnualVariableOperatingCost.csv", "AnnualVariableOperatingCost", "MINE", 100.0)):
            (d / fname).write_text(f"t,y,{col}\n{tech},2026,{val}\n{tech},2027,{val}\n")
        (d / "ProductionByTechnologyByMode.csv").write_text(
            "f,t,y,ProductionByTechnologyByMode\nELC,GEN,2026,200\nELC,GEN,2027,200\n"
            "COAL,MINE,2026,200\nCOAL,MINE,2027,200\n")
        (d / "UseByTechnologyByMode.csv").write_text(
            "f,t,y,UseByTechnologyByMode\nCOAL,GEN,2026,200\nCOAL,GEN,2027,200\n")

    base, reform = tmp_path / "b", tmp_path / "r"
    for d in (base, reform):
        d.mkdir()
        _write_lcoe(d)
    resolved = {}
    out = signals.energy_price_ratio("auto", base_dir=str(base), reform_dir=str(reform), share=1.0,
                                     og_start_year=2026, n=5, busbar="ELC", resolved=resolved)
    assert resolved["requested"] == "auto" and resolved["kind"] == "lcoe" and resolved["busbar"] == "ELC"
    assert np.allclose(out, 1.0)                          # identical base/reform -> flat ratio


# --- health channel skip path ------------------------------------------------------

def _fake_ctx(country, tmp_path):
    country.scenario.base_dir = str(tmp_path / "b")
    country.scenario.reform_dir = str(tmp_path / "r")
    os.makedirs(country.scenario.base_dir, exist_ok=True)
    os.makedirs(country.scenario.reform_dir, exist_ok=True)
    ctx = SimpleNamespace(country=country, og_reform=None, extras={}, provenance=[],
                          clews_inputs={}, reform_tpi=None)
    ctx.log = lambda channel, **kv: (ctx.provenance.append({"channel": channel, **kv})
                                     or {"channel": channel, **kv})
    return ctx


def test_health_skips_when_no_emissions_export(tmp_path, capsys):
    ctx = _fake_ctx(config_from_dict(ENTRY), tmp_path)    # empty scenario dirs
    rec = channels.health(ctx)
    assert rec["skipped"] and "unavailable" in rec["reason"]
    assert "[skip] health" in capsys.readouterr().out


def test_health_skips_when_species_absent(tmp_path):
    ctx = _fake_ctx(config_from_dict(ENTRY), tmp_path)    # health_emission default PM2_5
    _write_emissions(ctx.country.scenario.base_dir)       # exports CO2/CO2EQ only
    _write_emissions(ctx.country.scenario.reform_dir)
    rec = channels.health(ctx)
    assert rec["skipped"] and "PM2_5" in rec["reason"]


# --- MUIOGO export preflight --------------------------------------------------------

def test_preflight_reports_missing_stems(tmp_path, capsys):
    d = tmp_path / "s"; d.mkdir()
    _write_ebb4(str(d))
    found = muiogo_run.preflight(str(d), label="base")
    out = capsys.readouterr().out
    assert found["EBb4_EnergyBalanceEachYear4_ICR"] is True
    assert found["CapitalInvestment"] is False
    assert "CapitalInvestment" in out and "missing" in out


# --- write-back region / commodity threading ---------------------------------------

def test_emit_carbon_penalty_uses_country_region(tmp_path):
    ctx = _fake_ctx(config_from_dict(ENTRY), tmp_path)
    ctx.og_reform = SimpleNamespace(T=5)
    channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)
    assert ctx.clews_inputs["EmissionsPenalty"]["region"] == "REGA"
    assert ctx.clews_inputs["EmissionsPenalty"]["emission"] == "CO2EQ"


def test_write_demand_addresses_spec_region_and_fuel(tmp_path):
    spec = {"og_activity": "sector_output", "og_index": 2, "clews_fuel": "TST_HOU_ELE",
            "region": "REGA", "start_year": 2026, "ratio_by_period": [1.0, 1.01]}
    path = clews_io.write_demand(spec, str(tmp_path))
    df = pd.read_csv(path)
    assert set(df["REGION"]) == {"REGA"} and set(df["CLEWS_FUEL"]) == {"TST_HOU_ELE"}


# --- review fixes: countries-file robustness ----------------------------------------

def test_cwd_countries_file_bad_entry_does_not_break_phl(tmp_path, monkeypatch, capsys):
    """A half-drafted ./oglink_countries.json (typo'd entry) must not take down resolve_country('phl')."""
    bad = {"countries": [{"name": "Draftland", "power_prefx": "TYPO"}]}
    (tmp_path / "oglink_countries.json").write_text(json.dumps(bad))
    monkeypatch.chdir(tmp_path)
    assert resolve_country("phl") is PHL                  # survives; the bad entry is skipped...
    assert "[guardrail]" in capsys.readouterr().out       # ...loudly


def test_cwd_countries_file_invalid_json_does_not_break_phl(tmp_path, monkeypatch, capsys):
    (tmp_path / "oglink_countries.json").write_text("{not json")
    monkeypatch.chdir(tmp_path)
    assert resolve_country("phl") is PHL
    assert "not valid JSON" in capsys.readouterr().out


def test_cwd_foreign_config_file_ignored(tmp_path, monkeypatch, capsys):
    (tmp_path / "oglink_countries.json").write_text(json.dumps({"some_other_project": True}))
    monkeypatch.chdir(tmp_path)
    assert resolve_country("phl") is PHL
    assert "no 'countries' list" in capsys.readouterr().out


def test_explicit_countries_file_bad_entry_raises(tmp_path):
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"countries": [{"name": "Draftland"}]}))
    with pytest.raises(ValueError, match="c.json"):
        country_registry(config_file=str(f))


def test_env_countries_file_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("OGLINK_COUNTRIES", str(tmp_path / "nope.json"))
    with pytest.raises(FileNotFoundError, match="OGLINK_COUNTRIES"):
        country_registry()


def test_json_shadow_captures_module_attr_key(tmp_path):
    """A user's own 'Philippines' entry must also capture the CLI's default selector 'phl'."""
    mine = {**ENTRY, "name": "Philippines", "un_code": "608", "og_repo": "og-phl", "gdp_musd": 999.0}
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"countries": [mine]}))
    assert resolve_country("phl", config_file=str(f)).gdp_musd == 999.0
    assert resolve_country("og-phl", config_file=str(f)).gdp_musd == 999.0


def test_nested_unknown_keys_rejected():
    with pytest.raises(ValueError, match="scenario key"):
        config_from_dict({**ENTRY, "scenario": {"base_dirs": "/x"}})
    with pytest.raises(ValueError, match="units key"):
        config_from_dict({**ENTRY, "units": {"money": "USD"}})


# --- review fixes: emissions species robustness --------------------------------------

def test_emissions_blank_species_cell_no_typeerror(tmp_path):
    """A blank 'e' cell (totals row) must not TypeError the missing-species diagnostic."""
    d = tmp_path / "s"; d.mkdir()
    path = d / "AnnualTechnologyEmissionByMode.csv"
    pd.DataFrame([
        {"r": "RE1", "t": "T1", "e": "CO2e", "m": 1, "y": 2026, "v": 5.0},
        {"r": "RE1", "t": "T1", "e": None, "m": 1, "y": 2026, "v": 99.0},
    ]).to_csv(path, index=False)
    cc = config_from_dict({**ENTRY, "co2_emission": "CO2e"})
    assert float(signals.emissions_by_year(str(d), cc).loc[2026]) == pytest.approx(5.0)
    with pytest.raises(signals.EmissionsSpeciesAbsent, match="CO2e"):   # diagnostic renders cleanly
        signals.emissions_by_year(str(d), cc, species="PM2_5")


def test_emissions_emission_column_name_recognized(tmp_path):
    d = tmp_path / "s"; d.mkdir()
    pd.DataFrame([{"r": "RE1", "t": "T1", "EMISSION": "CO2", "y": 2026, "v": 7.0},
                  {"r": "RE1", "t": "T1", "EMISSION": "CH4", "y": 2026, "v": 1.0}]).to_csv(
        d / "AnnualTechnologyEmissionByMode.csv", index=False)
    cc = config_from_dict({**ENTRY, "co2_emission": "CO2"})
    assert float(signals.emissions_by_year(str(d), cc).loc[2026]) == pytest.approx(7.0)


def test_emissions_no_species_column_is_absence(tmp_path):
    d = tmp_path / "s"; d.mkdir()
    pd.DataFrame([{"r": "RE1", "t": "T1", "y": 2026, "v": 7.0}]).to_csv(
        d / "AnnualTechnologyEmissionByMode.csv", index=False)
    cc = config_from_dict(ENTRY)
    with pytest.raises(signals.EmissionsSpeciesAbsent, match="no species column"):
        signals.emissions_by_year(str(d), cc)


def test_health_does_not_swallow_corrupt_emissions(tmp_path):
    """An emissions file that EXISTS but is unparseable is corruption, not absence -> raises."""
    ctx = _fake_ctx(config_from_dict(ENTRY), tmp_path)
    for d in (ctx.country.scenario.base_dir, ctx.country.scenario.reform_dir):
        open(os.path.join(d, "AnnualTechnologyEmissionByMode.csv"), "w").close()   # 0-byte file
    with pytest.raises(Exception) as e:
        channels.health(ctx)
    assert not isinstance(e.value, (FileNotFoundError, signals.EmissionsSpeciesAbsent))


# --- review fixes: eager price ratio + write-back validation -------------------------

def test_auto_price_ratio_gated_on_couplability():
    from oglink import experiments
    ctx = SimpleNamespace(concordance=None)
    assert experiments._auto_price_ratio(ctx) is None     # no CLEWS read, no crash
    ctx = SimpleNamespace(concordance=SimpleNamespace(energy_good_index=None))
    assert experiments._auto_price_ratio(ctx) is None


def test_emit_carbon_penalty_warns_on_absent_species(tmp_path, capsys):
    ctx = _fake_ctx(config_from_dict({**ENTRY, "co2_emission": "CO2e"}), tmp_path)
    _write_emissions(ctx.country.scenario.base_dir, species=(("CO2", 1.0), ("CH4", 1.0)))
    ctx.og_reform = SimpleNamespace(T=5)
    rec = channels.emit_carbon_penalty(ctx, carbon_price_usd_per_tco2=50.0)
    assert rec["species_in_export"] is False
    assert "nonexistent species" in capsys.readouterr().out


def test_emit_energy_demand_warns_on_blank_fuel(tmp_path, capsys):
    cc = config_from_dict({k: v for k, v in ENTRY.items() if k != "electricity_fuel"})
    ctx = _fake_ctx(cc, tmp_path)
    channels.emit_energy_demand(ctx, np.ones(5), og_index_override=2)
    assert "names NO target commodity" in capsys.readouterr().out
    assert ctx.clews_inputs["Demand"]["clews_fuel"] is None


def test_manifest_excludes_provenance_only_records(tmp_path):
    from oglink.manifest import write_run_manifest
    cc = config_from_dict(ENTRY)
    ctx = _fake_ctx(cc, tmp_path)
    ctx.log("investment", pct_gdp=0.1)
    ctx.log("energy_price_source", provenance_only=True, kind="lcoe")
    def fake_exp(ctx, solve):
        """A fake experiment."""
    path = write_run_manifest(str(tmp_path), fake_exp, cc, ctx)
    m = json.load(open(path))
    assert {c["id"] for c in m["channels"]} == {"investment"}
    assert any(p.get("channel") == "energy_price_source" for p in m["provenance"])


def test_viz_resolver_sees_json_countries(tmp_path):
    build = pytest.importorskip("oglink.viz.build")
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"countries": [ENTRY]}))
    assert build._resolve_country("og-tst", config_file=str(f)).name == "Testland"

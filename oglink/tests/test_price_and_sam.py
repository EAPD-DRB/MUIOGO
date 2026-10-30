"""Price + SAM fixtures: LCOE reconstruction on a closed-form case, SAM input-intensity, and the
concordance couplability gate. Pure numpy/pandas, no ogcore.
"""
import numpy as np
import pandas as pd
import pytest

from oglink import aggregation, lcoe
from oglink.contract import Concordance


# --- SAM input-intensity phi_j -------------------------------------------------

def _sam():
    # rows = commodity/activity/value-added; cols = the two activities. celec is the electricity input.
    idx = ["aind0", "aelec", "celec", "va"]
    cols = ["aind0", "aelec"]
    data = {
        "aind0": [0.0, 0.0, 20.0, 80.0],   # gross(aind0)=100, celec into aind0 = 20 -> phi_0 = 0.2
        "aelec": [0.0, 0.0, 5.0, 45.0],    # gross(aelec)=50,  celec into aelec = 5  -> phi_1 = 0.1
    }
    return pd.DataFrame(data, index=idx, columns=cols)


def test_input_intensity_matches_hand_computation():
    prod = {"Ind0": ["aind0"], "Elec": ["aelec"]}
    phi = aggregation.input_intensity(_sam(), prod, carrier="electricity")
    assert phi.shape == (2,)
    assert np.allclose(phi, [0.2, 0.1])


# --- concordance couplability gate --------------------------------------------

def test_concordance_isolated_electricity():
    prod = {"Ind": ["aind"], "Elec": ["aelec"]}
    cons = {"Goods": ["cind"], "Elec": ["celec"]}
    con = Concordance.from_dicts(prod, cons)
    assert con.energy_industry_index == 1
    assert con.energy_good_index == 1
    assert not con.unavailable


def test_concordance_fused_industry_is_unavailable():
    prod = {"Util": ["aelec", "awatr"]}          # electricity fused with water -> not isolable
    cons = {"Goods": ["celec"]}
    con = Concordance.from_dicts(prod, cons)
    assert con.energy_industry_index is None
    assert con.energy_good_index is None
    assert "energy_industry_index" in con.unavailable


# --- LCOE reconstruction on a single-tech closed-form case --------------------

def _write_lcoe_case(d, own_cost):
    """One gen tech GEN producing busbar ELE (100 units), Inv+Fixed+Var = own_cost, burning a fuel the
    model prices at zero -> LCOE == own_cost / 100."""
    (d / "ProductionByTechnologyByMode.csv").write_text(
        "r,t,f,y,m,ProductionByTechnologyByMode\nRE1,GEN,ELE,2025,1,100\n")
    (d / "UseByTechnologyByMode.csv").write_text(
        "r,t,f,y,m,UseByTechnologyByMode\nRE1,GEN,FUELX,2025,1,50\n")
    (d / "CommodityMarginalPrice.csv").write_text(
        "r,f,y,CommodityMarginalPrice\nRE1,FUELX,2025,0\n")             # a free fuel adds nothing
    (d / "AnnualizedInvestmentCost.csv").write_text(
        f"r,t,y,AnnualizedInvestmentCost\nRE1,GEN,2025,{own_cost - 500}\n")
    (d / "AnnualFixedOperatingCost.csv").write_text(
        "r,t,y,AnnualFixedOperatingCost\nRE1,GEN,2025,200\n")
    (d / "AnnualVariableOperatingCost.csv").write_text(
        "r,t,y,AnnualVariableOperatingCost\nRE1,GEN,2025,300\n")


def test_lcoe_by_year_closed_form(tmp_path):
    _write_lcoe_case(tmp_path, own_cost=1500)      # 1000 inv + 200 fixed + 300 var
    out = lcoe.lcoe_by_year(str(tmp_path), busbar="ELE")
    assert set(out) == {2025}
    assert np.isclose(out[2025], 15.0)             # 1500 / 100 busbar units


def test_lcoe_ratio_reform_over_base(tmp_path):
    base = tmp_path / "base"; base.mkdir()
    reform = tmp_path / "reform"; reform.mkdir()
    _write_lcoe_case(base, own_cost=1500)          # LCOE 15
    _write_lcoe_case(reform, own_cost=3000)        # LCOE 30
    ratio = lcoe.lcoe_ratio(str(base), str(reform), busbar="ELE")
    assert np.isclose(float(ratio.loc[2025]), 2.0)


def _write_plant_case(d, *, inputs, prices, own_cost=1000.0, generation=100.0):
    """A power plant PP producing busbar ELE and using ``inputs`` {commodity: quantity}, with the
    model's commodity ``prices`` {commodity: price}. Whatever produced those inputs, and in what unit,
    is deliberately absent: the price must not need to know."""
    (d / "ProductionByTechnologyByMode.csv").write_text(
        f"r,t,f,y,m,ProductionByTechnologyByMode\nRE1,PP,ELE,2025,1,{generation}\n")
    (d / "UseByTechnologyByMode.csv").write_text(
        "r,t,f,y,m,UseByTechnologyByMode\n" + "".join(f"RE1,PP,{f},2025,1,{q}\n" for f, q in inputs.items()))
    (d / "CommodityMarginalPrice.csv").write_text(
        "r,f,y,CommodityMarginalPrice\n" + "".join(f"RE1,{f},2025,{p}\n" for f, p in prices.items()))
    (d / "AnnualizedInvestmentCost.csv").write_text(f"r,t,y,AnnualizedInvestmentCost\nRE1,PP,2025,{own_cost}\n")
    (d / "AnnualFixedOperatingCost.csv").write_text("r,t,y,AnnualFixedOperatingCost\nRE1,PP,2025,0\n")
    (d / "AnnualVariableOperatingCost.csv").write_text("r,t,y,AnnualVariableOperatingCost\nRE1,PP,2025,0\n")
    return str(d)


def test_every_input_counts_at_its_model_price_whatever_its_unit(tmp_path):
    """Gas in PJ, biomass in tonnes and cooling water that is costly to supply all count:
    (1000 + 200*2 + 50*3 + 10*0.5) / 100."""
    d = _write_plant_case(tmp_path, inputs={"GAS": 200, "BIOMASS_T": 50, "COOLWATER": 10},
                          prices={"GAS": 2.0, "BIOMASS_T": 3.0, "COOLWATER": 0.5})
    assert np.isclose(lcoe.lcoe_by_year(d, "ELE")[2025], 15.55)


def test_cost_free_inputs_add_nothing(tmp_path):
    """Surplus water or an accounting flow has a model price of zero, so it cannot move the price."""
    d = _write_plant_case(tmp_path, inputs={"GAS": 200, "SURPLUS_WATER": 1e6}, prices={"GAS": 2.0, "SURPLUS_WATER": 0.0})
    assert np.isclose(lcoe.lcoe_by_year(d, "ELE")[2025], 14.0)


def test_an_input_without_a_price_is_free(tmp_path):
    d = _write_plant_case(tmp_path, inputs={"GAS": 200, "UNPRICED": 7}, prices={"GAS": 2.0})
    assert np.isclose(lcoe.lcoe_by_year(d, "ELE")[2025], 14.0)


def _write_years_case(d, *, gas_price, gas_use=200.0, own_cost=1000.0, generation=100.0, regions=None):
    """One plant over several years; ``gas_price`` {year: price}. ``regions`` {region: (gas use,
    price multiplier)} splits the plant's gas use and prices across regions."""
    ys = sorted(gas_price)
    regions = regions or {"RE1": (gas_use, 1.0)}
    (d / "ProductionByTechnologyByMode.csv").write_text(
        "r,t,f,y,m,ProductionByTechnologyByMode\n" + "".join(f"RE1,PP,ELE,{y},1,{generation}\n" for y in ys))
    (d / "UseByTechnologyByMode.csv").write_text(
        "r,t,f,y,m,UseByTechnologyByMode\n" + "".join(
            f"{r},PP,GAS,{y},1,{q}\n" for y in ys for r, (q, _) in regions.items()))
    (d / "CommodityMarginalPrice.csv").write_text(
        "r,f,y,CommodityMarginalPrice\n" + "".join(
            f"{r},GAS,{y},{gas_price[y] * m}\n" for y in ys for r, (_, m) in regions.items()))
    for stem in ("AnnualizedInvestmentCost", "AnnualFixedOperatingCost", "AnnualVariableOperatingCost"):
        c = own_cost if stem == "AnnualizedInvestmentCost" else 0
        (d / f"{stem}.csv").write_text(f"r,t,y,{stem}\n" + "".join(f"RE1,PP,{y},{c}\n" for y in ys))
    return str(d)


def test_a_price_spike_is_flagged_but_not_changed(tmp_path):
    prices = {2025: 2.0, 2026: 2.0, 2027: 30.0, 2028: 2.0, 2029: 2.0}
    d = _write_years_case(tmp_path, gas_price=prices)
    flags = lcoe.input_price_spikes(d, "ELE")
    assert [f["year"] for f in flags] == [2027] and flags[0]["top_input"] == "GAS"
    assert np.isclose(lcoe.lcoe_by_year(d, "ELE")[2027], (1000 + 200 * 30) / 100)   # price kept


def test_smooth_or_small_inputs_are_not_flagged(tmp_path):
    a = tmp_path / "smooth"; a.mkdir()
    smooth = _write_years_case(a, gas_price={2025: 2.0, 2026: 2.4, 2027: 3.0, 2028: 3.5})
    b = tmp_path / "small"; b.mkdir()                    # spiky, but gas is a sliver of the cost
    small = _write_years_case(b, gas_use=0.1, gas_price={2025: 2.0, 2026: 2.0, 2027: 40.0, 2028: 2.0})
    assert lcoe.input_price_spikes(smooth, "ELE") == [] and lcoe.input_price_spikes(small, "ELE") == []


def test_each_region_pays_its_own_price(tmp_path):
    """150 units of gas in RE1 at 2, 50 in RE2 at 6: (1000 + 300 + 300) / 100."""
    d = _write_years_case(tmp_path, gas_price={2025: 2.0}, regions={"RE1": (150, 1.0), "RE2": (50, 3.0)})
    assert np.isclose(lcoe.lcoe_by_year(d, "ELE")[2025], 16.0)


def test_regions_that_cannot_be_matched_stop_with_a_clear_message(tmp_path):
    d = _write_years_case(tmp_path, gas_price={2025: 2.0}, regions={"RE1": (150, 1.0), "RE2": (50, 3.0)})
    use = pd.read_csv(tmp_path / "UseByTechnologyByMode.csv").drop(columns="r")
    use.to_csv(tmp_path / "UseByTechnologyByMode.csv", index=False)
    with pytest.raises(ValueError, match="cannot be matched"):
        lcoe.lcoe_by_year(d, "ELE")

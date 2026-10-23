"""Price + SAM fixtures: LCOE reconstruction on a closed-form case, SAM input-intensity, and the
concordance couplability gate. Pure numpy/pandas, no ogcore.
"""
import numpy as np
import pandas as pd

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
    """One gen tech GEN producing busbar ELE (100 units), Inv+Fixed+Var = own_cost, no priced fuel chain
    -> LCOE == own_cost / 100."""
    (d / "ProductionByTechnologyByMode.csv").write_text(
        "r,t,f,y,m,ProductionByTechnologyByMode\nRE1,GEN,ELE,2025,1,100\n")
    (d / "UseByTechnologyByMode.csv").write_text(
        "r,t,f,y,m,UseByTechnologyByMode\nRE1,GEN,FUELX,2025,1,50\n")   # FUELX has no producer -> alloc=0
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

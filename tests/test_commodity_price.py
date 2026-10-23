"""The annual commodity price MUIOGO rebuilds from the balance-row shadow prices.

MUIO 5.7 removed the single annual balance row the price used to come from.
These pin the weighting rules on small hand-checkable cases.
"""

import pandas as pd
import pytest

from Classes.Case.CommodityPrice import annual_commodity_price

TS = ["D", "N"]  # two timeslices, day 0.25 and night 0.75 of the year
YEAR_SPLIT = pd.DataFrame({"r": "R", "y": "2030", "l": TS, "YearSplit": [0.25, 0.75]})
TS_SEASON = {"D": "S1", "N": "S1"}


def _frame(columns, rows):
    return pd.DataFrame(rows, columns=columns)


def _price(levels, ts_duals=(), season_duals=(), yearly=(),
           profile=(), use=(), use_season=()):
    out = annual_commodity_price(
        levels,
        _frame(["r", "l", "f", "y", "dual"], ts_duals),
        _frame(["r", "ls", "f", "y", "dual"], season_duals),
        _frame(["r", "f", "y", "dual"], yearly),
        YEAR_SPLIT, TS_SEASON,
        _frame(["r", "f", "y", "l", "SpecifiedDemandProfile"], profile),
        _frame(["r", "l", "f", "y", "use"], use),
        _frame(["r", "ls", "f", "y", "use"], use_season),
    )
    return dict(zip(out["f"], out["price"]))


TS_DUALS = [("R", "D", "ELC", "2030", 40.0), ("R", "N", "ELC", "2030", 10.0)]


def test_commodity_with_demand_profile_is_weighted_by_the_profile():
    price = _price({"ELC": "Ts"}, ts_duals=TS_DUALS,
                   profile=[("R", "ELC", "2030", "D", 0.6), ("R", "ELC", "2030", "N", 0.4)],
                   yearly=[("R", "ELC", "2030", 99.0)])
    # 0.6*40 + 0.4*10; specified demand does not enter the yearly rows.
    assert price["ELC"] == pytest.approx(28.0)


def test_commodity_without_profile_is_weighted_by_when_it_is_used():
    price = _price({"ELC": "Ts"}, ts_duals=TS_DUALS,
                   use=[("R", "D", "ELC", "2030", 3.0), ("R", "N", "ELC", "2030", 1.0)],
                   yearly=[("R", "ELC", "2030", 2.0)])
    # 0.75*40 + 0.25*10, plus the yearly row a use also enters.
    assert price["ELC"] == pytest.approx(32.5 + 2.0)


def test_unused_commodity_falls_back_to_timeslice_length():
    price = _price({"ELC": "Ts"}, ts_duals=TS_DUALS)
    assert price["ELC"] == pytest.approx(0.25 * 40 + 0.75 * 10)


def test_annual_commodity_uses_its_yearly_balance_row():
    price = _price({"COA": "An"}, yearly=[("R", "COA", "2030", 7.5)])
    assert price["COA"] == pytest.approx(7.5)


def test_season_commodity_is_weighted_by_use_per_season():
    price = _price({"WAT": "Se"},
                   season_duals=[("R", "S1", "WAT", "2030", 12.0)],
                   use=[("R", "D", "WAT", "2030", 1.0)],
                   use_season=[("R", "S1", "WAT", "2030", 1.0)])
    # One season carries all the use, so its price is the annual price.
    assert price["WAT"] == pytest.approx(12.0)


def test_duplicate_yearly_rows_are_added_back_together():
    """Model files with duplicate yearly rows split one shadow price between
    them; write_csv adds them before they reach this function."""
    from Classes.Case import CommodityPrice
    results = pd.DataFrame({
        "parameter": ["EBb4_EnergyBalanceEachYear4_ICR", "EB_TimesliceAnnualBalance"],
        "id": ["R,COA,2030", "R,COA,2030"],
        "value": [0.0, 0.0], "dual": [3.0, 4.5],
    })
    rows = [CommodityPrice._rows(results, n, ["r", "f", "y"]) for n in CommodityPrice._YEARLY_ROWS]
    yearly = CommodityPrice._concat(rows, ["r", "f", "y", "dual"]).groupby(
        ["r", "f", "y"], as_index=False)["dual"].sum()
    assert _price({"COA": "An"}, yearly=yearly.values.tolist())["COA"] == pytest.approx(7.5)


def test_results_from_the_older_model_get_a_price_too():
    """The 5.4 model names its timeslice balance EBa11_EnergyBalanceEachTS5 and carries a duplicate
    yearly row; regenerating old results must still produce the price."""
    from Classes.Case import CommodityPrice
    results = pd.DataFrame({
        "parameter": ["EBa11_EnergyBalanceEachTS5", "EBa11_EnergyBalanceEachTS5",
                      "EBb4_EnergyBalanceEachYear4_ICR", "EBb4_EnergyBalanceEachYear4"],
        "id": ["R,D,ELC,2030", "R,N,ELC,2030", "R,ELC,2030", "R,ELC,2030"],
        "value": [0.0] * 4, "dual": [40.0, 10.0, 0.5, 1.5],
    })
    ts = CommodityPrice._concat([CommodityPrice._rows(results, n, ["r", "l", "f", "y"])
                                 for n in CommodityPrice._TS_BALANCES], ["r", "l", "f", "y", "dual"])
    yearly = CommodityPrice._concat([CommodityPrice._rows(results, n, ["r", "f", "y"])
                                     for n in CommodityPrice._YEARLY_ROWS], ["r", "f", "y", "dual"])
    yearly = yearly.groupby(["r", "f", "y"], as_index=False)["dual"].sum()
    price = _price({"ELC": "Ts"}, ts_duals=ts.values.tolist(), yearly=yearly.values.tolist(),
                   use=[("R", "D", "ELC", "2030", 1.0), ("R", "N", "ELC", "2030", 3.0)])
    assert price["ELC"] == pytest.approx(0.25 * 40 + 0.75 * 10 + 2.0)

"""The anchored CLEWS-CSV matcher (signals._find): it must return the EXACT stem and never a longer
decorated sibling that merely contains it -- the real siblings exist in a live MUIOGO run dir
(RateOfProductionByTechnologyByMode, CapitalInvestmentStorage, DiscountedCapitalInvestment).
"""
import os

import pytest

from oglink import signals


def _touch(d, *names):
    for n in names:
        (d / n).write_text("r,t,y,v\n")


def test_find_rejects_decorated_siblings(tmp_path):
    _touch(tmp_path,
           "CapitalInvestment.csv", "CapitalInvestmentStorage.csv", "DiscountedCapitalInvestment.csv",
           "ProductionByTechnologyByMode.csv", "RateOfProductionByTechnologyByMode.csv")
    assert os.path.basename(signals._find(str(tmp_path), "CapitalInvestment")) == "CapitalInvestment.csv"
    assert os.path.basename(
        signals._find(str(tmp_path), "ProductionByTechnologyByMode")) == "ProductionByTechnologyByMode.csv"


def test_find_accepts_region_and_year_decoration(tmp_path):
    _touch(tmp_path, "RE1_CapitalInvestment_2050.csv")     # only the region+year-decorated file present
    assert os.path.basename(
        signals._find(str(tmp_path), "CapitalInvestment")) == "RE1_CapitalInvestment_2050.csv"


def test_find_bymode_and_plain_are_distinct(tmp_path):
    _touch(tmp_path, "AnnualTechnologyEmission.csv", "AnnualTechnologyEmissionByMode.csv")
    assert os.path.basename(
        signals._find(str(tmp_path), "AnnualTechnologyEmission")) == "AnnualTechnologyEmission.csv"
    assert os.path.basename(
        signals._find(str(tmp_path), "AnnualTechnologyEmissionByMode")) == "AnnualTechnologyEmissionByMode.csv"


def test_find_raises_when_absent(tmp_path):
    with pytest.raises(FileNotFoundError):
        signals._find(str(tmp_path), "NoSuchMetric")

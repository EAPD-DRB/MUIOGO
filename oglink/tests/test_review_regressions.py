from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from oglink import channels, lcoe
from oglink.country import PHL, config_from_dict
from oglink.framework import ExperimentContext


def _health_context():
    c = replace(PHL, scenario=replace(PHL.scenario, og_start_year=2025),
                gbd_burden_csv=None)
    return ExperimentContext(country=c, og_reform=SimpleNamespace(e=np.ones((20, 80, 7)), E=20))


def test_health_uses_og_calendar_window(monkeypatch):
    ratio = pd.Series([1.0] * 10 + [0.5] * 10, index=range(2015, 2035))
    monkeypatch.setattr(channels.signals, 'emissions_ratio', lambda *a, **k: ratio)
    result = channels.health(_health_context(), enable_mortality=False,
                             morbidity_profile=np.ones(80))
    assert result['emissions_change'] == pytest.approx(-0.5)
    assert result['morbidity_benefit'] > 0


def test_health_rejects_missing_og_window(monkeypatch):
    ratio = pd.Series([1.0] * 10, index=range(2015, 2025))
    monkeypatch.setattr(channels.signals, 'emissions_ratio', lambda *a, **k: ratio)
    with pytest.raises(ValueError, match='OG window 2025-2034'):
        channels.health(_health_context(), enable_mortality=False)


def _write_case(path, prod, use, costs):
    path.mkdir()
    for stem, rows, keys in (
        (lcoe.PROD_STEM, prod, ['r', 't', 'f', 'y']),
        (lcoe.USE_STEM, use, ['r', 't', 'f', 'y']),
        (lcoe.PRICE_STEM, [['R1', 'GAS', 2025, 2], ['R1', 'GAS', 2030, 2],
                           ['R2', 'GAS', 2025, 2]], ['r', 'f', 'y']),
    ):
        pd.DataFrame(rows, columns=keys + [stem]).to_csv(path / (stem + '.csv'), index=False)
    for i, stem in enumerate(lcoe.COST_STEMS):
        rows = [row[:-1] + [row[-1] if i == 0 else 0] for row in costs]
        pd.DataFrame(rows, columns=['r', 't', 'y', stem]).to_csv(path / (stem + '.csv'), index=False)


def test_future_cogeneration_does_not_change_past_price(tmp_path):
    prod = [['R1', 'CHP', 'ELE', 2025, 100], ['R1', 'CHP', 'ELE', 2030, 100],
            ['R1', 'CHP', 'HEAT', 2030, 100]]
    use = [['R1', 'LOAD', 'HEAT', 2030, 100], ['R1', 'CHP', 'GAS', 2025, 100],
           ['R1', 'CHP', 'GAS', 2030, 100]]
    costs = [['R1', 'CHP', 2025, 100], ['R1', 'CHP', 2030, 100]]
    _write_case(tmp_path / 'case', prod, use, costs)
    result = lcoe.lcoe_by_year(str(tmp_path / 'case'), 'ELE')
    assert result[2025] == pytest.approx(3.0)  # all own + input cost belongs to electricity
    assert result[2030] == pytest.approx(1.5)  # split equally with useful heat


def test_cogeneration_keeps_regional_costs_separate(tmp_path):
    prod = [['R1', 'CHP', 'ELE', 2025, 100], ['R1', 'CHP', 'HEAT', 2025, 100],
            ['R2', 'CHP', 'ELE', 2025, 100]]
    use = [['R1', 'LOAD', 'HEAT', 2025, 100], ['R1', 'CHP', 'GAS', 2025, 100],
           ['R2', 'CHP', 'GAS', 2025, 100]]
    costs = [['R1', 'CHP', 2025, 100], ['R2', 'CHP', 2025, 300]]
    _write_case(tmp_path / 'case', prod, use, costs)
    # R1 electricity: (100 + 100*2)/2 = 150. R2: 300 + 100*2 = 500.
    assert lcoe.lcoe_by_year(str(tmp_path / 'case'), 'ELE')[2025] == pytest.approx(650 / 200)


def test_future_heat_consumption_does_not_make_current_dump_useful(tmp_path):
    prod = [['R1', 'CHP', 'ELE', 2025, 100], ['R1', 'CHP', 'HEAT', 2025, 100],
            ['R1', 'CHP', 'ELE', 2030, 100], ['R1', 'CHP', 'HEAT', 2030, 100]]
    use = [['R1', 'LOAD', 'HEAT', 2030, 100]]
    costs = [['R1', 'CHP', 2025, 100], ['R1', 'CHP', 2030, 100]]
    _write_case(tmp_path / 'case', prod, use, costs)
    result = lcoe.lcoe_by_year(str(tmp_path / 'case'), 'ELE')
    assert result[2025] == pytest.approx(1.0)
    assert result[2030] == pytest.approx(0.5)


def _country(**overrides):
    entry = dict(name='Indonesia', un_code='360', og_repo='og-idn',
                 gdp_musd=1000, og_start_year=2025, power_prefix='IDN_POW')
    entry.update(overrides)
    return config_from_dict(entry)


def test_foreign_country_has_no_philippines_health_default():
    assert PHL.gbd_burden_csv is not None
    assert _country(name="Exampleland").gbd_burden_csv is None


def test_health_default_requires_matching_year():
    c = config_from_dict(dict(name='Philippines', un_code='608', og_repo='og-phl',
                             gdp_musd=1000, og_start_year=2025, power_prefix='PHL_POW',
                             gbd_year=1999))
    assert c.gbd_burden_csv is None


@pytest.mark.parametrize('explicit', [None, '/custom/indonesia.csv'])
def test_explicit_health_source_is_preserved(explicit):
    assert _country(gbd_burden_csv=explicit).gbd_burden_csv == explicit

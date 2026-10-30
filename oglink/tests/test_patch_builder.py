import math

import pytest

from oglink.patch import build_clews_patch


def build(**overrides):
    args = dict(case='case', scenario='POLICY', demand_commodity='FINAL', case_years={2020, 2030, 2031},
                start_year=2026, demand_ratio_by_year={2030: 1.1, 2031: 0.9},
                base_sad_by_year={2030: 100, 2031: 200})
    args.update(overrides)
    return build_clews_patch(**args)


def test_absolute_values_and_application_shape():
    patch = build()
    assert [c['value'] for c in patch['changes']] == pytest.approx([110, 180])
    assert all(set(c) == {'group', 'code', 'year', 'value', 'scenario'} for c in patch['changes'])


def test_history_and_out_of_horizon_values_are_not_changed():
    patch = build(demand_ratio_by_year={2020: 2, 2030: 1.1, 2099: 2})
    assert [c['year'] for c in patch['changes']] == [2030]


def test_noop_suppression_includes_zero_base_cells():
    assert build(demand_ratio_by_year={2030: 1, 2031: 1 + 1e-12})['changes'] == []
    assert build(base_sad_by_year={2030: 0, 2031: 100},
                 demand_ratio_by_year={2030: 2, 2031: 1})['changes'] == []


@pytest.mark.parametrize('overrides', [
    {'base_sad_by_year': {}}, {'base_sad_by_year': {2030: 0}},
    {'base_sad_by_year': {2030: 100}}, {'demand_ratio_by_year': {2030: 0}},
    {'demand_ratio_by_year': {2030: -1}}, {'demand_ratio_by_year': {2030: math.nan}},
    {'demand_ratio_by_year': {2030: math.inf}}, {'base_sad_by_year': {2030: -1}},
    {'base_sad_by_year': {2030: math.inf}}, {'base_sad_by_year': {2030: 1e308},
                                         'demand_ratio_by_year': {2030: 1e308}}])
def test_invalid_or_structural_demand_change_is_rejected(overrides):
    with pytest.raises(ValueError):
        build(**overrides)


def test_unchanged_emissions_are_suppressed_against_effective_values():
    patch = build(demand_ratio_by_year={2030: 1}, emissions={'species': 'CO2e',
        'value_by_year': {2030: 50, 2031: 70}, 'base_by_year': {2030: 50, 2031: 60}})
    assert [(c['group'], c['year'], c['value']) for c in patch['changes']] == [('EmissionsPenalty', 2031, 70)]


def test_discount_rate_never_enters_changes():
    deferred = [{'artifact': 'DiscountRate', 'rate': 0.05}]
    assert build(deferred=deferred)['deferred'] == deferred
    assert all(c['group'] != 'DiscountRate' for c in build(deferred=deferred)['changes'])

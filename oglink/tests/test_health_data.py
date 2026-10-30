"""Validate the real bundled GBD records and their complete path into health inputs."""
import csv
import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from oglink import channels, country, health_profile
from oglink.framework import ExperimentContext

DATA = Path(__file__).resolve().parents[1] / 'IHME-GBD_2023_DATA'
COUNTRIES = [
    ('Philippines', '608', 'og-phl'),
    ('Indonesia', '360', 'og-idn'),
    ('South Africa', '710', 'og-zaf'),
    ('Ethiopia', '231', 'og-eth'),
]


def _config(name, code, repo):
    return country.config_from_dict(dict(
        name=name, un_code=code, og_repo=repo, power_prefix='TEST_POW',
        gdp_musd=1000, og_start_year=2025))


@pytest.mark.parametrize('name,code,repo', COUNTRIES)
def test_bundled_country_records_are_complete_and_consistent(name, code, repo):
    c = _config(name, code, repo)
    with open(c.gbd_burden_csv, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1118
    assert {r['location_name'] for r in rows} == {name}
    assert {r['year'] for r in rows} == {'2023'}
    assert {r['rei_name'] for r in rows} == {'Ambient particulate matter pollution'}
    assert {r['sex_name'] for r in rows} == {'Both'}
    assert {r['population_group_name'] for r in rows} == {'All Population'}
    key_fields = ('location_id', 'year', 'population_group_id', 'sex_id', 'age_id',
                  'rei_id', 'cause_id', 'measure_id', 'metric_id')
    assert len({tuple(r[k] for k in key_fields) for r in rows}) == len(rows)
    for r in rows:
        lower, value, upper = (float(r[k]) for k in ('lower', 'val', 'upper'))
        assert all(math.isfinite(v) for v in (lower, value, upper))
        assert 0 <= lower <= value <= upper
    labels = {g[0] for g in health_profile.GBD_GROUPS}
    deaths = [r for r in rows if r['measure_name'] == 'Deaths' and r['cause_name'] == 'All causes']
    for metric in ('Number', 'Rate'):
        assert labels <= {r['age_name'] for r in deaths if r['metric_name'] == metric}
    # Totals must sum disjoint age bins, never the overlapping summary bins also in the CSV.
    expected = math.fsum(float(r['val']) for r in deaths
                         if r['metric_name'] == 'Number' and r['age_name'] in labels)
    assert health_profile.total_deaths_from_gbd(
        c.gbd_burden_csv, name, 2023, key_col='cause_name', key_value='All causes'
    ) == pytest.approx(expected)
    mortality = health_profile.build_profile_from_gbd(
        c.gbd_burden_csv, name, 2023, key_col='cause_name', key_value='All causes')
    morbidity = health_profile.build_morbidity_profile_from_gbd(c.gbd_burden_csv, name, 2023)
    for profile in (mortality, morbidity):
        assert profile.shape == (100,)
        assert np.isfinite(profile).all() and (profile >= 0).all()
        assert profile.max() == pytest.approx(1.0)
    assert health_profile.morbidity_yld_rate_from_gbd(c.gbd_burden_csv, name, 2023) > 0
    assert health_profile.total_yld_from_gbd(c.gbd_burden_csv, name, 2023) > 0


@pytest.mark.parametrize('name,code,repo', COUNTRIES)
def test_real_country_data_reaches_mortality_and_productivity(name, code, repo, tmp_path):
    c = _config(name, code, repo)
    paths = []
    for side in ('base', 'reform'):
        path = tmp_path / side
        path.mkdir()
        # History is identical. The improvement starts exactly at OG period zero.
        pd.DataFrame([
            ['RE1', 'TEST_POW', 'PM2_5', y, 50 if side == 'reform' and y >= 2025 else 100]
            for y in range(2015, 2035)
        ], columns=['r', 't', 'e', 'y', 'AnnualTechnologyEmission']).to_csv(
            path / 'AnnualTechnologyEmission.csv', index=False)
        paths.append(str(path))
    c.scenario = replace(c.scenario, base_dir=paths[0], reform_dir=paths[1])
    p = SimpleNamespace(E=20, e=np.ones((30, 80, 7)))
    ctx = ExperimentContext(country=c, og_reform=p)
    result = channels.health(ctx)
    deaths = health_profile.total_deaths_from_gbd(
        c.gbd_burden_csv, name, 2023, key_col='cause_name', key_value='All causes')
    assert not result.get('skipped')
    assert result['emissions_change'] == pytest.approx(-0.5)
    assert ctx.extras['health_shock']['excess_deaths'] == pytest.approx(
        -0.5 * c.pm25_dose_response * deaths)
    np.testing.assert_array_equal(p.e[0], np.ones((80, 7)))  # phase-in begins without a jump
    assert np.max(p.e[5] - 1.0) > 0
    assert np.isfinite(p.e).all()


def test_bundled_file_hashes_match_provenance():
    manifest = json.loads((DATA / 'sources.json').read_text())
    entries = {**manifest['files'], manifest['reference']['file']: manifest['reference']}
    assert set(entries) == {p.name for p in DATA.glob('*.csv')}
    for filename, entry in entries.items():
        assert hashlib.sha256((DATA / filename).read_bytes()).hexdigest() == entry['sha256']


@pytest.mark.parametrize('field,value', [
    ('year', '2021'), ('sex_name', 'Male'),
    ('rei_name', 'Household air pollution from solid fuels'),
    ('population_group_name', 'Other population'),
    ('measure_name', 'YLDs (Years Lived with Disability)'),
    ('metric_name', 'Percent'), ('cause_name', 'Stroke'),
])
def test_default_does_not_select_an_incompatible_export(tmp_path, monkeypatch, field, value):
    row = dict(location_name='Indonesia', year='2023', sex_name='Both',
               rei_name='Ambient particulate matter pollution',
               population_group_name='All Population', measure_name='Deaths',
               metric_name='Rate', cause_name='All causes')
    row[field] = value
    path = tmp_path / 'gbd.csv'
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    monkeypatch.setattr(country.glob, 'glob', lambda *a: [str(path)])
    assert country._resolve_gbd_csv('Indonesia', 2023) is None


@pytest.mark.parametrize('explicit', [None, '/custom/export.csv'])
def test_explicit_health_configuration_does_not_scan_defaults(monkeypatch, explicit):
    def unexpected_scan(*args):
        raise AssertionError('explicit GBD settings must not inspect defaults')
    monkeypatch.setattr(country, '_resolve_gbd_csv', unexpected_scan)
    c = country.config_from_dict(dict(name='Indonesia', un_code='360', og_repo='og-idn',
                                     power_prefix='TEST', gdp_musd=1000, og_start_year=2025,
                                     gbd_burden_csv=explicit))
    assert c.gbd_burden_csv == explicit

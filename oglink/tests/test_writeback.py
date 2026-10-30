import dataclasses
import json
from types import SimpleNamespace

import pytest

from oglink import clews_case, cli, country, writeback


@pytest.fixture
def setup(tmp_path, monkeypatch):
    case = tmp_path / 'case'
    (case / 'view').mkdir(parents=True)
    (case / 'res/POLICY_RUN/csv').mkdir(parents=True)
    (case / 'genData.json').write_text(json.dumps({
        'osy-comm': [{'Comm': 'ELC002', 'CommId': 'C'}], 'osy-years': [2030, 2031],
        'osy-scenarios': [{'ScenarioId': 'SC_0'}, {'ScenarioId': 'POLICY'}],
        'osy-emis': [{'Emis': 'CO2e', 'EmisId': 'E'}]}))
    (tmp_path / 'Parameters.json').write_text(json.dumps({'RYC': [{'id': 'SAD', 'default': 0}], 'RYE': [{'id': 'EP', 'default': 0}]}))
    (case / 'RYC.json').write_text(json.dumps({'SAD': {
        'SC_0': [{'CommId': 'C', '2030': 100, '2031': 150}],
        'POLICY': [{'CommId': 'C', '2030': None, '2031': 200}]}}))
    (case / 'view/resData.json').write_text(json.dumps({'osy-cases': [{
        'Case': 'POLICY_RUN', 'Scenarios': [
            {'ScenarioId': 'SC_0', 'Active': True}, {'ScenarioId': 'POLICY', 'Active': True}]}]}))
    (case / 'RYE.json').write_text(json.dumps({'EP': {
        'SC_0': [{'EmisId': 'E', '2030': 0, '2031': 0}],
        'POLICY': [{'EmisId': 'E', '2030': None, '2031': None}]}}))
    cfg = dataclasses.replace(country.PHL, electricity_fuel='ELC001', demand_commodity='ELC002')
    monkeypatch.setattr(country, 'resolve_country', lambda selector, config_file=None: cfg)
    run = tmp_path / 'run'
    (run / 'clews_inputs').mkdir(parents=True)
    manifest = {'country': cfg.name, 'un_code': cfg.un_code,
                'scenario': {'reform_dir': str(case / 'res/POLICY_RUN/csv')},
                'concordance': {'energy_industry_index': 0, 'energy_good_index': 2}}
    (run / 'oglink_manifest.json').write_text(json.dumps(manifest))
    args = SimpleNamespace(country='phl', case='case', base_caserun='POLICY_RUN',
        scenario=None, countries=None, run=str(run), datastorage=str(tmp_path),
        with_emissions_penalty=False, dry_run=True, muiogo_url='http://localhost', solver='CBC')
    return SimpleNamespace(case=case, run=run, cfg=cfg, manifest=manifest, args=args)


def feedback(s, ratios=(1.1, 1.1), *, region='RE1', fuel='ELC001', driver='sector_output', index=0):
    p = s.run / 'clews_inputs/demand_scaling.csv'
    p.write_text('REGION,OG_ACTIVITY,OG_INDEX,CLEWS_FUEL,YEAR,DEMAND_RATIO\n' + ''.join(
        f'{region},{driver},{index},{fuel},{year},{ratio}\n'
        for year, ratio in zip((2030, 2031), ratios)))
    return p


def test_inherited_values_and_later_override_are_both_scaled(setup):
    s = setup
    feedback(s)
    writeback.run_writeback(s.args)
    patch_data = json.loads((s.run / 'clews_patch.json').read_text())
    assert [c['scenario'] for c in patch_data['changes']] == ['POLICY', 'POLICY']
    assert [c['value'] for c in patch_data['changes']] == pytest.approx([110, 220])



def test_lower_priority_explicit_target_is_rejected(setup):
    feedback(setup)
    setup.args.scenario = 'SC_0'
    with pytest.raises(ValueError, match='last active'):
        writeback.run_writeback(setup.args)


def test_explicit_zero_overrides_inherited_demand(setup):
    p = setup.case / 'RYC.json'
    data = json.loads(p.read_text())
    data['SAD']['POLICY'][0]['2030'] = 0
    p.write_text(json.dumps(data))
    values = clews_case.read_effective_sad(str(setup.case), 'POLICY_RUN', 'ELC002')
    assert values == {2030: 0, 2031: 200}


@pytest.mark.parametrize('field,bad', [
    ('region', 'OTHER'), ('fuel', 'ELC002'), ('driver', 'unknown'), ('index', 99)])
def test_feedback_identity_is_checked(setup, field, bad):
    feedback(setup, **{field: bad})
    with pytest.raises(ValueError):
        writeback.run_writeback(setup.args)
    assert not (setup.run / 'clews_patch.json').exists()


@pytest.mark.parametrize('bad', ['nan', 'inf', '-1'])
def test_nonphysical_ratios_are_rejected(setup, bad):
    feedback(setup, ratios=(bad, 1.1))
    with pytest.raises(ValueError, match='invalid demand-feedback ratio'):
        writeback.run_writeback(setup.args)


def test_duplicate_year_is_rejected(setup):
    path = feedback(setup)
    with path.open('a') as f:
        f.write('RE1,sector_output,0,ELC001,2030,1.2\n')
    with pytest.raises(ValueError, match='duplicate'):
        writeback.run_writeback(setup.args)


@pytest.mark.parametrize('kind', ['country', 'un_code', 'case', 'caserun', 'relative'])
def test_manifest_mismatch_is_rejected(setup, kind):
    feedback(setup)
    m = setup.manifest
    if kind in ('country', 'un_code'):
        m[kind] = 'wrong'
    elif kind == 'case':
        m['scenario']['reform_dir'] = str(setup.case.parent / 'other/res/POLICY_RUN/csv')
    elif kind == 'caserun':
        m['scenario']['reform_dir'] = str(setup.case / 'res/OTHER/csv')
    else:
        m['scenario']['reform_dir'] = 'relative/res/POLICY_RUN/csv'
    (setup.run / 'oglink_manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError):
        writeback.run_writeback(setup.args)
    assert not (setup.run / 'clews_patch.json').exists()


def test_missing_manifest_is_rejected(setup):
    feedback(setup)
    (setup.run / 'oglink_manifest.json').unlink()
    with pytest.raises(FileNotFoundError):
        writeback.run_writeback(setup.args)


def test_unchanged_feedback_never_posts(setup, monkeypatch, capsys):
    feedback(setup, ratios=(1, 1))
    setup.args.dry_run = False
    def fail(*args, **kwargs):
        pytest.fail('unchanged feedback must not POST')
    monkeypatch.setattr('oglink.writeback.apply_via_muiogo', fail)
    writeback.run_writeback(setup.args)
    assert json.loads((setup.run / 'clews_patch.json').read_text())['changes'] == []
    assert 'no patch was posted' in capsys.readouterr().out


def test_nonoverlapping_feedback_is_not_reported_as_unchanged(setup):
    p = feedback(setup, ratios=(1, 1))
    p.write_text(p.read_text().replace('2030', '2100').replace('2031', '2101'))
    with pytest.raises(ValueError, match='no years'):
        writeback.run_writeback(setup.args)


def test_emissions_changes_still_post_when_demand_is_unchanged(setup, monkeypatch):
    feedback(setup, ratios=(1, 1))
    (setup.run / 'clews_inputs/EmissionsPenalty.csv').write_text(
        'REGION,EMISSION,YEAR,VALUE\nRE1,CO2e,2030,50\n')
    setup.args.with_emissions_penalty = True
    setup.args.dry_run = False
    calls = []
    def apply(patch_data, *args, **kwargs):
        calls.append(patch_data)
        return {'warnings': []}
    monkeypatch.setattr('oglink.writeback.apply_via_muiogo', apply)
    writeback.run_writeback(setup.args)
    assert len(calls) == 1
    assert [c['group'] for c in calls[0]['changes']] == ['EmissionsPenalty']


def test_unchanged_emissions_are_suppressed_too(setup, monkeypatch):
    feedback(setup, ratios=(1, 1))
    (setup.run / 'clews_inputs/EmissionsPenalty.csv').write_text(
        'REGION,EMISSION,YEAR,VALUE\nRE1,CO2e,2030,0\n')
    setup.args.with_emissions_penalty = True
    setup.args.dry_run = False
    monkeypatch.setattr(writeback, 'apply_via_muiogo', lambda *a, **k: pytest.fail('must not POST'))
    assert writeback.run_writeback(setup.args)['status'] == 'unchanged'


@pytest.mark.parametrize('line', ['OTHER,CO2e,2030,50', 'RE1,PM2_5,2030,50',
                                 'RE1,CO2e,2030,nan', 'RE1,CO2e,2030,-1'])
def test_invalid_emissions_cannot_partially_apply_demand(setup, monkeypatch, line):
    feedback(setup)
    (setup.run / 'clews_inputs/EmissionsPenalty.csv').write_text('REGION,EMISSION,YEAR,VALUE\n' + line + '\n')
    setup.args.with_emissions_penalty = True
    setup.args.dry_run = False
    monkeypatch.setattr(writeback, 'apply_via_muiogo', lambda *a, **k: pytest.fail('must not POST'))
    with pytest.raises(ValueError):
        writeback.run_writeback(setup.args)
    assert not (setup.run / 'clews_patch.json').exists()


def test_discount_rate_is_deferred_and_never_becomes_a_change(setup):
    feedback(setup)
    (setup.run / 'clews_inputs/DiscountRate.csv').write_text('REGION,VALUE\nRE1,0.055\n')
    writeback.run_writeback(setup.args)
    patch = json.loads((setup.run / 'clews_patch.json').read_text())
    assert all(c['group'] == 'Demand' for c in patch['changes'])
    assert patch['deferred'][0]['artifact'] == 'DiscountRate'
    assert patch['deferred'][0]['rate'] == 0.055


def test_effective_sad_inherits_the_configured_default(setup):
    p = setup.case.parent / 'Parameters.json'
    p.write_text(json.dumps({'RYC': [{'id': 'SAD', 'default': 7}]}))
    p = setup.case / 'RYC.json'
    p.write_text(json.dumps({'SAD': {sc: [{'CommId': 'C', '2030': None, '2031': None}]
                                  for sc in ('SC_0', 'POLICY')}}))
    assert clews_case.read_effective_sad(setup.case, 'POLICY_RUN', 'ELC002') == {2030: 7, 2031: 7}


def test_inactive_scenario_does_not_override(setup):
    p = setup.case / 'view/resData.json'
    data = json.loads(p.read_text())
    data['osy-cases'][0]['Scenarios'][1]['Active'] = False
    p.write_text(json.dumps(data))
    assert clews_case.read_active_scenario_order(setup.case, 'POLICY_RUN') == ['SC_0']
    assert clews_case.read_effective_sad(setup.case, 'POLICY_RUN', 'ELC002') == {2030: 100, 2031: 150}


@pytest.mark.parametrize('kind', ['row', 'year', 'negative', 'nan', 'duplicate'])
def test_corrupt_source_demand_is_not_treated_as_inheritance(setup, kind):
    p = setup.case / 'RYC.json'
    data = json.loads(p.read_text())
    rows = data['SAD']['POLICY']
    if kind == 'row':
        rows.clear()
    elif kind == 'year':
        del rows[0]['2030']
    elif kind == 'duplicate':
        rows.append(dict(rows[0]))
    else:
        rows[0]['2030'] = -1 if kind == 'negative' else 'nan'
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        clews_case.read_effective_sad(setup.case, 'POLICY_RUN', 'ELC002')


@pytest.mark.parametrize('kind', ['empty', 'duplicate', 'unknown'])
def test_bad_caserun_order_is_rejected(setup, kind):
    p = setup.case / 'view/resData.json'
    data = json.loads(p.read_text())
    rows = data['osy-cases'][0]['Scenarios']
    if kind == 'empty':
        rows.clear()
    elif kind == 'duplicate':
        rows.append(dict(rows[0]))
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        clews_case.read_active_scenario_order(setup.case, 'UNKNOWN' if kind == 'unknown' else 'POLICY_RUN')


@pytest.mark.parametrize('bad', ['../case', 'case/../case', 'case\\other', '', '..'])
def test_invalid_case_name_is_rejected_before_reading(setup, bad):
    setup.args.case = bad
    with pytest.raises(ValueError, match='single non-empty name'):
        writeback.run_writeback(setup.args)


def test_missing_csv_directory_is_rejected(setup):
    (setup.case / 'res/POLICY_RUN/csv').rmdir()
    with pytest.raises(ValueError, match='CSV directory is missing'):
        writeback.run_writeback(setup.args)


def test_different_recorded_start_year_is_rejected(setup):
    setup.manifest['scenario']['og_start_year'] = 2000
    (setup.run / 'oglink_manifest.json').write_text(json.dumps(setup.manifest))
    with pytest.raises(ValueError, match='start year'):
        writeback.run_writeback(setup.args)


@pytest.mark.parametrize('content', [
    'YEAR,DEMAND_RATIO\n2030,1.1\n',
    'REGION,OG_ACTIVITY,OG_INDEX,CLEWS_FUEL,YEAR,DEMAND_RATIO,DEMAND_RATIO\n',
    'REGION,OG_ACTIVITY,OG_INDEX,CLEWS_FUEL,YEAR,DEMAND_RATIO\n',
    'REGION,OG_ACTIVITY,OG_INDEX,CLEWS_FUEL,YEAR,DEMAND_RATIO\nRE1,sector_output,0,ELC001,2030\n'])
def test_malformed_feedback_is_rejected(setup, content):
    (setup.run / 'clews_inputs/demand_scaling.csv').write_text(content)
    with pytest.raises(ValueError):
        writeback.run_writeback(setup.args)


def test_mixed_drivers_are_not_silently_overwritten(setup):
    p = feedback(setup)
    p.write_text(p.read_text().replace('RE1,sector_output,0,ELC001,2031',
                                     'RE1,consumption_good,2,ELC001,2031'))
    with pytest.raises(ValueError, match='multiple demand series'):
        writeback.run_writeback(setup.args)


def test_consumption_driver_uses_consumption_concordance(setup):
    feedback(setup, driver='consumption_good', index=2)
    assert writeback.run_writeback(setup.args)['status'] == 'dry_run'


def test_producer_to_writeback_preserves_mapping_and_precision(setup):
    from oglink import channels, clews_io
    from oglink.contract import Concordance
    from oglink.framework import ExperimentContext
    from oglink.manifest import write_run_manifest

    cfg = setup.cfg
    cfg.scenario = dataclasses.replace(cfg.scenario, og_start_year=2030,
        reform_dir=str(setup.case / 'res/POLICY_RUN/csv'))
    ctx = ExperimentContext(country=cfg, concordance=Concordance(0, 2))
    ratio = 1.000000123456789
    channels.emit_energy_demand(ctx, [ratio, 0.9])
    clews_io.write_all(ctx, str(setup.run / 'clews_inputs'))
    write_run_manifest(str(setup.run), 'coupled', cfg, ctx)
    writeback.run_writeback(setup.args)
    patch = json.loads((setup.run / 'clews_patch.json').read_text())
    assert patch['changes'][0]['value'] == 100 * ratio
    assert patch['changes'][0]['code'] == cfg.demand_commodity
    assert patch['changes'][1]['value'] == 180


def test_cli_dispatches_writeback_with_countries_and_dry_run(setup, monkeypatch):
    feedback(setup)
    seen = []
    def resolve(selector, config_file=None):
        seen.append((selector, config_file))
        return setup.cfg
    monkeypatch.setattr(country, 'resolve_country', resolve)
    result = cli.main(['writeback', '--run', str(setup.run), '--country', 'phl',
        '--countries', 'custom.json', '--case', 'case', '--base-caserun', 'POLICY_RUN',
        '--datastorage', str(setup.case.parent), '--dry-run'])
    assert result['status'] == 'dry_run'
    assert seen == [('phl', 'custom.json')]


def test_cli_reports_validation_errors_as_failure(setup):
    with pytest.raises(SystemExit, match='single non-empty name'):
        cli.main(['writeback', '--run', str(setup.run), '--country', 'phl', '--case', '../case'])


def test_server_warnings_are_not_reported_as_success(setup, monkeypatch):
    feedback(setup)
    setup.args.dry_run = False
    monkeypatch.setattr(writeback, 'apply_via_muiogo', lambda *a, **k: {'warnings': ['stale/no-op']})
    with pytest.raises(RuntimeError, match='stale/no-op'):
        writeback.run_writeback(setup.args)


def test_muiogo_bom_encoded_files_are_supported(setup):
    feedback(setup)
    files = [setup.case / 'genData.json', setup.case / 'RYC.json',
             setup.case / 'view/resData.json', setup.case.parent / 'Parameters.json',
             setup.run / 'oglink_manifest.json', setup.run / 'clews_inputs/demand_scaling.csv']
    for path in files:
        path.write_text(path.read_text(), encoding='utf-8-sig')
    assert writeback.run_writeback(setup.args)['status'] == 'dry_run'


def test_manifest_writer_canonicalizes_relative_paths(setup, monkeypatch):
    from oglink.framework import ExperimentContext
    from oglink.manifest import write_run_manifest

    monkeypatch.chdir(setup.case.parent)
    setup.cfg.scenario = dataclasses.replace(setup.cfg.scenario, base_dir='base/csv',
                                             reform_dir='case/res/POLICY_RUN/csv')
    ctx = ExperimentContext(country=setup.cfg)
    path = write_run_manifest(str(setup.run), 'coupled', setup.cfg, ctx)
    manifest = json.loads(open(path).read())
    assert manifest['scenario']['reform_dir'] == str(setup.case / 'res/POLICY_RUN/csv')
    assert manifest['scenario']['base_dir'] == str(setup.case.parent / 'base/csv')


def test_unsupported_region_is_rejected(setup):
    setup.cfg.clews_region = 'OTHER'
    with pytest.raises(ValueError, match='only region RE1'):
        writeback.run_writeback(setup.args)


def test_missing_demand_mapping_is_rejected(setup):
    setup.cfg.demand_commodity = None
    with pytest.raises(ValueError, match='configure demand_commodity'):
        writeback.run_writeback(setup.args)

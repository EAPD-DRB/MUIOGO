"""Run-page interaction and execution planning using real frontend modules."""
from pathlib import Path
from urllib.parse import urlsplit

import pytest

pytest.importorskip('pytest_playwright')
from playwright.sync_api import expect

WEBAPP = Path(__file__).resolve().parents[2] / 'WebAPP'


@pytest.fixture
def runs_page(page):
    styles = ['bootstrap.min.css', 'font-awesome.min.css', 'smartadmin-production.min.css',
              'smartadmin-skins.min.css', 'osy.css', 'muiogo.css']
    html = '<!doctype html><html><head>' + ''.join(
        f'<link rel="stylesheet" href="/References/smartadmin/css/{s}">' for s in styles
    ) + '</head><body>' + (WEBAPP / 'App/View/OGRuns.html').read_text() + '''
    <script src="/References/jquery/jquery-3.4.1.min.js"></script>
    <script type="module">
      import Runs from '/App/Controller/OGRuns.js';
      import {Ogc} from '/Classes/Ogc.Class.js';
      import {Message} from '/Classes/Message.Class.js';
      window.Runs = Runs; window.Ogc = Ogc;
      Message.smallBoxInfo = Message.warning = Message.danger = () => {};
      Runs.workspace = {country_id: 'ETH', country_name: 'Ethiopia'};
      Runs.entries = []; Runs.selected = {}; Runs.plan = []; Runs.running = false;
      Runs.monitorID = 0; Runs.pageToken = 1; Runs.isCurrent = () => true;
      Runs.initEvents(); Runs.render();
      window.ready = true;
    </script></body></html>'''

    def respond(route):
        path = urlsplit(route.request.url).path
        if path == '/':
            route.fulfill(body=html, content_type='text/html')
        elif (WEBAPP / path.lstrip('/')).is_file():
            route.fulfill(path=str(WEBAPP / path.lstrip('/')))
        else:
            route.abort()

    page.route('http://runs.test/**', respond)
    page.set_viewport_size({'width': 1280, 'height': 800})
    page.goto('http://runs.test/#/OGRuns')
    page.wait_for_function('window.ready')
    return page


SEED = '''() => {
    Runs.entries = Runs.flatten([{case: {country_id: 'ETH', casename: 'policy'}, runs: [
        {run_name: 'baseline', run_type: 'baseline', status: 'completed', reusable: true, time_path: false},
        {run_name: 'reform', run_type: 'reform', baseline_run: 'baseline', status: 'pending', reusable: false}
    ]}]);
    Runs.render();
}'''


def test_country_context_tracks_workspace(runs_page):
    page = runs_page
    expect(page.locator('#ogcRunCountryName')).to_have_text('Ethiopia')
    expect(page.locator('#ogcRunCountryFlag img')).to_have_attribute('src', 'References/flags/4x3/et.svg')
    page.evaluate("Runs.workspace = {country_id: 'ZAF', country_name: 'South Africa'}; Runs.render()")
    expect(page.locator('#ogcRunCountryName')).to_have_text('South Africa')
    expect(page.locator('#ogcRunCountryFlag img')).to_have_attribute('src', 'References/flags/4x3/za.svg')


def test_outcome_keeps_open_and_receives_inflight_log_after_render(runs_page):
    page = runs_page
    page.evaluate(SEED)
    page.evaluate("() => { Ogc.getRunStatus = () => new Promise(resolve => window.resolveLog = resolve); }")
    page.locator('[data-act="outcome"]').click()
    page.evaluate('Runs.render()')
    expect(page.locator('.ogc-history-log')).to_be_visible()
    page.evaluate("resolveLog({run_log: Array.from({length: 100}, (_, i) => 'Log line ' + i)})")
    expect(page.locator('.ogc-history-log pre')).to_contain_text('Log line 99')
    page.locator('.ogc-history-log pre').evaluate('e => e.scrollTop = 120')
    page.evaluate('Runs.render()')
    expect(page.locator('.ogc-history-log')).to_be_visible()
    assert page.locator('.ogc-history-log pre').evaluate('e => e.scrollTop') == 120
    page.locator('[data-act="outcome"]').click()
    page.evaluate('Runs.render()')
    expect(page.locator('.ogc-history-log')).to_be_hidden()


def test_new_execution_does_not_reuse_old_outcome_log(runs_page):
    page = runs_page
    page.evaluate(SEED)
    page.evaluate("Ogc.getRunStatus = async () => ({run_log: ['Previous execution']})")
    page.locator('[data-act="outcome"]').click()
    expect(page.locator('.ogc-history-log')).to_contain_text('Previous execution')
    page.evaluate("Runs.entries[0].completedAt = '2026-09-08T12:00:00Z'; Runs.render()")
    expect(page.locator('.ogc-history-log')).to_be_hidden()
    expect(page.locator('.ogc-history-log')).not_to_contain_text('Previous execution')


def test_idle_monitor_stops_and_refresh_discovers_external_job(runs_page):
    page = runs_page
    page.evaluate(SEED)
    page.evaluate("Ogc.getRunStatus = async () => ({run_log: ['Saved log']})")
    page.locator('[data-act="outcome"]').click()
    expect(page.locator('.ogc-history-log')).to_contain_text('Saved log')
    result = page.evaluate('''async () => {
        const timer = window.setTimeout;
        let timers = 0;
        window.setTimeout = (fn, ms) => ms === 2000 ? (++timers, 0) : timer(fn, ms);
        Ogc.getCases = async () => [{country_id:'ETH', casename:'policy'}];
        Ogc.getRuns = async () => Runs.entries.map(entry => entry.run);
        Ogc.getRunQueue = async () => ({active: {country_id: 'ETH', casename: 'policy', run_name: 'reform', state: 'running'}});
        Runs.startMonitor(1);
        const idleTimers = timers;
        document.querySelector('#ogcRefreshRuns').click();
        for (let i = 0; i < 40; i++) await Promise.resolve();
        Runs.monitorID++;
        window.setTimeout = timer;
        return {state: Runs.entries[1].state, idleTimers, timers};
    }''')
    assert result == {'state': 'running', 'idleTimers': 0, 'timers': 1}
    expect(page.locator('.ogc-history-log')).to_be_visible()
    expect(page.locator('.ogc-history-log')).to_contain_text('Saved log')


def test_monitor_stops_after_active_run_completes(runs_page):
    page = runs_page
    page.evaluate(SEED)
    result = page.evaluate('''async () => {
        const timer = window.setTimeout;
        let wake, timers = 0, statusCalls = 0;
        window.setTimeout = (fn, ms) => ms === 2000 ? (++timers, wake = fn, 0) : timer(fn, ms);
        Runs.entries[1].state = 'running';
        Ogc.getRunQueue = async () => ({active: null, queued: []});
        Ogc.getRunStatus = async () => {statusCalls++; return {run_state:'completed', reusable:true}};
        Runs.startMonitor(1);
        wake();
        for (let i = 0; i < 40; i++) await Promise.resolve();
        Runs.monitorID++;
        window.setTimeout = timer;
        return {state:Runs.entries[1].state, timers, statusCalls};
    }''')
    assert result == {'state': 'completed', 'timers': 1, 'statusCalls': 1}


@pytest.mark.parametrize('mode,baseline_mode,expected', [
    ('transition', False, ['baseline', 'reform']),
    ('transition', True, ['reform']),
    ('steady', True, ['baseline', 'reform']),
    ('steady', False, ['reform']),
])
def test_execution_mode_orders_matching_baseline_and_reform(runs_page, mode, baseline_mode, expected):
    page = runs_page
    page.evaluate(SEED)
    page.evaluate('''mode => {
        Runs.entries[0].run.time_path = mode;
        Runs.selected[Runs.entries[1].key] = true;
        window.submissions = [];
        Ogc.getRuns = async () => Runs.entries.map(entry => entry.run);
        Ogc.run = async (country, casename, name, timePath) => {
            submissions.push({name, timePath, disabled: document.querySelector('#ogcAnalysis').disabled});
            document.querySelector('#ogcAnalysis').value = timePath ? 'steady' : 'transition';
        };
        Runs.waitForTerminal = async job => {job.state = job.entry.state = 'completed'; return 'terminal'};
        Runs.load = async () => {};
        Runs.render();
    }''', baseline_mode)
    page.locator('#ogcAnalysis').select_option(mode)
    page.evaluate('Runs.runSelected()')
    submissions = page.evaluate('submissions')
    assert [s['name'] for s in submissions] == expected
    assert all(s['timePath'] == (mode == 'transition') and s['disabled'] for s in submissions)


def test_mode_changes_cached_result_and_rechecks_metadata_before_reuse(runs_page):
    page = runs_page
    page.evaluate(SEED)
    expect(page.locator('.ogc-cache-tag')).to_have_count(1)
    page.locator('#ogcAnalysis').select_option('transition')
    expect(page.locator('.ogc-cache-tag')).to_have_count(0)
    page.locator('#ogcAnalysis').select_option('steady')
    result = page.evaluate('''async () => {
        Runs.selected[Runs.entries[0].key] = true;
        Ogc.getRuns = async () => [{run_name:'baseline', time_path: true}];
        Ogc.getRunStatus = async () => ({run_state:'completed', reusable:true});
        const calls = [];
        Ogc.run = async (country, casename, run, mode) => calls.push(mode);
        Runs.waitForTerminal = async job => {job.state = 'completed'; return 'terminal'};
        Runs.load = async () => {};
        await Runs.runSelected();
        return calls;
    }''')
    assert result == [False]


def test_matching_transition_result_is_reused(runs_page):
    page = runs_page
    page.evaluate(SEED)
    page.locator('#ogcAnalysis').select_option('transition')
    result = page.evaluate('''async () => {
        Runs.selected[Runs.entries[0].key] = true;
        Ogc.getRuns = async () => [{run_name:'baseline', time_path:true, status:'completed', reusable:true}];
        Ogc.getRunStatus = async () => ({run_state:'completed', reusable:true});
        let calls = 0;
        Ogc.run = async () => calls++;
        Runs.load = async () => {};
        await Runs.runSelected();
        return {calls, state:Runs.plan[0].state};
    }''')
    assert result == {'calls': 0, 'state': 'reused'}


def test_changed_baseline_mode_invalidates_cached_reform(runs_page):
    page = runs_page
    page.evaluate(SEED)
    result = page.evaluate('''() => {
        const reform = Runs.entries[1];
        reform.run.time_path = true; reform.reusable = true; reform.state = 'completed';
        return Runs.buildQueue(Runs.entries, {[reform.key]:true}, false, true)
            .map(job => ({name:job.entry.run.run_name, state:job.state}));
    }''')
    assert result == [{'name': 'baseline', 'state': 'planned'}, {'name': 'reform', 'state': 'planned'}]


def test_failed_metadata_refresh_does_not_submit_or_reuse(runs_page):
    page = runs_page
    page.evaluate(SEED)
    result = page.evaluate('''async () => {
        Runs.selected[Runs.entries[0].key] = true;
        Ogc.getRuns = async () => {throw new Error('Unavailable')};
        let calls = 0;
        Ogc.run = async () => calls++;
        Runs.load = async () => {};
        await Runs.runSelected();
        return {calls, running:Runs.running, jobs:Runs.plan.length};
    }''')
    assert result == {'calls': 0, 'running': False, 'jobs': 0}

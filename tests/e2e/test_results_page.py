"""Browser checks for the OG-Core Results page, against the real controller,
vendored ECharts and Tabulator.

The test server has no OG-Core runs, so the Ogc client is replaced in the page
with a small fake that returns a baseline/reform pair and a report payload shaped
like /ogc/getResultsReport. Each test drives the page the way a user does.
"""
import pytest

from .test_shell_smoke import base_url  # noqa: F401

pytest.importorskip("pytest_playwright")

# Installs the fake client, loads the Results view and starts the page.
# window.fake lets a test change what the next response contains.
SEED = r"""async ({hash, overrides}) => {
    const html = await fetch('App/View/OGResults.html').then(r => r.text());
    const {Ogc} = await import('/Classes/Ogc.Class.js');
    const {default: R} = await import('/App/Controller/OGResults.js');
    document.querySelector('.osy-content').innerHTML = html;
    history.replaceState(null, '', hash || '#/OGResults');
    localStorage.setItem('osy-pageId', 'OGResults');
    localStorage.setItem('osy-ogc-country', JSON.stringify({country_id: 'ETH', country_name: 'Ethiopia'}));
    localStorage.removeItem('osy-ogc-results-recent');

    const years = Array.from({length: 12}, (_, t) => 2026 + t);
    const cmp = (baseline, reform, change, change_unit, value_unit, negative = false) =>
        ({baseline, reform, change, change_unit, value_unit, negative_baseline: negative});
    const row = (name, label, kind, c) => Object.assign({name, label, short: label, kind}, c);
    const path = (label, kind, unit, valueUnit, change) => ({label, short: label, kind, value_unit: valueUnit,
        change_unit: unit, baseline: years.map(() => 1), reform: years.map(() => 1.01), change,
        negative_baseline: false, steady: cmp(1, 1.01, 0.8, unit, valueUnit)});
    const report = () => ({
        status_code: 'success', mode: 'compare', analysis: 'transition',
        meta: {complete: true, start_year: 2026, T: 12, S: 3, J: 2, ages: [20, 21, 22],
            group_labels: ['0-50%', 'Top 50%'],
            weights: {baseline: [[0.2, 0.1], [0.2, 0.1], [0.3, 0.1]], reform: [[0.2, 0.1], [0.2, 0.1], [0.3, 0.1]]}},
        catalog: {Y: {label: 'Gross domestic product', short: 'GDP', category: 'Output', kind: 'level', dims: 'scalar'},
            r: {label: 'Real interest rate', short: 'Interest rate', category: 'Prices', kind: 'rate', dims: 'scalar'},
            c: {label: 'Household consumption', short: 'Consumption', category: 'Households', kind: 'level', dims: 'age_group'}},
        summary: [row('Y', 'GDP', 'level', cmp(2, 2.02, 1, '%', 'model units')),
            row('r', 'Interest rate', 'rate', cmp(7, 7.5, 0.5, 'pp', '%')),
            row('G', 'Govt. consumption', 'fiscal', cmp(-5, -4, 1, 'pp of GDP', '% of GDP', true))],
        macro: [row('Y', 'GDP', 'level', cmp(2, 2.02, 1, '%', 'model units'))],
        prices: [row('r', 'Interest rate', 'rate', cmp(7, 7.5, 0.5, 'pp', '%'))],
        fiscal: [row('G', 'Govt. consumption', 'fiscal', cmp(-5, -4, 1, 'pp of GDP', '% of GDP', true))],
        diagnostics: {baseline: {converged: true, values: {euler_savings: 1e-13}}, reform: {converged: true, values: {euler_savings: 1e-13}}},
        transition: {years, budget_window: 10, series: {
            Y: path('GDP', 'level', '%', 'model units', years.map((_, t) => t == 3 ? null : 0.5 + t / 100)),
            r: path('Interest rate', 'rate', 'pp', '%', years.map(() => 0.5))}},
        households: {c: {label: 'Household consumption', short: 'Consumption', kind: 'level', value_unit: 'model units',
            by_age: {baseline: [1, 2, 3], reform: [1.1, 2.2, 3.3]},
            by_age_group: {baseline: [[1, 2, 3], [2, 3, 4]], reform: [[1.1, 2.2, 3.3], [2.2, 3.3, 4.4]]},
            by_group: {baseline: [2, 3], reform: [2.2, 3.3]},
            group_change: [cmp(2, 2.2, 10, '%', 'model units'), cmp(3, 3.3, 10, '%', 'model units')],
            overall: cmp(2.5, 2.75, 10, '%', 'model units')}},
        households_reason: null
    });
    window.fake = Object.assign({
        runs: [
            {run_name: 'baseline', run_type: 'baseline', status: 'completed', reusable: true, time_path: true},
            {run_name: 'Tax cut', run_type: 'reform', baseline_run: 'baseline', status: 'completed', reusable: true, time_path: true},
            {run_name: 'Draft', run_type: 'reform', baseline_run: 'baseline', status: 'pending'}],
        report, reformParams: {cit_rate: [[0.2]]},
        calls: {report: 0, tables: 0}
    }, overrides || {});
    Ogc.getCases = async () => [{country_id: 'ETH', casename: 'Tax policy'}];
    Ogc.getRuns = async () => ({runs: window.fake.runs});
    Ogc.getResultsReport = async (country, casename, base, reform) => {
        window.fake.calls.report++;
        if (window.fake.hold) await window.fake.hold(casename, base, reform);
        return window.fake.report(base, reform);
    };
    Ogc.getParams = async (country, casename, run) => {
        if (window.fake.paramsFail) throw 'unavailable';
        return {params: run == 'baseline' ? {} : window.fake.reformParams};
    };
    Ogc.getParameterSchema = async () => ({cit_rate: {title: 'Corporate income tax rate', default: [[0.25]]}});
    Ogc.getSSVars = async (country, casename, run) => ({Y: run == 'baseline' ? 2 : 2.02,
        c: run == 'baseline' ? [[1, 2], [2, 3], [3, 4]] : [[1.1, 2.2], [2.2, 3.3], [3.3, 4.4]]});
    Ogc.getTPIVars = async () => ({Y: years.map(() => 2), r: years.map(() => 0.07)});
    Ogc.getResultTable = async (path) => {
        window.fake.calls.tables++;
        return [{Variable: 'Real interest rate ($r_t$)', Baseline: 0.07, Reform: 0.075, '% Change (or pp diff)': 7.1}];
    };
    window.R = R;
    R.onLoad();
    await new Promise(resolve => { const t = setInterval(() => {
        if ($('#ogcRsIntro').is(':visible') || $('#ogcRsView').is(':visible') || $('#ogcRsError').is(':visible')){ clearInterval(t); resolve(); }
    }, 20); });
}"""


def open_results(page, base_url, hash="#/OGResults", overrides=None):
    page.goto(base_url, wait_until="domcontentloaded")
    page.evaluate(SEED, {"hash": hash, "overrides": overrides})


def compare(page):
    page.click('[data-rs-act="compare"][data-reform="Tax cut"]')
    page.wait_for_selector("#ogcRsView", state="visible")
    page.wait_for_selector("#rsLifecycle svg")


def test_nothing_is_drawn_until_a_run_is_chosen(page, base_url):
    open_results(page, base_url)
    assert page.is_visible("#ogcRsIntro")
    assert not page.is_visible("#ogcRsView")
    assert page.evaluate("window.fake.calls.report") == 0
    assert page.is_enabled('[data-rs-act="compare"][data-reform="Tax cut"]')
    assert page.is_disabled('[data-rs-act="compare"][data-reform="Draft"]')
    assert "Not run yet" in page.inner_text("#ogcRsTree")


def test_compare_states_time_frame_units_and_negative_baselines(page, base_url):
    open_results(page, base_url)
    compare(page)
    periods = page.eval_on_selector_all('[data-rs-pane="report"] .ogc-rs-card-period', "els => els.map(e => e.textContent)")
    assert periods and all("Long run (steady state)" in p or p.startswith("Transition path, 2026") for p in periods)
    summary = page.inner_text("#rs-summary")
    assert "+0.50 pp" in summary
    assert "negative baseline" in summary
    assert "Negative baseline: Govt. consumption" in page.inner_text("#rs-fiscal")
    assert "Corporate income tax rate" in page.inner_text("#rs-policy")


def test_missing_path_values_stay_gaps_in_charts_and_tables(page, base_url):
    open_results(page, base_url)
    compare(page)
    data = page.evaluate("R.charts.rsPath_Y.getOption().series[0].data")
    assert data[3] is None and data[4] is not None
    cells = page.eval_on_selector_all('#ogcRsMainTable .tabulator-row:first-child .tabulator-cell',
                                      "els => els.map(e => e.textContent.trim())")
    assert "n/a" in cells[2:6]


def test_selection_is_kept_in_the_url_and_reopens(page, base_url):
    open_results(page, base_url)
    compare(page)
    hash_ = page.evaluate("location.hash")
    assert hash_.startswith("#/OGResults?") and "reform=Tax+cut" in hash_
    open_results(page, base_url, hash=hash_)
    assert page.is_visible("#ogcRsView")
    assert page.inner_text("#ogcRsTitle") == "Tax policy → Tax cut"
    open_results(page, base_url, hash="#/OGResults?case=Tax+policy&base=baseline&reform=Draft")
    assert page.is_visible("#ogcRsIntro")


def test_identical_reform_shows_the_guard_instead_of_charts(page, base_url):
    open_results(page, base_url, overrides={"reformParams": {}})
    compare_btn = '[data-rs-act="compare"][data-reform="Tax cut"]'
    page.click(compare_btn)
    page.wait_for_selector(".ogc-rs-guard")
    assert "same parameters as its baseline" in page.inner_text(".ogc-rs-guard")
    assert page.query_selector(".ogc-rs-kpis") is None


def test_households_default_to_the_weighted_average_and_show_one_scenario_per_group_view(page, base_url):
    open_results(page, base_url)
    compare(page)
    assert page.evaluate("R.charts.rsLifecycle.getOption().series.map(s => s.name)") == ["Baseline", "Reform"]
    page.click('[data-rs-act="hh-view"][data-view="groups"]')
    page.click('[data-rs-act="hh-scenario"][data-scenario="reform"]')
    option = page.evaluate("(() => { const o = R.charts.rsLifecycle.getOption(); return {names: o.series.map(s => s.name), first: o.series[0].data}; })()")
    assert option == {"names": ["0-50%", "Top 50%"], "first": [1.1, 2.2, 3.3]}
    assert page.evaluate("R.charts.rsGroups.getOption().xAxis[0].data") == ["0-50%", "Top 50%"]


def test_explore_uses_the_same_labels_and_offers_a_table(page, base_url):
    open_results(page, base_url)
    compare(page)
    page.click('[data-rs-tab="explore"]')
    page.click('[data-rs-act="var"][data-name="c"]')
    page.click('[data-rs-act="ex-breakdown"][data-value="groups"]')
    page.wait_for_selector("#ogcRsExChart svg")
    assert page.evaluate("R.charts.ogcRsExChart.getOption().xAxis[0].data") == ["0-50%", "Top 50%"]
    page.click('[data-rs-act="ex-view"][data-value="table"]')
    page.wait_for_selector("#ogcRsExTable .tabulator-row")
    assert "0-50%" in page.inner_text("#ogcRsExTable")
    assert page.query_selector("text=Save view") is None


def test_og_core_long_run_table_reads_rates_in_percentage_points_and_is_cached(page, base_url):
    open_results(page, base_url)
    compare(page)
    page.click('[data-rs-tab="explore"]')
    page.wait_for_selector("#ogcRsOgTable .tabulator-row")
    text = page.inner_text("#ogcRsOgTable")
    assert "Real interest rate" in text and "0.5" in text and "percentage points" in text
    calls = page.evaluate("window.fake.calls.tables")
    # the Explore tab stays open across selections
    page.click('[data-rs-act="view"][data-case="Tax policy"]:not([data-view])')
    page.wait_for_function("R.selection && !R.selection.reform && R.report && R.report.mode")
    page.wait_for_selector("#ogcRsOgTable .tabulator-row")
    page.click('[data-rs-act="compare"][data-reform="Tax cut"]')
    page.wait_for_function("R.selection && R.selection.reform == 'Tax cut'")
    page.wait_for_selector("#ogcRsOgTable .tabulator-row")
    # the single run built its own table; returning to the comparison reused the cached one
    assert page.evaluate("window.fake.calls.tables") == calls + 1


def test_chart_export_includes_title_and_time_frame(page, base_url):
    open_results(page, base_url)
    compare(page)
    svg = page.evaluate("""() => new Promise(resolve => {
        const click = HTMLAnchorElement.prototype.click;
        HTMLAnchorElement.prototype.click = function () { HTMLAnchorElement.prototype.click = click; resolve(decodeURIComponent(this.href.split(',')[1])); };
        R.exportChart('rsLifecycle', 'svg');
    })""")
    assert "Household consumption by age" in svg
    assert "Long run (steady state)" in svg


def test_unreadable_parameters_are_reported_not_hidden(page, base_url):
    open_results(page, base_url, overrides={"paramsFail": True})
    compare(page)
    assert "could not be read" in page.inner_text("#rs-policy")


def test_a_late_response_cannot_replace_the_current_comparison(page, base_url):
    open_results(page, base_url)
    page.evaluate("""() => {
        window.release = null;
        window.fake.hold = (casename, base, reform) => reform ? new Promise(r => { window.release = r; }) : null;
    }""")
    page.click('[data-rs-act="compare"][data-reform="Tax cut"]')
    page.wait_for_function("window.release !== null")
    page.click('[data-rs-act="view"][data-case="Tax policy"]:not([data-view])')
    page.wait_for_selector("#ogcRsView", state="visible")
    page.evaluate("window.release()")
    page.wait_for_timeout(200)
    assert page.inner_text("#ogcRsTitle") == "Tax policy"
    assert page.evaluate("R.selection.reform") is None


def test_leaving_results_unbinds_page_handlers(page, base_url):
    open_results(page, base_url, hash="#/OGResults/?case=x")
    result = page.evaluate("""() => {
        const bound = () => Object.values(jQuery._data(document, 'events') || {})
            .some(list => list.some(h => h.namespace === 'ogresults'));
        const current = R.isCurrent();
        const before = bound();
        location.hash = '#/OGCases';
        jQuery(window).triggerHandler('hashchange');
        return {current, before, after: bound()};
    }""")
    assert result == {"current": True, "before": True, "after": False}

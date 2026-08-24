"""
Browser smoke test for the MUIOGO shell: model selector, per-model navigation
chrome, and the per-route model assertions, against the real app served by
waitress.

Runs only when pytest-playwright is installed (the dedicated CI job); the plain
pytest job skips this module.
"""

import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("pytest_playwright")
from playwright.sync_api import expect

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTUP_TIMEOUT = 90  # seconds

expect.set_options(timeout=15_000)


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url():
    """Real server on a free port, torn down after the session."""
    port = _free_port()
    env = dict(os.environ, PORT=str(port))
    log = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "API" / "app.py")],
        cwd=REPO_ROOT, env=env,
        stdout=log, stderr=subprocess.STDOUT, text=True,
    )
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + STARTUP_TIMEOUT
    while True:
        if proc.poll() is not None:
            log.seek(0)
            out = log.read()
            log.close()
            pytest.fail(f"app exited during startup (code {proc.returncode}):\n{out[-2000:]}")
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    break
        except (urllib.error.URLError, ConnectionResetError, TimeoutError):
            pass
        if time.time() > deadline:
            proc.terminate()
            pytest.fail(f"app did not serve / within {STARTUP_TIMEOUT}s")
        time.sleep(0.25)
    yield url
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    log.close()


# Each test gets a fresh browser context (empty localStorage), so every test
# starts from the no-model-selected state.

def test_fresh_visit_shows_model_pick(page, base_url):
    page.goto(base_url)
    expect(page.locator("body.osy-mode-none")).to_have_count(1)
    expect(page.locator(".osy-pickwrap")).to_be_visible()
    expect(page.locator("#osy-mb-og")).to_be_visible()
    expect(page.locator("#osy-mb-clews")).to_be_visible()


def test_switch_to_og(page, base_url):
    page.goto(base_url)
    page.locator("#osy-mb-og").click()
    expect(page.locator("body.osy-mode-og")).to_have_count(1)
    # page skeleton only: asserting catalog contents would depend on a live fetch
    expect(page.locator(".ogc-page")).to_be_visible()
    expect(page.locator("#Navi > li.nav-home")).to_be_visible()
    # country tools appear only after opening a country card, not as global nav
    expect(page.locator("#Navi > li:not(.nav-home):visible")).to_have_count(0)


def test_sidebar_active_item_tracks_og_workspace_route(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-model', 'og');
        localStorage.setItem('osy-ogc-country', JSON.stringify({country_id:'ETH', country_name:'Ethiopia'}));""")
    page.goto(f"{base_url}/#/OGCases")
    expect(page.locator("#Navi > li.nav-og-workspace:visible")).to_have_count(3)
    expect(page.locator('#Navi > li.nav-og-workspace').filter(
        has=page.locator('a[href="#/OGCases"]'))).to_have_class(re.compile(r'(^|\s)active(\s|$)'))
    expect(page.locator('#Navi > li.nav-home')).not_to_have_class(re.compile(r'(^|\s)active(\s|$)'))
    expect(page.locator(".project-context")).to_be_hidden()


def test_desktop_sidebar_stays_fixed_while_content_scrolls(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""() => {
        const sidebar = document.querySelector('#left-panel');
        const nav = sidebar && sidebar.querySelector('nav');
        document.body.style.minHeight = '200vh';
        window.scrollTo(0, 0);
        const topBeforeScroll = sidebar && sidebar.getBoundingClientRect().top;
        window.scrollTo(0, 200);
        const topAfterScroll = sidebar && sidebar.getBoundingClientRect().top;
        return {
            sidebarPosition: sidebar && getComputedStyle(sidebar).position,
            sidebarOverflow: sidebar && getComputedStyle(sidebar).overflow,
            navOverflowY: nav && getComputedStyle(nav).overflowY,
            topBeforeScroll,
            topAfterScroll
        };
    }""")
    assert result['sidebarPosition'] == 'fixed'
    assert result['sidebarOverflow'] == 'hidden'
    assert result['navOverflowY'] == 'auto'
    assert result['topAfterScroll'] == result['topBeforeScroll']


def test_switch_to_clews(page, base_url):
    page.goto(base_url)
    page.locator("#osy-mb-clews").click()
    expect(page.locator("body.osy-mode-clews")).to_have_count(1)
    expect(page.locator(".project-context")).to_be_visible()
    expect(page.locator("#Navi > li.nav-og-workspace")).to_have_count(3)
    expect(page.locator("#Navi > li.nav-og-workspace:visible")).to_have_count(0)


def test_routes_assert_their_model(page, base_url):
    # with no model selected, the route itself must set the shell mode
    page.goto(f"{base_url}/#/Config")
    expect(page.locator("body.osy-mode-clews")).to_have_count(1)
    expect(page.locator(".project-context")).to_be_visible()
    page.goto(f"{base_url}/#/OGCore")
    expect(page.locator("body.osy-mode-og")).to_have_count(1)
    expect(page.locator(".ogc-page")).to_be_visible()


def test_results_tables_use_user_facing_headers_and_numeric_alignment(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")
    result = page.evaluate("""async () => {
        const markup = await fetch('App/View/OGResults.html').then(response => response.text());
        const { default: Results } = await import(
            new URL('App/Controller/OGResults.js', location.href).href
        );
        document.querySelector('.osy-content').innerHTML = markup;

        Results.activeTableKey = 'wealth';
        Results.selection = {casename: 'Case 1', base: 'Baseline 1', reform: 'Reform 1'};
        Results.renderTableRows([{Moment: 'Gini coefficient', Model: 0.5711}]);
        const wealthHeaders = [...document.querySelectorAll('#ogcResultTable th')]
            .map(cell => cell.textContent.trim());
        const wealthNumeric = [...document.querySelectorAll('#ogcResultTable td')]
            .map(cell => cell.classList.contains('ogc-num'));

        Results.activeTableKey = 'gini';
        Results.renderTableRows([{
            'Gini Type': 'Consumption',
            'Inequality Measure': 'Coefficient',
            Baseline: 0.2981,
            Reform: 0.2978,
        }]);
        const giniNumeric = [...document.querySelectorAll('#ogcResultTable td')]
            .map(cell => cell.classList.contains('ogc-num'));

        Results.activeTableKey = 'ineq';
        Results.renderTableRows([{
            'Steady-State Variable': 'Household Consumption ($' + String.fromCharCode(92) + 'tilde{c}_{j,s,t}$)',
            'Inequality Measure': 'Gini Coefficient',
            Baseline: [0.2981],
            Reform: [0.2978],
            '% Change': [-0.1177],
        }]);
        const cleanedValues = [...document.querySelectorAll('#ogcResultTable td')]
            .map(cell => cell.textContent.trim());
        const cleanedNumeric = [...document.querySelectorAll('#ogcResultTable td')]
            .map(cell => cell.classList.contains('ogc-num'));

        Results.tables = Results.tables || {};
        Results.tables.ineq = [{
            'Inequality Measure': 'Top 10% Share',
            Baseline: 0.2411,
            Reform: 0.2435,
        }];
        Results.renderInequality();
        const shareMetric = {
            label: document.querySelector('.ogc-inequality-metric > span').textContent,
            change: document.querySelector('.ogc-inequality-metric > strong').textContent,
            levels: document.querySelector('.ogc-inequality-metric > small').textContent,
        };

        return {
            wealthHeaders,
            wealthNumeric,
            giniNumeric,
            cleanedValues,
            cleanedNumeric,
            shareMetric,
            tableLabel: document.querySelector('#ogcResultTable table').getAttribute('aria-label'),
        };
    }""")

    assert result == {
        "wealthHeaders": ["Moment", "Baseline"],
        "wealthNumeric": [False, True],
        "giniNumeric": [False, False, True, True],
        "cleanedValues": [
            "Household Consumption",
            "Gini Coefficient",
            "0.2981",
            "0.2978",
            "-0.1177",
        ],
        "cleanedNumeric": [False, False, True, True, True],
        "shareMetric": {
            "label": "Top 10% share",
            "change": "+0.24 percentage points",
            "levels": "24.11% → 24.35%",
        },
        "tableLabel": "Inequality measures",
    }


def test_results_default_view_is_country_scoped_and_dimensions_are_explicit(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")
    result = page.evaluate("""async () => {
        const markup = await fetch('App/View/OGResults.html').then(response => response.text());
        const { default: Results } = await import(
            new URL('App/Controller/OGResults.js', location.href).href
        );
        document.querySelector('.osy-content').innerHTML = markup;

        Results.workspace = {country_id: 'ETH'};
        document.querySelector('#ogcExploreVariable').innerHTML = '<option value="c">Consumption</option>';
        document.querySelector('#ogcExploreMeasure').innerHTML = '<option value="pct">Percent change</option>';
        document.querySelector('#ogcExploreView').innerHTML = '<option value="heatmap">Heatmap</option>';
        document.querySelector('#ogcExploreGroup').innerHTML = '<option value="2">50–70%</option>';
        Results.saveView();
        const ethiopia = JSON.parse(localStorage.getItem('osy-ogc-result-view:ETH'));
        const savedNote = document.querySelector('#ogcSavedNote').textContent;

        Results.workspace = {country_id: 'PHL'};
        const philippines = Results.readSaved();

        Results.workspace = {country_id: 'ETH'};
        Results.groups = ['Bottom 25%', '25–50%', '50–70%', '70–80%', '80–90%', '90–99%', 'Top 1%'];
        Results.ages = Array.from({length: 80}, (_, index) => index + 21);
        Results.base = {c: Array.from({length: 80}, () => Array(7).fill(1))};
        Results.refreshExploreViews('heatmap');
        const dimensions = [...document.querySelector('#ogcExploreShape').children]
            .map(node => node.textContent.trim());

        return {ethiopia, philippines, savedNote, dimensions};
    }""")

    assert result == {
        "ethiopia": {
            "country_id": "ETH",
            "variable": "c",
            "measure": "pct",
            "view": "heatmap",
            "group": "2",
        },
        "philippines": None,
        "savedNote": "Default view saved",
        "dimensions": ["Dimensions", "Age × income group", "80 ages × 7 income groups"],
    }


def test_results_parameter_changes_show_names_for_all_value_types(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")
    result = page.evaluate("""async () => {
        const markup = await fetch('App/View/OGResults.html').then(response => response.text());
        const { default: Results } = await import(
            new URL('App/Controller/OGResults.js', location.href).href
        );
        document.querySelector('.osy-content').innerHTML = markup;

        Results.schema = {
            number_change: {title: 'Number parameter', default: 1},
            boolean_change: {title: 'Boolean parameter', default: false},
            string_change: {title: 'String parameter', default: 'old'},
            null_change: {title: 'Null parameter', default: null},
            flat_array_change: {title: 'Flat array parameter', default: [1, 2]},
            nested_array_change: {title: 'Nested array parameter', default: [[1, 2]]},
            baseline_only: {title: 'Baseline-only parameter', default: 0},
            reform_only: {title: 'Reform-only parameter', default: 0},
            fallback_title: {title: '', default: 0},
            unchanged_scalar: {title: 'Unchanged scalar', default: 1},
            unchanged_wrapper: {title: 'Unchanged wrapper', default: 1},
            unchanged_object: {title: 'Unchanged object', default: {}},
        };
        Results.baseParams = {
            number_change: 1,
            boolean_change: false,
            string_change: 'old',
            null_change: null,
            flat_array_change: [1, 2],
            nested_array_change: [[1, 2]],
            baseline_only: 5,
            fallback_title: 0,
            unchanged_scalar: 1,
            unchanged_wrapper: [[1]],
            unchanged_object: {first: 1, second: 2},
        };
        Results.reformParams = {
            number_change: 2,
            boolean_change: true,
            string_change: 'new',
            null_change: 'set',
            flat_array_change: [1, 3],
            nested_array_change: [[1, 4]],
            reform_only: 6,
            fallback_title: 1,
            unchanged_scalar: 1,
            unchanged_wrapper: 1,
            unchanged_object: {second: 2, first: 1},
        };
        Results.renderPolicy();

        const items = [...document.querySelectorAll('.ogc-policy-item')].map(item => ({
            label: item.querySelector('b').textContent,
            name: item.querySelector('code').textContent,
        }));
        return {
            count: document.querySelector('.ogc-policy-count').textContent,
            items,
            hasValues: document.querySelectorAll('.ogc-policy-values').length,
            hasUnsafeMarkup: document.querySelectorAll('#ogcPolicyChange img, #ogcPolicyChange script').length,
            text: document.querySelector('#ogcPolicyChange').textContent,
            hiddenExtra: document.querySelector('.ogc-policy-extra').hidden,
            more: document.querySelector('.ogc-policy-toggle').textContent,
        };
    }""")

    assert result == {
        "count": "9 parameters changed",
        "items": [
            {"label": "Baseline-only parameter", "name": "baseline_only"},
            {"label": "Boolean parameter", "name": "boolean_change"},
            {"label": "Fallback Title", "name": "fallback_title"},
            {"label": "Flat array parameter", "name": "flat_array_change"},
            {"label": "Nested array parameter", "name": "nested_array_change"},
            {"label": "Null parameter", "name": "null_change"},
            {"label": "Number parameter", "name": "number_change"},
            {"label": "Reform-only parameter", "name": "reform_only"},
            {"label": "String parameter", "name": "string_change"},
        ],
        "hasValues": 0,
        "hasUnsafeMarkup": 0,
        "text": (
            "9 parameters changedBaseline-only parameterbaseline_onlyBoolean parameter"
            "boolean_changeFallback Titlefallback_titleFlat array parameterflat_array_change"
            "Show 5 moreNested array parameternested_array_changeNull parameternull_change"
            "Number parameternumber_changeReform-only parameterreform_onlyString parameter"
            "string_change"
        ),
        "hiddenExtra": True,
        "more": "Show 5 more",
    }


def test_results_matrix_headers_and_missing_data_guard(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")
    result = page.evaluate("""async () => {
        const markup = await fetch('App/View/OGResults.html').then(response => response.text());
        const { default: Results } = await import(
            new URL('App/Controller/OGResults.js', location.href).href
        );
        document.querySelector('.osy-content').innerHTML = markup;

        Results.selection = {casename: 'Baseline 1', base: 'baseline', reform: 'Reform 1'};
        Results.groups = ['Bottom 50%', 'Top 50%'];
        Results.ages = [31, 32];
        Results.base = {c: [[1, 2], [3, 4]]};
        Results.reform = {c: [[2, 3], [4, 5]]};
        Results.renderExploreTable('c', 'levels');
        const headers = [...document.querySelectorAll('#ogcExploreTable th')]
            .map(cell => cell.textContent.trim());

        Results.reform = {c: [[2, 3]]};
        Results.renderExploreTable('c', 'pct');
        return {
            headers,
            missing: document.querySelector('#ogcExploreTable').textContent.trim(),
        };
    }""")

    assert result == {
        "headers": [
            "Age",
            "Baseline: Bottom 50%",
            "Reform: Bottom 50%",
            "Baseline: Top 50%",
            "Reform: Top 50%",
        ],
        "missing": "Comparable baseline and reform matrix data are unavailable.",
    }


def test_results_dimensions_prefer_run_metadata_and_explain_fallback(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")
    result = page.evaluate("""async () => {
        const markup = await fetch('App/View/OGResults.html').then(response => response.text());
        const { default: Results } = await import(
            new URL('App/Controller/OGResults.js', location.href).href
        );
        document.querySelector('.osy-content').innerHTML = markup;

        Results.base = {c: [[1, 2, 3], [4, 5, 6]]};
        Results.baseParams = {lambdas: [[0.2, 0.3, 0.5]], starting_age: [30]};
        Results.schema = {
            lambdas: {default: [0.5, 0.5]},
            starting_age: {default: 20},
        };
        Results.schemaUnavailable = false;
        Results.setDimensions();
        const fromRun = {
            groups: Results.groups,
            ages: Results.ages,
            hidden: document.querySelector('#ogcDimensionNote').hidden,
        };

        Results.base = {c: [[1, 2, 3, 4], [5, 6, 7, 8]]};
        Results.baseParams = {};
        Results.schema = {};
        Results.schemaUnavailable = true;
        Results.setDimensions();
        return {
            fromRun,
            fallback: {
                groups: Results.groups,
                ages: Results.ages,
                hidden: document.querySelector('#ogcDimensionNote').hidden,
                note: document.querySelector('#ogcDimensionNote').textContent,
            },
        };
    }""")

    assert result == {
        "fromRun": {
            "groups": ["Bottom 20%", "20–50%", "Top 50%"],
            "ages": [31, 32],
            "hidden": True,
        },
        "fallback": {
            "groups": ["Group 1", "Group 2", "Group 3", "Group 4"],
            "ages": [1, 2],
            "hidden": False,
            "note": (
                "Parameter metadata could not be loaded. "
                "Income-group metadata is unavailable, so generic group labels are shown. "
                "Starting-age metadata is unavailable, so model age indices are shown."
            ),
        },
    }


def test_results_comparison_tables_are_cached_independently(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")
    result = page.evaluate("""async () => {
        const { default: Results } = await import(
            new URL('App/Controller/OGResults.js', location.href).href
        );
        Results.tableCache = Object.create(null);
        const first = {casename: 'Baseline 1', base: 'baseline', reform: 'Reform 1'};
        const second = {casename: 'Baseline 1', base: 'baseline', reform: 'Reform 2'};

        Results.useTableCache(first);
        Results.tables.ineq = [{Baseline: 0.3, Reform: 0.29}];
        Results.useTableCache(second);
        const secondStartsEmpty = !Object.prototype.hasOwnProperty.call(Results.tables, 'ineq');
        Results.tables.gini = [{Baseline: 0.4, Reform: 0.39}];
        Results.useTableCache(first);

        return {
            secondStartsEmpty,
            firstIneq: Results.tables.ineq,
            firstHasGini: Object.prototype.hasOwnProperty.call(Results.tables, 'gini'),
            cacheCount: Object.keys(Results.tableCache).length,
        };
    }""")

    assert result == {
        "secondStartsEmpty": True,
        "firstIneq": [{"Baseline": 0.3, "Reform": 0.29}],
        "firstHasGini": False,
        "cacheCount": 2,
    }


def test_results_route_normalization_and_cleanup(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")
    result = page.evaluate("""async () => {
        const { default: Results } = await import(
            new URL('App/Controller/OGResults.js', location.href).href
        );
        history.replaceState({}, '', '#/OGResults/?tab=overview');
        localStorage.setItem('osy-pageId', 'OGResults');
        Results.pageID = 0;
        Results.initEvents();
        const normalized = Results.isCurrent();
        const before = Object.keys(jQuery._data(document, 'events') || {})
            .some(type => (jQuery._data(document, 'events')[type] || [])
                .some(handler => handler.namespace === 'ogresults'));
        location.hash = '#/OGCases';
        jQuery(window).triggerHandler('hashchange');
        const after = Object.keys(jQuery._data(document, 'events') || {})
            .some(type => (jQuery._data(document, 'events')[type] || [])
                .some(handler => handler.namespace === 'ogresults'));
        return {normalized, before, after};
    }""")

    assert result == {"normalized": True, "before": True, "after": False}


def test_local_folder_update_action_is_manual(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    html = page.evaluate("""async () => {
        const { default: OGCore } = await import(new URL('App/Controller/OGCore.js', location.href).href);
        return OGCore.actionsHtml(
            { install_state: 'update_available' },
            { source_type: 'local_path' },
        );
    }""")
    assert 'data-act="update"' not in html
    assert 'data-act="check"' in html
    assert 'Update the local folder' in html


def test_changed_add_form_disables_previous_check(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    expect(page.locator(".ogc-page")).to_be_visible()
    page.evaluate("""async () => {
        const { default: OGCore } = await import(new URL('App/Controller/OGCore.js', location.href).href);
        OGCore.openAdd();
        OGCore.checkedValues = { source: '/tmp/OG-KEN', label: 'Kenya', code: 'KEN', valid: true };
    }""")
    page.locator("#ogcAddSource").fill("/tmp/OG-ETH")
    expect(page.locator('[data-act="add-confirm"]')).to_be_disabled()


def test_failed_job_reopens_with_retry_action(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    expect(page.locator(".ogc-page")).to_be_visible()
    result = page.evaluate("""async () => {
        const { default: OGCore } = await import(new URL('App/Controller/OGCore.js', location.href).href);
        OGCore.model = { calibrations: [], records: {} };
        $('#ogcGrid').html(OGCore.cardHtml({
            country_id: 'KEN', country_name: 'Kenya', install_state: 'installing'
        }));
        OGCore.applyJob('KEN', {
            country_id: 'KEN', country_name: 'Kenya', install_state: 'failed',
            log_tail: ['failed'], error: 'install failed'
        }, OGCore.pageID);
        OGCore.openLog('KEN');
        return {
            heading: $('#ogcModalHead').text(),
            retry: $('#ogcModalFoot [data-act="retry-modal"]').length,
        };
    }""")
    assert 'install failed' in result['heading']
    assert result['retry'] == 1


def test_registry_install_id_is_authoritative(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    expect(page.locator(".ogc-page")).to_be_visible()
    result = page.evaluate("""async () => {
        const { default: OGCore } = await import(new URL('App/Controller/OGCore.js', location.href).href);
        localStorage.setItem('osy-ogc-jobs', JSON.stringify({ KEN: 'stale-browser-id' }));
        OGCore.model = {
            calibrations: [{ country_id: 'KEN', install_id: 'catalog-id' }],
            records: { KEN: { install_id: 'registry-id' } },
        };
        return OGCore.jobIdFor('KEN');
    }""")
    assert result == 'registry-id'


def test_failed_update_keeps_working_install(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    expect(page.locator(".ogc-page")).to_be_visible()
    result = page.evaluate("""async () => {
        const { default: OGCore } = await import(new URL('App/Controller/OGCore.js', location.href).href);
        OGCore.model = {
            calibrations: [{
                country_id: 'KEN', country_name: 'Kenya', install_state: 'installing'
            }],
            records: { KEN: {
                country_id: 'KEN', country_name: 'Kenya', install_state: 'installing',
                install_id: 'install_ken', venv_path: '/models/OG-KEN/.venv'
            } },
        };
        $('#ogcGrid').html(OGCore.cardHtml(
            OGCore.model.calibrations[0], OGCore.model.records.KEN
        ));
        OGCore.openLog('KEN', true);
        let refreshed = false;
        OGCore.refresh = () => { refreshed = true; };
        OGCore.applyJob('KEN', {
            country_id: 'KEN', country_name: 'Kenya', install_state: 'failed',
            log_tail: ['update failed'], error: 'update failed'
        }, OGCore.pageID);
        return {
            badge: $('#ogcGrid .ogc-badge').text(),
            action: $('#ogcGrid [data-act="log"]').text(),
            heading: $('#ogcModalHead').text(),
            retryUpdate: $('#ogcModalFoot [data-act="retry-update-modal"]').length,
            retryInstall: $('#ogcModalFoot [data-act="retry-modal"]').length,
            lastError: OGCore.model.records.KEN.last_error,
            refreshed,
        };
    }""")
    assert result['badge'] == 'installed'
    assert 'View update error' in result['action']
    assert 'update failed' in result['heading']
    assert result['retryUpdate'] == 1
    assert result['retryInstall'] == 0
    assert result['lastError'] == 'update failed'
    assert result['refreshed'] is True


def test_navigation_invalidates_old_og_page_load(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    expect(page.locator(".ogc-page")).to_be_visible()
    old_page_id = page.evaluate("""async () => {
        const { default: OGCore } = await import(new URL('App/Controller/OGCore.js', location.href).href);
        return OGCore.pageID;
    }""")
    page.evaluate("""async () => {
        const { default: OGCore } = await import(new URL('App/Controller/OGCore.js', location.href).href);
        OGCore.invalidatePage();
    }""")
    result = page.evaluate("""async (oldPageID) => {
        const { default: OGCore } = await import(new URL('App/Controller/OGCore.js', location.href).href);
        return { old_is_current: OGCore.isCurrent(oldPageID), new_page_id: OGCore.pageID };
    }""", old_page_id)
    assert result['old_is_current'] is False
    assert result['new_page_id'] > old_page_id


def test_og_page_survives_round_trip_navigation(page, base_url):
    """OG -> CLEWS -> OG must re-render the grid; a stale PAGE_ID would leave it empty."""
    page.goto(f"{base_url}/#/OGCore")
    expect(page.locator(".ogc-addcard")).to_be_visible()
    page.evaluate("window.__stamp = 'og1'")

    page.goto(f"{base_url}/#/Config")
    expect(page.locator("body.osy-mode-clews")).to_have_count(1)
    # #osy-title is shared across CLEWS views; waiting for it works around a real
    # router race where a late .load() callback can paint the previous view over
    # the current OGCore view.
    expect(page.locator("#osy-title")).to_be_visible()

    page.goto(f"{base_url}/#/OGCore")
    expect(page.locator("body.osy-mode-og")).to_have_count(1)
    # if the stamp is gone the browser reloaded, and the test is not exercising
    # a round trip within one document — which is the whole point
    assert page.evaluate("window.__stamp") == 'og1'
    expect(page.locator(".ogc-page")).to_be_visible()
    # the last thing renderGrid appends: present only if the reload was not
    # discarded as stale work from the previous visit
    expect(page.locator(".ogc-addcard")).to_be_visible()


def test_polling_stops_when_leaving_og_page(page, base_url):
    """No OG-Core requests continue after leaving the OG page."""
    page.goto(f"{base_url}/#/OGCore")
    expect(page.locator(".ogc-addcard")).to_be_visible()

    calls = []
    page.on("request", lambda r: calls.append(r.url) if "/ogc/" in r.url else None)

    # a bogus id produces an observable OG-Core request before the page is left.
    # This test covers the no-traffic guarantee; the page-ID bump mechanism is
    # covered by test_navigation_invalidates_old_og_page_load.
    page.evaluate("""async () => {
        const { default: OGCore } = await import(new URL('App/Controller/OGCore.js', location.href).href);
        OGCore.pollJob('KEN', 'no-such-job', OGCore.pageID);
        location.hash = '#/Config';
    }""")
    expect(page.locator("body.osy-mode-clews")).to_have_count(1)
    assert len(calls) > 0, "pollJob issued no request; the test would pass vacuously"
    settled = len(calls)
    page.wait_for_timeout(8_000)          # > 2x POLL_MS (3500)
    assert len(calls) == settled, f"polling outlived the page: {calls[settled:]}"
def test_og_workspace_routes_assert_og_mode(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGCases")
    expect(page.locator("body.osy-mode-og")).to_have_count(1)
    expect(page.locator("body.osy-og-workspace")).to_have_count(1)
    expect(page.locator("#ogcCasesPage")).to_be_visible()
    expect(page.locator("#Navi > li.nav-og-workspace:visible")).to_have_count(3)
    expect(page.locator("#ogcCasesPage [data-act='run']")).to_have_count(0)
    page.goto(f"{base_url}/#/OGRuns")
    expect(page.locator("body.osy-mode-og.osy-og-workspace")).to_have_count(1)
    expect(page.locator("#ogcRunsPage")).to_be_visible()
    expect(page.locator("#ogcRunsPage .ogc-run-workspace")).to_have_count(0)
    page.goto(f"{base_url}/#/OGParameters")
    expect(page.locator("body.osy-mode-og")).to_have_count(1)
    expect(page.locator("#ogcParamsPage")).to_be_visible()


def test_country_workspace_filters_cases(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGCases.Model.js', location.href).href);
        const model = new Model([
            { casename: 'ethiopia-case', country_id: 'ETH' },
            { casename: 'south-africa-case', country_id: 'ZAF' }
        ], {}, [{ country_id: 'ETH' }, { country_id: 'ZAF' }], 'ETH');
        return model.cases.map(c => c.casename);
    }""")
    assert result == ['ethiopia-case']


def test_run_keys_are_scoped_by_country(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const cases = await import(new URL('App/Controller/OGCases.js', location.href).href);
        const eth = cases.runKey('ETH', 'Baseline', 'baseline');
        const usa = cases.runKey('USA', 'Baseline', 'baseline');
        return {
            eth, usa,
            browserStaleStoreRemoved: cases.markRunsStale === undefined
        };
    }""")
    assert result == {
        'eth': 'ETH:Baseline:baseline',
        'usa': 'USA:Baseline:baseline',
        'browserStaleStoreRemoved': True,
    }


def test_ogc_adapter_matches_run_backend_contract(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        const calls = [];
        Ogc._request = async (type, path, data) => {
            calls.push({type, path, data});
            if (path === 'ogc/getRuns') {
                return {
                    baseline: {RunName: 'base', RunType: 'baseline', status: 'completed'},
                    reforms: [{RunName: 'reform', RunType: 'reform', baseline_run_name: 'base', status: 'pending'}]
                };
            }
            if (path === 'ogc/getParams') return {debt_ratio_ss: [[0.4]]};
            return {status_code: 'success'};
        };
        await Ogc.saveCase({casename: 'case-one', description: 'd', country_id: 'ETH'});
        await Ogc.createRun({country_id: 'ETH', casename: 'case-one', run_name: 'reform', run_type: 'reform', baseline_run: 'base'});
        await Ogc.cancelRun('ETH', 'case-one', 'reform');
        const runs = await Ogc.getRuns('ETH', 'case-one');
        const params = await Ogc.getParams('ETH', 'case-one', 'reform');
        await Ogc.getRunQueue('ETH', 'case-one');
        await Ogc.getSSVars('ETH', 'case-one', 'reform', ['Y']);
        await Ogc.getIneqTable('ETH', 'case-one', 'base', 'reform');
        await Ogc.setSession(null, 'ETH');
        await Ogc.setSession(null);
        return {calls, runs, params};
    }""")
    assert result['calls'][0]['data'] == {
        'data': {'ogc-casename': 'case-one', 'ogc-description': 'd', 'country_id': 'ETH'}
    }
    assert result['calls'][1]['data']['baseline_run_name'] == 'base'
    assert result['calls'][2]['data'] == {
        'country_id': 'ETH', 'casename': 'case-one', 'run_name': 'reform'
    }
    assert result['runs']['runs'][0]['run_name'] == 'base'
    assert result['runs']['runs'][1]['baseline_run'] == 'base'
    assert result['params']['params']['debt_ratio_ss'] == [[0.4]]
    assert result['calls'][5] == {
        'type': 'POST', 'path': 'ogc/getRunQueue',
        'data': {'country_id': 'ETH', 'casename': 'case-one'}
    }
    assert result['calls'][6] == {
        'type': 'POST', 'path': 'ogc/getSSVars',
        'data': {'country_id': 'ETH', 'casename': 'case-one', 'run_name': 'reform', 'vars': ['Y']}
    }
    assert result['calls'][7] == {
        'type': 'POST', 'path': 'ogc/getIneqTable',
        'data': {'country_id': 'ETH', 'casename': 'case-one', 'base_run': 'base', 'reform_run': 'reform'}
    }
    assert result['calls'][8]['data'] == {'casename': None, 'country_id': 'ETH'}
    assert result['calls'][9]['data'] == {'casename': None}


def test_workspace_opening_uses_real_backend_stages(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    page.wait_for_function("localStorage.getItem('osy-pageId') === 'OGCore'")
    result = page.evaluate("""async () => {
        const { OGWorkspace } = await import(new URL('Classes/OGWorkspace.Class.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        const calls = [];
        Ogc.getInstalledCalibrations = async () => {
            calls.push('installed');
            return {calibrations: [{country_id: 'ETH'}]};
        };
        Ogc.setSession = async (casename, countryId) => {
            calls.push(casename === null ? 'session:' + (countryId || 'clear') : 'case:' + casename);
            return {ogccase: casename, ogccountry: countryId || null};
        };
        Ogc.getCases = async () => {
            calls.push('cases');
            return [{casename: 'baseline-one', country_id: 'ETH'}];
        };
        Ogc.getRuns = async (countryId, casename) => {
            calls.push('runs:' + casename);
            return {runs: [{run_name: 'baseline', run_type: 'baseline'}]};
        };
        const ready = await OGWorkspace.prepare({country_id: 'ETH', country_name: 'Ethiopia'});
        const prepared = OGWorkspace.takePrepared('ETH');
        return {
            ready, calls, prepared,
            workspace: JSON.parse(localStorage.getItem('osy-ogc-country')),
            overlayVisible: $('#ogWorkspaceLifecycle').is(':visible')
        };
    }""")
    assert result['ready'] is True
    assert result['calls'] == ['installed', 'session:ETH', 'cases', 'runs:baseline-one']
    assert result['prepared']['runsByCase']['baseline-one'][0]['run_name'] == 'baseline'
    assert result['workspace'] == {'country_id': 'ETH', 'country_name': 'Ethiopia'}
    assert result['overlayVisible'] is False


def test_workspace_opening_keeps_cases_when_one_run_read_fails(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    page.wait_for_function("localStorage.getItem('osy-pageId') === 'OGCore'")
    result = page.evaluate("""async () => {
        const { OGWorkspace } = await import(new URL('Classes/OGWorkspace.Class.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        Ogc.getInstalledCalibrations = async () => ({calibrations: [{country_id: 'ETH'}]});
        Ogc.setSession = async () => ({ogccase: null, ogccountry: 'ETH'});
        Ogc.getCases = async () => [
            {casename: 'readable', country_id: 'ETH'},
            {casename: 'unavailable', country_id: 'ETH'}
        ];
        Ogc.getRuns = async (countryId, casename) => {
            if (casename == 'unavailable') throw 'run read failed';
            return {runs: [{run_name: 'baseline', run_type: 'baseline'}]};
        };
        const ready = await OGWorkspace.prepare({country_id: 'ETH', country_name: 'Ethiopia'});
        return {ready, prepared: OGWorkspace.takePrepared('ETH')};
    }""")
    assert result['ready'] is True
    assert result['prepared']['runsByCase']['readable'][0]['run_name'] == 'baseline'
    assert result['prepared']['runsByCase']['unavailable'] == []
    assert result['prepared']['failedRuns'] == ['unavailable']


def test_workspace_opening_unwinds_country_session_on_error(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    page.wait_for_function("localStorage.getItem('osy-pageId') === 'OGCore'")
    page.evaluate("""async () => {
        const { OGWorkspace } = await import(new URL('Classes/OGWorkspace.Class.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        window.__countrySessionCalls = [];
        Ogc.getInstalledCalibrations = async () => ({calibrations: [{country_id: 'ETH'}]});
        Ogc.setSession = async (casename, countryId) => {
            window.__countrySessionCalls.push({casename, countryId: countryId || null});
            return {ogccase: casename, ogccountry: countryId || null};
        };
        Ogc.getCases = async () => { throw new Error('case load failed'); };
        window.__countryOpen = OGWorkspace.prepare({country_id: 'ETH', country_name: 'Ethiopia'});
    }""")
    expect(page.locator('#ogWorkspaceLifeActions')).to_be_visible()
    page.locator('[data-og-life-action="back"]').click()
    result = page.evaluate("""async () => ({
        ready: await window.__countryOpen,
        calls: window.__countrySessionCalls,
        workspace: localStorage.getItem('osy-ogc-country'),
        overlayVisible: $('#ogWorkspaceLifecycle').is(':visible')
    })""")
    assert result == {
        'ready': False,
        'calls': [
            {'casename': None, 'countryId': 'ETH'},
            {'casename': None, 'countryId': None},
        ],
        'workspace': None,
        'overlayVisible': False,
    }


def test_workspace_opening_is_cancelled_when_ogcore_is_left(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    page.wait_for_function("localStorage.getItem('osy-pageId') === 'OGCore'")
    result = page.evaluate("""async () => {
        const { OGWorkspace } = await import(new URL('Classes/OGWorkspace.Class.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        let release;
        let installed = new Promise(resolve => { release = resolve; });
        Ogc.getInstalledCalibrations = async () => await installed;
        let current = true;
        let opening = OGWorkspace.prepare(
            {country_id: 'ETH', country_name: 'Ethiopia'},
            () => current
        );
        current = false;
        OGWorkspace.cancelPreparation();
        release({calibrations: [{country_id: 'ETH'}]});
        return {
            ready: await opening,
            workspace: localStorage.getItem('osy-ogc-country'),
            overlayVisible: $('#ogWorkspaceLifecycle').is(':visible')
        };
    }""")
    assert result == {'ready': False, 'workspace': None, 'overlayVisible': False}


def test_stay_in_workspace_changes_nothing(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    page.wait_for_function("localStorage.getItem('osy-pageId') === 'OGCore'")
    page.evaluate("""async () => {
        const { OGWorkspace } = await import(new URL('Classes/OGWorkspace.Class.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        localStorage.setItem('osy-ogc-country', JSON.stringify({country_id: 'ETH', country_name: 'Ethiopia'}));
        localStorage.setItem('osy-ogc-selection', JSON.stringify({casename: 'c1', run_name: 'baseline'}));
        window.__sessionCalls = [];
        Ogc.setSession = async value => { window.__sessionCalls.push(value); };
        window.__leavePromise = OGWorkspace.leave();
    }""")
    expect(page.locator("#ogWorkspaceConfirm")).to_be_visible()
    page.locator('[data-og-confirm="stay"]').click()
    result = page.evaluate("""async () => ({
        left: await window.__leavePromise,
        calls: window.__sessionCalls,
        workspace: localStorage.getItem('osy-ogc-country'),
        selection: localStorage.getItem('osy-ogc-selection')
    })""")
    assert result['left'] is False
    assert result['calls'] == []
    assert result['workspace'] is not None
    assert result['selection'] is not None


def test_workspace_exit_stay_restores_unsaved_navigation_guard(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    page.wait_for_function("localStorage.getItem('osy-pageId') === 'OGCore'")
    page.evaluate("""async () => {
        const { NavigationGuard } = await import(new URL('Classes/NavigationGuard.Class.js', location.href).href);
        const { OGWorkspace } = await import(new URL('Classes/OGWorkspace.Class.js', location.href).href);
        const { Message } = await import(new URL('Classes/Message.Class.js', location.href).href);
        localStorage.setItem('osy-ogc-country', JSON.stringify({country_id: 'ETH', country_name: 'Ethiopia'}));
        window.__guardConfirmCalls = 0;
        window.__guardAllowedCalls = 0;
        Message.confirmUnsavedModelChanges = async () => {
            window.__guardConfirmCalls++;
            return "Don't save";
        };
        NavigationGuard.activate({hasChanges: () => true, update: () => {}});
        window.__guardLeavePromise = NavigationGuard.requestLeave(
            async () => await OGWorkspace.leave()
        );
    }""")
    expect(page.locator("#ogWorkspaceConfirm")).to_be_visible()
    page.locator('[data-og-confirm="stay"]').click()
    result = page.evaluate("""async () => {
        const { NavigationGuard } = await import(new URL('Classes/NavigationGuard.Class.js', location.href).href);
        const firstResult = await window.__guardLeavePromise;
        await NavigationGuard.requestLeave(async () => {
            window.__guardAllowedCalls++;
            return true;
        });
        return {
            firstResult,
            confirms: window.__guardConfirmCalls,
            allowed: window.__guardAllowedCalls
        };
    }""")
    assert result == {'firstResult': False, 'confirms': 2, 'allowed': 1}


def test_confirmed_workspace_exit_clears_session_and_local_state(page, base_url):
    page.goto(f"{base_url}/#/OGCore")
    page.wait_for_function("localStorage.getItem('osy-pageId') === 'OGCore'")
    page.evaluate("""async () => {
        const { OGWorkspace } = await import(new URL('Classes/OGWorkspace.Class.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        localStorage.setItem('osy-ogc-country', JSON.stringify({country_id: 'ETH', country_name: 'Ethiopia'}));
        localStorage.setItem('osy-ogc-selection', JSON.stringify({casename: 'c1', run_name: 'baseline'}));
        window.__sessionCalls = [];
        Ogc.setSession = async value => { window.__sessionCalls.push(value); };
        window.__leavePromise = OGWorkspace.leave();
    }""")
    page.locator('[data-og-confirm="leave"]').click()
    result = page.evaluate("""async () => ({
        left: await window.__leavePromise,
        calls: window.__sessionCalls,
        workspace: localStorage.getItem('osy-ogc-country'),
        selection: localStorage.getItem('osy-ogc-selection')
    })""")
    assert result == {
        'left': True, 'calls': [None], 'workspace': None, 'selection': None
    }


def test_non_workspace_entry_reconciles_a_stranded_country_session(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { OGWorkspace } = await import(new URL('Classes/OGWorkspace.Class.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        localStorage.setItem('osy-ogc-country', JSON.stringify({country_id: 'ETH', country_name: 'Ethiopia'}));
        localStorage.setItem('osy-ogc-selection', JSON.stringify({casename: 'c1', run_name: 'baseline'}));
        const calls = [];
        Ogc.setSession = async (casename, countryId) => {
            calls.push([casename, countryId === undefined ? null : countryId]);
        };
        const reconciled = await OGWorkspace.reconcileEntry('/OGCore');
        return {
            reconciled,
            calls,
            workspace: localStorage.getItem('osy-ogc-country'),
            selection: localStorage.getItem('osy-ogc-selection')
        };
    }""")
    assert result == {
        'reconciled': True,
        'calls': [[None, None]],
        'workspace': None,
        'selection': None,
    }


def test_clews_switch_waits_for_workspace_exit_confirmation(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGCases")
    expect(page.locator("body.osy-mode-og.osy-og-workspace")).to_have_count(1)

    page.locator("#osy-mb-clews").click()
    expect(page.locator("#ogWorkspaceConfirm")).to_be_visible()
    page.locator('[data-og-confirm="stay"]').click()
    expect(page).to_have_url(f"{base_url}/#/OGCases")
    expect(page.locator("body.osy-mode-og.osy-og-workspace")).to_have_count(1)
    assert page.evaluate("localStorage.getItem('osy-model')") == 'og'

    page.locator("#osy-mb-clews").click()
    page.evaluate("window.location.hash = '#/OGCore'")
    expect(page).to_have_url(f"{base_url}/#/OGCases")
    page.locator('[data-og-confirm="leave"]').click()
    expect(page).to_have_url(f"{base_url}/#/")
    expect(page.locator("body.osy-mode-clews")).to_have_count(1)
    assert page.evaluate("localStorage.getItem('osy-ogc-country')") is None


def test_workspace_exit_is_serialized_and_back_cannot_reenter(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGCases")
    page.evaluate("""async () => {
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        window.__serializedSessionCalls = [];
        Ogc.setSession = async value => { window.__serializedSessionCalls.push(value); };
    }""")
    page.locator("[href='#/OGCore']").click()
    expect(page.locator("#ogWorkspaceConfirm")).to_be_visible()
    page.evaluate("window.location.hash = '#/'")
    page.locator('[data-og-confirm="leave"]').click()
    expect(page).to_have_url(f"{base_url}/#/OGCore")
    assert page.evaluate("window.__serializedSessionCalls") == [None]

    page.go_back()
    expect(page).to_have_url(f"{base_url}/#/OGCore")
    expect(page.locator("body.osy-og-workspace")).to_have_count(0)
    page.go_back()
    expect(page).to_have_url(f"{base_url}/#/")
    expect(page.locator("body.osy-og-workspace")).to_have_count(0)


def test_add_case_dialog_switches_between_baseline_and_reform(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGCases")
    expect(page.locator("#ogcCasesPage")).to_be_visible()
    page.evaluate("""async () => {
        const { default: Cases } = await import(new URL('App/Controller/OGCases.js', location.href).href);
        const { Model } = await import(new URL('App/Model/OGCases.Model.js', location.href).href);
        Cases.workspace = {country_id: 'ETH', country_name: 'Ethiopia'};
        Cases.model = new Model(
            [{casename: 'Baseline 1', country_id: 'ETH'}],
            {'Baseline 1': [{run_name: 'baseline', run_type: 'baseline'}]},
            [{country_id: 'ETH'}], 'ETH'
        );
        Cases.initEvents();
        Cases.openNewCase();
    }""")

    expect(page.locator("#ogcCasesModalHead")).to_have_text("Add a case")
    expect(page.locator("[data-act='case-type'][data-type='baseline']")).to_have_class("active")
    expect(page.locator("#ogcCaseName")).to_have_value("Baseline 2")
    expect(page.locator("#ogcCaseBaseWrap")).to_be_hidden()
    expect(page.locator("[data-act='new-case-confirm']")).to_have_text("Create and edit")

    page.locator("[data-act='case-type'][data-type='reform']").click()
    expect(page.locator("#ogcCaseName")).to_have_value("New reform")
    expect(page.locator("#ogcCaseBaseWrap")).to_be_visible()
    expect(page.locator("#ogcCaseBaseline option")).to_have_text("Baseline 1")
    expect(page.locator("#ogcCaseNote")).to_contain_text("inherits this baseline's values")


def test_baseline_action_menu_adds_reform_shortcut(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGCases")
    expect(page.locator("#ogcCasesPage")).to_be_visible()
    page.evaluate("""async () => {
        const { default: Cases } = await import(new URL('App/Controller/OGCases.js', location.href).href);
        const { Model } = await import(new URL('App/Model/OGCases.Model.js', location.href).href);
        Cases.workspace = {country_id: 'ETH', country_name: 'Ethiopia'};
        Cases.model = new Model(
            [{casename: 'Policy baseline', country_id: 'ETH'}],
            {'Policy baseline': [
                {run_name: 'baseline', run_type: 'baseline'},
                {run_name: 'Tax reform', run_type: 'reform', baseline_run: 'baseline'}
            ]},
            [{country_id: 'ETH'}], 'ETH'
        );
        Cases.renderCases(Cases.entries(Cases.model));
        Cases.initEvents();
    }""")

    baseline_menu = page.locator(
        "[data-act='run-menu'][data-case='Policy baseline'][data-run='baseline']"
    )
    baseline_menu.click()
    baseline_actions = baseline_menu.locator("xpath=..//span[@role='menu']")
    expect(baseline_actions).to_be_visible()
    expect(baseline_actions.get_by_text("Add reform", exact=True)).to_be_visible()
    expect(baseline_actions.get_by_text("Delete case", exact=True)).to_be_visible()

    baseline_actions.get_by_text("Add reform", exact=True).click()
    expect(page.locator("#ogcCasesModalHead")).to_have_text("Add a case")
    expect(page.locator("[data-act='case-type'][data-type='reform']")).to_have_class("active")
    expect(page.locator("#ogcCaseBaseline option:checked")).to_have_text("Policy baseline")

    page.locator("[data-act='close']").click()
    reform_menu = page.locator(
        "[data-act='run-menu'][data-case='Policy baseline'][data-run='Tax reform']"
    )
    reform_menu.click()
    reform_actions = reform_menu.locator("xpath=..//span[@role='menu']")
    expect(reform_actions).to_be_visible()
    expect(reform_actions.get_by_text("Delete reform", exact=True)).to_be_visible()
    expect(reform_actions.get_by_text("Add reform", exact=True)).to_have_count(0)


def test_create_reform_opens_parameters_for_the_selected_baseline(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGCases")
    expect(page.locator("#ogcCasesPage")).to_be_visible()
    page.evaluate("""async () => {
        const { default: Cases } = await import(new URL('App/Controller/OGCases.js', location.href).href);
        const { Model } = await import(new URL('App/Model/OGCases.Model.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        Cases.workspace = {country_id: 'ETH', country_name: 'Ethiopia'};
        Cases.model = new Model(
            [{casename: 'Policy baseline', country_id: 'ETH'}],
            {'Policy baseline': [{run_name: 'baseline', run_type: 'baseline'}]},
            [{country_id: 'ETH'}], 'ETH'
        );
        window.__newCaseCalls = [];
        Ogc.saveCase = async () => { throw new Error('A reform must not create a case container'); };
        Ogc.createRun = async data => {
            window.__newCaseCalls.push(data);
            return {status_code: 'success'};
        };
        Cases.initEvents();
        Cases.openNewCase('reform');
    }""")
    page.locator("#ogcCaseName").fill("Corporate tax cut")
    page.locator("#ogcCaseDesc").fill("Reduce the corporate income tax rate")
    page.locator("[data-act='new-case-confirm']").click()
    page.wait_for_url("**/#/OGParameters")

    result = page.evaluate("""({
        calls: window.__newCaseCalls,
        selection: JSON.parse(localStorage.getItem('osy-ogc-selection'))
    })""")
    assert result['calls'] == [{
        'country_id': 'ETH',
        'casename': 'Policy baseline',
        'run_name': 'Corporate tax cut',
        'run_type': 'reform',
        'baseline_run': 'baseline',
        'description': 'Reduce the corporate income tax rate',
    }]
    assert result['selection'] == {
        'casename': 'Policy baseline',
        'run_name': 'Corporate tax cut',
        'run_type': 'reform',
        'baseline_run': 'baseline',
        'country_id': 'ETH',
        'display_name': 'Corporate tax cut',
        'baseline_display_name': 'Policy baseline',
    }


def test_create_baseline_creates_its_container_and_opens_parameters(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGCases")
    expect(page.locator("#ogcCasesPage")).to_be_visible()
    page.evaluate("""async () => {
        const { default: Cases } = await import(new URL('App/Controller/OGCases.js', location.href).href);
        const { Model } = await import(new URL('App/Model/OGCases.Model.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        Cases.workspace = {country_id: 'ETH', country_name: 'Ethiopia'};
        Cases.model = new Model([], {}, [{country_id: 'ETH'}], 'ETH');
        window.__newCaseCalls = [];
        Ogc.saveCase = async data => {
            window.__newCaseCalls.push({method: 'saveCase', data});
            return {status_code: 'created'};
        };
        Ogc.createRun = async data => {
            window.__newCaseCalls.push({method: 'createRun', data});
            return {status_code: 'success'};
        };
        Cases.initEvents();
        Cases.openNewCase();
    }""")
    page.locator("#ogcCaseName").fill("Alternative baseline")
    page.locator("#ogcCaseDesc").fill("A second policy starting point")
    page.locator("[data-act='new-case-confirm']").click()
    page.wait_for_url("**/#/OGParameters")

    result = page.evaluate("""({
        calls: window.__newCaseCalls,
        selection: JSON.parse(localStorage.getItem('osy-ogc-selection'))
    })""")
    assert result['calls'] == [
        {
            'method': 'saveCase',
            'data': {
                'casename': 'Alternative baseline',
                'country_id': 'ETH',
                'description': 'A second policy starting point',
            },
        },
        {
            'method': 'createRun',
            'data': {
                'country_id': 'ETH',
                'casename': 'Alternative baseline',
                'run_name': 'baseline',
                'run_type': 'baseline',
                'description': 'A second policy starting point',
            },
        },
    ]
    assert result['selection'] == {
        'casename': 'Alternative baseline',
        'run_name': 'baseline',
        'run_type': 'baseline',
        'baseline_run': None,
        'country_id': 'ETH',
        'display_name': 'Alternative baseline',
    }


def test_failed_baseline_run_creation_rolls_back_the_case(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGCases")
    expect(page.locator("#ogcCasesPage")).to_be_visible()
    page.evaluate("""async () => {
        const { default: Cases } = await import(new URL('App/Controller/OGCases.js', location.href).href);
        const { Model } = await import(new URL('App/Model/OGCases.Model.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        Cases.workspace = {country_id: 'ETH', country_name: 'Ethiopia'};
        Cases.model = new Model([], {}, [{country_id: 'ETH'}], 'ETH');
        window.__rollbackCalls = [];
        Ogc.saveCase = async () => ({status_code: 'created'});
        Ogc.createRun = async () => { throw 'run creation failed'; };
        Ogc.deleteCase = async (countryId, casename) => {
            window.__rollbackCalls.push([countryId, casename]);
            return {status_code: 'success'};
        };
        Cases.initEvents();
        Cases.openNewCase();
    }""")
    page.locator("#ogcCaseName").fill("Incomplete baseline")
    page.locator("[data-act='new-case-confirm']").click()
    expect(page.locator("#ogcCaseErr")).to_contain_text("run creation failed")
    assert page.evaluate("window.__rollbackCalls") == [['ETH', 'Incomplete baseline']]


def test_runless_case_is_visible_and_recoverable(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { default: Cases } = await import(new URL('App/Controller/OGCases.js', location.href).href);
        const { Model } = await import(new URL('App/Model/OGCases.Model.js', location.href).href);
        Cases.workspace = {country_id: 'ETH', country_name: 'Ethiopia'};
        Cases.model = new Model(
            [{casename: 'Incomplete baseline', country_id: 'ETH'}],
            {'Incomplete baseline': []}, [{country_id: 'ETH'}], 'ETH'
        );
        const entries = Cases.entries(Cases.model);
        return {count: entries.length, html: Cases.entryRows(entries[0])};
    }""")
    assert result['count'] == 1
    assert 'Incomplete baseline' in result['html']
    assert 'Retry setup' in result['html']
    assert 'Delete case' in result['html']


def test_run_queue_orders_dependencies_and_marks_cache(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { default: Runs } = await import(new URL('App/Controller/OGRuns.js', location.href).href);
        const c = {country_id: 'ETH', casename: 'ethiopia-case'};
        const base = {case: c, key: 'ETH:ethiopia-case:base', name: 'Base', run: {
            run_name: 'base', run_type: 'baseline', status: 'pending'
        }};
        const reform = {case: c, key: 'ETH:ethiopia-case:reform', name: 'Reform', run: {
            run_name: 'reform', run_type: 'reform', baseline_run: 'base', status: 'pending'
        }};
        const dependency = Runs.buildQueue(
            [reform, base], {'ETH:ethiopia-case:reform': true}, false
        );
        base.run.status = 'completed';
        reform.run.status = 'completed';
        const cached = Runs.buildQueue([reform, base], {
            'ETH:ethiopia-case:reform': true, 'ETH:ethiopia-case:base': true
        }, false);
        base.stale = true;
        const invalidated = Runs.buildQueue(
            [reform, base], {'ETH:ethiopia-case:reform': true}, false
        );
        return {
            dependency: dependency.map(j => [j.entry.run.run_name, j.state, !!j.note]),
            cached: cached.map(j => [j.entry.run.run_name, j.state]),
            invalidated: invalidated.map(j => [j.entry.run.run_name, j.state])
        };
    }""")
    assert result['dependency'] == [['base', 'planned', True], ['reform', 'planned', False]]
    assert result['cached'] == [['base', 'reused'], ['reform', 'reused']]
    assert result['invalidated'] == [['base', 'planned'], ['reform', 'planned']]


def test_calibration_defaults_are_reference_only(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { default: Cases } = await import(new URL('App/Controller/OGCases.js', location.href).href);
        Cases.workspace = {country_id: 'ETH', country_name: 'Ethiopia'};
        Cases.model = {records: {ETH: {}}, cases: []};
        const row = Cases.defaultRow();
        const panel = Cases.panel('cubes', 'Baselines', [], true);
        return {
            row,
            panel,
            choices: Cases.baselineChoices()
        };
    }""")
    assert 'Calibration defaults' in result['row']
    assert 'reference only' in result['row']
    assert 'not runnable' in result['row']
    assert 'Create baseline' in result['row']
    assert 'Baselines <span>(0)</span>' in result['panel']
    assert result['choices'] == []
    assert 'Default baseline' not in result['row']


def test_parameters_page_token_also_requires_the_current_page(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { default: Parameters } = await import(
            new URL('App/Controller/OGParameters.js', location.href).href
        );
        localStorage.setItem('osy-pageId', 'OGParameters');
        Parameters.onLoad();
        const token = Parameters.pageID;
        const current = Parameters.isCurrent(token);
        localStorage.setItem('osy-pageId', 'OGRuns');
        return {current, afterNavigation: Parameters.isCurrent(token)};
    }""")
    assert result == {'current': True, 'afterNavigation': False}


def test_og_run_clears_clews_messages_and_late_home_is_scoped(page, base_url):
    page.goto(base_url)
    page.evaluate("""async () => {
        const { Message } = await import(new URL('Classes/Message.Class.js', location.href).href);
        Message.info('Please select existing or create new model to proceed!');
        localStorage.setItem('osy-ogc-country', JSON.stringify({
            country_id: 'ETH', country_name: 'Ethiopia'
        }));
    }""")
    page.goto(f"{base_url}/#/OGRuns")
    expect(page.locator('#ogcRunsPage')).to_be_visible()
    expect(page.locator('#osy-info')).to_be_empty()

    result = page.evaluate("""async () => {
        const { default: Home } = await import(new URL('App/Controller/Home.js', location.href).href);
        const { Base } = await import(new URL('Classes/Base.Class.js', location.href).href);
        let release;
        const session = new Promise(resolve => { release = resolve; });
        Base.getSession = async () => await session;
        Base.getCaseStudies = async () => [];
        localStorage.setItem('osy-model', 'clews');
        localStorage.setItem('osy-pageId', 'Home');
        window.location.hash = '#/OGRuns';
        Home.onLoad();
        localStorage.setItem('osy-model', 'og');
        localStorage.setItem('osy-pageId', 'OGRuns');
        release({session: null});
        await new Promise(resolve => setTimeout(resolve, 0));
        await new Promise(resolve => setTimeout(resolve, 0));
        return document.querySelector('#osy-info').textContent.trim();
    }""")
    assert result == ''


def test_run_selection_defaults_and_explicit_handoff(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { default: Runs } = await import(new URL('App/Controller/OGRuns.js', location.href).href);
        const entry = {key: 'ETH:case-one:baseline'};
        Runs.workspace = {country_id: 'ETH'};
        Runs.entries = [entry];
        Runs.selected = {};
        localStorage.setItem('osy-ogc-selection', JSON.stringify({
            casename: 'case-one', run_name: 'baseline', country_id: 'ETH'
        }));
        Runs.applyInitialSelection('OGCases');
        const direct = Runs.selected[entry.key];

        localStorage.setItem('osy-ogc-run-selection', JSON.stringify({
            casename: 'case-one', run_name: 'baseline', country_id: 'ETH'
        }));
        Runs.applyInitialSelection('OGCases');
        const fromCaseAction = Runs.selected[entry.key];

        Runs.applyInitialSelection('OGParameters');
        const fromParameters = Runs.selected[entry.key];
        return {direct, fromCaseAction, fromParameters};
    }""")
    assert result == {
        'direct': False,
        'fromCaseAction': True,
        'fromParameters': True,
    }


def test_navigation_stops_unsent_run_plan(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGRuns")
    expect(page.locator('#ogcRunsPage')).to_be_visible()
    result = page.evaluate("""async () => {
        const { default: Runs } = await import(new URL('App/Controller/OGRuns.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        localStorage.setItem('osy-ogc-country', JSON.stringify({country_id: 'ETH', country_name: 'Ethiopia'}));
        localStorage.setItem('osy-pageId', 'OGRuns');
        localStorage.setItem('osy-model', 'og');
        const records = [{
            run_name: 'base', run_type: 'baseline', status: 'pending'
        }, {
            run_name: 'reform', run_type: 'reform', baseline_run: 'base', status: 'pending'
        }];
        Ogc.getCases = async () => [{casename: 'case-one', country_id: 'ETH'}];
        Ogc.getRuns = async () => ({runs: records});
        Ogc.getRunQueue = async () => ({active: null, queued: []});
        Ogc.getRunStatus = async (countryId, casename, runName) => ({
            run_state: 'pending', run_stage: null, run_log: []
        });
        Runs.onLoad('OGCases');
        await new Promise(resolve => setTimeout(resolve, 20));
        Runs.selected = {
            'ETH:case-one:base': true, 'ETH:case-one:reform': true
        };
        let release;
        const accepted = new Promise(resolve => { release = resolve; });
        const calls = [];
        Ogc.run = async (countryId, casename, runName) => {
            calls.push(runName);
            await accepted;
            return {status_code: 'success'};
        };
        const running = Runs.runSelected();
        while (!calls.length) await new Promise(resolve => setTimeout(resolve, 0));
        history.replaceState(null, '', '#/OGCases');
        release();
        await running;
        return {calls, running: Runs.running};
    }""")
    assert result == {'calls': ['base'], 'running': False}


def test_run_reconstructs_and_cancels_backend_queue(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGRuns")
    expect(page.locator('#ogcRunsPage')).to_be_visible()
    result = page.evaluate("""async () => {
        const { default: Runs } = await import(new URL('App/Controller/OGRuns.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        localStorage.setItem('osy-ogc-country', JSON.stringify({country_id: 'ETH', country_name: 'Ethiopia'}));
        localStorage.setItem('osy-pageId', 'OGRuns');
        localStorage.setItem('osy-model', 'og');
        Ogc.getCases = async () => [{casename: 'case-one', country_id: 'ETH'}];
        Ogc.getRuns = async () => ({runs: [{
            run_name: 'baseline', run_type: 'baseline', status: 'pending'
        }]});
        const queueCases = [];
        Ogc.getRunQueue = async (countryId, casename) => {
            queueCases.push(casename);
            return {active: null, queued: [{
            casename: 'case-one', run_name: 'baseline', state: 'queued', queue_position: 2
            }]};
        };
        let statusCalls = 0;
        Ogc.getRunStatus = async () => {
            statusCalls++;
            return {
            run_state: 'pending', run_stage: 'Queued', queue_position: 2,
            run_log: ['Worker accepted the run.']
            };
        };
        const cancelled = [];
        Ogc.cancelRun = async (countryId, casename, runName) => {
            cancelled.push([countryId, casename, runName]);
        };
        Runs.onLoad('OGCases');
        while (!Runs.entries.length || Runs.entries[0].state != 'queued') {
            await new Promise(resolve => setTimeout(resolve, 0));
        }
        const before = {
            state: Runs.entries[0].state,
            selected: Runs.selected[Runs.entries[0].key],
            queue: document.querySelector('#ogcCurrentQueue').textContent,
            perJobCancel: document.querySelectorAll('[data-act="cancel-job"]').length,
            statusCalls
        };
        await Runs.cancelEntry('ETH:case-one:baseline');
        return {before, after: Runs.entries[0].state, cancelled, queueCases};
    }""")
    assert result['before']['state'] == 'queued'
    assert result['before']['selected'] is False
    assert 'Queue position 2' in result['before']['queue']
    assert result['before']['perJobCancel'] == 0
    assert result['before']['statusCalls'] == 0
    assert result['after'] == 'cancelled'
    assert result['cancelled'] == [['ETH', 'case-one', 'baseline']]
    assert result['queueCases'] == ['case-one']


def test_idle_run_monitor_keeps_checking_queue_without_status_fanout(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGRuns")
    expect(page.locator('#ogcRunsPage')).to_be_visible()
    result = page.evaluate("""async () => {
        const { default: Runs } = await import(new URL('App/Controller/OGRuns.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        localStorage.setItem('osy-pageId', 'OGRuns');
        Ogc.getCases = async () => [{casename: 'case-one', country_id: 'ETH'}];
        Ogc.getRuns = async () => ({runs: [{
            run_name: 'baseline', run_type: 'baseline', status: 'pending', reusable: false
        }]});
        let queueCalls = 0;
        let statusCalls = 0;
        Ogc.getRunQueue = async () => {
            queueCalls++;
            return {active: null, queued: []};
        };
        Ogc.getRunStatus = async () => {
            statusCalls++;
            return {run_state: 'pending'};
        };
        Runs.onLoad('OGCases');
        let deadline = Date.now() + 5000;
        while (queueCalls < 2 && Date.now() < deadline){
            await new Promise(resolve => setTimeout(resolve, 25));
        }
        history.replaceState(null, '', '#/OGCases');
        return {queueCalls, statusCalls};
    }""")
    assert result['queueCalls'] >= 2
    assert result['statusCalls'] == 0


def test_live_log_scroll_follows_bottom_and_preserves_manual_position(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { default: Runs } = await import(new URL('App/Controller/OGRuns.js', location.href).href);
        document.querySelector('#ogcCurrentQueue')?.remove();
        const host = document.createElement('div');
        host.id = 'ogcCurrentQueue';
        document.body.appendChild(host);
        const renderLog = lines => {
            host.innerHTML = `<div class="ogc-job" data-job="run"><pre class="ogc-live-run-log" style="display:block;height:100px;overflow:auto">${'line\\n'.repeat(lines)}</pre></div>`;
            return host.querySelector('pre');
        };
        let log = renderLog(100);
        log.scrollTop = log.scrollHeight;
        const bottom = Runs.captureLiveLogScroll();

        log = renderLog(120);
        Runs.restoreLiveLogScroll(bottom);
        const followed = log.scrollHeight - log.scrollTop - log.clientHeight < 2;

        log.scrollTop = 75;
        const manual = Runs.captureLiveLogScroll();
        log = renderLog(140);
        Runs.restoreLiveLogScroll(manual);
        return {followed, preserved: log.scrollTop};
    }""")
    assert result == {'followed': True, 'preserved': 75}


def test_backend_reusability_overrides_browser_cache(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { default: Runs } = await import(new URL('App/Controller/OGRuns.js', location.href).href);
        const entry = {
            key: 'ETH:case-one:baseline',
            case: {country_id: 'ETH', casename: 'case-one'},
            run: {run_name: 'baseline', run_type: 'baseline', status: 'completed'},
            state: 'completed', stale: false, reusable: false
        };
        localStorage.removeItem('osy-ogc-run-stale');
        const plan = Runs.buildQueue([entry], {[entry.key]: true}, false);
        return {state: plan[0].state};
    }""")
    assert result == {'state': 'planned'}


def test_invalidated_pending_run_is_shown_as_stale_with_reason(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { default: Runs } = await import(new URL('App/Controller/OGRuns.js', location.href).href);
        const entries = Runs.flatten([{
            case: {country_id: 'ETH', casename: 'case-one'},
            runs: [{
                run_name: 'baseline', run_type: 'baseline', status: 'pending',
                reusable: false,
                stale_reason: 'Parameters changed after the latest completed run.'
            }]
        }]);
        return {
            state: entries[0].state,
            stale: entries[0].stale,
            reason: entries[0].staleReason
        };
    }""")
    assert result == {
        'state': 'stale',
        'stale': True,
        'reason': 'Parameters changed after the latest completed run.',
    }


def test_new_backend_attempt_clears_previous_activity(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { default: Runs } = await import(new URL('App/Controller/OGRuns.js', location.href).href);
        const entry = {
            run: {status: 'failed', error: 'old failure'}, state: 'failed',
            stage: 'Old stage', iteration: 12, error: 'old failure',
            log: ['old output'], completedAt: '2026-08-12T10:00:00Z'
        };
        Runs.applyBackendStatus(entry, {
            status: 'queued', run_stage: null, run_iteration: null,
            run_log: [], error: null, completed_at: null
        });
        return {
            state: entry.state, stage: entry.stage, iteration: entry.iteration,
            error: entry.error, log: entry.log, completedAt: entry.completedAt
        };
    }""")
    assert result == {
        'state': 'queued', 'stage': '', 'iteration': None,
        'error': '', 'log': [], 'completedAt': ''
    }


def test_single_job_cancel_does_not_stop_remaining_plan(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { default: Runs } = await import(new URL('App/Controller/OGRuns.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        const execution = {id: 17, pageToken: 1};
        const entry = {
            key: 'ETH:case-one:baseline',
            case: {country_id: 'ETH', casename: 'case-one'},
            run: {run_name: 'baseline'}, state: 'queued'
        };
        Runs.entries = [entry];
        Runs.plan = [{entry, state: 'queued'}];
        Runs.execution = execution;
        Runs.stopExecutionID = null;
        Ogc.cancelRun = async () => ({status_code: 'success'});
        await Runs.cancelEntry(entry.key);
        return {state: entry.state, stopExecutionID: Runs.stopExecutionID};
    }""")
    assert result == {'state': 'cancelled', 'stopExecutionID': None}


def test_cached_status_error_always_reenables_run_controls(page, base_url):
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGRuns")
    expect(page.locator('#ogcRunsPage')).to_be_visible()
    result = page.evaluate("""async () => {
        const { default: Runs } = await import(new URL('App/Controller/OGRuns.js', location.href).href);
        const { Ogc } = await import(new URL('Classes/Ogc.Class.js', location.href).href);
        localStorage.setItem('osy-ogc-country', JSON.stringify({country_id: 'ETH', country_name: 'Ethiopia'}));
        localStorage.setItem('osy-pageId', 'OGRuns');
        localStorage.setItem('osy-model', 'og');
        localStorage.setItem('osy-ogc-run-selection', JSON.stringify({
            casename: 'case-one', run_name: 'baseline', country_id: 'ETH'
        }));
        Ogc.getCases = async () => [{casename: 'case-one', country_id: 'ETH'}];
        Ogc.getRuns = async () => ({runs: [{
            run_name: 'baseline', run_type: 'baseline', status: 'completed',
            completed_at: '2026-08-13T10:00:00Z'
        }]});
        Ogc.getRunQueue = async () => ({active: null, queued: []});
        Runs.onLoad('OGCases');
        while (!Runs.entries.length) await new Promise(resolve => setTimeout(resolve, 0));
        Ogc.getRunStatus = async () => { throw new Error('status unavailable'); };
        await Runs.runSelected();
        return {
            running: Runs.running,
            state: Runs.plan[0].state,
            buttonDisabled: document.querySelector('#ogcRunSelected').disabled,
            headings: document.querySelector('#ogcRunsPage').textContent
        };
    }""")
    assert result['running'] is False
    assert result['state'] == 'failed'
    assert result['buttonDisabled'] is False
    assert 'Runs' in result['headings']
    assert 'Current queue' in result['headings']
    assert 'Latest outcomes' in result['headings']
    assert 'Re-run completed selections' in result['headings']
    assert 'Queue & history' not in result['headings']


def test_runs_are_read_from_the_grouped_shape(page, base_url):
    """getRuns answers {baseline: [...], reform: [...]}, not a flat list. Reading
    it as a list finds no runs and every case renders as empty."""
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGCases.Model.js', location.href).href);
        const grouped = {
            c1: {
                baseline: [{ run_name: 'base', run_type: 'baseline', status: 'completed' }],
                reform: [{ run_name: 'rf', run_type: 'reform', baseline_run: 'base', status: 'pending' }]
            }
        };
        const m = new Model([{ casename: 'c1', country_id: 'ETH' }], grouped, [{ country_id: 'ETH' }]);
        // a flat list must keep working too, so a backend change cannot blank the page
        const flat = new Model(
            [{ casename: 'c1', country_id: 'ETH' }],
            { c1: [{ run_name: 'base', run_type: 'baseline' }] },
            [{ country_id: 'ETH' }]
        );
        // an unknown group key is still a run the user made
        const extra = new Model(
            [{ casename: 'c1', country_id: 'ETH' }],
            { c1: { baseline: [{ run_name: 'b', run_type: 'baseline' }],
                    something_new: [{ run_name: 'x', run_type: 'other' }] } },
            [{ country_id: 'ETH' }]
        );
        const c = m.cases[0];
        return {
            total: c.runs.length,
            baselines: Model.baselines(c.runs).map(r => r.run_name),
            reforms: Model.reformsOf(c.runs, 'base').map(r => r.run_name),
            baseline_done: Model.baselineDone(c.runs, 'base'),
            flat_total: flat.cases[0].runs.length,
            extra_total: extra.cases[0].runs.length
        };
    }""")
    assert result['total'] == 2, "the grouped shape must be flattened, not dropped"
    assert result['baselines'] == ['base']
    assert result['reforms'] == ['rf']
    assert result['baseline_done'] is True
    assert result['flat_total'] == 1, "a flat array must still be accepted"
    assert result['extra_total'] == 2, "an unfamiliar group key must not lose its runs"


def test_suffix_families_are_grouped_without_being_locked(page, base_url):
    """OG-Core carries whole families of derived parameters (_preTP, _ge) that a
    calibration can extend. Naming each one would go stale, so the suffix rules
    file them as reference data without deciding whether experts may edit them."""
    page.goto(f"{base_url}/#/OGParameters")
    result = page.evaluate("""async () => {
        const m = await import(new URL('App/Model/OGParams.Overlay.js', location.href).href);
        const mk = n => m.decorate(n, { title: n, shape: 'time', default: [[1]] });
        return {
            preTP: mk('omega_preTP'),
            ge: mk('cit_rate_ge'),
            // a name the rules do not match still falls through to the default
            plain: mk('some_future_param'),
            // an explicit table mapping must win over the old read-only suffix rule
            explicit: m.decorate('omega_S_preTP', { title: 'x', shape: 'time', default: [1, 2] }),
            futureSolver: m.decorate('future_solver_setting', {
                title: 'Future solver setting', section: 'Model Solution Parameters',
                shape: 'scalar', default: 1
            })
        };
    }""")
    for key in ('preTP', 'ge'):
        assert result[key]['group'] == 'arrays', f"{key} should be reference data"
        assert result[key]['readOnly'] is False
    # an unmatched name keeps the old fallback behaviour
    assert result['plain']['group'] == 'advanced'
    assert result['plain']['readOnly'] is False
    # explicitly mapped array parameters use the reviewed table editor
    assert result['explicit']['tableEditable'] is True
    assert result['explicit']['readOnly'] is False
    assert result['explicit']['expertEditReason'] == 'calibration'
    assert result['futureSolver']['readOnly'] is True
    assert result['futureSolver']['readOnlyReason'] == 'solver'


def test_parameters_page_without_a_selection_is_empty(page, base_url):
    """No run selected: the page must say so rather than call the backend."""
    page.goto(base_url)
    page.evaluate("""localStorage.setItem('osy-ogc-country', JSON.stringify({
        country_id: 'ETH', country_name: 'Ethiopia'
    }))""")
    page.goto(f"{base_url}/#/OGParameters")
    expect(page.locator("#ogcParamsPage")).to_be_visible()
    expect(page.locator("#ogcParamsEmpty")).to_be_visible()
    expect(page.locator("#ogcParamsEmptyTitle")).to_have_text("No run selected")
    expect(page.locator("#ogcParamsEditbar")).to_be_hidden()


def test_parameter_metadata_stays_compact(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { default: Parameters } = await import(
            new URL('App/Controller/OGParameters.js', location.href).href
        );
        const description = 'Parameter summarizing the quadratic effect of debt.';
        const bounded = {
            name: 'bounded', title: 'Bounded parameter', description,
            help: '', hasRange: true, min: 0, max: 1, readOnly: false
        };
        const broad = {
            name: 'broad', title: 'Broad parameter', description,
            help: '', hasRange: true, min: -99000000000, max: 99000000000,
            readOnly: false
        };
        return {
            label: Parameters.labelHtml(bounded),
            boundedHint: Parameters.hintHtml(bounded),
            broadHint: Parameters.hintHtml(broad),
            boundedSlider: Parameters.hasUsefulRange(bounded),
            broadSlider: Parameters.hasUsefulRange(broad),
            preciseSlider: Parameters.hasUsefulRange(
                {hasRange: true, min: -0.01, max: 0.08, type: 'rate'},
                0.05952286163357212
            ),
            preciseDisplay: Parameters.inputNumber(0.05952286163357212)
        };
    }""")
    assert result['label'].find(result_description := 'Parameter summarizing the quadratic effect of debt.') >= 0
    assert result_description not in result['boundedHint']
    assert 'default' not in result['boundedHint']
    assert 'Allowed' in result['boundedHint']
    assert '[0, 1]' in result['boundedHint']
    assert '[-9.9 × 10¹⁰, 9.9 × 10¹⁰]' in result['broadHint']
    assert result['boundedSlider'] is True
    assert result['broadSlider'] is False
    assert result['preciseSlider'] is False
    assert result['preciseDisplay'] == 0.059522862


def test_time_paths_are_editable(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGParameters.Model.js', location.href).href);
        const { default: Parameters } = await import(
            new URL('App/Controller/OGParameters.js', location.href).href
        );
        const model = new Model(
            {
                start_year: {title: 'Start year', type: 'year', shape: 'scalar', default: 2025, min: 2013, max: 2101},
                tau_payroll: {title: 'Payroll tax', description: 'API description', type: 'rate', shape: 'time', default: [0.18], min: 0, max: 0.99}
            },
            {},
            {casename: 'c1', run_name: 'reform', run_type: 'reform', baseline_run: 'base'},
            {}
        );
        const html = Parameters.fieldHtml(model, 'tau_payroll');
        model.cur.tau_payroll = [0.18, 0.2];
        return {
            editable: model.editable('tau_payroll'),
            html,
            payload: model.savePayload(),
            field: model.fields.tau_payroll
        };
    }""")
    assert result['editable'] is True
    assert 'data-role="path-cell"' in result['html']
    assert '2025' in result['html']
    assert 'Add 2026' in result['html']
    assert 'API description' in result['html']
    assert 'readOnlyNote' not in result['field']
    assert result['payload'] == {'tau_payroll': [0.18, 0.2]}


def test_singleton_matrices_use_human_controls_and_keep_backend_shape(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGParameters.Model.js', location.href).href);
        const { default: Parameters } = await import(
            new URL('App/Controller/OGParameters.js', location.href).href
        );
        const schema = {
            start_year: {title: 'Start year', type: 'year', shape: 'scalar', default: 2025, min: 2013, max: 2101},
            cit_rate: {
                title: 'Corporate income tax rate',
                description: "Set value for base year, click '+' to add value for next year.",
                type: 'rate', shape: 'time_x_industry', dimensions: [1, 1],
                default: [[0.3]], min: 0, max: 0.99
            },
            inv_tax_credit: {
                title: 'Investment tax credit rate', description: 'Credit on investment.',
                type: 'level', shape: 'time_x_industry', dimensions: [1, 1],
                default: [[0.1]], min: -1, max: 1
            },
            io_matrix: {
                title: 'Input-output matrix', description: 'Maps one good to one industry.',
                type: 'rate', shape: 'time_x_industry', dimensions: [1, 1],
                default: [[1]], min: 0, max: 1
            },
            flag: {
                title: 'Diagnostic flag', type: 'level', datatype: 'bool', shape: 'scalar',
                default: false, choices: [true, false], min: null, max: null
            }
        };
        const model = new Model(schema, {}, {
            casename: 'c1', run_name: 'base', run_type: 'baseline'
        }, {});
        model.cur.cit_rate = [0.31, 0.32];
        model.cur.inv_tax_credit = 0.2;
        return {
            citDimension: model.fields.cit_rate.dimension,
            citHtml: Parameters.fieldHtml(model, 'cit_rate'),
            creditDimension: model.fields.inv_tax_credit.dimension,
            creditHtml: Parameters.fieldHtml(model, 'inv_tax_credit'),
            ioEditable: model.editable('io_matrix'),
            ioHtml: Parameters.fieldHtml(model, 'io_matrix'),
            flagHtml: Parameters.fieldHtml(model, 'flag'),
            payload: model.savePayload()
        };
    }""")
    assert result['citDimension'] == 'by_year'
    assert 'data-role="path-cell"' in result['citHtml']
    assert 'edit-table' not in result['citHtml']
    assert result['creditDimension'] == 'scalar'
    assert 'data-role="range"' in result['creditHtml']
    assert 'edit-table' not in result['creditHtml']
    assert result['ioEditable'] is True
    assert 'data-role="range"' in result['ioHtml']
    assert 'edit-table' not in result['ioHtml']
    assert '>Yes<' in result['flagHtml'] and '>No<' in result['flagHtml']
    assert '>true<' not in result['flagHtml'] and '>false<' not in result['flagHtml']
    assert result['payload']['cit_rate'] == [[0.31], [0.32]]
    assert result['payload']['inv_tax_credit'] == [[0.2]]


def test_one_by_j_rows_do_not_open_a_table_editor(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGParameters.Model.js', location.href).href);
        const { default: Parameters } = await import(
            new URL('App/Controller/OGParameters.js', location.href).href
        );
        const model = new Model({
            labor_income_tax_noncompliance_rate: {
                title: 'Labor income tax noncompliance rate', type: 'rate',
                shape: 'time_x_industry', dimensions: [1, 7],
                default: [[0, 0, 0, 0, 0, 0, 0]], min: 0, max: 1
            }
        }, {}, {casename: 'c1', run_name: 'base', run_type: 'baseline'}, {});
        return {
            dimension: model.fields.labor_income_tax_noncompliance_rate.dimension,
            html: Parameters.fieldHtml(model, 'labor_income_tax_noncompliance_rate')
        };
    }""")
    assert result['dimension'] == 'by_j'
    assert result['html'].count('data-role="cell"') == 7
    assert 'edit-table' not in result['html']


def test_column_matrices_are_year_schedules_and_singleton_tensors_are_scalars(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGParameters.Model.js', location.href).href);
        const { default: Parameters } = await import(
            new URL('App/Controller/OGParameters.js', location.href).href
        );
        const model = new Model({
            start_year: {title: 'Start year', type: 'year', shape: 'scalar', default: 2025, min: 2013, max: 2101},
            delta_tau_annual: {
                title: 'Tax depreciation', type: 'rate', shape: 'time_x_industry',
                dimensions: [400, 1], default: [[0.027]], min: 0, max: 1
            },
            etr_params: {
                title: 'Effective tax parameters', type: 'level', shape: 'time',
                dimensions: [1, 1, 1], default: [[[0.2]]], min: -1, max: 1
            },
            tax_func_type: {
                title: 'Tax function', type: 'string', datatype: 'str', shape: 'scalar',
                default: 'linear', choices: ['linear', 'DEP'], min: null, max: null
            }
        }, {}, {casename: 'c1', run_name: 'base', run_type: 'baseline'}, {});
        model.cur.delta_tau_annual.push(0.03);
        model.cur.etr_params = 0.25;
        return {
            scheduleDimension: model.fields.delta_tau_annual.dimension,
            scheduleHtml: Parameters.fieldHtml(model, 'delta_tau_annual'),
            tensorDimension: model.fields.etr_params.dimension,
            tensorHtml: Parameters.fieldHtml(model, 'etr_params'),
            payload: model.savePayload()
        };
    }""")
    assert result['scheduleDimension'] == 'by_year'
    assert 'data-role="path-cell"' in result['scheduleHtml']
    assert 'edit-table' not in result['scheduleHtml']
    assert result['tensorDimension'] == 'scalar'
    assert 'data-role="num"' in result['tensorHtml']
    assert 'edit-table' not in result['tensorHtml']
    assert result['payload']['delta_tau_annual'] == [[0.027], [0.03]]
    assert result['payload']['etr_params'] == [[[0.25]]]


def test_time_path_add_year_inherits_value_and_reports_invalid_year(page, base_url):
    page.goto(base_url)
    page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGParameters.Model.js', location.href).href);
        const { default: Parameters } = await import(
            new URL('App/Controller/OGParameters.js', location.href).href
        );
        document.body.insertAdjacentHTML('beforeend', '<div id="ogcParamsBody"></div>');
        const model = new Model(
            {
                start_year: {title: 'Start year', type: 'year', shape: 'scalar', default: 2025, min: 2013, max: 2101},
                tau_payroll: {title: 'Payroll tax', type: 'rate', shape: 'time', default: [0.18, 0.2], min: 0, max: 0.99}
            },
            {}, {casename: 'c1', run_name: 'base', run_type: 'baseline'}, {}
        );
        Parameters.model = model;
        document.querySelector('#ogcParamsBody').innerHTML = Parameters.fieldHtml(model, 'tau_payroll');
        Parameters.initEvents();
    }""")
    add = page.get_by_role('button', name='Add 2027')
    add.click()
    values = page.locator('[data-role="path-cell"]')
    expect(values).to_have_count(3)
    expect(values.nth(2)).to_have_value('0.2')
    assert values.nth(2).evaluate('(element) => document.activeElement === element')
    expect(page.get_by_role('button', name='Add 2028')).to_be_visible()
    page.get_by_role('button', name='Remove 2026').click()
    expect(values).to_have_count(2)
    expect(page.get_by_role('button', name='Add 2027')).to_be_visible()
    values.nth(0).fill('1.2')
    values.nth(0).dispatch_event('input')
    expect(page.locator('.ogc-validation')).to_have_text('2025 must be within [0, 0.99].')


def test_overlay_keeps_schema_facts_and_adds_decisions(page, base_url):
    """The overlay must not overwrite title/range/default, only add what the
    schema cannot express (read-only status, dimension, group)."""
    page.goto(f"{base_url}/#/OGParameters")
    result = page.evaluate("""async () => {
        const m = await import(new URL('App/Model/OGParams.Overlay.js', location.href).href);
        // a plain scalar policy lever
        const cit = m.decorate('cit_rate', {
            title: 'Corporate income tax rate', description: 'd',
            section: 'Fiscal', subsection: null, type: 'rate', shape: 'scalar',
            default: [[0.21]], min: 0, max: 0.99
        });
        // a structural dimension the run layer refuses to differ on
        const S = m.decorate('S', {
            title: 'Max age', type: 'count', shape: 'scalar',
            default: [[80]], min: 3, max: 80
        });
        // a value the backend dropped for size
        const e = m.decorate('e', {
            title: 'Earnings ability', shape: 'time', default: null, large: true
        });
        // a per-group row the schema reports only as "time"
        const beta = m.decorate('beta_annual', {
            title: 'Time preference', shape: 'time',
            default: [[0.96, 0.96]], min: 0, max: 0.9999
        });
        // a name the overlay does not know at all
        const unknown = m.decorate('some_new_param', {
            title: 'New', shape: 'scalar', default: [[1]]
        });
        const deltaTax = m.decorate('delta_tau_annual', {
            title: 'Tax depreciation', shape: 'time_x_industry', default: [[0.03]]
        });
        const remittance = m.decorate('alpha_RM_T', {
            title: 'Remittances', shape: 'scalar', default: 0.1
        });
        return { cit, S, e, beta, unknown, deltaTax, remittance };
    }""")
    # schema facts survive
    assert result['cit']['title'] == 'Corporate income tax rate'
    assert result['cit']['min'] == 0 and result['cit']['max'] == 0.99
    # decorate passes the schema default through untouched; unwrapping the
    # broadcast form is OGParameters.Model.normalise's job, not the overlay's
    assert result['cit']['def'] == [[0.21]]
    assert result['cit']['readOnly'] is False
    assert result['cit']['group'] == 'taxes'
    # structural dimensions are locked, with the run-guard reason
    assert result['S']['readOnly'] is True
    assert result['S']['readOnlyReason'] == 'structural'
    # large calibration arrays are previewed and loaded only when their table opens
    assert result['e']['large'] is True
    assert result['e']['readOnly'] is False
    assert result['e']['tableEditable'] is True
    # the overlay supplies the dimension the schema collapsed to "time"
    assert result['beta']['dimension'] == 'by_j'
    assert result['cit']['dimension'] == 'scalar'
    # an unknown name still renders, it just lands in the fallback group
    assert result['unknown']['readOnly'] is False
    assert result['unknown']['group'] == 'advanced'
    assert result['deltaTax']['group'] == 'taxes'
    assert result['remittance']['group'] == 'open'


def test_reform_reads_against_its_baseline_not_the_default(page, base_url):
    """A reform's delta reference is its baseline's saved value; a baseline's is
    the calibration default. Getting this backwards changes the question asked."""
    page.goto(f"{base_url}/#/OGParameters")
    result = page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGParameters.Model.js', location.href).href);
        const schema = { cit_rate: {
            title: 'Corporate income tax rate', type: 'rate', shape: 'scalar',
            default: [[0.21]], min: 0, max: 0.99
        } };
        // baseline moved the calibration default 0.21 -> 0.25
        // reform moved its baseline 0.25 -> 0.15
        const reform = new Model(
            schema,
            { cit_rate: [[0.15]] },
            { casename: 'c1', run_name: 'rf', run_type: 'reform', baseline_run: 'base' },
            { cit_rate: [[0.25]] }
        );
        const baseline = new Model(
            schema,
            { cit_rate: [[0.25]] },
            { casename: 'c1', run_name: 'base', run_type: 'baseline' },
            {}
        );
        return {
            reform_ref_auto: reform.refValue('cit_rate', 'auto'),
            reform_ref_def: reform.refValue('cit_rate', 'def'),
            reform_cur: reform.cur.cit_rate,
            reform_changed_vs_own: reform.isChanged('cit_rate', 'auto'),
            reform_payload: reform.savePayload(),
            baseline_ref_auto: baseline.refValue('cit_rate', 'auto'),
            baseline_payload: baseline.savePayload()
        };
    }""")
    # the reform is measured against the baseline's 0.25, not the default 0.21
    assert result['reform_ref_auto'] == 0.25
    assert result['reform_ref_def'] == 0.21
    assert result['reform_cur'] == 0.15
    assert result['reform_changed_vs_own'] is True
    # Human-facing scalar controls preserve the backend's nested storage shape.
    assert result['reform_payload'] == {'cit_rate': [[0.15]]}
    # a baseline is measured against the calibration default
    assert result['baseline_ref_auto'] == 0.21
    assert result['baseline_payload'] == {'cit_rate': [[0.25]]}


def test_preview_reference_does_not_change_what_is_saved(page, base_url):
    """Pointing the deltas at another run is a look, not a re-attachment: the
    saved payload is still computed against the run's true reference."""
    page.goto(f"{base_url}/#/OGParameters")
    result = page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGParameters.Model.js', location.href).href);
        const m = new Model(
            { cit_rate: { title: 'c', type: 'rate', shape: 'scalar',
                          default: [[0.21]], min: 0, max: 0.99 } },
            { cit_rate: [[0.15]] },
            { casename: 'c1', run_name: 'rf', run_type: 'reform', baseline_run: 'base' },
            { cit_rate: [[0.15]] }          // baseline already at 0.15
        );
        // against its own baseline nothing moved, so nothing is saved
        const unchanged = m.isChanged('cit_rate', 'auto');
        const payloadBefore = m.savePayload();
        // previewing against the calibration default shows a difference
        const previewChanged = m.isChanged('cit_rate', 'def');
        const payloadAfter = m.savePayload();
        return { unchanged, payloadBefore, previewChanged, payloadAfter };
    }""")
    assert result['unchanged'] is False
    assert result['payloadBefore'] == {}
    # the preview shows a delta ...
    assert result['previewChanged'] is True
    # ... but changes nothing about what would be written
    assert result['payloadAfter'] == {}


def test_locked_dimensions_are_never_editable(page, base_url):
    """RunJob refuses a reform whose S/T/J/M/I differ from its baseline, so the
    form must not offer them even though the schema gives them a range."""
    page.goto(f"{base_url}/#/OGParameters")
    result = page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGParameters.Model.js', location.href).href);
        const { LOCKED_DIMS } = await import(new URL('App/Model/OGParams.Overlay.js', location.href).href);
        const schema = {};
        LOCKED_DIMS.forEach(d => {
            schema[d] = { title: d, type: 'count', shape: 'scalar',
                          default: [[10]], min: 1, max: 1000 };
        });
        schema.cit_rate = { title: 'c', type: 'rate', shape: 'scalar',
                            default: [[0.21]], min: 0, max: 0.99 };
        const m = new Model(schema, {}, { casename: 'c1', run_name: 'base', run_type: 'baseline' }, {});
        const locked = {};
        LOCKED_DIMS.forEach(d => { locked[d] = m.editable(d); });
        return { locked, dims: LOCKED_DIMS, cit_editable: m.editable('cit_rate') };
    }""")
    # the five the run layer compares
    assert sorted(result['dims']) == ['I', 'J', 'M', 'S', 'T']
    assert all(v is False for v in result['locked'].values()), result['locked']
    # a normal lever is still editable, so the lock is not blanket
    assert result['cit_editable'] is True


def test_tax_function_choice_controls_tax_parameter_tables(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGParameters.Model.js', location.href).href);
        const schema = {
            tax_func_type: {
                title: 'Tax function', type: 'string', datatype: 'str', shape: 'scalar',
                default: 'linear', choices: ['linear', 'DEP'], min: null, max: null
            },
            etr_params: {
                title: 'Effective tax parameters', type: 'level', datatype: 'float',
                shape: 'time_x_industry', default: [[0.2]], min: -1, max: 1
            }
        };
        const model = new Model(schema, {}, {
            casename: 'c1', run_name: 'base', run_type: 'baseline'
        }, {});
        const linear = {
            choice: model.editable('tax_func_type'), table: model.editable('etr_params')
        };
        model.cur.tax_func_type = 'DEP';
        return {linear, nonlinearTable: model.editable('etr_params')};
    }""")
    assert result['linear'] == {'choice': True, 'table': True}
    assert result['nonlinearTable'] is True


def test_array_parameters_use_a_compact_preview_and_round_trip_table_data(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGParameters.Model.js', location.href).href);
        const { default: Parameters } = await import(
            new URL('App/Controller/OGParameters.js', location.href).href
        );
        const { OGTableEditor } = await import(
            new URL('App/Controller/OGTableEditor.js', location.href).href
        );
        const value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]];
        const model = new Model(
            { io_matrix: {title: 'Input-output matrix', shape: 'time_x_industry',
                default: value, min: 0, max: 1} },
            {}, {casename: 'c1', run_name: 'base', run_type: 'baseline'}, {}
        );
        const rows = OGTableEditor.rows(value, value);
        rows[1].value_2 = 0.9;
        const fallbackModel = new Model(
            { io_matrix: {title: 'Input-output matrix', shape: 'time_x_industry',
                default: value, min: 0, max: 1} },
            {}, {casename: 'c1', run_name: 'base', run_type: 'baseline'}, {}
        );
        fallbackModel.cur.io_matrix[0][0] = 0.8;
        return {
            editable: model.editable('io_matrix'),
            preview: Parameters.fieldHtml(model, 'io_matrix'),
            roundTrip: OGTableEditor.value(rows, [2, 3]),
            shape: OGTableEditor.shapeLabel(value),
            baseIsIndependent: fallbackModel.base.io_matrix[0][0] === 0.1,
            fallbackChanged: fallbackModel.changedNames().includes('io_matrix'),
            nullEqualsZero: Model.equal(null, 0),
            blankInvalid: Parameters.outOfRange(model.fields.io_matrix, [[0.1, null]]),
            removedValueCount: Parameters.countDifferences([0.1], [0.1, 0.2])
        };
    }""")
    assert result['editable'] is True
    assert 'data-act="edit-table"' in result['preview']
    assert '<table>' in result['preview']
    assert result['roundTrip'] == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.9]]
    assert result['shape'] == '2 × 3'
    assert result['baseIsIndependent'] is True
    assert result['fallbackChanged'] is True
    assert result['nullEqualsZero'] is False
    assert result['blankInvalid'] is True
    assert result['removedValueCount'] == 1


def test_unchanged_lazy_defaults_and_string_choices_do_not_block_save(page, base_url):
    page.goto(base_url)
    result = page.evaluate("""async () => {
        const { Model } = await import(new URL('App/Model/OGParameters.Model.js', location.href).href);
        const { default: Parameters } = await import(
            new URL('App/Controller/OGParameters.js', location.href).href
        );
        const model = new Model({
            TPI_outer_method: {
                title: 'TPI method', type: 'string', datatype: 'str', shape: 'scalar',
                default: 'picard', choices: ['picard', 'anderson'], min: null, max: null
            },
            e: {
                title: 'Effective labor', type: 'level', datatype: 'float',
                shape: 'time_x_industry', default: null, large: true,
                preview: [[0.4, 0.5]], dimensions: [80, 7], min: 0, max: 9e99
            }
        }, {}, {casename: 'c1', run_name: 'base', run_type: 'baseline'}, {});
        const initial = Parameters.invalidChangedNames(model);
        const methodHtml = Parameters.fieldHtml(model, 'TPI_outer_method');
        model.cur.TPI_outer_method = 'invalid';
        const invalidChoice = Parameters.invalidChangedNames(model);
        model.cur.TPI_outer_method = 'anderson';
        const validChoice = Parameters.invalidChangedNames(model);
        return {initial, methodHtml, invalidChoice, validChoice};
    }""")
    assert result['initial'] == []
    assert '<option value="picard" selected>' in result['methodHtml']
    assert result['invalidChoice'] == ['TPI_outer_method']
    assert result['validChoice'] == []


def test_table_editor_copies_a_selected_numeric_cell(page, base_url):
    page.goto(base_url)
    page.evaluate("""async () => {
        document.body.insertAdjacentHTML('beforeend', `
          <div id="ogcTableModal" style="display:none">
            <h2 id="ogcTableTitle"></h2><div id="ogcTableMeta"></div>
            <div id="ogcTableGrid" style="height:300px"></div>
            <span id="ogcTableStatus"></span>
            <button data-table-act="cancel">Cancel</button>
            <button data-table-act="apply">Apply changes</button>
          </div>`);
        const { OGTableEditor } = await import(
            new URL('App/Controller/OGTableEditor.js', location.href).href
        );
        OGTableEditor.initEvents();
        OGTableEditor.open({
            name: 'sample', title: 'Sample', value: [0.027, 0.4],
            reference: [0.027, 0.4], min: 0, max: 1,
            onApply: value => { window.__tableApplied = value; }
        });
    }""")
    cells = page.locator(
        '#ogcTableGrid .tabulator-cell[tabulator-field="value_0"]'
    )
    cells.nth(0).click()
    page.keyboard.press('ControlOrMeta+C')
    cells.nth(1).click()
    page.keyboard.press('ControlOrMeta+V')
    expect(cells.nth(1)).to_have_text('0.027')
    page.get_by_role('button', name='Apply changes').click()
    result = page.evaluate("""() => ({
        value: window.__tableApplied[1],
        type: typeof window.__tableApplied[1]
    })""")
    assert result == {'value': 0.027, 'type': 'number'}


def test_table_editor_keeps_open_when_a_value_is_blank(page, base_url):
    page.goto(base_url)
    page.evaluate("""async () => {
        document.body.insertAdjacentHTML('beforeend', `
          <div id="ogcTableModal" style="display:none">
            <h2 id="ogcTableTitle"></h2><div id="ogcTableMeta"></div>
            <div id="ogcTableGrid" style="height:300px"></div>
            <span id="ogcTableStatus"></span>
            <button data-table-act="cancel">Cancel</button>
            <button data-table-act="apply">Apply changes</button>
          </div>`);
        const { OGTableEditor } = await import(
            new URL('App/Controller/OGTableEditor.js', location.href).href
        );
        window.__blankTableEditor = OGTableEditor;
        OGTableEditor.initEvents();
        OGTableEditor.open({
            name: 'sample', title: 'Sample', value: [0.1, 0.2],
            reference: [0.1, 0.2], min: 0, max: 1,
            onApply: value => { window.__blankTableApplied = value; }
        });
    }""")
    expect(page.locator('#ogcTableGrid .tabulator-row')).to_have_count(2)
    page.evaluate("""async () => {
        await window.__blankTableEditor.table.getRow(1).update({value_0: null});
    }""")
    page.get_by_role('button', name='Apply changes').click()
    expect(page.locator('#ogcTableModal')).to_be_visible()
    expect(page.locator('#ogcTableStatus')).to_contain_text('1 invalid value')
    assert page.evaluate('() => window.__blankTableApplied') is None

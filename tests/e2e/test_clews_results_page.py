"""CLEWs Results against the real controller, field panel, Tabulator and ECharts.

Only data access is replaced; fixture results never modify a stored model or
start a solver. The synthetic cases deliberately share the same result schema.
"""
import csv
import json
from pathlib import Path

import pytest

from .test_shell_smoke import base_url  # noqa: F401

pytest.importorskip("pytest_playwright")
from playwright.sync_api import expect

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "frontend/fixtures/clews_results.json").read_text())

SEED = r"""async fixture => {
    const {Base} = await import('/Classes/Base.Class.js');
    const {Osemosys} = await import('/Classes/Osemosys.Class.js');
    const {Message} = await import('/Classes/Message.Class.js');
    const {default: Pivot} = await import('/AppResults/Controller/Pivot.js');
    window.Pivot = Pivot;
    window.fake = {session: 'A', requests: [], views: {}};
    const copy = value => JSON.parse(JSON.stringify(value));
    Base.getSession = async () => ({session: fake.session});
    Base.setSession = async casename => {fake.session = casename; return {};};
    Osemosys.getData = async () => copy(fixture.genData);
    Osemosys.getParamFile = async file => file === 'Variables.json' ? copy(fixture.variables) : {};
    Osemosys.getResultData = async (casename, file) => {
        fake.requests.push({casename, file});
        if (file === 'resData.json') return {};
        if (file === 'viewDefinitions.json') return {'osy-views': copy(fake.views)};
        if (!(file in fixture.results)) throw new Error('Unexpected file: ' + file);
        return copy(fixture.results[file]);
    };
    Message.smallBoxConfirmation = () => {};
    const init = Pivot.initPage;
    Pivot.initPage = function (model) {window.resultsModel = model; return init.call(this, model);};
    Pivot.lastSnapshot = null;
    const html = await fetch('/AppResults/View/Pivot.html').then(r => r.text());
    document.querySelectorAll('#casePicker').forEach(element => element.remove());
    document.querySelector('.osy-content').innerHTML =
        '<div id="casePicker"><button class="selectCS" data-ps="A">Case A</button>' +
        '<button class="selectCS" data-ps="B">Case B</button></div>' + html;
    history.replaceState(null, '', '#/Pivot');
    Pivot.onLoad();
}"""


def open_results(page, base_url):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base_url, wait_until="networkidle")
    page.locator("#osy-mb-clews").click()
    expect(page.locator("body.osy-mode-clews")).to_have_count(1)
    page.wait_for_load_state("networkidle")
    page.evaluate(SEED, FIXTURE)
    page.wait_for_selector("#pivotGrid .tabulator-row")
    page.wait_for_selector("#pivotChart svg")
    return errors


def wait_grid(page):
    page.evaluate("async () => {await Pivot.activeApp.resultGrid.pending;}")


def field_settings(page, field):
    page.locator(f'.result-panel-chip[data-field="{field}"]').click(button="right")
    page.locator('.result-panel-menu-command[data-action="settings"]').click()
    expect(page.locator(".result-field-settings")).to_be_visible()


def percentage_totals(page):
    field_settings(page, "Value")
    page.locator(".result-field-show-as").select_option("percentGrand")
    page.locator(".result-field-apply").click()
    page.check("#showRowTotals")
    page.check("#showColumnTotals")
    wait_grid(page)


def test_percentage_totals_render_correctly_and_chart_excludes_total_series(page, base_url):
    errors = open_results(page, base_url)
    percentage_totals(page)
    total = page.locator('.result-grid-grand-total .tabulator-cell[tabulator-field="value_2"]')
    expect(total).to_have_text("100.00%")
    assert page.evaluate("Pivot.chart.getOption().series.length") == 2
    assert page.evaluate("Pivot.chart.getOption().series.map(s => s.data)") == [[0.1, 0.3], [0.2, 0.4]]
    assert not errors


def test_condition_filter_is_cleared_when_selecting_another_variable(page, base_url):
    errors = open_results(page, base_url)
    field_settings(page, "Tech")
    page.locator(".result-field-edit").click()
    page.locator('[data-mode="condition"]').click()
    page.locator('.result-field-condition-operator[data-index="0"]').select_option("beginsWith")
    page.locator('.result-field-condition-value[data-index="0"]').fill("SOL")
    page.locator(".result-field-apply").click()
    wait_grid(page)
    assert page.evaluate("Pivot.activeApp.aggregateResult.columnKeys") == [["SOLAR"]]
    page.select_option("#cmbParams", "NC")
    page.wait_for_function("resultsModel.param === 'NC' && !Pivot.activeApp.updatingParam")
    wait_grid(page)
    assert page.evaluate("Pivot.activeApp.aggregateResult.columnKeys") == [["SOLAR"], ["WIND"]]
    assert page.evaluate("resultsModel.DEFAULTVIEW.conditionFilters") == {}
    assert page.evaluate("Pivot.activeApp.state.configuration().filters") == []
    assert not errors


def test_case_picker_restores_a_remembered_variable_from_its_own_group(page, base_url):
    errors = open_results(page, base_url)
    page.select_option("#cmbParams", "OV")
    page.wait_for_function("resultsModel.param === 'OV' && !Pivot.activeApp.updatingParam")
    page.evaluate("Pivot.saveSnapshot(resultsModel)")
    page.locator('#casePicker [data-ps="B"]').click()
    page.wait_for_function("resultsModel.casename === 'B' && resultsModel.param === 'ANC'")
    wait_grid(page)
    page.locator('#casePicker [data-ps="A"]').click()
    page.wait_for_function("resultsModel.casename === 'A' && resultsModel.param === 'OV'")
    wait_grid(page)
    assert page.evaluate("resultsModel.group") == "R"
    assert page.evaluate("resultsModel.pivotData[0].Value") == 40
    assert page.evaluate("fake.requests.filter(r => r.file === 'R.json').length") == 2
    expect(page.locator('#pivotGrid .tabulator-cell[tabulator-field="value_0"]')).to_have_text("40.00")
    assert not errors


def test_case_picker_restores_the_remembered_saved_view(page, base_url):
    errors = open_results(page, base_url)
    page.select_option("#cmbParams", "OV")
    page.wait_for_function("resultsModel.param === 'OV' && !Pivot.activeApp.updatingParam")
    page.evaluate("""() => {
        const view = {'osy-viewId': 'saved-ov', 'osy-viewname': 'Remembered objective',
            'osy-varId': 'OV', 'osy-viewdef': Pivot.activeApp.state.definition()};
        fake.views = {OV: [view]};
        resultsModel.VIEWS.push(view);
        Pivot.fillSelect('#cmbViews', resultsModel.VIEWS, 'osy-viewId', 'osy-viewname', 'saved-ov');
        $('#cmbViews').trigger('change');
        Pivot.saveSnapshot(resultsModel);
    }""")
    page.locator('#casePicker [data-ps="B"]').click()
    page.wait_for_function("resultsModel.casename === 'B' && resultsModel.param === 'ANC'")
    wait_grid(page)
    page.locator('#casePicker [data-ps="A"]').click()
    page.wait_for_function("resultsModel.casename === 'A' && resultsModel.VIEW === 'saved-ov'")
    wait_grid(page)
    expect(page.locator("#cmbViews")).to_have_value("saved-ov")
    assert page.evaluate("resultsModel.pivotData[0].Value") == 40
    assert not errors


def test_percentage_csv_exports_transformed_totals(page, base_url, tmp_path):
    errors = open_results(page, base_url)
    percentage_totals(page)
    with page.expect_download() as pending:
        page.click("#csvExport")
    path = tmp_path / "results.csv"
    pending.value.save_as(path)
    rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))
    total = next(row for row in rows if row[0] == "Grand Total")
    assert [float(value) for value in total[2:]] == [0.4, 0.6, 1.0]
    assert not errors


def test_detail_view_still_returns_original_records_for_percentage_totals(page, base_url):
    errors = open_results(page, base_url)
    percentage_totals(page)
    page.locator('.result-grid-grand-total .tabulator-cell[tabulator-field="value_2"]').dblclick()
    page.wait_for_selector(".result-grid-detail-dialog .tabulator-row")
    expect(page.locator(".result-grid-detail-summary")).to_contain_text("4 items")
    values = page.locator('.result-grid-detail-table .tabulator-cell[tabulator-field="Value"]').all_text_contents()
    assert sorted(float(value) for value in values) == [10, 20, 30, 40]
    assert not errors


def test_hide_table_and_chart_svg_export_work_with_totals(page, base_url, tmp_path):
    errors = open_results(page, base_url)
    percentage_totals(page)
    page.check("#hideTable")
    expect(page.locator("#pivotGrid")).to_be_hidden()
    page.uncheck("#hideTable")
    expect(page.locator("#pivotGrid")).to_be_visible()
    with page.expect_download() as pending:
        page.click("#svgExport")
    path = tmp_path / "chart.svg"
    pending.value.save_as(path)
    svg = path.read_text()
    assert "<svg" in svg and "SOLAR" in svg and "WIND" in svg
    assert not errors


def test_res_multiselect_search_preserves_selection_and_destroy_cleans_up(page, base_url):
    errors = open_results(page, base_url)
    page.evaluate("""async () => {
        const {MultiSelect} = await import('/Classes/MultiSelect.Class.js');
        const host = document.createElement('div');
        host.id = 'test-res-technologies';
        host.className = 'pull-right';
        document.querySelector('.osy-content').prepend(host);
        window.selected = [];
        window.selector = new MultiSelect(host, {
            displayMemberPath: 'Tech', headerFormat: '{count} Technology',
            itemsSource: [{Tech: 'SOLAR', $checked: true}, {Tech: 'WIND'}, {Tech: 'HYDRO', $checked: true}],
            checkedItemsChanged: sender => {window.selected = sender.checkedItems.map(item => item.Tech);}
        });
    }""")
    expect(page.locator(".muio-multiselect-toggle")).to_have_text("2 Technology")
    page.locator(".muio-multiselect-toggle").click()
    page.locator(".muio-multiselect-search").fill("WIND")
    page.locator(".muio-multiselect-item input").check()
    assert page.evaluate("window.selected") == ["SOLAR", "WIND", "HYDRO"]
    page.locator(".muio-multiselect-search").fill("SOL")
    expect(page.locator(".muio-multiselect-item input")).to_be_checked()
    expect(page.locator(".muio-multiselect-toggle")).to_have_text("3 Technology")
    page.locator(".muio-multiselect-search").fill("")
    page.locator(".muio-multiselect-all input").uncheck()
    assert page.evaluate("window.selected") == []
    page.evaluate("selector.destroy()")
    expect(page.locator("#test-res-technologies")).to_be_empty()
    assert not errors

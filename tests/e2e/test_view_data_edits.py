"""Real grid events must save exactly one source cell and survive a page reload."""

import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import pytest

pytest.importorskip("pytest_playwright")

from tests.view_data_fixtures import CASE_NAME, make_view_data_case

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def edit_server(tmp_path_factory):
    """Serve the production app with disposable source tables, never live cases."""
    case = make_view_data_case(tmp_path_factory.mktemp("view-edits") / "DataStorage")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, PYTHONPATH=str(ROOT / "API"),
               MUIOGO_OG_DATA_DIR=str(case.parent.parent / "og-state"),
               MUIOGO_CLEWS_DATA_DIR=str(case.parent.parent / "clews-state"),
               MUIOGO_CLEWS_CATALOG_URL="")
    server = """
import sys
from pathlib import Path
from Classes.Base import Config
Config.DATA_STORAGE = Path(sys.argv[1])
from app import app
from flask import send_from_directory
from waitress import serve
@app.route('/DataStorage/<path:filename>')
def test_storage(filename):
    return send_from_directory(Config.DATA_STORAGE, filename)
serve(app, host='127.0.0.1', port=int(sys.argv[2]))
"""
    url = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as log:
        proc = subprocess.Popen([sys.executable, "-c", server, str(case.parent), str(port)],
                                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and proc.poll() is None:
                try:
                    with urllib.request.urlopen(url, timeout=1) as response:
                        if response.status == 200:
                            break
                except (urllib.error.URLError, ConnectionResetError, TimeoutError):
                    time.sleep(0.1)
            else:
                log.seek(0)
                pytest.fail(f"Edit test server did not start: {log.read()[-3000:]}")
            yield url, case
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)


def open_editor(page, url):
    page.goto(url)
    assert page.request.post(f"{url}/setSession", data={"case": CASE_NAME}).ok
    # Capture the model without changing any API, adapter, grid or event handler.
    page.evaluate("""async () => {
        const {default: ViewData} = await import('/App/Controller/ViewData.js');
        const init = ViewData.initPage;
        ViewData.initPage = function(model) {
            window.editModel = model;
            return init.call(this, model);
        };
    }""")
    page.evaluate("location.hash = '/ViewData'")
    page.wait_for_function("window.editModel && $('#osy-gridViewData').jqxGrid('getboundrows')?.length > 0")


def rows(page, kind, entity, scalar):
    return page.evaluate("""({kind, entity, scalar}) =>
        (scalar ? window.editModel.gridRTData : window.editModel.gridData)[kind][entity]
    """, {"kind": kind, "entity": entity, "scalar": scalar})


@pytest.mark.parametrize("kind,entity,group,param,scenario,selectors,value", [
    ("Tech", "T1", "RYTM", "VC", "SC_0", {"MoId": "2"}, 0),
    ("Tech", "T1", "RYTCn", "CAM", "SC_0", {"ConId": "CN2"}, 7.5),
    ("Comm", "C1", "RYC", "SAD", "SC_0", {}, 12.5),
    ("Emi", "E1", "RYE", "EP", "SC_0", {}, 15.5),
    ("Tech", "T1", "RT", "OL", "SC_0", {}, 25),
    ("Emi", "E1", "RE", "MPEL", "SC_0", {}, 0),
])
def test_grid_edit_saves_one_cell_and_reloads(page, edit_server, kind, entity, group, param, scenario, selectors, value):
    url, case = edit_server
    scalar = group in ("RT", "RE")
    grid = "#osy-gridRT" if scalar else "#osy-gridViewData"
    column = "value" if scalar else "2030"
    selected = {"groupId": group, "param": param, "ScId": scenario, **selectors}
    open_editor(page, url)
    if kind != "Tech":
        page.locator(f'input[name="bytype"][value="{kind}"]').locator("..").click()
    page.wait_for_function("""({grid, selected}) => $(grid).jqxGrid('getboundrows').some(row =>
        Object.entries(selected).every(([key, value]) => String(row[key]) === value))
    """, arg={"grid": grid, "selected": selected})
    before = rows(page, kind, entity, scalar)
    expected = copy.deepcopy(before)
    matches = [row for row in expected if all(str(row[key]) == val for key, val in selected.items())]
    assert len(matches) == 1
    matches[0][column] = value

    sources = {p.name: p.read_bytes() for p in case.glob("*.json")}
    source = json.loads(sources[f"{group}.json"])
    source_rows = source[param][scenario]
    if scalar:
        source_rows[0][entity] = value
    else:
        identity = {"Tech": "TechId", "Comm": "CommId", "Emi": "EmisId"}[kind]
        targets = [row for row in source_rows if row[identity] == entity and
                   all(str(row[key]) == val for key, val in selectors.items())]
        assert len(targets) == 1
        targets[0]["2030"] = value

    endpoint = "/updateTEViewData" if scalar else "/updateViewData"
    with page.expect_response(lambda response: response.url.endswith(endpoint)) as saved:
        page.evaluate("""({grid, selected, column, value}) => {
            const index = $(grid).jqxGrid('getboundrows').findIndex(row =>
                Object.entries(selected).every(([key, value]) => String(row[key]) === value));
            $(grid).jqxGrid('setcellvalue', index, column, value);
        }""", {"grid": grid, "selected": selected, "column": column, "value": value})
    assert saved.value.status == 200, saved.value.text()
    assert json.loads((case / f"{group}.json").read_text()) == source
    assert {p.name: p.read_bytes() for p in case.glob("*.json") if p.stem != group} == {
        name: data for name, data in sources.items() if name != f"{group}.json"}
    assert rows(page, kind, entity, scalar) == expected

    # Re-fetch through the real API and rebuild the grid, checking persisted data.
    page.reload()
    page.wait_for_function("$('#osy-gridViewData').length && $('#osy-gridViewData').jqxGrid('getboundrows')?.length > 0")
    if kind != "Tech":
        page.locator(f'input[name="bytype"][value="{kind}"]').locator("..").click()
    actual = page.evaluate("""({grid, selected, column}) => $(grid).jqxGrid('getboundrows').find(row =>
        Object.entries(selected).every(([key, value]) => String(row[key]) === value))[column]
    """, {"grid": grid, "selected": selected, "column": column})
    assert actual == value

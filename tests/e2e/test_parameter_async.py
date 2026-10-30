"""Delayed parameter responses must preserve page ownership and newer edits."""
import mimetypes
from pathlib import Path
from urllib.parse import urlsplit

import pytest

pytest.importorskip("pytest_playwright")

WEBAPP = Path(__file__).resolve().parents[2] / "WebAPP"


@pytest.fixture
def parameters(page):
    def serve(route):
        path = WEBAPP / urlsplit(route.request.url).path.lstrip("/")
        if path.suffix == ".html":
            route.fulfill(body='<base href="/">' + path.read_text(), content_type="text/html")
            return
        route.fulfill(path=path, content_type=mimetypes.guess_type(path)[0] or "application/octet-stream")
    page.route("http://parameters.test/**", serve)
    page.goto("http://parameters.test/App/View/OGParameters.html")
    page.add_script_tag(url="http://parameters.test/References/jquery/jquery-3.4.1.min.js")
    page.evaluate("""async () => {
        const {default: Parameters} = await import('/App/Controller/OGParameters.js');
        const {Model} = await import('/App/Model/OGParameters.Model.js');
        const {Ogc} = await import('/Classes/Ogc.Class.js');
        const {Message} = await import('/Classes/Message.Class.js');
        const {NavigationGuard} = await import('/Classes/NavigationGuard.Class.js');
        const {OGTableEditor} = await import('/App/Controller/OGTableEditor.js');
        Object.assign(window, {Parameters, Model, Ogc, Message, NavigationGuard, OGTableEditor});
        Message.smallBoxInfo = Message.warning = Message.danger = () => {};
        localStorage.setItem('osy-pageId', 'OGParameters');
        Parameters.model = new Model({frisch: {shape:'scalar', default:1.5},
            e: {default:null, large:true, dimensions:[80,7], preview:[[1,2,3]]}
        }, {}, {country_id:'ETH', casename:'policy', run_name:'baseline'});
        Parameters.render(Parameters.model, 0);
        Parameters.initEvents();
    }""")
    return page


def test_save_keeps_newer_edits_guarded_and_serializes_requests(parameters):
    result = parameters.evaluate("""async () => {
        let resolve, requests = 0, prompts = 0, allowed = 0;
        Ogc.saveParams = () => {requests++; return new Promise(done => resolve = done)};
        Message.confirmUnsavedModelChanges = async () => {prompts++; return 'Cancel'};
        Parameters.model.cur.frisch = 1.6;
        const pending = Parameters.save();
        Parameters.save();
        Parameters.model.cur.frisch = 1.7;
        resolve({status_code:'success'});
        await pending;
        await NavigationGuard.requestLeave(() => allowed++);
        const afterFirst = {requests, prompts, allowed, saved:Parameters.model.params.frisch};
        Ogc.saveParams = async () => ({status_code:'success'});
        await Parameters.save();
        await NavigationGuard.requestLeave(() => {allowed++});
        return {afterFirst, allowed, prompts, saved:Parameters.model.params.frisch};
    }""")
    assert result == {
        "afterFirst": {"requests": 1, "prompts": 1, "allowed": 0, "saved": 1.6},
        "allowed": 1, "prompts": 1, "saved": 1.7,
    }


def test_delayed_table_default_cannot_reopen_after_navigation(parameters):
    result = parameters.evaluate("""async () => {
        let resolve, opened = 0;
        Ogc.getParameterDefault = () => new Promise(done => resolve = done);
        OGTableEditor.open = () => opened++;
        Parameters.openTable('e');
        localStorage.setItem('osy-pageId', 'OGCases');
        resolve({value:[[1,2,3]]});
        for (let i = 0; i < 10; i++) await Promise.resolve();
        return {opened, value:Parameters.model.cur.e, modal:document.body.classList.contains('ogc-table-open')};
    }""")
    assert result == {"opened": 0, "value": None, "modal": False}

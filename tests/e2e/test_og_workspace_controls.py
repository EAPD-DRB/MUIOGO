"""Render workspace controls with local assets and no API requests."""

import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import pytest

pytest.importorskip("pytest_playwright")
from playwright.sync_api import expect

WEBAPP = Path(__file__).resolve().parents[2] / "WebAPP"


def test_parameter_controls(page):
    def serve(route):
        path = WEBAPP / urlparse(route.request.url).path.lstrip("/")
        if path.suffix == ".html":
            route.fulfill(body='<base href="/">' + path.read_text(), content_type="text/html")
            return
        route.fulfill(
            path=path,
            content_type=mimetypes.guess_type(path)[0] or "application/octet-stream",
        )

    page.route("http://og-ui.test/**", serve)
    page.goto("http://og-ui.test/App/View/OGParameters.html")
    page.add_script_tag(url="http://og-ui.test/References/jquery/jquery-3.4.1.min.js")
    page.add_style_tag(url="http://og-ui.test/References/smartadmin/css/muiogo.css")
    page.evaluate("""async () => {
        const {default: Parameters} = await import('/App/Controller/OGParameters.js');
        const {Model} = await import('/App/Model/OGParameters.Model.js');
        localStorage.setItem('osy-ogc-country', JSON.stringify({country_id: 'ETH', country_name: 'Ethiopia'}));
        localStorage.setItem('osy-pageId', 'OGParameters');
        const model = new Model({
            start_year: {shape: 'scalar', default: 2025, title: 'Start year'},
            frisch: {shape: 'scalar', default: 1.5, title: 'Frisch elasticity'}
        }, {}, {country_id: 'ETH', casename: 'Example', run_name: 'baseline'});
        Parameters.model = model;
        Parameters.render(model, 0);
    }""")
    expect(page.locator("#ogcParamsCountryName")).to_have_text("Ethiopia")
    expect(page.locator("#ogcParamsCountryFlag img")).to_have_attribute("src", "References/flags/4x3/et.svg")
    expect(page.locator("a[href='#/OGCases'], a[href='#/OGCore']")).to_have_count(0)
    expect(page.locator("[data-act='reset-all']")).to_have_class("btn ogc-btn ogc-btn-main")
    expect(page.locator("[data-group='frequent']")).to_have_attribute("open", "")
    expect(page.locator("[data-param='frisch']")).not_to_be_visible()
    page.locator("[data-group='households'] summary").click()
    expect(page.locator("[data-param='frisch']")).to_be_visible()
    expect(page.locator("[data-param='start_year']")).to_have_count(1)

    page.goto("http://og-ui.test/App/View/OGCases.html")
    expect(page.get_by_role("link", name="Exit workspace")).to_have_count(0)
    expect(page.get_by_role("group", name="Cases view")).to_be_visible()
    expect(page.get_by_role("button", name="Grouped", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Separate", exact=True)).to_be_visible()

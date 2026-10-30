"""Route failures expose recovery without stale callbacks replacing a newer page."""

import pytest

pytest.importorskip("pytest_playwright")
from playwright.sync_api import expect
from tests.e2e.test_shell_smoke import base_url


@pytest.mark.parametrize("failure_kind,failed_resource", [
    ("view", "App/View/Versions.html"),
    ("module", "App/Controller/Config.js"),
    ("callback", "App/Controller/Config.js"),
])
def test_route_failure_can_retry(page, base_url, failure_kind, failed_resource):
    failed = False

    def resource(route):
        nonlocal failed
        if not failed:
            failed = True
            if failure_kind == "callback":
                route.fulfill(body="export default { onLoad() { return Promise.reject(new Error('failed')); } };", content_type="text/javascript")
            else:
                route.abort()
        elif failed_resource.endswith(".js"):
            route.fulfill(body="export default { onLoad() {} };", content_type="text/javascript")
        else:
            route.fulfill(body='<div id="retried-view">Loaded after retry</div>', content_type="text/html")

    page.route("**/" + failed_resource, resource)
    page.goto(base_url + ("/#/Config" if failed_resource.endswith(".js") else "/#/Versions"))
    expect(page.get_by_role("button", name="Retry", exact=True)).to_be_visible()
    expect(page.locator(".ajax-loading-animation")).to_have_count(0)
    page.get_by_role("button", name="Retry", exact=True).click()
    expect(page.get_by_role("button", name="Retry", exact=True)).to_have_count(0)
    if failed_resource.endswith(".html"):
        expect(page.locator("#retried-view")).to_be_visible()
    else:
        expect(page.locator("body.osy-mode-clews")).to_have_count(1)
        expect(page.locator(".ajax-loading-animation")).to_have_count(0)


def test_late_view_failure_does_not_replace_new_route(page, base_url):
    page.goto(base_url)
    page.evaluate("""() => {
        const get = $.get;
        $.get = function(path) {
            if (path === 'App/View/Versions.html') {
                return new Promise((resolve, reject) => { window.rejectOldView = reject; });
            }
            return get.apply(this, arguments);
        };
        location.hash = '#/Versions';
    }""")
    page.wait_for_function("typeof window.rejectOldView === 'function'")
    page.evaluate("location.hash = '#/'")
    expect(page.locator(".osy-pickwrap")).to_be_visible()
    page.evaluate("window.rejectOldView(new Error('late failure'))")
    expect(page.locator(".osy-pickwrap")).to_be_visible()
    expect(page.get_by_role("button", name="Retry", exact=True)).to_have_count(0)


def test_parameters_sidebar_without_selected_run(page, base_url):
    page.add_init_script("""
        localStorage.setItem('osy-model', 'og');
        localStorage.setItem('osy-ogc-country', JSON.stringify({country_id: 'ETH', country_name: 'Ethiopia'}));
        localStorage.removeItem('osy-ogc-selection');
    """)
    page.goto(base_url + "/#/OGParameters")
    expect(page.locator("#Navi a[href='#/OGParameters']")).to_be_visible()
    expect(page.locator("#Navi li.active a[href='#/OGParameters']")).to_have_count(1)
    expect(page.locator("#ogcParamsEmptyTitle")).to_have_text("No run selected")
    expect(page.locator("#Navi a[href='#/OGCases']")).to_be_visible()

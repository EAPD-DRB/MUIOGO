"""
Browser check for the CLEWs install page (#540): the route sets the shell mode,
the Home page links to it, a country block renders from a repository's menu
with installed models grouped by version, and adding a local repository without
a manifest goes through the real discovery on the backend.

Runs only when pytest-playwright is installed (the dedicated CI job); the plain
pytest job skips this module.
"""

import pytest

pytest.importorskip("pytest_playwright")
from playwright.sync_api import expect

from .test_shell_smoke import base_url  # noqa: F401  (session fixture: real server)

expect.set_options(timeout=15_000)


def test_route_sets_clews_mode_and_shows_page(page, base_url):
    page.goto(f"{base_url}/#/ClewsInstall")
    expect(page.locator("body.osy-mode-clews")).to_have_count(1)
    expect(page.locator(".clw-page")).to_be_visible()
    expect(page.locator(".clw-addblock")).to_be_visible()
    expect(page.locator("#clwSource")).to_be_visible()


def test_home_links_to_the_page(page, base_url):
    page.goto(base_url)
    page.locator("#osy-mb-clews").click()
    expect(page.locator('a[href="#ClewsInstall"]')).to_be_visible()


def test_country_block_shows_url_newest_and_installed_by_version(page, base_url):
    page.goto(f"{base_url}/#/ClewsInstall")
    expect(page.locator(".clw-page")).to_be_visible()
    page.evaluate("""async () => {
        const { default: ClewsInstall } = await import(new URL('App/Controller/ClewsInstall.js', location.href).href);
        const menu = {
            name: 'Philippines', iso3: 'PHL', discovered: true, ordering: 'date',
            source: { type: 'repo_url', repo_url: 'https://github.com/EAPD-DRB/CLEWs-PHL' },
            vintages: [
                { id: 'vIS2', last_changed: '2026-09-01T00:00:00Z', cases: [{ case: 'Philippines_vIS2', recommended: true }] },
                { id: 'v18', last_changed: '2026-07-01T00:00:00Z', cases: [{ case: 'Philippines_v18', recommended: true }] },
                { id: 'v12', last_changed: '2026-01-01T00:00:00Z', cases: [
                    { case: 'Philippines_v12', role: 'source', recommended: true },
                    { case: 'Philippines_v12_ENV_LAND', role: 'env-land' }] },
            ],
        };
        // what the machine holds: two v18 variants, one v12 layer, a stranger
        const installed = ['Philippines_v18', 'Philippines_v18_GOLD', 'Philippines_v12_ENV_LAND', 'CLEWs Demo']
            .map(n => ({ casename: n, source_type: 'unmanaged' }));
        ClewsInstall.renderOne(menu, installed);
    }""")
    block = page.locator('.clw-country[data-key="test"]')
    expect(block.locator(".clw-url")).to_have_text("github.com/EAPD-DRB/CLEWs-PHL")
    expect(block.locator(".clw-badge").first).to_have_text("newer version available")
    expect(block.locator(".clw-latest-text")).to_contain_text("vIS2")
    expect(block.locator(".clw-latest-text")).to_contain_text("Philippines_vIS2")
    expect(block.locator('[data-act="install-latest"]')).to_be_enabled()
    # installed on this machine: under the repository, grouped by version, newest
    # first -- v18 has two rows (the version named once), v12 one; every row has
    # a labelled Delete; the stranger lands under other models at the end
    installed = page.locator("#clwInstalled")
    titles = installed.locator(".clw-have-title")
    expect(titles).to_have_count(2)
    expect(titles.nth(0)).to_contain_text("github.com/EAPD-DRB/CLEWs-PHL")
    expect(titles.nth(1)).to_contain_text("Other models")
    rows = installed.locator("tr[data-case]")
    expect(rows).to_have_count(4)
    expect(rows.nth(0).locator(".clw-vid")).to_have_text("v18")
    expect(rows.nth(0)).to_contain_text("Philippines_v18")
    expect(rows.nth(1).locator(".clw-vid")).to_have_count(0)
    expect(rows.nth(1)).to_contain_text("Philippines_v18_GOLD")
    expect(rows.nth(2).locator(".clw-vid")).to_have_text("v12")
    expect(rows.nth(2)).to_contain_text("Philippines_v12_ENV_LAND")
    expect(rows.nth(3)).to_contain_text("CLEWs Demo")
    expect(installed.locator('[data-act="delete"]')).to_have_count(4)
    expect(installed.locator('[data-act="delete"]').first).to_have_text("Delete")
    # the page order: repositories, then add a repository, then installed
    expect(page.locator(".clw-addblock")).to_be_visible()
    order = page.evaluate("""() => {
        const ids = ['clwCountries', 'clwAdded', 'clwInstalledBlock'].map(id => document.getElementById(id).getBoundingClientRect().top);
        return ids[0] < ids[1] && ids[1] < ids[2];
    }""")
    assert order
    # all versions is closed until asked, then lists every case newest first
    expect(block.locator(".clw-all")).to_be_hidden()
    block.locator('[data-act="toggle-all"]').click()
    rows = block.locator(".clw-all tr[data-case]")
    expect(rows).to_have_count(4)
    expect(rows.nth(0)).to_contain_text("vIS2")
    expect(rows.nth(0).locator(".clw-badge")).to_have_text("newest")
    expect(rows.nth(1).locator(".clw-status")).to_have_text("installed here")
    expect(rows.nth(1).locator("button")).to_be_disabled()


def test_adding_a_local_repository_without_manifest_is_discovered(page, base_url, tmp_path):
    for v in ("v1", "v2"):
        d = tmp_path / f"Testland_{v}_CLEWs_build" / "muio"
        d.mkdir(parents=True)
        (d / "SHA256SUMS").write_text("")
        (d / f"Testland_{v}_{v}.0.0_MUIO.zip").write_bytes(b"zip")

    page.goto(f"{base_url}/#/ClewsInstall")
    page.locator("#clwSource").fill(str(tmp_path))
    page.locator("#clwLookup").click()

    block = page.locator("#clwAdded .clw-country")
    expect(block).to_have_count(1)
    expect(block.locator(".clw-url")).to_contain_text(str(tmp_path))
    expect(block.locator(".clw-latest-text")).to_contain_text("Testland_v2")
    expect(block.locator(".clw-fine")).to_contain_text("read from the repository's contents")
    expect(block.locator('[data-act="install-latest"]')).to_be_enabled()
    block.locator('[data-act="toggle-all"]').click()
    expect(block.locator(".clw-all tr[data-case]")).to_have_count(2)


def test_folder_with_nothing_installable_reports_it(page, base_url, tmp_path):
    page.goto(f"{base_url}/#/ClewsInstall")
    page.locator("#clwSource").fill(str(tmp_path))
    page.locator("#clwLookup").click()
    expect(page.locator("#clwAdded .clw-err")).to_contain_text("No installable models")

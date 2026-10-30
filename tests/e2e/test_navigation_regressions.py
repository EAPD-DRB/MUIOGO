"""Navigation behavior against the real sidebar, styles, and SmartAdmin handlers."""

from pathlib import Path
from urllib.parse import urlsplit

import pytest

pytest.importorskip('pytest_playwright')
from playwright.sync_api import expect

WEBAPP = Path(__file__).resolve().parents[2] / 'WebAPP'


@pytest.fixture
def navigation(page):
    styles = ['bootstrap.min.css', 'font-awesome.min.css',
              'smartadmin-production-plugins.min.css', 'smartadmin-production.min.css',
              'smartadmin-skins.min.css', 'osy.css', 'muiogo.css']
    scripts = ['References/jquery/jquery-3.4.1.min.js',
               'References/smartadmin/js/app.config.js', 'References/smartadmin/js/app.min.js']
    html = ('<!doctype html><html><head>' + ''.join(
        f'<link rel="stylesheet" href="/References/smartadmin/css/{name}">' for name in styles
    ) + '</head><body class="fixed-header smart-style-4 minified osy-mode-clews">'
        '<header id="header"></header><aside id="left-panel">'
        + (WEBAPP / 'App/View/Sidebar.html').read_text() + '</aside><div id="main"></div>'
        + ''.join(f'<script src="/{name}"></script>' for name in scripts)
        + '''<script type="module">
        import {MuiogoShell} from '/Classes/MuiogoShell.Class.js';
        window.Shell = MuiogoShell;
        $('.dynamicRoutesLink,.dynamicRoutesRES,.dynamicResults').show();
        $('#dynamicRoutes').html('<li><a href="#/Parameters/Test">Test parameter</a></li>');
        MuiogoShell.initEvents();
        window.navigationReady = true;
        </script></body></html>''')

    def respond(route):
        path = urlsplit(route.request.url).path
        if path == '/':
            route.fulfill(body=html, content_type='text/html')
        else:
            asset = WEBAPP / path.lstrip('/')
            if asset.is_file():
                route.fulfill(path=str(asset))
            else:
                route.abort()

    page.route('http://navigation.test/**', respond)
    page.set_viewport_size({'width': 1280, 'height': 800})
    page.goto('http://navigation.test/')
    page.wait_for_function('window.navigationReady')
    return page


def assert_hit_target(page, selector):
    assert page.locator(selector).first.evaluate('''element => {
        const r = element.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && r.top >= 0 && r.bottom <= innerHeight
            && element.contains(document.elementFromPoint(r.x+r.width/2, r.y+r.height/2));
    }''')


@pytest.mark.parametrize('width', [980, 1280])
def test_collapsed_flyouts_and_toggle_are_accessible(navigation, width):
    page = navigation
    page.set_viewport_size({'width': width, 'height': 800})
    for parent, link in [('#Navi > li:has(#dynamicRoutes)', '#dynamicRoutes a'),
                         ('.dynamicRoutesRES', '.dynamicRoutesRES ul a')]:
        page.locator(parent).hover()
        assert_hit_target(page, link)
        page.locator(link).first.click()
        expect(page.locator(link).first.locator('..')).to_have_class('active')
    assert_hit_target(page, '.minifyme')
    page.locator('.minifyme').click()
    assert not page.locator('body').evaluate("e => e.classList.contains('minified')")
    assert_hit_target(page, '.minifyme')
    page.locator('.minifyme').click()
    assert page.locator('body').evaluate("e => e.classList.contains('minified')")


def test_expanded_navigation_scrolls_without_hiding_toggle(navigation):
    page = navigation
    page.locator('.minifyme').click()
    page.evaluate('''() => {
        const ul = document.querySelector('#dynamicRoutes');
        ul.innerHTML = Array.from({length: 60}, (_, i) => `<li><a href="#/Parameters/${i}">Parameter ${i}</a></li>`).join('');
        ul.style.display = 'block';
        ul.parentElement.classList.add('open');
    }''')
    assert_hit_target(page, '.minifyme')
    page.locator('#dynamicRoutes li:last-child a').scroll_into_view_if_needed()
    assert_hit_target(page, '#dynamicRoutes li:last-child a')
    assert_hit_target(page, '.minifyme')
    assert page.locator('#left-panel nav').evaluate('e => e.scrollTop > 0')


def test_nested_active_route_preserves_open_state_and_clears_old_markers(navigation):
    page = navigation
    result = page.evaluate('''() => {
        const ul = document.querySelector('#dynamicRoutes');
        ul.parentElement.classList.add('open');
        ul.style.display = 'block';
        history.replaceState(null, '', '#/Parameters/Test?mode=edit');
        Shell.syncSidebarActive();
        const selected = [...document.querySelectorAll('#Navi li.active > a')].map(a => a.getAttribute('href'));
        history.replaceState(null, '', '#/OGCases');
        document.body.classList.remove('osy-mode-clews');
        document.body.classList.add('osy-mode-og', 'osy-og-workspace');
        Shell.syncSidebarActive();
        return {selected, after: [...document.querySelectorAll('#Navi li.active > a')].map(a => a.getAttribute('href')),
            open: ul.parentElement.classList.contains('open'), display: ul.style.display};
    }''')
    assert result == {'selected': ['#', '#/Parameters/Test'], 'after': ['#/OGCases'],
                      'open': True, 'display': 'block'}
    expect(page.locator('#Navi li.active')).to_be_visible()


@pytest.mark.parametrize('width,extra_class', [(768, ''), (1280, 'menu-on-top')])
def test_responsive_sidebar_layout_retains_upstream_rules(navigation, width, extra_class):
    page = navigation
    page.set_viewport_size({'width': width, 'height': 800})
    result = page.evaluate('''extra => {
        document.body.classList.remove('minified');
        if (extra) document.body.classList.add(extra);
        const read = () => {
            const panel = getComputedStyle(document.querySelector('#left-panel'));
            const nav = getComputedStyle(document.querySelector('#left-panel nav'));
            return [panel.position, panel.display, panel.overflow, nav.overflow];
        };
        const before = read();
        document.querySelector('link[href$="muiogo.css"]').disabled = true;
        return {before, after: read()};
    }''', extra_class)
    assert result['before'] == result['after']

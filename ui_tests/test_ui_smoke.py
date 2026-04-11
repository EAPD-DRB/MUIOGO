"""
test_ui_smoke.py — Playwright smoke tests for the MUIOGO frontend.

Scope: verify that Flask serves the app and core UI elements are present.
These tests are intentionally minimal and environment-agnostic.

Design rules:
  - wait_until="commit" on every page.goto() — returns the moment Flask starts
    sending the response without waiting for CDN resources (MathJax etc.).
  - Element assertions use generous timeouts because index.html loads ~20
    synchronous <script> tags before #main and the footer are fully parsed.
  - No SPA route tests (/#AddCase, /#Home, /#Config) — those require jQuery
    $.load() to complete and are flaky in headless CI.
"""
import re

import requests
from playwright.sync_api import Page, expect


# ---------------------------------------------------------------------------
# Pure API tests (no browser required)
# ---------------------------------------------------------------------------

def test_health_endpoint(live_server: str):
    """Flask /health must return {"status": "ok"}."""
    r = requests.get(f"{live_server}/health", timeout=5)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_session_api(live_server: str):
    """Flask /getSession must return a JSON object with a 'session' key."""
    r = requests.get(f"{live_server}/getSession", timeout=5)
    assert r.status_code == 200
    assert "session" in r.json()


# ---------------------------------------------------------------------------
# Browser tests (Playwright)
# ---------------------------------------------------------------------------

def test_load_app(page: Page, live_server: str):
    """
    The root URL must serve index.html with the correct page title.

    wait_until='commit' returns the instant Flask starts sending bytes.
    to_have_title then polls until the <title> tag is parsed (fast, in <head>).
    """
    page.goto(live_server, wait_until="commit")
    expect(page).to_have_title(re.compile(r"MUIO\s*5\.5"), timeout=15000)


def test_static_footer(page: Page, live_server: str):
    """
    The footer copyright text must be present in the DOM.

    'MUIO ver.5.5' is hardcoded in index.html (line 143) — no JS needed.
    It sits after ~20 synchronous <script> tags so we allow 60 s for the
    browser to finish downloading and executing all blocking scripts.
    to_be_attached (not to_be_visible) because the footer may be off-screen.
    """
    page.goto(live_server, wait_until="commit")
    expect(
        page.get_by_text("MUIO ver.5.5", exact=False).first
    ).to_be_attached(timeout=60000)

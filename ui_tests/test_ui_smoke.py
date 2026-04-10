import re
import requests
from playwright.sync_api import Page, expect


def test_health_endpoint(live_server: str):
    """Verify the /health API endpoint returns 200 OK (pure API smoke test)."""
    response = requests.get(f"{live_server}/health", timeout=5)
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_load_app(page: Page, live_server: str):
    """
    Verify that the root page loads with the correct title and static scaffold.

    This checks what Flask actually server-renders via index.html — the page
    title, the fixed footer text, and the static structural containers.
    These are guaranteed to be present before any JS executes.
    """
    page.goto(live_server)

    # 1. Page title is set statically in index.html
    expect(page).to_have_title(re.compile(r"MUIO\s*5\.5"))

    # 2. Footer text is hardcoded in index.html — always present
    expect(page.get_by_text("MUIO ver.5.5", exact=False).first).to_be_visible(timeout=10000)

    # 3. The main content div exists in index.html (no JS needed)
    expect(page.locator("#main")).to_be_visible(timeout=10000)


def test_spa_navbar_hydrates(page: Page, live_server: str):
    """
    Verify that jQuery loads the Navbar.html partial into the header.

    The navbar brand text 'MUIO' is injected by:
      $('header').load('App/View/Navbar.html')
    We wait up to 15s for it to appear, which covers CI cold-start latency.
    """
    page.goto(live_server)

    # The navbar brand text is inside Navbar.html loaded by jQuery
    expect(page.locator("#header").get_by_text("MUIO", exact=False)).to_be_visible(
        timeout=15000
    )


def test_session_api(live_server: str):
    """Verify the /getSession endpoint returns a valid JSON response."""
    response = requests.get(f"{live_server}/getSession", timeout=5)
    assert response.status_code == 200
    data = response.json()
    # session key must be present (value can be None for a fresh session)
    assert "session" in data

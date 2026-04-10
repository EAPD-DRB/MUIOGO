import re
import requests
from playwright.sync_api import Page, expect


def test_load_app(page: Page, live_server: str):
    """Verify the app title and core navigation scaffold renders correctly."""
    page.goto(live_server)

    # Wait for full hydration — check a known branded text in the navbar
    expect(page.get_by_text("MUIO", exact=False).first).to_be_visible(timeout=15000)
    expect(page).to_have_title(re.compile(r"MUIO\s*5\.5"))


def test_add_case_ui_renders(page: Page, live_server: str):
    """
    Verify the Add Case form UI mounts correctly.

    Note: Full case creation requires complex jqx widget interaction (year range
    slider checkboxes) that doesn't translate to headless automation. This smoke
    test validates the form scaffold renders, which is the critical regression
    surface for this route.
    """
    page.goto(f"{live_server}/#AddCase")

    # The Model name input field must be visible — proves the AddCase view mounted
    expect(page.get_by_placeholder("Model name")).to_be_visible(timeout=10000)

    # The page title heading must reflect the route
    expect(page.get_by_text("Model configuration", exact=False).first).to_be_visible(timeout=10000)


def test_home_ui_renders(page: Page, live_server: str):
    """Verify the Home page MUIO models panel renders without errors."""
    page.goto(f"{live_server}/#Home")

    # The 'MUIO models' heading inside the jarviswidget must be present
    expect(page.get_by_text("MUIO models", exact=False).first).to_be_visible(timeout=10000)

    # The case search input must be visible — proves the widget scaffold loaded
    expect(page.get_by_placeholder("Search ...")).to_be_visible(timeout=10000)


def test_navigation_diagnostics(page: Page, live_server: str):
    """Verify the Config/Parameters view mounts with expected headings."""
    page.goto(f"{live_server}/#Config")

    # The h2 page title for the Config route contains "Parameters"
    expect(
        page.get_by_role("heading", name=re.compile("Parameters", re.IGNORECASE)).first
    ).to_be_visible(timeout=10000)


def test_health_endpoint(live_server: str):
    """Verify the /health API endpoint returns 200 OK (pure API smoke test)."""
    response = requests.get(f"{live_server}/health", timeout=5)
    assert response.status_code == 200
    assert response.json().get("status") == "ok"

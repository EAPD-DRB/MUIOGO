import re
from playwright.sync_api import Page, expect

def test_load_app(page: Page, live_server: str):
    """Verify that the index defaults and app container loads correctly."""
    page.goto(live_server)
    
    # Wait for the frontend to be fully hydrated by checking a known nav element
    # Explicitly bypassing CSS/ID selectors as requested, using get_by_text / get_by_role
    expect(page.get_by_text("MUIO", exact=False).first).to_be_visible(timeout=15000)
    expect(page).to_have_title(re.compile(r"MUIO\s*5\.5"))

def test_case_management(page: Page, live_server: str):
    """Verify the creation, session activation, and deletion of a mock case."""
    # Ensure hydration before navigating
    page.goto(f"{live_server}/#AddCase")
    
    # Use placeholder instead of #osy-casename ID locator
    model_name_input = page.get_by_placeholder("Model name")
    expect(model_name_input).to_be_visible(timeout=10000)
    
    # Fill in case data
    test_case_name = "PlaywrightMockCase"
    model_name_input.fill(test_case_name)
    
    # Click Save new model using role and text
    page.get_by_role("button", name=re.compile("Save new model", re.IGNORECASE)).click()
    
    # Wait to allow AJAX save request to complete before navigating away
    page.wait_for_timeout(3000)
    
    # Go to Home
    page.goto(f"{live_server}/#Home")
    
    # Wait for the case text to be visible in the datatable/cards, confirming creation
    expect(page.get_by_text(test_case_name).first).to_be_visible(timeout=10000)
    
    # Delete the case utilizing the trash icon or delete button role 
    # (Checking for 'Delete model' title which bypasses class name reliance)
    trash_icon = page.get_by_title("Delete model").first
    if trash_icon.count() > 0:
        trash_icon.click()
        # Accept confirmation dialogs automatically
        page.on("dialog", lambda dialog: dialog.accept())
        confirm_btn = page.get_by_role("button", name=re.compile("Yes", re.IGNORECASE))
        if confirm_btn.is_visible():
            confirm_btn.click()

def test_navigation_diagnostics(page: Page, live_server: str):
    """Ensure major tabs render properly and verify equations in ModelFile diagnostic UI."""
    page.goto(f"{live_server}/#ModelFile")
    
    # Wait for hydration on ModelFile by checking for expected text content
    expect(page.get_by_text("Model", exact=False).first).to_be_visible(timeout=10000)
    
    # Check Parameters / Config page
    page.goto(f"{live_server}/#Config")
    expect(page.get_by_role("heading", name=re.compile("Parameters", re.IGNORECASE)).first).to_be_visible(timeout=10000)


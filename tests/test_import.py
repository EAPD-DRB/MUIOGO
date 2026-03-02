"""Smoke tests — verify that the core application module can be imported.

Why this matters:
    If a dependency is missing, a syntax error was introduced, or a circular
    import exists, this test will fail immediately.  Running it in CI on every
    push/PR acts as a *fast* first gate before deeper integration or unit tests
    are added later.
"""

import importlib
import os

# ------------------------------------------------------------------
# Path constants
# ------------------------------------------------------------------
# The Flask app (API/app.py) uses *intra-package* imports such as
# ``from Classes.Base import Config`` which resolve only when ``API/``
# is on ``sys.path``.  We use monkeypatch.syspath_prepend so the
# change is isolated per test and automatically cleaned up.
# ------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.join(PROJECT_ROOT, "API")


def test_api_app_imports_successfully(monkeypatch):
    """The API.app module should be importable without raising exceptions."""
    monkeypatch.syspath_prepend(PROJECT_ROOT)
    monkeypatch.syspath_prepend(API_DIR)
    importlib.import_module("API.app")


def test_flask_app_object_exists(monkeypatch):
    """After import, the module must expose a Flask ``app`` object."""
    monkeypatch.syspath_prepend(PROJECT_ROOT)
    monkeypatch.syspath_prepend(API_DIR)
    mod = importlib.import_module("API.app")
    assert hasattr(mod, "app"), "API.app does not expose an 'app' attribute"

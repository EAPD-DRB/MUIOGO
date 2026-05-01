"""
Smoke tests -- does the app start at all?

These catch the obvious stuff early: missing deps, syntax errors, broken imports.
If these fail, nothing else will work either.
"""

from flask import Flask

import app as api_app


def test_app_is_flask_instance():
    """app.py needs to give us a Flask object, not something broken."""
    assert isinstance(api_app.app, Flask)


def test_case_blueprint_is_registered():
    """If CaseRoute isn't wired up, all case endpoints silently return 404."""
    assert "CaseRoute" in api_app.app.blueprints


def test_datafile_blueprint_is_registered():
    """If DataFileRoute isn't wired up, all run and datafile endpoints silently return 404."""
    assert "DataFileRoute" in api_app.app.blueprints


def test_app_has_secret_key(app):
    """Sessions break silently if there's no secret key set."""
    assert app.config.get("SECRET_KEY") not in (None, "")


def test_home_returns_200(client):
    """The home route should render without crashing."""
    resp = client.get("/")
    assert resp.status_code == 200

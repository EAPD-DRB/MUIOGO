"""
Smoke tests -- does the app start at all?

These catch the obvious stuff early: missing deps, syntax errors, broken imports.
If these fail, nothing else will work either.

Written as unittest.TestCase so both runners execute them: pytest (CI) collects
unittest classes natively, and the smoke scripts use `unittest discover`.
"""

import sys
import unittest
from pathlib import Path

# pytest puts API/ on the path via pyproject.toml pythonpath; the smoke scripts run
# this file under `unittest discover`, which does not read that config.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "API"))

from flask import Flask

import app as api_app


class AppSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Mirror tests/conftest.py: TESTING stays False so routes return real
        # HTTP responses instead of re-raising exceptions.
        api_app.app.config.update({"SECRET_KEY": "test-secret-key", "TESTING": False})

    def test_app_is_flask_instance(self):
        """app.py needs to give us a Flask object, not something broken."""
        self.assertIsInstance(api_app.app, Flask)

    def test_case_blueprint_is_registered(self):
        """If CaseRoute isn't wired up, all case endpoints silently return 404."""
        self.assertIn("CaseRoute", api_app.app.blueprints)

    def test_datafile_blueprint_is_registered(self):
        """If DataFileRoute isn't wired up, all run and datafile endpoints silently return 404."""
        self.assertIn("DataFileRoute", api_app.app.blueprints)

    def test_app_has_secret_key(self):
        """Sessions break silently if there's no secret key set."""
        self.assertNotIn(api_app.app.config.get("SECRET_KEY"), (None, ""))

    def test_home_returns_200(self):
        """The home route should render without crashing."""
        with api_app.app.test_client() as client:
            resp = client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_results_chart_runtime_is_vendored(self):
        root = Path(__file__).resolve().parents[1]
        controller = (root / "WebAPP" / "App" / "Controller" / "OGResults.js").read_text(
            encoding="utf-8"
        )
        references = root / "WebAPP" / "References" / "echarts"

        self.assertIn("References/echarts/echarts-6.1.0.min.js", controller)
        self.assertNotIn("cdn.jsdelivr.net/npm/echarts", controller)
        for name in (
            "echarts-6.1.0.min.js",
            "LICENSE",
            "NOTICE",
            "LICENSE-d3",
            "LICENSE-zrender",
        ):
            self.assertTrue((references / name).is_file(), name)

        with api_app.app.test_client() as client:
            response = client.get("/References/echarts/echarts-6.1.0.min.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Licensed to the Apache Software Foundation", response.data[:500])

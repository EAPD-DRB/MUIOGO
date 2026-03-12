"""
Pytest fixtures for the MUIOGO API test suite.

The Flask application in API/app.py is not structured as a factory, so the app
instance is imported once per test session with TESTING enabled. Each test
receives a fresh Flask test client whose file system operations are redirected
to a per-test temporary directory via monkeypatching of Config.DATA_STORAGE.
No test touches the real WebAPP/DataStorage directory.
"""

import json
import sys
from pathlib import Path

import pytest

# Make the Flask application and its internal modules importable.
API_DIR = Path(__file__).parent.parent / "API"
sys.path.insert(0, str(API_DIR))


@pytest.fixture(scope="session")
def flask_app():
    """
    Import and return the Flask application with TESTING mode enabled.

    Session-scoped so the app is initialised only once. Blueprint registration
    and module-level imports (including Config) happen here.
    """
    from app import app as flask_application  # noqa: PLC0415

    flask_application.config["TESTING"] = True
    flask_application.config["SECRET_KEY"] = "test-secret-key-not-for-production"
    return flask_application


@pytest.fixture
def data_storage(tmp_path):
    """
    Create an isolated DataStorage directory containing the minimal files
    that the API expects to exist at startup.

    Parameters.json uses empty arrays for every parameter group so that
    CaseClass and Osemosys.__init__ can iterate over them without side effects.
    Variables.json is an empty mapping so deleteCaseRun's view-cleanup loop
    is a no-op.
    """
    storage = tmp_path / "DataStorage"
    storage.mkdir()

    parameters = {
        group: []
        for group in [
            "R", "RY", "RT", "RE", "RS",
            "RYT", "RYC", "RYE", "RYTC", "RYTM",
            "RYTCM", "RYTE", "RYTEM", "RYTTs", "RYCTs",
            "RYTs", "RYDtb", "RYSeDt", "RYS", "RYTSM",
            "RTSM", "RYCn", "RYTCn",
        ]
    }
    (storage / "Parameters.json").write_text(json.dumps(parameters))
    (storage / "Variables.json").write_text(json.dumps({}))

    return storage


@pytest.fixture
def case_fixture(data_storage):
    """
    Create a minimal valid case directory under data_storage.

    The structure matches what Osemosys.__init__ and route handlers expect:
      <storage>/<case_name>/
        genData.json
        res/
        view/
          resData.json
          viewDefinitions.json

    Returns the case name string so tests can pass it in request payloads.
    """
    case_name = "test_case"
    case_dir = data_storage / case_name
    case_dir.mkdir()

    gen_data = {
        "osy-casename": case_name,
        "osy-desc": "A test case",
        "osy-version": 1.0,
        "osy-years": ["2020", "2025"],
        "osy-scenarios": [{"ScenarioId": "SC_0", "Active": True}],
        "osy-tech": [],
        "osy-emis": [],
        "osy-comm": [],
        "osy-stg": [],
        "osy-ts": [],
        "osy-se": [],
        "osy-dt": [],
        "osy-dtb": [],
        "osy-mo": "1",
        "osy-constraints": [],
    }
    (case_dir / "genData.json").write_text(json.dumps(gen_data))

    (case_dir / "res").mkdir()

    view_dir = case_dir / "view"
    view_dir.mkdir()
    (view_dir / "resData.json").write_text(json.dumps({"osy-cases": []}))
    (view_dir / "viewDefinitions.json").write_text(json.dumps({"osy-views": {}}))

    return case_name


@pytest.fixture
def client(flask_app, data_storage, monkeypatch):
    """
    Flask test client with Config.DATA_STORAGE redirected to a temporary
    directory. No active session is set. Use this for unauthenticated requests
    or cases where the test sets up session state explicitly.
    """
    import Classes.Base.Config as Config  # noqa: PLC0415

    monkeypatch.setattr(Config, "DATA_STORAGE", data_storage)
    with flask_app.test_client() as test_client:
        yield test_client


@pytest.fixture
def authed_client(flask_app, data_storage, case_fixture, monkeypatch):
    """
    Flask test client with Config.DATA_STORAGE redirected to a temporary
    directory and the Flask session pre-set to case_fixture.

    Yields a (client, case_name) tuple so tests have easy access to the
    active case name when constructing request payloads.
    """
    import Classes.Base.Config as Config  # noqa: PLC0415

    monkeypatch.setattr(Config, "DATA_STORAGE", data_storage)
    with flask_app.test_client() as test_client:
        with test_client.session_transaction() as sess:
            sess["osycase"] = case_fixture
        yield test_client, case_fixture

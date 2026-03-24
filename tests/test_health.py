"""Tests for the /api/health and /api/health/solvers endpoints."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Make sure the API package is importable when running from the repo root.
# The Flask app expects to run from inside API/, so we add that to sys.path
# the same way the start scripts do.
# ---------------------------------------------------------------------------
API_DIR = Path(__file__).resolve().parents[1] / "API"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app import app  # noqa: E402
from Routes.System import HealthRoute  # noqa: E402


@pytest.fixture
def client():
    """Flask test client with testing mode enabled."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset_health_cache(monkeypatch):
    """Ensure every test runs on a clean environment/cache.

    Copilot Review point: Ensure solver env vars are cleared so tests
    deterministically use the mocked shutil.which or bundled paths.
    """
    monkeypatch.setattr(HealthRoute, "_SOLVER_CACHE_DATA", {})
    monkeypatch.setattr(HealthRoute, "_SOLVER_CACHE_TIME", 0.0)
    # Clear environment variables so they don't interfere with PATH/bundled tests
    for var in ["SOLVER_GLPK_PATH", "SOLVER_CBC_PATH"]:
        monkeypatch.delenv(var, raising=False)


# ── /api/health ──────────────────────────────────────────────────────────────

class TestHealthEndpoint:

    def test_returns_200_when_healthy(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_returns_503_when_storage_unwritable(self, client):
        """Copilot Review point: Return non-200 when storage is degraded."""
        with patch("Routes.System.HealthRoute.Config") as mock_cfg:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                # Mock a directory that exists but we'll make reports as unwritable
                # (Easiest way in this context is to mock os.access or just the dir check result)
                mock_cfg.DATA_STORAGE = Path(tmpdir)
                with patch("Routes.System.HealthRoute.os.access", return_value=False):
                    resp = client.get("/api/health")

        assert resp.status_code == 503
        data = json.loads(resp.data)
        assert data["status"] == "error"
        assert data["dataStorage"] == "error"

    def test_response_contains_required_fields(self, client):
        resp = client.get("/api/health")
        data = json.loads(resp.data)
        assert data["status"] == "ok"
        assert "platform" in data
        assert "python" in data
        assert "architecture" in data
        assert "dataStorage" in data

    def test_python_version_looks_valid(self, client):
        resp = client.get("/api/health")
        data = json.loads(resp.data)
        # should be something like "3.11.9"
        parts = data["python"].split(".")
        assert len(parts) >= 2
        assert int(parts[0]) >= 3


# ── /api/health/solvers ──────────────────────────────────────────────────────

class TestSolverStatusEndpoint:

    def test_returns_200(self, client):
        resp = client.get("/api/health/solvers")
        assert resp.status_code == 200

    def test_response_has_solver_keys(self, client):
        resp = client.get("/api/health/solvers")
        data = json.loads(resp.data)
        assert "glpk" in data
        assert "cbc" in data
        assert "anyAvailable" in data

    def test_solver_entry_shape(self, client):
        """Each solver entry should have found/source/path keys."""
        resp = client.get("/api/health/solvers")
        data = json.loads(resp.data)
        for solver_key in ("glpk", "cbc"):
            entry = data[solver_key]
            assert "found" in entry
            assert "source" in entry
            assert "path" in entry

    @patch("Routes.System.HealthRoute.shutil.which")
    def test_glpk_found_on_path(self, mock_which, client):
        """When glpsol is on PATH, glpk should report found=True."""
        def side_effect(name):
            if name in ("glpsol", "glpsol.exe"):
                return "/usr/bin/glpsol"
            return None
        mock_which.side_effect = side_effect

        resp = client.get("/api/health/solvers")
        data = json.loads(resp.data)
        assert data["glpk"]["found"] is True
        assert data["glpk"]["source"] == "path"

    @patch("Routes.System.HealthRoute.shutil.which", return_value=None)
    def test_no_solvers_reports_false(self, mock_which, client):
        """When no solver is found anywhere, anyAvailable should be False."""
        # also need to make sure bundled dir scan finds nothing
        with patch("Routes.System.HealthRoute.Config") as mock_cfg:
            # point SOLVERs_FOLDER to a temp dir that has nothing
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                mock_cfg.SOLVERs_FOLDER = Path(tmpdir)
                mock_cfg.DATA_STORAGE = Path(tmpdir)
                resp = client.get("/api/health/solvers")

        data = json.loads(resp.data)
        assert data["anyAvailable"] is False

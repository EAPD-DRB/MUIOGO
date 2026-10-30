"""Exercise the app-to-linker subprocess boundary without starting an OG solve."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from Classes.Base import Config
from Classes.OGLink.PostRunHook import PostRunHook


@pytest.fixture()
def empty_model_registry(tmp_path, monkeypatch):
    registry = tmp_path / "models.json"
    registry.write_text(json.dumps({"models": {}}))
    monkeypatch.setenv("OGLINK_MODEL_REGISTRY", str(registry))
    return registry


def test_app_reports_in_repo_linker_and_no_installed_models(client, empty_model_registry):
    response = client.get("/oglink/status?deep=1")
    assert response.status_code == 200
    info = response.get_json()
    assert info["installed"] is True
    assert Path(info["home"]) == Config.BASE_DIR / "oglink"
    assert info["python"] == sys.executable
    assert info["models_registered"] is False
    assert "no OG models registered" in info["models_output"]


@pytest.mark.parametrize("command,expected", [
    (["list"], "coupled"),
    (["channels"], "emit_energy_demand"),
    (["models", "list"], "no OG models registered"),
])
def test_real_linker_cli_runs_in_application_python(empty_model_registry, command, expected):
    result = subprocess.run(
        [sys.executable, "-m", "oglink", *command],
        cwd=Config.BASE_DIR / "oglink", env=dict(os.environ),
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout


def test_status_explains_a_missing_linker_dependency(monkeypatch):
    monkeypatch.setattr("Classes.OGLink.PostRunHook.importlib.util.find_spec",
                        lambda name: None if name == "scipy" else object())
    info = PostRunHook.status()
    assert info["installed"] is False
    assert "scipy" in info["reason"]
    assert "setup" in info["reason"]

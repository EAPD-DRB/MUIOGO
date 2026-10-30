"""Case-save path safety, including operator-linked country cases."""

import json
import os
from pathlib import Path
import shutil

import pytest

from Classes.Base import Config
from Routes.Case import CaseRoute


INVALID_NAMES = (
    None, False, 0, [], {}, "", ".", "..", "../escape", "a/../../escape",
    "/tmp/escape", "nested/case", "nested\\case", "..\\escape", "case\x00name",
)


def _model(name):
    return {
        "osy-version": "5.7",
        "osy-casename": name,
        "osy-desc": "Disposable case-save test fixture",
        "osy-date": "2026-10-30",
        "osy-currency": "USD",
        "osy-mo": "1",
        "osy-years": ["2025"],
        "osy-scenarios": [{"ScenarioId": "SC_0", "ScenarioName": "Reference"}],
        **{key: [] for key in (
            "osy-tech", "osy-stg", "osy-techGroups", "osy-comm", "osy-ts",
            "osy-se", "osy-dt", "osy-dtb", "osy-emis", "osy-constraints", "osy-indicators",
        )},
    }


def _save(client, name):
    return client.post("/saveCase", json={"data": _model(name)})


def _set_session(client, name):
    with client.session_transaction() as sess:
        sess["osycase"] = name


def _snapshot(root):
    """Record both storage and external fixtures without following symlinks."""
    snapshot = {}
    for path in root.rglob("*"):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            snapshot[relative] = ("symlink", os.readlink(path))
        elif path.is_file():
            snapshot[relative] = ("file", path.read_bytes())
        else:
            snapshot[relative] = ("directory",)
    return snapshot


def _symlink(link, target):
    try:
        link.symlink_to(os.path.relpath(target, link.parent), target_is_directory=True)
    except OSError as exc:
        if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
            pytest.skip("Creating symlinks requires Windows developer mode or privileges")
        raise


@pytest.fixture
def case_storage(monkeypatch, tmp_path):
    storage = tmp_path / "DataStorage"
    storage.mkdir()
    for name in ("Parameters.json", "Variables.json", "Duals.json", "Indicators.json"):
        shutil.copyfile(Path(Config.DATA_STORAGE) / name, storage / name)
    monkeypatch.setattr(Config, "DATA_STORAGE", storage)
    return storage


@pytest.fixture
def original_case(client, case_storage):
    response = _save(client, "Original")
    assert response.status_code == 200
    assert response.get_json()["status_code"] == "created"
    return case_storage / "Original"


def _forbid_case_io(monkeypatch):
    def unexpected_io(*args, **kwargs):
        pytest.fail("Invalid case name reached case-file I/O")

    monkeypatch.setattr(CaseRoute.File, "readParamFile", unexpected_io)
    monkeypatch.setattr(CaseRoute.File, "writeFile", unexpected_io)


@pytest.mark.parametrize("name", INVALID_NAMES)
def test_validate_case_name_rejects_paths_and_non_strings(name):
    with pytest.raises(PermissionError):
        Config.validate_case_name(name)


@pytest.mark.parametrize("name", ("Model", "Country Model_2026", "Country-v1.2", "Modèle α"))
def test_validate_case_name_preserves_single_component_names(name):
    assert Config.validate_case_name(name) == name


@pytest.mark.parametrize("name", INVALID_NAMES)
@pytest.mark.parametrize("editing", (False, True))
def test_save_case_rejects_invalid_destination_before_io(
    client, original_case, monkeypatch, tmp_path, name, editing,
):
    active = "Original" if editing else None
    _set_session(client, active)
    before = _snapshot(tmp_path)
    _forbid_case_io(monkeypatch)

    response = _save(client, name)

    assert response.status_code == 400
    assert response.get_json()["status_code"] == "error"
    assert _snapshot(tmp_path) == before
    with client.session_transaction() as sess:
        assert sess["osycase"] == active


@pytest.mark.parametrize("name", ("LinkedCase/../escaped", "RealCase/out/../escaped"))
@pytest.mark.parametrize("editing", (False, True))
def test_save_case_blocks_symlink_dotdot_create_and_rename(
    client, original_case, case_storage, monkeypatch, tmp_path, name, editing,
):
    outside = tmp_path / "CountryRepo" / "case" / "LinkedCase"
    outside.mkdir(parents=True)
    _symlink(case_storage / "LinkedCase", outside)
    (case_storage / "RealCase").mkdir()
    _symlink(case_storage / "RealCase" / "out", outside)
    _set_session(client, "Original" if editing else None)
    before = _snapshot(tmp_path)
    _forbid_case_io(monkeypatch)

    response = _save(client, name)

    assert response.status_code == 400
    assert response.get_json()["status_code"] == "error"
    assert not (outside.parent / "escaped").exists()
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("active", (
    "../Outside", "Original/..", "Original/subcase", "LinkedCase/../escaped",
    "..\\Outside", False, 0, [], {},
))
def test_save_case_rejects_invalid_session_source_before_io(
    client, original_case, monkeypatch, tmp_path, active,
):
    (tmp_path / "Outside").mkdir()
    _set_session(client, active)
    before = _snapshot(tmp_path)
    _forbid_case_io(monkeypatch)

    response = _save(client, "Renamed")

    assert response.status_code == 400
    assert response.get_json()["status_code"] == "error"
    assert _snapshot(tmp_path) == before
    with client.session_transaction() as sess:
        assert sess["osycase"] == active


def test_save_case_rejects_absolute_session_source_before_io(
    client, original_case, monkeypatch, tmp_path,
):
    outside = tmp_path / "Outside"
    outside.mkdir()
    _set_session(client, str(outside))
    before = _snapshot(tmp_path)
    _forbid_case_io(monkeypatch)

    assert _save(client, "Renamed").status_code == 400
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("data", ([], "not an object", {}, {"osy-desc": "Missing name"}))
def test_save_case_rejects_malformed_model_data_before_io(client, monkeypatch, data):
    _forbid_case_io(monkeypatch)

    response = client.post("/saveCase", json={"data": data})

    assert response.status_code == 400
    assert response.get_json()["status_code"] == "error"


@pytest.mark.parametrize("active", (None, ""))
@pytest.mark.parametrize("name", ("Country Model_2026", "Country-v1.2", "Modèle α"))
def test_save_case_creates_edits_and_renames_ordinary_models(
    client, case_storage, name, active,
):
    _set_session(client, active)
    response = _save(client, name)
    assert response.status_code == 200
    assert response.get_json()["status_code"] == "created"
    original = case_storage / name
    parameter_path = original / "R.json"
    parameters = json.loads(parameter_path.read_text())
    parameters["DR"]["SC_0"][0]["value"] = 0.123
    parameter_path.write_text(json.dumps(parameters))

    response = _save(client, name)
    assert response.status_code == 200
    assert response.get_json()["status_code"] == "edited"
    assert json.loads(parameter_path.read_text()) == parameters

    response = _save(client, name + "_renamed")
    assert response.status_code == 200
    assert response.get_json()["status_code"] == "edited"
    assert not original.exists()
    assert json.loads((case_storage / (name + "_renamed") / "R.json").read_text()) == parameters
    with client.session_transaction() as sess:
        assert sess["osycase"] == name + "_renamed"


def test_save_case_edits_and_renames_linked_case_without_moving_external_directory(
    client, original_case, case_storage, tmp_path,
):
    outside = tmp_path / "CountryRepo" / "case" / "Original"
    outside.parent.mkdir(parents=True)
    original_case.rename(outside)
    _symlink(original_case, outside)
    parameters = (outside / "R.json").read_bytes()

    response = _save(client, "Original")
    assert response.status_code == 200
    assert response.get_json()["status_code"] == "edited"
    assert (outside / "R.json").read_bytes() == parameters

    response = _save(client, "RenamedLink")
    assert response.status_code == 200
    assert response.get_json()["status_code"] == "edited"
    renamed = case_storage / "RenamedLink"
    assert renamed.is_symlink()
    assert renamed.resolve() == outside
    assert not original_case.is_symlink()
    assert outside.is_dir()
    assert (outside / "R.json").read_bytes() == parameters
    assert json.loads((outside / "genData.json").read_text())["osy-casename"] == "RenamedLink"


def test_save_case_preserves_existing_handling_of_filesystem_permission_errors(
    client, case_storage, monkeypatch,
):
    def denied(*args, **kwargs):
        raise PermissionError("Fixture permission failure")

    monkeypatch.setattr(CaseRoute.File, "readParamFile", denied)

    assert _save(client, "ValidModel").status_code == 404

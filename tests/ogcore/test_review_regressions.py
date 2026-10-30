"""Regression cases for workspace scope, run ownership, and reuse reads."""
import json
from pathlib import Path

import pytest

from Classes.Base import Config
from Classes.OGCore import OGCoreCase as CaseModule
from Classes.OGCore import RunJob as JobModule
from Classes.OGCore.OGResults import OGResults
from Classes.OGCore.CalibrationRegistry import CalibrationRegistry
from Classes.OGCore.OGCoreCase import OGCoreCase
from Classes.OGCore.RunJob import RunJob


@pytest.mark.parametrize("endpoint", ["getParameterSchema", "getParameterDefault"])
@pytest.mark.parametrize("address", [{"country_id": "ETH"}, {"casename": "other"}])
def test_parameter_read_rejects_partial_case_address(client, make_case, calibration, endpoint, address):
    make_case("selected", runs=[("base", "baseline", None)])
    response = client.get(f"/ogc/{endpoint}", query_string={**address, "parameter": "frisch"})
    assert response.status_code == 400


def test_country_only_activation_validates_before_registry_lookup(client, monkeypatch):
    calls = []
    monkeypatch.setattr(CalibrationRegistry, "get", lambda country: calls.append(country) or {})
    response = client.post("/ogc/setSession", json={"casename": None, "country_id": "../outside"})
    assert response.status_code == 400
    assert calls == []
    assert client.get("/ogc/getSession").get_json()["ogccountry"] is None


def test_status_poll_does_not_fail_newly_claimed_run(client, make_case, calibration, monkeypatch):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "queued")
    original = RunJob.get_live
    reads = []
    def claim_after_snapshot(country, casename, name):
        reads.append(name)
        if len(reads) == 1:
            RunJob._queue.append((country, casename, name, False))
            return None
        return original(country, casename, name)
    monkeypatch.setattr(RunJob, "get_live", claim_after_snapshot)
    killed = []
    monkeypatch.setattr(JobModule, "kill_worker_tree", lambda *args: killed.append(args))
    response = client.post("/ogc/getRunStatus", json={"country_id": "ETH", "casename": "c1", "run_name": "base"})
    assert response.status_code == 200
    assert response.get_json()["run_state"] == "queued"
    assert case.get_run_meta("base")["status"] == "queued"
    assert killed == []


def test_unknown_active_baseline_mode_allows_only_steady_reform(make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None), ("reform", "reform", "base")])
    RunJob._active = {"country_id": "ETH", "casename": "c1", "run_name": "base"}
    with RunJob._lock:
        assert RunJob._validate_reform_locked(case, "reform", False, allow_preceding_baseline=True) is None
        error = RunJob._validate_reform_locked(case, "reform", True, allow_preceding_baseline=True)
    assert "transition" in error["message"]


def test_corrupt_live_dependency_blocks_baseline_edit_without_500(client, make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None), ("reform", "reform", "base")])
    (case.res_path / "reform" / "run_meta.json").write_text("{broken")
    RunJob._queue.append(("ETH", "c1", "reform", False))
    response = client.post("/ogc/saveParams", json={
        "country_id": "ETH", "casename": "c1", "run_name": "base", "params": {"frisch": 1.7},
    })
    assert response.status_code == 400
    assert "dependent reform" in response.get_json()["message"]
    assert case.get_params("base") == {}


def test_status_explains_parameter_invalidation(client, make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "completed", time_path=True)
    completed_at = case.get_run_meta("base")["completed_at"]
    case.save_params("base", {"frisch": 1.7})
    response = client.post("/ogc/getRunStatus", json={"country_id": "ETH", "casename": "c1", "run_name": "base"})
    data = response.get_json()
    assert data["reusable"] is False
    assert "Parameters changed" in data["stale_reason"]
    assert data["time_path"] is True
    assert data["run_state"] == "completed"
    assert data["completed_at"] == completed_at


@pytest.mark.parametrize("endpoint,key", [("getSSVars", "run_name"), ("getTPIVars", "run_name"), ("getResults", "base_run"), ("getMacroTable", "base_run")])
def test_result_reads_reject_changed_calibration(client, make_case, calibration, monkeypatch, endpoint, key):
    case = make_case("c1", runs=[("base", "baseline", None)])
    case.update_run_status("base", "completed", time_path=True)
    CalibrationRegistry.upsert({"country_id": "ETH", "commit_sha": "changed"})
    monkeypatch.setattr(OGResults, "load_ss", lambda path: {"Yss": 1.0})
    monkeypatch.setattr(OGResults, "load_tpi", lambda path: {"Y": [1.0]})
    response = client.post(f"/ogc/{endpoint}", json={
        "country_id": "ETH", "casename": "c1", key: "base", "table_type": "macro",
    })
    assert response.status_code == 404
    if key == "base_run":
        assert "current inputs" in response.get_json()["message"]


def test_tax_hash_cached_until_file_changes(make_case, calibration):
    case = make_case("c1", runs=[("base", "baseline", None)])
    tax_path = case.res_path / "base" / "ogcTaxParams.pkl"
    tax_path.write_bytes(b"first")
    CaseModule._tax_params_sha256.cache_clear()
    first = case.execution_input_fingerprint("base", False)
    assert case.execution_input_fingerprint("base", False) == first
    assert CaseModule._tax_params_sha256.cache_info().misses == 1
    assert CaseModule._tax_params_sha256.cache_info().hits == 1
    tax_path.write_bytes(b"second")
    assert case.execution_input_fingerprint("base", False) != first
    assert CaseModule._tax_params_sha256.cache_info().misses == 2


def test_run_listing_reads_registry_once(make_case, calibration, monkeypatch):
    case = make_case("c1", runs=[("base", "baseline", None), ("reform", "reform", "base")])
    for name in ("base", "reform"):
        case.update_run_status(name, "completed", time_path=False)
    original = CalibrationRegistry.get
    reads = []
    monkeypatch.setattr(CalibrationRegistry, "get", lambda country: reads.append(country) or original(country))
    assert all(run["reusable"] for run in case.get_runs())
    assert reads == ["ETH"]


def test_migration_cleanup_failure_still_counts_success(monkeypatch, caplog):
    flat = Config.OGC_CASES_DIR / "legacy"
    flat.mkdir(parents=True)
    (flat / "genData.json").write_text(json.dumps({"country_id": "ETH"}))
    original = Path.rmdir
    def fail_cleanup(path):
        if path.parent.name == "migrate_tmp":
            raise OSError("Directory busy")
        return original(path)
    monkeypatch.setattr(Path, "rmdir", fail_cleanup)
    assert OGCoreCase.migrate_flat_cases() == 1
    assert (Config.OGC_CASES_DIR / "ETH" / "legacy" / "genData.json").is_file()
    assert "Could not move case" not in caplog.text

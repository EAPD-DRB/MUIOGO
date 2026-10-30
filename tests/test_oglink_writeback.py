"""Real CLI/HTTP/case-generation round trips; the optimizer boundary is stubbed.

All cases are created through saveCase in disposable DataStorage. Matrix checks
use glpsol --check only. No live case or optimizer is used by these tests.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest
from werkzeug.serving import make_server

from Classes.Base import Config
from Classes.Case.DataFileClass import DataFile


@pytest.fixture
def writeback_case(client, monkeypatch, tmp_path):
    storage = tmp_path / "DataStorage"
    storage.mkdir()
    for name in ("Parameters.json", "Variables.json", "Duals.json", "Indicators.json"):
        shutil.copyfile(Path(Config.DATA_STORAGE) / name, storage / name)
    params = json.loads((storage / "Parameters.json").read_text())
    monkeypatch.setattr(Config, "DATA_STORAGE", storage)
    tech = {"TechId": "T", "Tech": "GEN", "Desc": "Synthetic producer"}
    for group in ("RYTC", "RYTCM", "RYTEM"):
        tech.update({p["id"]: [] for p in params[group]})
    tech.update({"OAR": ["C"], "EAR": []})
    scenarios = [{"ScenarioId": s, "Scenario": s, "Active": True} for s in ("SC_0", "POLICY")]
    gen = {
        "osy-version": "5.7", "osy-casename": "Source", "osy-desc": "Disposable writeback test",
        "osy-date": "2026-10-30", "osy-currency": "USD", "osy-mo": "1", "osy-years": ["2030", "2031"],
        "osy-scenarios": scenarios, "osy-tech": [tech],
        "osy-comm": [{"CommId": "C", "Comm": "FINAL", "BalanceLevel": "Ts"}],
        "osy-emis": [{"EmisId": "E", "Emis": "CO2e"}],
        "osy-ts": [{"TsId": "L", "Ts": "L", "SE": "S", "DT": "D", "DTB": "B"}],
        "osy-se": [{"SeId": "S", "Se": "1"}], "osy-dt": [{"DtId": "D", "Dt": "1"}],
        "osy-dtb": [{"DtbId": "B", "Dtb": "1"}],
        **{k: [] for k in ("osy-stg", "osy-techGroups", "osy-constraints", "osy-indicators")},
    }
    with client.session_transaction() as session:
        session["osycase"] = None
    response = client.post("/saveCase", json={"data": gen})
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["status_code"] == "created"
    case = storage / "Source"

    def values(filename, parameter, scenario, y2030, y2031):
        path = case / filename
        data = json.loads(path.read_text())
        for row in data[parameter][scenario]:
            row.update({"2030": y2030, "2031": y2031})
        path.write_text(json.dumps(data))

    values("RYC.json", "SAD", "SC_0", 100, 150)
    values("RYC.json", "SAD", "POLICY", None, 200)
    values("RYTs.json", "YS", "SC_0", 1, 1)
    values("RYCTs.json", "SDP", "SC_0", 1, 1)
    values("RYTCM.json", "OAR", "SC_0", 1, 1)
    record = {"Case": "POLICY_RUN", "CaseId": "CS_source", "Scenarios": scenarios}
    assert DataFile("Source").createCaseRun("POLICY_RUN", record)["status_code"] == "success"
    run = tmp_path / "run"
    (run / "clews_inputs").mkdir(parents=True)
    manifest = {"country": "Testland", "un_code": "999", "scenario": {
        "reform_dir": str(case / "res/POLICY_RUN/csv"), "og_start_year": 2030},
        "concordance": {"energy_industry_index": 0}}
    (run / "oglink_manifest.json").write_text(json.dumps(manifest))
    countries = tmp_path / "countries.json"
    countries.write_text(json.dumps({"countries": [{
        "name": "Testland", "un_code": "999", "og_repo": "og-test", "gdp_musd": 1000,
        "og_start_year": 2030, "power_prefix": "GEN", "electricity_fuel": "FINAL",
        "demand_commodity": "FINAL", "gbd_burden_csv": None, "pm25_dose_response": None}]}))
    return SimpleNamespace(storage=storage, case=case, run=run, countries=countries)


def _feedback(case, ratio):
    (case.run / "clews_inputs/demand_scaling.csv").write_text(
        "REGION,OG_ACTIVITY,OG_INDEX,CLEWS_FUEL,YEAR,DEMAND_RATIO\n"
        f"RE1,sector_output,0,FINAL,2030,{ratio}\nRE1,sector_output,0,FINAL,2031,{ratio}\n")


def _snapshot(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob("*") if p.is_file()}


def _generated_demand(path):
    # parseDataFile intentionally reads only the parameters used by the results
    # exporter, so inspect the actual GMPL demand block directly.
    block = path.read_text().split("param SpecifiedAnnualDemand ", 1)[1].split("\n;", 1)[0]
    rows = [line.split()[1:] for line in block.splitlines() if line.startswith("FINAL ")]
    assert len(rows) == 1
    return list(map(float, rows[0]))


@pytest.mark.parametrize("mode", ["dry_run", "unchanged", "apply", "http_error"])
def test_cli_http_roundtrip_preserves_source_and_scenario_order(writeback_case, app, monkeypatch, mode):
    fixture = writeback_case
    _feedback(fixture, 1 if mode == "unchanged" else 1.1)
    before = _snapshot(fixture.case)
    runs = []

    def stub_optimizer(self, solver, caserun):
        runs.append((self.case, caserun, solver))
        datafile = Path(Config.DATA_STORAGE, self.case, "res", caserun, "data.txt")
        assert _generated_demand(datafile) == pytest.approx([110, 220])
        if mode == "http_error":
            return {"status_code": "error", "cbc_message": "synthetic solver failure"}
        return {"status_code": "success", "timer": 0}

    monkeypatch.setattr(DataFile, "run", stub_optimizer)
    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    command = [sys.executable, "-m", "oglink", "writeback", "--run", str(fixture.run),
        "--country", "Testland", "--countries", str(fixture.countries), "--case", "Source",
        "--base-caserun", "POLICY_RUN", "--datastorage", str(fixture.storage),
        "--muiogo-url", f"http://127.0.0.1:{server.server_port}"]
    if mode == "dry_run":
        command.append("--dry-run")
    try:
        result = subprocess.run(command, cwd=Config.BASE_DIR / "oglink", env=dict(os.environ),
                                capture_output=True, text=True, timeout=30)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
    assert not thread.is_alive()
    assert result.returncode == (1 if mode == "http_error" else 0), result.stderr
    assert _snapshot(fixture.case) == before
    patch = json.loads((fixture.run / "clews_patch.json").read_text())
    assert all(c["scenario"] == "POLICY" for c in patch["changes"])
    if mode in ("dry_run", "unchanged"):
        assert runs == []
        assert set(p.name for p in fixture.storage.iterdir() if p.is_dir()) == {"Source"}
    else:
        assert len(runs) == 1
        copied, caserun, _ = runs[0]
        assert copied != "Source"
        gen = json.loads((fixture.storage / copied / "genData.json").read_text())
        assert gen["osy-casename"] == copied
        applied = json.loads((fixture.storage / copied / "oglink/patch_applied.json").read_text())
        assert applied["base_caserun"] == "POLICY_RUN"
        if mode == "http_error":
            assert "solve did not succeed" in result.stderr
        else:
            assert "Write-back applied and solved successfully" in result.stdout


def test_patched_demand_survives_preprocessing_and_matrix_check(writeback_case, monkeypatch, tmp_path):
    glpsol = shutil.which("glpsol")
    if glpsol is None:
        pytest.skip("GLPK is required for matrix-only validation")
    monkeypatch.syspath_prepend(str(Config.BASE_DIR / "oglink"))
    from oglink import clews_case
    from oglink.patch import build_clews_patch
    from Classes.OGLink.PatchApply import OGLinkPatch

    fixture = writeback_case
    values = clews_case.read_effective_sad(fixture.case, "POLICY_RUN", "FINAL")
    patch = build_clews_patch(case="Source", scenario="POLICY", demand_commodity="FINAL",
        demand_ratio_by_year={2030: 1.1, 2031: 1.1}, base_sad_by_year=values,
        case_years={2030, 2031}, start_year=2030)
    plan = OGLinkPatch.resolve_changes(fixture.case, patch["changes"], {"SC_0", "POLICY"})
    OGLinkPatch.apply_plan(fixture.case, plan)
    datafile = fixture.case / "res/POLICY_RUN/data.txt"
    processed = tmp_path / "data_processed.txt"
    runner = DataFile("Source")
    runner.generateDatafile("POLICY_RUN")
    runner.preprocessData(datafile, processed)
    assert _generated_demand(processed) == pytest.approx([110, 220])
    assert re.search(r"set MODEperTECHNOLOGY\[GEN\]\s*:=\s*1\s*;", processed.read_text())
    lp = tmp_path / "lp.lp"
    checked = subprocess.run([glpsol, "--check", "-m", str(runner.osemosysFile),
        "-d", str(processed), "--wlp", str(lp)], capture_output=True, text=True, timeout=30)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert lp.is_file()
    assert ">= 220" in lp.read_text()

"""The Results report: comparison rules, household weighting, metadata backfill.

Rates are compared in percentage points, fiscal quantities as shares of GDP, and
a percent change is never reported against a negative baseline. Household views
use the run's own population weights and group labels, and a run without that
metadata gets a reason instead of invented labels.
"""
import json

import pytest

from Classes.OGCore import OGReport, OGTables
from Classes.OGCore.OGResults import OGResults

META = {
    "meta_version": 2, "start_year": 2026, "T": 3, "S": 2, "J": 2,
    "starting_age": 20, "ending_age": 22, "ages": [20, 21],
    "lambdas": [0.25, 0.75], "group_labels": ["0-25%", "Top 75%"],
    "omega_SS": [0.4, 0.6], "g_y": 0.02, "time_path": True,
}


def close(actual, expected):
    assert actual == pytest.approx(expected, rel=1e-12, abs=1e-12)


# ── comparison rules ─────────────────────────────────────────────────────────
def test_level_is_a_percent_change():
    out = OGReport.compare("level", 2.0, 2.1)
    close(out["change"], 5.0)
    assert out["change_unit"] == "%" and out["negative_baseline"] is False


def test_rate_is_compared_in_percentage_points():
    out = OGReport.compare("rate", 0.070, 0.075)
    close(out["baseline"], 7.0)
    close(out["change"], 0.5)
    assert out["change_unit"] == "pp"


def test_fiscal_is_a_share_of_each_runs_gdp():
    out = OGReport.compare("fiscal", 0.6, 0.66, base_gdp=2.0, reform_gdp=2.0)
    close(out["baseline"], 30.0)
    close(out["change"], 3.0)
    assert out["change_unit"] == "pp of GDP"


def test_negative_level_baseline_reports_a_difference_not_a_percent():
    out = OGReport.compare("level", -10.0, -5.0)
    assert out["negative_baseline"] is True
    assert out["change_unit"] == "difference"
    close(out["change"], 5.0)


def test_negative_fiscal_baseline_is_flagged():
    out = OGReport.compare("fiscal", -1.0, -0.5, base_gdp=10.0, reform_gdp=10.0)
    assert out["negative_baseline"] is True
    close(out["change"], 5.0)


def test_wage_is_a_level_and_interest_is_a_rate():
    assert OGReport.describe("w")["kind"] == "level"
    assert OGReport.describe("r")["kind"] == "rate"
    assert OGReport.describe("G")["kind"] == "fiscal"


# ── weighting ────────────────────────────────────────────────────────────────
def test_age_only_weights_combine_with_group_shares():
    weights = OGReport.household_weights(META)
    close(weights[0][0], 0.4 * 0.25)
    close(weights[1][1], 0.6 * 0.75)


def test_age_by_group_weights_are_used_directly():
    meta = dict(META, omega_SS=[[0.1, 0.3], [0.15, 0.45]])
    weights = OGReport.household_weights(meta)
    close(weights[0][1], 0.3)


def test_weighted_profiles_match_a_hand_calculation():
    weights = OGReport.household_weights(META)
    matrix = [[1.0, 3.0], [5.0, 7.0]]
    by_age, by_group, overall = OGReport.weighted_profiles(matrix, weights)
    close(by_age[0], 0.25 * 1 + 0.75 * 3)
    close(by_group[1], 0.4 * 3 + 0.6 * 7)
    close(overall, 0.1 * 1 + 0.3 * 3 + 0.15 * 5 + 0.45 * 7)


def test_meta_without_weights_is_incomplete():
    assert OGReport.meta_complete(META)
    assert not OGReport.meta_complete({"start_year": 2026, "T": 3, "S": 2})
    assert OGReport.household_weights({"start_year": 2026}) is None


# ── report ───────────────────────────────────────────────────────────────────
def run(y=2.0, r=0.05, c=((1.0, 3.0), (5.0, 7.0)), meta=META, tpi=True):
    ss = {"Y": y, "C": 1.0, "r": r, "D": 1.2, "G": -0.1, "total_tax_revenue": 0.5,
          "c": [list(row) for row in c], "euler_savings": [[1e-14, 2e-14], [0.0, 0.0]]}
    path = {"Y": [y] * 3, "r": [r] * 3, "D": [1.2] * 3} if tpi else None
    return {"ss": ss, "tpi": path, "meta": meta}


def test_report_labels_groups_and_ages_from_metadata():
    report = OGReport.build_report(run(), run(y=2.2, c=((1.1, 3.3), (5.5, 7.7))))
    assert report["meta"]["group_labels"] == ["0-25%", "Top 75%"]
    assert report["meta"]["ages"] == [20, 21]
    close(report["meta"]["weights"]["baseline"][1][1], 0.45)
    household = report["households"]["c"]
    close(household["overall"]["change"], 10.0)
    assert [round(g["change"], 9) for g in household["group_change"]] == [10.0, 10.0]


def test_report_states_period_and_units():
    report = OGReport.build_report(run(), run(y=2.2, r=0.06))
    assert report["analysis"] == "transition"
    summary = {row["name"]: row for row in report["summary"]}
    assert summary["r"]["change_unit"] == "pp"
    close(summary["r"]["change"], 1.0)
    assert summary["D"]["change_unit"] == "pp of GDP"
    assert report["transition"]["budget_window"] == 10
    assert report["transition"]["years"] == [2026, 2027, 2028]


def test_negative_government_consumption_is_flagged_in_fiscal():
    report = OGReport.build_report(run(), run())
    fiscal = {row["name"]: row for row in report["fiscal"]}
    assert fiscal["G"]["negative_baseline"] is True


def test_steady_state_only_runs_report_the_long_run():
    report = OGReport.build_report(run(tpi=False), run(tpi=False))
    assert report["analysis"] == "steady" and report["transition"] is None


def test_missing_metadata_gives_a_reason_not_labels():
    legacy = {"start_year": 2026, "T": 3, "S": 2}
    report = OGReport.build_report(run(meta=legacy), run(meta=legacy))
    assert report["households"] is None
    assert "metadata" in report["households_reason"]
    assert report["meta"]["group_labels"] is None


def test_single_run_has_no_changes():
    report = OGReport.build_report(run())
    assert report["mode"] == "single"
    assert all(row["change"] is None for row in report["summary"])


def test_diagnostics_report_convergence():
    report = OGReport.build_report(run())
    assert report["diagnostics"]["baseline"]["converged"] is True


# ── metadata backfill ────────────────────────────────────────────────────────
def test_complete_metadata_is_not_rebuilt(tmp_path, monkeypatch):
    (tmp_path / "results_meta.json").write_text(json.dumps(META))
    monkeypatch.setattr(OGTables, "run_worker_mode", lambda *a, **k: pytest.fail("rebuilt"))
    meta, reason = OGTables.ensure_run_metadata(object(), tmp_path)
    assert reason is None and meta["group_labels"] == ["0-25%", "Top 75%"]


def test_legacy_metadata_without_parameters_explains_why(tmp_path):
    (tmp_path / "results_meta.json").write_text(json.dumps({"start_year": 2026, "T": 3, "S": 2}))
    meta, reason = OGTables.ensure_run_metadata(object(), tmp_path)
    assert meta["S"] == 2 and "parameters" in reason


def test_legacy_metadata_is_rebuilt_and_saved(tmp_path, monkeypatch):
    (tmp_path / "results_meta.json").write_text(json.dumps({"start_year": 2026, "T": 3, "S": 2}))
    (tmp_path / "model_params.pkl").write_bytes(b"")
    monkeypatch.setattr(OGTables, "resolve_python", lambda case: ("python", None))
    calls = []

    def fake_worker(python_path, argv, timeout=180):
        calls.append(argv)
        return dict(META), None

    monkeypatch.setattr(OGTables, "run_worker_mode", fake_worker)
    meta, reason = OGTables.ensure_run_metadata(object(), tmp_path)
    assert reason is None and calls[0][:2] == ["meta", "--run-dir"]
    saved = json.loads((tmp_path / "results_meta.json").read_text())
    assert OGReport.meta_complete(saved)


# ── endpoint ─────────────────────────────────────────────────────────────────
def test_report_endpoint_compares_a_completed_pair(client, make_case, calibration, monkeypatch):
    case = make_case("c1", runs=[("base", "baseline", None), ("reform", "reform", "base")])
    case.update_run_status("base", "completed", time_path=False)
    case.update_run_status("reform", "completed", time_path=False)
    runs = {"base": run(tpi=False), "reform": run(y=2.2, tpi=False)}
    monkeypatch.setattr(OGResults, "load_ss", lambda path: runs[path.name]["ss"])
    monkeypatch.setattr(OGResults, "load_tpi", lambda path: None)
    monkeypatch.setattr(OGTables, "ensure_run_metadata", lambda case, path: (META, None))
    response = client.post("/ogc/getResultsReport", json={
        "country_id": "ETH", "casename": "c1", "base_run": "base", "reform_run": "reform",
    })
    data = response.get_json()
    assert response.status_code == 200, data
    assert data["mode"] == "compare" and data["analysis"] == "steady"
    assert data["households"]["c"]["by_age"]["baseline"]


def test_report_endpoint_requires_a_completed_run(client, make_case, calibration):
    make_case("c1", runs=[("base", "baseline", None)])
    response = client.post("/ogc/getResultsReport", json={
        "country_id": "ETH", "casename": "c1", "base_run": "base",
    })
    assert response.status_code == 404

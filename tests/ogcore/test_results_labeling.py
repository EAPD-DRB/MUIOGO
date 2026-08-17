"""Result-table labelling.

OG-Core names a table's two slots by position and cannot be told otherwise, so a
single-run table of a reform would claim to be a baseline. A one-run table is
labelled with that run's own name instead; a two-run comparison keeps the
baseline/reform wording. The slot name arrives in three shapes: a suffix of the
"Variable" value (macro), a whole column key (ineq, gini), and a suffix of a column
key (time_series).
"""
import csv
import io

import pytest

from Classes.OGCore import OGTables


def macro_rows():
    return [
        {"Variable": "GDP Baseline", "2025": 1.0, "SS": 2.0},
        {"Variable": "Consumption Baseline", "2025": 3.0, "SS": 4.0},
    ]


def ineq_rows():
    return [{"Steady-State Variable": "Income", "Baseline": 0.71}]


def time_series_rows():
    return [{"Year": 2025, "GDP: Baseline": 1.0}]


# ── the relabelling itself ───────────────────────────────────────────────────
def test_relabel_uses_the_run_name():
    rows = OGTables.relabel_single_run(macro_rows(), "reform1")
    assert [r["Variable"] for r in rows] == ["GDP (reform1)", "Consumption (reform1)"]


def test_relabel_keeps_the_values():
    rows = OGTables.relabel_single_run(macro_rows(), "reform1")
    assert rows[0]["2025"] == 1.0 and rows[0]["SS"] == 2.0


def test_relabel_does_not_mutate_the_input():
    original = macro_rows()
    OGTables.relabel_single_run(original, "reform1")
    assert original[0]["Variable"] == "GDP Baseline"


def test_relabel_renames_a_whole_column_key():
    # ineq and gini put the slot name in the column key, not the Variable value.
    rows = OGTables.relabel_single_run(ineq_rows(), "reform1")
    assert rows[0] == {"Steady-State Variable": "Income", "reform1": 0.71}


def test_relabel_renames_a_suffixed_column_key():
    rows = OGTables.relabel_single_run(time_series_rows(), "reform1")
    assert rows[0] == {"Year": 2025, "GDP: reform1": 1.0}


def test_relabel_leaves_unsuffixed_rows_alone():
    # Percent-change and difference tables carry no slot label.
    rows = OGTables.relabel_single_run(
        [{"Variable": "GDP"}, {"Variable": "GDP Reform"}, {"Variable": None}], "r1"
    )
    assert [r["Variable"] for r in rows] == ["GDP", "GDP Reform", None]


def test_relabel_only_strips_the_trailing_slot_label():
    rows = OGTables.relabel_single_run(
        [{"Variable": "Baseline Spending Baseline"}], "reform1"
    )
    assert rows[0]["Variable"] == "Baseline Spending (reform1)"


def test_relabel_passes_through_non_dict_rows():
    assert OGTables.relabel_single_run(["oops", None], "r1") == ["oops", None]


# ── through the endpoints ────────────────────────────────────────────────────
def _completed(case, run_name, run_type="baseline", baseline=None):
    case.create_run(run_name, run_type, baseline, {})
    case.update_run_status(run_name, "completed", time_path=False)


def _stub_worker(monkeypatch, rows):
    """Replace the OG-side worker call; captures the argv it was given."""
    captured = {}

    def fake_run(python_path, argv, timeout=180):
        captured["argv"] = argv
        return {"rows": rows}, None

    monkeypatch.setattr(OGTables, "resolve_python", lambda case: ("py", None))
    monkeypatch.setattr(OGTables, "run_worker_mode", fake_run)
    return captured


@pytest.fixture
def case_with_runs(make_case, calibration):
    case = make_case("c1")
    _completed(case, "base")
    _completed(case, "reform1", "reform", "base")
    return case


def test_macro_table_single_reform_is_labelled_by_run(
    client, case_with_runs, monkeypatch
):
    captured = _stub_worker(monkeypatch, macro_rows())

    resp = client.post("/ogc/getMacroTable",
                       json={"country_id": "ETH", "casename": "c1", "base_run": "reform1"})

    assert resp.status_code == 200
    labels = [r["Variable"] for r in resp.get_json()]
    assert labels == ["GDP (reform1)", "Consumption (reform1)"]
    assert not any("Baseline" in label for label in labels)
    # A single-run macro table is only meaningful as levels, and sends no reform.
    assert "--reform-dir" not in captured["argv"]
    assert "levels" in " ".join(captured["argv"])


def test_macro_table_single_baseline_is_labelled_by_run(
    client, case_with_runs, monkeypatch
):
    # The previously-correct path also becomes name-labelled: one run, one name.
    _stub_worker(monkeypatch, macro_rows())

    resp = client.post("/ogc/getMacroTable",
                       json={"country_id": "ETH", "casename": "c1", "base_run": "base"})

    assert [r["Variable"] for r in resp.get_json()] == [
        "GDP (base)", "Consumption (base)",
    ]


def test_macro_table_comparison_keeps_baseline_and_reform(
    client, case_with_runs, monkeypatch
):
    rows = macro_rows() + [{"Variable": "GDP Reform", "2025": 9.0, "SS": 9.0}]
    _stub_worker(monkeypatch, rows)

    resp = client.post(
        "/ogc/getMacroTable",
        json={"country_id": "ETH", "casename": "c1", "base_run": "base", "reform_run": "reform1",
              "output_type": "levels"},
    )

    assert resp.status_code == 200
    assert [r["Variable"] for r in resp.get_json()] == [
        "GDP Baseline", "Consumption Baseline", "GDP Reform",
    ]


def test_ineq_table_single_reform_is_labelled_by_run(
    client, case_with_runs, monkeypatch
):
    _stub_worker(monkeypatch, ineq_rows())

    resp = client.post("/ogc/getIneqTable",
                       json={"country_id": "ETH", "casename": "c1", "base_run": "reform1"})

    assert resp.status_code == 200
    row = resp.get_json()[0]
    assert "Baseline" not in row and row["reform1"] == 0.71


def test_time_series_table_single_reform_is_labelled_by_run(
    client, case_with_runs, monkeypatch
):
    _stub_worker(monkeypatch, time_series_rows())

    resp = client.post("/ogc/getTimeSeriesTable",
                       json={"country_id": "ETH", "casename": "c1", "base_run": "reform1"})

    assert resp.status_code == 200
    assert resp.get_json()[0] == {"Year": 2025, "GDP: reform1": 1.0}


def test_table_worker_failure_is_a_502(client, case_with_runs, monkeypatch):
    monkeypatch.setattr(OGTables, "resolve_python", lambda case: ("py", None))
    monkeypatch.setattr(
        OGTables, "run_worker_mode",
        lambda python_path, argv, timeout=180: (None, "boom"),
    )

    resp = client.post("/ogc/getMacroTable",
                       json={"country_id": "ETH", "casename": "c1", "base_run": "base"})

    assert resp.status_code == 502
    assert resp.get_json()["message"] == "boom"


def test_download_single_reform_csv_is_labelled_by_run(
    client, case_with_runs, monkeypatch
):
    _stub_worker(monkeypatch, macro_rows())

    resp = client.get("/ogc/downloadResults?country_id=ETH&casename=c1&base_run=reform1")

    assert resp.status_code == 200
    rows = list(csv.DictReader(io.StringIO(resp.get_data(as_text=True))))
    assert [r["Variable"] for r in rows] == ["GDP (reform1)", "Consumption (reform1)"]


def test_download_comparison_csv_keeps_baseline_and_reform(
    client, case_with_runs, monkeypatch
):
    rows = macro_rows() + [{"Variable": "GDP Reform", "2025": 9.0, "SS": 9.0}]
    _stub_worker(monkeypatch, rows)

    resp = client.get(
        "/ogc/downloadResults?country_id=ETH&casename=c1&base_run=base&reform_run=reform1"
    )

    assert resp.status_code == 200
    parsed = list(csv.DictReader(io.StringIO(resp.get_data(as_text=True))))
    assert [r["Variable"] for r in parsed] == [
        "GDP Baseline", "Consumption Baseline", "GDP Reform",
    ]


def test_wealth_moments_accepts_data_moments(client, case_with_runs, monkeypatch):
    """OG-Core's wealth table needs data_moments to build at all, and the worker
    accepts it, so the route has to pass it through or the table is unreachable."""
    captured = _stub_worker(monkeypatch, [{"Moment": "Gini", "Data": 0.8, "Model": 0.7}])

    resp = client.post(
        "/ogc/getWealthMomentsTable",
        json={
            "country_id": "ETH",
            "casename": "c1",
            "base_run": "base",
            "data_moments": [0.1, 0.2],
        },
    )

    assert resp.status_code == 200
    argv = captured["argv"]
    assert "--args-json" in argv
    assert "data_moments" in argv[argv.index("--args-json") + 1]


def test_wealth_moments_asks_for_blank_data_when_none_given(
    client, case_with_runs, monkeypatch
):
    """OG-Core cannot build this table without a Data column, so the worker fills it
    with blanks and drops it again; the caller gets the model's own numbers."""
    captured = _stub_worker(monkeypatch, [{"Moment": "Gini", "Model": 0.57}])

    resp = client.post("/ogc/getWealthMomentsTable",
                       json={"country_id": "ETH", "casename": "c1", "base_run": "base"})

    assert resp.status_code == 200
    assert "Data" not in resp.get_json()[0]
    # Nothing is asked of the worker: it supplies the blanks itself.
    argv = captured["argv"]
    assert "--args-json" not in argv or "data_moments" not in argv[
        argv.index("--args-json") + 1
    ]

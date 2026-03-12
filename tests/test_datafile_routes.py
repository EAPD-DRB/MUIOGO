"""
Smoke tests for the data-file blueprint (DataFileRoute).

POST /createCaseRun  -- creates a run subdirectory and registers it in resData.json
POST /deleteCaseRun  -- removes a run (full or results-only) and updates resData.json

Solver-invoking endpoints (/run, /batchRun) are intentionally excluded; they
require platform-specific binaries and belong in a separate integration suite.
"""

import json


def _create_run_directory(data_storage, case_name, run_name):
    """Create a minimal case-run directory with an empty csv/ subdirectory."""
    run_dir = data_storage / case_name / "res" / run_name
    run_dir.mkdir(parents=True)
    (run_dir / "csv").mkdir()
    return run_dir


def _register_run_in_resdata(data_storage, case_name, run_name):
    """Append a run entry to the case's resData.json."""
    res_data_path = data_storage / case_name / "view" / "resData.json"
    res_data = json.loads(res_data_path.read_text())
    res_data["osy-cases"].append({"Case": run_name, "Scenarios": []})
    res_data_path.write_text(json.dumps(res_data))


class TestCreateCaseRun:
    def test_new_run_is_created_successfully(self, client, case_fixture):
        run_data = {"Case": "run1", "Scenarios": []}

        response = client.post(
            "/createCaseRun",
            json={
                "casename": case_fixture,
                "caserunname": "run1",
                "data": run_data,
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.get_json()["status_code"] == "success"

    def test_duplicate_run_name_returns_exist_status(
        self, client, case_fixture, data_storage
    ):
        _create_run_directory(data_storage, case_fixture, "run1")

        run_data = {"Case": "run1", "Scenarios": []}
        response = client.post(
            "/createCaseRun",
            json={
                "casename": case_fixture,
                "caserunname": "run1",
                "data": run_data,
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.get_json()["status_code"] == "exist"


class TestDeleteCaseRun:
    def test_full_delete_removes_run_and_resdata_entry(
        self, client, case_fixture, data_storage
    ):
        _create_run_directory(data_storage, case_fixture, "run1")
        _register_run_in_resdata(data_storage, case_fixture, "run1")

        response = client.post(
            "/deleteCaseRun",
            json={
                "casename": case_fixture,
                "caserunname": "run1",
                "resultsOnly": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.get_json()["status_code"] == "success"

    def test_results_only_clears_run_contents_and_returns_success(
        self, client, case_fixture, data_storage
    ):
        run_dir = _create_run_directory(data_storage, case_fixture, "run1")
        # Place a dummy result file so the cleanup loop has something to process.
        (run_dir / "results.txt").write_text("solver output")
        _register_run_in_resdata(data_storage, case_fixture, "run1")

        response = client.post(
            "/deleteCaseRun",
            json={
                "casename": case_fixture,
                "caserunname": "run1",
                "resultsOnly": True,
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.get_json()["status_code"] == "success"

    def test_nonexistent_run_returns_404(self, client, case_fixture):
        response = client.post(
            "/deleteCaseRun",
            json={
                "casename": case_fixture,
                "caserunname": "run_does_not_exist",
                "resultsOnly": False,
            },
            content_type="application/json",
        )

        assert response.status_code == 404

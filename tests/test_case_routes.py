"""
Smoke tests for the case management blueprint (CaseRoute).

GET  /getCases      -- scans DataStorage and returns a list of case directory names
POST /getDesc       -- reads osy-desc from a case's genData.json
POST /copyCase      -- copies a case directory; guarded by session match
POST /deleteCase    -- removes a case directory; guarded by session match
POST /getResultCSV  -- lists CSV files in a case run's csv/ subdirectory
"""

import json


class TestGetCases:
    def test_returns_empty_list_when_storage_has_no_cases(self, client):
        response = client.get("/getCases")

        assert response.status_code == 200
        assert response.get_json() == []

    def test_returns_case_name_when_case_directory_exists(self, client, case_fixture):
        response = client.get("/getCases")

        assert response.status_code == 200
        assert case_fixture in response.get_json()


class TestGetDesc:
    def test_returns_description_for_existing_case(self, client, case_fixture):
        response = client.post(
            "/getDesc",
            json={"casename": case_fixture},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["desc"] == "A test case"

    def test_missing_case_returns_404(self, client):
        response = client.post(
            "/getDesc",
            json={"casename": "no_such_case"},
            content_type="application/json",
        )

        assert response.status_code == 404


class TestCopyCase:
    def test_authorized_copy_succeeds(self, authed_client):
        test_client, case_name = authed_client

        response = test_client.post(
            "/copyCase",
            json={"casename": case_name},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.get_json()["status_code"] == "success"

    def test_no_active_session_returns_403(self, client, case_fixture):
        response = client.post(
            "/copyCase",
            json={"casename": case_fixture},
            content_type="application/json",
        )

        assert response.status_code == 403

    def test_session_case_mismatch_returns_403(self, authed_client):
        test_client, _ = authed_client

        response = test_client.post(
            "/copyCase",
            json={"casename": "different_case"},
            content_type="application/json",
        )

        assert response.status_code == 403

    def test_copy_destination_already_exists_returns_warning(
        self, authed_client, data_storage
    ):
        test_client, case_name = authed_client
        # Pre-create the destination so copytree would fail.
        (data_storage / (case_name + "_copy")).mkdir()

        response = test_client.post(
            "/copyCase",
            json={"casename": case_name},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.get_json()["status_code"] == "warning"


class TestDeleteCase:
    def test_authorized_delete_succeeds(self, authed_client):
        test_client, case_name = authed_client

        response = test_client.post(
            "/deleteCase",
            json={"casename": case_name},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.get_json()["status_code"] == "success_session"

    def test_no_active_session_returns_403(self, client, case_fixture):
        response = client.post(
            "/deleteCase",
            json={"casename": case_fixture},
            content_type="application/json",
        )

        assert response.status_code == 403


class TestGetResultCSV:
    def test_returns_csv_filenames_when_directory_exists(
        self, client, case_fixture, data_storage
    ):
        csv_dir = data_storage / case_fixture / "res" / "run1" / "csv"
        csv_dir.mkdir(parents=True)
        (csv_dir / "TotalCapacityAnnual.csv").touch()
        (csv_dir / "NewCapacity.csv").touch()

        response = client.post(
            "/getResultCSV",
            json={"casename": case_fixture, "caserunname": "run1"},
            content_type="application/json",
        )

        assert response.status_code == 200
        csv_files = response.get_json()
        assert "TotalCapacityAnnual.csv" in csv_files
        assert "NewCapacity.csv" in csv_files

    def test_missing_csv_directory_returns_empty_list(self, client, case_fixture):
        response = client.post(
            "/getResultCSV",
            json={"casename": case_fixture, "caserunname": "nonexistent_run"},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.get_json() == []

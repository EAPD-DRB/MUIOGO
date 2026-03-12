"""
Smoke tests for session management endpoints.

GET  /getSession  -- returns the name of the currently active case or null
POST /setSession  -- sets the active case; validates the case directory exists
"""


class TestGetSession:
    def test_returns_null_when_no_session_is_active(self, client):
        response = client.get("/getSession")

        assert response.status_code == 200
        assert response.get_json()["session"] is None

    def test_returns_case_name_when_session_is_active(self, authed_client):
        test_client, case_name = authed_client

        response = test_client.get("/getSession")

        assert response.status_code == 200
        assert response.get_json()["session"] == case_name


class TestSetSession:
    def test_valid_case_name_stores_session(self, client, case_fixture):
        response = client.post(
            "/setSession",
            json={"case": case_fixture},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.get_json()["osycase"] == case_fixture

    def test_null_case_clears_active_session(self, authed_client):
        test_client, _ = authed_client

        response = test_client.post(
            "/setSession",
            json={"case": None},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.get_json()["osycase"] is None

    def test_nonexistent_case_directory_returns_404(self, client):
        response = client.post(
            "/setSession",
            json={"case": "case_that_does_not_exist"},
            content_type="application/json",
        )

        assert response.status_code == 404

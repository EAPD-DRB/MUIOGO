"""
Tests for /getSession and /setSession.

Checks the basic contract: fresh session is null, bad case name gets rejected,
missing fields don't blow up with a 500.
"""


def test_get_session_returns_200(client):
    resp = client.get("/getSession")
    assert resp.status_code == 200


def test_get_session_is_null_when_no_session_set(client):
    """Before anything is set, the session should come back as null."""
    resp = client.get("/getSession")
    data = resp.get_json()
    assert "session" in data
    assert data["session"] is None


def test_set_session_nonexistent_case_returns_404(client):
    """Trying to set a case that doesn't exist on disk should get a 404, not a 500."""
    resp = client.post("/setSession", json={"case": "__nonexistent_test_xyz__"})
    assert resp.status_code == 404


def test_set_session_missing_field_returns_404(client):
    """Sending an empty body should not crash the server -- the route handles the KeyError."""
    resp = client.post("/setSession", json={})
    assert resp.status_code == 404


def test_set_session_wrong_method_returns_405(client):
    """Only POST should work here."""
    resp = client.delete("/setSession")
    assert resp.status_code == 405

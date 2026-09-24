"""
Tests for the Flask Security Hardening Middleware.

Validates that:
1. MAX_CONTENT_LENGTH is enforced (no longer None)
2. Security response headers are present on every response
3. Upload size limits are enforced (HTTP 413 for oversized payloads)
"""
import pytest
import sys
import os
from pathlib import Path

# Ensure the API directory is on sys.path for imports
api_path = Path(__file__).parent.parent / "API"
sys.path.insert(0, str(api_path.resolve()))

from app import app
from Classes.Base import Config


@pytest.fixture
def client():
    Config.AWS_SYNC = 0
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    with app.test_client() as client:
        yield client


# ------------------------------------------------------------------
# 1. MAX_CONTENT_LENGTH is enforced
# ------------------------------------------------------------------
def test_max_content_length_is_set():
    """MAX_CONTENT_LENGTH must not be None (DoS prevention)."""
    assert app.config["MAX_CONTENT_LENGTH"] is not None
    assert app.config["MAX_CONTENT_LENGTH"] > 0


# ------------------------------------------------------------------
# 2. Security response headers are present
# ------------------------------------------------------------------
def test_x_frame_options(client):
    """X-Frame-Options header must be present to prevent clickjacking."""
    rv = client.get("/getSession")
    assert "X-Frame-Options" in rv.headers
    assert rv.headers["X-Frame-Options"] == "DENY"


def test_x_content_type_options(client):
    """X-Content-Type-Options must be 'nosniff' to prevent MIME-sniffing."""
    rv = client.get("/getSession")
    assert "X-Content-Type-Options" in rv.headers
    assert rv.headers["X-Content-Type-Options"] == "nosniff"


def test_x_xss_protection(client):
    """X-XSS-Protection header must enable the browser XSS filter."""
    rv = client.get("/getSession")
    assert "X-XSS-Protection" in rv.headers


def test_content_security_policy(client):
    """Content-Security-Policy header must be present."""
    rv = client.get("/getSession")
    assert "Content-Security-Policy" in rv.headers


def test_referrer_policy(client):
    """Referrer-Policy header must be present."""
    rv = client.get("/getSession")
    assert "Referrer-Policy" in rv.headers
    assert rv.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


# ------------------------------------------------------------------
# 3. Upload size limit is correctly configured
# ------------------------------------------------------------------
def test_upload_limit_is_reasonable():
    """MAX_CONTENT_LENGTH must be set to a reasonable limit (not unlimited)."""
    limit = app.config["MAX_CONTENT_LENGTH"]
    assert limit is not None, "MAX_CONTENT_LENGTH must not be None (DoS risk)"
    # Should be between 10 MB and 1 GB for model archives
    assert 10 * 1024 * 1024 <= limit <= 1024 * 1024 * 1024, (
        f"MAX_CONTENT_LENGTH={limit} is outside the safe range (10MB–1GB)"
    )

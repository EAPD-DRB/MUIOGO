"""
Fixtures shared across all tests.

API/ is on the path via pyproject.toml so imports just work -- no sys.path hacks needed.
"""

import pytest

from app import app as _flask_app


@pytest.fixture(scope="session")
def app():
    """
    The Flask app, set up for testing.

    TESTING is kept False on purpose. When it's True, Flask re-raises exceptions
    instead of returning 500, which means tests would crash instead of asserting
    the right status code. We want real HTTP responses, not stack traces.
    """
    _flask_app.config.update(
        {
            "SECRET_KEY": "test-secret-key",
            "TESTING": False,
        }
    )
    yield _flask_app


@pytest.fixture()
def client(app):
    """Return a test client for the Flask app."""
    with app.test_client() as c:
        yield c

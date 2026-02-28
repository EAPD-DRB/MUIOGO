import pytest
from API.app import app
from API.Classes.Base import Config

@pytest.fixture
def client():
    # Make sure we don't try to sync to AWS during tests
    Config.AWS_SYNC = 0
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Test that the application starts and serves the frontend."""
    # We check /getSession as a basic API liveness probe
    rv = client.get('/getSession')
    # Because we haven't set a session, it returns a 200 with session: null
    assert rv.status_code == 200
    assert b'session' in rv.data

def test_cors_headers(client):
    """Test that CORS headers are appended to requests."""
    rv = client.get('/getSession')
    assert 'Access-Control-Allow-Origin' in rv.headers
    assert 'Access-Control-Allow-Credentials' in rv.headers

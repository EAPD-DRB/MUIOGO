import sys
import os
import threading
import time
import pytest
import requests
from werkzeug.serving import make_server

# Ensure API module can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from API.app import app

class ServerThread(threading.Thread):
    def __init__(self, host='127.0.0.1', port=5003):
        threading.Thread.__init__(self)
        # Disable werkzeug logging to keep test output clean
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        
        self.server = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
        self.ctx.pop()

@pytest.fixture(scope="session", autouse=True)
def live_server():
    """Starts the Flask server in a background thread for Playwright tests."""
    host = '127.0.0.1'
    port = 5003
    url = f"http://{host}:{port}"
    
    server = ServerThread(host, port)
    server.daemon = True
    server.start()
    
    # Wait for the server to be responsive (15 seconds max for slow CI runners)
    for _ in range(30):
        try:
            # Polling the getSession route to ensure app context and routing are up
            r = requests.get(f"{url}/getSession")
            if r.status_code in (200, 400, 404):  # Any valid HTTP response means it's up
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.5)
    else:
        server.shutdown()
        server.join(timeout=2)
        raise RuntimeError("Failed to start the test Flask server.")

    yield url
    
    server.shutdown()
    server.join(timeout=2)

@pytest.fixture(scope="session")
def base_url(live_server):
    """Overrides the pytest-playwright base_url fixture."""
    return live_server

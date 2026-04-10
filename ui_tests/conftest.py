import os
import sys
import time
import pytest
import requests
import subprocess

@pytest.fixture(scope="session")
def live_server():
    """
    Spins up the Flask backend server on port 5003 for Playwright UI tests.
    Polls the /health endpoint until it is ready (max 15 seconds) before
    yielding control to the test runners.
    """
    env = os.environ.copy()
    env["PORT"] = "5003"
    env["HEROKU_DEPLOY"] = "0"

    print("\nStarting Flask server for E2E tests on port 5003...")
    
    # Start the Flask app
    process = subprocess.Popen(
        [sys.executable, "API/app.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    base_url = "http://127.0.0.1:5003"
    api_ready = False
    
    # Poll for 15 seconds
    for _ in range(30):
        try:
            res = requests.get(f"{base_url}/health", timeout=1)
            if res.status_code == 200:
                api_ready = True
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.5)

    if not api_ready:
        process.terminate()
        outs, errs = process.communicate(timeout=2)
        raise RuntimeError(f"Flask server at {base_url} did not start within 15 seconds.\nStderr: {errs}")

    yield base_url

    print("\nShutting down Flask server...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()

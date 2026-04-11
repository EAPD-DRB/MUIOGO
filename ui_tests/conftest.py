"""
conftest.py — pytest fixture that starts the MUIOGO Flask server for Playwright E2E tests.

Strategy: Run Waitress in a daemon thread *inside* the pytest process.

Why not subprocess?
  subprocess + Flask dev server (app.run) hangs serving static files on Python 3.12 Windows.

Why Waitress (not Flask dev server)?
  - Proven to work: it's how the app runs in production.
  - Threaded properly: 16 threads prevent exhaustion from Playwright's burst of concurrent
    JS/CSS asset requests when loading index.html.

Why daemon thread (not subprocess)?
  - Avoids all cross-platform CWD / sys.path / env-var inheritance issues.
  - The thread is killed automatically when the pytest session ends.
"""
import os
import sys
import time
import threading

import pytest
import requests

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))          # ui_tests/
_PROJECT_ROOT = os.path.dirname(_HERE)                       # MUIOGO/
_API_DIR = os.path.join(_PROJECT_ROOT, "API")                # MUIOGO/API/

TEST_PORT = 5003
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"


def _run_waitress(app) -> None:
    """Target function for the daemon thread: serve with Waitress."""
    from waitress import serve
    serve(
        app,
        host="127.0.0.1",
        port=TEST_PORT,
        threads=16,          # handles burst of parallel asset requests from Playwright
        channel_timeout=10,  # release idle connections quickly between test sessions
    )


@pytest.fixture(scope="session")
def live_server():
    """
    Start the Flask app in a Waitress daemon thread on port 5003.

    The fixture:
      1. Configures the environment (HEROKU_DEPLOY=0 → local file sessions, no PostgreSQL).
      2. Adds API/ to sys.path and changes CWD to project root — mirrors how the app
         is normally launched, so Config.WEBAPP_PATH resolves to the correct WebAPP/ dir.
      3. Imports the Flask `app` object and hands it to Waitress running in a daemon thread.
      4. Polls /health for up to 15 seconds before yielding to the tests.
      5. Restores CWD on teardown (the daemon thread is killed automatically).
    """
    # 1. Configure environment BEFORE importing the app so Config reads correct values.
    os.environ["HEROKU_DEPLOY"] = "0"
    os.environ["PORT"] = str(TEST_PORT)

    # 2. Add API/ to sys.path so `from app import app` and its internal imports work.
    if _API_DIR not in sys.path:
        sys.path.insert(0, _API_DIR)

    # 3. Change CWD to project root — same as when the app is launched normally.
    original_cwd = os.getcwd()
    os.chdir(_PROJECT_ROOT)

    try:
        import mimetypes
        mimetypes.add_type("application/javascript", ".js")

        # Import the Flask application (app-level Config is read here).
        from app import app  # noqa: E402  (import after path manipulation)

        thread = threading.Thread(
            target=_run_waitress,
            args=(app,),
            daemon=True,          # killed automatically when pytest exits
            name="muiogo-test-server",
        )
        thread.start()

        # 4. Poll /health until the server is ready (max 15 s).
        ready = False
        for _ in range(30):
            try:
                r = requests.get(f"{BASE_URL}/health", timeout=1)
                if r.status_code == 200:
                    ready = True
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(0.5)

        if not ready:
            raise RuntimeError(
                f"Flask test server at {BASE_URL} did not start within 15 seconds."
            )

        yield BASE_URL

    finally:
        # 5. Restore CWD for safety (daemon thread dies with the process).
        os.chdir(original_cwd)

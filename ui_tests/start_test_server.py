"""
Test-specific Flask server entrypoint for Playwright E2E tests.

Uses Flask's built-in threaded WSGI server (not Waitress) to reliably handle
the burst of concurrent asset requests that Playwright fires when loading
index.html — jQuery, Wijmo, SmartAdmin, Plotly etc load in parallel.

Waitress defaults to 4 threads which gets saturated on Windows causing all
subsequent requests to hang. Flask's threaded=True uses a new thread per
connection which correctly handles concurrent browser asset loading.
"""
import os
import sys
import mimetypes

# Resolve paths relative to this file
_ui_tests_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_ui_tests_dir)
_api_dir = os.path.join(_project_root, "API")

# API-internal imports (Config, Routes, etc.) use non-package style
sys.path.insert(0, _api_dir)

# Ensure CWD is the project root so Flask finds WebAPP/ for templates/static
os.chdir(_project_root)

from app import app  # noqa: E402  (after path manipulation)

mimetypes.add_type("application/javascript", ".js")

port = int(os.environ.get("PORT", 5003))

app.run(
    host="127.0.0.1",
    port=port,
    threaded=True,       # one thread per connection — handles burst asset loads
    use_reloader=False,  # never auto-restart inside a test subprocess
    debug=False,
)

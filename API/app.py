from pathlib import Path
import atexit
import logging
import os
import secrets
import signal
import sys
import time
import warnings
from logging.handlers import TimedRotatingFileHandler

# Fail fast: unsupported Python hits cryptic pandas/numpy import errors without this.
SUPPORTED_PYTHON_MIN = (3, 10)
SUPPORTED_PYTHON_MAX = (3, 13)

if not (SUPPORTED_PYTHON_MIN <= sys.version_info[:2] < SUPPORTED_PYTHON_MAX):
    detected_version = ".".join(str(part) for part in sys.version_info[:3])
    min_str = f"{SUPPORTED_PYTHON_MIN[0]}.{SUPPORTED_PYTHON_MIN[1]}"
    max_str = f"{SUPPORTED_PYTHON_MAX[0]}.{SUPPORTED_PYTHON_MAX[1] - 1}"
    print(
        f"Unsupported Python version: {detected_version}\n"
        f"MUIOGO currently supports Python {min_str} to {max_str} (recommended: 3.11).\n"
        "Use scripts/setup.sh or scripts\\setup.bat with a supported Python installation.",
        file=sys.stderr,
    )
    raise SystemExit(1)

from flask import Flask, jsonify, request, session, render_template
from flask_cors import CORS
from datetime import timedelta
# from pathlib import Path

#import json
from Classes.Base import Config
# from API.Classes.Base.SyncS3 import SyncS3
from Routes.Upload.UploadRoute import upload_api
from Routes.Case.CaseRoute import case_api
from Routes.Case.SyncS3Route import syncs3_api
from Routes.Case.ViewDataRoute import viewdata_api
from Routes.DataFile.DataFileRoute import datafile_api
from Routes.OGCore.OGCoreInstallRoute import ogcore_install_api
from Routes.OGCore.OGCoreRunRoute import ogcore_run_api
from Routes.OGLink.OGLinkRoute import oglink_api
from Routes.Clews.ClewsRoute import clews_api
from Classes.OGCore.InstallJob import InstallJob
from Classes.OGCore.OGCoreCase import OGCoreCase
from Classes.OGCore.RunJob import RunJob
from Classes.Case.CaseImporter import ACCEPTED_CASE_VERSIONS, CURRENT_CASE_VERSION
from Classes.Clews.CountryRegistry import CountryRegistry

def _configure_logging():
    if getattr(_configure_logging, "_configured", False):
        return getattr(_configure_logging, "_log_path", None)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler._muiogo_handler = True
    logger.addHandler(console_handler)

    log_path = None
    try:
        log_path = Config.get_runtime_log_path()
        file_handler = TimedRotatingFileHandler(
            log_path, when="midnight", interval=1, backupCount=7, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler._muiogo_handler = True
        logger.addHandler(file_handler)
    except OSError as exc:
        logger.warning("Runtime log file unavailable. Continuing with console logging only: %s", exc)

    logging.captureWarnings(True)
    warnings.simplefilter("default")

    def log_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error("UNCAUGHT EXCEPTION", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = log_exception

    _configure_logging._configured = True
    _configure_logging._log_path = log_path
    return log_path


RUNTIME_LOG_PATH = _configure_logging()

template_dir = str(Config.WEBAPP_PATH)
static_dir = str(Config.WEBAPP_PATH)

app = Flask(__name__, static_url_path='', static_folder=static_dir,  template_folder=template_dir)

app.permanent_session_lifetime = timedelta(days=5)
secret_key = os.environ.get("MUIOGO_SECRET_KEY", "").strip()
if not secret_key:
    secret_key = secrets.token_hex(32)
    logging.getLogger(__name__).warning(
        "MUIOGO_SECRET_KEY is not configured. Using a temporary in-memory key. "
        "Run setup to create a persistent secret in .env."
    )
app.config['SECRET_KEY'] = secret_key
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config["MAX_CONTENT_LENGTH"] = None

app.register_blueprint(upload_api)
app.register_blueprint(case_api)
app.register_blueprint(viewdata_api)
app.register_blueprint(datafile_api)
app.register_blueprint(syncs3_api)
app.register_blueprint(ogcore_install_api)
app.register_blueprint(ogcore_run_api)
app.register_blueprint(oglink_api)
app.register_blueprint(clews_api)

CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)

# @app.errorhandler(CustomException)
# def handle_invalid_usage(error):
#     response = jsonify(error.to_dict())
#     response.status_code = error.status_code
#     return response

#entry point to frontend
@app.route("/", methods=['GET'])
def home():
    #sync bucket with local storage
    # if Config.AWS_SYNC == 1:
    #     syncS3 = SyncS3()
    #     cases = syncS3.getCasesSyncInit()
    #     for case in cases:
    #         syncS3.downloadSync(case, Config.DATA_STORAGE, Config.S3_BUCKET)
    #     #downoload param file from S3 bucket
    #     syncS3.downloadSync('Parameters.json', Config.DATA_STORAGE, Config.S3_BUCKET)
    return render_template('index.html', api_base_url=Config.API_BASE_URL)


@app.route("/getSession", methods=['GET'])
def getSession():
    try:
        ses = session.get('osycase', None) or None
        response = {
            "session":ses
        }
        return jsonify(response), 200
    except( KeyError ):
        return jsonify('No selected parameters!'), 404

@app.route("/getVersion", methods=['GET'])
def getVersion():
    """The case-schema version this MUIOGO writes, and every version its importer
    accepts. Lets a client (an installer, a script) check compatibility before
    sending an archive, instead of learning from a failed import."""
    return jsonify({
        "muio_version": CURRENT_CASE_VERSION,
        "accepted_case_versions": list(ACCEPTED_CASE_VERSIONS),
        "status_code": "success",
    }), 200


@app.route("/setSession", methods=['POST'])
def setSession():
    try:
        cs = request.json['case']
        if cs is None:
            session.pop('osycase', None)
            return jsonify({"osycase": None}), 200

        if not Path(Config.DATA_STORAGE, cs).is_dir():
            return jsonify({'message': 'Case not found.', 'status_code': 'error'}), 404
        session['osycase'] = cs
        response = {"osycase": session['osycase']}
        return jsonify(response), 200
    except KeyError:
        return jsonify('No selected parameters!'), 404


def _stop_inflight_installs():
    """Cancel any in-flight OG install and wait briefly for it to tear down.

    Installs run in their own process group so cancel/timeout can kill the whole tree;
    that detachment also means a plain server stop would leave them running orphaned.
    Signalling cancel lets the running supervisors kill their trees and record the
    failure. Best-effort and idempotent: called from the shutdown signal handler and
    again from atexit.
    """
    try:
        ids = InstallJob.cancel_all()
        if not ids:
            return
        logging.getLogger(__name__).info(
            "Server stopping: cancelling %d in-flight OG install(s).", len(ids))
        deadline = time.monotonic() + 5.0
        while InstallJob.active_count() and time.monotonic() < deadline:
            time.sleep(0.1)
    except Exception:
        # Shutdown cleanup must never raise out of a signal handler or atexit.
        pass


def _stop_inflight_run():
    """Stop a model run the same way, so its worker tree is not orphaned either.

    A solve is spawned detached for the same reason an install is, so a server stop
    leaves it running unless it is told to stop. Best-effort and idempotent.
    """
    try:
        if RunJob.stop_active():
            logging.getLogger(__name__).info(
                "Server stopping: cancelling the in-flight OG model run.")
    except Exception:
        pass


def _stop_inflight_work():
    """Shutdown cleanup for both long-running OG subprocesses.

    The run goes first: killing it is immediate, while the install cleanup waits up
    to five seconds, and a second Ctrl+C during that wait force-quits. Doing the fast
    one first means an impatient stop still does not orphan the solve.
    """
    _stop_inflight_run()
    _stop_inflight_installs()


def _install_shutdown_handlers():
    """Run install and run cleanup on Ctrl+C / SIGTERM and at normal interpreter exit.

    atexit covers any clean shutdown (including waitress returning on Ctrl+C); the
    signal handlers cover a SIGTERM/SIGINT that would otherwise kill the process before
    atexit can run. On Windows only console Ctrl+C (SIGINT) and clean exits are really
    covered: a service/taskkill stop is uncatchable there, so cleanup then relies on the
    next start's reconcile pass. The handler re-raises the default disposition so the
    process still exits the way that signal normally would, and a second signal during
    the cleanup wait force-quits instead of nesting another wait.
    """
    atexit.register(_stop_inflight_work)

    shutting_down = {"active": False}

    def _handler(signum, _frame):
        if shutting_down["active"]:
            # Second Ctrl+C/SIGTERM while cleanup is running: give up and terminate now.
            signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)
            return
        shutting_down["active"] = True
        _stop_inflight_work()
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError):
            # Not the main thread, or a platform without this signal: skip.
            pass


if __name__ == '__main__':
# if __name__ == 'app':
    #potrebno radi module js importa u index.html ES6 modules
    #Flask.__version__
    import mimetypes
    mimetypes.add_type('application/javascript', '.js')
    port = int(os.environ.get("PORT", 5002))

    # Fail any OG install left mid-flight by a previous restart, so it does not read as
    # installing forever. Runs when the server actually starts, not on mere import. Note:
    # this is tied to launching via `python app.py`; a WSGI loader that imports app:app
    # would need to call this itself.
    InstallJob.reconcile_interrupted_jobs()

    # Cases used to be stored by name alone. Move any left from that layout under
    # their country first, so the reconcile below walks a single consistent shape.
    try:
        OGCoreCase.migrate_flat_cases()
    except Exception:
        logging.getLogger(__name__).warning(
            "Could not migrate flat OG-Core cases at startup.", exc_info=True)

    # Same for a model run the previous process left behind: mark it failed and kill
    # its worker if that process somehow outlived the server.
    try:
        RunJob.reconcile_interrupted_runs()
    except Exception:
        logging.getLogger(__name__).warning(
            "Could not reconcile interrupted runs at startup.", exc_info=True)

    # Stop any running install or solve cleanly when the server is stopped, so their
    # detached process trees are not orphaned. Same deployment assumption as above.
    # Bring the CLEWs case registry in line with DataStorage: cases added by hand
    # are indexed (as unmanaged unless they carry a provenance sidecar), cases
    # removed by hand are dropped. Logs one summary line; never blocks startup.
    CountryRegistry.reconcile_safe()

    # Stop any running install cleanly when the server is stopped, so its detached
    # process tree is not orphaned. Same deployment assumption as reconcile above.
    _install_shutdown_handlers()

    def print_startup_info(host, current_port, server_name):
        mode = 'local' if Config.HEROKU_DEPLOY == 0 else 'heroku'
        access_host = '127.0.0.1' if host == '0.0.0.0' else host
        print("MUIOGO API starting...")
        print(f"Server: {server_name}")
        print(f"Mode: {mode}")
        print(f"Host: {host}")
        print(f"Port: {current_port}")
        print(f"Open: http://{access_host}:{current_port}")

    if Config.HEROKU_DEPLOY == 0: 
        #localhost
        #app.run(host='127.0.0.1', port=port, debug=True)
        #waitress server
        #prod server
        from waitress import serve
        host = '127.0.0.1'
        print_startup_info(host, port, 'waitress')
        serve(app, host=host, port=port)
    else:
        #HEROKU
        host = '0.0.0.0'
        print_startup_info(host, port, 'flask-dev')
        app.run(host=host, port=port, debug=True)
        #app.run(host='127.0.0.1', port=port, debug=True)

"""CLEWs country install + registry endpoints.

All routes live under /clews. This is the CLEWs-side counterpart of the /ogc layer:
where /ogc installs CODE (an OG model repo with its own venv), /clews installs DATA
(verified case archives extracted into DataStorage through the same CaseImporter
pipeline the browser upload uses).

DataStorage stays the source of truth for which cases exist; the registry adds
provenance and is reconciled against a directory scan on every read, so cases
added or removed by hand are picked up without any extra action. That is also why
there is no unregister endpoint: the index follows the disk, so removing a case
is /deleteCase, and there is nothing else to forget.
"""
import re
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request

from Classes.Clews.ClewsInstallJob import ClewsInstallJob
from Classes.Clews.ClewsInstaller import ClewsInstaller
from Classes.Clews.CountryCatalog import CountryCatalog
from Classes.Clews.CountryManifest import (
    CountrySource,
    ManifestError,
    parse_github_url,
    select_vintage,
)
from Classes.Clews.CountryRegistry import CountryRegistry
from Classes.Clews.Provenance import Provenance

clews_api = Blueprint("ClewsRoute", __name__, url_prefix="/clews")

_INSTALL_ID_RE = re.compile(r"^clews_\d{4}_\d{2}_\d{2}_\d{3}$")
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


# ── small helpers (same conventions as the /ogc routes) ──────────────────────
def _err(message, http=400, status="error"):
    return jsonify({"message": message, "status_code": status}), http


def _blocked_cross_site():
    """Refuse a state-changing request that a cross-site page drove via the browser.

    A browser always attaches an Origin header on a cross-origin POST, so if one is
    present it must be the local app. Non-browser callers (the desktop shell, curl,
    tests) send no Origin and are allowed, matching the app's local-only model.
    """
    origin = request.headers.get("Origin")
    if origin:
        host = urlparse(origin).hostname
        if host not in _LOCAL_HOSTS:
            return _err("Cross-site request refused.", http=403)
    return None


def _body():
    return request.get_json(silent=True)


def _source_from_request(data):
    """Build a CountrySource from a request body. Raises ManifestError."""
    source_type = data.get("source_type")
    if source_type == "catalog":
        entry = CountryCatalog.find_entry(data.get("catalog_key"))
        if entry is None:
            raise ManifestError(
                f"'{data.get('catalog_key')}' is not in the country catalogue. "
                "Use a Git URL instead, or configure a catalogue register.")
        return CountrySource(source_type="repo_url", repo_url=entry["repo_url"],
                             ref=data.get("ref"),
                             iso3=entry.get("iso3") or None,
                             name=entry.get("country_name") or None)
    if source_type == "repo_url":
        return CountrySource(source_type="repo_url", repo_url=data.get("repo_url"),
                             ref=data.get("ref"))
    if source_type == "local_path":
        return CountrySource(source_type="local_path",
                             local_path=data.get("local_path"))
    raise ManifestError("source_type must be one of: catalog, repo_url, local_path.")


def _country_key(source):
    """What serializes concurrent installs: one at a time per source."""
    if source.source_type == "local_path":
        return f"local:{source.local_path}"
    return f"github:{source.owner}/{source.repo}"


# ── 1. catalogue ──────────────────────────────────────────────────────────────
@clews_api.route("/getCountryCatalog", methods=["GET"])
def getCountryCatalog():
    countries, source = CountryCatalog.get_catalog_with_state()
    return jsonify({
        "status_code": "success",
        "countries": countries,
        "catalog_source": source,  # live | cache | none
    }), 200


# ── 2. installed list ─────────────────────────────────────────────────────────
@clews_api.route("/getInstalledCountries", methods=["GET"])
def getInstalledCountries():
    """Every case on this machine with its provenance, reconciled against disk.

    Each record carries managed=True (installed through a tracked path, provenance
    sidecar present) or managed=False (install_state "unmanaged": added by hand or
    predating this layer). The reconcile summary says what this call just changed.
    """
    summary = CountryRegistry.reconcile()
    return jsonify({
        "status_code": "success",
        "cases": CountryRegistry.list_all(),
        "reconcile": summary,
    }), 200


# ── 3. pre-flight: read the manifest, return the install menu ────────────────
@clews_api.route("/inspectSource", methods=["POST"])
def inspectSource():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = _body()
    if data is None:
        return _err("Request body must be valid JSON.")
    try:
        source = _source_from_request(data)
        menu = ClewsInstaller.inspect(source)
    except ManifestError as exc:
        return _err(str(exc))
    menu["status_code"] = "success"
    return jsonify(menu), 200


# ── 4. install ────────────────────────────────────────────────────────────────
@clews_api.route("/installCountry", methods=["POST"])
def installCountry():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = _body()
    if data is None:
        return _err("Request body must be valid JSON.")
    try:
        source = _source_from_request(data)
    except ManifestError as exc:
        return _err(str(exc))

    casenames = data.get("cases")
    if casenames is not None and (
            not isinstance(casenames, list)
            or not all(isinstance(c, str) and c for c in casenames)):
        return _err("cases must be a list of case names.")

    job = ClewsInstallJob.start_install(
        source=source,
        country_key=_country_key(source),
        vintage_id=data.get("vintage") or None,
        casenames=casenames or None,
    )
    if job is None:
        return _err("An install from this source is already running.")
    return jsonify({
        "status_code": "success",
        "install_id": job["install_id"],
        "install_state": job["install_state"],
        "message": "Country install started.",
    }), 200


# ── 5. install status ─────────────────────────────────────────────────────────
@clews_api.route("/getInstallStatus", methods=["GET"])
def getInstallStatus():
    install_id = request.args.get("install_id")
    if not install_id:
        return _err("Missing required query value: install_id")
    if not _INSTALL_ID_RE.match(install_id):
        return _err("Invalid install_id.")
    job = ClewsInstallJob.get_status(install_id)
    if job is None:
        return _err("No install job with that id.", http=404)
    return jsonify({
        "status_code": "success",
        "install_id": job["install_id"],
        "country_key": job.get("country_key"),
        "install_state": job["install_state"],
        "install_stage": job["install_stage"],
        "progress_label": job["progress_label"],
        "results": job.get("results"),
        "log_tail": job.get("log_tail", []),
        "error": job.get("error"),
    }), 200


# ── 6. update check ───────────────────────────────────────────────────────────
@clews_api.route("/checkCountryUpdate", methods=["POST"])
def checkCountryUpdate():
    """Compare one installed case's archive checksum against its source, now.

    Check-only, never applies anything: the source's manifest is re-read at the
    recorded ref and the published checksum for this case's archive is compared
    with the checksum recorded at install time.
    """
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = _body()
    if data is None:
        return _err("Request body must be valid JSON.")
    casename = data.get("casename")
    if not casename:
        return _err("Missing required field: casename")

    sidecar = Provenance.read(casename)
    if sidecar is None:
        return _err("That case has no provenance record, so there is nothing to "
                    "compare against. Only cases installed from a source can be "
                    "checked.", http=404)
    src = sidecar.get("source") or {}
    if src.get("type") not in ("repo_url", "local_path"):
        return _err("This case was not installed from a repository or folder, so "
                    "it cannot be checked for updates.")
    archive = sidecar.get("archive") or {}
    known = archive.get("sha256_declared") or archive.get("sha256_computed")
    if not (archive.get("name") and known and src.get("vintage")):
        return _err("This case's provenance does not record enough to compare "
                    "(archive name, checksum and vintage are needed).")

    try:
        source = CountrySource(source_type=src["type"], repo_url=src.get("repo_url"),
                               ref=src.get("ref"), local_path=src.get("local_path"))
        manifest = source.load_manifest()
        vintage = select_vintage(manifest, src["vintage"])
        checksums = source.load_checksums(vintage)
    except ManifestError as exc:
        return _err(str(exc))

    published = checksums.get(archive["name"])
    if not published:
        return _err(f"The source no longer publishes a checksum for "
                    f"{archive['name']} in vintage {src['vintage']}.", http=404)

    update_available = published != known
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = CountryRegistry.get(casename)
    if record is not None:
        record["last_checked_at"] = now
        record["update_available"] = update_available
        CountryRegistry.upsert(record)
    return jsonify({
        "status_code": "success",
        "casename": casename,
        "update_available": update_available,
        "installed_sha256": known,
        "published_sha256": published,
        "message": ("A newer archive is published for this case."
                    if update_available else "This case is up to date."),
    }), 200


# ── 7. cancel a running install ───────────────────────────────────────────────
@clews_api.route("/cancelInstall", methods=["POST"])
def cancelInstall():
    blocked = _blocked_cross_site()
    if blocked:
        return blocked
    data = _body()
    if data is None:
        return _err("Request body must be valid JSON.")
    install_id = data.get("install_id")
    if not install_id or not isinstance(install_id, str) \
            or not _INSTALL_ID_RE.match(install_id):
        return _err("Invalid install_id.")
    if not ClewsInstallJob.cancel(install_id):
        return _err("No running install with that id to cancel.", http=404)
    return jsonify({
        "status_code": "success",
        "install_id": install_id,
        "message": "Cancellation requested.",
    }), 200

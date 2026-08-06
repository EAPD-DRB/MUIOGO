"""CLEWs country install + registry endpoints.

All routes live under /clews. This is the CLEWs-side counterpart of the /ogc layer:
where /ogc installs CODE (an OG model repo with its own venv), /clews installs DATA
(verified case archives extracted into DataStorage through the same CaseImporter
pipeline the browser upload uses).

DataStorage stays the source of truth for which cases exist; the registry adds
provenance and is reconciled against a directory scan on every read, so cases
added or removed by hand are picked up without any extra action.
"""
from flask import Blueprint, jsonify

from Classes.Clews.CountryRegistry import CountryRegistry

clews_api = Blueprint("ClewsRoute", __name__, url_prefix="/clews")


# ── installed list ────────────────────────────────────────────────────────────
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

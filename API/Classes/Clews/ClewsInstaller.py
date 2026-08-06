"""Inspect a CLEWs country source, and install its cases through the shared importer.

Where the OG Installer builds a code environment (clone + uv sync + import check),
this installs DATA: fetch the declared archives, verify each against the vintage's
published SHA256SUMS (hard fail on mismatch -- an unverifiable model does not get
installed), then hand each archive to CaseImporter.import_zip -- the exact pipeline
the browser upload runs -- which also writes the provenance sidecar.

Downloads stage under Config.CLEWS_DOWNLOADS_DIR, never in DataStorage, so a
partial download can never appear in the case picker. Name collisions are not
resolved here: an existing case reports already_exists (same as an upload) and is
left untouched; replacing a case is the user's own deliberate delete + reinstall.
"""
import os
import shutil
from pathlib import Path

from Classes.Base import Config
from Classes.Case.CaseImporter import (
    ACCEPTED_CASE_VERSIONS,
    CURRENT_CASE_VERSION,
    CaseImporter,
)
from Classes.Clews.CountryManifest import (
    CountrySource,
    InstallCancelled,
    ManifestError,
    select_cases,
    select_vintage,
)
from Classes.Clews.Provenance import sha256_of


def _version_tuple(text):
    """'5.6' -> (5, 6); tolerant of junk (None on failure)."""
    try:
        return tuple(int(part) for part in str(text).strip().split("."))
    except (ValueError, AttributeError):
        return None


def version_gate(vintage):
    """None if this MUIOGO may install the vintage, else a refusal message."""
    declared = vintage.get("muio_min_version")
    if not declared:
        return None
    need, have = _version_tuple(declared), _version_tuple(CURRENT_CASE_VERSION)
    if need is None:
        return None  # an unparseable declaration must not brick the install
    if have < need:
        return (f"This vintage needs MUIO {declared} or newer; this MUIOGO "
                f"writes case version {CURRENT_CASE_VERSION}.")
    return None


class ClewsInstaller:
    # ── pre-flight ───────────────────────────────────────────────────────────
    @staticmethod
    def inspect(source):
        """Read the manifest and return the full install menu, without downloading.

        Each case in each vintage is annotated with whether a case of that name
        already exists in DataStorage; each vintage with whether this MUIOGO's
        version passes its gate. This is what lets a client show a real menu
        before anything heavy happens.
        """
        manifest = source.load_manifest()
        vintages = []
        for v in manifest["vintages"]:
            entry = {
                "id": v["id"],
                "recommended": bool(v.get("recommended")),
                "dir": v["dir"],
                "muio_min_version": v.get("muio_min_version"),
                "version_gate": version_gate(v),
                "cases": [],
            }
            for c in v["cases"]:
                entry["cases"].append({
                    "case": c["case"],
                    "archive": c["archive"],
                    "role": c.get("role"),
                    "recommended": bool(c.get("recommended")),
                    "already_exists": Path(Config.DATA_STORAGE, c["case"]).is_dir(),
                })
            vintages.append(entry)
        return {
            "iso3": manifest["iso3"],
            "un_code": manifest.get("un_code"),
            "name": manifest["name"],
            "og": manifest.get("og"),
            "source": source.describe(),
            "muio_version": CURRENT_CASE_VERSION,
            "accepted_case_versions": list(ACCEPTED_CASE_VERSIONS),
            "vintages": vintages,
        }

    # ── the install work function (runs on a ClewsInstallJob thread) ─────────
    @classmethod
    def run_install(cls, *, source, vintage_id=None, casenames=None,
                    staging_dir, progress, log, cancel):
        """Fetch, verify and import the selected cases. Returns a result dict.

        {"ok": bool, "iso3", "results": [{case, archive, status, message}...],
         "error": ...}. status per case: installed | already_exists | failed.
        The job is ok if at least one case installed and none FAILED (an
        already-existing case is a warning, not a failure -- same as an upload).
        """
        progress("manifest", "Reading the country manifest")
        manifest = source.load_manifest()
        vintage = select_vintage(manifest, vintage_id)
        gate = version_gate(vintage)
        if gate:
            return {"ok": False, "error": gate}
        cases = select_cases(vintage, casenames)
        log(f"{manifest['name']} ({manifest['iso3']}), vintage {vintage['id']}: "
            f"{len(cases)} case(s) selected.")

        progress("checksums", "Reading the published checksums")
        checksums = source.load_checksums(vintage)

        staging = Path(staging_dir)
        staging.mkdir(parents=True, exist_ok=True)
        results = []
        try:
            for c in cases:
                if cancel.is_set():
                    raise InstallCancelled()
                case_name, archive = c["case"], c["archive"]
                declared = checksums.get(archive)

                if Path(Config.DATA_STORAGE, case_name).is_dir():
                    log(f"{case_name}: already exists; leaving it untouched.")
                    results.append({"case": case_name, "archive": archive,
                                    "status": "already_exists",
                                    "message": f"Model {case_name} already exists!"})
                    continue

                progress("download", f"Downloading {archive}")
                log(f"Downloading {archive}...")
                local = staging / archive
                source.download_archive(f"{vintage['dir']}/{archive}", str(local),
                                        cancel=cancel)

                progress("verify", f"Verifying {archive}")
                if declared:
                    computed = sha256_of(local)
                    if computed != declared:
                        # Hard fail: an archive that does not match its published
                        # checksum must never reach DataStorage.
                        results.append({
                            "case": case_name, "archive": archive, "status": "failed",
                            "message": (f"Checksum mismatch for {archive}: the "
                                        "download does not match the repository's "
                                        "SHA256SUMS. Nothing was installed from it."),
                        })
                        log(f"{archive}: sha256 mismatch (expected {declared[:12]}..., "
                            f"got {computed[:12]}...).")
                        continue
                    log(f"{archive}: checksum verified.")
                else:
                    log(f"{archive}: no published checksum; recording the computed "
                        "hash in the case's provenance.")

                progress("import", f"Importing {case_name}")
                prov_source = source.describe()
                prov_source.update({
                    "iso3": manifest["iso3"],
                    "country_name": manifest["name"],
                    "vintage": vintage["id"],
                })
                if c.get("role"):
                    prov_source["role"] = c["role"]
                msgs = CaseImporter.import_zip(
                    str(local), cleanup=False,
                    source=prov_source, sha256_declared=declared,
                )
                first = msgs[0] if msgs else {}
                if first.get("casename"):
                    log(f"{case_name}: imported.")
                    results.append({"case": case_name, "archive": archive,
                                    "status": "installed",
                                    "message": first.get("message", "")})
                else:
                    results.append({"case": case_name, "archive": archive,
                                    "status": "failed",
                                    "message": first.get("message",
                                                         "The archive did not import.")})
        finally:
            shutil.rmtree(staging, ignore_errors=True)

        installed = [r for r in results if r["status"] == "installed"]
        failed = [r for r in results if r["status"] == "failed"]
        ok = bool(installed) and not failed
        error = None
        if not ok:
            if failed:
                error = failed[0]["message"]
            elif not installed:
                error = "No case was installed (everything selected already exists)."
        return {"ok": ok, "iso3": manifest["iso3"],
                "country_name": manifest["name"], "vintage": vintage["id"],
                "results": results, "error": error}

"""Read and validate a CLEWs country repo's self-description: clews-country.json.

A CLEWs country repository (e.g. EAPD-DRB/CLEWs-PHL) declares what it ships in a
manifest at its root: country identity, one or more VINTAGES (model generations --
v12, v16 -- each a directory of portable MUIO case archives with a SHA256SUMS
file), and which vintage/case is recommended. MUIOGO refuses to guess: a repo
without a manifest cannot be installed from, only inspected by hand. (CLEWs-PHL
ships several vintages side by side, so sniffing */muio/*.zip would happily
install the wrong model.)

Nothing here clones anything. Repos carry tens of MB of build history while the
payload is a few MB of archives, so the manifest, checksums and archives are
fetched as raw files (the same technique the OG CalibrationCatalog uses for
repos.json). A local checkout works too: source_type local_path reads the same
files from disk.

Manifest shape (schema_version 1):

    { "schema_version": 1,
      "iso3": "PHL", "un_code": "608", "name": "Philippines",
      "og": {"key": "og-phl"},                      # optional: the OG pairing
      "vintages": [
        { "id": "v16", "recommended": true,
          "dir": "Philippines_v16_CLEWs_build/muio",
          "sha256sums": "SHA256SUMS",               # relative to dir
          "muio_min_version": "5.6",                # optional gate
          "cases": [
            { "case": "Philippines_v16", "role": "analysis", "recommended": true,
              "archive": "Philippines_v16_v16.0.0_MUIO.zip" } ] } ] }
"""
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

MANIFEST_NAME = "clews-country.json"
MANIFEST_SCHEMA_VERSION = 1

_FETCH_TIMEOUT_SECONDS = 20
_GITHUB_URL_RE = re.compile(
    r"^https?://(www\.)?github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(\.git)?/?$"
)
_SHA256_LINE_RE = re.compile(r"^(?P<sha>[0-9a-fA-F]{64})[ \t]+\*?(?P<name>.+)$")


class ManifestError(ValueError):
    """The manifest is missing, unreadable, or does not validate."""


class ManifestNotFound(ManifestError):
    """A file the source was asked for does not exist (a 404, or no such file)."""


def parse_github_url(repo_url):
    """(owner, repo) from a GitHub repo URL, or None if it is not one."""
    if not repo_url:
        return None
    m = _GITHUB_URL_RE.match(repo_url.strip())
    if not m:
        return None
    return m.group("owner"), m.group("repo")


def raw_url(owner, repo, ref, relpath):
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{relpath}"


def _auth_headers():
    """A GitHub token, if the environment has one, for private country repos."""
    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    headers = {"User-Agent": "MUIOGO-clews-install"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_bytes(url, timeout=_FETCH_TIMEOUT_SECONDS):
    """GET a raw file. Raises urllib.error.URLError/HTTPError on failure.

    Kept as the single seam every remote read goes through, so tests (and an
    offline mirror) can swap it without touching the callers.
    """
    req = urllib.request.Request(url, headers=_auth_headers())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def parse_sha256sums(text):
    """{filename: sha256} from a SHA256SUMS file (the `shasum -a 256` format)."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _SHA256_LINE_RE.match(line)
        if m:
            out[m.group("name").strip()] = m.group("sha").lower()
    return out


def validate_manifest(data):
    """Validate a parsed manifest; returns it normalized. Raises ManifestError."""
    if not isinstance(data, dict):
        raise ManifestError("The manifest is not a JSON object.")
    if data.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ManifestError(
            f"Unsupported manifest schema_version {data.get('schema_version')!r} "
            f"(this MUIOGO reads version {MANIFEST_SCHEMA_VERSION})."
        )
    for field in ("iso3", "name"):
        if not data.get(field) or not isinstance(data[field], str):
            raise ManifestError(f"The manifest is missing required field: {field}")
    vintages = data.get("vintages")
    if not isinstance(vintages, list) or not vintages:
        raise ManifestError("The manifest declares no vintages.")
    seen_ids = set()
    for v in vintages:
        if not isinstance(v, dict):
            raise ManifestError("Every vintage must be an object.")
        for field in ("id", "dir"):
            if not v.get(field) or not isinstance(v[field], str):
                raise ManifestError(f"A vintage is missing required field: {field}")
        if v["id"] in seen_ids:
            raise ManifestError(f"Duplicate vintage id: {v['id']}")
        seen_ids.add(v["id"])
        if _unsafe_relpath(v["dir"]) or _unsafe_relpath(v.get("sha256sums") or ""):
            raise ManifestError(f"Vintage {v['id']} uses an unsafe path.")
        cases = v.get("cases")
        if not isinstance(cases, list) or not cases:
            raise ManifestError(f"Vintage {v['id']} declares no cases.")
        for c in cases:
            if not isinstance(c, dict) or not c.get("case") or not c.get("archive"):
                raise ManifestError(
                    f"Vintage {v['id']}: every case needs 'case' and 'archive'.")
            if _unsafe_relpath(c["archive"]) or os.path.basename(c["archive"]) != c["archive"]:
                raise ManifestError(
                    f"Vintage {v['id']}: archive {c['archive']!r} must be a plain "
                    "filename inside the vintage dir.")
    return data


def _unsafe_relpath(relpath):
    """True for absolute paths or anything that climbs out of the repo."""
    if relpath is None:
        return True
    p = relpath.replace("\\", "/")
    return p.startswith("/") or p.startswith("~") or ".." in p.split("/")


def select_vintage(manifest, vintage_id=None):
    """The requested vintage, or the recommended one, or the first. Raises on miss."""
    vintages = manifest["vintages"]
    if vintage_id:
        for v in vintages:
            if v["id"] == vintage_id:
                return v
        raise ManifestError(
            f"Vintage {vintage_id!r} is not in the manifest "
            f"(available: {', '.join(v['id'] for v in vintages)}).")
    for v in vintages:
        if v.get("recommended"):
            return v
    return vintages[0]


def select_cases(vintage, casenames=None):
    """The requested cases of a vintage, or its recommended one(s), or all."""
    cases = vintage["cases"]
    if casenames:
        by_name = {c["case"]: c for c in cases}
        missing = [n for n in casenames if n not in by_name]
        if missing:
            raise ManifestError(
                f"Case(s) not in vintage {vintage['id']}: {', '.join(missing)} "
                f"(available: {', '.join(by_name)}).")
        return [by_name[n] for n in casenames]
    recommended = [c for c in cases if c.get("recommended")]
    return recommended or list(cases)


class CountrySource:
    """One resolvable source of a country manifest + its files.

    source_type "repo_url": raw-fetches from GitHub at ``ref`` (default branch
    name must be given by the caller or defaults to 'main').
    source_type "local_path": reads the same layout from a directory on disk.
    """

    def __init__(self, *, source_type, repo_url=None, ref=None, local_path=None,
                 iso3=None, name=None):
        self.source_type = source_type
        self.repo_url = repo_url
        self.ref = ref or "main"
        self.local_path = local_path
        # what the register says about this repository; used when the
        # repository has no manifest and its models are discovered instead
        self.hint_iso3 = iso3
        self.hint_name = name
        if source_type == "repo_url":
            parsed = parse_github_url(repo_url)
            if not parsed:
                raise ManifestError(
                    "Only github.com repository URLs are supported for now "
                    "(e.g. https://github.com/EAPD-DRB/CLEWs-PHL).")
            self.owner, self.repo = parsed
        elif source_type == "local_path":
            if not local_path or not Path(local_path).is_dir():
                raise ManifestError("local_path does not exist or is not a directory.")
            self.owner = self.repo = None
        else:
            raise ManifestError("source_type must be 'repo_url' or 'local_path'.")

    # ── raw reads ────────────────────────────────────────────────────────────
    def read_text(self, relpath):
        if self.source_type == "local_path":
            p = Path(self.local_path, relpath)
            if not p.is_file():
                raise ManifestNotFound(f"{relpath} not found under {self.local_path}.")
            return p.read_text(encoding="utf-8-sig")
        try:
            return fetch_bytes(raw_url(self.owner, self.repo, self.ref, relpath)).decode("utf-8-sig")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise ManifestNotFound(
                    f"{relpath} not found in {self.owner}/{self.repo}@{self.ref}. "
                    "If the repository is private, set GITHUB_TOKEN.") from exc
            raise ManifestError(f"Fetching {relpath} failed: HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            raise ManifestError(f"Fetching {relpath} failed: {exc.reason}.") from exc

    def download_archive(self, relpath, dest_path, cancel=None, chunk_size=1024 * 1024):
        """Stream one archive to dest_path. Honors a threading.Event cancel between
        chunks. Raises ManifestError on network trouble, OSError on disk trouble."""
        if self.source_type == "local_path":
            src = Path(self.local_path, relpath)
            if not src.is_file():
                raise ManifestError(f"{relpath} not found under {self.local_path}.")
            with open(src, "rb") as fin, open(dest_path, "wb") as fout:
                while True:
                    if cancel is not None and cancel.is_set():
                        raise InstallCancelled()
                    chunk = fin.read(chunk_size)
                    if not chunk:
                        return
                    fout.write(chunk)
        url = raw_url(self.owner, self.repo, self.ref, relpath)
        req = urllib.request.Request(url, headers=_auth_headers())
        try:
            with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT_SECONDS) as resp, \
                    open(dest_path, "wb") as fout:
                while True:
                    if cancel is not None and cancel.is_set():
                        raise InstallCancelled()
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        return
                    fout.write(chunk)
        except urllib.error.HTTPError as exc:
            raise ManifestError(f"Downloading {relpath} failed: HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            raise ManifestError(f"Downloading {relpath} failed: {exc.reason}.") from exc

    # ── the manifest itself ──────────────────────────────────────────────────
    def load_manifest(self):
        """The repository's own manifest when it has one; otherwise a manifest
        discovered from its layout (see RepoScan). Both go through the same
        validation, so every caller sees one shape."""
        # Read first, parse second: a fetch failure is already a clean
        # ManifestError (which subclasses ValueError) and must not be rewrapped
        # as a JSON complaint.
        try:
            text = self.read_text(MANIFEST_NAME)
        except ManifestNotFound:
            return validate_manifest(self.discover_manifest())
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise ManifestError(f"{MANIFEST_NAME} is not valid JSON: {exc}.") from exc
        return validate_manifest(data)

    def discover_manifest(self):
        # imported here: RepoScan builds on this module
        from Classes.Clews import RepoScan
        if self.source_type == "local_path":
            return RepoScan.scan_local(self.local_path, iso3=self.hint_iso3, name=self.hint_name)
        return RepoScan.scan_remote(self.owner, self.repo, self.ref,
                                    iso3=self.hint_iso3, name=self.hint_name)

    def load_checksums(self, vintage):
        """{archive filename: declared sha256} for a vintage, or {} if undeclared."""
        sums_name = vintage.get("sha256sums")
        if not sums_name:
            return {}
        return parse_sha256sums(self.read_text(f"{vintage['dir']}/{sums_name}"))

    def describe(self):
        """How this source shows up in a provenance sidecar."""
        if self.source_type == "local_path":
            return {"type": "local_path", "local_path": str(self.local_path)}
        return {"type": "repo_url", "repo_url": self.repo_url, "ref": self.ref}


class InstallCancelled(Exception):
    """The user cancelled the running install."""

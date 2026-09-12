"""Discover a country repository's installable models from its contents.

A repository is not required to describe itself in clews-country.json. When
that file is missing, MUIOGO reads the repository's layout instead and builds
the same manifest shape from it, so inspection, checksums, download and import
work identically. What counts as an installable version is deliberately
simple and convention-light:

    a folder holding a SHA256SUMS file and at least one .zip archive

Everything else is derived from names, with the rules written out so a
surprising result can be traced:

- The version label comes from the top-level folder: ``Philippines_v12_CLEWs_build``
  drops the ``_CLEWs_<word>`` suffix and the country prefix shared by all
  folders, giving ``v12``. A folder without a version token keeps its name.
- A folder often also carries its predecessors' archives as evidence
  (``Philippines_v24_CLEWs_build`` holds v15 through v24). Only archives whose
  name starts with the folder's own model prefix (``Philippines_v24_``) belong
  to the version; if none match that rule, every archive in the folder does.
- The case name is the archive name without ``_MUIO.zip`` and without a
  trailing version token (``Philippines_v12_ENV_LAND_v12.0.0_MUIO.zip`` is the
  case ``Philippines_v12_ENV_LAND``; ``Philippines_vIS2_vIS2.0.0_MUIO.zip`` is
  ``Philippines_vIS2``). Several archives for the same case in one folder
  (patch releases) collapse to the highest.
- Newest first means most recently changed in the repository, from the commit
  history of each version folder. When that cannot be read (a plain folder
  without git) the versions are ordered by name and the menu says so
  (``ordering: "name"``). No version is marked recommended: the first one is
  what Install picks, the same rule the manifest path uses.

Remote repositories are read through git, not a hosting API: a blobless clone
(``--filter=blob:none``: commits and trees, no file contents) is a few MB, needs
no token, has no request limit, works for any git host, and gives both the file
listing and per-folder dates locally. The clone is kept under the CLEWs state
directory and refreshed with a fetch; the derived manifest is cached for an hour
per repository and branch. Nothing here downloads an archive.
"""
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from Classes.Base import Config
from Classes.Clews.CountryManifest import ManifestError, MANIFEST_SCHEMA_VERSION

SUMS_NAME = "SHA256SUMS"
CACHE_TTL_SECONDS = 3600
_GIT_TIMEOUT = 180

_BUILD_SUFFIX_RE = re.compile(r"_CLEWs(_[A-Za-z0-9]+)?$", re.IGNORECASE)
# a trailing token that reads as a version: v12.0.0, vIS2.0.0, 2.0.3, raw-v1.0.0
_VERSION_TOKEN_RE = re.compile(r"(^v[A-Za-z]*\d|^\d|-v?\d)", re.IGNORECASE)
_REPO_ISO3_RE = re.compile(r"^CLEWs-([A-Za-z]{3})$", re.IGNORECASE)


def natural_key(text):
    """Sort key that orders embedded numbers numerically (v2 < v2.9 < v12)."""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", str(text))]


def _case_name(archive):
    name = archive[:-4] if archive.lower().endswith(".zip") else archive
    if name.lower().endswith("_muio"):
        name = name[:-5]
    head, sep, last = name.rpartition("_")
    if sep and head and _VERSION_TOKEN_RE.search(last):
        return head
    return name


def _model_prefix(top_folder):
    """``Philippines_v12_CLEWs_build`` -> ``Philippines_v12``; ``Fiji_CLEWs_Global`` -> ``Fiji``."""
    return _BUILD_SUFFIX_RE.sub("", top_folder) or top_folder


def _country_token(prefixes):
    """The leading token every model prefix shares (``Philippines``), or ''.

    A prefix may be the bare token itself (a folder without a version part)."""
    tokens = {p.split("_", 1)[0] for p in prefixes}
    if len(tokens) != 1:
        return ""
    return tokens.pop()


def manifest_from_listing(paths, dates=None, *, repo_name=None, iso3=None, name=None):
    """Build a manifest dict from repository paths.

    paths: iterable of file paths relative to the repository root.
    dates: {version dir: ISO date string} of each folder's last change, or None.
    Raises ManifestError when nothing installable is found.
    """
    files = [p.replace("\\", "/").strip("/") for p in paths]
    dirs_with_sums = {p.rsplit("/", 1)[0] for p in files
                      if p.rsplit("/", 1)[-1] == SUMS_NAME and "/" in p}
    zips_by_dir = {}
    for p in files:
        if p.lower().endswith(".zip") and "/" in p:
            d, f = p.rsplit("/", 1)
            zips_by_dir.setdefault(d, []).append(f)
    candidates = sorted(d for d in dirs_with_sums if zips_by_dir.get(d))
    if not candidates:
        raise ManifestError(
            "No installable models found: no folder with a SHA256SUMS file and "
            "MUIO archives (.zip). A clews-country.json would also do.")

    prefixes = {d: _model_prefix(d.split("/", 1)[0]) for d in candidates}
    country = _country_token(prefixes.values())

    vintages, seen_ids = [], {}
    for d in candidates:
        prefix = prefixes[d]
        own = [z for z in zips_by_dir[d] if z.startswith(prefix + "_")] or list(zips_by_dir[d])
        best_by_case = {}
        for z in own:
            case = _case_name(z)
            if case not in best_by_case or natural_key(z) > natural_key(best_by_case[case]):
                best_by_case[case] = z
        cases = [{"case": c, "archive": a} for c, a in
                 sorted(best_by_case.items(), key=lambda kv: natural_key(kv[0]))]
        plain = [c for c in cases if c["case"] == prefix]
        (plain[0] if plain else cases[0])["recommended"] = True

        vid = prefix[len(country) + 1:] if country and prefix.startswith(country + "_") else prefix
        vid = vid or prefix
        if vid in seen_ids:
            seen_ids[vid] += 1
            vid = f"{vid}-{seen_ids[vid]}"
        else:
            seen_ids[vid] = 1
        entry = {"id": vid, "dir": d, "sha256sums": SUMS_NAME, "cases": cases}
        if dates and dates.get(d):
            entry["last_changed"] = dates[d]
        vintages.append(entry)

    if dates and all(v.get("last_changed") for v in vintages):
        vintages.sort(key=lambda v: (v["last_changed"], natural_key(v["id"])), reverse=True)
        ordering = "date"
    else:
        vintages.sort(key=lambda v: natural_key(v["id"]), reverse=True)
        ordering = "name"

    if not iso3:
        m = _REPO_ISO3_RE.match(repo_name or "")
        iso3 = m.group(1).upper() if m else (country or repo_name or "UNKNOWN").upper()[:12]
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "iso3": iso3,
        "name": name or country or repo_name or iso3,
        "discovered": True,
        "ordering": ordering,
        "vintages": vintages,
    }


# ── the derived-manifest cache ────────────────────────────────────────────────

def _cache_path():
    return Path(Config.CLEWS_DATA_STORAGE) / "scan_cache.json"


def _cache_read(key):
    try:
        data = json.loads(_cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    entry = data.get(key)
    if entry and time.time() - entry.get("fetched_at", 0) < CACHE_TTL_SECONDS:
        return entry.get("manifest")
    return None


def _cache_write(key, manifest):
    try:
        path = _cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        data[key] = {"fetched_at": time.time(), "manifest": manifest}
        path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    except OSError:
        pass  # a failed cache write must not fail the scan


# ── git ───────────────────────────────────────────────────────────────────────

def _git(args, cwd=None):
    """Run git; returns stdout. Raises ManifestError with git's own words."""
    try:
        out = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                             timeout=_GIT_TIMEOUT)
    except FileNotFoundError as exc:
        raise ManifestError("git is needed to read a repository's contents and was "
                            "not found on this machine.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ManifestError("Reading the repository took too long; try again.") from exc
    if out.returncode != 0:
        detail = (out.stderr or out.stdout or "").strip().splitlines()
        raise ManifestError("Reading the repository failed: "
                            + (detail[-1] if detail else f"git exit {out.returncode}"))
    return out.stdout


def _dates_from_git(repo_dir, ref, dirs):
    dates = {}
    for d in dirs:
        stamp = _git(["log", "-1", "--format=%cI", ref, "--", d], cwd=repo_dir).strip()
        if not stamp:
            return {}
        dates[d] = stamp
    return dates


def _mirror_dir(owner, repo):
    return Path(Config.CLEWS_DATA_STORAGE) / "scan-cache" / f"{owner}__{repo}.git"


def scan_remote(owner, repo, ref, *, iso3=None, name=None,
                clone_url=None):
    """Manifest discovered from a remote git repository at ref. Raises ManifestError.

    Keeps a blobless bare clone per repository and refreshes it on each scan
    that is older than the cache; the manifest itself is cached for an hour."""
    key = f"{owner}/{repo}@{ref}"
    cached = _cache_read(key)
    if cached:
        return cached
    url = clone_url or f"https://github.com/{owner}/{repo}.git"
    mirror = _mirror_dir(owner, repo)
    refspec = f"+refs/heads/{ref}:refs/heads/{ref}"
    if (mirror / "HEAD").exists():
        try:
            _git(["fetch", "-q", "--filter=blob:none", "--no-tags", "origin", refspec], cwd=mirror)
        except ManifestError:
            shutil.rmtree(mirror, ignore_errors=True)  # a broken mirror is rebuilt below
    if not (mirror / "HEAD").exists():
        mirror.parent.mkdir(parents=True, exist_ok=True)
        try:
            _git(["clone", "-q", "--bare", "--filter=blob:none", "--no-tags",
                  "--single-branch", "--branch", ref, url, str(mirror)])
        except ManifestError as exc:
            shutil.rmtree(mirror, ignore_errors=True)
            raise ManifestError(
                f"Could not read {owner}/{repo} (branch {ref}). {exc} "
                "If the repository is private, sign in to GitHub with git first.") from exc

    paths = _git(["ls-tree", "-r", "--name-only", ref], cwd=mirror).splitlines()
    manifest = manifest_from_listing(paths, None, repo_name=repo, iso3=iso3, name=name)
    dates = _dates_from_git(mirror, ref, [v["dir"] for v in manifest["vintages"]])
    if dates:
        manifest = manifest_from_listing(paths, dates, repo_name=repo, iso3=iso3, name=name)
    _cache_write(key, manifest)
    return manifest


# ── local folder ──────────────────────────────────────────────────────────────

def scan_local(root, *, iso3=None, name=None):
    """Manifest discovered from a folder on disk (a checkout, or a copy)."""
    root = Path(root)
    paths, sums_dirs = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        rel = Path(dirpath).relative_to(root).as_posix()
        for f in filenames:
            paths.append(f if rel == "." else f"{rel}/{f}")
        if SUMS_NAME in filenames and rel != ".":
            sums_dirs.append(rel)
    dates = {}
    if (root / ".git").exists():
        try:
            dates = _dates_from_git(root, "HEAD", sums_dirs)
        except ManifestError:
            dates = {}
    if not dates:
        for d in sums_dirs:
            try:
                mtimes = [os.path.getmtime(p) for p in Path(root, d).iterdir() if p.is_file()]
            except OSError:
                mtimes = []
            if mtimes:
                dates[d] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(max(mtimes)))
    return manifest_from_listing(paths, dates or None, repo_name=root.name, iso3=iso3, name=name)

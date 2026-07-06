"""Reflect the OG-Core installer's catalogue of available country calibrations.

MUIOGO does NOT maintain its own country list. The available list is read live from
the installer's machine-readable register (scripts/repos.json) every time, and the
last good copy is cached only as an offline fallback (a copy of the register, never a
hand-maintained list). Each entry is then tagged with this machine's install state,
joined from the local installed registry.

repos.json shape (schema_version 1):
    { "schema_version": 1,
      "repos": [ { "key", "owner", "repo", "package", "description" }, ... ] }
"""
import json
import urllib.error
import urllib.request

from Classes.Base import Config
from Classes.OGCore.CalibrationRegistry import CalibrationRegistry

_FETCH_TIMEOUT_SECONDS = 10


def derive_country_id(repo_name):
    """OG-ETH -> ETH, OG-Core -> CORE. The suffix after the last dash, uppercased."""
    if not repo_name:
        return ""
    return repo_name.rsplit("-", 1)[-1].upper()


def normalize_entry(raw):
    """Turn one raw repos.json entry into MUIOGO's catalogue shape."""
    key = raw.get("key", "")
    owner = raw.get("owner", "")
    repo = raw.get("repo", "")
    return {
        "country_id": derive_country_id(repo),
        "country_name": raw.get("description") or repo or key,
        "catalog_key": key,
        "repo_url": f"https://github.com/{owner}/{repo}" if owner and repo else "",
        "default_branch": None,  # not in the register; the installer clones the default
        "package_name": raw.get("package", ""),
        "uv_ready": True,  # the register only lists repos that are uv-installable
        "is_base": key == "og-core",
    }


class CalibrationCatalog:
    @staticmethod
    def _write_cache(payload):
        try:
            Config.OGC_DATA_STORAGE.mkdir(parents=True, exist_ok=True)
            with open(Config.OGC_CATALOG_CACHE, mode="w", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=True, indent=4))
        except OSError:
            # A failed cache write must not fail the request; live data is in hand.
            pass

    @staticmethod
    def _read_cache():
        path = Config.OGC_CATALOG_CACHE
        if not path.exists():
            return None
        try:
            with open(path, mode="r", encoding="utf-8") as f:
                return json.loads(f.read())
        except (OSError, ValueError):
            return None

    @staticmethod
    def _parse_payload(payload):
        """Validate the register payload and return its repo entries, or None."""
        if not isinstance(payload, dict):
            return None
        repos = payload.get("repos")
        if not isinstance(repos, list):
            return None
        return repos

    @classmethod
    def fetch_register(cls):
        """Return (entries, source). source is 'live', 'cache', or 'none'.

        Live first; on any network/parse failure fall back to the cached copy.
        """
        # 1. Live.
        try:
            req = urllib.request.Request(
                Config.OGC_INSTALLER_REPOS_JSON_URL,
                headers={"User-Agent": "MUIOGO-calibration-catalog"},
            )
            with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT_SECONDS) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            repos = cls._parse_payload(payload)
            if repos is not None:
                cls._write_cache(payload)
                return [normalize_entry(r) for r in repos], "live"
        except (urllib.error.URLError, ValueError, OSError, TimeoutError):
            pass

        # 2. Cache fallback.
        cached = cls._read_cache()
        repos = cls._parse_payload(cached) if cached is not None else None
        if repos is not None:
            return [normalize_entry(r) for r in repos], "cache"

        # 3. Nothing available. The user can still add by URL or local path.
        return [], "none"

    @classmethod
    def get_catalog_with_state(cls):
        """Catalogue entries, each tagged with this machine's country_state.

        Returns (countries, source).
        """
        entries, source = cls.fetch_register()
        for entry in entries:
            record = CalibrationRegistry.get(entry["country_id"])
            entry["install_state"] = (
                record.get("install_state", "installed") if record else "not_installed"
            )
        return entries, source

    @classmethod
    def find_entry(cls, catalog_key):
        """Look up one register entry by its installer key (e.g. og-eth)."""
        if not catalog_key:
            return None
        entries, _ = cls.fetch_register()
        for entry in entries:
            if entry["catalog_key"] == catalog_key:
                return entry
        return None

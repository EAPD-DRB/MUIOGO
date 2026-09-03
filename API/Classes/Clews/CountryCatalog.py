"""Reflect the CLEWs country register.

The register (Config.CLEWS_CATALOG_URL, by default MUIOGO's own
scripts/clews-repos.json read from the main branch) is read live on every call
and the last good copy cached as an offline fallback -- exactly the OG
CalibrationCatalog pattern. With the URL emptied out, the catalogue is honestly
empty and installs go by Git URL or local path.

Register shape (schema_version 1):
    { "schema_version": 1,
      "repos": [ { "key", "owner", "repo", "iso3", "description" }, ... ] }
"""
import json
import urllib.error

from Classes.Base import Config
from Classes.Clews.CountryManifest import fetch_bytes
from Classes.Clews.CountryRegistry import CountryRegistry

_FETCH_TIMEOUT_SECONDS = 10


def normalize_entry(raw):
    owner = raw.get("owner", "")
    repo = raw.get("repo", "")
    return {
        "catalog_key": raw.get("key", ""),
        "iso3": (raw.get("iso3") or "").upper(),
        "country_name": raw.get("description") or repo or raw.get("key", ""),
        "repo_url": f"https://github.com/{owner}/{repo}" if owner and repo else "",
    }


class CountryCatalog:
    @staticmethod
    def _write_cache(payload):
        try:
            Config.CLEWS_DATA_STORAGE.mkdir(parents=True, exist_ok=True)
            with open(Config.CLEWS_CATALOG_CACHE, mode="w", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=True, indent=4))
        except OSError:
            pass  # live data is in hand; a failed cache write must not fail the call

    @staticmethod
    def _read_cache():
        path = Config.CLEWS_CATALOG_CACHE
        if not path.exists():
            return None
        try:
            with open(path, mode="r", encoding="utf-8") as f:
                return json.loads(f.read())
        except (OSError, ValueError):
            return None

    @staticmethod
    def _parse_payload(payload):
        if not isinstance(payload, dict):
            return None
        repos = payload.get("repos")
        return repos if isinstance(repos, list) else None

    @classmethod
    def fetch_register(cls):
        """(entries, source): source is 'live', 'cache', or 'none'."""
        url = Config.CLEWS_CATALOG_URL
        if not url:
            return [], "none"
        try:
            payload = json.loads(fetch_bytes(url, timeout=_FETCH_TIMEOUT_SECONDS)
                                 .decode("utf-8"))
            repos = cls._parse_payload(payload)
            if repos is not None:
                cls._write_cache(payload)
                return [normalize_entry(r) for r in repos], "live"
        except (urllib.error.URLError, ValueError, OSError, TimeoutError):
            pass
        cached = cls._read_cache()
        repos = cls._parse_payload(cached) if cached is not None else None
        if repos is not None:
            return [normalize_entry(r) for r in repos], "cache"
        return [], "none"

    @classmethod
    def get_catalog_with_state(cls):
        """Catalogue entries, each tagged with this storage's installed cases."""
        entries, source = cls.fetch_register()
        if entries:
            installed = {}
            for record in CountryRegistry.list_all():
                iso3 = (record.get("source") or {}).get("iso3") or record.get("iso3")
                if iso3 and record.get("managed"):
                    installed.setdefault(iso3.upper(), []).append(record["casename"])
            for entry in entries:
                cases = installed.get(entry["iso3"], [])
                entry["installed_cases"] = sorted(cases)
                entry["install_state"] = "installed" if cases else "not_installed"
        return entries, source

    @classmethod
    def find_entry(cls, catalog_key):
        if not catalog_key:
            return None
        entries, _ = cls.fetch_register()
        for entry in entries:
            if entry["catalog_key"] == catalog_key:
                return entry
        return None

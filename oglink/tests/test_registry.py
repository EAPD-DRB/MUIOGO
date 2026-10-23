"""Link-side unit tests for the OG-model registry loader. No OG env, no numpy/ogcore. The registry is
keyed by OG repo key (og-phl), and an entry is a pure install record {package, env_python, version}.
Run with the standalone link venv: `uv run pytest tests/test_registry.py`.
"""
from __future__ import annotations

import json
import os
import types

from oglink import registry


def _fake_py(tmp_path, name="fake-python"):
    """A file that EXISTS to stand in for an interpreter (lookup() isfile-checks env_python);
    a literal /bin/sh would fail on Windows."""
    p = tmp_path / name
    p.write_text("")
    return str(p)


def _write(tmp_path, env_python=None):
    p = tmp_path / "og_model_registry.json"
    p.write_text(json.dumps({"schema_version": 1, "models": {
        "og-phl": {"package": "ogphl", "env_python": env_python or _fake_py(tmp_path),
                   "version": "0.1.0"}}}))
    return str(p)


def test_packaged_default_ships_empty():
    # the wheel must NOT bake a machine-specific path; a machine populates the register via the installer
    reg = registry.load_registry(path=registry._packaged_default())
    assert reg == {}


def test_registry_path_resolution_order(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)                                        # no ./og_model_registry.json here
    monkeypatch.delenv(registry.ENV_VAR, raising=False)
    assert registry.registry_path() == registry._packaged_default()   # falls back to packaged
    envfile = _write(tmp_path)
    monkeypatch.setenv(registry.ENV_VAR, envfile)
    assert registry.registry_path() == envfile                        # env var wins


def test_lookup_by_repo_key_package_and_country(tmp_path):
    rp = _write(tmp_path)
    e = registry.lookup("og-phl", path=rp)
    assert (e.key, e.package, e.version) == ("og-phl", "ogphl", "0.1.0")
    assert e.params_resource_name == "ogphl_default_parameters.json"   # derived by convention
    assert registry.lookup("ogphl", path=rp).key == "og-phl"          # also resolves by package name
    country = types.SimpleNamespace(og_repo="og-phl", name="Philippines")
    assert registry.lookup(country, path=rp).package == "ogphl"       # and via a CountryConfig (.og_repo)


def test_entry_carries_calibration_and_discovered(tmp_path):
    # a registered model may pin a CHOSEN calibration + carry the SAVED discovery status; absent -> None
    entry = {"package": "ogzaf", "env_python": _fake_py(tmp_path), "version": "0.1.0", "source_dir": "/x/ogzaf",
             "calibration": "ogzaf_default_parameters_multisector.json",
             "discovered": {"at": "2026-01-01T00:00:00Z", "recommended": "m.json", "couplable_count": 1,
                            "candidates": [{"file": "m.json", "couplable": True}]}}
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"schema_version": 1, "models": {"og-zaf": entry}}))
    e = registry.lookup("og-zaf", path=str(p))
    assert e.calibration == "ogzaf_default_parameters_multisector.json"
    assert e.source_dir == "/x/ogzaf" and e.discovered["couplable_count"] == 1
    bare = registry.lookup("og-phl", path=_write(tmp_path))
    assert bare.calibration is None and bare.discovered is None


def test_package_source_dir_derived_from_env_python():
    # absent source_dir -> derived from the env interpreter (<install>/.venv/bin/python -> <install>/<pkg>)
    e = registry.ModelEntry(key="og-phl", package="ogphl",
                            env_python=os.path.join("/Users/x/OG-PHL", ".venv", "bin", "python"))
    assert registry.package_source_dir(e) == os.path.join("/Users/x/OG-PHL", "ogphl")


def test_unregistered_raises_actionable(tmp_path):
    import pytest
    with pytest.raises(registry.ModelNotInstalledError) as e:
        registry.lookup("og-xxx", path=_write(tmp_path))
    assert "No OG model registered" in str(e.value) and "og-xxx" in str(e.value)


def test_absent_interpreter_raises(tmp_path):
    import pytest
    bad = _write(tmp_path, env_python="/no/such/python")
    with pytest.raises(registry.ModelNotInstalledError) as e:
        registry.lookup("og-phl", path=bad)
    assert "not found at" in str(e.value)

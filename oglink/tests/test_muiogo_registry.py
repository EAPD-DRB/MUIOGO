"""Link-side tests for resolving an OG model from a MUIOGO install's register (MUIOGO PR #487/#502).

The link READS MUIOGO's og-state register (``$MUIOGO_OG_DATA_DIR`` / ``~/.muiogo/og-state`` /
``og_calibrations_installed.json``; the pre-#502 in-tree path is a legacy fallback) and never writes it.
MUIOGO's register fills what the link's own lacks; on a key collision the link's OWN registration wins
(a deliberate pin, e.g. a dev worktree). An explicit ``$OGLINK_MODEL_REGISTRY`` / ``path=`` overrides
both. Fully tolerant -- a missing or corrupt MUIOGO file must never break lookup. No OG env, no
numpy/ogcore. Run with the standalone link venv: ``uv run pytest tests/test_muiogo_registry.py``.
"""
from __future__ import annotations

import json
import os

import pytest

from oglink import registry


def _fake_py(tmp_path, name="fake-python"):
    """A file that EXISTS to stand in for an interpreter (lookup() isfile-checks env_python);
    a literal /bin/sh would fail on Windows."""
    p = tmp_path / name
    p.write_text("")
    return str(p)


def _og_record(tmp_path, *, package="ogphl", repo="OG-PHL", python_path=None,
               make_source=False, country_id="PHL", state="installed"):
    """One installed-OG record dict + its local_path (shared by both register locations)."""
    python_path = python_path or _fake_py(tmp_path, "muiogo-python")
    local_path = tmp_path / "models" / repo
    if make_source:
        (local_path / package).mkdir(parents=True)          # source_dir present -> discovery is attempted
    rec = {"country_id": country_id, "country_name": "Philippines", "package_name": package,
           "local_path": str(local_path), "python_path": python_path, "commit_sha": "abc123",
           "install_state": state}
    return rec, str(local_path)


def _og_state(tmp_path, monkeypatch, *, records=None, **kw):
    """Create a fake ~/.muiogo/og-state register (the post-#502 location, pointed at via
    $MUIOGO_OG_DATA_DIR -- MUIOGO's own override env) with one record; return local_path."""
    if records is None:
        rec, local_path = _og_record(tmp_path, **kw)
        records = {rec["country_id"]: rec}
    else:
        local_path = None
    state = tmp_path / "og-state"
    state.mkdir(exist_ok=True)
    (state / "og_calibrations_installed.json").write_text(json.dumps({"calibrations": records}))
    monkeypatch.setenv(registry.MUIOGO_OG_STATE_ENV, str(state))
    return local_path


def _muiogo_home_legacy(tmp_path, **kw):
    """The pre-#502 in-tree register (legacy fallback); return (home, local_path)."""
    rec, local_path = _og_record(tmp_path, **kw)
    ogc = tmp_path / "MUIOGO" / "WebAPP" / "DataStorage" / "OGCore"
    ogc.mkdir(parents=True)
    (ogc / "og_calibrations_installed.json").write_text(
        json.dumps({"calibrations": {rec["country_id"]: rec}}))
    return str(tmp_path / "MUIOGO"), local_path


def _link_registry(tmp_path, *, env_python=None, key="og-phl", package="ogphl"):
    p = tmp_path / "og_model_registry.json"
    p.write_text(json.dumps({"schema_version": 1, "models": {
        key: {"package": package, "env_python": env_python or _fake_py(tmp_path, "link-python"),
              "version": "0.1.0"}}}))
    return str(p)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    # isolate from the real machine: env overrides, any sibling ../MUIOGO, AND the real
    # ~/.muiogo/og-state (point the og-state env at an empty tmp dir by default)
    monkeypatch.delenv(registry.ENV_VAR, raising=False)
    monkeypatch.delenv(registry.MUIOGO_HOME_ENV, raising=False)
    empty = tmp_path / "_empty-og-state"
    empty.mkdir()
    monkeypatch.setenv(registry.MUIOGO_OG_STATE_ENV, str(empty))


def test_resolves_model_from_muiogo_register(tmp_path, monkeypatch):
    py = _fake_py(tmp_path, "muiogo-python")
    local = _og_state(tmp_path, monkeypatch, make_source=True, python_path=py)
    # the link's OWN discovery picks the couplable calibration from MUIOGO's checkout (MUIOGO needn't know)
    monkeypatch.setattr("oglink.discovery.discover_calibrations",
                        lambda pkg_dir, package: {"recommended": "ogphl_multisector_default_parameters.json",
                                                  "couplable_count": 1})
    monkeypatch.chdir(tmp_path)                              # link-own -> packaged empty (no ./registry here)
    e = registry.lookup("og-phl")
    assert (e.key, e.package, e.env_python) == ("og-phl", "ogphl", py)
    assert e.source_dir == os.path.join(local, "ogphl")
    assert e.calibration == "ogphl_multisector_default_parameters.json"
    assert registry.lookup("ogphl").key == "og-phl"         # also resolvable by package name


def test_legacy_pre502_register_is_still_read(tmp_path, monkeypatch):
    # a pre-#502 MUIOGO keeps its register in-tree; with no og-state file it must still resolve
    py = _fake_py(tmp_path, "muiogo-python")
    home, _ = _muiogo_home_legacy(tmp_path, python_path=py)
    monkeypatch.setenv(registry.MUIOGO_HOME_ENV, home)
    monkeypatch.chdir(tmp_path)
    assert registry.lookup("og-phl").env_python == py


def test_og_state_wins_over_legacy_path(tmp_path, monkeypatch):
    # both locations present (e.g. an upgraded MUIOGO with a stale in-tree file): og-state wins
    new_py, old_py = _fake_py(tmp_path, "new-python"), _fake_py(tmp_path, "old-python")
    home, _ = _muiogo_home_legacy(tmp_path, python_path=old_py, repo="OG-PHL-old")
    monkeypatch.setenv(registry.MUIOGO_HOME_ENV, home)
    _og_state(tmp_path, monkeypatch, python_path=new_py)
    monkeypatch.chdir(tmp_path)
    assert registry.lookup("og-phl").env_python == new_py


def test_link_own_register_wins_over_muiogo(tmp_path, monkeypatch):
    # an explicit `models register` is a deliberate pin (e.g. a dev worktree); a MUIOGO install of
    # the same model must NOT silently shadow it -- that is the stale-code contamination case
    mu_py, link_py = _fake_py(tmp_path, "muiogo-python"), _fake_py(tmp_path, "link-python")
    _og_state(tmp_path, monkeypatch, python_path=mu_py)
    monkeypatch.chdir(tmp_path)
    _link_registry(tmp_path, env_python=link_py)            # link-own points at a DIFFERENT interpreter
    e = registry.lookup("og-phl")
    assert e.env_python == link_py                           # the link's own pin wins

def test_muiogo_fills_gaps_in_link_own(tmp_path, monkeypatch):
    mu_py = _fake_py(tmp_path, "muiogo-python")
    _og_state(tmp_path, monkeypatch, python_path=mu_py, repo="OG-ETH", package="ogeth",
              country_id="ETH")
    monkeypatch.chdir(tmp_path)
    _link_registry(tmp_path)                                # own register has og-phl only
    assert registry.lookup("og-eth").env_python == mu_py    # muiogo provides the missing model
    assert registry.lookup("og-phl").package == "ogphl"     # own entries untouched


def test_models_list_shows_merged_view(tmp_path, monkeypatch):
    # the health check (`models list`) must show what lookup would use, not just the own register
    from oglink import models
    mu_py = _fake_py(tmp_path, "muiogo-python")
    _og_state(tmp_path, monkeypatch, python_path=mu_py, repo="OG-ETH", package="ogeth",
              country_id="ETH")
    monkeypatch.chdir(tmp_path)
    _link_registry(tmp_path)                                # own register: og-phl
    rows = {r[0]: r for r in models.list_models()}
    assert set(rows) == {"og-phl", "og-eth"}                # merged
    assert rows["og-eth"][5] is True                        # muiogo interpreter exists


def test_explicit_registry_bypasses_muiogo(tmp_path, monkeypatch):
    mu_py, link_py = _fake_py(tmp_path, "muiogo-python"), _fake_py(tmp_path, "link-python")
    _og_state(tmp_path, monkeypatch, python_path=mu_py)
    rp = _link_registry(tmp_path, env_python=link_py)
    assert registry.lookup("og-phl", path=rp).env_python == link_py   # explicit path -> MUIOGO ignored
    monkeypatch.setenv(registry.ENV_VAR, rp)                 # $OGLINK_MODEL_REGISTRY is also an override
    assert registry.lookup("og-phl").env_python == link_py


def test_absent_muiogo_falls_back_to_link_own(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)                              # empty og-state, no home, no sibling
    assert registry.load_muiogo_registry() == {}
    rp = _link_registry(tmp_path)
    assert registry.lookup("og-phl", path=rp).package == "ogphl"


def test_corrupt_muiogo_register_is_tolerated(tmp_path, monkeypatch):
    state = tmp_path / "og-state"
    state.mkdir()
    (state / "og_calibrations_installed.json").write_text("{ not: valid json ]")
    monkeypatch.setenv(registry.MUIOGO_OG_STATE_ENV, str(state))
    assert registry.load_muiogo_registry() == {}            # corrupt -> {}, never raises
    rp = _link_registry(tmp_path)
    assert registry.lookup("og-phl", path=rp).package == "ogphl"   # link still resolves


def test_incomplete_record_is_skipped(tmp_path, monkeypatch):
    # a record missing python_path/local_path/package_name is not a usable install -> ignored
    _og_state(tmp_path, monkeypatch,
              records={"PHL": {"country_id": "PHL", "install_state": "installing"}})
    assert registry.load_muiogo_registry() == {}

"""Windows portability of the link runtime, EXERCISED ON POSIX (we have no Windows CI): the interpreter
resolver probes both .venv layouts, register resolves a Windows-layout env, package_source_dir's walk-up is
depth-correct for Scripts\\python.exe, and the encoding sweep makes reads BOM/UTF-8 tolerant. numpy/pandas-
only (no ogcore)."""
import json
import os

import pytest

from oglink import golden, models, registry, serde
from oglink.registry import ModelEntry, venv_python


def _make_env(root, layout):
    """Create a fake OG-model checkout with a venv interpreter in the given layout ('posix'|'windows'),
    a minimal pyproject, and a package source dir. Returns (install_dir, interpreter_path)."""
    inst = root / "OG-FAKE"
    if layout == "windows":
        interp = inst / ".venv" / "Scripts" / "python.exe"
    else:
        interp = inst / ".venv" / "bin" / "python"
    interp.parent.mkdir(parents=True)
    interp.write_text("")                                   # the file just has to EXIST
    (inst / "pyproject.toml").write_text('[project]\nname = "ogfake"\nversion = "0.1.0"\n')
    (inst / "ogfake").mkdir()                               # <install>/<package> source dir
    return str(inst), str(interp)


# --- venv_python: probe both layouts -----------------------------------------------

def test_resolves_posix_layout(tmp_path):
    inst, interp = _make_env(tmp_path, "posix")
    assert venv_python(inst) == interp


def test_resolves_windows_layout_on_posix(tmp_path):
    # The whole point: a .venv/Scripts/python.exe env (what uv builds on Windows) resolves even when the
    # test host is POSIX -- resolution is by existence-probe, not by the host OS.
    inst, interp = _make_env(tmp_path, "windows")
    assert venv_python(inst) == interp
    assert interp.endswith(os.path.join("Scripts", "python.exe"))


def test_windows_preferred_first_when_both_exist(tmp_path, monkeypatch):
    inst, _ = _make_env(tmp_path, "posix")
    win = os.path.join(inst, ".venv", "Scripts", "python.exe")
    os.makedirs(os.path.dirname(win))
    open(win, "w").close()                                  # now BOTH layouts exist
    monkeypatch.setattr(registry, "_IS_WINDOWS", True)
    assert venv_python(inst) == win                         # Windows host -> Scripts preferred
    monkeypatch.setattr(registry, "_IS_WINDOWS", False)
    assert venv_python(inst).endswith(os.path.join("bin", "python"))   # POSIX host -> bin preferred


def test_missing_interpreter_fails_loud_listing_both(tmp_path):
    (tmp_path / "OG-EMPTY").mkdir()
    with pytest.raises(FileNotFoundError) as e:
        venv_python(str(tmp_path / "OG-EMPTY"))
    msg = str(e.value)
    assert os.path.join("Scripts", "python.exe") in msg and os.path.join("bin", "python") in msg


def test_python_override(tmp_path):
    interp = tmp_path / "conda" / "python"
    interp.parent.mkdir(parents=True)
    interp.write_text("")
    assert venv_python(str(tmp_path / "nonexistent-install"), override=str(interp)) == str(interp)
    with pytest.raises(FileNotFoundError, match="does not exist"):
        venv_python(str(tmp_path), override=str(tmp_path / "no" / "such" / "python"))


# --- package_source_dir: depth-3 walk-up is correct for the Windows layout too -----

def test_package_source_dir_windows_walkup():
    entry = ModelEntry(key="og-fake", package="ogfake",
                       env_python=os.path.join("C:\\OG-FAKE", ".venv", "Scripts", "python.exe"))
    # walk up 3 (python.exe -> Scripts -> .venv -> install) then join package
    assert registry.package_source_dir(entry) == os.path.join("C:\\OG-FAKE", "ogfake")


# --- register: resolves + records a Windows-layout env (no discovery/subprocess) ---

def test_register_windows_layout(tmp_path):
    inst, interp = _make_env(tmp_path, "windows")
    rf = tmp_path / "reg.json"
    rec = models.register(inst, registry_file=str(rf), run_discovery=False)
    assert rec["env_python"] == interp and rec["key"] == "og-fake" and rec["package"] == "ogfake"
    reg = registry.load_registry(str(rf))                   # round-trips through JSON
    assert reg["og-fake"].env_python == interp


def test_register_python_and_source_overrides(tmp_path):
    inst, _ = _make_env(tmp_path, "windows")
    conda = tmp_path / "conda" / "python"
    conda.parent.mkdir(parents=True); conda.write_text("")
    src = tmp_path / "custom_src"; src.mkdir()
    rf = tmp_path / "reg.json"
    rec = models.register(inst, registry_file=str(rf), run_discovery=False,
                          python=str(conda), source_dir=str(src))
    assert rec["env_python"] == str(conda) and rec["source_dir"] == str(src)


# --- encoding: reads tolerate a UTF-8 BOM (Windows Notepad / Excel author them) -----

def test_load_registry_tolerates_bom(tmp_path):
    rf = tmp_path / "reg.json"
    payload = {"schema_version": 1, "models": {"og-x": {"package": "ogx", "env_python": "/x/py"}}}
    rf.write_text("﻿" + json.dumps(payload), encoding="utf-8")   # leading BOM
    # a plain utf-8 json.load would choke on the BOM; the link now reads utf-8-sig
    reg = registry.load_registry(str(rf))
    assert reg["og-x"].package == "ogx"


def test_golden_load_tolerates_bom(tmp_path):
    p = tmp_path / "golden.json"
    p.write_text("﻿" + json.dumps({"run1": {"Y": 1.0}}), encoding="utf-8")
    assert golden.load(str(p))["run1"]["Y"] == 1.0


def test_health_json_roundtrip_nonascii(tmp_path):
    # a profile round-trips; the write is utf-8 and the read is utf-8-sig
    p = tmp_path / "health.json"
    serde.write_health_json({"excess_deaths": -5.0, "profile": [0.1, 0.2], "phase_years": 5}, str(p))
    out = serde.read_health_json(str(p))
    assert out["excess_deaths"] == -5.0 and list(out["profile"]) == [0.1, 0.2]

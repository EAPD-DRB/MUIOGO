"""The OG-model registry: where each onboarded country model's environment lives, so the link can
locate and launch it as a subprocess without importing it. Stdlib-only (imports in the link env).

Keyed by the OG REPO KEY (e.g. ``og-phl``), mirroring ``OG-Core/scripts/repos.json`` and the universal
installer. An entry is a pure INSTALL RECORD -- ``{package, env_python, version}`` -- nothing about
coupling or calibration, and NOT the UN country code (the OG package owns that: ``ogphl.UN_COUNTRY_CODE``).

The link only READS registries; it never installs. Resolution: an explicit registry (the ``path`` arg or
``$OGLINK_MODEL_REGISTRY``) is used ALONE; otherwise MUIOGO's installed-OG register fills what the link's
own register (``./og_model_registry.json`` > the packaged EMPTY default) lacks. MUIOGO's register lives at
``$MUIOGO_OG_DATA_DIR``/``~/.muiogo/og-state``/``og_calibrations_installed.json`` (MUIOGO PR #502 moved OG
state out of the DataStorage tree; the pre-#502 in-tree path is still read as a legacy fallback, since #502
shipped no migration). On a key collision the link's OWN registration wins: an explicit ``models register``
is a deliberate pin (e.g. a dev worktree) that a later MUIOGO install of the same model must not silently
shadow -- stale-code contamination is exactly the failure the pin exists to prevent. The link maps MUIOGO's
record (``python_path`` / ``local_path`` / ``package_name``) to an entry and picks the couplable calibration
with its OWN discovery (MUIOGO needn't know anything about energy-coupling). A missing/unbuilt model raises
an actionable ModelNotInstalledError.
"""
from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass

ENV_VAR = "OGLINK_MODEL_REGISTRY"

# Platform constant, computed once (MUIOGO convention: SYSTEM = platform.system()). Used only to
# ORDER the interpreter-layout probe below.
_IS_WINDOWS = platform.system() == "Windows"


def venv_python(install_dir: str, *, override: str | None = None) -> str:
    """Resolve an OG model checkout's venv interpreter, cross-platform.

    Mirrors MUIOGO's bin-vs-Scripts idiom: a uv/venv puts the
    interpreter at ``.venv/Scripts/python.exe`` on Windows and ``.venv/bin/python`` on POSIX. But the link
    RESOLVES an already-built env (it does not create it), so rather than branch on the OS alone it PROBES
    BOTH layouts (the platform-preferred one first) -- so an env copied between machines, or a
    non-standard build, still resolves. ``override`` (``--python``) short-circuits the probe for a
    conda/system interpreter. Returns the existing interpreter path; raises FileNotFoundError listing what
    was tried (fail loud with an actionable message, as MUIOGO's solver resolver does)."""
    if override:
        p = os.path.abspath(os.path.expanduser(override))
        if os.path.exists(p):
            return p
        raise FileNotFoundError(f"--python interpreter {override!r} does not exist (resolved to {p}).")
    venv = os.path.join(install_dir, ".venv")
    win = os.path.join(venv, "Scripts", "python.exe")
    posix = os.path.join(venv, "bin", "python")
    for cand in ((win, posix) if _IS_WINDOWS else (posix, win)):
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError(
        f"no model interpreter under {venv} (looked for {os.path.join('Scripts', 'python.exe')} and "
        f"{os.path.join('bin', 'python')}). Build the model's env first (the OG installer runs "
        f"`uv sync` in {install_dir}), or pass --python <interpreter> for a conda/system env.")


class ModelNotInstalledError(RuntimeError):
    """The requested OG model is not registered, or its environment is not on disk."""


@dataclass(frozen=True)
class ModelEntry:
    key: str                   # the repo key, e.g. "og-phl" (matches repos.json + the installer)
    package: str               # importable package in the model's env, e.g. "ogphl"
    env_python: str            # absolute path to that env's python interpreter
    version: str | None = None
    calibration: str | None = None   # the CHOSEN multisector param resource (from `models register`'s
                                     # discovery); None -> the package's single-industry default, so the
                                     # energy channels skip. Recorded once at onboarding, used every run.
    source_dir: str | None = None    # the package's SOURCE dir (holds its *.py + param JSONs), so the link
                                     # can read PROD_DICT/CONS_DICT + the calibrations WITHOUT importing it.
                                     # None -> derived from env_python (see package_source_dir).
    discovered: dict | None = None   # the SAVED discovery findings (calibration menu + couplability +
                                     # an 'at' timestamp), recorded at register time so the status is
                                     # durable + user-inspectable without re-running. The authoritative
                                     # CHOICE is `calibration` (edit that to override); `discovered` is the
                                     # record. Re-read with `models calibrations --refresh` (it's cheap).

    @property
    def params_resource_name(self) -> str:
        return f"{self.package}_default_parameters.json"


def _packaged_default() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "og_model_registry.json")


def registry_path(path: str | None = None) -> str:
    """The registry file to use: explicit arg > $OGLINK_MODEL_REGISTRY > ./og_model_registry.json >
    the packaged default."""
    if path:
        return path
    env = os.environ.get(ENV_VAR)
    if env:
        return env
    local = os.path.join(os.getcwd(), "og_model_registry.json")
    return local if os.path.exists(local) else _packaged_default()


def load_registry(path: str | None = None) -> dict[str, ModelEntry]:
    """Parse the installed register into {repo_key: ModelEntry}."""
    rp = registry_path(path)
    with open(rp, encoding="utf-8-sig") as f:   # utf-8-sig: tolerate a BOM if the registry was hand-edited on Windows
        data = json.load(f)
    out: dict[str, ModelEntry] = {}
    for key, e in data.get("models", {}).items():
        out[key] = ModelEntry(key=key, package=e["package"], env_python=e["env_python"],
                              version=e.get("version"), calibration=e.get("calibration"),
                              source_dir=e.get("source_dir"), discovered=e.get("discovered"))
    return out


def package_source_dir(entry: ModelEntry) -> str:
    """The package's source dir (for link-side reading of PROD_DICT/CONS_DICT + calibrations). The stored
    ``source_dir`` if present, else derived from the env interpreter by walking up 3 levels to the install
    dir, then joining the package name. That walk is depth-correct on BOTH platforms -- ``.venv/bin/python``
    (POSIX) and ``.venv/Scripts/python.exe`` (Windows) each sit exactly 3 levels below the install dir --
    so no OS branch is needed here once ``register`` stored the right interpreter. NB: an arbitrary
    ``--python`` interpreter (conda/system) will NOT sit under ``<install>/.venv``, so ``register`` records
    an explicit ``source_dir`` in that case rather than relying on this derivation."""
    if entry.source_dir:
        return entry.source_dir
    install = os.path.dirname(os.path.dirname(os.path.dirname(entry.env_python)))   # .venv/{bin|Scripts}/py -> install
    return os.path.join(install, entry.package)


MUIOGO_HOME_ENV = "OGLINK_MUIOGO_HOME"


def _muiogo_home() -> str | None:
    """The MUIOGO install dir: $OGLINK_MUIOGO_HOME; else the MUIOGO checkout this package is nested inside
    (a dir holding both API/ and WebAPP/DataStorage -- our <MUIOGO>/oglink/oglink layout); else a sibling
    ``../MUIOGO`` (standalone checkout). Mirrors country._muiogo_home so registry + CLEWS-scenario
    resolution agree on where MUIOGO lives."""
    env = os.environ.get(MUIOGO_HOME_ENV)
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    cur = here
    for _ in range(6):
        if os.path.isdir(os.path.join(cur, "API")) and \
           os.path.isdir(os.path.join(cur, "WebAPP", "DataStorage")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    sibling = os.path.normpath(os.path.join(
        os.path.dirname(os.path.dirname(here)), os.pardir, "MUIOGO"))
    return sibling if os.path.isdir(sibling) else None


MUIOGO_OG_STATE_ENV = "MUIOGO_OG_DATA_DIR"


def _muiogo_og_state_file() -> str | None:
    """MUIOGO's installed-OG register file, or None. Since MUIOGO PR #502 OG state lives OUTSIDE the
    MUIOGO checkout at ``~/.muiogo/og-state`` (override: ``$MUIOGO_OG_DATA_DIR`` -- MUIOGO's own env var,
    honored here so both tools read the same file). #502 shipped no migration, so a pre-#502 install's
    in-tree ``WebAPP/DataStorage/OGCore/`` register is still read as a legacy fallback."""
    name = "og_calibrations_installed.json"
    state_dir = os.environ.get(MUIOGO_OG_STATE_ENV, "").strip() or os.path.join(
        os.path.expanduser("~"), ".muiogo", "og-state")
    candidates = [os.path.join(state_dir, name)]
    home = _muiogo_home()
    if home:
        candidates.append(os.path.join(home, "WebAPP", "DataStorage", "OGCore", name))
    return next((c for c in candidates if os.path.isfile(c)), None)


def load_muiogo_registry() -> dict[str, ModelEntry]:
    """MUIOGO's installed-OG register as ``{repo_key: ModelEntry}``, or ``{}`` when there is no MUIOGO
    install / file / usable record. Read-only and FULLY TOLERANT: a missing or corrupt MUIOGO registry
    must never break the link -- it just falls back to the link's own. MUIOGO records where a model is
    installed (``python_path`` / ``local_path`` / ``package_name``); the link's own discovery picks the
    couplable calibration, so the link never depends on MUIOGO understanding coupling."""
    f = _muiogo_og_state_file()
    if not f:
        return {}
    try:
        with open(f, encoding="utf-8-sig") as fh:        # utf-8-sig: tolerate a BOM (MUIOGO writes utf-8)
            records = json.load(fh)["calibrations"].values()
    except (OSError, ValueError, KeyError, AttributeError, TypeError):
        return {}
    from . import (
        discovery,  # lazy: keep the module import graph flat (registry loads early)
    )
    out: dict[str, ModelEntry] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        env_python, local_path, package = rec.get("python_path"), rec.get("local_path"), rec.get("package_name")
        if not (env_python and local_path and package):
            continue                                     # not a usable/complete install record
        key = os.path.basename(os.path.normpath(local_path)).lower()    # OG-PHL -> og-phl (repos.json key)
        source_dir = os.path.join(local_path, package)                  # the checkout convention
        calibration = disc = None
        if os.path.isdir(source_dir):
            try:                                         # best-effort: a bad source dir -> single-industry
                disc = discovery.discover_calibrations(source_dir, package)
                calibration = disc.get("recommended")
            except Exception:                            # noqa: BLE001 -- discovery must never break lookup
                disc = None
        out[key] = ModelEntry(key=key, package=package, env_python=env_python,
                              version=rec.get("commit_sha"), calibration=calibration,
                              source_dir=source_dir, discovered=disc)
    return out


def lookup(model, path: str | None = None, *, require_env: bool = True) -> ModelEntry:
    """Resolve a repo key ('og-phl'), a package name ('ogphl'), or a CountryConfig (its ``og_repo``/
    ``og_package``) to its ModelEntry. Raises ModelNotInstalledError -- with an actionable message --
    if unregistered or (when ``require_env``) its interpreter is not on disk. ``require_env=False`` for
    link-side-only uses (e.g. reading the calibration menu, which needs the source dir, not the env).
    NEVER installs a model."""
    ident = str(getattr(model, "og_repo", None) or getattr(model, "og_package", None) or model)
    rp = registry_path(path)
    reg = load_registry(path)
    # Unless an explicit registry is pinned (the arg or $OGLINK_MODEL_REGISTRY -- the override/escape
    # hatch), a present MUIOGO install's register fills what the link's own lacks. On a key collision
    # the link's OWN registration wins: an explicit `models register` is a deliberate pin (e.g. a dev
    # worktree) that a later MUIOGO install of the same model must not silently shadow. A
    # missing/corrupt MUIOGO registry yields {} -> no-op.
    saw_muiogo = False
    if not path and not os.environ.get(ENV_VAR):
        muiogo = load_muiogo_registry()
        if muiogo:
            reg = {**muiogo, **reg}
            saw_muiogo = True
    entry = reg.get(ident) or next((e for e in reg.values() if e.package == ident), None)
    if entry is None:
        raise ModelNotInstalledError(
            f"No OG model registered for '{ident}'. Registry: {rp}"
            f"{' (+ MUIOGO install)' if saw_muiogo else ''}. Register your checkout under this EXACT key: "
            f"`oglink models register --path <dir> --key {ident}` -- the key must equal the "
            f"country's og_repo ('{ident}'); without --key it defaults to the directory's name, which is "
            f"wrong for worktrees/renamed folders. (Or install via the MUIOGO OG installer/tab, or set "
            f"${ENV_VAR} to a registry that has it.)")
    if require_env and not os.path.exists(entry.env_python):
        raise ModelNotInstalledError(
            f"OG model env for '{entry.key}' ({entry.package}) not found at {entry.env_python}. "
            f"Re-install/register that model (its interpreter moved or was never built).")
    return entry

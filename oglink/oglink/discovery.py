"""Link-side calibration discovery: enumerate a country OG package's calibration choices by READING ITS
SOURCE -- the param JSONs (plain files) and the PROD_DICT/CONS_DICT aggregation maps (literal dicts parsed
from the package source with ``ast``). No import of the country package and no subprocess into its env:
the dicts are guaranteed literals, so discovery is pure file-reading and runs entirely in the link env.
(Only the actual SOLVE needs the OG env -- that's irreducible; discovery does not.)

stdlib + ``contract`` only. The concordance logic itself stays in ``contract.Concordance.from_dicts`` (one
source of truth); discovery just supplies the dicts it reads from source.
"""
from __future__ import annotations

import ast
import glob
import json
import os

from .contract import Concordance


def _param_dim(params: dict, key: str, default: int = 1) -> int:
    """Read an integer dimension (M or I) from a param JSON whether plain or a paramtools value-object."""
    v = params.get(key, default)
    if isinstance(v, dict):
        v = v.get("value", v)
    if isinstance(v, list) and v:
        v = v[0].get("value") if isinstance(v[0], dict) else v[0]
    try:
        return int(v)
    except (TypeError, ValueError):
        return int(default)


def _shape(v):
    """Nested-list shape (rows, cols, ...) without importing numpy -- for DISPLAY only."""
    return [len(v)] + (_shape(v[0]) if v and isinstance(v[0], list) else []) if isinstance(v, list) else []


def _array_shape(params: dict, key: str):
    """The shape of a parameter array in the JSON (paramtools value-object aware), or None if absent."""
    if key not in params:
        return None
    v = params[key]
    if isinstance(v, dict):
        v = v.get("value", v)
    if isinstance(v, list) and v and isinstance(v[0], dict) and "value" in v[0]:
        v = v[0]["value"]
    return _shape(v) if isinstance(v, list) else None


def _literal_assign(tree: ast.Module, name: str):
    """The value of a top-level ``name = <literal>`` assignment, via ast.literal_eval, or None. Relies on
    the (guaranteed) invariant that PROD_DICT/CONS_DICT are literal dicts -- a computed value yields None
    (and the carrier is then simply unresolved, never silently wrong)."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            try:
                return ast.literal_eval(node.value)
            except (ValueError, SyntaxError, TypeError):
                return None
    return None


def read_package_dicts(pkg_dir: str):
    """(PROD_DICT, CONS_DICT) parsed as literals from the package source under ``pkg_dir`` -- WITHOUT
    importing the package. Scans its top-level ``*.py`` (``constants.py`` first), returning the first
    literal assignment found for each. Either is None if the package ships it elsewhere/computed."""
    files = sorted(glob.glob(os.path.join(pkg_dir, "*.py")),
                   key=lambda f: (os.path.basename(f) != "constants.py", f))   # constants.py first
    prod = cons = None
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        prod = prod if prod is not None else _literal_assign(tree, "PROD_DICT")
        cons = cons if cons is not None else _literal_assign(tree, "CONS_DICT")
        if prod is not None and cons is not None:
            break
    return prod, cons


def _read_sam(pkg_dir: str):
    """The package's SAM (``<pkg_dir>/data/*SAM*.csv``) as a DataFrame, or None -- best-effort, used only
    to report how diluted the route-A energy GOOD is. Needs pandas (in the link env); never fatal."""
    hits = glob.glob(os.path.join(pkg_dir, "data", "*SAM*.csv"))
    if not hits:
        return None
    try:
        import pandas as pd
        return pd.read_csv(min(hits), index_col=1, thousands=",").fillna(0)
    except Exception:    # noqa: BLE001 -- a missing/odd SAM just leaves the share unreported
        return None


def _good_electricity_share(sam, cons_dict, good_index, carrier="electricity"):
    """Electricity's value share of the resolved consumption good (route-A dilution), from the SAM, or
    None. <0.5 means the household 'energy good' is mostly NOT electricity (e.g. it's a broad Services or
    Energy-and-water composite) -- the demand-side wedge is heavily diluted. The PRODUCTION side has no
    analogue: the purity gate already guarantees the energy INDUSTRY is pure electricity (share 1.0)."""
    if sam is None or good_index is None:
        return None
    from . import aggregation as ag
    try:
        for g in ag.shares(sam, cons_dict, carrier, axis="consumption").groups:
            if g.index == good_index:
                return round(float(g.share), 4)
    except Exception:    # noqa: BLE001 -- SAM quirks must not break discovery
        return None
    return None


def iter_param_files(pkg_dir: str):
    """Yield (filename, params_dict) for each packaged ``*param*.json`` under ``pkg_dir``, sorted."""
    for path in sorted(glob.glob(os.path.join(pkg_dir, "*.json"))):
        if "param" not in os.path.basename(path).lower():
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                yield os.path.basename(path), json.load(fh)
        except (OSError, ValueError, UnicodeDecodeError):
            continue


def discover_calibrations(pkg_dir: str, package: str) -> dict:
    """Enumerate the package's calibration choices for the link to DISPLAY and the user to CHOOSE from --
    the explicit, auditable replacement for silently scanning + picking the first M>1 file. For each
    packaged param JSON: its shape (M x I), the industry/good NAMES (from PROD_DICT/CONS_DICT), and whether
    electricity is isolable at that aggregation (couplable). ``recommended`` is the lone couplable
    multisector candidate when unambiguous, else None (single-industry -> the energy channels skip).
    Pure file-reading -- runs in the link env, no country import, no subprocess."""
    prod, cons = read_package_dicts(pkg_dir)
    prod_names = list(prod) if isinstance(prod, dict) else None
    cons_names = list(cons) if isinstance(cons, dict) else None
    sam = _read_sam(pkg_dir)                                            # for the route-A good's dilution
    candidates = []
    for name, params in iter_param_files(pkg_dir):
        M, I = _param_dim(params, "M"), _param_dim(params, "I")
        names_map = prod_names is not None and len(prod_names) == M     # do PROD_DICT columns line up?
        con = Concordance.from_dicts(prod, cons) if (M > 1 and names_map and cons is not None) else None
        isolated = bool(con and con.energy_industry_index is not None)
        good_share = _good_electricity_share(sam, cons, con.energy_good_index) if con else None
        if M <= 1:
            reason = "single-industry calibration -- no electricity industry; energy channels skip"
        elif prod is None or cons is None:
            reason = f"{package} ships no literal PROD_DICT/CONS_DICT -- cannot identify the energy industry"
        elif not names_map:
            reason = f"PROD_DICT has {len(prod_names)} groups but this calibration is M={M} -- names do not map"
        elif isolated:
            reason = "electricity isolated as its own industry -- couplable on energy"
        else:
            reason = (con.unavailable.get("energy_industry_index")
                      or con.unavailable.get("energy_good_index") or "electricity not isolable")
        candidates.append({
            "file": name, "M": M, "I": I,
            "industries": prod_names if (M > 1 and names_map) else None,
            "goods": cons_names if (cons_names is not None and len(cons_names) == I) else None,
            "couplable": isolated,
            "energy_industry_index": (con.energy_industry_index if con else None),
            "energy_good_index": (con.energy_good_index if con else None),
            "energy_good_electricity_share": good_share,        # route-A dilution (<0.5 = mostly NOT electricity)
            "energy_good_diluted": (good_share is not None and good_share < 0.5),
            "reason": reason,
            "shapes": {k: _array_shape(params, k) for k in ("gamma", "epsilon", "Z", "alpha_c", "io_matrix")},
        })
    couplable = [c for c in candidates if c["couplable"]]
    return {"og_package": package, "source_dir": pkg_dir, "candidates": candidates,
            "couplable_count": len(couplable),
            "recommended": couplable[0]["file"] if len(couplable) == 1 else None}


def print_calibrations(findings: dict, emit) -> None:
    """Render the discovery menu via the ``emit`` callable (e.g. ``print``); ``*`` marks the auto-pick."""
    emit(f"  {findings['og_package']}: {len(findings['candidates'])} calibration(s), "
         f"{findings['couplable_count']} couplable on energy")
    for c in findings["candidates"]:
        mark = "*" if c["file"] == findings.get("recommended") else " "
        port = (f"energy industry={c['energy_industry_index']} good={c['energy_good_index']}"
                if c["couplable"] else "no energy coupling")
        inds = ", ".join(c["industries"]) if c["industries"] else "(unnamed)"
        emit(f"   {mark} {c['file']}  M={c['M']} I={c['I']}  [{port}]")
        emit(f"        industries: {inds}")
        if c["couplable"]:                                  # report the route-A (household demand) good's dilution
            gi, sh = c.get("energy_good_index"), c.get("energy_good_electricity_share")
            if gi is None:
                emit("        route-A: no energy consumption good (electricity not isolable in CONS_DICT)")
            elif sh is None:
                emit("        route-A good dilution: unknown (no SAM found to measure it)")
            else:
                emit(f"        route-A good is {sh:.0%} electricity"
                     + ("  -- DILUTED (mostly non-electricity; demand-side wedge is approximate)"
                        if c.get("energy_good_diluted") else ""))
        emit(f"        {c['reason']}")
    rec = findings.get("recommended")
    emit(f"  recommended: {rec if rec else '(single-industry -- energy channels skip)'}")

"""Link-side calibration discovery: reads a package's param JSONs + PROD_DICT/CONS_DICT (literals, via
ast) from SOURCE -- no country import, no subprocess. Synthetic package dirs keep these hermetic.
"""
from __future__ import annotations

import json

from oglink import discovery


def _mk_pkg(tmp_path, name, prod, cons, params):
    """A synthetic package source dir: constants.py (literal dicts) + the given param JSONs."""
    pkg = tmp_path / name
    pkg.mkdir()
    (pkg / "constants.py").write_text(f"PROD_DICT = {prod!r}\nCONS_DICT = {cons!r}\n")
    for fname, body in params.items():
        (pkg / fname).write_text(json.dumps(body))
    return str(pkg)


def test_discover_isolated_is_couplable_and_recommended(tmp_path):
    src = _mk_pkg(
        tmp_path, "ogiso",
        prod={"Ag": ["aagr"], "Energy": ["aelec"], "Rest": ["aoth"]},
        cons={"Food": ["cfood"], "Energy": ["celec", "cwatr"], "Rest": ["coth"]},
        params={"ogiso_default_parameters.json": {"M": 1, "I": 1},
                "ogiso_multisector_parameters.json": {"M": 3, "I": 3}})
    f = discovery.discover_calibrations(src, "ogiso")
    assert f["couplable_count"] == 1
    assert f["recommended"] == "ogiso_multisector_parameters.json"
    ms = next(c for c in f["candidates"] if c["M"] == 3)
    assert ms["couplable"] and (ms["energy_industry_index"], ms["energy_good_index"]) == (1, 1)
    assert ms["industries"] == ["Ag", "Energy", "Rest"]
    assert ms["energy_good_electricity_share"] is None        # no SAM shipped -> dilution unknown
    assert not next(c for c in f["candidates"] if c["M"] == 1)["couplable"]   # single-industry skips


def test_discover_fused_electricity_not_couplable(tmp_path):
    # electricity fused with water in one production group -> purity gate -> not couplable
    src = _mk_pkg(
        tmp_path, "ogfus",
        prod={"Ag": ["aagr"], "Utilities": ["aelec", "awatr"], "Rest": ["aoth"]},
        cons={"Food": ["cfood"], "Energy": ["celec"], "Rest": ["coth"]},
        params={"ogfus_multisector_parameters.json": {"M": 3, "I": 3}})
    f = discovery.discover_calibrations(src, "ogfus")
    assert f["couplable_count"] == 0 and f["recommended"] is None
    assert "not isolated" in f["candidates"][0]["reason"]


def test_discover_mismatched_prod_dict_not_couplable(tmp_path):
    # a calibration whose M != len(PROD_DICT): the names don't map -> refuse (no misaligned index)
    src = _mk_pkg(
        tmp_path, "ogmis",
        prod={"Ag": ["aagr"], "Energy": ["aelec"], "Rest": ["aoth"]},   # 3 groups
        cons={"Food": ["cfood"], "Energy": ["celec"], "Rest": ["coth"]},
        params={"ogmis_multisector_parameters.json": {"M": 4, "I": 5}})  # but M=4
    f = discovery.discover_calibrations(src, "ogmis")
    assert f["couplable_count"] == 0
    assert "do not map" in f["candidates"][0]["reason"]

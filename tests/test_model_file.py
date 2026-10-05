"""Guards on the OSeMOSYS model file and on what MUIOGO expects to find in it.

An upstream MUIO release can replace the model file wholesale, and git merges
that cleanly even when MUIOGO depends on something the new file drops. MUIO 5.7
did exactly that: it removed the energy-balance row (EBb4_..._ICR) that the
Duals view read its shadow price from. These tests fail loudly instead.
"""

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from Classes.Base import Config
from Classes.Case.OsemosysClass import Osemosys

MODEL = Path(Config.SOLVERs_FOLDER, Osemosys.MODEL_FILE_NAME)
DUALS = Path(Config.DATA_STORAGE, "Duals.json")


def _model_text():
    return MODEL.read_text(encoding="utf-8")


def test_solver_model_file_exists():
    assert MODEL.is_file(), f"solver model file missing: {MODEL}"


def test_model_file_page_shows_the_model_the_solver_uses(client):
    response = client.get("/readModelFile")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == _model_text()


def _constraint_names(model_text):
    return set(re.findall(r"^s\.t\.\s+(\w+)", model_text, flags=re.M))


def test_every_shadow_price_points_at_a_real_constraint():
    constraints = _constraint_names(_model_text())
    duals = json.loads(DUALS.read_text())
    missing = [
        (group, entry["id"], entry["name"])
        for group, entries in duals.items()
        for entry in entries
        if entry["name"] not in constraints
    ]
    assert not missing, (
        "Duals.json names constraints the model file does not have, so those "
        f"shadow prices would silently come out empty: {missing}"
    )


def test_model_declares_the_balance_level_sets_the_data_file_writes():
    model = _model_text()
    for name in ("COMMODITY_TS", "COMMODITY_S", "COMMODITY_AN"):
        assert re.search(rf"^set {name}\b", model, flags=re.M), name


def _comm_lists(*comms):
    fake = SimpleNamespace(genData={"osy-comm": list(comms)})
    return Osemosys.getAllCommLists(fake)


def test_commodity_without_balance_level_stays_timeslice():
    # Cases saved before MUIO 5.7 have no BalanceLevel on disk.
    lists = _comm_lists({"Comm": "ELC"}, {"Comm": "COA", "BalanceLevel": "An"})
    assert lists["Ts"] == ["ELC"]
    assert lists["An"] == ["COA"]
    assert lists["ALL"] == ["ELC", "COA"]


def test_unknown_balance_level_is_refused():
    # Otherwise the commodity would land in no balance set and go unbalanced.
    with pytest.raises(ValueError, match="unknown balance level"):
        _comm_lists({"Comm": "ELC", "BalanceLevel": "Weekly"})


def test_case_saved_before_a_new_parameter_still_generates(tmp_path):
    """MUIO 5.7 added Operational Profile. A case saved earlier has no entry for
    it, and generating its data file must write the default, not crash."""
    import io

    from Classes.Case.DataFileClass import DataFile

    rytts_path = tmp_path / "RYTTs.json"
    rytts_path.write_text("{}")
    out = io.StringIO()
    fake = SimpleNamespace(
        ryttsPath=rytts_path,
        RYTTs=lambda data: {},
        PARAM={"RYTTs": {"OP": "OperationalProfile"}},
        defaultValue={"OP": 0},
        techIDs=["T1"],
        timesliceIDs=["L1"],
        yearIDs=["2020"],
        scOrder=[],
        f=out,
    )
    DataFile.gen_RYTTs(fake)
    assert out.getvalue() == "param OperationalProfile default 0 := \n;\n"

import io
import json

from API.Classes.Case.DataFileClass import DataFile


def test_gen_rycn_uses_default_when_all_active_scenarios_are_null(tmp_path):
    years = ("2020", "2021")
    constraints = ("EV", "NUCLEAR")
    path = tmp_path / "RYCn.json"
    path.write_text(json.dumps({
        "UCC": {
            "BASE": [
                {"ConId": "EV", "2020": 0.0, "2021": 0.0},
                {"ConId": "NUCLEAR", "2020": None, "2021": None},
            ],
            "EV_SCENARIO": [
                {"ConId": "EV", "2020": 100.0, "2021": 325.513},
                {"ConId": "NUCLEAR", "2020": None, "2021": None},
            ],
        }
    }))

    data_file = object.__new__(DataFile)
    data_file.rycnPath = path
    data_file.PARAM = {"RYCn": {"UCC": "UDCConstant"}}
    data_file.defaultValue = {"UCC": 0.0}
    data_file.years = "2020 2021 "
    data_file.yearIDs = list(years)
    data_file.conIDs = list(constraints)
    data_file.conMap = {name: name for name in constraints}
    data_file.scOrder = [
        {"ScId": "BASE", "Active": True},
        {"ScId": "EV_SCENARIO", "Active": True},
    ]
    data_file.f = io.StringIO()

    data_file.gen_RYCn()

    generated = data_file.f.getvalue()
    assert "EV 100.0 325.513" in generated
    assert "NUCLEAR 0.0 0.0" in generated

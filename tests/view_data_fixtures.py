"""Disposable source tables for testing individual cross-parameter cell edits."""

import copy
import json
from pathlib import Path
import shutil


CASE_NAME = "ViewFixture"
CATALOG = Path(__file__).resolve().parents[1] / "WebAPP" / "DataStorage"


def make_view_data_case(storage):
    storage = Path(storage)
    case = storage / CASE_NAME
    (case / "view").mkdir(parents=True)
    catalog = json.loads((CATALOG / "Parameters.json").read_text())
    selected = {
        "RT": ["OL"], "RE": ["MPEL"], "RYT": ["CC"], "RYC": ["SAD"],
        "RYE": ["EP"], "RYTM": ["VC"], "RYTC": ["INCR"],
        "RYTCM": ["OAR"], "RYTEM": ["EAR"], "RYTTs": ["CF"],
        "RYCTs": ["SDP"], "RYTCn": ["CAM"],
    }
    parameters = {
        group: [row for row in catalog[group] if row["id"] in ids]
        for group, ids in selected.items()
    }
    (storage / "Parameters.json").write_text(json.dumps(parameters))
    for name in ("Variables.json", "Duals.json", "Indicators.json"):
        shutil.copyfile(CATALOG / name, storage / name)

    gen = {
        "osy-version": "5.7", "osy-casename": CASE_NAME,
        "osy-currency": "USD", "osy-years": ["2030", "2031"], "osy-mo": "2",
        "osy-tech": [
            {"TechId": name, "Tech": name, "Desc": name,
             "CapUnitId": "GW", "ActUnitId": "PJ", "TG": [],
             "IAR": ["C1"], "OAR": ["C2"], "EAR": ["E1"],
             "INCR": ["C1"], "ITCR": ["C1"]}
            for name in ("T1", "T2")
        ],
        "osy-comm": [{"CommId": name, "Comm": name, "Desc": name,
                      "UnitId": "PJ", "BalanceLevel": "Ts"} for name in ("C1", "C2")],
        "osy-emis": [{"EmisId": name, "Emis": name, "Desc": name,
                      "UnitId": "Ton"} for name in ("E1", "E2")],
        "osy-ts": [{"TsId": name, "Ts": name, "Desc": name,
                    "SE": "SE1", "DT": "DT1", "DTB": "DB1"} for name in ("TS1", "TS2")],
        "osy-constraints": [{"ConId": name, "Con": name, "Desc": name,
                             "Tag": 1, "CM": ["T1"]} for name in ("CN1", "CN2")],
        "osy-scenarios": [{"ScenarioId": name, "Scenario": name, "Desc": name,
                           "Active": True} for name in ("SC_0", "SC_1")],
        "osy-stg": [], "osy-techGroups": [], "osy-indicators": [],
        "osy-se": [{"SeId": "SE1", "Se": "1"}],
        "osy-dt": [{"DtId": "DT1", "Dt": "1"}],
        "osy-dtb": [{"DtbId": "DB1", "Dtb": "1"}],
    }
    (case / "genData.json").write_text(json.dumps(gen))
    (case / "view" / "resData.json").write_text('{"osy-cases": []}')

    def annual(*rows):
        return [dict(row, **{"2030": 10.0 + index, "2031": 50.0 + index})
                for index, row in enumerate(rows)]

    sources = {
        "RT": {"OL": [{"T1": 20, "T2": 30}]},
        "RE": {"MPEL": [{"E1": 100, "E2": 200}]},
        "RYT": {"CC": annual({"TechId": "T1"}, {"TechId": "T2"})},
        "RYC": {"SAD": annual({"CommId": "C1"}, {"CommId": "C2"})},
        "RYE": {"EP": annual({"EmisId": "E1"}, {"EmisId": "E2"})},
        "RYTM": {"VC": annual(*({"TechId": tech, "MoId": mode}
                                 for tech in ("T1", "T2") for mode in (1, 2)))},
        "RYTC": {"INCR": annual(*({"TechId": "T1", "CommId": comm} for comm in ("C1", "C2")))},
        "RYTCM": {"OAR": annual(*({"TechId": "T1", "CommId": comm, "MoId": mode}
                                    for comm in ("C1", "C2") for mode in (1, 2)))},
        "RYTEM": {"EAR": annual(*({"TechId": "T1", "EmisId": emission, "MoId": mode}
                                    for emission in ("E1", "E2") for mode in (1, 2)))},
        "RYTTs": {"CF": annual(*({"TechId": "T1", "TsId": ts} for ts in ("TS1", "TS2")))},
        "RYCTs": {"SDP": annual(*({"CommId": "C1", "TsId": ts} for ts in ("TS1", "TS2")))},
        "RYTCn": {"CAM": annual(*({"TechId": "T1", "ConId": con} for con in ("CN1", "CN2")))},
    }
    for group, entries in sources.items():
        document = {}
        for param, rows in entries.items():
            inherited = copy.deepcopy(rows)
            for row in inherited:
                for key in row:
                    if key in ("2030", "2031", "T1", "T2", "E1", "E2"):
                        row[key] = None
            document[param] = {"SC_0": rows, "SC_1": inherited}
        (case / f"{group}.json").write_text(json.dumps(document, indent=4))
    return case

"""Regression checks for MUIO #66; matrix checks never optimize a case."""

import json
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from Classes.Base import Config
from Classes.Case.DataFileClass import DataFile
from Classes.Case.HelpersClass import Helpers
from Classes.Case.OsemosysClass import Osemosys


@pytest.mark.parametrize("timeslice_activity", [False, True])
def test_annual_flows_export_without_requiring_timeslice_activity(tmp_path, timeslice_activity):
    variables = json.loads(Path(Config.DATA_STORAGE, "Variables.json").read_text())
    data = {
        "OutputActivityRatio": [
            ("RE1", "F", "T", "2020", "1", "2"),
            ("RE1", "F", "T", "2020", "2", "3"),
            ("RE1", "F", "T", "2020", "3", "1"),
            ("RE1", "F", "IDLE", "2020", "1", "1"),
        ],
        "InputActivityRatio": [
            ("RE1", "F", "T", "2020", "1", "0.5"),
            ("RE1", "F", "T", "2020", "2", "2"),
            ("RE1", "F", "T", "2020", "3", "1"),
        ],
        "YearSplit": [("RE1", "2020", "L", "1")],
        "EmissionActivityRatio": [],
    }
    fake = SimpleNamespace(
        genData={},
        getYears=lambda: ["2020"],
        getTechNames=lambda: ["T", "IDLE"],
        parseDataFile=lambda _: data,
        VAR_BY_NAME=Helpers.build_var_by_name(variables),
        DUALS_BY_NAME={},
        IND_BY_NAME={},
    )
    records = [
        f"{i} TotalAnnualTechnologyActivityByMode(RE1,T,{mode},2020) {activity} 0"
        for i, (mode, activity) in enumerate([(1, 20), (2, 3), (3, 0)])
    ]
    if timeslice_activity:
        records += [
            f"{i + 3} RateOfActivity(RE1,L,T,{mode},2020) {activity} 0"
            for i, (mode, activity) in enumerate([(1, 20), (2, 3), (3, 0)])
        ]
    results = tmp_path / "results.txt"
    results.write_text("Optimal - objective value 23\n" + "\n".join(records) + "\n")

    DataFile.generateCSVfromCBC(fake, None, results, tmp_path)

    for name, expected in (
        ("ProductionByTechnologyByMode", [40.0, 9.0]),
        ("UseByTechnologyByMode", [10.0, 6.0]),
    ):
        flows = pd.read_csv(tmp_path / "csv" / f"{name}.csv")
        assert list(flows.columns) == ["r", "t", "m", "f", "y", name]
        assert flows["t"].tolist() == ["T", "T"]
        assert flows["m"].tolist() == [1, 2]
        assert flows[name].tolist() == expected
        assert not flows.isna().any().any()
        timeslice_file = tmp_path / "csv" / f"{name}Ts.csv"
        assert timeslice_file.exists() == timeslice_activity
        if timeslice_activity:
            assert pd.read_csv(timeslice_file)[name + "Ts"].sum() == sum(expected)


def _minimal_data(model, level, specified, accumulated):
    """One producer, no storage/emissions/UDCs, and no optimization required."""
    sets = {
        "REGION": "RE1", "TECHNOLOGY": "T", "COMMODITY": "F",
        "YEAR": "2020", "TIMESLICE": "L", "SEASON": "1",
        "DAYTYPE": "1", "DAILYTIMEBRACKET": "1", "MODE_OF_OPERATION": "1",
        "EMISSION": "", "STORAGE": "", "STORAGEINTRADAY": "",
        "STORAGEINTRAYEAR": "", "UDC": "", "INPUTxFUEL": "",
        "MODEperTECHNOLOGY[T]": "1",
        "MODExTECHNOLOGYperFUELout[F]": "(1,T)",
        "MODExTECHNOLOGYperFUELin[F]": "",
        "INPUTxNEWxCAPACITYperFUEL[F]": "",
        "INPUTxTOTALxCAPACITYperFUEL[F]": "",
    }
    sets.update({"COMMODITY_" + s: "F" if s == level else "" for s in ("TS", "S", "AN")})
    defaults = dict.fromkeys([
        "OperationalLife", "CapacityFactor", "AvailabilityFactor", "CapacityToActivityUnit",
        "OutputActivityRatio", "YearSplit", "SpecifiedDemandProfile", "Conversionls",
        "Conversionld", "Conversionlh", "CapitalRecoveryFactor", "PvAnnuity", "VariableCost",
    ], 1)
    defaults.update({
        "DiscountRate": 0.05, "DiscountRateIdv": 0.05,
        "SpecifiedAnnualDemand": specified, "AccumulatedAnnualDemand": accumulated,
    })
    # All other inputs are zero unless a nonbinding upper limit is needed.
    # Derived parameters (TechnologyBalanceLevel) are supplied by the model.
    declarations = re.findall(r"^param (\w+)", model.read_text(), flags=re.M)
    lines = [f"set {name} := {members};" for name, members in sets.items()]
    for name in declarations:
        if name == "TechnologyBalanceLevel":
            continue
        default = defaults.get(name, 999999 if "UpperLimit" in name or "MaxCapacity" in name else 0)
        lines.append(f"param {name} default {default} := ;")
    return "\n".join(lines) + "\nend;\n"


@pytest.mark.parametrize("model_name", [Osemosys.MODEL_FILE_NAME, "model.v.5.7.txt"])
@pytest.mark.parametrize("level,specified,accumulated,valid", [
    ("AN", 100, 0, False),
    ("AN", 0, 100, True),
    ("AN", 0, 0, True),
    ("TS", 100, 0, True),
    ("S", 100, 0, True),
])
def test_demand_validation_during_matrix_generation(
    tmp_path, model_name, level, specified, accumulated, valid,
):
    glpsol = shutil.which("glpsol")
    if glpsol is None:
        pytest.skip("GLPK is required for matrix-only validation")
    model = Path(Config.SOLVERs_FOLDER, model_name)
    data = tmp_path / "data.txt"
    data.write_text(_minimal_data(model, level, specified, accumulated))
    lp = tmp_path / "lp.lp"

    result = subprocess.run(
        [glpsol, "--check", "-m", str(model), "-d", str(data), "--wlp", str(lp)],
        capture_output=True, text=True, timeout=30,
    )
    output = result.stdout + result.stderr
    if valid:
        assert result.returncode == 0, output
        assert lp.is_file()
        if specified or accumulated:
            assert ">= 100" in lp.read_text()
    else:
        assert result.returncode != 0, output
        assert not lp.exists()
        assert "Annual commodity F (region RE1, year 2020) has SpecifiedAnnualDemand" in output
        assert "Use AccumulatedAnnualDemand" in output


@pytest.mark.parametrize("model_name", [Osemosys.MODEL_FILE_NAME, "model.v.5.7.txt"])
@pytest.mark.parametrize("value", [-1, 0, 999999])
@pytest.mark.parametrize("parameter,constraint", [
    ("TotalTechnologyAnnualActivityUpperLimit", "AAC2_TotalAnnualTechnologyActivityUpperLimit"),
    ("TotalTechnologyModelPeriodActivityUpperLimit", "TAC2_TotalModelHorizonTechnologyActivityUpperLimit"),
    ("TotalAnnualMaxCapacityInvestment", "NCC1_TotalAnnualMaxNewCapacityConstraint"),
    ("TotalAnnualMaxCapacity", "TCC1_TotalAnnualMaxCapacityConstraint"),
    ("AnnualEmissionLimit", "E8_AnnualEmissionsLimit"),
    ("ModelPeriodEmissionLimit", "E9_ModelPeriodEmissionsLimit"),
])
def test_unlimited_upper_limits_match_across_model_variants(
    tmp_path, model_name, value, parameter, constraint,
):
    glpsol = shutil.which("glpsol")
    if glpsol is None:
        pytest.skip("GLPK is required for matrix-only validation")
    model = Path(Config.SOLVERs_FOLDER, model_name)
    contents = _minimal_data(model, "TS", 100, 0)
    contents = contents.replace(
        "set EMISSION := ;",
        "set EMISSION := E;\n"
        "set MODExTECHNOLOGYperEMISSION[E] := (1,T);\n"
        "set MODExTECHNOLOGYperEMISSIONChange[E] := ;",
    ).replace("param EmissionActivityRatio default 0 := ;", "param EmissionActivityRatio default 1 := ;")
    contents = re.sub(
        rf"param {parameter} default [^ ]+ := ;", f"param {parameter} default {value} := ;", contents,
    )
    data = tmp_path / "data.txt"
    data.write_text(contents)
    lp = tmp_path / "lp.lp"

    result = subprocess.run(
        [glpsol, "--check", "-m", str(model), "-d", str(data), "--wlp", str(lp)],
        capture_output=True, text=True, timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    rows = re.findall(rf"^ *{constraint}\(.*?(?=^ [A-Za-z]|^\w|\Z)", lp.read_text(), flags=re.M | re.S)
    assert bool(rows) == (value != -1)
    if rows:
        upper_bound = re.search(r"<= (\S+)", rows[0])
        assert upper_bound is not None
        assert float(upper_bound[1]) == value

"""Regression checks for commodity-price export; never run an optimizer."""

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from Classes.Base import Config
from Classes.Case import CommodityPrice
from Classes.Case.DataFileClass import DataFile


def _input_data():
    return {
        "YearSplit": [("R", "2030", "D", "0.25"), ("R", "2030", "N", "0.75")],
        "SpecifiedDemandProfile": [],
        "InputActivityRatio": [("R", "F", "T", "2030", "1", "1")],
        "DiscountRate": [("R", "0")],
    }


def _gen_data(level="Ts"):
    return {
        "osy-comm": [{"Comm": "F", "BalanceLevel": level}],
        "osy-se": [{"SeId": "SE1", "Se": 1}],
        "osy-ts": [{"Ts": "D", "SE": "SE1"}, {"Ts": "N", "SE": "SE1"}],
    }


def _records(scale=1):
    return [
        ("EB_TimesliceBalance", "R,D,F,2030", 0, 40),
        ("EB_TimesliceBalance", "R,N,F,2030", 0, 10),
        ("EBb4_EnergyBalanceEachYear4_ICR", "R,F,2030", 0, 0),
        ("RateOfActivity", "R,D,T,1,2030", scale, 0),
        ("RateOfActivity", "R,N,T,1,2030", 3 * scale, 0),
    ]


@pytest.mark.parametrize("scale", [1, 0.00001])
@pytest.mark.parametrize("price_scale", [1, 0.000001])
def test_export_keeps_use_weights_when_activity_is_small(tmp_path, scale, price_scale, monkeypatch):
    writes = []
    original_write = CommodityPrice.write_csv

    def track_write(results, *args):
        writes.append(results[["value", "dual"]].copy())
        return original_write(results, *args)

    monkeypatch.setattr(CommodityPrice, "write_csv", track_write)
    result = tmp_path / "results.txt"
    result.write_text(
        "Optimal - objective value 1\n"
        + "".join(
            f"{i} {p}({ids}) {v:.10g} {d * price_scale:.10g}\n" for i, (p, ids, v, d) in enumerate(_records(scale))
        )
    )
    fake = SimpleNamespace(
        getYears=lambda: ["2030"],
        getTechNames=lambda: ["T"],
        parseDataFile=lambda _: _input_data(),
        genData=_gen_data(),
        VAR_BY_NAME={},
        DUALS_BY_NAME={},
        IND_BY_NAME={},
    )
    DataFile.generateCSVfromCBC(fake, None, result, tmp_path)
    assert fake.postprocessWarnings == []
    out = pd.read_csv(tmp_path / "csv" / "CommodityMarginalPrice.csv")
    # Use is scale*0.25 in D and 3*scale*0.75 in N: weights 10%/90%.
    assert out.CommodityMarginalPrice.iloc[0] == pytest.approx(13.0 * price_scale)
    assert len(writes) == 1
    assert writes[0]["value"].iloc[3] == scale
    assert writes[0]["dual"].iloc[0] == pytest.approx(40 * price_scale, rel=1e-14, abs=0)


def test_failed_regeneration_removes_preexisting_price(tmp_path):
    old = tmp_path / "CommodityMarginalPrice.csv"
    old.write_text("r,f,y,CommodityMarginalPrice\nR,F,2030,999\n")
    results = pd.DataFrame(_records(), columns=["parameter", "id", "value", "dual"])
    warning = CommodityPrice.write_csv_or_warn(results, {}, _gen_data(), 2030, tmp_path)
    assert warning is not None
    assert not old.exists(), "The old price is still consumable after the warning claims it is missing"


def test_regenerating_old_run_does_not_use_current_balance_level(tmp_path):
    results = pd.DataFrame(_records(), columns=["parameter", "id", "value", "dual"])
    results.loc[results.parameter == "EB_TimesliceBalance", "parameter"] = "EBa11_EnergyBalanceEachTS5"
    # These are old timeslice results. The user has since changed F to annual in the editor.
    out = CommodityPrice.write_csv(results, _input_data(), _gen_data("An"), 2030, tmp_path)
    assert out.CommodityMarginalPrice.iloc[0] == pytest.approx(13.0)


def test_rerun_cleanup_removes_cached_commodity_price(tmp_path):
    run = "REF"
    res = tmp_path / "res"
    view = tmp_path / "view"
    (res / run / "csv").mkdir(parents=True)
    view.mkdir()
    cached = {"CMP_d": {run: [{"Comm": "F", "2030": 999}]}}
    cache_file = view / "RYC.json"
    cache_file.write_text(json.dumps(cached))
    fake = SimpleNamespace(
        resultsPath=res,
        viewFolderPath=view,
        VARIABLES=json.loads((Path(Config.DATA_STORAGE) / "Variables.json").read_text()),
        DUALS=json.loads((Path(Config.DATA_STORAGE) / "Duals.json").read_text()),
        IND_GROUPED={},
    )
    DataFile.deleteCaseResultsJSON(fake, run)
    assert run not in json.loads(cache_file.read_text()).get("CMP_d", {}), (
        "An old price remains visible after rerun cleanup"
    )


@pytest.mark.parametrize("has_csv", [False, True])
def test_viewer_refresh_replaces_or_removes_old_price(tmp_path, monkeypatch, has_csv):
    monkeypatch.setattr(Config, "DATA_STORAGE", tmp_path)
    case = tmp_path / "C"
    view = case / "view"
    csv = case / "res" / "REF" / "csv"
    view.mkdir(parents=True)
    csv.mkdir(parents=True)
    cache = view / "RYC.json"
    cache.write_text(
        json.dumps({"CMP_d": {"REF": [{"Comm": "F", "2030": 999}], "OTHER": [{"Comm": "F", "2030": 777}]}})
    )
    if has_csv:
        (csv / "CommodityMarginalPrice.csv").write_text("r,f,y,CommodityMarginalPrice\nR,F,2030,13\n")
    fake = SimpleNamespace(
        case="C",
        viewFolderPath=view,
        VAR_BY_NAME={},
        IND_BY_NAME={},
        DUALS_BY_NAME={"CommodityMarginalPrice": {"id": "CMP_d", "group": "RYC"}},
    )
    DataFile.generateResultsViewer(fake, "REF")
    saved = json.loads(cache.read_text())["CMP_d"]
    assert saved["OTHER"] == [{"Comm": "F", "2030": 777}]
    if has_csv:
        assert saved["REF"] == [{"Comm": "F", "2030": 13}]
    else:
        assert "REF" not in saved


def test_failed_write_removes_partial_price(tmp_path, monkeypatch):
    output = tmp_path / "CommodityMarginalPrice.csv"

    def fail(*args):
        output.write_text("r,f,y,CommodityMarginalPrice\nR,F")
        raise OSError("interrupted write")

    monkeypatch.setattr(CommodityPrice, "write_csv", fail)
    warning = CommodityPrice.write_csv_or_warn(None, None, None, None, tmp_path)
    assert warning
    assert not output.exists()


def test_failed_invalidation_blocks_postprocessing(tmp_path, monkeypatch):
    def fail_write(*args):
        raise ValueError("invalid inputs")

    def fail_unlink(*args, **kwargs):
        raise PermissionError("cannot invalidate price")

    monkeypatch.setattr(CommodityPrice, "write_csv", fail_write)
    monkeypatch.setattr(Path, "unlink", fail_unlink)
    with pytest.raises(PermissionError, match="cannot invalidate price"):
        CommodityPrice.write_csv_or_warn(None, None, None, None, tmp_path)


@pytest.mark.parametrize(
    "balance,expected",
    [
        ("EB_TimesliceBalance", "Ts"),
        ("EBa11_EnergyBalanceEachTS5", "Ts"),
        ("EB_SeasonalBalance", "Se"),
        ("EB_AnnualBalance", "An"),
    ],
)
def test_resolution_comes_from_result_rows(balance, expected):
    ids = "R,F,2030" if expected == "An" else "R,L,F,2030"
    results = pd.DataFrame({"parameter": [balance, "EBb4_EnergyBalanceEachYear4_ICR"], "id": [ids, "R,F,2030"]})
    assert CommodityPrice._solved_levels(results) == {"F": expected}

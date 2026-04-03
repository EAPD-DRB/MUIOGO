"""
ResultAdapter.py
================
Dimension-agnostic extraction engine for CBC / GLPK solver outputs.
"""

import sys
sys.dont_write_bytecode = True  # SeaCelo check — must precede all other imports

import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from Classes.Base import Config
from Classes.Base.MetadataResolver import MetadataResolver, VariableNotFoundError

log = logging.getLogger(__name__)

class SecurityError(PermissionError):
    """Raised when a requested write path escapes the DATA_STORAGE root."""

class ExtractionError(RuntimeError):
    """Raised when the result file cannot be parsed."""

def _assert_path(value: object, label: str) -> Path:
    if not isinstance(value, Path):
        raise TypeError(
            f"ResultAdapter requires Path objects, got {type(value).__name__} "
            f"for parameter '{label}'. Cast your string with Path(...)."
        )
    return value

def _assert_within_storage(output_path: Path) -> None:
    storage = Config.DATA_STORAGE.resolve()
    target = output_path.resolve()

    try:
        within = target.is_relative_to(storage)
    except AttributeError:
        try:
            from os.path import commonpath
            within = commonpath([str(storage), str(target)]) == str(storage)
        except ValueError:
            within = False

    if not within:
        raise SecurityError(
            f"ResultAdapter refused to write outside DATA_STORAGE.\n"
            f"  Attempted path : {target}\n"
            f"  Allowed root   : {storage}\n"
            "Ensure 'output_path' is inside Config.DATA_STORAGE."
        )

class ResultAdapter:

    def __init__(self) -> None:
        self._resolver = MetadataResolver()

    def extract(
        self,
        results_file: Path,
        data_file: Path,
        output_path: Path,
        start_year: int,
        discount_rate_series: Optional[pd.DataFrame] = None,
    ) -> list[Path]:
        _assert_path(results_file, "results_file")
        _assert_path(data_file, "data_file")
        _assert_path(output_path, "output_path")

        _assert_within_storage(output_path)
        _assert_within_storage(results_file)

        csv_dir = output_path / "csv"
        csv_dir.mkdir(parents=True, exist_ok=True)

        raw_df = self._read_results(results_file)
        if raw_df is None or raw_df.empty:
            log.warning("ResultAdapter: results file is empty — no CSVs written.")
            return []

        if discount_rate_series is None:
            discount_rate_series = self._read_discount_rate(data_file)

        written: list[Path] = []
        seen_params = set(raw_df["parameter"].unique())

        for var_name in seen_params:
            try:
                meta = self._resolver.get_var_metadata(var_name)
            except VariableNotFoundError:
                continue

            try:
                csv_path = self._process_variable(
                    var_name=var_name,
                    meta=meta,
                    raw_df=raw_df,
                    csv_dir=csv_dir,
                    start_year=start_year,
                    discount_rate_df=discount_rate_series,
                )
                if csv_path is not None:
                    written.append(csv_path)
            except Exception as exc:  # noqa: BLE001
                log.error(
                    "ResultAdapter: failed to process '%s': %s", var_name, exc
                )

        return written

    def _read_results(self, results_file: Path) -> Optional[pd.DataFrame]:
        if not results_file.is_file():
            raise ExtractionError(
                f"ResultAdapter: results file not found: '{results_file}'"
            )
        try:
            df = pd.read_csv(results_file, sep="\t", header=None, names=["raw"])
        except Exception as exc:
            raise ExtractionError(
                f"ResultAdapter: cannot read '{results_file}': {exc}"
            ) from exc

        df["raw"] = df["raw"].str.lstrip(" *\n\t")
        if df.empty:
            return None

        split = df["raw"].str.split(")", expand=True, n=1)
        if split.shape[1] < 2:
            return None

        df = df.copy()
        df["lhs"] = split[0].str.strip()
        df["rhs"] = split[1].str.strip()

        mask = df["lhs"].str.contains(r"\(", na=False)
        df = df[mask].copy()
        if df.empty:
            return None

        value_split = df["rhs"].str.split(expand=True)
        df["value"] = pd.to_numeric(value_split[0], errors="coerce").round(6)
        df["dual"] = pd.to_numeric(
            value_split[1] if value_split.shape[1] > 1 else None,
            errors="coerce",
        ).round(6)

        lhs_split = df["lhs"].str.split("(", expand=True, n=1)
        df["parameter"] = (
            lhs_split[0].str.split().str[-1]
        )
        df["id"] = lhs_split[1].str.strip() if lhs_split.shape[1] > 1 else ""

        df = df.dropna(subset=["parameter"])
        return df[["parameter", "id", "value", "dual"]].reset_index(drop=True)

    def _read_discount_rate(self, data_file: Path) -> pd.DataFrame:
        try:
            from Classes.Case.DataFileClass import DataFile  # noqa: PLC0415
            parsed = DataFile.parseDataFile(None, data_file)  # type: ignore[arg-type]
            from Classes.Base.Config import PARAMETERS_C_full  # noqa: PLC0415
            dr = pd.DataFrame(
                parsed["DiscountRate"],
                columns=PARAMETERS_C_full["DiscountRate"],
            )
            dr["DiscountRate"] = dr["DiscountRate"].astype(float)
            return dr[["r", "DiscountRate"]]
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "ResultAdapter: could not derive DiscountRate from data file "
                "(%s) — DUAL adjustments may be inaccurate.", exc
            )
            return pd.DataFrame(columns=["r", "DiscountRate"])

    def _process_variable(
        self,
        var_name: str,
        meta: dict,
        raw_df: pd.DataFrame,
        csv_dir: Path,
        start_year: int,
        discount_rate_df: pd.DataFrame,
    ) -> Optional[Path]:
        dimensions: list[str] = meta["dimensions"]
        var_type: str = meta["type"]

        df_var = raw_df[raw_df["parameter"] == var_name].copy()
        if df_var.empty:
            return None

        try:
            dim_cols = df_var["id"].str.split(",", expand=True)
            if dim_cols.shape[1] != len(dimensions):
                return None
            for i, dim in enumerate(dimensions):
                df_var[dim] = dim_cols[i].str.strip()
        except Exception:
            return None

        value_col = "dual" if var_type == "DUAL" else "value"
        result_cols = dimensions + [value_col]
        df_out = df_var[result_cols].rename(columns={value_col: var_name})

        if var_type == "DUAL" and not discount_rate_df.empty and "y" in dimensions:
            df_out["y"] = df_out["y"].astype(int)
            df_merged = pd.merge(df_out, discount_rate_df, on="r", how="left")
            df_merged[var_name] = df_merged[var_name] * (
                (1 + df_merged["DiscountRate"]) ** (
                    df_merged["y"] - start_year + 0.5
                )
            )
            df_out = df_merged[dimensions + [var_name]]

        out_path = csv_dir / f"{var_name}.csv"
        df_out.to_csv(out_path, index=False)
        return out_path

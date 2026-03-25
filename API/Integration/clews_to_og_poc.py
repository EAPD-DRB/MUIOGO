from pathlib import Path

import pandas as pd

from Classes.Base import Config


def _resolve_variable_name(csv_path: str, variable_name: str | None) -> str:
    if variable_name:
        return variable_name
    return Path(csv_path).stem


def load_clews_result_csv(
    csv_path: str, variable_name: str | None = None
) -> pd.DataFrame:
    """
    Load and validate a repository-style CLEWS result CSV.

    The PoC intentionally relies on repository metadata rather than guessed
    CLEWS-to-OG-Core mappings. It validates that the CSV contains the expected
    OSeMOSYS dimensions and one numeric value column matching the variable name.
    """

    resolved_name = _resolve_variable_name(csv_path, variable_name)
    expected_dims = Config.VARIABLES_C.get(resolved_name)
    if expected_dims is None:
        raise ValueError(f"Unsupported CLEWS result variable: {resolved_name}")

    df = pd.read_csv(csv_path)
    required_columns = expected_dims + [resolved_name]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Missing expected columns for {resolved_name}: {missing_columns}"
        )

    normalized = df[required_columns].copy()
    normalized[resolved_name] = pd.to_numeric(normalized[resolved_name], errors="raise")
    return normalized


def poc_pivot_clews_data(
    csv_path: str, variable_name: str | None = None
) -> pd.DataFrame:
    """
    Proof of concept for repository-grounded CLEWS result extraction.

    For variables that include both `y` and `t` dimensions, collapse any extra
    dimensions by summing over `(y, t)` and return a year-by-technology matrix.
    """

    normalized = load_clews_result_csv(csv_path, variable_name)
    resolved_name = _resolve_variable_name(csv_path, variable_name)
    expected_dims = Config.VARIABLES_C[resolved_name]

    if "y" not in expected_dims or "t" not in expected_dims:
        raise ValueError(
            f"{resolved_name} cannot be pivoted by this PoC because it does not "
            "include both 'y' and 't' dimensions."
        )

    grouped = (
        normalized.groupby(["y", "t"], as_index=False)[resolved_name]
        .sum()
        .sort_values(["y", "t"])
    )
    matrix = (
        grouped.pivot(index="y", columns="t", values=resolved_name)
        .fillna(0)
        .sort_index()
        .sort_index(axis=1)
    )
    matrix.index.name = "Year"
    matrix.columns.name = "Technology"
    return matrix

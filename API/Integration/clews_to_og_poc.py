import json
from numbers import Number
from pathlib import Path

import pandas as pd

from Classes.Base import Config


def _resolve_variable_name(csv_path: str, variable_name: str | None) -> str:
    if variable_name:
        return variable_name
    return Path(csv_path).stem


def _infer_case_and_run_names(
    run_root: str | Path | None,
    case_name: str | None,
    run_name: str | None,
) -> tuple[str | None, str | None]:
    if run_root is None:
        return case_name, run_name

    run_root_path = Path(run_root)
    resolved_run = run_name or run_root_path.name
    resolved_case = case_name
    if resolved_case is None and run_root_path.parent.name == "res":
        resolved_case = run_root_path.parent.parent.name
    return resolved_case, resolved_run


def _to_json_scalar(value):
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _sorted_unique(values) -> list:
    normalized = [_to_json_scalar(value) for value in values]
    if all(isinstance(value, Number) for value in normalized):
        return sorted(normalized)
    return sorted(normalized, key=str)


def _display_path(path: str | Path, run_root: str | Path | None) -> str:
    path_obj = Path(path)
    if run_root is None:
        return str(path_obj)

    try:
        return str(path_obj.relative_to(Path(run_root)))
    except ValueError:
        return str(path_obj)


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


def build_clews_input_manifest(
    csv_path: str,
    run_root: str | Path | None = None,
    variable_name: str | None = None,
    case_name: str | None = None,
    run_name: str | None = None,
) -> dict:
    normalized = load_clews_result_csv(csv_path, variable_name)
    resolved_name = _resolve_variable_name(csv_path, variable_name)
    expected_dims = Config.VARIABLES_C[resolved_name]
    resolved_case, resolved_run = _infer_case_and_run_names(
        run_root, case_name, run_name
    )

    input_record = {
        "variable_name": resolved_name,
        "source_csv": _display_path(csv_path, run_root),
        "dimensions": expected_dims,
        "value_column": resolved_name,
        "row_count": int(len(normalized)),
        "dimension_members": {
            dim: _sorted_unique(normalized[dim].dropna().unique().tolist())
            for dim in expected_dims
        },
    }
    if "y" in normalized.columns:
        input_record["years"] = _sorted_unique(normalized["y"].dropna().unique().tolist())

    return {
        "schema_version": "0.1",
        "case_name": resolved_case,
        "run_name": resolved_run,
        "inputs": [input_record],
    }


def build_coupled_run_summary(
    csv_path: str,
    run_root: str | Path,
    variable_name: str | None = None,
    case_name: str | None = None,
    run_name: str | None = None,
) -> dict:
    matrix = poc_pivot_clews_data(csv_path, variable_name)
    resolved_name = _resolve_variable_name(csv_path, variable_name)
    run_root_path = Path(run_root)
    integration_dir = run_root_path / "integration"
    resolved_case, resolved_run = _infer_case_and_run_names(
        run_root_path, case_name, run_name
    )

    return {
        "schema_version": "0.1",
        "case_name": resolved_case,
        "run_name": resolved_run,
        "workflow": "coupled",
        "status": "ready_for_ogcore_adapter",
        "source_results_dir": _display_path(Path(csv_path).parent, run_root_path),
        "integration_dir": _display_path(integration_dir, run_root_path),
        "generated_files": {
            "clews_input_manifest": _display_path(
                integration_dir / "clews_input_manifest.json", run_root_path
            ),
            "coupled_run_summary": _display_path(
                integration_dir / "coupled_run_summary.json", run_root_path
            ),
        },
        "variables": [resolved_name],
        "transforms": [
            {
                "variable_name": resolved_name,
                "output_kind": "year_by_technology_matrix",
                "years": _sorted_unique(matrix.index.tolist()),
                "technologies": _sorted_unique(matrix.columns.tolist()),
                "year_count": int(len(matrix.index)),
                "technology_count": int(len(matrix.columns)),
            }
        ],
    }


def write_coupled_integration_outputs(
    csv_path: str,
    run_root: str | Path,
    variable_name: str | None = None,
    case_name: str | None = None,
    run_name: str | None = None,
) -> dict[str, Path]:
    run_root_path = Path(run_root)
    integration_dir = run_root_path / "integration"
    integration_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_clews_input_manifest(
        csv_path,
        run_root=run_root_path,
        variable_name=variable_name,
        case_name=case_name,
        run_name=run_name,
    )
    summary = build_coupled_run_summary(
        csv_path,
        run_root=run_root_path,
        variable_name=variable_name,
        case_name=case_name,
        run_name=run_name,
    )

    manifest_path = integration_dir / "clews_input_manifest.json"
    summary_path = integration_dir / "coupled_run_summary.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )

    return {
        "manifest_path": manifest_path,
        "summary_path": summary_path,
    }

"""
test_result_adapter.py
======================
Self-contained smoke-test for :class:`ResultAdapter`.

What this proves
----------------
1. The engine handles a **4D variable** (r, y, t, m) it has never seen
   before, with zero code changes — proving true dimension-agnosticism.
2. The **SecurityError** guard fires when an out-of-root path is passed.
3. A **DUAL variable** receives the present-value discount adjustment.
4. A **TypeError** is raised when ``str`` paths are passed instead of
   ``Path`` objects.

Run
---
::

    # from the muiogo repo root
    python -m API.Integration.test_result_adapter

Exit code 0  →  all assertions passed.
Exit code 1  →  one or more assertions failed (details printed).
"""

import sys
import json
import tempfile
import textwrap
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: make sure the API directory is in sys.path so that the relative
# imports inside API.* work when this script is run directly.
# ---------------------------------------------------------------------------
API_ROOT = Path(__file__).resolve().parents[1]  # …/muiogo/API/
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

# Now patch Config.DATA_STORAGE to point at our temp directory BEFORE the
# first import of anything that references it.
import importlib
import Classes.Base.Config as _Config  # noqa: E402

# We will override DATA_STORAGE per-test using a tmp dir.

from Classes.Base.MetadataResolver import MetadataResolver  # noqa: E402
from Integration.ResultAdapter import ResultAdapter, SecurityError  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_variables_json(tmp_dir: Path, extra_group: str, entry: dict) -> Path:
    """Write a minimal Variables.json that includes *entry* under *extra_group*."""
    # Load the real Variables.json and inject our synthetic variable
    real_vars_path = _Config.DATA_STORAGE / "Variables.json"
    if real_vars_path.is_file():
        with real_vars_path.open() as fh:
            data = json.load(fh)
    else:
        data = {}

    if extra_group not in data:
        data[extra_group] = []
    data[extra_group].append(entry)

    out = tmp_dir / "Variables.json"
    out.write_text(json.dumps(data, indent=2))
    return out


def _build_results_txt(tmp_dir: Path, rows: list[str]) -> Path:
    """Write a minimal CBC-format results.txt file."""
    header = "Optimal - objective value  9999.0000"
    content = header + "\n" + "\n".join(rows)
    out = tmp_dir / "results.txt"
    out.write_text(content)
    return out


def _build_discount_rate_df():
    """Return a tiny DiscountRate DataFrame for DUAL tests."""
    import pandas as pd
    return pd.DataFrame({"r": ["RE1"], "DiscountRate": [0.05]})


# ---------------------------------------------------------------------------
# Individual test cases
# ---------------------------------------------------------------------------

PASS = "PASS"
FAIL = "FAIL"


def test_4d_variable_extraction() -> str:
    """
    Injects a synthetic 4D variable (r, y, t, m) → MockVar4D.
    Verifies output CSV has exactly those four dimension columns plus
    a fifth column named 'MockVar4D'.
    """
    import pandas as pd

    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp)
        data_storage = tmp / "DataStorage"
        data_storage.mkdir()

        # Patch Config so MetadataResolver and ResultAdapter use our tmp dir
        original_ds = _Config.DATA_STORAGE
        _Config.DATA_STORAGE = data_storage
        MetadataResolver.reset()          # force singleton re-init with new path

        # Inject our 4D variable into Variables.json
        var_entry = {
            "id": "MV4",
            "value": "Mock Variable 4D",
            "name": "MockVar4D",
            "unitRule": {"cat": [{"var": "ActUnitId"}]},
        }
        _build_variables_json(data_storage, "RYTM", var_entry)

        # Patch Config.VARIABLES_C with the new variable's dimension list
        _Config.VARIABLES_C["MockVar4D"] = ["r", "y", "t", "m"]

        try:
            # Build a fake results.txt with two rows for MockVar4D
            results_rows = [
                "    1 MockVar4D(RE1,2025,SOLAR,1)                   3.1400        0.0",
                "    2 MockVar4D(RE1,2026,WIND,2)                    1.5900        0.0",
            ]
            results_txt = _build_results_txt(data_storage, results_rows)

            output_path = data_storage / "case01" / "res" / "run01"
            output_path.mkdir(parents=True)

            adapter = ResultAdapter()
            written = adapter.extract(
                results_file=results_txt,
                data_file=results_txt,          # data_file unused in this test
                output_path=output_path,
                start_year=2025,
                discount_rate_series=pd.DataFrame(columns=["r", "DiscountRate"]),
            )

            csv_path = output_path / "csv" / "MockVar4D.csv"
            assert csv_path.is_file(), f"CSV not written: {csv_path}"

            df = pd.read_csv(csv_path)
            expected_cols = {"r", "y", "t", "m", "MockVar4D"}
            actual_cols = set(df.columns)
            assert actual_cols == expected_cols, (
                f"Column mismatch.\n  Expected: {expected_cols}\n  Got: {actual_cols}"
            )
            assert len(df) == 2, f"Expected 2 rows, got {len(df)}"

        finally:
            _Config.DATA_STORAGE = original_ds
            _Config.VARIABLES_C.pop("MockVar4D", None)
            MetadataResolver.reset()

    return PASS


def test_security_error_on_out_of_root_write() -> str:
    """
    Passes an output_path that lives outside DATA_STORAGE.
    results_file is legitimately inside DATA_STORAGE; only output_path escapes.
    Expects SecurityError to be raised.
    """
    import pandas as pd

    original_ds = _Config.DATA_STORAGE

    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp)
        data_storage = tmp / "DataStorage"
        data_storage.mkdir()

        # Copy real Variables.json so MetadataResolver can initialise
        real = original_ds / "Variables.json"
        (data_storage / "Variables.json").write_bytes(
            real.read_bytes() if real.is_file() else b"{}"
        )

        _Config.DATA_STORAGE = data_storage
        MetadataResolver.reset()

        # results_file is inside DATA_STORAGE ✓; output_path is not ✗
        results_txt = data_storage / "results.txt"
        results_txt.write_text("Optimal - objective value  0\n")

        with tempfile.TemporaryDirectory() as _escape:
            escape_path = Path(_escape) / "attacker_dir"
            escape_path.mkdir()

            try:
                adapter = ResultAdapter()
                raised = False
                try:
                    adapter.extract(
                        results_file=results_txt,
                        data_file=results_txt,
                        output_path=escape_path,   # ← outside DATA_STORAGE
                        start_year=2020,
                        discount_rate_series=pd.DataFrame(
                            columns=["r", "DiscountRate"]
                        ),
                    )
                except SecurityError:
                    raised = True

                assert raised, "SecurityError was NOT raised for an out-of-root path."

            finally:
                _Config.DATA_STORAGE = original_ds
                MetadataResolver.reset()

    return PASS


def test_dual_variable_discount_applied() -> str:
    """
    Verifies that EBb4_EnergyBalanceEachYear4_ICR (a DUAL) has its
    present-value discount formula applied: dual × (1+r)^(y−start+0.5).
    """
    import math
    import pandas as pd

    original_ds = _Config.DATA_STORAGE

    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp)
        data_storage = tmp / "DataStorage"
        data_storage.mkdir()

        # Copy real Variables.json BEFORE resetting the singleton so that
        # the next MetadataResolver() call can find it immediately.
        real = original_ds / "Variables.json"
        (data_storage / "Variables.json").write_bytes(
            real.read_bytes() if real.is_file() else b"{}"
        )

        _Config.DATA_STORAGE = data_storage
        MetadataResolver.reset()

        try:
            DUAL_VAR = "EBb4_EnergyBalanceEachYear4_ICR"
            raw_dual = 2.0
            start_year = 2020
            year = 2025
            rate = 0.10
            expected_pv = raw_dual * math.pow(1 + rate, year - start_year + 0.5)

            results_rows = [
                f"    1 {DUAL_VAR}(RE1,FUEL1,{year})        {raw_dual:.4f}  {raw_dual:.4f}",
            ]
            # results_txt must be inside data_storage (root-protection check)
            results_txt = data_storage / "results.txt"
            results_txt.write_text(
                "Optimal - objective value  9999.0000\n" + "\n".join(results_rows)
            )

            output_path = data_storage / "case01" / "res" / "run01"
            output_path.mkdir(parents=True)

            dr_df = pd.DataFrame({"r": ["RE1"], "DiscountRate": [rate]})

            adapter = ResultAdapter()
            adapter.extract(
                results_file=results_txt,
                data_file=results_txt,
                output_path=output_path,
                start_year=start_year,
                discount_rate_series=dr_df,
            )

            csv_path = output_path / "csv" / f"{DUAL_VAR}.csv"
            assert csv_path.is_file(), f"DUAL CSV not written: {csv_path}"

            df = pd.read_csv(csv_path)
            assert len(df) == 1
            actual_pv = df[DUAL_VAR].iloc[0]
            assert abs(actual_pv - expected_pv) < 1e-3, (
                f"PV mismatch: expected {expected_pv:.4f}, got {actual_pv:.4f}"
            )

        finally:
            _Config.DATA_STORAGE = original_ds
            MetadataResolver.reset()

    return PASS


def test_type_error_on_string_path() -> str:
    """Passing a raw string instead of a Path should raise TypeError."""
    import pandas as pd

    adapter = ResultAdapter()
    raised = False
    try:
        adapter.extract(
            results_file="/some/string/path",   # ← not a Path
            data_file=Path("/placeholder"),
            output_path=_Config.DATA_STORAGE,
            start_year=2020,
            discount_rate_series=pd.DataFrame(columns=["r", "DiscountRate"]),
        )
    except TypeError:
        raised = True

    assert raised, "TypeError was NOT raised when a str path was passed."
    return PASS


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

TESTS = [
    ("4D variable extraction",          test_4d_variable_extraction),
    ("SecurityError on out-of-root",    test_security_error_on_out_of_root_write),
    ("DUAL discount applied",           test_dual_variable_discount_applied),
    ("TypeError on str path",           test_type_error_on_string_path),
]


def main() -> int:
    print("\n" + "═" * 60)
    print("  MUIOGO ResultAdapter — Mock Test Suite")
    print("═" * 60)

    failures = 0
    for name, fn in TESTS:
        try:
            result = fn()
            status = result
        except AssertionError as exc:
            status = FAIL
            failures += 1
            print(f"  [ FAIL ]  {name}")
            print(f"            AssertionError: {exc}")
            continue
        except Exception:  # noqa: BLE001
            status = FAIL
            failures += 1
            print(f"  [ FAIL ]  {name}")
            traceback.print_exc()
            continue
        mark = "✓" if status == PASS else "✗"
        print(f"  [ {mark}    ]  {name}")

    print("─" * 60)
    if failures == 0:
        print(f"  All {len(TESTS)} tests passed.\n")
        return 0
    else:
        print(f"  {failures}/{len(TESTS)} test(s) FAILED.\n")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())

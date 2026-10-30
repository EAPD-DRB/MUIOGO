#!/usr/bin/env python3
"""Verify and document Philippines v22 EV/truck live promotion identity."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP/DataStorage"
CANDIDATE = STORAGE / ".Philippines_v22-ev-truck-turnover-candidate-20260824"
LIVE = STORAGE / "Philippines_v22"
CANDIDATE_RUN = CANDIDATE / "res/EV_TRUCK_TURNOVER_V22_BASE"
LIVE_RUN = LIVE / "res/EV_TRUCK_TURNOVER_V22_PROMOTION_CHECK"
LEDGERS = ("SOURCES.csv", "ASSUMPTIONS.csv", "CALCULATIONS.csv", "MODEL_MAP.csv", "GAPS.csv", "CHANGES.csv")
EXPECTED_MATRIX = {"rows": 553001, "columns": 584981, "matrix_nonzeros": 8108315}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def normalized_processed(path: Path) -> bytes:
    output = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(set\s+[^:]+:=)\s*(.*);$", line)
        if match:
            tokens = re.findall(r"\([^)]*\)|\S+", match.group(2))
            line = f"{match.group(1)} {' '.join(sorted(tokens))};"
        output.append(line)
    return ("\n".join(output) + "\n").encode("utf-8")


def update_csv(path: Path, key: str, identifier: str, values: dict[str, str]) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    selected = [row for row in rows if row[key] == identifier]
    if selected:
        selected[0].update(values)
    else:
        rows.append({name: values.get(name, "") for name in fieldnames})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def document(case: Path, report: dict) -> None:
    report_path = case / "data_sources/snapshots/ev_truck_turnover_promotion_identity.json"
    write(report_path, report)
    write(case / "documentation/EV_TRUCK_TURNOVER_PROMOTION_IDENTITY.json", report)
    report_hash = sha(report_path)

    fix_path = case / "documentation/MODEL_FIXES_EV_TRUCK_TURNOVER_2026-08-24.md"
    text = fix_path.read_text(encoding="utf-8")
    marker = "## Promotion identity (2026-08-24)"
    if marker not in text:
        text = text.rstrip() + f"""

{marker}

The validated source was promoted to `Philippines_v22`. All root source JSON
files and all six schema-ledger CSVs were byte-identical to the disposable
candidate before adding this promotion record. The live application-generated
`data.txt` is byte-identical to the solved BASE candidate. Preprocessed data
are equivalent after canonicalizing unordered derived-set declarations, and
GLPK reproduced the 553,001-row, 584,981-column, 8,108,315-nonzero matrix.
No post-promotion CBC optimization was run; the four validated disposable
scenario results remain the authoritative simulation record.
"""
        fix_path.write_text(text, encoding="utf-8")

    ledger = case / "data_sources"
    update_csv(ledger / "SOURCES.csv", "source_id", "SRC_PHL_V22_EV_TRUCK_PROMOTION_IDENTITY", {
        "source_id": "SRC_PHL_V22_EV_TRUCK_PROMOTION_IDENTITY",
        "provider": "MUIOGO",
        "product": "Philippines v22 EV/truck promotion identity report",
        "edition": "2026-08-24", "reference_period": "promotion", "geography": "Philippines",
        "variable": "source, ledger and generated-input identity", "source_unit": "hashes and status",
        "exact_locator": "data_sources/snapshots/ev_truck_turnover_promotion_identity.json",
        "access_date": "2026-08-24", "license": "Repository license", "sha256": report_hash,
        "local_file": "snapshots/ev_truck_turnover_promotion_identity.json",
        "notes": "No post-promotion CBC; live data.txt is byte-identical and processed differences are unordered set declarations only.",
    })
    update_csv(ledger / "CALCULATIONS.csv", "calculation_id", "CALC_PHL_V22_EV_TRUCK_PROMOTION_IDENTITY", {
        "calculation_id": "CALC_PHL_V22_EV_TRUCK_PROMOTION_IDENTITY",
        "formula": "compare root source JSON and six ledgers; compare data.txt; canonicalize unordered processed sets; compare GLPK dimensions",
        "source_ids": "SRC_PHL_V22_EV_TRUCK_VALIDATION;SRC_PHL_V22_EV_TRUCK_PROMOTION_IDENTITY",
        "input_values": f"data={report['hashes']['data_txt']};matrix={EXPECTED_MATRIX}",
        "input_units": "SHA-256;rows/columns/nonzeros",
        "output_value": "pass; zero post-promotion optimizer runs", "output_unit": "status",
        "script_path": "scripts/verify_philippines_v22_ev_truck_turnover_promotion.py", "script_version": "v1",
        "notes": "The solved disposable BASE result is accepted as the validated live result by exact generated-input identity.",
    })
    update_csv(ledger / "MODEL_MAP.csv", "map_id", "MAP_PHL_V22_EV_TRUCK_PROMOTION_IDENTITY", {
        "map_id": "MAP_PHL_V22_EV_TRUCK_PROMOTION_IDENTITY",
        "model_file": "Philippines_v22 root JSON;res/EV_TRUCK_TURNOVER_V22_PROMOTION_CHECK/data.txt",
        "parameter": "promotion identity", "entity": "Philippines_v22", "scenario": "BASE", "years": "2020-2053",
        "value_or_expression": "byte-identical source, ledgers and data.txt; canonical processed-set equivalence; matching matrix",
        "model_unit": "status", "evidence_ids": "SRC_PHL_V22_EV_TRUCK_PROMOTION_IDENTITY",
        "evidence_type": "promotion validation", "notes": "No live CBC rerun.",
    })
    update_csv(ledger / "CHANGES.csv", "change_id", "CHG_PHL_V22_EV_TRUCK_TURNOVER_20260824", {
        "resolve_status": "promoted_live_identity_pass",
        "notes": "Generic gate and four candidate matrices passed. BASE solved first; COAL_PHASEOUT, RE and EV then solved concurrently and all four were optimal. Live source, six ledgers and data.txt identity passed; processed sets are canonically equivalent and matrix dimensions match. No post-promotion CBC run.",
    })


def main() -> None:
    candidate_json = sorted(path.name for path in CANDIDATE.glob("*.json"))
    source_failures = [name for name in candidate_json if sha(CANDIDATE / name) != sha(LIVE / name)]
    if source_failures:
        raise AssertionError({"source_failures": source_failures})
    ledger_failures = [name for name in LEDGERS if sha(CANDIDATE / "data_sources" / name) != sha(LIVE / "data_sources" / name)]
    if ledger_failures:
        raise AssertionError({"ledger_failures": ledger_failures})
    if sha(CANDIDATE_RUN / "data.txt") != sha(LIVE_RUN / "data.txt"):
        raise AssertionError("live data.txt differs from solved candidate")
    candidate_processed = normalized_processed(CANDIDATE_RUN / "data_processed.txt")
    live_processed = normalized_processed(LIVE_RUN / "data_processed.txt")
    if candidate_processed != live_processed:
        raise AssertionError("processed data differ beyond unordered set declarations")
    matrix = read(LIVE_RUN / "generation_matrix_report.json")["matrix_dimensions"]
    if matrix != EXPECTED_MATRIX:
        raise AssertionError((matrix, EXPECTED_MATRIX))
    validation = read(CANDIDATE / "data_sources/snapshots/ev_truck_turnover_validation_manifest.json")
    if validation["optimizer_run_count"] != 4:
        raise AssertionError("candidate validation did not retain exactly four optimizer runs")
    if not all(record["solver_status"].startswith("Optimal") for record in validation["scenario_records"].values()):
        raise AssertionError("not every candidate scenario is optimal")

    report = {
        "schema": "philippines-v22-ev-truck-turnover-promotion-identity-v1",
        "date": "2026-08-24", "status": "pass",
        "candidate_case": str(CANDIDATE), "live_case": str(LIVE),
        "four_scenario_candidate_gate": "pass", "candidate_optimizer_runs": 4,
        "source_json_count": len(candidate_json), "source_json_byte_identical": True,
        "schema_ledger_csv_count": len(LEDGERS), "schema_ledger_csv_byte_identical_before_promotion_record": True,
        "data_txt_byte_identical": True,
        "data_processed_txt_byte_identical": sha(CANDIDATE_RUN / "data_processed.txt") == sha(LIVE_RUN / "data_processed.txt"),
        "data_processed_set_order_equivalent": True,
        "data_processed_normalized_sha256": hashlib.sha256(live_processed).hexdigest(),
        "matrix": matrix, "glpsol_check": "pass", "post_promotion_optimizer_runs": 0,
        "post_promotion_cbc": "not run because source JSON and generated data.txt are byte-identical; processed data differ only in unordered set declaration order and matrix dimensions match",
        "hashes": {
            "data_txt": sha(LIVE_RUN / "data.txt"),
            "data_processed_txt": sha(LIVE_RUN / "data_processed.txt"),
            "lp": sha(LIVE_RUN / "lp.lp"),
        },
    }
    document(CANDIDATE, report)
    document(LIVE, report)
    for name in LEDGERS:
        if sha(CANDIDATE / "data_sources" / name) != sha(LIVE / "data_sources" / name):
            raise AssertionError(f"post-documentation ledger mismatch: {name}")
    if sha(CANDIDATE / "documentation/MODEL_FIXES_EV_TRUCK_TURNOVER_2026-08-24.md") != sha(LIVE / "documentation/MODEL_FIXES_EV_TRUCK_TURNOVER_2026-08-24.md"):
        raise AssertionError("post-documentation model-fixes mismatch")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

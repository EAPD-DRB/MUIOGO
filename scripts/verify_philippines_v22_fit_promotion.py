#!/usr/bin/env python3
"""Verify and document the result-free Philippines v22 live promotion."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
CANDIDATE = STORAGE / ".Philippines_v22-transition-scope-fit-repair-candidate-r9"
LIVE = STORAGE / "Philippines_v22"
CANDIDATE_RUN = CANDIDATE / "res" / "FIT_ACCOUNTING_V22_BASE"
LIVE_RUN = LIVE / "res" / "FIT_ACCOUNTING_V22_PROMOTION_CHECK"
EXPECTED_MATRIX = {"rows": 553001, "columns": 584981, "matrix_nonzeros": 8108623}


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
        if not match:
            output.append(line)
            continue
        tokens = re.findall(r"\([^)]*\)|\S+", match.group(2))
        output.append(f"{match.group(1)} {' '.join(sorted(tokens))};")
    return ("\n".join(output) + "\n").encode("utf-8")


def parse_matrix() -> dict[str, int]:
    report = read(LIVE_RUN / "generation_matrix_report.json")
    return report["matrix_dimensions"]


def update_csv(path: Path, key: str, identifier: str, values: dict[str, str]) -> None:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    selected = [row for row in rows if row[key] == identifier]
    if selected:
        selected[0].update(values)
    else:
        rows.append({name: values.get(name, "") for name in fieldnames})
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def document(case: Path, report: dict) -> None:
    documentation = case / "documentation"
    snapshot = case / "data_sources" / "snapshots" / "fit_accounting_r9_promotion_identity.json"
    write(documentation / "FIT_ACCOUNTING_R9_PROMOTION_IDENTITY.json", report)
    write(snapshot, report)
    report_hash = sha(snapshot)

    validation_path = documentation / "FIT_ACCOUNTING_R9_VALIDATION_SUMMARY.json"
    validation = read(validation_path)
    validation.update({
        "status": "promoted_live_identity_pass",
        "promoted": True,
        "live_case": "Philippines_v22",
        "promotion_identity": "documentation/FIT_ACCOUNTING_R9_PROMOTION_IDENTITY.json",
        "promotion_identity_sha256": report_hash,
        "post_promotion_optimizer_runs": 0,
    })
    validation.pop("pause_point", None)
    write(validation_path, validation)

    fix_path = documentation / "MODEL_FIXES_FIT_ACCOUNTING_V22_2026-08-20.md"
    text = fix_path.read_text(encoding="utf-8")
    marker = "## Promotion (2026-08-21)"
    if marker not in text:
        text = text.rstrip() + f"""

{marker}

The validated r9 source was promoted to `Philippines_v22`. All 22 root source
JSON files and all six schema-ledger CSVs were byte-identical before final
promotion documentation. The live application-generated `data.txt` is
byte-identical to the solved BASE candidate. Preprocessed data are equivalent
after canonicalizing unordered derived-set declarations, and GLPK reproduced
the exact 553001-row, 584981-column, 8108623-nonzero matrix. No post-promotion
CBC optimization was run.
"""
        fix_path.write_text(text, encoding="utf-8")

    ledger = case / "data_sources"
    update_csv(ledger / "SOURCES.csv", "source_id", "SRC_PHL_V22_FIT_PROMOTION_IDENTITY", {
        "source_id": "SRC_PHL_V22_FIT_PROMOTION_IDENTITY", "provider": "MUIOGO",
        "product": "Philippines v22 FIT promotion identity report", "edition": "2026-08-21",
        "reference_period": "promotion", "geography": "Philippines",
        "variable": "source and generated-input identity", "source_unit": "hashes and status",
        "exact_locator": "data_sources/snapshots/fit_accounting_r9_promotion_identity.json",
        "access_date": "2026-08-21", "license": "Repository license", "sha256": report_hash,
        "local_file": "snapshots/fit_accounting_r9_promotion_identity.json",
        "notes": "No post-promotion CBC; live data.txt is byte-identical and processed differences are unordered set declarations only.",
    })
    update_csv(ledger / "CALCULATIONS.csv", "calculation_id", "CALC_PHL_V22_FIT_PROMOTION_IDENTITY", {
        "calculation_id": "CALC_PHL_V22_FIT_PROMOTION_IDENTITY",
        "formula": "compare 22 root source JSON hashes; compare data.txt hash; canonicalize unordered processed sets; compare GLPK dimensions",
        "source_ids": "SRC_PHL_V22_FIT_PROMOTION_IDENTITY",
        "input_values": f"data={report['hashes']['data_txt']};matrix={EXPECTED_MATRIX}",
        "input_units": "SHA-256;rows/columns/nonzeros", "output_value": "pass; zero post-promotion optimizer runs",
        "output_unit": "status", "script_path": "scripts/verify_philippines_v22_fit_promotion.py",
        "script_version": "v1",
    })
    update_csv(ledger / "MODEL_MAP.csv", "map_id", "MAP_PHL_V22_FIT_PROMOTION_IDENTITY", {
        "map_id": "MAP_PHL_V22_FIT_PROMOTION_IDENTITY",
        "model_file": "Philippines_v22 root JSON;res/FIT_ACCOUNTING_V22_PROMOTION_CHECK/data.txt",
        "parameter": "promotion identity", "entity": "Philippines_v22", "scenario": "BASE",
        "years": "2020-2053", "value_or_expression": "byte-identical source and data.txt; canonical processed-set equivalence; matching matrix",
        "model_unit": "status", "evidence_ids": "SRC_PHL_V22_FIT_PROMOTION_IDENTITY",
        "evidence_type": "promotion validation", "notes": "No live CBC rerun.",
    })
    update_csv(ledger / "CHANGES.csv", "change_id", "CHG_PHL_V22_FIT_ACCOUNTING_R9_20260820", {
        "resolve_status": "promoted_live_identity_pass",
        "notes": "BASE solved first and all three policies solved concurrently. Live source and data.txt identity passed; processed sets are canonically equivalent and matrix dimensions match. No post-promotion CBC run.",
    })


def main() -> None:
    candidate_json = sorted(path.name for path in CANDIDATE.glob("*.json"))
    source_failures = [name for name in candidate_json if sha(CANDIDATE / name) != sha(LIVE / name)]
    if source_failures:
        raise AssertionError({"source_failures": source_failures})
    ledger_names = ["SOURCES.csv", "ASSUMPTIONS.csv", "CALCULATIONS.csv", "MODEL_MAP.csv", "GAPS.csv", "CHANGES.csv"]
    ledger_failures = [name for name in ledger_names
                       if sha(CANDIDATE / "data_sources" / name) != sha(LIVE / "data_sources" / name)]
    if ledger_failures:
        raise AssertionError({"ledger_failures": ledger_failures})
    if sha(CANDIDATE_RUN / "data.txt") != sha(LIVE_RUN / "data.txt"):
        raise AssertionError("live data.txt differs from solved candidate")
    normalized_candidate = normalized_processed(CANDIDATE_RUN / "data_processed.txt")
    normalized_live = normalized_processed(LIVE_RUN / "data_processed.txt")
    if normalized_candidate != normalized_live:
        raise AssertionError("processed data differ beyond unordered set declarations")
    matrix = parse_matrix()
    if matrix != EXPECTED_MATRIX:
        raise AssertionError((matrix, EXPECTED_MATRIX))
    validation = read(CANDIDATE / "documentation" / "FIT_ACCOUNTING_R9_VALIDATION_SUMMARY.json")
    if not validation["promotion_allowed_by_solve_gate"] or len(validation["optimizer_executions"]) != 4:
        raise AssertionError("four-scenario solve gate is not passed")
    if not all(str(item["status"]).startswith("Optimal") for item in validation["optimizer_executions"]):
        raise AssertionError("not every candidate scenario is optimal")

    report = {
        "schema": "philippines-v22-fit-accounting-r9-promotion-identity-v1",
        "date": str(date.today()), "status": "pass",
        "candidate_case": str(CANDIDATE), "live_case": str(LIVE),
        "four_scenario_candidate_gate": "pass",
        "source_json_count": len(candidate_json), "source_json_byte_identical": True,
        "schema_ledger_csv_count": len(ledger_names), "schema_ledger_csv_byte_identical_before_promotion_record": True,
        "data_txt_byte_identical": True,
        "data_processed_txt_byte_identical": sha(CANDIDATE_RUN / "data_processed.txt") == sha(LIVE_RUN / "data_processed.txt"),
        "data_processed_set_order_equivalent": True,
        "data_processed_normalized_sha256": hashlib.sha256(normalized_live).hexdigest(),
        "matrix": matrix, "glpsol_check": "pass",
        "post_promotion_optimizer_runs": 0,
        "post_promotion_cbc": "not run because source JSON and generated data.txt are byte-identical; processed data differ only in unordered set declaration order and matrix dimensions match",
        "hashes": {
            "data_txt": sha(LIVE_RUN / "data.txt"),
            "data_processed_txt": sha(LIVE_RUN / "data_processed.txt"),
            "lp": sha(LIVE_RUN / "lp.lp"),
        },
    }
    document(CANDIDATE, report)
    document(LIVE, report)
    # Documentation/ledger mutations above must remain identical in both cases.
    for name in ledger_names:
        if sha(CANDIDATE / "data_sources" / name) != sha(LIVE / "data_sources" / name):
            raise AssertionError(f"post-documentation ledger mismatch: {name}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

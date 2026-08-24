#!/usr/bin/env python3
"""Verify and document result-free Philippines v23 Package 1 promotion."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
CANDIDATE = STORAGE / ".Philippines_v23-package1-candidate-20260824"
LIVE = STORAGE / "Philippines_v23"
CANDIDATE_RUN = CANDIDATE / "res" / "PACKAGE1_V23_BASE"
LIVE_RUN = LIVE / "res" / "PACKAGE1_V23_PROMOTION_CHECK"
LEDGERS = ("SOURCES.csv", "ASSUMPTIONS.csv", "CALCULATIONS.csv", "MODEL_MAP.csv", "GAPS.csv", "CHANGES.csv")
EXPECTED_MATRIX = {"rows": 554873, "columns": 586648, "matrix_nonzeros": 8118754}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
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


def update_csv(path: Path, key: str, identifier: str, values: dict[str, str]) -> None:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    selected = [row for row in rows if row[key] == identifier]
    if selected:
        selected[0].update(values)
    else:
        rows.append({field: values.get(field, "") for field in fields})
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def document(case: Path, report: dict) -> None:
    documentation = case / "documentation"
    snapshot = case / "data_sources" / "snapshots" / "package1_v23_promotion_identity.json"
    write_json(documentation / "PACKAGE1_V23_PROMOTION_IDENTITY.json", report)
    write_json(snapshot, report)
    report_hash = sha256(snapshot)
    ledger = case / "data_sources"
    update_csv(ledger / "SOURCES.csv", "source_id", "SRC_PHL_V23_PROMOTION_IDENTITY", {
        "source_id": "SRC_PHL_V23_PROMOTION_IDENTITY", "provider": "MUIOGO",
        "product": "Philippines v23 Package 1 promotion identity", "edition": "2026-08-24",
        "reference_period": "promotion", "geography": "Philippines",
        "variable": "source, generated-input and matrix identity", "source_unit": "hashes and status",
        "exact_locator": "data_sources/snapshots/package1_v23_promotion_identity.json",
        "url": "", "access_date": "2026-08-24", "license": "Repository license",
        "sha256": report_hash, "local_file": "snapshots/package1_v23_promotion_identity.json",
        "notes": "No post-promotion CBC; live data.txt is byte-identical and processed differences are unordered derived-set declarations only.",
    })
    update_csv(ledger / "CALCULATIONS.csv", "calculation_id", "CALC_PHL_V23_PROMOTION_IDENTITY", {
        "calculation_id": "CALC_PHL_V23_PROMOTION_IDENTITY",
        "formula": "compare root source JSON and six ledger CSV hashes; compare data.txt; canonicalize unordered processed sets; compare GLPK matrix",
        "source_ids": "SRC_PHL_V23_PROMOTION_IDENTITY",
        "input_values": f"data={report['hashes']['data_txt']};matrix={EXPECTED_MATRIX}",
        "input_units": "SHA-256;rows/columns/nonzeros", "output_value": "pass; zero post-promotion optimizer runs",
        "output_unit": "status", "script_path": "scripts/verify_philippines_v23_package1_promotion.py",
        "script_version": "v1",
    })
    update_csv(ledger / "MODEL_MAP.csv", "map_id", "MAP_PHL_V23_PROMOTION_IDENTITY", {
        "map_id": "MAP_PHL_V23_PROMOTION_IDENTITY",
        "model_file": "Philippines_v23 root JSON;res/PACKAGE1_V23_PROMOTION_CHECK/data.txt",
        "parameter": "promotion identity", "entity": "Philippines_v23", "scenario": "BASE",
        "years": "2020-2053",
        "value_or_expression": "byte-identical source/data.txt; canonical processed-set equivalence; matching matrix",
        "model_unit": "status", "evidence_ids": "SRC_PHL_V23_PROMOTION_IDENTITY",
        "evidence_type": "promotion validation", "notes": "No live CBC rerun.",
    })
    update_csv(ledger / "CHANGES.csv", "change_id", "CHG_PHL_V23_PACKAGE1_20260824", {
        "resolve_status": "promoted_live_identity_pass",
        "notes": "All four scenarios are optimal. Live root source and data.txt are byte-identical; processed sets are canonically equivalent and GLPK matrix dimensions match. No post-promotion CBC run.",
    })

    fixes = documentation / "MODEL_FIXES_PACKAGE_1_V23_2026-08-24.md"
    text = fixes.read_text(encoding="utf-8")
    marker = "## Completed promotion identity (2026-08-24)"
    if marker not in text:
        text = text.rstrip() + f"""

{marker}

The validated source was promoted to `Philippines_v23`. All root source JSON
files and all six schema-ledger CSVs were byte-identical before adding this
promotion record. Live application-generated `data.txt` is byte-identical to
the solved BASE candidate. Preprocessed data are equivalent after
canonicalizing unordered derived-set declarations, and GLPK reproduced the
554873-row, 586648-column, 8118754-nonzero matrix. No post-promotion CBC
optimization was run; the four disposable candidate results remain the
authoritative simulation record.
"""
        fixes.write_text(text, encoding="utf-8")

    note = ledger / "calculation_notes" / "MODEL_FIXES_PACKAGE_1_V23_2026-08-24.md"
    text = note.read_text(encoding="utf-8")
    if marker not in text:
        note.write_text(text.rstrip() + f"""

{marker}

Live root source JSON and generated `data.txt` are byte-identical to the solved
candidate. Canonicalized processed sets and GLPK dimensions match. No live CBC
rerun was performed.
""", encoding="utf-8")

    build_path = documentation / "package1_v23_build_manifest.json"
    build = json.loads(build_path.read_text(encoding="utf-8"))
    build.update({
        "candidate_hashes": {path.name: sha256(path) for path in sorted(CANDIDATE.glob("*.json"))},
        "policy_inheritance_repair": "documentation/package1_v23_policy_inheritance_repair.json",
        "validation_status": "promoted_live_identity_pass",
        "four_scenario_validation": "documentation/package1_v23_four_scenario_validation.json",
        "optimizer_runs": 4,
        "model_generation_runs": 5,
        "promotion_identity": "documentation/PACKAGE1_V23_PROMOTION_IDENTITY.json",
    })
    build.pop("required_next_step", None)
    write_json(build_path, build)


def main() -> None:
    candidate_json = sorted(path.name for path in CANDIDATE.glob("*.json"))
    source_failures = [name for name in candidate_json if sha256(CANDIDATE / name) != sha256(LIVE / name)]
    if source_failures:
        raise AssertionError({"source_failures": source_failures})
    ledger_failures = [name for name in LEDGERS if sha256(CANDIDATE / "data_sources" / name) != sha256(LIVE / "data_sources" / name)]
    if ledger_failures:
        raise AssertionError({"ledger_failures": ledger_failures})
    if sha256(CANDIDATE_RUN / "data.txt") != sha256(LIVE_RUN / "data.txt"):
        raise AssertionError("live data.txt differs from solved candidate")
    candidate_normalized = normalized_processed(CANDIDATE_RUN / "data_processed.txt")
    live_normalized = normalized_processed(LIVE_RUN / "data_processed.txt")
    if candidate_normalized != live_normalized:
        raise AssertionError("processed data differ beyond unordered set declarations")
    matrix = json.loads((LIVE_RUN / "generation_matrix_report.json").read_text(encoding="utf-8"))["matrix_dimensions"]
    if matrix != EXPECTED_MATRIX:
        raise AssertionError((matrix, EXPECTED_MATRIX))
    qualification = json.loads((CANDIDATE / "documentation" / "package1_v23_four_scenario_validation.json").read_text(encoding="utf-8"))
    if qualification.get("status") != "passed" or qualification.get("optimizer_runs") != 4:
        raise AssertionError("four-scenario qualification is not complete")

    report = {
        "schema": "philippines-v23-package1-promotion-identity-v1",
        "date": str(date.today()), "status": "pass",
        "candidate_case": str(CANDIDATE), "live_case": str(LIVE),
        "four_scenario_candidate_gate": "pass",
        "source_json_count": len(candidate_json), "source_json_byte_identical": True,
        "schema_ledger_csv_count": len(LEDGERS), "schema_ledger_csv_byte_identical_before_promotion_record": True,
        "data_txt_byte_identical": True,
        "data_processed_txt_byte_identical": sha256(CANDIDATE_RUN / "data_processed.txt") == sha256(LIVE_RUN / "data_processed.txt"),
        "data_processed_set_order_equivalent": True,
        "data_processed_normalized_sha256": hashlib.sha256(live_normalized).hexdigest(),
        "matrix": matrix, "glpsol_check": "pass",
        "candidate_optimizer_runs": 4, "post_promotion_optimizer_runs": 0,
        "post_promotion_cbc": "not run because source JSON and generated data.txt are byte-identical; processed data differ only in unordered derived-set order and matrix dimensions match",
        "hashes": {
            "data_txt": sha256(LIVE_RUN / "data.txt"),
            "data_processed_txt": sha256(LIVE_RUN / "data_processed.txt"),
            "lp": sha256(LIVE_RUN / "lp.lp"),
        },
    }
    document(CANDIDATE, report)
    document(LIVE, report)
    for name in LEDGERS:
        if sha256(CANDIDATE / "data_sources" / name) != sha256(LIVE / "data_sources" / name):
            raise AssertionError(f"post-documentation ledger mismatch: {name}")
    if sha256(CANDIDATE / "documentation" / "MODEL_FIXES_PACKAGE_1_V23_2026-08-24.md") != sha256(LIVE / "documentation" / "MODEL_FIXES_PACKAGE_1_V23_2026-08-24.md"):
        raise AssertionError("post-documentation MODEL_FIXES mismatch")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

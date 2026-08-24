#!/usr/bin/env python3
"""Stage the validated Package 1 candidate as source-only Philippines_v23."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "WebAPP" / "DataStorage"
CANDIDATE = STORAGE / ".Philippines_v23-package1-candidate-20260824"
LIVE = STORAGE / "Philippines_v23"
LEDGERS = ("SOURCES.csv", "ASSUMPTIONS.csv", "CALCULATIONS.csv", "MODEL_MAP.csv", "GAPS.csv", "CHANGES.csv")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    qualification = json.loads(
        (CANDIDATE / "documentation" / "package1_v23_four_scenario_validation.json").read_text(encoding="utf-8")
    )
    semantic = json.loads(
        (CANDIDATE / "documentation" / "package1_v23_deterministic_gate.json").read_text(encoding="utf-8")
    )
    if qualification.get("status") != "passed" or not qualification.get("promotion_allowed"):
        raise RuntimeError("four-scenario qualification is not a clean pass")
    if semantic.get("status") != "passed" or semantic.get("failure_count") != 0:
        raise RuntimeError("Package 1 semantic gate is not a clean pass")
    if LIVE.exists():
        raise FileExistsError(f"refusing to replace existing live case: {LIVE}")
    shutil.copytree(CANDIDATE, LIVE, ignore=shutil.ignore_patterns("res", ".DS_Store"))

    # The source-only live case must not advertise disposable candidate runs.
    registry = LIVE / "view" / "resData.json"
    if registry.is_file():
        data = json.loads(registry.read_text(encoding="utf-8"))
        data["osy-cases"] = [
            row for row in data.get("osy-cases", [])
            if not str(row.get("Case", "")).startswith("PACKAGE1_V23_")
        ]
        registry.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")

    source_hashes = {path.name: sha256(path) for path in sorted(CANDIDATE.glob("*.json"))}
    live_source_hashes = {path.name: sha256(path) for path in sorted(LIVE.glob("*.json"))}
    ledger_hashes = {name: sha256(CANDIDATE / "data_sources" / name) for name in LEDGERS}
    live_ledger_hashes = {name: sha256(LIVE / "data_sources" / name) for name in LEDGERS}
    if source_hashes != live_source_hashes or ledger_hashes != live_ledger_hashes:
        raise RuntimeError("staged source or six-table ledger is not byte-identical")
    report = {
        "schema": "philippines-v23-package1-promotion-staging-v1",
        "candidate": str(CANDIDATE), "live": str(LIVE),
        "status": "source_staged_pending_live_generation_identity",
        "candidate_source_hashes": source_hashes,
        "live_source_hashes": live_source_hashes,
        "candidate_ledger_hashes": ledger_hashes,
        "live_ledger_hashes": live_ledger_hashes,
        "root_source_byte_identical": True, "six_table_ledger_byte_identical": True,
        "disposable_results_copied": False,
        "optimizer_runs_during_promotion": 0,
        "required_next_step": "Generate/preprocess live BASE, GLPK-check, and compare data.txt with the solved candidate.",
    }
    for case in (CANDIDATE, LIVE):
        (case / "documentation" / "package1_v23_promotion_staging.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps({key: report[key] for key in (
        "status", "root_source_byte_identical", "six_table_ledger_byte_identical",
        "disposable_results_copied", "optimizer_runs_during_promotion", "required_next_step"
    )}, indent=2))


if __name__ == "__main__":
    main()

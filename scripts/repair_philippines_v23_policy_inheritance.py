#!/usr/bin/env python3
"""Restore untouched v22 policy TAMaxCI cells cleared by the first v23 builder."""

from __future__ import annotations

import json
from pathlib import Path

from build_philippines_v23_package1 import PRE2026_BUILD_GW, SOURCE, DEFAULT_TARGET, write_json


def main() -> None:
    parent_gen = json.loads((SOURCE / "genData.json").read_text(encoding="utf-8"))
    target_gen = json.loads((DEFAULT_TARGET / "genData.json").read_text(encoding="utf-8"))
    parent_ids = {row["Tech"]: row["TechId"] for row in parent_gen["osy-tech"]}
    target_ids = {row["Tech"]: row["TechId"] for row in target_gen["osy-tech"]}
    parent = json.loads((SOURCE / "RYT.json").read_text(encoding="utf-8"))
    target = json.loads((DEFAULT_TARGET / "RYT.json").read_text(encoding="utf-8"))
    restored = []
    for scenario in target["TAMaxCI"]:
        if scenario == "SC_0":
            continue
        parent_rows = {row["TechId"]: row for row in parent["TAMaxCI"][scenario]}
        target_rows = {row["TechId"]: row for row in target["TAMaxCI"][scenario]}
        for name in PRE2026_BUILD_GW:
            source = parent_rows[parent_ids[name]]
            destination = target_rows[target_ids[name]]
            for year in map(str, range(2026, 2054)):
                if destination[year] != source[year]:
                    restored.append({"scenario": scenario, "technology": name, "year": year,
                                     "before": destination[year], "after": source[year]})
                    destination[year] = source[year]
    write_json(DEFAULT_TARGET / "RYT.json", target)
    report = {
        "schema": "philippines-v23-policy-inheritance-repair-v1",
        "candidate": str(DEFAULT_TARGET),
        "reason": "The initial builder cleared policy overrides outside the edited 2020-2025 BASE envelope.",
        "scope": "TAMaxCI policy cells for Package 1 pre-2026 envelope technologies, years 2026-2053",
        "restored_cell_count": len(restored),
        "restored_cells": restored,
        "policy_optimizer_runs_before_detection": 0,
        "total_optimizer_runs_before_detection": 1,
        "model_generation_runs_before_detection": 0,
    }
    output = DEFAULT_TARGET / "documentation" / "package1_v23_policy_inheritance_repair.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in report if key != "restored_cells"}, indent=2))


if __name__ == "__main__":
    main()

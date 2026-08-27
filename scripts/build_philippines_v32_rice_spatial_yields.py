#!/usr/bin/env python3
"""Apply the sourced Philippines v32 spatial rice-yield candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


TECHNOLOGIES = [f"LNDAGRPHLC{i:02d}" for i in range(1, 9)]
MODE_BY_REGIME = {"rainfed": 11, "irrigated": 19}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    case = args.case.resolve()
    gen_path = case / "genData.json"
    oar_path = case / "RYTCM.json"
    source_path = (
        case
        / "data_sources/evidence/v32_rice_spatial_yield/derived/phl_rice_cluster_yields_2020.csv"
    )

    gen = json.loads(gen_path.read_text())
    old_case = gen["osy-casename"]
    if old_case not in {"Philippines_v31", "Philippines_v32"}:
        raise SystemExit(f"Unexpected source case identity: {old_case}")
    tech_ids = {
        row["Tech"]: row["TechId"]
        for row in gen["osy-tech"]
        if row["Tech"] in TECHNOLOGIES
    }
    if set(tech_ids) != set(TECHNOLOGIES):
        raise SystemExit("Could not resolve all eight rice land technologies")
    rice_id = next(row["CommId"] for row in gen["osy-comm"] if row["Comm"] == "CRPRCP")

    anchors = pd.read_csv(source_path)
    expected = {(regime, cluster) for regime in MODE_BY_REGIME for cluster in range(1, 9)}
    found = set(zip(anchors.regime, anchors.clusters_yield))
    if found != expected:
        raise SystemExit(f"Unexpected anchor keys: {sorted(found ^ expected)}")
    anchor_map = {
        (row.regime, int(row.clusters_yield)): float(row.model_oar_mt_per_1000km2)
        for row in anchors.itertuples()
    }

    oar = json.loads(oar_path.read_text())
    rows = oar["OAR"]["SC_0"]
    id_to_cluster = {value: index + 1 for index, value in enumerate(tech_ids.values())}
    changed = []
    for row in rows:
        cluster = id_to_cluster.get(row.get("TechId"))
        if cluster is None or row.get("CommId") != rice_id:
            continue
        regime = next(
            (name for name, mode in MODE_BY_REGIME.items() if row.get("MoId") == mode),
            None,
        )
        if regime is None:
            continue
        old_2020 = float(row["2020"])
        new_2020 = anchor_map[(regime, cluster)]
        for year in range(2020, 2054):
            key = str(year)
            old_value = float(row[key])
            new_value = new_2020 * old_value / old_2020
            row[key] = new_value
            changed.append(
                {
                    "technology": TECHNOLOGIES[cluster - 1],
                    "mode": row["MoId"],
                    "year": year,
                    "before": old_value,
                    "after": new_value,
                }
            )

    if len(changed) != 8 * 2 * 34:
        raise SystemExit(f"Expected 544 OAR cells, changed {len(changed)}")

    gen["osy-casename"] = "Philippines_v32"
    gen["osy-desc"] = (
        "Philippines v32 candidate: v31 plus achieved province-to-GAEZ-cluster "
        "rice yields; observed regime outcomes remain validation benchmarks."
    )
    gen["osy-date"] = "2026-08-27"

    gen_path.write_text(json.dumps(gen, indent=2) + "\n")
    oar_path.write_text(json.dumps(oar, indent=2) + "\n")

    audit = {
        "case": "Philippines_v32",
        "source_case": old_case,
        "status": "source_candidate_built",
        "parameter": "RYTCM.json OAR SC_0",
        "technologies": TECHNOLOGIES,
        "modes": MODE_BY_REGIME,
        "years": [2020, 2053],
        "changed_cells": len(changed),
        "future_path": "Each existing v31 year/2020 FOFA BAU index is preserved exactly within each regime and cluster.",
        "non_forcing": True,
        "source_anchor_sha256": sha256(source_path),
        "rytm_unchanged_sha256": sha256(case / "RYTM.json"),
        "ryc_unchanged_sha256": sha256(case / "RYC.json"),
        "changes": changed,
    }
    audit_path = case / "documentation/rice_spatial_yield_source_change_v32.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({k: v for k, v in audit.items() if k != "changes"}, indent=2))


if __name__ == "__main__":
    main()

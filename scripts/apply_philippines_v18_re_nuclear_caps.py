#!/usr/bin/env python3
"""Align the Philippines v18 RE nuclear commissioning caps with PEP 2023-2050."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


EXPECTED_RYT_SHA256 = "f7e846bb1214d5279218f40734973081f22d4bdc395d51f4163c4ee7bbfaa959"
RE_SCENARIO = "SC_w03qj"
BASE_SCENARIO = "SC_0"
NU = "PHL_POW_PP_NU"
NUSMR = "PHL_POW_PP_NUSMR"
FIRST_COMMISSIONING_YEAR = 2032
MILESTONES = {2032: 1.2, 2035: 2.4, 2050: 4.8}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def append_rows(path: Path, additions: list[dict]) -> None:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        existing = list(reader)
    if fieldnames is None:
        raise AssertionError(f"Missing CSV header: {path}")
    key = fieldnames[0]
    duplicate = sorted({row[key] for row in existing} & {row[key] for row in additions})
    if duplicate:
        raise AssertionError(f"Duplicate ledger IDs in {path.name}: {duplicate}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(existing)
        writer.writerows(additions)


def apply(case: Path, package: Path) -> dict:
    ryt_path = case / "RYT.json"
    current_hash = sha256(ryt_path)
    if current_hash != EXPECTED_RYT_SHA256:
        raise AssertionError(f"Unexpected Philippines v18 RYT fingerprint: {current_hash}")

    gen = read_json(case / "genData.json")
    if gen["osy-casename"] != "Philippines_v18":
        raise AssertionError("Unexpected case identity")
    scenario_ids = {row["ScenarioId"] for row in gen["osy-scenarios"]}
    if {BASE_SCENARIO, RE_SCENARIO} - scenario_ids:
        raise AssertionError("BASE or RE scenario is missing")
    tech_ids = {row["Tech"]: row["TechId"] for row in gen["osy-tech"]}
    nu_id = tech_ids[NU]
    smr_id = tech_ids[NUSMR]

    before_hashes = {path.name: sha256(path) for path in sorted(case.glob("*.json"))}
    ryt = read_json(ryt_path)
    re_rows = {row["TechId"]: row for row in ryt["TAMaxCI"][RE_SCENARIO]}
    base_rows = {row["TechId"]: row for row in ryt["TAMaxCI"][BASE_SCENARIO]}
    nu_row = re_rows[nu_id]
    smr_row = re_rows[smr_id]

    changes = []
    for year in range(2032, 2035):
        key = str(year)
        before = nu_row[key]
        nu_row[key] = 1.2
        changes.append({"technology": NU, "technology_id": nu_id, "year": year, "before": before, "after": 1.2, "resolution": "explicit RE override"})
    for year in range(2035, 2054):
        key = str(year)
        before = nu_row[key]
        nu_row[key] = None
        changes.append({"technology": NU, "technology_id": nu_id, "year": year, "before": before, "after": None, "resolved_value": base_rows[nu_id][key], "resolution": "inherit SC_0"})
    for year in range(2032, 2035):
        key = str(year)
        before = smr_row[key]
        smr_row[key] = 0.3
        changes.append({"technology": NUSMR, "technology_id": smr_id, "year": year, "before": before, "after": 0.3, "resolution": "explicit RE override"})

    write_json(ryt_path, ryt)
    after_hashes = {path.name: sha256(path) for path in sorted(case.glob("*.json"))}
    changed_files = sorted(name for name in before_hashes if before_hashes[name] != after_hashes[name])
    if changed_files != ["RYT.json"]:
        raise AssertionError(f"Unexpected source-file changes: {changed_files}")

    data_sources = package / "data_sources"
    source_id = "SRC_PHL_PEP_2023_2050_VOL3_NUCLEAR"
    append_rows(data_sources / "SOURCES.csv", [{
        "source_id": source_id,
        "provider": "Philippines Department of Energy",
        "product": "Philippine Energy Plan 2023-2050 Volume III",
        "edition": "PEP 2023-2050",
        "reference_period": "2023-2050",
        "geography": "Philippines",
        "variable": "Nuclear Energy Program roadmap and commercial-operation milestones",
        "source_unit": "MW and milestone year",
        "exact_locator": "NEP Roadmap 2023-2032; Targets for Milestone 3; Long-Term NEP Targets",
        "url": "https://legacy.doe.gov.ph/sites/default/files/pdf/pep/PEP%202023-2050%20Vol.%20III.pdf",
        "access_date": "2026-08-13",
        "license": "Philippine government publication; provider terms",
        "sha256": "",
        "local_file": "",
        "notes": "First nuclear commercial operation in 2032; at least 1,200 MW in 2032, an additional 1,200 MW by 2035, and an additional 2,400 MW by 2050. PEP discusses conventional PWRs and SMRs but does not prescribe a technology split.",
    }])

    assumption_rows = [
        {
            "assumption_id": "ASM_PHL_V18_RE_PP_NU_2032_2034",
            "statement": "In the RE clean-energy scenario, conventional nuclear may commission from 2032 at the existing 1.20 GW/year v18 nuclear expansion rate.",
            "central_value": "1.20", "unit": "GW/year",
            "evidence_source_ids": f"{source_id};SRC_PHL_DOE_POWER_STATISTICS_2024;SRC_HEGGARTY_MAX_INVESTMENT_RATE_2024",
            "lower_bound": "", "upper_bound": "",
            "rationale": "PEP places first commercial nuclear operation and at least 1,200 MW in 2032. The scenario-specific start year is moved to 2032 while retaining the already documented v18 conventional-nuclear annual ceiling.",
            "notes": "classification=policy-scenario commissioning envelope; upper bound only; the existing aggregate PEP milestone remains separate",
        },
        {
            "assumption_id": "ASM_PHL_V18_RE_PP_NUSMR_2032_2034",
            "statement": "In the RE clean-energy scenario, nuclear SMRs may commission from 2032 at the existing early-market 0.30 GW/year v18 SMR expansion rate.",
            "central_value": "0.30", "unit": "GW/year",
            "evidence_source_ids": f"{source_id};SRC_PHL_DOE_POWER_STATISTICS_2024;SRC_HEGGARTY_MAX_INVESTMENT_RATE_2024",
            "lower_bound": "", "upper_bound": "",
            "rationale": "PEP discusses SMRs as a potentially faster-deployment nuclear option and does not prescribe the technology mix. The RE entry year moves to 2032 while retaining the documented v18 SMR rate.",
            "notes": "classification=policy-scenario commissioning envelope; upper bound only; no SMR minimum or technology share",
        },
        {
            "assumption_id": "ASM_PHL_V18_RE_NUCLEAR_INHERIT_BASE_2035_2053",
            "statement": "From 2035 onward the RE scenario inherits the policy-neutral SC_0 nuclear commissioning ceilings instead of overriding conventional nuclear with zero.",
            "central_value": "inherit SC_0", "unit": "scenario overlay rule",
            "evidence_source_ids": f"{source_id}", "lower_bound": "", "upper_bound": "",
            "rationale": "The PEP clean-energy scenario includes nuclear; retaining a zero conventional-nuclear override conflicts with that scenario. Sparse inheritance keeps physical deployment rates consistent across scenarios.",
            "notes": "classification=scenario-overlay correction; SC_0 remains unchanged",
        },
    ]
    append_rows(data_sources / "ASSUMPTIONS.csv", assumption_rows)

    calculation_rows = []
    map_rows = []
    for change in changes:
        tech_suffix = change["technology"].removeprefix("PHL_POW_")
        year = change["year"]
        calc_id = f"CALC_PHL_V18_RE_TAMAXCI_{tech_suffix}_{year}"
        assumption_id = (
            "ASM_PHL_V18_RE_PP_NUSMR_2032_2034" if change["technology"] == NUSMR
            else "ASM_PHL_V18_RE_PP_NU_2032_2034" if year <= 2034
            else "ASM_PHL_V18_RE_NUCLEAR_INHERIT_BASE_2035_2053"
        )
        resolved = change.get("resolved_value", change["after"])
        formula = "explicit RE commissioning ceiling" if change["after"] is not None else "null RE override -> inherit SC_0 commissioning ceiling"
        calculation_rows.append({
            "calculation_id": calc_id, "formula": formula,
            "source_ids": f"{source_id};SRC_MUIO_FORMULATION",
            "assumption_ids": assumption_id, "input_calculation_ids": "",
            "input_values": f"before={change['before']};source_value={change['after']};resolved={resolved}",
            "input_units": "GW/year;GW/year;GW/year", "output_value": str(resolved),
            "output_unit": "GW/year", "script_path": "scripts/apply_philippines_v18_re_nuclear_caps.py",
            "script_version": "v1", "notes": "classification=calculated scenario overlay; TotalAnnualMaxCapacityInvestment only",
        })
        map_rows.append({
            "map_id": f"MAP_PHL_V18_RE_TAMAXCI_{tech_suffix}_{year}",
            "model_file": "case/Philippines_v18/RYT.json",
            "parameter": "TotalAnnualMaxCapacityInvestment",
            "entity": f"{change['technology_id']} / {change['technology']}", "mode": "",
            "scenario": RE_SCENARIO, "years": str(year),
            "value_or_expression": str(change["after"]) if change["after"] is not None else f"inherit SC_0 ({resolved})",
            "model_unit": "GW/year", "evidence_ids": f"{calc_id};{assumption_id};{source_id}",
            "superseded_by": "", "evidence_type": "derived",
            "notes": "NCC1 new-capacity ceiling; aggregate nuclear milestone remains unchanged; no technology-specific minimum.",
        })
    append_rows(data_sources / "CALCULATIONS.csv", calculation_rows)
    append_rows(data_sources / "MODEL_MAP.csv", map_rows)

    change_id = "CHG_PHL_V18_RE_NUCLEAR_CAPS_20260813"
    append_rows(data_sources / "CHANGES.csv", [{
        "change_id": change_id, "date": "2026-08-13", "class": "B",
        "description": "Aligned RE-scenario nuclear commissioning ceilings with PEP 2023-2050: both represented nuclear options can enter in 2032, and conventional nuclear inherits the SC_0 physical envelope from 2035 instead of remaining prohibited.",
        "model_objects": "case/Philippines_v18/RYT.json TAMaxCI.SC_w03qj for PHL_POW_PP_NU and PHL_POW_PP_NUSMR",
        "evidence_path": "documentation/MODEL_FIXES_RE_NUCLEAR_CAPS_2026-08-13.md;data_sources/snapshots/re_nuclear_caps_v18_2026-08-13.json",
        "map_rows_affected": ";".join(row["map_id"] for row in map_rows),
        "resolve_status": "resolve_required", "author": "Codex", "commit": "",
        "notes": "No change to NUCLEAR_CAPACITY_TARGET, activity, dispatch, renewable share, costs, lifetimes, BASE scenario, or model equations.",
    }])

    snapshot = {
        "schema": "philippines-v18-re-nuclear-caps-v1",
        "case": "Philippines_v18", "scenario": RE_SCENARIO,
        "parameter": "TotalAnnualMaxCapacityInvestment",
        "equation": "NCC1: NewCapacity[t,y] <= TotalAnnualMaxCapacityInvestment[t,y]",
        "pep_milestones_gw": {str(year): value for year, value in MILESTONES.items()},
        "pep_first_commercial_operation_year": FIRST_COMMISSIONING_YEAR,
        "technology_split": "endogenous; PEP does not prescribe conventional nuclear versus SMR shares",
        "source_ryt_sha256": current_hash, "target_ryt_sha256": after_hashes["RYT.json"],
        "changed_source_files": changed_files, "changes": changes,
    }
    snapshot_path = data_sources / "snapshots" / "re_nuclear_caps_v18_2026-08-13.json"
    write_json(snapshot_path, snapshot)

    documentation = case / "documentation" / "MODEL_FIXES_RE_NUCLEAR_CAPS_2026-08-13.md"
    documentation.write_text(
        "# Philippines v18 RE nuclear commissioning ceilings\n\n"
        "## Reason\n\n"
        "The RE scenario retains the PEP 2023-2050 aggregate nuclear-capacity milestones of 1.2 GW in 2032, 2.4 GW in 2035 and 4.8 GW in 2050. The inherited RE `TAMaxCI` overlay nevertheless prohibited conventional nuclear throughout the horizon, while the v18 BASE deployment envelope did not allow either represented nuclear technology to commission before 2035.\n\n"
        "## Source change\n\n"
        "Only `RYT.json` `TotalAnnualMaxCapacityInvestment` (`TAMaxCI`) cells in scenario `SC_w03qj` change. Conventional nuclear receives a 1.20 GW/year ceiling in 2032-2034 and then inherits the unchanged BASE 1.20 GW/year ceiling from 2035. SMR receives a 0.30 GW/year ceiling in 2032-2034 and then continues to inherit the unchanged BASE ceilings of 0.30 GW/year in 2035-2039 and 0.60 GW/year from 2040.\n\n"
        "No capacity minimum, activity bound, generation share, technology split or new constraint is introduced. `NUCLEAR_CAPACITY_TARGET` is unchanged and remains aggregate across conventional nuclear and SMR.\n\n"
        "## Evidence and interpretation\n\n"
        "DOE PEP 2023-2050 Volume III places construction of the first nuclear plant in Milestone 3 (2028-2032), first commercial operation in 2032, at least 1,200 MW in 2032, an additional 1,200 MW by 2035 and an additional 2,400 MW by 2050. It discusses conventional PWR and SMR options without prescribing a technology split. In OSeMOSYS, `NewCapacity` is commissioned capacity; construction starts are not represented separately.\n\n"
        "## Validation\n\n"
        "A disposable copy was generated and preprocessed through `DataFile.generateDatafile('TOMORROWLAND')` and `preprocessData()`. Deterministic validation confirmed that only 25 `TAMaxCI.SC_w03qj` cells changed and that no nuclear commissioning is allowed before 2032. GLPK successfully generated the complete matrix: 791,532 rows, 886,010 columns and 12,818,407 matrix nonzeros.\n\n"
        "The single source-candidate CBC optimization completed optimal with objective 369,766,929.90727115 after 310,312 iterations and 426.77 wall-clock seconds. There was zero primal infeasibility after postsolve and cleanup. No nuclear capacity was built before 2032. The endogenous technology split was 0.9 GW conventional plus 0.3 GW SMR in 2032; cumulative capacity was 1.8 plus 0.6 GW in 2035; and 3.6 plus 1.2 GW in 2050, exactly meeting the unchanged aggregate PEP milestones. All annual construction caps were respected.\n\n"
        "Two initial GLPK matrix-generation attempts ended before writing an LP because two stale CBC processes from the earlier failed/manual diagnosis were still consuming host memory. Those previously requested-to-stop processes were terminated; GLPK then completed normally. These matrix-generation attempts were not optimizer runs.\n",
        encoding="utf-8",
    )
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(apply(args.case.resolve(), args.package.resolve()), indent=2))


if __name__ == "__main__":
    main()

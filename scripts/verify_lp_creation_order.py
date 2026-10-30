#!/usr/bin/env python3
"""Retroactively verify that a generated run's LP respects data-file creation order.

Reads only artifacts already on disk -- no regeneration, no solving. It re-parses
`data.txt` with the same loop `DataFile.preprocessData` uses, builds the set-member
order that first-seen de-duplication (`dict.fromkeys`) must produce, and compares it
element-by-element with the `set MODExTECHNOLOGYper...` / `set MODEperTECHNOLOGY`
lines actually written into `data_processed.txt`.

A run generated with the old `list(set(...))` de-duplication fails this check
(hash order != first-seen order); a run generated with the fix passes exactly.
Usage: verify_lp_creation_order.py <run-dir> [<run-dir> ...]
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PARAM_STARTS = (
    'param OutputActivityRatio', 'param InputActivityRatio',
    'param EmissionActivityRatio', 'param EmissionToActivityChangeRatio',
    'param OperationalLife', 'param DiscountRateIdv', 'param DiscountRate',
    'param TechnologyToStorage', 'param TechnologyFromStorage',
    'param InputToNewCapacityRatio', 'param InputToTotalCapacityRatio',
)
RATIO_PARAMS = ('OutputActivityRatio', 'InputActivityRatio',
                'EmissionActivityRatio', 'EmissionToActivityChangeRatio')
SET_LINE = re.compile(r"^set (\S+?)\[(.*?)\]:=(.*);$")
PAIR = re.compile(r"\((\S+?), (\S+?)\)")


def parse_source(data_txt: Path, start_year: str):
    """Replicate DataFileClass.preprocessData's parse of data.txt, in file order."""
    data: dict[str, list] = {}
    data_all: list[tuple[str, str]] = []
    param_current = None
    tech = fuel_emi = None
    with data_txt.open(encoding="utf-8", errors="replace") as handle:
        parsing = False
        for line in handle:
            line = line.rstrip().replace('\t', ' ')
            if line.startswith(";"):
                parsing = False
            if parsing:
                if line.startswith('['):
                    element = line.split(',')
                    tech = element[1]
                    fuel_emi = element[2]
                elif line.startswith(start_year):
                    pass
                elif param_current in RATIO_PARAMS:
                    mode = line.split(' ')[0]
                    data[param_current].append((fuel_emi, tech, mode))
                    data_all.append((tech, mode))
            if line.startswith(PARAM_STARTS):
                param_current = line.split(' ')[1]
                data[param_current] = []
                parsing = True
    return data, data_all


def expected_sets(data, data_all):
    """First-seen de-duplication, exactly as dict.fromkeys produces."""
    out: dict[str, dict[str, list]] = {}
    for param, set_name in (
        ("OutputActivityRatio", "MODExTECHNOLOGYperFUELout"),
        ("InputActivityRatio", "MODExTECHNOLOGYperFUELin"),
        ("EmissionActivityRatio", "MODExTECHNOLOGYperEMISSION"),
        ("EmissionToActivityChangeRatio", "MODExTECHNOLOGYperEMISSIONChange"),
    ):
        grouped: dict[str, list] = defaultdict(list)
        for key, tech, mode in dict.fromkeys(data.get(param, [])):
            grouped[key].append((mode, tech))
        out[set_name] = dict(grouped)
    modes: dict[str, list] = defaultdict(list)
    for tech, mode in dict.fromkeys(data_all):
        if mode not in modes[tech]:
            modes[tech].append(mode)
    out["MODEperTECHNOLOGY"] = dict(modes)
    return out


def actual_sets(processed: Path):
    found: dict[str, dict[str, list]] = defaultdict(dict)
    with processed.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = SET_LINE.match(line.strip())
            if not match:
                continue
            name, key, body = match.groups()
            if name == "MODEperTECHNOLOGY":
                found[name][key] = body.split()
            elif name.startswith("MODExTECHNOLOGYper"):
                found[name][key] = [(m, t) for m, t in PAIR.findall(body)]
    return found


def verify(run: Path) -> dict:
    data_txt, processed = run / "data.txt", run / "data_processed.txt"
    if not data_txt.is_file() or not processed.is_file():
        return {"run": run.name, "status": "skipped", "reason": "missing artifacts"}
    # start_year is the first year column label in the ratio blocks
    start_year = None
    with data_txt.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            m = re.match(r"^\s*(\d{4})\s", line)
            if m:
                start_year = m.group(1)
                break
    data, data_all = parse_source(data_txt, start_year)
    expected, actual = expected_sets(data, data_all), actual_sets(processed)

    mismatches, compared = [], 0
    for set_name, groups in expected.items():
        got = actual.get(set_name, {})
        for key, want in groups.items():
            have = got.get(key)
            if have is None:
                continue
            compared += 1
            if have != want:
                if len(mismatches) < 5:
                    mismatches.append({
                        "set": set_name, "key": key,
                        "expected_first_seen_order": [list(x) for x in want[:8]],
                        "written_order": [list(x) if isinstance(x, tuple) else x
                                          for x in have[:8]],
                        "same_members": sorted(map(str, have)) == sorted(map(str, want)),
                    })
    return {
        "run": run.name, "case": run.parent.parent.name,
        "start_year": start_year,
        "set_groups_compared": compared,
        "mismatch_count": sum(
            1 for set_name, groups in expected.items()
            for key, want in groups.items()
            if actual.get(set_name, {}).get(key) is not None
            and actual[set_name][key] != want
        ),
        "status": "pass" if not mismatches else "FAIL",
        "example_mismatches": mismatches,
    }


def main() -> None:
    results = [verify(Path(a)) for a in sys.argv[1:]]
    print(json.dumps(results, indent=2))
    if any(r["status"] == "FAIL" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()

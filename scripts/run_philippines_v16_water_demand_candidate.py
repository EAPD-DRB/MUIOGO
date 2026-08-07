#!/usr/bin/env python3
"""Generate and solve the disposable Philippines v16 water-demand candidate."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import types
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(REPO / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.DataFileClass import DataFile  # noqa: E402


def first_matching_line(text: str, patterns: tuple[str, ...]) -> str | None:
    for line in text.splitlines():
        if any(pattern in line for pattern in patterns):
            return line.strip()
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--run", default="BASE_V15")
    args = parser.parse_args()

    # Preserve a DataStorage symlink entry: global Parameters/Variables files
    # live beside the link, not beside its resolved external case directory.
    target = args.target.absolute()
    Config.DATA_STORAGE = target.parent
    model = DataFile(target.name)

    started = time.time()
    generation = model.generateDatafile(args.run)
    response = model.run("cbc", args.run)
    elapsed = time.time() - started

    cbc = response.get("cbc_message", "")
    glpk = response.get("glpk_message", "")
    objective_match = re.search(r"objective value\s*([-+0-9.eE]+)", cbc, re.IGNORECASE)
    summary = {
        "case": target.name,
        "run": args.run,
        "generation": generation,
        "status": response.get("status_code"),
        "timer": response.get("timer"),
        "wall_seconds": elapsed,
        "objective": float(objective_match.group(1)) if objective_match else None,
        "cbc_status_line": first_matching_line(cbc, ("Optimal", "infeasible", "ERROR")),
        "cbc_time_line": first_matching_line(cbc, ("Total time (CPU seconds):",)),
        "matrix_line": first_matching_line(glpk, ("rows,", "columns,")),
        "artifacts": {
            name: str(target / "res" / args.run / name)
            for name in ("data.txt", "data_processed.txt", "lp.lp", "results.txt")
        },
    }
    output = target / "water_demand_validation_summary.json"
    output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

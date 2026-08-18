#!/usr/bin/env python3
"""Run the single budgeted CBC solve for the PHL v18 fossil candidate."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import types
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STORAGE = REPO / "WebAPP" / "DataStorage"
DEFAULT_CASE = ".Philippines_v18-fossil-resource-candidate"
DEFAULT_RUN = "TOMORROWLAND"

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(REPO / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.DataFileClass import DataFile  # noqa: E402
from Classes.Case.OsemosysClass import Osemosys  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--run", default=DEFAULT_RUN)
    parser.add_argument("--cbc-seconds", type=int, default=850)
    args = parser.parse_args()

    case_path = STORAGE / args.case
    run_path = case_path / "res" / args.run
    lp = run_path / "lp.lp"
    result = run_path / "results.txt"
    log = run_path / "candidate_cbc.log"
    report_path = run_path / "candidate_solve_report.json"
    if not lp.is_file():
        raise FileNotFoundError(lp)
    for path in (result, log, report_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite prior candidate artifact: {path}")

    Config.DATA_STORAGE = STORAGE
    model = DataFile(args.case)
    cbc = Osemosys._find_solver_binary(model.cbcFolder.resolve(), "cbc", recursive=False)
    if cbc is None:
        raise RuntimeError("CBC solver is unavailable")
    command = [
        str(cbc),
        str(lp.resolve()),
        "-seconds",
        str(args.cbc_seconds),
        "solve",
        "-printing",
        "all",
        "-solu",
        str(result.resolve()),
    ]
    print(f"CBC candidate solve started with {args.cbc_seconds}s solver budget", flush=True)
    started = time.monotonic()
    with log.open("w", encoding="utf-8") as stream:
        import subprocess

        process = subprocess.Popen(
            command,
            cwd=model.cbcFolder.resolve() if model.cbc_is_bundled else None,
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
        )
        last_report = 0
        while process.poll() is None:
            elapsed = int(time.monotonic() - started)
            if elapsed - last_report >= 30:
                print(f"CBC still running: {elapsed}s elapsed", flush=True)
                last_report = elapsed
            time.sleep(5)
        returncode = process.returncode
    wall_seconds = time.monotonic() - started
    output = log.read_text(encoding="utf-8", errors="replace")
    optimal = re.search(r"Optimal objective\s+([-+0-9.eE]+)", output)
    if optimal is None:
        optimal = re.search(r"Optimal - objective value\s+([-+0-9.eE]+)", output)
    status = "optimal" if returncode == 0 and optimal else "failed"
    objective = float(optimal.group(1)) if optimal else None
    report = {
        "status": status,
        "case": str(case_path),
        "run": args.run,
        "cbc_seconds_budget": args.cbc_seconds,
        "wall_seconds": wall_seconds,
        "returncode": returncode,
        "objective": objective,
        "command": command,
        "log_tail": output[-6000:],
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if status != "optimal":
        print(json.dumps(report, indent=2), flush=True)
        raise SystemExit(1)

    # Export the already solved result; these calls do not invoke an optimizer.
    model.generateCSVfromCBC(run_path / "data.txt", result, run_path)
    model.generateResultsViewer(args.run)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

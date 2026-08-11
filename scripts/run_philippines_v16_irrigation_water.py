#!/usr/bin/env python3
"""Run the disposable or live Philippines v16 rice-water validation chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import types
from datetime import date
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(REPO / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.DataFileClass import DataFile  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_run(model: DataFile, run: str) -> None:
    run_path = Path(Config.DATA_STORAGE, model.case, "res", run)
    if run_path.is_dir():
        return
    scenarios = [
        {
            "ScenarioId": item["ScenarioId"],
            "Scenario": item["Scenario"],
            "Desc": item.get("Desc", ""),
            "Active": item["ScenarioId"] == "SC_0",
        }
        for item in model.genData["osy-scenarios"]
    ]
    response = model.createCaseRun(
        run,
        {
            "Case": run,
            "CaseId": "RUN_PHL_V16_IRRIGATION_WATER",
            "Desc": "Philippines v16 engineering rice-water validation.",
            "Runtime": date.today().isoformat(),
            "Scenarios": scenarios,
        },
    )
    if response.get("status_code") != "success":
        raise RuntimeError(json.dumps(response, indent=2))


def initialize(target: Path, run: str) -> tuple[DataFile, Path]:
    target = target.absolute()
    Config.DATA_STORAGE = target.parent
    model = DataFile(target.name)
    ensure_run(model, run)
    return model, target / "res" / run


def generate(model: DataFile, run: str, run_path: Path) -> dict:
    started = time.time()
    generation = model.generateDatafile(run)
    model.preprocessData(run_path / "data.txt", run_path / "data_processed.txt")
    return {
        "phase": "generate",
        "generation": generation,
        "wall_seconds": time.time() - started,
        "hashes": {name: sha256(run_path / name) for name in ("data.txt", "data_processed.txt")},
    }


def matrix(model: DataFile, run_path: Path) -> dict:
    started = time.time()
    command = [
        "/opt/homebrew/bin/glpsol", "--check", "-m", str(model.osemosysFile.resolve()),
        "-d", str((run_path / "data_processed.txt").resolve()),
        "--wlp", str((run_path / "lp.lp").resolve()),
    ]
    process = subprocess.run(command, text=True, capture_output=True)
    text = process.stdout + process.stderr
    match = re.search(r"(\d+) rows, (\d+) columns, (\d+) non-zeros", text)
    if match is None:
        match = re.search(
            r"Number of rows\s*=\s*(\d+).*?Number of columns\s*=\s*(\d+).*?Number of non-zeros \(matrix\)\s*=\s*(\d+)",
            text,
            re.DOTALL,
        )
    if process.returncode != 0 or match is None:
        raise RuntimeError(text[-5000:])
    return {
        "phase": "matrix",
        "wall_seconds": time.time() - started,
        "matrix": {"rows": int(match.group(1)), "columns": int(match.group(2)), "nonzeros": int(match.group(3))},
        "lp_sha256": sha256(run_path / "lp.lp"),
        "tail": text[-3000:],
    }


def bounded(run_path: Path, seconds: int) -> dict:
    started = time.time()
    command = [
        "/opt/homebrew/bin/cbc", str((run_path / "lp.lp").resolve()),
        "-seconds", str(seconds), "solve", "-solu", str((run_path / "bounded_results.txt").resolve()),
    ]
    process = subprocess.run(command, text=True, capture_output=True)
    text = process.stdout + process.stderr
    if process.returncode != 0:
        raise RuntimeError(text[-5000:])
    return {"phase": "bounded", "limit_seconds": seconds, "wall_seconds": time.time() - started, "tail": text[-3000:]}


def solve(model: DataFile, run: str, run_path: Path) -> dict:
    started = time.time()
    response = model.run("cbc", run)
    elapsed = time.time() - started
    first_line = (run_path / "results.txt").open(encoding="utf-8").readline().strip()
    objective_match = re.search(r"objective value\s+([-+0-9.eE]+)", first_line, re.IGNORECASE)
    matrix_match = re.search(r"(\d+) rows, (\d+) columns, (\d+) non-zeros", response.get("glpk_message", ""))
    if response.get("status_code") != "success" or objective_match is None:
        raise RuntimeError(json.dumps(response, indent=2)[-10000:])
    return {
        "phase": "solve",
        "status": response.get("status_code"),
        "first_line": first_line,
        "objective": float(objective_match.group(1)),
        "wall_seconds": elapsed,
        "timer": response.get("timer"),
        "matrix": ({"rows": int(matrix_match.group(1)), "columns": int(matrix_match.group(2)), "nonzeros": int(matrix_match.group(3))} if matrix_match else None),
        "hashes": {name: sha256(run_path / name) for name in ("data.txt", "data_processed.txt", "lp.lp", "results.txt")},
        "cbc_tail": response.get("cbc_message", "")[-3000:],
        "glpk_tail": response.get("glpk_message", "")[-3000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("generate", "matrix", "bounded", "solve"))
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--run", default="IRRIGATION_WATER_TEST")
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    started = time.time()
    try:
        model, run_path = initialize(args.target, args.run)
        if args.phase == "generate":
            result = generate(model, args.run, run_path)
        elif args.phase == "matrix":
            result = matrix(model, run_path)
        elif args.phase == "bounded":
            result = bounded(run_path, args.seconds)
        else:
            result = solve(model, args.run, run_path)
        result.update({"case": args.target.name, "run": args.run, "total_wall_seconds": time.time() - started})
        if args.report:
            args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"status": "fail", "phase": args.phase, "error": str(error)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

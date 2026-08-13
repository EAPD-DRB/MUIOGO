#!/usr/bin/env python3
"""Generate and preprocess a Philippines v18 TOMORROWLAND test artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--run", default="TOMORROWLAND")
    args = parser.parse_args()
    # Preserve an application-visible DataStorage symlink. Resolving it would
    # move Config.DATA_STORAGE away from the shared Parameters.json file.
    case = args.case.absolute()
    Config.DATA_STORAGE = case.parent
    model = DataFile(case.name)
    run_path = case / "res" / args.run
    run_path.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    generation = model.generateDatafile(args.run)
    generated_seconds = time.monotonic() - started
    started = time.monotonic()
    model.preprocessData(run_path / "data.txt", run_path / "data_processed.txt")
    preprocessed_seconds = time.monotonic() - started
    report = {
        "status": "pass",
        "case": str(case),
        "run": args.run,
        "generation_response": generation,
        "timings_seconds": {
            "generate_datafile": generated_seconds,
            "preprocess_data": preprocessed_seconds,
        },
        "hashes": {
            name: sha256(run_path / name)
            for name in ("data.txt", "data_processed.txt")
        },
    }
    (run_path / "generation_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate and preprocess the disposable PHL v18 border-price candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import types
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STORAGE = REPO / "WebAPP" / "DataStorage"
DEFAULT_CASE = ".Philippines_v18-fossil-border-price-candidate"
DEFAULT_RUN = "TOMORROWLAND"

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
sys.path.insert(0, str(REPO / "API"))

from Classes.Base import Config  # noqa: E402
from Classes.Case.DataFileClass import DataFile  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--run", default=DEFAULT_RUN)
    parser.add_argument(
        "--replace-existing-generated",
        action="store_true",
        help="Allow application regeneration of existing data.txt and data_processed.txt.",
    )
    args = parser.parse_args()

    Config.DATA_STORAGE = STORAGE
    model = DataFile(args.case)
    run_path = STORAGE / args.case / "res" / args.run
    data = run_path / "data.txt"
    processed = run_path / "data_processed.txt"
    if (data.exists() or processed.exists()) and not args.replace_existing_generated:
        raise FileExistsError(f"refusing to overwrite generated candidate input: {run_path}")
    run_path.mkdir(parents=True, exist_ok=True)
    model.generateDatafile(args.run)
    model.preprocessData(data, processed)
    report = {
        "schema": "philippines-v18-fossil-border-price-generation-v1",
        "date": "2026-08-18",
        "case": args.case,
        "run": args.run,
        "data_txt": str(data),
        "data_txt_sha256": sha256(data),
        "data_processed_txt": str(processed),
        "data_processed_txt_sha256": sha256(processed),
        "optimizer_runs": 0,
    }
    report_path = run_path / "border_price_generation_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

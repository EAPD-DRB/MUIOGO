#!/usr/bin/env python3
"""Seal, verify, and promote a complete validated MUIO case without rebuilding it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


SEAL_RELATIVE_PATH = Path("documentation") / "SEALED_CANDIDATE.json"
IGNORED_PARTS = {".DS_Store", "view"}
REQUIRED_RUN_FILES = (
    "data.txt",
    "data_processed.txt",
    "lp.lp",
    "cbc.log",
    "results.txt",
    "generation_matrix_report.json",
    "optimization_record.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def included_files(case: Path) -> list[Path]:
    files: list[Path] = []
    for path in case.rglob("*"):
        relative = path.relative_to(case)
        if path.is_symlink():
            raise RuntimeError(f"sealed cases may not contain symlinks: {relative}")
        if not path.is_file() or relative == SEAL_RELATIVE_PATH:
            continue
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        files.append(relative)
    return sorted(files, key=lambda item: item.as_posix())


def file_manifest(case: Path) -> dict[str, dict[str, int | str]]:
    return {
        relative.as_posix(): {
            "sha256": sha256(case / relative),
            "bytes": (case / relative).stat().st_size,
        }
        for relative in included_files(case)
    }


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected a JSON object: {path}")
    return value


def validate_run_inventory(case: Path, required_runs: list[str]) -> dict[str, dict]:
    if len(required_runs) != len(set(required_runs)):
        raise RuntimeError("required run names must be unique")
    run_root = case / "res"
    actual = sorted(path.name for path in run_root.iterdir() if path.is_dir()) if run_root.is_dir() else []
    expected = sorted(required_runs)
    if actual != expected:
        raise RuntimeError(f"unclean run inventory: expected {expected}, found {actual}")

    records: dict[str, dict] = {}
    for name in required_runs:
        run = run_root / name
        missing = [filename for filename in REQUIRED_RUN_FILES if not (run / filename).is_file()]
        if missing:
            raise RuntimeError(f"run {name} is incomplete: missing {missing}")
        optimization = read_json(run / "optimization_record.json")
        generation = read_json(run / "generation_matrix_report.json")
        if not str(optimization.get("status", "")).startswith("Optimal"):
            raise RuntimeError(f"run {name} is not optimal: {optimization.get('status')}")
        if optimization.get("optimizer_runs") != 1:
            raise RuntimeError(f"run {name} has an invalid optimizer-run count")
        if generation.get("status") != "passed" or generation.get("optimizer_runs") != 0:
            raise RuntimeError(f"run {name} lacks a clean generation/matrix gate")
        if sha256(run / "lp.lp") != optimization.get("lp_sha256"):
            raise RuntimeError(f"run {name} LP hash does not match its optimization record")
        if sha256(run / "results.txt") != optimization.get("results_sha256"):
            raise RuntimeError(f"run {name} results hash does not match its optimization record")
        records[name] = {
            "status": optimization["status"],
            "scenario": optimization.get("scenario"),
            "objective": optimization.get("objective"),
            "lp_sha256": optimization["lp_sha256"],
            "results_sha256": optimization["results_sha256"],
        }
    return records


def seal_case(case: Path, final_name: str, required_runs: list[str], qualification: Path) -> dict:
    case = case.resolve()
    if not case.is_dir():
        raise FileNotFoundError(case)
    if Path(final_name).name != final_name or final_name in ("", ".", ".."):
        raise ValueError("final name must be one directory name")
    seal_path = case / SEAL_RELATIVE_PATH
    if seal_path.exists():
        raise FileExistsError(f"candidate is already sealed: {seal_path}")
    qualification = qualification if qualification.is_absolute() else case / qualification
    qualification = qualification.resolve()
    if case not in qualification.parents:
        raise RuntimeError("qualification must be stored inside the candidate")
    qualification_record = read_json(qualification)
    if qualification_record.get("promotion_allowed") is not True:
        raise RuntimeError("qualification does not allow promotion")
    run_records = validate_run_inventory(case, required_runs)
    manifest = {
        "schema": "muio-sealed-candidate-v1",
        "final_case_name": final_name,
        "candidate_directory_at_seal": case.name,
        "qualification": qualification.relative_to(case).as_posix(),
        "qualification_sha256": sha256(qualification),
        "required_runs": required_runs,
        "run_records": run_records,
        "excluded_from_seal": ["view/**", ".DS_Store", SEAL_RELATIVE_PATH.as_posix()],
        "files": file_manifest(case),
        "promotion_contract": {
            "generation_runs_during_promotion": 0,
            "preprocess_runs_during_promotion": 0,
            "glpsol_runs_during_promotion": 0,
            "optimizer_runs_during_promotion": 0,
            "method": "verified recoverable filesystem rename",
        },
    }
    seal_path.parent.mkdir(parents=True, exist_ok=True)
    seal_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify_seal(case: Path) -> dict:
    case = case.resolve()
    seal_path = case / SEAL_RELATIVE_PATH
    manifest = read_json(seal_path)
    if manifest.get("schema") != "muio-sealed-candidate-v1":
        raise RuntimeError("unsupported or invalid seal schema")
    expected = manifest.get("files")
    actual = file_manifest(case)
    if actual != expected:
        missing = sorted(set(expected or {}) - set(actual))
        added = sorted(set(actual) - set(expected or {}))
        changed = sorted(
            path for path in set(actual) & set(expected or {}) if actual[path] != expected[path]
        )
        raise RuntimeError(
            f"sealed candidate changed: missing={missing}, added={added}, changed={changed}"
        )
    qualification = case / manifest["qualification"]
    if sha256(qualification) != manifest["qualification_sha256"]:
        raise RuntimeError("qualification hash changed after sealing")
    validate_run_inventory(case, list(manifest["required_runs"]))
    return manifest


def promote_case(candidate: Path, live: Path, backup: Path, execute: bool, allow_new: bool = False) -> dict:
    candidate = candidate.resolve()
    live = live.parent.resolve() / live.name
    backup = backup.parent.resolve() / backup.name
    manifest = verify_seal(candidate)
    if live.name != manifest["final_case_name"]:
        raise RuntimeError(f"seal targets {manifest['final_case_name']}, not {live.name}")
    if candidate.parent != live.parent or live.parent != backup.parent:
        raise RuntimeError("candidate, live case and backup must be siblings")
    live_exists = live.is_dir()
    if live.exists() and not live_exists:
        raise RuntimeError(f"live path exists but is not a directory: {live}")
    if not live_exists and not allow_new:
        raise FileNotFoundError(live)
    if backup.exists():
        raise FileExistsError(backup)
    if len({candidate, live, backup}) != 3:
        raise RuntimeError("candidate, live case and backup must be distinct")
    device = candidate.stat().st_dev
    if (live_exists and live.stat().st_dev != device) or live.parent.stat().st_dev != device:
        raise RuntimeError("promotion must remain on one filesystem")
    report = {
        "status": "ready" if not execute else "promoted",
        "candidate": str(candidate),
        "live": str(live),
        "backup": str(backup),
        "promotion_mode": "replace" if live_exists else "first_publication",
        "sealed_file_count": len(manifest["files"]),
        "generation_runs": 0,
        "preprocess_runs": 0,
        "glpsol_runs": 0,
        "optimizer_runs": 0,
    }
    if not execute:
        return report
    if not live_exists:
        os.rename(candidate, live)
    else:
        os.rename(live, backup)
        try:
            os.rename(candidate, live)
        except BaseException:
            os.rename(backup, live)
            raise
    return report


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    seal = commands.add_parser("seal", help="validate and hash a clean release candidate")
    seal.add_argument("--candidate", type=Path, required=True)
    seal.add_argument("--final-name", required=True)
    seal.add_argument("--run", action="append", required=True, dest="runs")
    seal.add_argument("--qualification", type=Path, required=True)
    verify = commands.add_parser("verify", help="verify an existing candidate seal")
    verify.add_argument("--candidate", type=Path, required=True)
    promote = commands.add_parser("promote", help="verify and swap a sealed candidate into place")
    promote.add_argument("--candidate", type=Path, required=True)
    promote.add_argument("--live", type=Path, required=True)
    promote.add_argument("--backup", type=Path, required=True)
    promote.add_argument("--allow-new", action="store_true", help="allow first publication when the live case does not yet exist")
    promote.add_argument("--execute", action="store_true", help="perform the rename; default is dry-run")
    return root


def main() -> None:
    args = parser().parse_args()
    if args.command == "seal":
        result = seal_case(args.candidate, args.final_name, args.runs, args.qualification)
        output = {"status": "sealed", "files": len(result["files"]), "runs": result["required_runs"]}
    elif args.command == "verify":
        result = verify_seal(args.candidate)
        output = {"status": "verified", "files": len(result["files"]), "runs": result["required_runs"]}
    else:
        output = promote_case(args.candidate, args.live, args.backup, args.execute, args.allow_new)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

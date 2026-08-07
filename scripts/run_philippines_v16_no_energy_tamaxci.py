#!/usr/bin/env python3
"""Solve the disposable Philippines v16 no-energy-TAMaxCI case.

The normal path is the MUIO application chain, which needs pandas. Where
pandas is unavailable the script falls back to datafile surgery: it copies the
reference BASE run's ``data_processed.txt`` and rewrites only the
``TotalAnnualMaxCapacityInvestment`` block, keeping every other byte identical.

The fallback is exact rather than approximate. ``DataFile.gen_RYT`` writes a
technology row only when at least one year differs from the parameter default,
so a case whose energy-sector TAMaxCI is all 999999 regenerates a block holding
just the two non-energy accounting terminals. ``DataFile.preprocessData`` does
not parse TAMaxCI, so the block also passes from ``data.txt`` into
``data_processed.txt`` unchanged. Both claims are asserted before solving.

Solver invocation mirrors ``DataFile.run``:
    glpsol --check -m <model> -d data_processed.txt --wlp lp.lp
    cbc lp.lp solve -solu results.txt
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
STORAGE = REPO / "WebAPP" / "DataStorage"
MODEL = REPO / "WebAPP" / "SOLVERs" / "model.v.5.4.txt"

PARAM_HEADER = "param TotalAnnualMaxCapacityInvestment"
KEEP_TECHS = ("ENV_LAND", "ENV_WATER")


def split_block(lines: list[str]) -> tuple[int, int]:
    """Return the half-open line range of the TAMaxCI block."""
    start = next(i for i, line in enumerate(lines) if line.startswith(PARAM_HEADER))
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith(";"))
    return start, end + 1


def rewrite_datafile(reference: Path, destination: Path, manifest: dict) -> dict:
    lines = reference.read_text().splitlines(keepends=True)
    start, end = split_block(lines)
    block = lines[start:end]

    header, region, years = block[0], block[1], block[2]
    rows = block[3:-1]
    assert region.startswith("[RE1,*,*]"), region
    assert years.lstrip().startswith("2020"), years

    cleared = {item["tech"] for item in manifest["cleared"]}
    retained = {item["tech"] for item in manifest["retained"]}
    assert retained == set(KEEP_TECHS), retained

    present = [line.split(" ", 1)[0] for line in rows]
    assert set(present) == cleared | retained, sorted(set(present) ^ (cleared | retained))

    kept = [line for line in rows if line.split(" ", 1)[0] in retained]
    assert len(kept) == len(KEEP_TECHS), kept

    new_block = [header, region, years, *kept, lines[end - 1]]
    destination.write_text("".join(lines[:start] + new_block + lines[end:]))

    # Everything outside the block must be byte-identical to the reference.
    after = destination.read_text().splitlines(keepends=True)
    new_start, new_end = split_block(after)
    assert lines[:start] == after[:new_start]
    assert lines[end:] == after[new_end:]

    return {
        "reference_rows": len(rows),
        "rewritten_rows": len(kept),
        "removed_rows": len(rows) - len(kept),
        "retained_rows": sorted(retained),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=STORAGE / ".Philippines_v16-no-energy-tamaxci")
    parser.add_argument(
        "--reference-run",
        type=Path,
        default=STORAGE / "Philippines_v16" / "res" / "BASE_V15",
        help="solved BASE run whose data_processed.txt is the byte-for-byte reference",
    )
    parser.add_argument("--run", default="BASE_V15")
    args = parser.parse_args()

    target = args.target.absolute()
    manifest = json.loads((target / "no_energy_tamaxci_manifest.json").read_text())

    run_dir = target / "res" / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "csv").mkdir(exist_ok=True)

    reference = args.reference_run / "data_processed.txt"
    shutil.copy2(args.reference_run / "data.txt", run_dir / "data.txt")
    surgery = rewrite_datafile(reference, run_dir / "data_processed.txt", manifest)

    lp_file = run_dir / "lp.lp"
    results = run_dir / "results.txt"

    started = time.time()
    glpk = subprocess.run(
        ["glpsol", "--check", "-m", str(MODEL), "-d", str(run_dir / "data_processed.txt"),
         "--wlp", str(lp_file)],
        capture_output=True,
        text=True,
    )
    matrix = time.time() - started
    if glpk.returncode != 0:
        raise SystemExit(f"glpsol failed:\n{glpk.stdout[-4000:]}\n{glpk.stderr[-2000:]}")

    cbc = subprocess.run(
        ["cbc", str(lp_file), "solve", "-solu", str(results)],
        capture_output=True,
        text=True,
    )
    elapsed = time.time() - started
    if cbc.returncode != 0:
        raise SystemExit(f"cbc failed:\n{cbc.stdout[-4000:]}\n{cbc.stderr[-2000:]}")

    status = results.read_text(errors="ignore").split("\n", 1)[0].strip()
    objective = re.search(r"objective value\s*([-+0-9.eE]+)", status)
    summary = {
        "case": target.name,
        "run": args.run,
        "reference_run": str(args.reference_run),
        "datafile_surgery": surgery,
        "status_line": status,
        "objective": float(objective.group(1)) if objective else None,
        "matrix_seconds": matrix,
        "wall_seconds": elapsed,
        "matrix_line": next(
            (line.strip() for line in glpk.stdout.splitlines() if "rows," in line), None
        ),
    }
    (target / "no_energy_tamaxci_run_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

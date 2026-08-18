#!/usr/bin/env python3
"""Prove that two MUIO preprocessed data files differ only by set ordering."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


TOKEN = re.compile(r"\([^)]*\)|\S+")


def normalize_set(line: str) -> tuple[str, Counter[str]] | None:
    if not line.startswith("set ") or ":=" not in line or not line.endswith(";"):
        return None
    declaration, values = line[:-1].split(":=", 1)
    return declaration.strip(), Counter(TOKEN.findall(values.strip()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()

    left = args.left.read_text(encoding="utf-8").splitlines()
    right = args.right.read_text(encoding="utf-8").splitlines()
    if len(left) != len(right):
        raise SystemExit(f"FAIL: line counts differ: {len(left)} != {len(right)}")

    changed = 0
    for line_number, (old, new) in enumerate(zip(left, right), start=1):
        if old == new:
            continue
        changed += 1
        old_set = normalize_set(old)
        new_set = normalize_set(new)
        if old_set is None or new_set is None or old_set != new_set:
            raise SystemExit(
                f"FAIL: result-relevant difference at line {line_number}\nLEFT: {old}\nRIGHT: {new}"
            )

    print(
        "PASS: files have identical ordered lines except for "
        f"{changed} derived set declarations whose members are exactly equal as multisets"
    )


if __name__ == "__main__":
    main()

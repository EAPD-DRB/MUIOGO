"""Run the frontend behavior regressions without a browser or backend writes."""

from pathlib import Path
import shutil
import subprocess

import pytest


def test_frontend_runtime():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for frontend runtime tests")
    root = Path(__file__).resolve().parents[1]
    tests = sorted((root / "tests" / "frontend").glob("*.test.mjs"))
    result = subprocess.run(
        [node, "--test", *map(str, tests)],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr

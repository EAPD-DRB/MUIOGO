"""Browser (Playwright) tests. They run under pytest only: `pytest tests/e2e`.

`scripts/smoke.sh` and `smoke.bat` use `unittest discover`, whose pattern
`test_*smoke.py` also matches `test_shell_smoke.py` here. These tests are pytest
functions, so unittest has nothing to run in them, and importing them fails on a
plain install, which has no pytest. This hook tells unittest discovery to skip
the package; pytest does not use it.
"""


def load_tests(loader, standard_tests, pattern):
    return standard_tests

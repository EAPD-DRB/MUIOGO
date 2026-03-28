"""
Test for Issue #328: File handle not closed in readDataFile.
Verifies that the `with open()` pattern is used instead of bare `f.close` (no parens).
"""
import sys
import inspect
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'API'))

from API.Classes.Case.DataFileClass import DataFile


def run_tests():
    passed = 0
    failed = 0

    # Test 1: Check that readDataFile uses 'with open' (context manager)
    source = inspect.getsource(DataFile.readDataFile)

    if 'with open(' in source:
        print("PASS: readDataFile uses 'with open()' context manager")
        passed += 1
    else:
        print("FAIL: readDataFile does not use 'with open()' context manager")
        failed += 1

    # Test 2: Check that bare 'f.close' (without parens) is NOT present
    # Split lines and check for 'f.close' that isn't 'f.close()'
    lines = source.split('\n')
    has_bare_close = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if 'f.close' in stripped and 'f.close()' not in stripped:
            has_bare_close = True
            break

    if not has_bare_close:
        print("PASS: no bare 'f.close' (without parentheses) found")
        passed += 1
    else:
        print("FAIL: bare 'f.close' still present — file handle leak!")
        failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_tests()

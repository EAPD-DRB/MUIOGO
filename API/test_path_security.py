"""Quick smoke-test for the path_security module after PR review changes."""

import sys, os, tempfile, zipfile, shutil
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from Classes.Base.path_security import (
    validate_path_component,
    safe_resolve_path,
    safe_zip_extract,
    PathValidationError,
)

passed = 0
failed = 0

def ok(msg):
    global passed
    passed += 1
    print(f"  PASS: {msg}")

def fail(msg):
    global failed
    failed += 1
    print(f"  FAIL: {msg}")


print("=== 1. PathValidationError is a ValueError subclass ===")
if issubclass(PathValidationError, ValueError):
    ok("PathValidationError inherits ValueError")
else:
    fail("PathValidationError should inherit ValueError")


print("\n=== 2. Valid names accepted ===")
for name in ["MyCase", "DEMO CASE", "file.json", "case_123", "v5.0", "test(1)"]:
    try:
        validate_path_component(name)
        ok(f"accepted {name!r}")
    except PathValidationError:
        fail(f"rejected valid name {name!r}")


print("\n=== 3. Malicious inputs rejected as PathValidationError ===")
malicious = [
    "../../etc/passwd",
    "foo/bar",
    "foo\\bar",
    "file\x00.json",
    "",
    "..",
    ".",
    "..\\Windows\\System32",
]
for name in malicious:
    try:
        validate_path_component(name)
        fail(f"accepted malicious {name!r}")
    except PathValidationError:
        ok(f"rejected {name!r}")
    except Exception as e:
        fail(f"{name!r} raised {type(e).__name__} instead of PathValidationError")


print("\n=== 4. safe_resolve_path works ===")
base = Path("WebAPP", "DataStorage")
try:
    result = safe_resolve_path(base, "MyCase", "genData.json")
    ok(f"resolved -> {result}")
except Exception as e:
    fail(f"raised {e}")


print("\n=== 5. safe_resolve_path rejects traversal as PathValidationError ===")
try:
    safe_resolve_path(base, "..", "..", "etc", "passwd")
    fail("should have raised")
except PathValidationError:
    ok("traversal blocked")
except Exception as e:
    fail(f"raised {type(e).__name__} instead of PathValidationError")


print("\n=== 6. safe_zip_extract blocks Zip Slip (streaming) ===")
tmp = tempfile.mkdtemp()
try:
    malicious_zip = os.path.join(tmp, "evil.zip")
    safe_dir = os.path.join(tmp, "safe_extract")
    os.makedirs(safe_dir, exist_ok=True)

    with zipfile.ZipFile(malicious_zip, "w") as zf:
        zf.writestr("model/genData.json", "OK")
        zf.writestr("../../../evil.txt", "HACKED")
        zf.writestr("model/../../../escape.txt", "ESCAPED")

    with zipfile.ZipFile(malicious_zip, "r") as zf:
        safe_zip_extract(zf, Path(safe_dir))

    if os.path.exists(os.path.join(safe_dir, "model", "genData.json")):
        ok("normal file extracted")
    else:
        fail("normal file missing")

    if not os.path.exists(os.path.join(tmp, "evil.txt")):
        ok("evil.txt blocked")
    else:
        fail("evil.txt escaped!")

    if not os.path.exists(os.path.join(tmp, "escape.txt")):
        ok("escape.txt blocked")
    else:
        fail("escape.txt escaped!")
finally:
    shutil.rmtree(tmp)


print("\n" + "=" * 50)
print(f"Results: {passed} passed, {failed} failed")
if failed == 0:
    print("=== ALL SECURITY TESTS PASSED ===")
else:
    print("!!! SOME TESTS FAILED !!!")
    sys.exit(1)

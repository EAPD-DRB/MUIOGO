import shutil
import subprocess
import platform
import os
from pathlib import Path
from Classes.Base import Config


class StartupValidationError(Exception):
    pass


def _check_directory(path: Path, require_write=False):
    if not path.exists():
        return False, f"{path} does not exist"

    if require_write and not os.access(path, os.W_OK):
        return False, f"{path} is not writable"

    return True, "OK"


# def _check_binary(binary_name, package_name):
#     path = shutil.which(binary_name)

#     if not path:
#         system = platform.system()
#         install_hint = {
#             "Darwin": f"brew install {package_name}",
#             "Linux": f"sudo apt install {package_name}",
#             "Windows": f"choco install {package_name}",
#         }.get(system, f"Install {package_name} using your OS package manager.")

#         return False, f"Not found in PATH. Install using: {install_hint}"

#     if not os.access(path, os.X_OK):
#         return False, f"Found at {path} but not executable"

#     # Try to retrieve version
#     try:
#         result = subprocess.run(
#             [binary_name, "--version"],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True,
#             timeout=5,
#         )

#         version_output = result.stdout or result.stderr
#         version_line = version_output.splitlines()[0] if version_output else "version unknown"

#         return True, f"Found ({version_line})"

#     except Exception:
#         return True, "Found (version unknown)"

def _get_version_info(binary_path):
    try:
        result = subprocess.run(
            [binary_path, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )

        version_output = result.stdout or result.stderr
        version_line = version_output.splitlines()[0] if version_output else "version unknown"

        return True, f"Found ({version_line})"

    except Exception:
        return True, "Found (version unknown)"
    
def _check_binary(binary_name, package_name):
    system = platform.system()

    # Handle Windows .exe suffix
    binary_candidate = binary_name
    if system == "Windows" and not binary_name.endswith(".exe"):
        binary_candidate = f"{binary_name}.exe"

    # 1️⃣ Check local solver folder first
    local_solver_dir = Path(Config.SOLVERs_FOLDER)
    local_binary = local_solver_dir / binary_candidate

    if local_binary.exists() and os.access(local_binary, os.X_OK):
        return _get_version_info(str(local_binary))

    # 2️⃣ Fallback to system PATH
    system_path = shutil.which(binary_name)
    if system_path and os.access(system_path, os.X_OK):
        return _get_version_info(system_path)

    # 3️⃣ Not found → install hint
    install_hint = {
        "Darwin": f"brew install {package_name}",
        "Linux": f"sudo apt install {package_name}",
        "Windows": f"choco install {package_name}",
    }.get(system, f"Install {package_name} using your OS package manager.")

    return False, f"Not found locally or in PATH. Install using: {install_hint}"

def run_startup_checks():
    print("\n[Startup Validation] Running dependency checks...\n")

    results = []

    # DATA_STORAGE must exist and be writable
    data_storage = Path(Config.DATA_STORAGE)
    ok, message = _check_directory(data_storage, require_write=True)
    results.append(("DATA_STORAGE", ok, message))

    # WebAPP directory must exist (template/static root)
    webapp_dir = Path("WebAPP")
    ok, message = _check_directory(webapp_dir, require_write=False)
    results.append(("WebAPP directory", ok, message))

    # GLPK
    ok, message = _check_binary("glpsol", "glpk")
    results.append(("GLPK (glpsol)", ok, message))

    # CBC
    ok, message = _check_binary("cbc", "cbc")
    results.append(("CBC", ok, message))

    # Print summary
    print("Startup Validation Summary")
    print("-" * 45)

    failures = 0
    for name, ok, message in results:
        status = "OK" if ok else "FAIL"
        print(f"{name:<20} {status:<5} {message}")
        if not ok:
            failures += 1

    print("-" * 45)

    if failures:
        raise StartupValidationError(
            f"\nStartup validation failed. {failures} issue(s) detected.\n"
        )

    print("All checks passed.\n")
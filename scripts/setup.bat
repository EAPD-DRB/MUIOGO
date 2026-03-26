@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM MUIOGO Development Environment Setup (Windows)
REM
REM Usage:
REM   scripts\setup.bat                 &  full setup (installs demo data by default)
REM   scripts\setup.bat --no-demo-data  &  skip demo data
REM   scripts\setup.bat --check         &  verification only
REM ─────────────────────────────────────────────────────────────────────────────
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

if not "%CONDA_DEFAULT_ENV%"=="" (
    echo ERROR: Conda environment "%CONDA_DEFAULT_ENV%" is active.
    echo Run conda deactivate until no conda env is active, then re-run setup.
    exit /b 1
)

REM Try versioned executables first (3.12, 3.11, 3.10)
for %%V in (3.12 3.11 3.10) do (
    where python%%V >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON=python%%V"
        goto :run
    )
)

REM Try the Python Launcher (py.exe) with each supported version
where py >nul 2>&1
if %errorlevel% equ 0 (
    for %%V in (3.12 3.11 3.10) do (
        py -%%V -c "import sys" >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON=py -%%V"
            goto :run
        )
    )
)

REM Try plain `python` and let setup_dev.py validate the version
where python >nul 2>&1
if %errorlevel% equ 0 (
    python -c "import sys; v=sys.version_info; exit(0 if (3,10)<=v<(3,13) else 1)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON=python"
        goto :run
    )
)

echo ERROR: No supported Python runtime found (requires 3.10, 3.11, or 3.12^).
echo Install a supported version, then re-run setup.
echo   winget: winget install -e --id Python.Python.3.12
echo   Python.org: https://www.python.org/downloads/windows/
exit /b 1

:run
echo Using Python:
!PYTHON! --version
!PYTHON! "%SCRIPT_DIR%setup_dev.py" %*

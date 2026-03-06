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

where python3.11 >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON=python3.11"
    goto :run
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3.11 -c "import sys" >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON=py -3.11"
        goto :run
    )
)

echo ERROR: Python 3.11 was not found in PATH.
echo Install Python 3.11, then re-run setup.
echo   In PowerShell (winget): winget install -e --id Python.Python.3.11
echo   Python.org Windows installer: https://www.python.org/downloads/windows/
exit /b 1

:run
echo Using Python:
!PYTHON! --version
!PYTHON! "%SCRIPT_DIR%setup_dev.py" %*

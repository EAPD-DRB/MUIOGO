@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "DEFAULT_VENV_PY=%USERPROFILE%\.venvs\muiogo\Scripts\python.exe"
set "ACTIVE_VENV_PY=%VIRTUAL_ENV%\Scripts\python.exe"

if not "%CONDA_DEFAULT_ENV%"=="" (
    echo ERROR: Conda environment "%CONDA_DEFAULT_ENV%" is active.
    echo Run conda deactivate until no conda env is active, then re-run smoke.
    exit /b 1
)

if not "%MUIOGO_VENV_PYTHON%"=="" (
    if not exist "%MUIOGO_VENV_PYTHON%" (
        echo ERROR: MUIOGO_VENV_PYTHON is set but not executable: %MUIOGO_VENV_PYTHON%
        exit /b 1
    )
    set "PYTHON=%MUIOGO_VENV_PYTHON%"
    goto :run
)

if not "%VIRTUAL_ENV%"=="" if exist "%ACTIVE_VENV_PY%" (
    set "PYTHON=%ACTIVE_VENV_PY%"
    goto :run
)

if exist "%DEFAULT_VENV_PY%" (
    set "PYTHON=%DEFAULT_VENV_PY%"
    goto :run
)

echo ERROR: MUIOGO is not installed in a supported venv.
echo Run scripts\setup.bat first.
echo If you used a custom venv path, activate it before running smoke or set MUIOGO_VENV_PYTHON to that interpreter.
exit /b 1

:run
echo Using Python:
%PYTHON% --version
%PYTHON% -m unittest discover -s "%PROJECT_ROOT%\tests" -p "test_*smoke.py"

@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM MUIOGO Launcher (Windows)
REM
REM Starts the API with the setup venv and opens the browser automatically.
REM Usage:
REM   scripts\start.bat
REM ─────────────────────────────────────────────────────────────────────────────
setlocal

if not "%CONDA_DEFAULT_ENV%"=="" (
    echo ERROR: Conda environment "%CONDA_DEFAULT_ENV%" is active.
    echo Run conda deactivate until no conda env is active, then launch again.
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "VENV_DIR=%MUIOGO_VENV_DIR%"
if "%VENV_DIR%"=="" set "VENV_DIR=%USERPROFILE%\.venvs\muiogo"
set "PYTHON=%VENV_DIR%\Scripts\python.exe"
set "HOST=127.0.0.1"
if "%PORT%"=="" (set "PORT=5002")
set "URL=http://%HOST%:%PORT%/"

if not exist "%PYTHON%" (
    echo ERROR: Venv Python not found at: %PYTHON%
    echo Run setup first:
    echo   scripts\setup.bat
    exit /b 1
)

echo Starting MUIOGO on %URL%
start "" "%URL%"
pushd "%PROJECT_ROOT%"
"%PYTHON%" API\app.py
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%

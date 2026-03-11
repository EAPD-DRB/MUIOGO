@ECHO OFF
REM ============================================================================
REM MUIOGO - Uninstall / Reset Script (Windows)
REM
REM Reverses the local environment changes created by scripts\setup.bat
REM so that running setup again behaves like a first-time install.
REM
REM Usage:  scripts\uninstall.bat
REM ============================================================================
setlocal EnableDelayedExpansion

REM -- Resolve repo root (this script lives in <repo>\scripts\) ----------------
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "REPO_ROOT=%CD%"
popd

REM -- Logging helpers ---------------------------------------------------------
goto :start

:info
echo [INFO]    %~1
goto :eof

:warn
echo [WARN]    %~1
goto :eof

:success
echo [OK]      %~1
goto :eof

:error
echo [ERROR]   %~1
goto :eof

REM ============================================================================
:start
REM ============================================================================

echo.
call :info "============================================"
call :info " MUIOGO Uninstall / Reset"
call :info "============================================"
echo.

REM -- Track what we will remove -----------------------------------------------
set "ITEM_COUNT=0"
set "HAS_ITEMS=0"

REM ============================================================================
REM  1. Detect state to remove
REM ============================================================================

REM -- 1a. Virtual environment -------------------------------------------------
if defined MUIOGO_VENV_DIR (
    set "VENV_DIR=%MUIOGO_VENV_DIR%"
) else (
    set "VENV_DIR=%USERPROFILE%\.venvs\muiogo"
)

set "REMOVE_VENV=0"
if exist "%VENV_DIR%\" (
    set /a ITEM_COUNT+=1
    set "ITEM_!ITEM_COUNT!=Virtual environment: %VENV_DIR%"
    set "REMOVE_VENV=1"
    set "HAS_ITEMS=1"
)

REM -- 1b. .env entries --------------------------------------------------------
set "ENV_FILE=%REPO_ROOT%\.env"
set "HAS_SETUP_ENTRIES=0"

if exist "%ENV_FILE%" (
    findstr /C:"# MUIOGO-setup" "%ENV_FILE%" >NUL 2>&1
    if not errorlevel 1 (
        set "HAS_SETUP_ENTRIES=1"
        set /a ITEM_COUNT+=1
        set "ITEM_!ITEM_COUNT!=.env setup entries in: %ENV_FILE%"
        set "HAS_ITEMS=1"
    )
)

REM -- 1c. Demo data -----------------------------------------------------------
set "DEMO_MARKER=%REPO_ROOT%\.muiogo_demo_installed"
set "DEMO_DIR=%REPO_ROOT%\WebAPP\DataStorage\CLEWs Demo"
set "REMOVE_DEMO=0"

if exist "%DEMO_MARKER%" (
    set "REMOVE_DEMO=1"
    set /a ITEM_COUNT+=1
    set "ITEM_!ITEM_COUNT!=Demo data directory: %DEMO_DIR%"
    set /a ITEM_COUNT+=1
    set "ITEM_!ITEM_COUNT!=Demo marker file: %DEMO_MARKER%"
    set "HAS_ITEMS=1"
)

REM -- 1d. Solver fallback installs --------------------------------------------
set "GLPK_FALLBACK=%LOCALAPPDATA%\glpk"
set "CBC_FALLBACK=%LOCALAPPDATA%\cbc"
set "REMOVE_GLPK_FALLBACK=0"
set "REMOVE_CBC_FALLBACK=0"

if exist "%GLPK_FALLBACK%\" (
    set "REMOVE_GLPK_FALLBACK=1"
    set /a ITEM_COUNT+=1
    set "ITEM_!ITEM_COUNT!=Solver fallback: %GLPK_FALLBACK%"
    set "HAS_ITEMS=1"
)

if exist "%CBC_FALLBACK%\" (
    set "REMOVE_CBC_FALLBACK=1"
    set /a ITEM_COUNT+=1
    set "ITEM_!ITEM_COUNT!=Solver fallback: %CBC_FALLBACK%"
    set "HAS_ITEMS=1"
)

REM -- 1e. Windows environment variables ---------------------------------------
set "REMOVE_GLPK_ENV=0"
set "REMOVE_CBC_ENV=0"

REM Check user-level env vars
REG QUERY "HKCU\Environment" /v GLPK_PATH >NUL 2>&1
if not errorlevel 1 (
    set "REMOVE_GLPK_ENV=1"
    set /a ITEM_COUNT+=1
    set "ITEM_!ITEM_COUNT!=User env var: GLPK_PATH"
    set "HAS_ITEMS=1"
)

REG QUERY "HKCU\Environment" /v CBC_PATH >NUL 2>&1
if not errorlevel 1 (
    set "REMOVE_CBC_ENV=1"
    set /a ITEM_COUNT+=1
    set "ITEM_!ITEM_COUNT!=User env var: CBC_PATH"
    set "HAS_ITEMS=1"
)

REM -- 1f. Chocolatey solvers (advisory only) ----------------------------------
set "CHOCO_GLPK=0"
set "CHOCO_CBC=0"

where choco >NUL 2>&1
if not errorlevel 1 (
    choco list --local-only glpk >NUL 2>&1
    if not errorlevel 1 (
        set "CHOCO_GLPK=1"
    )
    choco list --local-only cbc >NUL 2>&1
    if not errorlevel 1 (
        set "CHOCO_CBC=1"
    )
)

REM ============================================================================
REM  2. Show summary
REM ============================================================================

if "%HAS_ITEMS%"=="0" (
    if "%CHOCO_GLPK%"=="0" (
        if "%CHOCO_CBC%"=="0" (
            call :success "Nothing to uninstall - your environment is already clean."
            goto :done_exit
        )
    )
)

if "%HAS_ITEMS%"=="1" (
    call :info "The following items will be removed:"
    echo.
    for /L %%i in (1,1,%ITEM_COUNT%) do (
        echo   %%i. !ITEM_%%i!
    )
    echo.
)

if "%CHOCO_GLPK%"=="1" (
    call :warn "GLPK appears to have been installed via Chocolatey."
    call :warn "It may be used outside MUIOGO, so it is NOT auto-removed."
    echo   To remove manually: choco uninstall glpk
    echo.
)

if "%CHOCO_CBC%"=="1" (
    call :warn "CBC appears to have been installed via Chocolatey."
    call :warn "It may be used outside MUIOGO, so it is NOT auto-removed."
    echo   To remove manually: choco uninstall cbc
    echo.
)

REM ============================================================================
REM  3. Confirm before proceeding
REM ============================================================================
if "%HAS_ITEMS%"=="1" (
    set /p CONFIRM="Continue with removal? (y/N) "
    if /i not "!CONFIRM!"=="y" (
        if /i not "!CONFIRM!"=="yes" (
            call :warn "Aborted. No changes were made."
            goto :done_exit
        )
    )
    echo.
)

REM ============================================================================
REM  4. Execute removal
REM ============================================================================

REM -- 4a. Remove virtual environment ------------------------------------------
if "%REMOVE_VENV%"=="1" (
    call :info "Removing virtual environment: %VENV_DIR%"
    if exist "%VENV_DIR%\" (
        rmdir /s /q "%VENV_DIR%"
        call :success "Virtual environment removed."
    )
)

REM -- 4b. Clean .env ----------------------------------------------------------
if "%HAS_SETUP_ENTRIES%"=="1" (
    if exist "%ENV_FILE%" (
        call :info "Cleaning setup entries from .env"

        REM Filter out lines containing the sentinel
        set "TEMP_ENV=%TEMP%\muiogo_env_clean.tmp"
        findstr /v /C:"# MUIOGO-setup" "%ENV_FILE%" > "!TEMP_ENV!" 2>NUL

        REM Check if anything remains
        set "FILE_HAS_CONTENT=0"
        for %%A in ("!TEMP_ENV!") do (
            if %%~zA GTR 0 (
                REM Check for non-blank content
                findstr /r /v "^$" "!TEMP_ENV!" >NUL 2>&1
                if not errorlevel 1 (
                    set "FILE_HAS_CONTENT=1"
                )
            )
        )

        if "!FILE_HAS_CONTENT!"=="0" (
            del /f /q "%ENV_FILE%"
            call :success ".env file removed (it contained only setup entries)."
        ) else (
            copy /y "!TEMP_ENV!" "%ENV_FILE%" >NUL
            call :success "Setup entries removed from .env (user entries preserved)."
        )

        del /f /q "!TEMP_ENV!" 2>NUL
    )
)

REM -- 4c. Remove demo data ----------------------------------------------------
if "%REMOVE_DEMO%"=="1" (
    if exist "%DEMO_DIR%\" (
        call :info "Removing demo data directory: %DEMO_DIR%"
        rmdir /s /q "%DEMO_DIR%"
        call :success "Demo data removed."
    ) else (
        call :warn "Demo marker exists but demo directory not found - skipping data removal."
    )
    if exist "%DEMO_MARKER%" (
        call :info "Removing demo marker file."
        del /f /q "%DEMO_MARKER%"
        call :success "Demo marker removed."
    )
)

REM -- 4d. Remove solver fallback installs -------------------------------------
if "%REMOVE_GLPK_FALLBACK%"=="1" (
    call :info "Removing solver fallback: %GLPK_FALLBACK%"
    if exist "%GLPK_FALLBACK%\" (
        rmdir /s /q "%GLPK_FALLBACK%"
        call :success "GLPK fallback removed."
    )
)

if "%REMOVE_CBC_FALLBACK%"=="1" (
    call :info "Removing solver fallback: %CBC_FALLBACK%"
    if exist "%CBC_FALLBACK%\" (
        rmdir /s /q "%CBC_FALLBACK%"
        call :success "CBC fallback removed."
    )
)

REM -- 4e. Remove Windows environment variables --------------------------------
if "%REMOVE_GLPK_ENV%"=="1" (
    call :info "Removing user environment variable: GLPK_PATH"
    REG DELETE "HKCU\Environment" /v GLPK_PATH /f >NUL 2>&1
    call :success "GLPK_PATH removed."
)

if "%REMOVE_CBC_ENV%"=="1" (
    call :info "Removing user environment variable: CBC_PATH"
    REG DELETE "HKCU\Environment" /v CBC_PATH /f >NUL 2>&1
    call :success "CBC_PATH removed."
)

REM -- 4f. Clean solver directories from user PATH ----------------------------
REM Read current user PATH
set "CLEANED_PATH="
set "PATH_CHANGED=0"

for /f "tokens=2,*" %%A in ('REG QUERY "HKCU\Environment" /v Path 2^>NUL') do (
    set "USER_PATH=%%B"
)

if defined USER_PATH (
    REM Split PATH by semicolons and rebuild without solver dirs
    set "REMAINING="
    for %%P in ("!USER_PATH:;=" "!") do (
        set "SEGMENT=%%~P"
        set "SKIP=0"

        REM Check if this segment points to a setup-installed solver
        if defined GLPK_FALLBACK (
            echo "!SEGMENT!" | findstr /i /C:"%GLPK_FALLBACK%" >NUL 2>&1
            if not errorlevel 1 set "SKIP=1"
        )
        if defined CBC_FALLBACK (
            echo "!SEGMENT!" | findstr /i /C:"%CBC_FALLBACK%" >NUL 2>&1
            if not errorlevel 1 set "SKIP=1"
        )

        if "!SKIP!"=="0" (
            if defined REMAINING (
                set "REMAINING=!REMAINING!;!SEGMENT!"
            ) else (
                set "REMAINING=!SEGMENT!"
            )
        ) else (
            set "PATH_CHANGED=1"
        )
    )

    if "!PATH_CHANGED!"=="1" (
        call :info "Cleaning solver directories from user PATH"
        REG ADD "HKCU\Environment" /v Path /t REG_EXPAND_SZ /d "!REMAINING!" /f >NUL 2>&1
        call :success "User PATH cleaned."
    )
)

REM -- 4g. Offer Chocolatey solver removal (advisory) -------------------------
if "%CHOCO_GLPK%"=="1" (
    set /p CHOCO_GLPK_CONFIRM="GLPK appears installed via Chocolatey. Remove it? (y/N) "
    if /i "!CHOCO_GLPK_CONFIRM!"=="y" (
        call :info "Running: choco uninstall glpk -y"
        choco uninstall glpk -y
        if not errorlevel 1 (
            call :success "GLPK removed via Chocolatey."
        ) else (
            call :warn "Failed to remove GLPK. You can run manually: choco uninstall glpk"
        )
    ) else (
        call :info "Skipped GLPK. To remove manually: choco uninstall glpk"
    )
)

if "%CHOCO_CBC%"=="1" (
    set /p CHOCO_CBC_CONFIRM="CBC appears installed via Chocolatey. Remove it? (y/N) "
    if /i "!CHOCO_CBC_CONFIRM!"=="y" (
        call :info "Running: choco uninstall cbc -y"
        choco uninstall cbc -y
        if not errorlevel 1 (
            call :success "CBC removed via Chocolatey."
        ) else (
            call :warn "Failed to remove CBC. You can run manually: choco uninstall cbc"
        )
    ) else (
        call :info "Skipped CBC. To remove manually: choco uninstall cbc"
    )
)

REM ============================================================================
REM  5. Done
REM ============================================================================
echo.
call :success "============================================"
call :success " MUIOGO uninstall complete."
call :success " You can now run setup again for a fresh install."
call :success "============================================"
echo.

:done_exit
endlocal
exit /b 0

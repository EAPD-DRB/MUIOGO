<#
.SYNOPSIS
    MUIOGO installer for Windows (uv-based).

.DESCRIPTION
    Takes a user from a clean machine to a running MUIOGO environment:
      1. Check git is installed
      2. Install uv (if not present)
      3. Clone MUIOGO
      4. uv sync (installs Python + all dependencies)
      5. Platform setup: solvers, demo data, secret key, verification
      6. Start the app (optional, user prompted)

.PARAMETER Dest
    Parent directory where the repo is cloned. Default: current directory.
    The clone always lands in <Dest>\MUIOGO.

.PARAMETER Branch
    Clone a non-default branch. Useful for testing forks/PRs.

.PARAMETER Yes
    Auto-confirm every prompt (non-interactive).

.PARAMETER NoDemoData
    Skip demo data installation.

.PARAMETER SkipUvInstall
    Skip uv installation; assume uv is already on PATH.

.PARAMETER Log
    Write an install log file.

.PARAMETER RepoUrl
    Override the repository URL to clone from. Default: https://github.com/EAPD-DRB/MUIOGO.git
    Useful for testing a fork before the PR is merged.

.EXAMPLE
    irm https://raw.githubusercontent.com/EAPD-DRB/MUIOGO/main/scripts/install.ps1 | iex
    One-liner install with all defaults.

.EXAMPLE
    .\scripts\install.ps1 -Dest C:\work -Yes
    Unattended install into C:\work\MUIOGO.

.EXAMPLE
    .\scripts\install.ps1 -RepoUrl https://github.com/YOUR_FORK/MUIOGO.git -Branch YOUR_BRANCH
    Test a fork branch before the PR is merged.
#>

[CmdletBinding()]
param(
    [string]$Dest = "",
    [string]$Branch = "",
    [string]$RepoUrl = "",
    [switch]$Yes,
    [switch]$NoDemoData,
    [switch]$SkipUvInstall,
    [switch]$Log
)

$ErrorActionPreference = 'Stop'
$ScriptDir = (Get-Location).Path

if ($RepoUrl -eq "") { $RepoUrl = "https://github.com/EAPD-DRB/MUIOGO.git" }
$RepoName = "MUIOGO"

# -- Colors --------------------------------------------------------------------
$UseAnsi = $Host.UI.SupportsVirtualTerminal -or ($env:WT_SESSION -ne $null)
if ($UseAnsi) {
    $E = [char]27
    $BOLD = "$E[1m"; $DIM = "$E[2m"
    $RED = "$E[91m"; $GREEN = "$E[92m"; $YELLOW = "$E[93m"; $RESET = "$E[0m"
} else {
    $BOLD = ""; $DIM = ""; $RED = ""; $GREEN = ""; $YELLOW = ""; $RESET = ""
}

# -- Logging -------------------------------------------------------------------
$Ts = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $ScriptDir ".install-$Ts.log"
$WriteLog = [bool]$Log
if ($WriteLog) {
    try { Start-Transcript -Path $LogFile -Append | Out-Null }
    catch {
        Write-Host "WARN: could not start transcript at $LogFile : $($_.Exception.Message)"
        $WriteLog = $false
    }
}
function Stop-TranscriptIfActive {
    if ($script:WriteLog) { try { Stop-Transcript | Out-Null } catch {} }
}

# -- Helpers -------------------------------------------------------------------
function Write-Hr      { Write-Host "--------------------------------------------------------------" }
function Write-HrThick { Write-Host "==============================================================" }

function Write-Pass($label, $detail = "") {
    $suffix = if ($detail) { "  $DIM($detail)$RESET" } else { "" }
    Write-Host "  $GREEN[PASS]$RESET $label$suffix"
}
function Write-Fail($label, $detail = "") {
    $suffix = if ($detail) { "  $DIM($detail)$RESET" } else { "" }
    Write-Host "  $RED[FAIL]$RESET $label$suffix"
}
function Write-Warn2($label, $detail = "") {
    $suffix = if ($detail) { "  $DIM($detail)$RESET" } else { "" }
    Write-Host "  $YELLOW[WARN]$RESET $label$suffix"
}
function Write-Skip($label, $detail = "") {
    $suffix = if ($detail) { "  $DIM($detail)$RESET" } else { "" }
    Write-Host "  $YELLOW[SKIP]$RESET $label$suffix"
}
function Write-Cmd($cmd) { Write-Host "  $DIM`$ $cmd$RESET" }

$TotalSteps = 5
function Step-Banner($n, $title) {
    Write-Host ""
    Write-Hr
    Write-Host "  ${BOLD}Step $n of ${TotalSteps}: $title${RESET}"
    Write-Hr
}

function Test-Interactive {
    try { return -not [Console]::IsInputRedirected }
    catch { return [Environment]::UserInteractive }
}

function Prompt-YN($prompt, $default = 'y') {
    $opts = '[Y/N]'
    if ($Yes) {
        Write-Host "$prompt $opts ${DIM}(auto: yes)${RESET}"
        return $true
    }
    if (-not (Test-Interactive)) {
        Write-Host "${RED}ERROR:${RESET} non-interactive session and -Yes not given."
        return $false
    }
    while ($true) {
        $ans = Read-Host "$prompt $opts"
        if ([string]::IsNullOrWhiteSpace($ans)) { $ans = $default }
        switch -Regex ($ans) {
            '^(y|yes)$'  { return $true }
            '^(n|no)$'   { return $false }
            default { Write-Host "  Please answer Y or N." }
        }
    }
}

# -- Result tracking -----------------------------------------------------------
$StepResults = New-Object System.Collections.Generic.List[object]
function Record-Step($name, $state, $detail = "") {
    $script:StepResults.Add([pscustomobject]@{ Name=$name; State=$state; Detail=$detail })
}

# -- Pre-flight ----------------------------------------------------------------
if ($env:CONDA_DEFAULT_ENV) {
    Write-Host "${RED}ERROR:${RESET} conda env '$($env:CONDA_DEFAULT_ENV)' is active. Run 'conda deactivate' first."
    Stop-TranscriptIfActive; exit 1
}
if ($env:VIRTUAL_ENV) {
    Write-Host "${RED}ERROR:${RESET} virtualenv '$($env:VIRTUAL_ENV)' is active. Run 'deactivate' first."
    Stop-TranscriptIfActive; exit 1
}

# -- Detect existing uv --------------------------------------------------------
$UvBin = $null
function Detect-Uv {
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) { $script:UvBin = $cmd.Source; return $true }
    $candidates = @(
        "$env:USERPROFILE\.local\bin\uv.exe",
        "$env:USERPROFILE\.cargo\bin\uv.exe",
        "$env:LOCALAPPDATA\Programs\uv\uv.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $script:UvBin = $c; return $true }
    }
    return $false
}
[void](Detect-Uv)
$UvPresent = [bool]$UvBin

# -- Pick destination ----------------------------------------------------------
if (-not $Dest) {
    if (-not (Test-Interactive)) {
        $Dest = "."
    } else {
        Write-Host ""
        Write-Host "  Where would you like to install MUIOGO?"
        Write-Host "  Enter the PARENT directory; MUIOGO will be cloned as a subfolder inside."
        Write-Host "  Default: current directory ($(Get-Location))"
        $entered = Read-Host "  Parent directory [.]"
        if ([string]::IsNullOrWhiteSpace($entered)) { $Dest = "." } else { $Dest = $entered }
    }
}

$Dest = [Environment]::ExpandEnvironmentVariables($Dest)
if ($Dest.StartsWith("~")) {
    $Dest = Join-Path $env:USERPROFILE $Dest.Substring(1).TrimStart('\','/')
}

if (-not (Test-Path $Dest)) {
    Write-Host "${RED}ERROR:${RESET} parent directory does not exist: $Dest"
    Write-Host "Create it first or pick a different -Dest."
    Stop-TranscriptIfActive; exit 1
}
$ParentAbs = (Resolve-Path $Dest).Path
$DestAbs   = Join-Path $ParentAbs $RepoName

# -- Banner --------------------------------------------------------------------
Write-Host ""
Write-HrThick
Write-Host "  ${BOLD}MUIOGO Installer (uv-based)${RESET}"
Write-HrThick
Write-Host ("  Platform    : Windows {0}" -f $env:PROCESSOR_ARCHITECTURE)
Write-Host ("  Destination : {0}" -f $DestAbs)
if ($Branch) { Write-Host ("  Branch      : {0}" -f $Branch) }
if ($UvPresent) {
    Write-Host ("  uv          : {0} {1}detected{2}" -f $UvBin, $GREEN, $RESET)
} else {
    Write-Host ("  uv          : {0}will install{1} (~5MB, official installer)" -f $YELLOW, $RESET)
}
if ($WriteLog) { Write-Host ("  Log file    : {0}" -f $LogFile) }
Write-Host ""
Write-Host "  ${BOLD}Plan ($TotalSteps steps):${RESET}"
Write-Host "    1. Check git"
if ($UvPresent -or $SkipUvInstall) {
    Write-Host "    2. Install uv                      ${DIM}skipped (already present)${RESET}"
} else {
    Write-Host "    2. Install uv                      ${DIM}~5MB, seconds${RESET}"
}
Write-Host ("    3. Clone MUIOGO                    ${DIM}depends on network${RESET}")
Write-Host "    4. uv sync (Python + deps)         ${DIM}~30s${RESET}"
Write-Host "    5. Platform setup (solvers, demo data, secret key, verification)"
Write-Host ""

if (-not (Prompt-YN "Proceed with installation?" 'y')) {
    Write-Host "${YELLOW}Aborted by user.${RESET}"
    Stop-TranscriptIfActive; exit 0
}

$StartTime = Get-Date

# -- Step 1: Check git ---------------------------------------------------------
Step-Banner 1 "Check git"
$GitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $GitCmd) {
    Write-Fail "git is not installed or not on PATH"
    Write-Host ""
    Write-Host "  Install git for Windows, then re-run this installer:"
    Write-Host "    winget install -e --id Git.Git"
    Write-Host "    https://git-scm.com/download/win"
    Record-Step "git" "FAIL" "not installed"
    Stop-TranscriptIfActive; exit 1
}
$GitBin = $GitCmd.Source
$gitVer = ""
try { $gitVer = (& $GitBin --version 2>$null).Trim() } catch {}
Write-Pass "git" $gitVer
Record-Step "git" "PASS" $gitVer

# -- Step 2: Install uv --------------------------------------------------------
Step-Banner 2 "Install uv"
if ($UvPresent) {
    $uvVer = ""
    try { $uvVer = ((& $UvBin --version 2>$null) | Select-Object -First 1).Trim() } catch {}
    Write-Pass "uv already present" "$UvBin ($uvVer)"
    Record-Step "uv" "SKIP" "already present"
} elseif ($SkipUvInstall) {
    Write-Fail "-SkipUvInstall given but uv not found"
    Record-Step "uv" "FAIL" "no uv and -SkipUvInstall"
    Stop-TranscriptIfActive; exit 1
} else {
    Write-Host "  Installing uv via the official installer (no admin required)..."
    Write-Cmd "irm https://astral.sh/uv/install.ps1 | iex"
    $ProgressPreference = 'SilentlyContinue'
    $uvInstallCmd = "[Net.ServicePointManager]::SecurityProtocol = 'Tls12'; iwr https://astral.sh/uv/install.ps1 -UseBasicParsing | iex"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -Command $uvInstallCmd
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "uv install failed (exit $LASTEXITCODE)"
        Record-Step "uv" "FAIL" "install failed"
        Stop-TranscriptIfActive; exit 1
    }
    [void](Detect-Uv)
    if (-not $UvBin) {
        $candidate = "$env:USERPROFILE\.local\bin\uv.exe"
        if (Test-Path $candidate) { $UvBin = $candidate }
    }
    if (-not $UvBin -or -not (Test-Path $UvBin)) {
        Write-Fail "uv installed but binary not found; open a new terminal and re-run"
        Record-Step "uv" "FAIL" "binary not found post-install"
        Stop-TranscriptIfActive; exit 1
    }
    $uvVer = ""
    try { $uvVer = ((& $UvBin --version 2>$null) | Select-Object -First 1).Trim() } catch {}
    Write-Pass "uv installed" "$UvBin ($uvVer)"
    Record-Step "uv" "PASS" $UvBin
}

# -- Step 3: Clone MUIOGO ------------------------------------------------------
Step-Banner 3 "Clone MUIOGO"

function Normalize-RemoteUrl($u) { return ($u -replace '\.git/?$', '').ToLower() }

$DestHasRepo = $false
if (Test-Path $DestAbs) {
    if (Test-Path (Join-Path $DestAbs ".git")) {
        $existingUrl = ""
        try { $existingUrl = (& $GitBin -C $DestAbs config --get remote.origin.url 2>$null).Trim() } catch {}
        if ((Normalize-RemoteUrl $existingUrl) -eq (Normalize-RemoteUrl $RepoUrl)) {
            $DestHasRepo = $true
        } else {
            Write-Fail "Destination exists but points to a different remote" $existingUrl
            Write-Host "  Remove $DestAbs or pick a different -Dest."
            Record-Step "Clone" "FAIL" "wrong remote"
            Stop-TranscriptIfActive; exit 1
        }
    } else {
        $isEmpty = (Get-ChildItem -Force $DestAbs -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0
        if (-not $isEmpty) {
            Write-Fail "Destination exists and is not empty" $DestAbs
            Write-Host "  Remove $DestAbs or pick a different -Dest."
            Record-Step "Clone" "FAIL" "destination not empty"
            Stop-TranscriptIfActive; exit 1
        }
    }
}

if ($DestHasRepo) {
    $branch = "?"
    try { $branch = (& $GitBin -C $DestAbs rev-parse --abbrev-ref HEAD 2>$null).Trim() } catch {}
    Write-Host ("  Existing MUIOGO clone found at {0} (branch: {1})." -f $DestAbs, $branch)

    # -- Version check against what `git pull` would bring in ------------------
    # The clone's own tracked branch (the branch and repository it was installed
    # from); EAPD-DRB/MUIOGO:main only when it tracks nothing, e.g. a detached HEAD.
    $localSha    = ""
    $remoteSha   = ""
    $behind      = "?"
    $ahead       = "?"
    $upstream    = ""
    $compareRef  = "FETCH_HEAD"
    $latestLabel = "EAPD-DRB/MUIOGO:main"
    try { $localSha = (& $GitBin -C $DestAbs rev-parse --short HEAD 2>$null).Trim() } catch {}
    try { $upstream = (& $GitBin -C $DestAbs rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null).Trim() } catch {}
    if ($LASTEXITCODE -eq 0 -and $upstream) {
        try { & $GitBin -C $DestAbs fetch --quiet 2>$null } catch {}
        $compareRef  = "@{u}"
        $latestLabel = $upstream
    } else {
        try { & $GitBin -C $DestAbs fetch https://github.com/EAPD-DRB/MUIOGO.git main --quiet 2>$null } catch {}
    }
    try { $remoteSha = (& $GitBin -C $DestAbs rev-parse --short $compareRef 2>$null).Trim() } catch {}
    try { $behind    = (& $GitBin -C $DestAbs rev-list --count "HEAD..$compareRef" 2>$null).Trim() } catch {}
    try { $ahead     = (& $GitBin -C $DestAbs rev-list --count "$compareRef..HEAD" 2>$null).Trim() } catch {}

    Write-Host ("  Local:   {0}  ({1})" -f $localSha, $branch)
    Write-Host ("  Latest:  {0}  ({1})" -f $remoteSha, $latestLabel)
    Write-Host ""

    if ($behind -eq "?") {
        Write-Warn2 "Could not check for updates - continuing with current version"
        Record-Step "Clone" "WARN" "could not reach remote"
    } elseif ($behind -eq "0") {
        Write-Pass "Up to date  --  0 behind, $ahead ahead"
        Record-Step "Clone" "PASS" "up to date ($branch)"
    } else {
        Write-Warn2 "$behind behind, $ahead ahead  --  update now?"
        if (Prompt-YN "Update now?" 'y') {
            $pullArgs = @("pull", "--ff-only")
            if ($compareRef -eq "FETCH_HEAD") { $pullArgs += @("https://github.com/EAPD-DRB/MUIOGO.git", "main") }
            & $GitBin -C $DestAbs @pullArgs
            if ($LASTEXITCODE -eq 0) {
                $newSha = ""
                try { $newSha = (& $GitBin -C $DestAbs rev-parse --short HEAD 2>$null).Trim() } catch {}
                Write-Pass "Updated to $newSha"
                Record-Step "Clone" "PASS" "updated (was $behind behind)"
            } else {
                Write-Warn2 "git pull failed; continuing with existing state"
                Record-Step "Clone" "WARN" "pull failed; existing state used"
            }
        } else {
            Write-Skip "Update skipped" "continuing with $localSha"
            Record-Step "Clone" "SKIP" "user declined update"
        }
    }
} else {
    $cloneArgs = @("clone")
    if ($Branch) { $cloneArgs += @("--branch", $Branch) }
    $cloneArgs += @($RepoUrl, $DestAbs)

    Write-Host ("  Cloning MUIOGO into {0}..." -f $DestAbs)
    Write-Cmd ("git {0}" -f ($cloneArgs -join ' '))
    & $GitBin @cloneArgs

    if ($LASTEXITCODE -ne 0) {
        Write-Fail "git clone failed"
        Write-Host "  Re-run the installer to try again."
        Record-Step "Clone" "FAIL" "git clone failed"
        Stop-TranscriptIfActive; exit 1
    }

    $branch = "?"
    try { $branch = (& $GitBin -C $DestAbs rev-parse --abbrev-ref HEAD 2>$null).Trim() } catch {}
    Write-Pass "Cloned MUIOGO" "$DestAbs (branch: $branch)"
    Record-Step "Clone" "PASS" $branch
}

# -- Step 4: uv sync -----------------------------------------------------------
Step-Banner 4 "Install dependencies (uv sync)"
Write-Host ("  Installing Python + all dependencies into {0}\.venv" -f $DestAbs)
Write-Cmd "uv sync"
Push-Location $DestAbs
try {
    & $UvBin sync
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "uv sync failed"
        Record-Step "uv sync" "FAIL" "exit $LASTEXITCODE"
        Stop-TranscriptIfActive; exit 1
    }
    Write-Pass "Dependencies installed" ".venv"
    Record-Step "uv sync" "PASS" ".venv"
} finally {
    Pop-Location
}

# -- Step 5: Platform setup ----------------------------------------------------
Step-Banner 5 "Platform setup (solvers, demo data, secret key, verification)"
$VenvPython = Join-Path $DestAbs ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Fail "venv Python not found" $VenvPython
    Record-Step "Platform setup" "FAIL" "no venv python"
    Stop-TranscriptIfActive; exit 1
}

$SetupArgs = @("scripts\setup_dev.py", "--platform-only", "--venv-dir", ".venv")
if ($NoDemoData) { $SetupArgs += "--no-demo-data" }
if ($Yes) { $SetupArgs += "--yes" }

Write-Cmd ("python {0}" -f ($SetupArgs -join ' '))
Push-Location $DestAbs
try {
    & $VenvPython @SetupArgs
    if ($LASTEXITCODE -ne 0) {
        # Don't exit here: record the failure and fall through to the summary
        # (matches install.sh) so the full result table prints before exiting.
        Write-Fail "Platform setup reported failures -- review output above"
        Record-Step "Platform setup" "FAIL" "setup_dev.py exited $LASTEXITCODE"
    } else {
        Record-Step "Platform setup" "PASS" "solvers, demo data, secret key, verification"
    }
} finally {
    Pop-Location
}

# -- Summary -------------------------------------------------------------------
$Elapsed    = (Get-Date) - $StartTime
$ElapsedMin = [int]$Elapsed.TotalMinutes
$ElapsedSec = [int]($Elapsed.TotalSeconds - ($ElapsedMin * 60))

Write-Host ""
Write-HrThick
Write-Host "  ${BOLD}Installation Summary${RESET}"
Write-HrThick

$AllOk = $true
foreach ($r in $StepResults) {
    switch ($r.State) {
        "PASS" { Write-Pass  $r.Name $r.Detail }
        "SKIP" { Write-Skip  $r.Name $r.Detail }
        "WARN" { Write-Warn2 $r.Name $r.Detail }
        "FAIL" { Write-Fail  $r.Name $r.Detail; $AllOk = $false }
        default { Write-Warn2 $r.Name "unknown state" }
    }
}
Write-Host ""
Write-Host ("  Elapsed  : {0}m {1}s" -f $ElapsedMin, $ElapsedSec)
Write-Host ("  Location : {0}" -f $DestAbs)
if ($WriteLog) { Write-Host ("  Log      : {0}" -f $LogFile) }
Write-Host ""

if ($AllOk) {
    Write-Host "  ${GREEN}${BOLD}MUIOGO is installed and ready.${RESET}"
    Write-Host ""
    if (Prompt-YN "Start MUIOGO now?" 'y') {
        $Port = if ($env:PORT) { $env:PORT } else { "5002" }
        $Url  = "http://127.0.0.1:${Port}/"
        Write-Host ("  Opening browser at {0}" -f $Url)
        Write-Host "  Press Ctrl+C to stop the app."
        Start-Process $Url
        Push-Location $DestAbs
        try {
            & $VenvPython "API\app.py"
        } finally {
            Pop-Location
        }
    }

    Stop-TranscriptIfActive
    exit 0
} else {
    Write-Host "  ${RED}${BOLD}One or more steps failed -- review the output above.${RESET}"
    if ($WriteLog) { Write-Host "  Full log: $LogFile" }
    Stop-TranscriptIfActive
    exit 1
}

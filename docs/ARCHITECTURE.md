# MUIOGO Architecture (Current State)

## System overview

`MUIOGO` currently runs as a Flask application that serves:

- backend API routes from `API/`
- static frontend assets from `WebAPP/`
- CLEWS model data and run artifacts from `WebAPP/DataStorage/`
- OG-Core calibration, case, parameter, and run state from directories outside
  the repository

CLEWS solver execution uses backend subprocess calls to GLPK or CBC. OG-Core
runs use a separate worker process started with the selected country
calibration's Python environment.

## Major components

### Backend

- Entry point: `API/app.py`
- API routes:
  - `API/Routes/Case/`
  - `API/Routes/DataFile/`
  - `API/Routes/Upload/`
  - `API/Routes/Case/SyncS3Route.py`
  - `API/Routes/OGCore/`
- OG-Core services:
  - `API/Classes/OGCore/OGCoreCase.py` owns case, run, and parameter storage.
  - `API/Classes/OGCore/OGSchema.py` projects installed calibration metadata for
    the parameter form without importing OG-Core into Flask.
  - `API/Classes/OGCore/RunJob.py` owns run admission, queueing, status, and
    recovery.
  - `API/Classes/OGCore/OGRunner.py` starts and supervises the worker process.
  - `API/Classes/OGCore/ogc_worker.py` imports OG-Core inside the selected
    calibration environment and writes model results.
  - `API/Classes/OGCore/OGResults.py` and `OGTables.py` read completed result
    artifacts and build OG-Core-native analysis responses.

### Frontend

- Main static app: `WebAPP/index.html`
- Core classes and route handling:
  - `WebAPP/Classes/`
  - `WebAPP/Routes/`

#### Frontend shell (MUIOGO)

The static frontend is a two-model shell: a header selector switches between
CLEWS (the existing MUIO interface, unchanged) and OG-Core. The selected model
drives per-model navigation through a body class
(`WebAPP/Classes/MuiogoShell.Class.js`, `muiogo.css`). Model-specific routes set
that state explicitly; `localStorage` remembers the default used by `/`.
OG-Core pages are scoped UI islands (`.ogc-*` styles) and call the `/ogc` API
through `WebAPP/Classes/Ogc.Class.js`.

#### OG-Core workspace

Opening an installed country calibration activates a country-scoped workspace.
`WebAPP/Classes/OGWorkspace.Class.js` coordinates the frontend workspace state
with the backend session. The Cases, Parameters, and Run routes require an
active workspace and use both `country_id` and `casename` when addressing a
case. Leaving the workspace clears the active backend session but does not stop
a running job.

### Runtime data and outputs

CLEWS continues to use:

- `WebAPP/DataStorage/Parameters.json`
- `WebAPP/DataStorage/Variables.json`
- `WebAPP/DataStorage/<model>/...`

OG-Core state is kept outside `WebAPP/DataStorage/` so CLEWS data discovery does
not interpret OG-Core state as CLEWS models. `MUIOGO_OG_DATA_DIR` controls the
location and defaults to `~/.muiogo/og-state`. It contains the calibration
registry, install jobs, installer cache, and country-scoped cases:

```text
cases/<country_id>/<casename>/
  genData.json
  res/<run_name>/
    run_meta.json
    ogcParams.json
    run_status.json
    run_log.txt
    <OG-Core result files>
```

Installed country calibrations and their virtual environments are stored under
`MUIOGO_OG_MODELS_DIR`, which defaults to `~/.muiogo/og-models`.

### OG-Core run lifecycle

The `/ogc` routes validate the active country workspace and delegate case and
run operations to the OG-Core service classes. `RunJob` permits one active
OG-Core solve per application process and holds later requests in a FIFO queue.
Runs are identified by the combination of country, case, and run name.

`OGRunner` starts `ogc_worker.py` with the Python interpreter from the selected
country calibration. MUIOGO owns `run_meta.json` and `run_log.txt`; the worker
owns `run_status.json` and the result files. A run is complete only when the
worker exits successfully and writes a successful terminal status.

A baseline is the reference run for a case. A reform records its baseline run
name, and its results remain reusable only while that baseline result remains
current. A reform requires a completed baseline; a transition-path reform also
requires a transition-path baseline. The run layer rejects a reform whose `S`,
`T`, `J`, `M`, or `I` dimensions differ from its baseline.

The worker builds each run from four layers, in order: OG-Core defaults, country
defaults, the country calibration dictionary, and the run's saved parameter
overrides. The browser receives form metadata from the installed defaults files;
large parameter arrays are loaded only when their table editor needs them.

Completed runs store an input fingerprint covering the run parameters, optional
tax input, calibration identity, time-path mode, and baseline result identity.
Changing parameters invalidates that run's results; changing or rerunning a
baseline also invalidates its dependent reforms. The client may display cached
results only when this fingerprint still matches the current inputs.

Parameter changes and case deletion are blocked while affected runs are active
or queued. Calibration installation or updates are also blocked while a run is
using that country environment, and a run cannot start while that environment
is being installed or updated. Cancellation stops the worker process tree.
Application startup marks interrupted active or queued runs as failed and
terminates a matching orphaned worker when one is found.

## Known architectural constraints

- Hardcoded or relative path assumptions exist and reduce portability.
- Solver binary discovery is not fully platform-agnostic.
- API/base URL and CORS configuration are not fully runtime-configurable.
- Backend and static frontend serving are tightly coupled.

These constraints are tracked as implementation issues and should be addressed
incrementally with tested changes.

### Solver resolution

Solver binaries (GLPK / CBC) are resolved at runtime using a four-tier
priority chain implemented in `Osemosys._resolve_solver_folder`:

1. **Environment variable** — `SOLVER_GLPK_PATH` or `SOLVER_CBC_PATH`
2. **System PATH** — via `shutil.which` (supports package-manager installs)
3. **Platform standard locations** — macOS: `/opt/homebrew/bin`,
   `/usr/local/bin`, `/usr/bin`; Linux: `/usr/bin`, `/usr/local/bin`, `/bin`,
   `/snap/bin`. Catches installs where the package manager placed the binary
   in a standard location but did not refresh PATH for the current shell.
   Inherited from MUIO 5.6.
4. **Bundled fallback** — folder inside `Config.SOLVERs_FOLDER`

If no solver is found through any of these steps, a `RuntimeError` is raised
at startup with a clear, actionable message. This replaces the previous
hardcoded, platform-specific path strings which failed silently on
Linux and Apple Silicon (see issue #43).

The resolver returns `(folder, is_bundled)`. `is_bundled` is `True` only when
the binary was found via tier 4. `DataFileClass.run` uses this to decide
whether to set the solver subprocess's `cwd` to the solver folder (bundled,
so adjacent DLLs resolve) or leave it inheriting from the caller (system
install). Inherited from MUIO 5.6.

## Upstream/downstream relationship

- Upstream reference: `OSeMOSYS/MUIO`
- This repository: downstream, separately managed

Design and delivery decisions for this repo must not depend on upstream schedules.

## MUIO-Mac relationship

`MUIO-Mac` is a separate macOS port effort. The long-term direction for `MUIOGO`
is platform independence so separate platform-specific forks are not required.

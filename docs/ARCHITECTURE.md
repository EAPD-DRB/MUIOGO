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
through `WebAPP/Classes/Ogc.Class.js`. The CLEWs install page (`#/ClewsInstall`,
reached from the Home page) follows the same pattern: `.clw-*` styles, and the
`/clews` API through `WebAPP/Classes/Clews.Class.js`.

#### OG-Core workspace

Opening an installed country calibration activates a country-scoped workspace.
`WebAPP/Classes/OGWorkspace.Class.js` coordinates the frontend workspace state
with the backend session. The Cases, Parameters, and Run routes require an
active workspace and use both `country_id` and `casename` when addressing a
case. Leaving the workspace clears the active backend session but does not stop
a running job.

The Results route (`#/OGResults`) draws nothing until a run is chosen: "View"
shows one run, "Compare" a reform against its baseline. The choice is kept in
the route's optional query (`#/OGResults?case=...&base=...&reform=...`), which
the page updates in place so refresh and shared links reopen the same view.

#### CLEWS results

The Results page uses MUIOGO-owned aggregation and layout state, with Tabulator,
Apache ECharts and jQuery UI for its table, chart and field panel. The RES Viewer
uses `MultiSelect.Class.js`. Vendored libraries live under `WebAPP/References/`
with their licences.

- `ResultAggregator.Class.js` groups records, applies filters and calculates
  totals. Show As calculations transform both detail cells and totals from a
  snapshot of their raw values. Percentage denominators include detail cells
  only; differences and running totals compare siblings at the same hierarchy
  depth, with grand totals left blank for those calculations.
- `ResultLayoutState.Class.js` serialises layouts and reads both legacy Wijmo
  saved views and the versioned MUIOGO format. Changing variables resets both
  value and condition filters before capturing the new default layout.
- `ResultPanel.Class.js` and `ResultFieldSettings.Class.js` edit the layout.
  `ResultGrid.Class.js` renders the table, clipboard selection and detail view.
- `AppResults/Controller/Pivot.js` coordinates the renderers. Case switching
  captures the remembered variable once and uses its group for both fetching
  result data and constructing the model.

Run the frontend regressions with `node --test tests/frontend/*.test.mjs`.
`tests/e2e/test_clews_results_page.py` exercises the real renderers and controls
with synthetic results, including percentages, CSV/SVG exports, original detail
records, filter resets, remembered views and the RES Viewer multiselect. These
checks do not write model inputs or launch a solver.

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

### OG-Core results

Each finished OG-Core run writes `results_meta.json` next to its results: start
year, `T`, `S`, `J`, the age vector, income-group shares and labels (from
OG-Core's `lambda_labels`), and steady-state population weights. Household
outputs are labelled and weighted only from this file. Runs solved before it
carried these fields are rebuilt once from their `model_params.pkl` by the
worker's `meta` mode.

`API/Classes/OGCore/OGReport.py` owns the variable catalog and the comparison
rules served by `/ogc/getResultsReport`: levels as a percent change, rates in
percentage points, fiscal values as shares of GDP, and a negative baseline
flagged instead of given a percent change.

## Code reading map

Start with the route for the user action, follow its service call, then inspect
the source table or run artifact it owns. The main paths are:

| Workflow | Browser code | Backend code |
| --- | --- | --- |
| Page loading and unsaved changes | `WebAPP/Routes/Routes.Class.js`, `NavigationGuard.Class.js` | `API/app.py` serves templates and registers blueprints |
| CLEWS structure and parameter editing | `WebAPP/App/Controller/AddCase.js`, dimension controllers such as `RYTCM.js`, `DataModel.Class.js` | `CaseRoute.py`, `CaseClass.py`, `UpdateCaseClass.py`, `OsemosysClass.py` |
| CLEWS import and installation | `Base.Class.js`, `ClewsInstall.js` | `UploadRoute.py`, `CaseImporter.py`, `API/Classes/Clews/` |
| CLEWS execution and results | `DataFile.js`, `WebAPP/AppResults/Controller/Pivot.js` | `DataFileRoute.py`, `DataFileClass.py`, `CommodityPrice.py` |
| OG country workspace and runs | `OGWorkspace.Class.js`, `OGCases.js`, `OGParameters.js`, `OGRuns.js` | `OGCoreRunRoute.py`, `OGCoreCase.py`, `RunJob.py`, `OGRunner.py`, `ogc_worker.py` |
| OG–CLEWS coupling | Run-hook and patch endpoints under `/oglink` | `API/Classes/OGLink/`, `oglink/oglink/`; see `oglink/README.md` |

Class filenames in the browser column without a directory prefix are under
`WebAPP/Classes/`; controller filenames are under `WebAPP/App/Controller/`.
CLEWS case services are under `API/Classes/Case/`, OG services are under
`API/Classes/OGCore/`, and route modules are under `API/Routes/` in their
matching workflow directory.

### CLEWS table conventions

`genData.json` declares entities, stable IDs, and relationships. Shared
`WebAPP/DataStorage/Parameters.json` defines parameter IDs, defaults, dimension groups,
and units. A case's `<group>.json` files hold its source parameter values.
Group letters describe dimensions: `R` region, `Y` year, `T` technology, `C`
commodity, `E` emission, `S` storage, `M` mode, `Ts` timeslice, `Se` season,
`Dt` day type, `Dtb` daily time bracket, and `Cn` user-defined constraint.
The current exporter writes a single solver region, `RE1`.

For example, `RYTCM.json` is indexed first by parameter and then by scenario.
Each scenario contains rows with `TechId`, `CommId`, `MoId`, and year columns.
`OsemosysClass.RYTCM()` and the browser's `DataModel.RYTCM()` turn these rows
into nested lookups. Grid projections add names, descriptions, and units;
save handlers retain IDs and parameter values and group rows by scenario again.

`SC_0` is initialized with parameter defaults. Other scenarios use `null` for
an inherited value. Export starts with the parameter default and applies
non-null values from active scenarios in the caserun's saved order, so the last
such value wins. Zero is an explicit value. Sorting the scenario list or
replacing nulls with zero changes the exported model.

### CLEWS execution and result ownership

For CBC, the application exports `data.txt`, preprocesses it into
`data_processed.txt`, builds `lp.lp` with `glpsol --check`, then optimizes with
CBC. Preprocessing derives sparse technology/mode sets from the exported
relationships. Matrix caching fingerprints the model file, processed data, and
matrix flavor; a matching filename alone is insufficient for reuse.

`res/<caserun>/` owns generated inputs, logs, solver results, and extracted
CSVs. `view/<group>.json` combines results from several runs and is a UI cache.
Batch solving uses a separate `DataFile` instance per worker and serializes
updates to those shared JSON files. The annual commodity price is calculated
from full-precision solver values before ordinary CSV display rounding.

In the browser, `Pivot.js` coordinates `ResultLayoutState` (saved layout and
filters), `ResultAggregator` (grouping and calculations), `ResultGrid`
(Tabulator), and `Chart` (ECharts). `ResultPanel` and `ResultFieldSettings`
edit the shared layout state. Keep numerical aggregation separate from display
formatting so charts, tables, and exports use the same values.

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

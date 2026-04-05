# MUIOGO Architecture (Current State)

## System overview

`MUIOGO` currently runs as a Flask application that serves:

- backend API routes from `API/`
- static frontend assets from `WebAPP/`
- model data and run artifacts in `WebAPP/DataStorage/`

Solver execution is handled by backend subprocess calls (GLPK/CBC).

## Major components

### Backend

- Entry point: `API/app.py`
- API routes:
  - `API/Routes/Case/`
  - `API/Routes/DataFile/`
  - `API/Routes/Upload/`
  - `API/Routes/Case/SyncS3Route.py`

### Frontend

- Main static app: `WebAPP/index.html`
- Core classes and route handling:
  - `WebAPP/Classes/`
  - `WebAPP/Routes/`

### Runtime data and outputs

- `WebAPP/DataStorage/Parameters.json`
- `WebAPP/DataStorage/Variables.json`
- `WebAPP/DataStorage/<model>/...`

## Known architectural constraints

- Hardcoded or relative path assumptions exist and reduce portability.
- Solver binary discovery is not fully platform-agnostic.
- API/base URL and CORS configuration are not fully runtime-configurable.
- Backend and static frontend serving are tightly coupled.

These constraints are tracked as implementation issues and should be addressed
incrementally with tested changes.

### Solver resolution

Solver binaries (GLPK / CBC) are resolved at runtime using a three-tier
priority chain implemented in `Osemosys._resolve_solver_folder`:

1. **Environment variable** — `SOLVER_GLPK_PATH` or `SOLVER_CBC_PATH`
2. **System PATH** — via `shutil.which` (supports package-manager installs)
3. **Bundled fallback** — folder inside `Config.SOLVERs_FOLDER`

If no solver is found through any of these steps, a `RuntimeError` is raised
at startup with a clear, actionable message. This replaces the previous
hardcoded, platform-specific path strings which failed silently on
Linux and Apple Silicon (see issue #43).

## Upstream/downstream relationship

- Upstream reference: `OSeMOSYS/MUIO`
- This repository: downstream, separately managed

Design and delivery decisions for this repo must not depend on upstream schedules.

## MUIO-Mac relationship

`MUIO-Mac` is a separate macOS port effort. The long-term direction for `MUIOGO`
is platform independence so separate platform-specific forks are not required.


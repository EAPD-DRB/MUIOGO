# Upstream Sync Notes

Use this when pulling a new upstream `MUIO` release into `MUIOGO`.

## Baseline

- Start from `origin/main`.
- Compare against the upstream release tag, not `upstream/master`, unless there is a specific reason to include later commits.
- Do not build from exploratory merge branches or dirty worktrees.

## Review First

These files are the main overlap surface and should always be reviewed directly against upstream:

- `API/app.py`
- `API/Classes/Base/Config.py`
- `API/Classes/Base/FileClass.py`
- `API/Classes/Case/DataFileClass.py`
- `API/Classes/Case/OsemosysClass.py`
- `API/Routes/DataFile/DataFileRoute.py`
- `API/Routes/Upload/UploadRoute.py`
  (the zip-import core of `handle_full_zip` and the version-migration helpers
  moved to `API/Classes/Case/CaseImporter.py`; port upstream changes to that
  logic there, not back into the route)
- `WebAPP/index.html`
- `WebAPP/App/View/Navbar.html`
- `WebAPP/App/View/Sidebar.html`
- `WebAPP/Routes/Routes.Class.js`
- `WebAPP/Classes/Osemosys.Class.js`
- `WebAPP/Classes/Html.Class.js`
- `WebAPP/Classes/Const.Class.js`
- `WebAPP/Classes/DataModelResult.Class.js`
- `WebAPP/AppResults/Controller/Pivot.js`
- `WebAPP/DataStorage/Variables.json`

## Reject As-Is

Do not take these upstream patterns without a deliberate compatibility decision:

- cwd-relative path regressions
- `WebAPP/app.log` or any other log path under the static web tree
- deleting logs on startup
- `shell=True` solver calls
- dormant files that are not actually wired into the app, such as `FileClassCompressed.py`
- removals of MUIOGO-specific repo infrastructure under `.github/`, `docs/`, `scripts/`, or repo assets
- frontend churn unrelated to the approved sync scope, such as `Home.js` event regressions, `app.config.js`, or theme/image swaps

## Repeatable Checks

Run these before starting the port and after each stacked branch lands:

```bash
./scripts/setup.sh --check
python -m py_compile API/app.py
./scripts/smoke.sh
git ls-files -u
git grep -n -E '^(<<<<<<<|=======|>>>>>>>)($| )' -- . || true
```

Notes:

- `git ls-files -u` must return nothing. That is the real unresolved-merge check.
- The conflict-marker scan is a secondary check and should not replace the Git index check.
- Smoke tests should not depend on the repo root being writable and should be run with the installed MUIOGO interpreter, not whichever `python` happens to be on PATH.
- The smoke command assumes MUIOGO was installed correctly with `./scripts/setup.sh`. For a custom `--venv-dir`, activate that virtual environment first or set `MUIOGO_VENV_PYTHON` explicitly.

### Frontend shell check (required)

The MUIOGO shell patches four upstream files (`WebAPP/App/View/Navbar.html`, `WebAPP/App/View/Sidebar.html`, `WebAPP/Routes/Routes.Class.js`, `WebAPP/index.html`). Python smoke tests cannot detect breakage there, so the Playwright smoke test in `tests/e2e` is a required check on every upstream sync.

One-time setup, from the repo root with the MUIOGO virtualenv active:

```bash
pip install "pytest>=7" pytest-playwright
playwright install --with-deps chromium
```

The app needs a solver at startup; `./scripts/setup.sh` already installs the supported solvers, so no extra solver step is required when that setup path is used.

Run it:

```bash
pytest tests/e2e -v --screenshot on --full-page-screenshot --tracing retain-on-failure
```

This must pass before a sync branch is merged. CI runs this automatically on every pull request via the `e2e` job; run it locally before opening the sync PR so shell breakage surfaces before review. It covers the model picker, both header switches, sidebar and case-picker visibility per model, and model-specific deep links. The `--screenshot` and `--tracing` flags let CI capture artifacts and can be dropped for a plain local run. Failures leave screenshots and traces under `test-results/`; CI uploads the same directory as the `e2e-results` artifact.

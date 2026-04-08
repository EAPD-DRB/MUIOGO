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
- `WebAPP/index.html`
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
- The smoke command assumes MUIOGO was installed correctly with `./scripts/setup.sh`. If you used a custom `--venv-dir`, activate that venv first or set `MUIOGO_VENV_PYTHON` explicitly.

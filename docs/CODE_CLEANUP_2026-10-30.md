# Code cleanup validation — 2026-10-30

This document and its companion hash manifest record the initial cleanup stage.
Subsequent [country-model tests](../output/cleanup-validation-2026-10-30/summary.json)
completed two Vietnam CBC solves and two OG-ZAF steady-state solves. Both issues
found there were then fixed; the [final verification record](../output/cleanup-validation-2026-10-30/edit-fixes.json)
contains the updated source hashes and passing results: 727 backend tests,
19 subtests, 85 JavaScript tests and 125 browser tests. Earlier records below
are retained as snapshots of the initial checks.

The cleanup was performed on `main` in `/Users/sato/GitHub/MUIOGO`, against
baseline commit `f6b70a56d003465a9bb7d138213a6f1e7bd11b41`. The user authorized
this checkout and correcting the stale checkout path in `AGENTS.md`.

## Changes

- Removed obsolete commented-out implementations and commented debug statements
  from the backend and frontend. Excess blank lines were reduced where parsed
  code and literal values remained identical.
- Removed 26 unused Python import bindings and 15 unused JavaScript import
  bindings. The unused `Home.js` route import was retained to preserve its
  dependency on route initialization.
- Replaced 43 assignments immediately followed by returning the same value with
  direct returns in `OsemosysClass.py` and `ImportTemplate.py`.
- Removed unused temporary values from data-file generation, batch execution,
  viewer generation, and CSV download. Retained the view-data update call while
  discarding its unused return value, and removed an unused exception binding.
- Removed the earlier, overridden `DataModel.getStgData` and `DataModel.StgName`
  definitions. Their effective implementations remain.
- Removed `DataModelResult.getUnitDataOLD` and `getPivot_OLD`. Repository-wide
  reference searches found no callers. The current unit and pivot methods remain.
- Updated eight tuple-based `isinstance` expressions to equivalent Python 3.11
  union expressions, resolving the pre-existing configured lint findings.

Changes affect 26 Python files and 74 JavaScript files. Model source parameters,
solver formulations, dependencies, tests, and vendored libraries were not changed.
Existing untracked work was excluded from cleanup. Compatibility endpoints,
including `/uploadCaseUnchunked_old`, remain available.

## Verification

Three kinds of checks were used: source inspection and parsed-code comparisons,
baseline/candidate behavior comparisons, and existing regression suites.

| Check | Baseline | Cleaned code |
| --- | --- | --- |
| Backend and API regressions | 662 passed; 19 subtests passed | 662 passed; 19 subtests passed |
| Linker regressions | 319 passed; 7 skipped | 319 passed; 7 skipped |
| JavaScript behavior regressions | 78 passed | 78 passed |
| Chrome browser regressions | 119 passed | 119 passed |
| Configured Ruff check | 8 existing findings | Passed |
| Git whitespace check | — | Passed |

Python syntax and abstract syntax trees were checked for all 199 tracked Python
files. Comparisons against the baseline allowed only the reviewed import, direct
return, type-check, and unused-local changes. JavaScript was parsed and compared
for all 117 first-party application modules; comparisons allowed only the listed
import and method removals. Comment-only edits preserved parsed executable code,
including string and template contents.

An additional 138 direct baseline/candidate comparisons passed. These exercised
the 29 simplified data getters with populated, empty, and missing-key inputs;
13 default entity factories with both initial and generated IDs; and worker
serialization with native values, NumPy scalars and arrays, nested values,
and non-finite numbers. These checks did not write case data or run optimizers.

The source hashes in `CODE_CLEANUP_2026-10-30.json` identify the tested files.
Final hash verification confirmed that those files had not changed after testing.
The existing frontend test is also invoked by the backend suite, so the suite
counts above should not be added as a count of distinct behaviors.

## Environment and limits

The repository's `.venv` was used. PyYAML was missing from that environment;
an isolated temporary copy of the cached PyYAML package passed an import
preflight before tests ran. Cached browser-test packages and the installed
Chrome were used without modifying project dependencies. Node came from the
bundled local runtime.

The first sandboxed backend run could not open local test servers or inspect
test worker processes. With the required local access, all five affected tests
passed on both baseline and cleaned code.

The seven skipped linker checks require unavailable optional OG-Core/OG-PHL
packages or local OG-ETH, OG-IDN, OG-PHL, and OG-ZAF calibrations. Full country
optimizations were not run: this cleanup does not change model inputs or
equations. Existing matrix-only and mocked solver regressions passed as part
of the backend suite. No optimizer runs were performed.

No regressions were found in the available checks. These checks provide evidence
for preserved behavior, rather than a guarantee for every untested environment
or external caller.

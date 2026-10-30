# PR #550 review fixes

These fixes were validated against PR #550 head `8ab279eddfa0f4189b9fc390785c5873622223e7`
and MUIOGO main `efb56662`. No case parameters or solver equations were edited.

## Health emissions window

`oglink/channels.py` now selects emissions ratios from `og_start_year` through `og_start_year + 9`.
Previously it averaged the first ten exported rows, potentially including only pre-simulation history.
An empty or all-missing simulation window raises a clear error. Available values within the calendar
window are averaged without inventing observations. The existing non-finite-result check remains.

The regression with unchanged 2015–2024 emissions and a 50% reduction in 2025–2034 now produces a
-50% change for an OG model beginning in 2025, rather than zero.

## Cogeneration electricity-cost allocation

`oglink/lcoe.py` preserves region when loading annual plant costs. It computes useful-output allocation
fractions by `(region, technology, year)` and applies the same fraction to own costs and priced inputs.
Useful co-output consumption is determined in that region and year. Regionless records are accepted
only when the available exports describe at most one region; ambiguous regional matching raises.

Previously a technology-wide fraction pooled all years and regions. Future heat production could
change historical electricity prices, and one region's co-output could dilute another region's costs.
Tests cover future production, future co-output consumption, heterogeneous regional costs and inputs.
The PR's existing physical-output-share allocation convention is retained. This change does not
establish a general allocation rule for co-products expressed in different physical units.

## Health-source discovery and missing country records

`oglink/country.py` selects default GBD files by country, year, population group, sex, risk and the
mortality input's measure/metric/cause. Explicit paths and explicit `None` are preserved without
scanning defaults. An unmatched country no longer inherits the Philippines file.

The original research repository supplied verified Indonesia, South Africa and Ethiopia extracts.
Their original numerical text is preserved; hashes, source revision, extraction description and the
unchanged Philippines reference are recorded in `IHME-GBD_2023_DATA/sources.json` and `DATA.md`.
Brazil is deferred at the user's explicit request. Its age-specific CSV and country multiplier are
outside the completed scope; official data access requires a signed-in IHME account, and checked
public sources did not provide a complete matching extract.

## Validation

- Full backend suite before adding the new integration checks: **510 passed, 1 skipped**.
- Linker suite, including real-data and regression checks: **235 passed, 7 skipped**.
- Application/linker integration checks: **5 passed**, using the real CLI subprocess and status route.
- Repository lint and linker syntax/undefined-name lint: passed.
- Documented CLI and actual post-run-hook subprocess launch in the synced app environment: passed.
- Runtime dependency sync: `uv sync --frozen` installed the declared SciPy 1.17.1; app status reports
  the in-repository linker installed. No country models were registered in the isolated launch check.
- Source/configuration whitespace check: passed. Imported data bytes, including the original
  McDuffie table's CRLF endings, are preserved.
- PyYAML preflight: passed using the isolated disposable test dependency directory.
- Existing Philippines burden values and uncertainty bounds: all 1,118 matched the recovered source.
- CBC/GLPK optimizations: **zero**. Existing backend tests include generation/matrix-only checks.
- Full OG country equilibria and browser end-to-end tests: not run. Existing linker tests requiring
  local external data or installed OG packages remain skipped; they are not counted as validations.

Tests use MUIOGO's `.venv/bin/python` with the declared dependencies and test tools isolated under
`/tmp/muiogo-pr550-deps`; no other project's site-packages directory is used.

## PR #539 reverse-pass corrections — 2026-10-30

Implemented the reviewed reverse pass against main `9a9f6f665`, preserving the newer linker from
PR #550. The reviewed PR head was `28f6841c7909fd467d8ea37cb0bab718e85d1209`; its outdated forward
linker and packaging were not copied over main. No country case, source parameter, solver equation,
live result or viewer cache was changed. No branch or additional worktree was created.

This focused integration supersedes PR #539 and credits its original reverse-pass implementation
by @Adityakushwaha2006 (commit `e7c650e5b`). The PR's 24 add/add conflicts were reviewed individually:
19 retain the current main version; README, CLI, country configuration and manifest retain main plus
the corrected writeback integration; `.gitignore` combines useful patterns from both versions.
The combined rules preserve `oglink_runs/` and the machine-local registry ignore and add
`ogclews_runs/`, `_validation*/`, `_validation*.json`, `_pr1_gate_run/`, logs and Python caches.

The newer demographic income-group inputs, 2025 Philippines start year, health-year alignment,
region/year-specific commodity-price costing, calibrated solver settings, in-process steady-state
solves, clean mortality marginal, in-repository launcher and regression tests are preserved. The
McDuffie CSV retains its original bytes. The unused PR-only reporting helpers `layered_entry()` and
`stage_clews_source()` are deferred to reporting work; standalone packaging and its incompatible
launcher test are excluded from this integration.

### Behavior and implementation

- Added `oglink/clews_case.py`, `patch.py`, `muiogo_client.py` and `writeback.py`, and exposed
  `python -m oglink writeback` through the existing CLI. Country configuration now declares the final
  demand carrier; the Philippines mapping is `PHL_HOU_ELE` to `PHL_HOU_ELEF`. The example countries
  file and README document custom mappings and command usage.
- Replaced the proposed raw, selected-scenario SAD read with effective demand computed from
  `Parameters.json` defaults and all active scenarios in the caserun's stored order. Null inherits;
  explicit zero overrides. This matches `DataFile.gen_RYC` and `Osemosys.getScOrder`. The write layer
  is the last active scenario, and an explicitly requested lower-priority layer is rejected.
  Inherited demand 100 and overridden demand 200 therefore become 110 and 220 at ratio 1.1.
- Required and checked the forward manifest's country, UN code and originating reform caserun, plus
  the CSV's region, price-facing source fuel, activity driver and recorded concordance index. Duplicate
  years, mixed series, invalid ratios and malformed input are rejected before posting. The caserun
  cloned by `--base-caserun` must match `scenario.reform_dir`, retaining its reform policies. Manifest
  scenario paths are now absolute and include the OG start year. Optional emissions and deferred-rate
  feedback also validate their region/species or shape. The current application exports region RE1;
  other regions are rejected. Custom countries files work for both run and writeback.
- Suppressed empty patches locally after considering demand and optional emissions changes. A valid
  unchanged response requests no case copy or solve. No overlapping forecast years remains an error.
  Unchanged emissions penalties are compared against effective RYE/EP values, preventing false no-op
  warnings when only demand changes. Discount rates remain deferred, never constraints or changes.
- Changed demand-ratio and emissions-penalty CSV serialization from six decimal places to 17 significant
  digits, retaining full double precision when these outputs become model inputs. HTTP failures retain
  structured application reasons, and HTTP 200 must describe a successful solved-case record.

### Validation

- Backend suite: **661 passed, 1 skipped, 19 subtests passed** (`tests`, excluding browser E2E).
- Linker suite: **319 passed, 7 skipped**. Coverage across the four new implementation modules: **94%**;
  the HTTP client has **100%** statement coverage.
- Real CLI subprocess to local Flask HTTP endpoint: dry-run, unchanged, applied and server-error paths
  passed using disposable cases created through `/saveCase`. The optimizer boundary was stubbed.
  The actual application copied cases, applied source changes and generated datafiles. Source case
  hashes remained unchanged; dry-run and unchanged paths created no case copy and called no optimizer.
- Deterministic model export: `generateDatafile` then `preprocessData` retained 110/220 demand and the
  expected `MODEperTECHNOLOGY` set. `glpsol --check` emitted a valid LP containing the updated demand
  constraints. This was generation/check-only, not an optimization.
- Unit regressions cover inheritance/defaults/zeros, malformed sources, input identity and time-grid
  mismatches, duplicate years, invalid ratios, optional emissions, deferred rates, precision, CLI
  argument forwarding, BOM input and structured HTTP failures.
- Repository lint, linker syntax/undefined-name lint and whitespace checks passed.
- Bare `.venv` lacks PyYAML and pytest. Tests used its interpreter with the existing disposable
  `/tmp/muiogo-pr550-deps` dependency directory; the PyYAML preflight passed there. This is an environment
  dependency arrangement, not a model or validator failure.
- CBC/GLPK/OG country optimizations: **zero**. Full country equilibria and browser E2E were not run.

### Limits

Manifest path/mapping checks establish input identity, not freshness. No source/result hash contract
is added here, so edits made later in the same paths are not detected. Legacy relative manifests need
their absolute origin established from verified provenance. Feedback using an index override absent
from the recorded concordance is rejected. Existing safeguards still refuse all-zero demand carriers
and changes that set live demand to zero. These changes correct the application of external final
demand feedback; they do not validate or recalibrate the underlying economic demand-driver assumption.

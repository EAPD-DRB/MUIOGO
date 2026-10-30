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

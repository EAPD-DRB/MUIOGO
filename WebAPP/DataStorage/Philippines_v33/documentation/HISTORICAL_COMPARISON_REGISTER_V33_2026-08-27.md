# Philippines v33 historical-comparison register

## Status

This register is a read-only comparison of the canonical `Philippines_v33/BASE_V33_GAS_DELIVERY` result with retained or current official observations. It changes no source parameter, constraint, generated solver file, or result.

- Total rows: 30
- Score-ready comparisons: 19
- Diagnostic-only boundary or period comparisons: 7
- Explicit evidence gaps: 4

`score_ready` does not mean the model passes. It means the observation and model result are sufficiently aligned to evaluate against the declared tolerance. `diagnostic_only` rows must not enter an aggregate calibration score. `evidence_gap` rows identify the specific data needed before a historical test is possible.

## Main additions

- Water: national and agricultural-withdrawal boundary diagnostics, current PSA abstraction revision, source-share diagnostic, and explicit missing cooling/pumping-energy evidence.
- Climate: 2020 national energy-plus-transport emissions, rice CH4, managed-soil N2O, agriculture-scope coverage, and missing land-carbon accounting.
- Nexus: AFF final-energy total and electricity share, irrigation water, biomass-to-energy boundary, and thermal-power water.

## Important boundary decisions

- PSA total abstraction includes large non-consumptive hydropower flows absent from v33; it is diagnostic only.
- AQUASTAT variable 4250 is broader than crop irrigation; it is diagnostic only.
- The complete national agriculture GHG inventory includes livestock and manure categories absent from v33; only rice CH4 and managed-soil N2O are score-ready.
- DOE agriwaste and the model's recoverable residue basket are not identical; the biomass row is diagnostic only.
- No observed outcome is converted into a model constraint.

## Files

- `historical_comparison_register_v33.csv`: complete auditable register.
- `historical_comparison_register_v33_score_ready.csv`: aligned subset for the comparison scorer.
- `historical_comparison_register_v33_sources.csv`: source catalogue, retained-evidence paths, and hashes.
- `historical_comparison_register_v33_evidence.json`: exact calculations and SHA-256 identities of model-result inputs.
- `historical_comparison_register_v33_history.json`: generated fit/forcing summary for score-ready rows.
- `build_historical_comparison_register_v33.py`: reproducible read-only extractor retained with the case.

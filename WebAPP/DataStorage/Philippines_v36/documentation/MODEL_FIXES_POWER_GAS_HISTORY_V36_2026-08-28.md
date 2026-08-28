# Philippines v36 electricity and gas-generation history candidate

## Outcome

V36 is a clean, non-forcing successor to canonical `Philippines_v33`. It is a
failed calibration candidate and was not promoted. The sourced accounting and
physical corrections reduce the 2024 gross-generation shortfall from 13.39% to
6.58% and increase 2024 gas generation from 1.6374 PJ to 31.9347 PJ, but the
latter remains 50.85% below DOE's 64.9692 PJ observation. That is outside the
declared 15% validation tolerance, so no policy runs, seal or promotion were
performed.

Observed gross generation and fuel dispatch remain benchmark-only. No activity
floor, historical target, forced share, `TAL`, `TAU` or equality was introduced.

## Prior attempts inspected

- V20 introduced the take-or-pay idea as a useful economic correction. Its
  implementation credited the full domestic-gas envelope to the aggregate legacy
  gas technology. That proxy was broader and longer-lived than the disclosed
  plant contracts, so it could subsidize activity outside the contractual tranche.
- V21 changed the gross-to-sales conversion to 1.1170, representing distribution
  and transmission losses but omitting station service/plant own-use.
- V33 corrected gas delivery competition but retained the low gross balance and
  the broad contract proxy. Its sealed BASE result is the unchanged canonical
  comparison: objective 852438.33485986, 78.1788 seconds, and 467075 rows,
  517844 columns and 8194641 matrix nonzeros.
- V34 was an unrelated broad endogenous-cost candidate. Its only optimization
  timed out at the 180-second budget and it was not promoted.
- V35 replaced 17 zero variable costs with a user-specified 0.1 MUSD/PJ proxy.
  It solved, but raised 2024 gas generation only to 23.1989 PJ and caused
  unsupported shifts elsewhere. It remains an unsealed research candidate.

Because both requested successor names already existed, this candidate is v36.

## Equation-first classification

| Observation or driver | Classification | Treatment |
|---|---|---|
| DOE gross grid generation | Benchmark only | Validation; never a demand or activity target |
| DOE natural-gas generation | Benchmark only | Validation; never a dispatch target |
| Grid sales, station service and system loss | Physical pass-through coefficient | `PHL_POW_TD` input/activity ratio |
| Grid gas nameplate capacity | Initial physical stock | Scale the inherited residual-capacity path while preserving retirements |
| Dependable/nameplate gas capacity ratio | Continuing physical availability | Legacy-gas availability factor from 2022 onward |
| Aggregate gas input per gross gas generation | Physical conversion efficiency | Legacy-gas processed-fuel input ratio |
| Disclosed Santa Rita and San Lorenzo contract quantities | Continuing contractual cost/eligibility tranche | Capped discounted mode; no minimum activity |
| Sector electricity demands | Exogenous final demand | Unchanged because the commercial-meter boundary cannot yet be split without double counting endogenous electric heat |

`PHL_POW_TD` is a pass-through conversion. `PHL_POW_CHP_NG_OLD` is a
physical conversion stock with two economically distinct but physically identical
modes. Gas extraction/import are resource supplies and gas processing is a fuel
conversion. These classifications were verified from the active equations and
mappings, not inferred from names.

## Sources and schema ledger

The complete provenance is in all six canonical tables under `data_sources/`:

- `SOURCES.csv`: DOE grid electricity balance and off-grid boundary, DOE capacity,
  DOE power fuel-input situationers, and the FPH annual report.
- `ASSUMPTIONS.csv`: grid boundary, gas-stock remeasurement, contract-cost
  reclassification, and gas-plant efficiency.
- `CALCULATIONS.csv`: full-precision gross/sales ratios, capacity scaling,
  fuel-input coefficients, and contract-mode cost/cap arithmetic.
- `MODEL_MAP.csv`: exact source files, parameters, scenarios, modes and years.
- `GAPS.csv`: the unresolved commercial-meter decomposition and the missing
  Luzon/inter-island/plant-contract dispatch boundary.
- `CHANGES.csv`: the complete v36 source scope and non-forcing status.

The five retained source PDFs are under
`data_sources/evidence/v36_power_gas/`; their SHA-256 hashes are checked by the
builder and recorded in `SOURCES.csv`. The builder rejects any evidence mismatch.

## Source changes

- `RYTCM.json / IAR / SC_0 / PHL_POW_TD / mode 1`: replace 1.117030861453816
  with annual DOE grid-consumption/grid-sales ratios of 1.2235072721192584,
  1.2138853739520623, 1.2209843885740153, 1.2316726166486582 and
  1.2216639919482726 for 2020-2024; hold 2024 thereafter. The 2020 inputs remove
  the separately reported off-grid sales and consumption; DOE excludes off-grid
  from the table from 2021 onward.
- `RYT.json / RC / SC_0 / PHL_POW_CHP_NG_OLD`: scale the inherited post-2021
  stock path by 3.732/3.4525 = 1.080955829109341. Inherited retirement years
  remain unchanged.
- `RYT.json / AF / SC_0 / PHL_POW_CHP_NG_OLD`: use
  3.281/3.732 = 0.8791532690246516 from 2022 onward.
- `RYTCM.json / IAR / SC_0 / PHL_POW_CHP_NG_OLD / modes 1-2`: use DOE
  aggregate processed-gas/gross-electricity coefficients of
  1.6373952695146499 in 2022, 1.7156831653467723 in 2023 and
  1.8049151659555605 in 2024, holding 2024 thereafter. The 2020-2021 physical
  coefficient remains inherited.
- `RYTM.json`, `RYTCM.json`, `RYTEM.json` and `RYT.json`: mode 1 represents
  the disclosed 43.0 + 21.5 PJ/year legacy contract tranche through the stated
  PPA endpoints; mode 2 has the same physical input, output and emissions but
  ordinary market fuel cost. Mode 1 has only a maximum eligible tranche and no
  minimum. The fixed payment is represented in fixed cost with an exactly
  corresponding activity credit so the sunk payment is neither omitted nor
  double-counted. No take-or-pay quantity is inferred for the new LNG GSPA.
- `genData.json`: case identity, description and the legacy-gas mode description
  only. No technology or commodity identity set changed.

All unrelated source JSON files, including `RYC.json`, are byte-identical to v33.

## Pre-flight gates

The source-specific equation-first gate passed with zero optimizer and zero
generation runs. It proves exact source-diff scope, unchanged final demand,
preserved retirements, identical physical mode mappings, absence of activity
minimums, and sufficient stock/resource envelopes for observed gas generation.

The generic active-formulation physical gate passed for BASE and all three policy
configurations. Its optional strict historical-stock mode reports inherited
2020-2024 heat-service shortfalls in both v33 and v36 because that diagnostic
deliberately ignores finite endogenous historical investment. Canonical v33
actually builds heat capacity in 2021-2022. Therefore v36 requires the active
formulation gate plus the new source-specific gas stock/resource envelope check;
the strict no-historical-investment report remains advisory. This interpretation
is recorded in `preflight_gate_adjustment_v36.json`.

The expected second gas mode increases matrix size by 136 rows, 680 columns and
7192 nonzeros. The corruption tripwire was narrowly adjusted from 0.1% to 0.2% so
the known 0.1313% column increase passes while larger unexplained growth still
fails. A first GLPK generation-only attempt stopped at the old threshold; it used
no optimizer and was moved outside the clean candidate.

## Generation, matrix and optimizer runs

The clean BASE candidate was generated and preprocessed through the application
`DataFile` path. The generated-value gate verified that source edits survived
export, including `MODEperTECHNOLOGY := 1 2` and the duplicated physical/emissions
mappings. `glpsol --check` passed.

| Evidence | V33 BASE | V36 BASE |
|---|---:|---:|
| Solver status | Optimal | Optimal |
| Objective (MUSD) | 852438.33485986 | 863976.44309006 |
| Objective change | -- | +1.35354% |
| CBC runtime (seconds) | 78.1788 | 68.1574 |
| Rows | 467075 | 467211 |
| Columns | 517844 | 518524 |
| Matrix nonzeros | 8194641 | 8201833 |

BASE was the initial candidate optimization. Deterministic checks could prove
physical headroom and exact export, but only the coupled LP could determine
endogenous fuel allocation and dispatch. After the user explicitly accepted the
material improvement and residual historical limitation, the three required policy
runs were generated separately and optimized concurrently.

## Historical result

DOE gross values below use the main-grid consumption boundary in the sourced
balance (GWh converted at 0.0036 PJ/GWh).

| Year | DOE gross PJ | V33 gross PJ | V36 gross PJ | V36 error | DOE gas PJ | V33 gas PJ | V36 gas PJ | V36 gas error |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 360.9890 | 331.9804 | 361.5214 | +0.15% | 70.1892 | 73.2472 | 34.4912 | -50.86% |
| 2021 | 382.0130 | 336.0149 | 365.1499 | -4.41% | 68.6160 | 62.8636 | 62.8636 | -8.38% |
| 2022 | 401.4564 | 351.6933 | 379.1020 | -5.57% | 64.3824 | 55.4642 | 67.5355 | +4.90% |
| 2023 | 424.8141 | 372.7770 | 407.3749 | -4.11% | 60.0048 | 38.3862 | 49.5280 | -17.46% |
| 2024 | 456.9870 | 395.7969 | 426.8960 | -6.58% | 64.9692 | 1.6374 | 31.9347 | -50.85% |

The gross accounting correction works materially in every year. Gas fit improves
in 2022-2024, but 2020 becomes worse once the old unlimited subsidy is replaced by
the disclosed tranche, and 2023-2024 still fail qualification.

In 2024, mode 1 produces 31.9347 PJ against its 35.7358 PJ cap, mode 2 produces
zero, and legacy-gas capacity is slack. Domestic extraction is exactly at its
76.8819 PJ source cap with a -5.2604 dual, imports/LNG are unused, and the contract
cap has zero dual. Thus legacy plant stock, availability and contract eligibility
do not bind the missing 33.03 PJ. The national least-cost model instead rejects
market LNG at the official high 2024 landed price. Widening the contract tranche
or lowering LNG price would conceal the remaining structural omission and lacks
source support.

## Qualification and disposition

- Passed: source identity/diff gate, six-table provenance, evidence hashes,
  non-forcing gate, stock/resource feasibility, active-formulation physical gates,
  application generation, preprocessing, generated mappings, GLPK matrix check,
  CBC optimality, runtime gate, result/hash identity.
- Accepted limitation: gross generation is not within 5% in every historical year (2022 and 2024 are
  outside); gas generation within 15% in every historical year (2020, 2023 and
  2024 are outside). The user explicitly accepted this material improvement without
  weakening the non-forcing or integrity gates.
- Completed: all four required runs are optimal and runtime-acceptable.

| Scenario | Objective (MUSD) | Change from v33 | CBC seconds | Runtime ratio |
|---|---:|---:|---:|---:|
| BASE | 863976.44309006 | +1.35354% | 68.1574 | 0.872x |
| COAL_PHASEOUT | 887217.82426329 | +1.58969% | 122.2568 | 0.982x |
| RE | 874666.81369337 | +1.39182% | 136.2589 | 1.028x |
| EV | 840539.25824178 | +1.49087% | 160.3135 | 1.079x |

The original BASE disposition remains at
`documentation/power_gas_history_base_qualification_v36.json`. The explicit
acceptance, four-scenario validation and final promotion qualification are at
`documentation/USER_ACCEPTANCE_V36_2026-08-28.json`,
`documentation/power_gas_history_four_scenario_validation_v36.json`, and
`documentation/power_gas_history_candidate_status_v36.json`.

## Required next correction before another solve

The remaining equation-level requirement is a sourced representation of the real
regional and contractual operating boundary: Luzon load, inter-island transfer
limits, and plant-level PPA/GSPA/LNG scheduling terms. A national copperplate can
select apparently cheaper generation anywhere in the Philippines and therefore
cannot explain why relatively costly Luzon gas ran when cheaper national
substitutes appeared available. Another optimizer run is not justified until that
boundary and its source inputs are identified and pass a deterministic envelope
check.

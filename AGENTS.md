# MUIOGO model-change protocol

These instructions apply whenever changing or validating an OSeMOSYS case in this repository.

## Skill-use preference

Never invoke or consult a Codex skill unless the user explicitly asks for that
specific skill. Do not infer skill authorization from the task type or from a
skill's trigger description.

## Non-forcing calibration master rule

Never force an endogenous model outcome to match an observed outcome merely
to reproduce history. This includes technology activity, market shares,
dispatch, irrigated area, production mix and resource-source shares.

Observed outcomes are validation benchmarks. Calibrate the underlying
physical and economic drivers—final demands, initial stocks, resource
availability, yields, efficiencies, costs and lifetimes—so the model
reproduces reality endogenously.

If the model does not reproduce an observed outcome, identify the incorrect
or missing driver, parameter, mapping or equation. Do not add an activity
target, equality constraint, fixed share, `TAL`/`TAU` bound or temporary
calibration window to force the observed result.

A constraint is permitted only when the constrained quantity is itself a
genuine exogenous final demand or a continuing physical, legal or resource
constraint—not because its historical outcome is known.

When a user request appears to violate this rule, stop before editing the
model and alert the user explicitly. Explain which endogenous outcome would
be forced, why that would conceal a likely calibration or formulation error,
and which underlying physical or economic drivers should be investigated
instead. Continue only after the request has been reformulated consistently
with this rule, or the user establishes that the quantity is genuinely
exogenous or a continuing real-world constraint.

## Useful resources

- Consult the [OSeMOSYS model documentation](https://osemosys.readthedocs.io/en/latest/manual/Introduction.html) when model concepts, equations, parameters, or constraints need clarification.
- Consult the [OSeMOSYS/MUIO model code](https://github.com/OSeMOSYS/MUIO) when implementation details or the upstream model formulation need clarification.

## Required equation-first design gate

Before editing source parameters or attempting a full solve:

1. State the intended physical behavior and classify every observation as an
   initial stock, final demand, continuing real-world constraint, or
   benchmark-only value.
2. Inspect the active local solver formulation and MUIO generation,
   preprocessing and export code. Map every proposed parameter to the exact
   source file, equation, generated representation and expected effect.
3. Classify affected technologies explicitly as physical stocks,
   pass-throughs, conversions, accounting devices, backstops or demands.
   Never assign physical behavior from a technology-name prefix alone.
4. Use lossless source or full-precision solver values for numerical
   initialization. Rounded display CSVs may be cross-checks, not authoritative
   inputs when more precise evidence exists.
5. Build deterministic checks for initial-year capacity and commodity
   balances and for every-year, every-timeslice stock/vintage/service
   envelopes. Include survival and replacement of endogenous vintages.
6. Identify the latest verifiable unchanged canonical result, define one
   minimal candidate, record the last known-good runtime, and budget one new
   candidate optimization by default.

Do not use a full optimizer to discover a deterministic contradiction. Do not
try alternative formulations until the failed equation, indices and source
inputs are identified.

## Calibration constraints

- Do not reproduce observed activity with `TAL`, `TAU`, fuel shares or
  dispatch shares by default. Use observations as initial conditions, final
  demands or validation benchmarks according to their physical meaning.
- Do not add a constraint that expires after an arbitrary calibration window.
  Use a sourced full-horizon physical dynamic or leave the outcome endogenous.
- Distinguish capacity turnover from utilization. Stock and lifetime
  assumptions can limit replacement speed but do not guarantee smooth
  dispatch among available technologies.
- Treat per-technology and aggregate investment limits as different
  formulations. Document market interpretation, possible over-allowance,
  matrix coupling and solve-time evidence.

## Python environment

- Use MUIOGO's existing virtual environment at `.venv` for validators and
  repository tooling.
- Before a validator that imports PyYAML (`yaml`), run an `import yaml`
  preflight with `.venv/bin/python`. If it fails, treat it as an environment
  dependency issue: repair the declared environment with approval or expose
  only an isolated disposable PyYAML package path. Do not put another
  project's entire `site-packages` directory on `PYTHONPATH`.
- Do not report a missing interpreter dependency as a validator, skill or
  model failure.

## Source of truth

- Make permanent model changes only in the case's source parameter files. Examples include `RYC.json` for demand, `RYT.json` for capacity limits, `RYTM.json` for costs, and the appropriate `RY*.json` file for other parameters.
- Make structural changes, such as adding technologies or commodities, in `genData.json` and pass them through the application's `UpdateCase` workflow so all parameter JSON files are regenerated while existing values are preserved.
- Never make a permanent change directly in generated solver files such as `data.txt`, `data_processed.txt`, or an LP file. Such a change is not reproducible from the application and must not be promoted as a model fix.

## Solve-economy rule

Use the minimum number of optimizer runs needed to establish the result. An
optimizer run means any full, bounded, presolve-only or otherwise truncated
CBC/GLPK optimization; generation, preprocessing, `glpsol --check` and
source/hash validation are not optimizer runs.

For a source-parameter change, the default budget is one new optimization: the
disposable candidate solve. Do not rerun an unchanged control when an existing
canonical result can be verified against the pre-change source. Do not rerun
the promoted live case when its source and regenerated solver input are
byte-identical to the solved candidate.

Before launching any additional optimization, state:

1. which unresolved question it answers;
2. why deterministic checks or existing results cannot answer it; and
3. whether the additional run is required or merely desirable.

Do not run an additional optimization merely to repeat an already established
result in another directory.

## Parallel simulation rule

When two or more independent CBC optimizations are required, run them
concurrently when sufficient CPU and memory are available. CBC uses one CPU
core per solve, so a moderate increase in each run's duration is acceptable
when parallel execution reduces total wall-clock time.

Before parallel execution, distinguish:

- **Top-level cases**: separate directories under `WebAPP/DataStorage/`.
  These may run end-to-end concurrently because their `res/` and `view/`
  directories are isolated.
- **Case runs**: distinct scenario or configuration runs stored under the same
  top-level case/version. Their solver artifacts are isolated under
  `res/<caserun>/`, but their viewer outputs share files under `view/`.

For multiple case runs within one top-level case:

1. Generate each run's inputs separately and verify its run identity.
2. Run preprocessing, LP generation and CBC optimization concurrently using
   distinct `res/<caserun>/` directories and independent `DataFile` instances
   or processes.
3. Never use the same case-run name for concurrent processes.
4. Run-specific CSV extraction may proceed concurrently, but do not generate
   shared viewer JSON concurrently. After the solves finish, update viewer
   files sequentially, or protect them with a reliable lock and atomic writes.
5. Verify that every expected case-run key remains present in the shared
   viewer JSON after post-processing.

Treat run-specific artifacts as the authoritative simulation record:

- `res/<caserun>/results.txt`;
- `res/<caserun>/csv/*.csv`;
- solver logs and status; and
- `data.txt`, `data_processed.txt` and `lp.lp`.

Files under `view/*.json` are shared UI caches. Do not use them as the sole
evidence for reported simulation results.

Parallel execution does not authorize additional optimizer runs. Continue to
follow the solve-economy rule and reuse a verified canonical baseline instead
of recomputing it. If exact solver-runtime benchmarking is the objective,
control or disclose concurrent resource contention.

## Required validation chain

1. Identify the latest valid canonical pre-change result. Verify its case,
   scenario, source identity, generated-data identity, solver status and
   timestamp from retained manifests or run records. Use it as the unchanged
   baseline; do not rerun it by default.
2. Work on a disposable copy of the case. Do not overwrite the live case's
   `res/` outputs while testing. Run the deterministic design checks and stop
   on any unexplained shortfall,
   ID mismatch, unintended activity bound, negative stock or source-diff
   violation.
3. Generate and preprocess the disposable candidate through the same
   application path used by the UI: call
   `DataFile(case).generateDatafile(run)` and then `.preprocessData()`.
4. Inspect the generated data and derived sets to confirm that the source edits
   survived export and that mappings such as `MODEperTECHNOLOGY` were built
   correctly. Run `glpsol --check` to validate the matrix and emit the LP;
   inspect its dimensions without launching a separate bounded optimization.
5. Run one full candidate optimization through CBC within the declared runtime
   budget. Compare it with the verified existing baseline. At minimum, check
   solver status, objective value and percentage change, runtime, matrix size,
   the specifically affected activities/capacities/emissions, relevant
   constraint residuals and duals, adjacent-year changes, and unexpected
   changes elsewhere.
6. Verify result timestamps and case/version identity so stale or mismatched
   outputs are never treated as results of the new inputs.
7. Promote only the validated source files. After promotion, verify that the
   promoted source is byte-identical to the solved candidate; regenerate and
   preprocess the live solver input; verify that live `data.txt` is
   byte-identical to the candidate input; and run `glpsol --check`.
8. If the promoted source and regenerated solver input are byte-identical,
   treat the disposable candidate solve as the validated live result. Do not
   solve again, and do not copy disposable runtime results into the live case.
9. An additional control or post-promotion optimization is permitted only when:
   - no trustworthy pre-change result can be matched to its source;
   - promoted source or generated solver input differs from the solved
     candidate;
   - application generation is nondeterministic in a result-relevant way;
   - the change modifies model equations, scenario activation, structural
     sets, preprocessing or solver configuration;
   - the candidate result is numerically unstable or otherwise suspect; or
   - the user explicitly requests replication or sensitivity runs.
10. Record every optimizer run, its purpose and why it was necessary. Report
    generation/check-only executions separately from optimizer runs.

## Diagnostic exception

- A generated file may be modified only inside a disposable test area for a narrowly scoped A/B diagnosis, such as isolating a constraint responsible for infeasibility or poor solver performance.
- Clearly label this as a diagnostic experiment. A diagnostic optimizer run is
  an explicitly justified exception to the one-run default. Reproduce any
  accepted remedy in the source parameter files, then use the resulting source
  candidate for the one final application-generation and solve chain before
  treating it as a model change.

## Solve-time regression triage

- Treat a sudden solve-time regression as an incident. Inspect the latest source-parameter diff first, then test the smallest plausible rollback in a disposable copy before designing a new formulation.
- A previously validated canonical run is the preferred unchanged control.
  Recomputing it is not an A/B requirement when source and run identity can be
  verified.
- Use one verified unchanged control and one minimal A/B variant. Use the last
  known-good runtime as the initial time budget; stop a regressed run after
  roughly twice that runtime unless its solver log shows credible convergence.
- When the minimal rollback restores an optimal solve, stabilize the case with that rollback and complete the required validation chain. Investigate ways to recover optional calibration detail as separate follow-up work.
- Treat identical positive activity bounds (`TAL = TAU`) as a high-risk calibration technique in CBC. They are mathematically valid, but every new use requires a dedicated solve-time A/B test against the unpinned case.
- Treat large user-defined constraint families and cross-technology coupling as
  formulation changes. Require a matrix-size and runtime A/B before promotion.
- Do not run a long sequence of alternative formulations during incident recovery unless the user explicitly prioritizes preserving the disputed formulation over restoring a working solve.

## Reporting

- Document every model change in the affected case's `MODEL_FIXES*.md` file before considering the work complete. If the case does not yet have one, create it using the case's existing naming convention.
- Each entry must record the reason for the change, the source files and parameters changed, the before/after formulation or values, the generated artifacts and baseline inspected, the validation results, and any incomplete checks or known limitations.
- A promoted source-only change is fully validated when its disposable
  candidate has completed the normal generation, preprocessing, matrix and CBC
  chain; it has been compared with a verified canonical baseline; and the
  promoted source plus regenerated solver input are byte-identical to that
  solved candidate. A second CBC solve of the live copy is not required.
- Report exactly which checks passed, failed, timed out, or were not run.
- Preserve an audit trail of the source files changed, generated artifacts inspected, baseline used, and material result differences.

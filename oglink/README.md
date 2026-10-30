# oglink — MUIOGO's OG-CLEWS linker

Couples a solved CLEWS case into an OG-Core country model: it reads the CLEWS results, turns the
electricity price and related signals into OG-Core inputs, runs the country model, and writes the
macroeconomic result as data (a macro table, a results file and a run record).

## How it runs

The linker is part of MUIOGO and needs no separate installation. It runs with MUIOGO's own Python, as
a separate process: MUIOGO's web app never imports it. The linker in turn launches each OG country
model in that model's own environment and gives it this folder's source for the length of the run.
Nothing is installed into the country model's environment.

`GET /oglink/status?deep=1` reports whether the linker can run and lists the OG country models it can
see. It reads them from MUIOGO's installed-model register, so a model installed from MUIOGO's OG tab
appears without extra steps.

## Use

- **From MUIOGO:** a case with `<case>/oglink/hook.json` runs the linker after each CLEWS solve and
  records the OG result with the case.
- **By hand**, from this folder with MUIOGO's Python:
  `python -m oglink run coupled --country phl --clews-base <base csv dir> --clews-reform <reform csv dir> --out <dir>`

## Apply demand feedback to CLEWS

After the forward run, build and inspect its absolute demand patch:

```bash
python -m oglink writeback --run ./runs/coupled --country phl \
  --case "<case>" --base-caserun "<reform run>" --dry-run
```

Remove `--dry-run` to post the patch to the running app at `http://127.0.0.1:5000`.
Use `--muiogo-url` for another address. The app copies the case before applying and solving;
the linker writes only `clews_patch.json` in the OG run directory. This command performs one
reverse pass; it does not start an iterative coupling loop.

`--base-caserun` names the caserun to **clone**, which must be the forward manifest's CLEWS
**reform** caserun. This preserves the policies that produced the macroeconomic response.
It defaults to `$OGLINK_CLEWS_REFORM_RUN`; `--case` defaults to `$OGLINK_CLEWS_CASE`.
The CLI reads `oglink_manifest.json` and checks its country, UN code and absolute reform path.
It also checks feedback region, source fuel, activity driver and index against the configured
country and recorded concordance. Relative or unidentified legacy manifests must be corrected
from their verified provenance before use. Matching paths establish identity, not freshness:
this command does not verify retained source/result hashes or detect edits made later in place.

Demand is scaled after resolving parameter defaults and active scenarios in the caserun's stored
order. Null cells inherit; explicit zeros override. Changes are written into the last active
scenario so later layers cannot hide them. `--scenario`, when given, must name that final layer.
No forecast-year overlap is an error. Valid unchanged feedback returns successfully without a
request, case copy or solve.

For a custom country, pass the same `--countries <file>` used by the forward run. Configure
`demand_commodity` as the load-carrying final-demand code. The feedback's `CLEWS_FUEL` is checked
against `electricity_fuel`, the source/price-facing code; these codes can differ. The bundled
Philippines mapping is `PHL_HOU_ELE` to `PHL_HOU_ELEF`. The current MUIOGO exporter supports
writeback for region `RE1`. Feedback accepts one series using the recorded energy concordance;
an unrecorded index override is rejected.

`--with-emissions-penalty` also applies the validated `EmissionsPenalty.csv` for the configured
region/species. Unchanged penalties are suppressed against effective case values. Discount-rate
feedback is recorded under `deferred`, since the endpoint cannot express region-level parameters.
Demand and emissions feedback CSVs retain full floating-point precision for subsequent model input.

## Tests

From this folder, with MUIOGO's Python: `python -m pytest`

From the repository root, run `PYTHONPATH=oglink .venv/bin/python -m pytest oglink/tests`
for linker tests and `.venv/bin/python -m pytest tests/test_oglink_writeback.py` for CLI/HTTP/export
integration. The integration tests use temporary cases and stub the optimizer. Their matrix
check runs `glpsol --check` only and skips when GLPK is unavailable.

This package came from the research repository ogclews-link (branch `experiment/v18-gold-coupled`,
commit `ee92c9b`). New work on the linker happens here.

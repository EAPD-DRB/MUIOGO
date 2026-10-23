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

## Tests

From this folder, with MUIOGO's Python: `python -m pytest`

This package came from the research repository ogclews-link (branch `experiment/v18-gold-coupled`,
commit `ee92c9b`). New work on the linker happens here.

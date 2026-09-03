# oglink — OG-CLEWS linker (Bridge A)

The coupling engine that reads a solved CLEWS case and runs OG-Core's macro model on it, in a **separate
environment** from both models. Installable, not wired into MUIOGO by default. This is PR-1: the forward
pass (CLEWS → OG), reproducing the reference PHL `coupled` steady-state output effect (Y_ss ≈ −0.138%).

## Environment isolation (important)

The link imports **numpy/pandas only** — never `ogcore`, never a country package, never the Flask app. It
drives the OG model in that model's **own interpreter** as a subprocess, passing files across the boundary
(JSON overrides in, `.npz` solutions out; no pickle, no ogcore object ever crosses).

To keep that isolation intact, `oglink` is installed into **both** environments and the OG subprocess imports
it from its **own** site-packages (there is no `PYTHONPATH` injection — that would let the OG solve import the
link env's numpy, defeating the separation):

```bash
# 1. the link env (numpy/pandas only)
pip install -e ./oglink

# 2. each OG model's env (already has ogcore/distributed/cloudpickle; oglink's deps are unpinned so this
#    never perturbs that env's numpy)
<OG-PHL venv python> -m pip install -e ./oglink
```

## Register an OG model, point at CLEWS, run

```bash
# register the OG model's checkout (its .venv is probed for the interpreter)
oglink models register --path <OG-PHL checkout> --key og-phl

# run the coupled forward pass; CLEWS dirs come from the MUIOGO install or explicit flags
oglink run coupled --country phl \
  --clews-base   "<MUIOGO>/WebAPP/DataStorage/<case>/res/<base>/csv" \
  --clews-reform "<MUIOGO>/WebAPP/DataStorage/<case>/res/<reform>/csv" \
  --out ./runs
```

Outputs land under `./runs/coupled/`: `macro_table.csv` (the Y/C/K/L/r/w % differences, incl. the SS row),
`oglink_manifest.json` (self-describing provenance), and any CLEWS-side emit artifacts.

MUIOGO discovery is automatic where possible: when `oglink` is nested inside a MUIOGO checkout it finds the
CLEWS `DataStorage` and the installed-OG registry without configuration; `$OGLINK_MUIOGO_HOME` /
`$OGLINK_CLEWS_*` override.

## Tests

```bash
pytest              # fast unit suite (synthetic fixtures; no ogcore, no solve)
pytest -m slow      # the acceptance gate: reproduce PHL coupled Y_ss ≈ −0.138% (needs a registered OG-PHL)
```

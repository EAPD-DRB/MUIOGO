# Data the health channel needs

The health channel applies pollution mortality via the **disease_pop method** from
DeBacker, Evans & LaFleur, *The Macroeconomic Returns to Public Health Investments*
(the `CostOfDisease` repo): an age-specific shock `rho(s,t) = rho0 + kappa·g_t·h(s)`,
phased in, then the population is recomputed. Two inputs come from data:

- The emissions→deaths dose-response multiplier **ships with the repo** (`M = 0.082` for the
  Philippines, in `oglink/data/pm25_health.json`) — nothing to do.
- The GBD burden CSV **ships with the repo** at `IHME-GBD_2023_DATA/IHME-GBD_2023_DATA-a20a92ea-1.csv` —
  nothing to do on a fresh clone. §1 below documents its provenance and how to refresh it if a newer
  GBD round is needed.

## 1. The age profile h(s) — IHME GBD (included; provenance + refresh recipe)

Already on disk at `IHME-GBD_2023_DATA/` in the repo root (one multi-country CSV covers PHL +
IDN/ZAF/ETH). To refresh it or pull a newer GBD round, download from the IHME GBD Results tool as
below and replace the export in place.

- Portal: https://vizhub.healthdata.org/gbd-results/
- GBD round: **GBD 2023** (to match the HIV extract used in CostOfDisease)
- Context/hierarchy: **Risk** (deaths attributable to a risk factor)
- Risk (rei): **Ambient particulate matter pollution** (`rei_id 86`)
- Cause: **All causes** (`cause_id 294`)
- Location: **Philippines** (`location_id 16`)
- Sex: **Both** (`sex_id 3`)
- Measure: **Deaths** (`measure_id 1`); Metric: pull **both Rate** (`metric_id 3`, per 100,000 —
  gives the age shape `h(s)`) **and Number** (`metric_id 1` — gives the total attributable deaths,
  i.e. the `disease_pop` `excess_deaths` target). One export yields both inputs.
- Age: the fine bins `<1 year`, `12-23 months`, `2-4 years`, then 5-year groups `5-9`…`90-94`, and `95+ years`
  (the `Number` total can also come from the `All ages` row)
- Year: latest available

Save the CSV, then build BOTH the age shape and the total (same logic as the HIV builder):

```python
from oglink import health_profile
kw = dict(location_name="Philippines", year=2023,
          key_col="rei_name", key_value="Ambient particulate matter pollution")
h = health_profile.build_profile_from_gbd("<path>/IHME-GBD_pm25_PHL.csv", **kw)   # age shape h(s), peak 1
excess = health_profile.total_deaths_from_gbd("<path>/IHME-GBD_pm25_PHL.csv", **kw)  # total deaths = excess_deaths target
# then run the health channel with this profile + excess_deaths target (both GBD-sourced).
```

(A GBD *risk* export keys on `rei_name`, not `cause_name` — both readers handle that via `key_col`.
The readers are tested against the real HIV/SA export in `tests/test_channels.py`, so they are proven
before the PHL CSV arrives.)

## 2. The dose-response and morbidity magnitudes

- **Mortality total — now GBD-sourceable directly.** The `excess_deaths` target (how many PHL deaths
  the cleaner CLEWS reform avoids) can be read straight from the GBD `Number` export above via
  `total_deaths_from_gbd`, then scaled by the *fraction* of ambient-PM2.5 emissions the reform removes
  (the CLEWS base→reform PM2.5 change). That replaces the old placeholder `kappa`: the magnitude is
  GBD-anchored, and `disease_pop` solves the per-age `shock_scale` to hit it. (A finer version derives
  the deaths change from the PM2.5 concentration-response / IER rather than scaling the GBD total
  linearly — a refinement, not a blocker.)
- `morbidity_response` (emissions change → effective-labor `e` productivity shift): placeholder
  MAGNITUDE. CostOfDisease builds its labor wedge from absenteeism/impairment studies (ILO, Keogh
  et al.); the pollution analogue would use working-age morbidity (e.g. low-birthweight,
  cardiopulmonary work-loss).
- `morbidity_profile` (the AGE DISTRIBUTION of that productivity shift) — the channel now accepts a
  per-age shape for the morbidity effect, exactly as the mortality effect takes `h(s)`. Default is
  uniform ("all active ages gain equally"); `health_profile.working_age_profile` gives an illustrative
  prime-age-concentrated shape. A real shape needs GBD **YLD/DALY-by-age** for the relevant pollution
  outcomes (a separate pull from the mortality `Deaths` export above), not yet on disk.

## Caveat carried from the HIV study

In CostOfDisease ~98% of the GDP loss came from mortality — but that is because HIV kills
**working-age** adults. Ambient PM2.5 deaths skew **elderly**, who are mostly out of the
workforce, so expect the mortality→GDP channel to be **weaker** and the working-age
morbidity/productivity channel to matter relatively more. Do not carry over the 98% result.

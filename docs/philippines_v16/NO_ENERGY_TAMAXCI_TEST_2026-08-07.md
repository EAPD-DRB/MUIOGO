# Philippines v16 — BASE with all energy-sector TAMaxCI removed

Date: 2026-08-07. Disposable sensitivity, not a model change.

## What was tested

`TotalAnnualMaxCapacityInvestment` (`TAMaxCI`) is the per-year upper bound on
`NewCapacity`. It appears in `model.v.5.4.txt` exactly once, as
`NCC1_TotalAnnualMaxNewCapacityConstraint`, so removing it is a pure relaxation
of the feasible set and the objective can only fall.

The BASE scenario of `Philippines_v16` carries 95 non-default `TAMaxCI` rows.
93 are energy-sector and were reset to the parameter default 999999. The two
left in place are the `ENV_LAND` and `ENV_WATER` accounting terminals, which are
land/water bookkeeping rather than energy; `ENV_LAND` is additionally pinned by
the Tag-1 `BAL_ENV_LAND` constraint.

What the 93 bounds were:

| block | rows | nature of the bound |
| --- | --- | --- |
| `PHL_TRA_*` | 37 | v14 stock-turnover adoption envelope, all 34 years |
| `PHL_INDU_*` | 14 | same |
| `PHL_SER_*` | 6 | same |
| `PHL_HOU_*` | 5 | same |
| `PHL_AGR_*` | 6 | 5 envelopes plus one 2020 build ban |
| `PHL_POW_*` | 25 | 19 are a 2020-only build ban; 6 add a committed 2021-2025 pipeline and nothing after 2025 |

31 of the 93 bind somewhere in BASE (551 tech-year bindings, read from the
`NCC1` duals). The largest are liquid-fuel freight and aviation, industrial
coal heat, and coal cooking.

## Reproduction

```bash
python3 scripts/create_philippines_v16_no_energy_tamaxci.py
python3 scripts/run_philippines_v16_no_energy_tamaxci.py
python3 scripts/compare_philippines_v16_no_energy_tamaxci.py \
  --out docs/philippines_v16/no_energy_tamaxci_comparison.json
```

The MUIO application chain needs pandas, which was unavailable in the execution
environment. The runner therefore copies the reference BASE
`data_processed.txt` and rewrites only the `TAMaxCI` block. This is exact, not
approximate: `DataFile.gen_RYT` emits a technology row only when some year
differs from the default, and `preprocessData` never parses `TAMaxCI`. Verified
after the fact — the two datafiles differ in exactly 93 lines, all of them the
deleted energy rows.

## Result

Both runs solve to CBC optimality.

| | BASE | no energy TAMaxCI | delta |
| --- | --- | --- | --- |
| objective | 369,729,190.46 | 368,021,984.62 | −1,707,205.84 (−0.462 %) |
| cumulative CO2e 2020-2053 (Mt) | 6,532.39 | 6,437.19 | −95.20 (−1.46 %) |
| cumulative PM2.5 2020-2053 (kt) | 4,394.40 | 4,329.04 | −65.37 (−1.49 %) |

Annual emissions reverse sign partway through the horizon.

| year | CO2e base | CO2e delta | PM2.5 base | PM2.5 delta |
| --- | --- | --- | --- | --- |
| 2020 | 118.05 | +13.79 | 95.60 | −23.61 |
| 2025 | 145.94 | +4.21 | 105.13 | −8.63 |
| 2030 | 155.03 | −1.36 | 117.66 | +0.60 |
| 2040 | 196.06 | −6.70 | 131.75 | +2.08 |
| 2053 | 273.83 | −7.42 | 167.38 | +2.59 |

## Structural changes

Every shift is toward coal and liquid fuels, and away from CCS, gas, hydrogen
and electrification.

- **Cooking (2020-2025 only).** Biomass cooking disappears immediately:
  `PHL_HOU_COOK_BIOM` −81.27 PJ in 2020, `PHL_HOU_COOK_COAL` +85.18 PJ. From
  2030 the two runs are identical, because BASE has already collapsed to
  all-coal cooking by then. The envelope only delayed the collapse.
- **Industrial heat (whole horizon).** `PHL_INDU_OTHHPH_COAL` +66 PJ (2020)
  rising to +111 PJ (2053), displacing `..._COAL_CCS` (−21 to −79 PJ),
  `..._NG` (−21 to −29 PJ) and `..._H2`. Low-temperature heat shows the same
  pattern and additionally drops `PHL_INDU_OTHLPH_ELE` by 22-61 PJ.
- **Freight transport (whole horizon).** `PHL_TRA_TRUL_LIQ` +9 PJ (2025) to
  +55 PJ (2053), displacing NG (−5 to −44 PJ), H2 (−4 to −12 PJ) and the small
  electric share. Heavy trucks mirror this.
- **Power sector shrinks.** Total generation falls 4.6 PJ (2020) to 58.9 PJ
  (2053) — 1.2 % to 4.2 % — because industry moved off electric heat.
  `PHL_POW_PP_SPV_T1` output drops 8.8 to 37.7 PJ and 6.9 GW of solar capacity
  is not built by 2053. `PHL_POW_PP_COAL` output drops 20 PJ in 2040.
- **Fuel supply.** Coal extraction +235 PJ in 2020; gas extraction −1.7 PJ
  (2020) to −287 PJ (2053); biofuel processing and blending +50 to +247 PJ; oil
  imports −112 PJ in 2020.
- **Land: bit-identical.** Maximum absolute difference across every cluster,
  land-cover and water-supply technology, all 34 years, is exactly 0.
- **Water: near-identical.** Power-sector cooling withdrawal falls 0.14 to
  0.65 ×10⁹ m³ in step with the smaller thermal fleet. Irrigation swaps
  0.81 ×10⁹ m³ from surface to groundwater in 2053 only, which is marginal
  basis behaviour rather than a signal.
- **Agriculture energy and fisheries energy: unchanged in total.**

## Why the cost difference is not an energy-system result

The −1.7 M objective saving is dominated by rescheduling one technology's
capital spending, not by the mix changes above.

`PHL_TRA_SHIP_LIQ` accounts for 706.70 M of the 707.48 M model-period
`CapitalInvestment` in BASE — 99.9 % of all capital cost in the Philippines
model. Its annual investment runs at roughly 20-40 M per year on a fleet of
500-1,000 activity units, which is out of scale with every other technology by
three to four orders of magnitude. Removing its `TAMaxCI` lets the LP lump two
years of fleet renewal into one (2039 takes 1,213.5 units and 2040 takes none;
2049 takes 2,036.5 and 2050 takes none), moving 27.73 M of undiscounted capital
and giving up 4.54 M of discounted salvage.

No other technology's model-period cost moves by more than about 60 k. So the
cost figure reported above is a shipping-cost artifact, and the meaningful
output of this test is the emission and mix response, not the saving.

## Two pre-existing defects this test exposed

1. **Industrial CCS earns no emission credit.** CO2e is accounted at the
   fuel-processing gate (`PHL_PRO_PROC_COAL` 0.0953, `PROC_NG` 0.055,
   `PROC_OIL` 0.0733 Mt/PJ). Of the 29 technologies with a nonzero
   `EmissionActivityRatio`, the CCS entries are all power-sector
   (`PHL_POW_PP_COAL_CCS`, `PP_NGCC_CCS`, `PP_BIOM_CCS`, `BH2_NG`, `POW_DAC`).
   `PHL_INDU_OTHHPH_COAL_CCS` and `PHL_INDU_OTHHPH_NG_CCS` carry no CO2e factor
   at all. BASE therefore builds industrial coal-CCS for no climate benefit; it
   appears only because the `TAMaxCI` envelope capped unabated coal. Removing
   the cap deletes the CCS build and *lowers* CO2e, which is the wrong sign for
   the right reason.
2. **`PHL_HOU_COOK_OIL` carries a negative CO2e factor** (−0.0102 Mt/PJ) on top
   of its PM2.5 factor. A cooking device that removes CO2 from the atmosphere
   is a sign error.

## Interpretation

In BASE the stock-turnover `TAMaxCI` envelopes are the only thing holding back
coal and liquid fuels in end-use. There is no carbon constraint in BASE, no
emission price, and the fuel-cost data makes coal and oil products the cheapest
way to serve industrial heat, cooking and freight. The envelopes were doing the
work that a policy constraint should be doing. Anyone reading BASE's gradual
gas, hydrogen, electrification and CCS uptake as a model finding should know
that it is an artefact of the turnover bounds: remove them and the model goes
straight to coal and liquids in year one.

## Artifacts

- disposable case: `WebAPP/DataStorage/.Philippines_v16-no-energy-tamaxci`
  (gitignored, safe to delete)
- `no_energy_tamaxci_manifest.json` — the 93 cleared rows with their prior values
- `no_energy_tamaxci_run_summary.json` — solve status and datafile-surgery proof
- `docs/philippines_v16/no_energy_tamaxci_comparison.json` — full numeric diff

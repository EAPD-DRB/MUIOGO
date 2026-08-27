# Philippines v32 rice spatial-yield candidate

Date: 2026-08-27  
Parent: `Philippines_v31`  
Status: solved and validated with advisories; approved for promotion  
Promotion recommendation: eligible with a required forward irrigation follow-up

## Purpose and non-forcing classification

The v31 rice problem was an incorrect physical-production coefficient, not a
missing rice activity constraint. The model met all 2020 paddy demand with
1.505 million ha of irrigated rice, left rainfed rice unused, and assigned the
remaining 0.501 million ha of inherited irrigation service to vegetables and
maize. The active GAEZ-potential yield coefficients—9.36 to 12.91 t/ha-year
for irrigated rice—were too high for achieved Philippine production.

The evidence is classified as follows:

- 2020 paddy final demand remains the existing exogenous final demand in
  `RYC.json`.
- 2.006 million ha of inherited irrigation service remains the existing
  initial physical stock in `RYT.json`.
- PSA irrigated/rainfed production and harvested area are benchmark-only
  observations. They are not activity, production, share, `TAL`, or `TAU`
  constraints.
- The derived cluster yields are physical production coefficients. They are
  the only model parameter changed in this candidate.

No endogenous rice area, production split, irrigation allocation, water-source
share, or cluster allocation is forced.

## Equation and object mapping

`LNDAGRPHLC01` through `LNDAGRPHLC08` are land-conversion technologies. Rice
mode 11 converts annual land activity into rainfed paddy; mode 19 converts
annual land activity into irrigated paddy and uses irrigation service. Their
rice `OutputActivityRatio` values are therefore achieved annual production per
unit of physical land activity.

The source path is `RYTCM.json` -> `OAR`, scenario `SC_0`. MUIO exports those
values as `OutputActivityRatio` in each run's `data.txt` and
`data_processed.txt`. In `WebAPP/SOLVERs/model.v.5.4.txt`, the coefficient
multiplies `RateOfActivity` in the annual commodity-balance equations
`EBb4_EnergyBalanceEachYear4_ICR` and `EBb4_EnergyBalanceEachYear4`. Annual
technology activity is reconstructed by `AAC1_TotalAnnualTechnologyActivity`.

The expected effect was lower rice output per land unit while preserving the
eight-cluster ranking, so that the inherited irrigation stock and rainfed land
would compete endogenously to meet unchanged paddy demand.

## Source reconstruction and derivation

The missing CLEWs Global cell layer was reconstructed once and retained under
`data_sources/evidence/v32_rice_spatial_yield/`. The reconstruction uses CLEWs
GAEZ commit `30ec12e6524dc9c8ce474ffe1a467508f992007f`, the retained Philippines
configuration and patch, and all 92 raster sources named by the retained cache
manifest. It produced 3,457 cells and exactly reproduced both archived
eight-cluster summary tables. The adjusted national land total is 295,813.1
km2 and the maximum numeric difference from the archived summaries is 0.0.

Official PSA OpenSTAT 2020 annual palay production and harvested-area results
were preserved verbatim for irrigated and rainfed ecosystems. GADM 4.1
level-1 polygons were intersected with the recovered cells in EPSG:6933.
Within each province, observed production and harvested area were allocated
across clusters by intersected land share. This is an explicit spatial
allocation assumption, not an observed cluster-level crop survey.

The irrigated national harvested-to-physical-area factor is
`3,253,454.36 ha / 2,006,000 ha = 1.6218615952143568`. The resulting 2020
anchors retain genuine cluster differences:

- irrigated mode 19: 0.654821 to 0.760507 Mt per 1,000 km2, weighted mean
  0.7264090324;
- rainfed mode 11: 0.294087 to 0.398922 Mt per 1,000 km2, weighted mean
  0.3222980657.

The retained derivation reconstructs 14.57176519 Mt of irrigated production
and 4.72309035 Mt of rainfed production exactly. The full method, source URLs,
hashes, reusable script, cell GeoPackage, source query outputs, and allocation
ledgers are documented in
`data_sources/evidence/v32_rice_spatial_yield/README.md` and `manifest.json`.

## Source change

The only substantive source edit is `RYTCM.json`, `OAR`, `SC_0`:

- technologies: `LNDAGRPHLC01` through `LNDAGRPHLC08`;
- modes: 11 (rainfed rice) and 19 (irrigated rice);
- years: 2020 through 2053;
- changed numeric cells: 544.

Each cluster/regime receives its achieved 2020 anchor. Every later-year value
preserves the exact v31 year/2020 FOFA BAU ratio for the same cluster and
regime. The anchor-file SHA-256 is
`95fa0b66bb076aac45b21d0aa81669e840a4f054603b7a4afa6c144cdab85424`.

`RYC.json`, `RYTM.json`, `RYT.json`, all other parameter JSON files, crop
costs, irrigation fees, low-input modes, water ceilings, groundwater shares,
and all activity/capacity constraints are unchanged. The deterministic source
gate passed all checks, including all 16 anchors, all 544 future-path ratios,
unchanged non-target parameters, and no activity/share-constraint changes.

## Generation and matrix validation

Each canonical candidate run was generated with
`DataFile(case).generateDatafile(run)`, preprocessed with
`DataFile.preprocessData()`, and checked with `glpsol --check` before CBC. All
four matrices passed and exactly match the corresponding v31 dimensions:

| Scenario | Rows | Columns | Matrix nonzeros |
|---|---:|---:|---:|
| BASE | 467,075 | 517,844 | 8,194,641 |
| COAL_PHASEOUT | 467,090 | 517,844 | 8,194,911 |
| RE | 467,075 | 517,844 | 8,195,151 |
| EV | 467,075 | 517,844 | 8,194,949 |

Generated `data.txt`, `data_processed.txt`, `lp.lp`, matrix reports, solver
logs, `results.txt`, extracted CSVs, and optimization records are retained
under `res/<run>/`. Shared viewer JSON was not regenerated concurrently and
is not used as validation evidence.

## Optimizer inventory

Four optimizer runs were made: BASE first, followed by the three required
policy scenarios concurrently. There were no diagnostic, failed, truncated,
or duplicate optimizations.

| Scenario | Candidate objective | Change from v31 | CBC seconds | Runtime ratio |
|---|---:|---:|---:|---:|
| BASE | 838,560.9556 | +2.6674% | 66.16 | 0.891x |
| COAL_PHASEOUT | 854,467.8494 | +2.6164% | 130.41 | 1.316x |
| RE | 847,837.2695 | +2.6374% | 140.43 | 1.226x |
| EV | 815,538.1473 | +2.7448% | 140.43 | 1.234x |

All four runs terminated optimal. Policy-run wall times include concurrent CPU
contention and are not serial runtime benchmarks. The identical absolute
objective increase of about 21,786.6143 across scenarios is consistent with a
shared 2020 rice-account correction rather than a policy-specific interaction.

## BASE outcome and benchmark validation

| 2020 quantity | v31 | v32 candidate | Benchmark |
|---|---:|---:|---:|
| Irrigated rice area, Mha | 1.505 | 2.006 | 2.006 |
| Rainfed rice area, Mha | 0.000 | 1.045 | 1.465 |
| Total rice area, Mha | 1.505 | 3.051 | 3.471 |
| Irrigated production, Mt | 19.295 | 15.256 | 14.572 |
| Rainfed production, Mt | 0.000 | 4.039 | 4.723 |
| Total production, Mt | 19.295 | 19.295 | 19.295 demand |
| Irrigation-service use, Mha | 2.006 | 2.006 | 2.006 inherited stock |
| Surface withdrawal, km3 | 46.455 | 58.220 | 39–71 predicted range |
| Groundwater withdrawal, km3 | 0.000 | 0.000 | benchmark-only advisory |

The candidate reproduces irrigated area to 0.00002%, irrigated production to
4.69%, rainfed production to -14.48%, total rice area to -12.12%, and total
production to numerical tolerance. Rainfed area remains 28.71% below the
benchmark. Rice uses all inherited irrigation service, while irrigated
vegetable and maize activity falls from 0.501 Mha to zero. Active rice remains
concentrated in clusters 5 and 7, but that ranking now follows the derived
achieved-yield evidence rather than the former GAEZ potential-yield spread.

The same 2020 rice and water result appears in BASE, COAL_PHASEOUT, RE, and EV.
No 2020 activity outside the affected land/agriculture/water family differs by
more than 0.01; smaller paired differences are numerical or degenerate
substitutions. All four scenario gates pass with advisories.

## Accepted forward-horizon advisory

The correction works in the inherited-stock year but exposes a separate
forward calibration gap. In every scenario the optimizer expands irrigation
service from 2.006 Mha in 2020 to 2.560 Mha in 2021—about 0.554 Mha of immediate
new capacity—and rainfed rice returns to zero. Irrigated rice supplies all
19.580 Mt in 2021.

This is not caused by the new yield anchors alone. The inherited irrigation
technology has residual capacity 20.06, capital cost 604.5949214, zero fixed
cost, variable cost 0.6091371, no annual-addition ceiling after 2020
(`TAMaxCI = 999999`), and no binding total-capacity ceiling. Once investment is
allowed, new irrigation is economically preferred to continued rainfed rice.

No arbitrary capacity cap, rice-share target, or temporary calibration bound
has been added. A follow-up must establish a sourced continuing irrigation
deployment/build-rate constraint or correct physical/economic investment
drivers such as capital cost, fixed cost, lifetime, or service mapping. The
observed 2020 stock by itself does not justify constraining future endogenous
irrigated area.

## Final disposition

The spatial-yield reconstruction, source candidate, generated matrices, and
four optimal scenario results are retained and fully documented. The user
accepted the 2021 irrigation expansion as a high-priority follow-up rather than
a release blocker because v32 materially repairs the 2020 rice allocation
without forcing it. The candidate is eligible for content-preserving sealing
and promotion as `Philippines_v32`; no regeneration or optimizer run is
permitted during promotion. `Philippines_v31` remains the parent and rollback
case.

Machine-readable evidence:

- `preflight_rice_spatial_yield_v32.json` — deterministic source gate;
- `rice_spatial_yield_source_change_v32.json` — complete 544-cell audit;
- `rice_spatial_yield_base_validation_v32.json` — BASE reconstruction gate;
- `rice_spatial_yield_four_scenario_validation_v32.json` — four-scenario
  comparison and hold recommendation;
- `rice_spatial_yield_candidate_status_v32.json` — concise disposition.

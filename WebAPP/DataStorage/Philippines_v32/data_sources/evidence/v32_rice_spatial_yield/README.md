# Philippines rice spatial-yield reconstruction (2026-08-27)

This directory preserves the recovered cell-level CLEWs Global/GeoCLEWs
cluster result and every derived input needed to reproduce the proposed rice
yield coefficients without rerunning the 92-raster workflow.

## What was recovered

The workflow was reconstructed from the Philippines inherited build snapshot:

- CLEWs GAEZ commit `30ec12e6524dc9c8ce474ffe1a467508f992007f`;
- the retained Philippines `config.yaml`, crop-code override, GADM 4.1 level-0
  boundary, raster manifest, and `CLEWs_GAEZ_changes.patch`;
- all 92 source rasters identified by the retained cache manifest.

The regenerated `PHL_LandCover_byCluster_summary.csv` and
`PHL_Parameter_byCluster_summary.csv` match the archived summaries cell for
cell after CSV parsing: same 8 x 75 parameter table, same 8-cluster land table,
and maximum absolute numeric difference `0.0`. The national adjusted land
total is `295813.1 km2`.

`reconstructed_geospatial/PHL_clustered_cells.gpkg` is the missing 3,457-cell
cluster layer. It is retained locally so this reconstruction does not need to
be repeated.

## Rice mapping

Official PSA OpenSTAT 2020 annual palay production and harvested area were
queried separately for irrigated and rainfed ecosystems at province level.
The exact query results are under `psa_openstat/`.

GADM 4.1 level-1 polygons were intersected with the recovered CLEWs cells in
EPSG:6933. Within each province, the intersected cell land was normalized into
cluster shares. Provincial production and harvested area were allocated by
those shares, then summed by cluster and water regime. This is a transparent
spatial allocation assumption; the resulting cluster values are achieved
yield coefficients, not GAEZ potential-yield coefficients.

For rainfed rice, modeled annual physical area equals the observed harvested
area proxy. For irrigated rice, the national harvested-to-physical-area ratio
is applied uniformly across clusters:

`3,253,454.36 harvested ha / 2,006,000 physical ha = 1.6218615952143568`.

This preserves the model's annual-physical-hectare convention without
inventing province-specific cropping intensities. The arithmetic reconstructs:

- irrigated: `14.57176519 Mt`, `20.06` thousand km2, weighted OAR
  `0.7264090324027915 Mt/1000 km2`;
- rainfed: `4.72309035 Mt`, `14.6544173` thousand km2, weighted OAR
  `0.32229806571701763 Mt/1000 km2`.

These area and production values remain benchmark-only. No activity, share,
production, irrigation-use, `TAL`, or `TAU` constraint is created.

## Files

- `reconstructed_geospatial/PHL_clustered_cells.gpkg`: recovered cell layer.
- `reconstructed_geospatial/*_summary.csv`: exact regenerated cluster tables.
- `psa_openstat/*.csv`: exact 2020 official query outputs.
- `derived/phl_rice_province_cluster_allocation_2020.csv`: complete
  province/regime/cluster allocation ledger.
- `derived/phl_rice_cluster_yields_2020.csv`: the 16 source OAR anchors and
  reconstruction checks.
- `derive_philippines_rice_cluster_yields.py`: reproducible derivation code.
- `manifest.json`: source locators, versions, hashes, and validation results.

The GADM level-1 archive itself is not copied here. Its official URL and exact
archive checksum are frozen in `manifest.json`; the retained derived
allocation ledger makes another geometry overlay unnecessary.


# Health-channel data and provenance

The health channel needs two separate country inputs:

- GBD 2023 ambient-PM2.5-attributable deaths and disability by age: the baseline burden and age profiles.
- The country's emissions-to-health multiplier in `oglink/data/pm25_health.json`: the energy-sector
  contribution to ambient PM2.5 multiplied by the approximate concentration-response elasticity.

The multiplier does not replace the burden CSV. The current channel stages a mortality shock and
changes effective labour from the reform's emissions change; it does not constrain CLEWS activity.

## Bundled country coverage

All bundled files describe 2023, Both sexes, All Population, and the risk **Ambient particulate matter
pollution** (`rei_id=86`). They contain Deaths and YLDs, with Number, Rate and Percent metrics.

| Country | CSV under `IHME-GBD_2023_DATA/` | Records | Multiplier |
| --- | --- | ---: | --- |
| Philippines | `IHME-GBD_2023_DATA-a2dc02fe-1.csv` | 1,118 | Present |
| Indonesia | `IHME-GBD_2023_DATA-IDN.csv` | 1,118 | Present |
| South Africa | `IHME-GBD_2023_DATA-ZAF.csv` | 1,118 | Present |
| Ethiopia | `IHME-GBD_2023_DATA-ETH.csv` | 1,118 | Present |
| Brazil | Deferred by user | — | Not yet calibrated |

Brazil is explicitly deferred at the user's request for this change. Its estimates exist in GBD 2023,
but a matching age-specific export has not yet been obtained. The official detailed-data endpoints
require an IHME sign-in. Aggregate or age-standardised published
Brazil totals cannot supply the missing age profiles or YLD inputs. No replacement country or
synthetic burden is used. A country without a matching default CSV takes the existing health-channel
skip path; this is not a validated estimate of zero health effects.

## Source of the recovered country extracts

Indonesia, South Africa and Ethiopia were recovered from the original linker's multi-country export:

- Repository: <https://github.com/marcelolafleur/ogclews-link>
- Revision: `4134763e00234cd499cd744b36e400888f228278`
- File: `IHME-GBD_2023_DATA/IHME-GBD_2023_DATA-a20a92ea-1.csv`
- Immutable source: <https://raw.githubusercontent.com/marcelolafleur/ogclews-link/4134763e00234cd499cd744b36e400888f228278/IHME-GBD_2023_DATA/IHME-GBD_2023_DATA-a20a92ea-1.csv>
- Source SHA-256: `81ce2033f8fa3f5479354d12d882651754d562f5f7c8294dff76eee113da7ab1`

Each new CSV retains the original header and original records byte-for-byte, selecting its country and
Deaths/YLDs measures. Numeric text and uncertainty bounds are not reformatted or rounded. The
Philippines CSV is unchanged: all its 1,118 records have identical values and uncertainty bounds in the
recovered export. File hashes and record counts are in `IHME-GBD_2023_DATA/sources.json`. The source
export's original citation is preserved in `citation.txt`.

## Refreshing or adding a country

Download from the [IHME GBD Results tool](https://vizhub.healthdata.org/gbd-results/), retaining the
citation and recording the export's provenance and hashes. Use these selections for a comparable file:

- GBD round and year: **GBD 2023 / 2023**.
- Context: **Risk**; risk: **Ambient particulate matter pollution** (`rei_id=86`).
- Population group: **All Population**; sex: **Both**.
- Location: the exact country's name, including **Brazil** for the outstanding extract.
- Measures: **Deaths** and **YLDs (Years Lived with Disability)**.
- Metrics: **Number** and **Rate**; Percent may also be retained.
- Causes: **All causes**, **Ischemic heart disease**, **Stroke**, **Chronic obstructive pulmonary
  disease**, and **Diabetes mellitus type 2**.
- Ages: `<1 year`, `12-23 months`, `2-4 years`, then five-year bins `5-9` through `90-94`, and `95+`.
  `All ages` may also be retained for totals. Do not substitute age-standardised rates for age-specific
  rates or sum overlapping summary age groups.

`CountryConfig.gbd_year` selects the observation year. Automatic file discovery requires a matching
country, year, population group, sex, risk and All-causes Deaths/Rate record. The readers subsequently
validate the mortality age support and morbidity inputs. Explicit `gbd_burden_csv` settings, including
`None`, override discovery. A new country's multiplier needs its own sourced calibration; the existing
fallback to a multiplier of 1.0 is approximate and produces a warning.

## Checks

From the repository root, with MUIOGO's Python and declared dependencies:

```sh
PYTHONPATH=oglink .venv/bin/python -m pytest -c oglink/pytest.ini oglink/tests
```

`test_health_data.py` checks all bundled country/year/risk identities, full-precision file hashes,
unique record keys, finite values and uncertainty bounds, disjoint mortality age-bin totals, mortality
and morbidity profiles, and the complete result-reading path from synthetic CLEWS emissions to real
country mortality and labour inputs. These checks do not launch an optimizer.

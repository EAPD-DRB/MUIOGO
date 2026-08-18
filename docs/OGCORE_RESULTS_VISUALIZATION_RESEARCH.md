# OG-Core Results visualization: research and v1 decision

Date: 2026-08-13
Prototype branch: `feature/og-results-visualization`

## Decision

Build a **guided analysis workspace**, not a generic pivot dashboard:

1. **Overview** — a small set of curated, defensible economic views.
2. **Explore** — freedom to select any output, comparison measure, compatible view, and model dimension.
3. **Tables** — OG-Core's own model-native analysis tables and downloadable data.

Use **Apache ECharts 6.1** as the v1 chart renderer, with MUIOGO-owned controls and accessible HTML tables. Keep **Perspective** as a phase-2 proof of concept for an optional advanced pivot/data-grid mode after a result metadata contract exists.

This is guided freedom: the economist controls the question, while the product prevents dimensionally meaningless charts.

“Any baseline with any reform” should mean any **compatible** completed pair. V1 keeps the pair inside the same case/run lineage, where provenance is known. Cross-case comparison should be enabled only when model version, calibration, dimensions, units, and result-manifest compatibility pass validation; otherwise the UI would make non-comparable runs look scientifically interchangeable.

## Evidence used

The decision is based on four sources rather than a feature-list comparison:

- The visualization meeting transcript, especially 13:00–16:30 and 20:23 onward.
- The current MUIOGO code and visual system.
- The actual completed Ethiopia baseline and reform outputs.
- Current official documentation and repositories for OG-Core, ECharts, Perspective, Vega-Lite, and Plotly.

The transcript sets these constraints:

- The existing proprietary visualization dependency cannot be reused.
- The replacement should be a clean break, not a visual clone.
- Defaults must improve; opening on an arbitrary or unreadable chart is unacceptable.
- Dense stacks with roughly 15 categories are specifically considered chart junk.
- Analytical capability must be preserved.
- The approach should be proved with OG-Core first and later reused for CLEWS.

## What the real run contains

The prototype reads the current completed run pair directly:

- Case: `Baseline 1`
- Country calibration: Ethiopia (`ETH`)
- Baseline: `baseline`
- Reform: `Base Reform`
- Run type: steady state only; there is no transition path in these runs.
- Recorded reform: `c_corp_share_of_assets` changes from the calibration default `0.55` to `0.351`.
- Both runs contain 69 steady-state outputs.

The output shapes are materially different:

| Shape | Examples | Natural economist view |
|---|---|---|
| Scalar | GDP, capital, labor, wage, interest rate, tax revenue | KPI, comparison bar, table |
| One value per lifetime-income group | some household and transfer outputs | horizontal bars or dot plot |
| Age × lifetime-income group (80 × 7) | household consumption, labor, savings, income, tax rates | heatmap, selected lifecycle profile, table |
| Industry vector/tensor | prices and industry outputs | bars now; heatmap/small multiples when multiple industries exist |
| Transition time × dimensions | absent in this run, supported by OG-Core | line, selected small multiples, time × category heatmap |

Important current results shown by the prototype include:

- GDP: `-0.83%`
- Aggregate consumption: `-1.16%`
- Capital: `-1.66%`
- Labor: `+0.30%`
- Wage: `-1.12%`
- Total tax revenue: `+4.26%`
- Business tax revenue: `+38.69%`
- Real interest rate: about `-0.04 percentage points`

The page explicitly labels the comparison as steady state. This avoids presenting long-run equilibria as a year-by-year forecast.

## Economist jobs the product must support

An economist normally arrives with one of five questions:

1. What changed overall?
2. Which mechanism or fiscal component explains the result?
3. Who gains or loses across age, income group, industry, region, or time?
4. Are the model results and diagnostics credible?
5. Can I obtain the exact values and reproduce/export my view?

A blank pivot designer makes the economist reconstruct basic model meaning before answering question 1. A fixed dashboard answers question 1 but blocks questions 2–5. The three-part design serves both modes.

## Why these Overview charts are defensible

### Long-run impact: zero-centred horizontal bars

GDP, consumption, investment, capital, labor, and wages are shown as signed percent changes from baseline.

- A common transformation makes different model-level scales comparable.
- The zero line makes direction unambiguous.
- Horizontal labels remain readable.
- Orange and blue encode direction, not a moral judgment that an increase is always good.

### Fiscal effects: ranked independent bars

Tax revenue and outlay components are ranked by absolute effect.

- This directly addresses the transcript's criticism of dense stacked bars.
- The components are changes, not necessarily shares of one total, so stacking would imply a relationship that may be false.
- Ranking makes the dominant mechanism immediately visible.

### Distribution: age × lifetime-income heatmap

Household consumption has 560 cells in the current run. A heatmap shows every cell without generating fourteen lines or eighty grouped bars.

- The diverging scale is centred at zero.
- Exact values remain available on hover and in the table.
- A selected cell can lead to a lifecycle profile in Explore.

### Lifecycle profile: two lines at a time

The selected lifetime-income group is shown with baseline and reform lines over age.

- Levels remain interpretable.
- Selecting one group avoids fourteen competing series.
- The economist can change outcome and group without rebuilding the chart.

### OG-Core-native tables

Macro steady state, inequality, Gini detail, and wealth moments are calculated by the installed OG-Core environment. They are not reimplemented in the browser.

This keeps the model package authoritative and avoids quietly diverging definitions.

## Chart compatibility rules

The engine should derive available views from declared dimensions, not expose a list of every chart ECharts can draw.

| Data semantics | Default | Allowed alternatives | Avoid |
|---|---|---|---|
| One scalar, two scenarios | comparison/KPI | table | pie, line |
| One categorical dimension | horizontal bar or dot | table | line unless categories are ordered |
| Baseline and reform by category | grouped bar or dumbbell | percent/difference bar, table | stack unless values are genuine parts of a total |
| Time or age | line | area when a meaningful magnitude/baseline exists | unordered bars for long paths |
| Age × income group | heatmap | selected profile, table | fourteen-line default, 3D surface |
| Time × category | selected lines, small multiples, or heatmap | table | all-category spaghetti line |
| Industry × time | heatmap or selected/top-N profiles | small multiples, table | giant stack |
| Composition that sums to a meaningful whole | 100% stack in limited cases | table | stack merely because categories exist |

Initial user-facing view vocabulary should stay small: **Table, Line/Profile, Bar/Comparison, Heatmap**. Scatter can be added once the explorer supports a genuine x-variable/y-variable question.

## Is pivoting required?

Not as the main v1 interaction.

The current data is not an arbitrary business table. It has known scientific dimensions: scenario, variable, time/age, lifetime-income group, and industry. A generic Rows/Columns/Values pivot:

- makes valid and invalid combinations look equally legitimate;
- loses the distinction between percent change, absolute difference, levels, and percentage-point change;
- cannot infer whether aggregation across age, income group, or industry is economically valid;
- makes the first-use experience resemble a tool-builder rather than an economic result;
- increases runtime, accessibility, theming, persistence, and testing surface before the semantic contract exists.

Pivoting becomes useful later for advanced users, especially when CLEWS adds more categorical dimensions. Perspective is a strong candidate for that isolated mode because its viewer supports grouping, splitting, filtering, aggregation, datagrid/chart plugins, and saved/restored configurations.

The gate for adding pivot is not library availability. It is a result manifest that tells the pivot engine which aggregations and transformations are legal.

## The prerequisite: a normalized result contract

The current endpoints can return real raw variables and official tables, which is enough for the proof of concept. Production needs a model-neutral result manifest.

Each variable should declare at least:

```json
{
  "id": "c",
  "label": "Household consumption",
  "description": "Consumption by model age and lifetime-income group",
  "category": "Households",
  "unit": "model units",
  "dimensions": ["age", "lifetime_income_group"],
  "comparison": "percent_change",
  "rate_display": null,
  "allowed_aggregations": [],
  "compatible_views": ["heatmap", "profile", "table"],
  "default_view": "heatmap"
}
```

The contract must preserve case-sensitive IDs. OG-Core outputs currently include both `C` and `c`; case-folding them would corrupt the catalog.

Suggested normalized long-form fields are:

```text
model, case, run, scenario, variable,
year, age, lifetime_income_group, industry,
value, unit, provenance
```

Baseline/reform levels should remain source values. Difference, percent difference, and percentage-point difference should be computed as typed comparison measures, not stored as unrelated variables.

For CLEWS, the same contract can add dimensions such as technology, fuel, region, emission, or scenario without replacing the visualization shell.

## Library decision

### Apache ECharts 6.1 — v1 recommendation

Why it fits this repository:

- Apache-2.0 open-source license.
- Plain JavaScript integration matches the current ES-module/jQuery application; no React rewrite is required.
- SVG and Canvas renderers.
- Strong line, bar, scatter, heatmap, dataset/transform, interaction, and export support.
- Enough visual control to look native to MUIOGO rather than like an embedded BI product.
- ARIA support exists, but must be deliberately enabled and verified.

Version 6.1.0 is vendored under `WebAPP/References/echarts` with its license and notice files. Results load the local bundle without a network dependency.

### Perspective 5.2 — phase-2 advanced Explore candidate

Perspective is the closest fit for a configurable pivot/data-grid experience. It is Apache-2.0 and its viewer can persist a complete configuration.

It is not the v1 page engine because it adds multiple packages, WebAssembly/runtime surface, an opinionated viewer, and a second chart system before MUIOGO has a semantic result manifest. A focused POC should test theming, accessibility, configuration migration, bundle/runtime cost, and embedding in the legacy shell.

### Vega-Lite 6.4 — strong specification layer, not the end-user UI

Vega-Lite's declarative grammar and statistical defaults are excellent for reproducible chart specifications and potentially for future AI-generated *view specifications*. It does not provide the economist-facing selection/pivot interface by itself, so MUIOGO would still build the controls and metadata logic.

### Plotly.js 3.7 — viable fallback, not the clean-break choice

Plotly is MIT licensed and MUIOGO already contains an older 2.27 bundle, making it the lowest short-term integration effort. It remains a chart engine rather than a semantic explorer, and the existing bundled version should not silently become the new foundation. If ECharts integration encounters a blocking compatibility issue, a separately tested Plotly upgrade is a reasonable fallback.

### License note

Apache-2.0, MIT, and BSD-3-Clause are permissive open-source licenses and do not depend on whether MUIOGO is commercial. Distribution still requires compliance with the applicable copyright, license, and NOTICE obligations. Dependency files and transitive licenses should be recorded even for a non-commercial project.

## Architecture

```text
OG-Core worker output
        |
        v
Results API + model adapter
        |
        +-- source arrays (baseline/reform)
        +-- typed variable/dimension manifest
        +-- OG-Core-native tables
        +-- run and parameter provenance
        |
        v
Model-neutral Results store
        |
        +-- Overview recipes ----> ECharts
        +-- Explore resolver -----> ECharts + HTML table
        +-- Analysis tables ------> accessible HTML table/export
        +-- later Advanced pivot -> Perspective POC
```

The visualization engine should accept trusted data and a validated declarative view configuration. It should never evaluate model-provided HTML, JavaScript formatters, URLs, or arbitrary regular expressions.

## Delivery plan

### Phase 1: professional steady-state result (current prototype direction)

- Result pair selector.
- Explicit steady-state/transition-path status.
- Policy parameter change provenance.
- Curated Overview.
- Dimension-aware Explore across all steady-state outputs.
- Official OG-Core tables.
- SVG export and saved local view.
- Keyboard, color, ARIA, and screen-reader review.

### Phase 1.5: productionize the data contract

- Add server-generated variable and dimension metadata.
- Move catalog labels/units/aggregation rules out of the frontend.
- Add stable view-configuration schema and migration version.
- Vendor the selected runtime and record licenses.
- Add CSV/data export from the normalized result set.

### Phase 2: transition paths

- Levels / absolute difference / percent difference / percentage-point difference.
- Time-range and category filters.
- Lines, selected small multiples, and time × category heatmaps.
- Revenue decomposition and time-series tables.

### Phase 3: CLEWS adapter and advanced analysis

- Map CLEWS dimensions into the same manifest.
- Reuse Overview/Explore/Tables shell and chart resolver.
- Evaluate Perspective behind an “Advanced table/pivot” boundary.
- Add saved/shareable views with schema-version migration.

## Main risks and controls

| Risk | Control |
|---|---|
| A flexible tool produces misleading charts | Dimension/measure compatibility resolver; curated defaults |
| Units and aggregation meaning are unknown | Server-generated typed manifest before broad pivoting |
| `C` and `c` collide | Preserve exact case-sensitive variable IDs |
| Steady state is mistaken for a forecast | Prominent run-scope label; no year axis without TPI data |
| Mixed rate semantics | Metadata-driven percentage-point vs percent-change display |
| Library becomes another proprietary-style lock-in | MUIOGO owns controls, view schema, and normalized store; chart adapter boundary |
| CDN/offline failure | Vendor pinned production assets and license notices |
| Large future CLEWS datasets | Server filtering/Arrow or Perspective evaluation; progressive chart rendering |
| Saved configurations break on upgrade | Version the MUIOGO view schema; do not persist raw library internals as the only format |
| Chart injection or unsafe export | Treat labels/config as untrusted; whitelist view properties and filenames |

## Acceptance criteria for the library decision

ECharts should remain the v1 choice if the production spike confirms:

1. The real steady-state and TPI shapes render without custom forks.
2. SVG charts meet MUIOGO visual and accessibility requirements.
3. Resize, export, tooltips, and keyboard behavior work in the existing shell.
4. The vendored bundle and license material are acceptable.
5. The MUIOGO view schema stays renderer-neutral.

Perspective should be added only if advanced users can complete representative pivot tasks materially faster than with the guided explorer, and only after the manifest can prevent invalid aggregations.

## Official references

- OG-Core output plots: <https://pslmodels.github.io/OG-Core/content/api/output_plots.html>
- OG-Core output tables: <https://pslmodels.github.io/OG-Core/content/api/output_tables.html>
- Apache ECharts: <https://github.com/apache/echarts>
- ECharts accessibility guidance: <https://echarts.apache.org/handbook/en/best-practices/aria/>
- Perspective: <https://perspective.finos.org/>
- Vega-Lite: <https://vega.github.io/vega-lite/>
- Plotly.js: <https://github.com/plotly/plotly.js>

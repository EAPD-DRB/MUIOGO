6. Read and export results
==========================

Use **Results** to inspect one completed run or compare a reform with its
baseline. Results must still match the saved inputs and country model.
The run list groups reforms under their baselines.

Open the example comparison
---------------------------

1. Click **Results** in the left menu.
2. Find ``ZAF tax example`` in the run list. Use **Filter runs...** if needed.
3. Find its ``CIT cut`` reform and click **Compare** on that row.
4. Check the title: it should name ``ZAF tax example`` and ``CIT cut``.
5. In **Report**, click **Policy**. Under **Policy changes**, check that only
   ``cit_rate`` differs, with the intended baseline and reform values.

**Check:** for the steady-state example, the analysis label says
**Long run (steady state) only**. The Summary shows changes from the baseline.
Do not read the reform's level as its change.

To inspect the baseline alone, click **View** on its row. **View** on a
reform row shows that reform on its own. Use **Compare** to measure its
policy effect against its linked baseline.

Choose runs and views
---------------------

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Control
     - What it does
   * - Filter runs...
     - Filters the run list by case, baseline or reform name. Clear it to see all rows.
   * - View
     - Opens current completed results for that run alone. A baseline does not need a reform to be viewed.
   * - Compare
     - Opens a reform and its linked baseline. Both need current completed results.
   * - Recent
     - Reopens an available run or comparison recently viewed in this browser and country workspace.
   * - Report
     - Shows the summary, policy changes when comparing, macroeconomy, government, households and main results table.
   * - Explore data
     - Lets you choose a variable, time period, breakdown and chart or table. It also contains OG-Core's analysis tables.
   * - Go to Cases / Go to Run
     - Helps you create or finish runs when no results are available.

The run rows show the analysis and completion date when available. The
report header shows the selected run's completion time and analysis.
Disabled actions give a reason, such as results being out of date.
Refreshing the page keeps the selected view when it remains available.

Read the Report
----------------

Use **Summary**, **Policy**, **Macroeconomy**, **Government**, **Households**
and **Table** below the report title to jump between sections.
**Policy** appears for a comparison.

Read **Policy changes** before the results. It shows the baseline and
reform input values. **Show [number] more** expands a long list of changes.
For a large array, open **Parameters** to inspect the full schedule.

If the reform has the same saved parameters as its baseline, the Report
shows an explanation and **Edit reform parameters**. For the tax example,
return to Parameters, save the intended ``cit_rate`` change and run the
reform again before comparing.

The summary cards identify their time frame and units. In a comparison,
macroeconomic quantities such as GDP and consumption use percent changes;
interest rates use percentage-point changes; government finances use
shares of GDP. A single-run view shows values for that run.

The header may show **Solution converged** or **Check solution accuracy**.
The latter means the recorded solver errors need attention. Review the
run log with your modeller before interpreting a flagged solution.
A completed calculation does not by itself establish that the assumptions
are suitable for a policy choice.

Long run and transition paths
------------------------------

**Long run (steady state) only** means no year-by-year transition was
calculated for this selection. The Report shows long-run values or changes.

**Transition path + long run** adds charts over time when the saved
transition results are available. A comparison needs transition results
for both the baseline and reform. The macroeconomic charts shade an initial
window of up to ten years and mark the long-run result with a dashed line.
Read the year range above each chart.

The **Main results table** includes up to the first ten model years and
a separate **Long run** column. A steady-state selection instead has a
**Long-run results table**. The **CSV** button above the table exports its
values and units.

Household results
------------------

Under **Households**, choose an **Outcome**, such as **Consumption**.
The lifecycle chart shows ages in the long-run economy. The other chart
summarises outcomes or changes by lifetime-income group.

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Control
     - What it shows
   * - Population average
     - The outcome by age, averaged across income groups using the run's own population weights. This is the starting view.
   * - All income groups
     - One age profile for each lifetime-income group.
   * - Baseline / Reform
     - In All income groups for a comparison, chooses which scenario's group profiles to display.
   * - One income group
     - Shows the age profile for the selected group. A comparison plots the baseline and reform together.
   * - Income group
     - Chooses the group when One income group is active.

Group averages and changes use the population weights saved with each run.
Read the displayed group labels; their number and boundaries depend on the
country model. Lifetime-income groups describe earning ability over a
lifetime. They are not survey-year income groups. An age profile compares
ages in a long-run economy; it does not follow one person through time.

If age, income-group or population information is missing, the app shows
an explanation instead of inventing household averages. Older results may
have their metadata rebuilt on first opening. Keep the country model
installed so the app can read the necessary information.

Explore data
-------------

1. Open **Explore data**.
2. Use **Find a variable...** or browse the variable list, then select an
   outcome such as GDP or household consumption.
3. Choose the available **Period**, **Show** and **Breakdown** controls.
4. Choose **Chart** or **Table** under **View**.

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Control
     - What it does
   * - Period: Long run
     - Shows the steady-state outcome.
   * - Period: Over time
     - Shows the transition path for an economy-wide variable when available. It is disabled for a steady-state selection or an unsupported variable.
   * - Show: Change
     - Shows the reform's change from the baseline, with the unit appropriate to the variable. Available for comparisons.
   * - Show: Baseline & reform
     - Shows the two scenarios' values together. Available for comparisons.
   * - Breakdown: By age
     - Shows a household outcome by age, averaged using population weights.
   * - Breakdown: By income group
     - Shows a household outcome averaged within each lifetime-income group.
   * - Breakdown: Age × income
     - Shows the age and income-group detail as a grid or heatmap.
   * - Scenario: Baseline / Reform
     - Chooses the scenario when displaying levels in an age-by-income grid.
   * - View: Chart / Table
     - Switches between a chart and its data table.

Controls depend on the variable and the selected run or comparison.
Unavailable values appear as gaps or missing entries, not as zero.

Download charts and data
-------------------------

On a chart, click **Download**, then **Download PNG** or **Download SVG**.
PNG suits documents and presentations; SVG stays sharp when resized.
Exports include the chart's title. Check the selection, period and units
before using an exported image.

For data, use the **CSV** button above the Report's main results table or
choose **Table** in Explore data and click its **CSV** button. Chart images
and CSV exports do not change the model inputs or provide a complete case
backup.

OG-Core tables
---------------

The **OG-Core tables** section is inside **Explore data**. Choose a table,
wait for it to load, then click **CSV** beside the table controls.

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Table
     - Availability and meaning
   * - Macro (long run)
     - Long-run baseline and reform values and changes. Requires a comparison.
   * - Inequality
     - Available measures of differences across households for the selection.
   * - Gini
     - More detail on the Gini measure of inequality.
   * - Wealth moments
     - Summary measures of the selected run's wealth distribution. In a comparison it is labelled Wealth moments (baseline) and uses the baseline only. It does not supply survey observations.
   * - Macro (10 years)
     - A transition-path selection's macroeconomic table for the first ten years and long run.
   * - Revenue decomposition
     - The available revenue breakdown for a comparison solved with transition paths.

A disabled table explains which run or analysis is needed. If a table
fails to load, keep the error message and check that the country model is
still installed; see :doc:`troubleshooting`.

Read the measures correctly
---------------------------

* **Percent change:** for a positive baseline, ``100 × (reform − baseline) /
  baseline``. A value of ``+2%`` means the result is 2% above the baseline.
* **Percentage-point change (pp):** the gap between rates in percent. A
  change from 5% to 6% is ``+1 pp``.
* **Share of GDP:** government values are expressed as a percentage of each
  run's GDP. A change from 30% to 32% of GDP is ``+2 pp of GDP``.
* **Difference:** reform minus baseline in the outcome's units. For a level
  with a zero or negative baseline, the app uses a difference instead of
  a misleading percent change. Negative baselines are flagged.
* **Levels:** the scenario's values. Unless a unit or conversion says
  otherwise, monetary-looking levels are model units, not pesos.

``n/a``, a dash or a gap is not zero. Very small calculated changes may be
displayed as zero to avoid presenting numerical solver noise as an effect.
The sign of a change shows its direction; it does not establish whether the
policy is desirable.

Record a result for a policy note
---------------------------------

Save the country, case, baseline and reform names, country model version,
analysis type, parameter changes, completion date and exported files. State
whether each finding is long-run or refers to particular transition years.
Explain the government's spending and debt assumptions in the baseline.

Do not insert expected GDP or revenue changes before running the example.
Results can differ across model versions.

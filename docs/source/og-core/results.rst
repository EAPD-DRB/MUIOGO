6. Read and export results
==========================

The Results screen compares a completed reform with its completed baseline.
Both must belong to the same case. A baseline alone does not open this
comparison screen.

Open the example
-----------------

1. Click **Results** in the left menu.
2. Under **Case**, choose ``PHL tax example``.
3. Under **Reform**, choose ``CIT cut``. The app selects its linked baseline.
4. Check **Parameter changes**. Only ``cit_rate`` should differ.
5. Read the long-run effects, then compare household groups.

The baseline may be labelled ``baseline`` here. Cases displays that same
baseline as ``PHL tax example``.

Top controls and tabs
----------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Control
     - What it does
   * - Case
     - Chooses a case with a completed baseline–reform pair.
   * - Reform
     - Chooses a completed reform linked to that case's baseline.
   * - Overview
     - Shows the policy changes, main results and household charts.
   * - Explore
     - Lets you choose an outcome, measure and display.
   * - Tables
     - Opens the available result tables.
   * - Go to Run
     - Appears when no completed comparison exists. Opens the Run screen.

The displayed date identifies the reform's completion date. Check the case
and reform names whenever you switch comparisons.

Overview
---------

Read **Parameter changes** first. It describes the policy difference.
**Show [number] more** expands a long list; **Show less** folds it again.
For array inputs, it may list the parameter without every changed value.
Review the Parameters screen for those details.

The main cards show GDP, consumption, labor, tax revenue and the real
interest rate. The macroeconomic and fiscal charts show selected changes.
Inequality summaries appear when those results are available.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Chart control
     - What it does
   * - Distribution: Outcome
     - Chooses household consumption, labor supply, wealth or before-tax income when available.
   * - Distribution: Measure
     - Chooses Percent change or Difference from the baseline.
   * - Heatmap cell
     - Point to a cell for its value. Click it to open Explore with that income group's lifecycle profile.
   * - Lifecycle profiles: Outcome
     - Chooses the household outcome shown by age.
   * - Lifecycle profiles: Income group
     - Chooses a lifetime-income group.
   * - Lifecycle profiles: Measure
     - Chooses Levels, Percent change or Difference.
   * - Export SVG
     - Downloads that chart as an image for reports or presentations.

In the heatmap, each cell represents an age and a lifetime-income group.
Read the colour scale. Extreme values can be outside the displayed colour
range; the scale notes this. Use the cell value to check them.

Lifetime-income groups describe earning ability over a lifetime. They are
not the same as income groups measured in a single survey year. A lifecycle
profile compares ages in the long-run economy; it does not track one person
year by year.

Explore
--------

1. Choose an **Outcome**, such as Gross domestic product or Household
   consumption.
2. Choose a **Measure**.
3. Choose a **View**. Options depend on the outcome's data.
4. For a lifecycle profile, choose a **Lifetime-income group**.

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Control or view
     - What it does
   * - Outcome
     - Selects an available model result. The short code in brackets identifies it.
   * - Measure
     - Selects levels, changes or differences. Rate outcomes offer percentage-point differences and rates in percent.
   * - View
     - Selects comparison bars, a comparison chart, an age × income heatmap, a lifecycle profile or a table, where available.
   * - Lifetime-income group
     - Selects a group for a lifecycle profile. Hidden when not needed.
   * - Set as default
     - Saves the current selection and view for this country in this browser.
   * - Restore defaults
     - Clears the saved view and returns to the default GDP comparison. It does not change model inputs.
   * - Export SVG
     - Saves the current chart. This button is hidden in the table view.

**Dimensions** describes whether an outcome is a single value, a list or a
table. If age or income-group information is missing, the app may show
generic labels. Check the note before interpreting the groups.

Tables
-------

Choose a table, wait for it to load, then click **Export CSV**. Open the
downloaded file in a spreadsheet app.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Button
     - Table shown
   * - Macroeconomic
     - Long-run economic results for the baseline and reform.
   * - Inequality
     - Available measures of differences across households.
   * - Gini detail
     - More detail on the Gini measure of inequality.
   * - Wealth moments
     - Summary measures of the baseline wealth distribution. This view does not compare the reform or supply survey observations.
   * - Export CSV
     - Downloads the currently loaded table. Disabled until a table is available.

Read the measures correctly
---------------------------

* **Percent change:** ``100 × (reform − baseline) / baseline``. A value of
  ``+2%`` means the result is 2% above the baseline.
* **Difference:** reform minus baseline, in the outcome's units.
* **Percentage-point difference:** the gap between two rates. A rise from
  5% to 6% is +1 percentage point.
* **Levels:** the underlying result values. Monetary-looking values may
  use model units. Do not label them pesos unless the calibration confirms
  that conversion.

``n/a``, a dash or a blank is not zero. A percent change cannot be computed
when the baseline is zero, and some outputs may be unavailable.

Record a result for a policy note
---------------------------------

Save the case and reform names, country model version, analysis type, tax
values, run date and exported files. State that this is a **long-run model
comparison**. Explain the government's spending and debt assumptions used
in the baseline. A completed run confirms that the calculation finished;
it does not establish that the assumptions are suitable for a policy choice.

Do not insert expected GDP or revenue numbers before running the example.
Results can differ across model versions.

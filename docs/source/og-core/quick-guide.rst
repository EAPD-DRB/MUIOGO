Quick Guide
===========

This quick guide shows you how to install MUIOGO and run a simulation.
You will compare a baseline with a corporate tax cut from 25% to 20% in the
Philippines.

.. include:: ../_includes/install-and-open.rst

2. Open the Philippines workspace
---------------------------------

1. Click **Open OG-Core**, or **OG-Core** in the top bar.
2. Find **Philippines (PHL)**. Click **Install** if needed.
3. Wait until the card says **installed**. Click **Open workspace**.

**Check:** the page title says **Philippines workspace**.

3. Create the baseline
----------------------

1. Click **Create baseline** beside **Calibration defaults**.
2. Leave **Type** as **Baseline**. Set **Name** to ``PHL tax example``.
3. Click **Create and edit**. The Parameters screen opens.
4. Keep the default values. Check **Corporate income tax rate**
   (``cit_rate``) under **Frequently Used Parameters**. For this example,
   it should be ``0.25``. Click **Save**.

``0.25`` means 25%. If your installed default differs, keep it and see
:ref:`og-tax-example` before making the reform.

4. Create the tax reform
------------------------

1. Click **Cases** in the left menu.
2. On the ``PHL tax example`` row, open the three-dot menu. Click
   **Add reform**.
3. Set **Name** to ``CIT cut``. Check that **Based on** is
   ``PHL tax example``. Click **Create and edit**.
4. Under **Frequently Used Parameters**, set **Corporate income tax rate**
   (``cit_rate``) to ``0.20``. If there is more than one year, set each
   displayed year to ``0.20``.
5. Keep all other values. Click **Save**.

**Check:** with **Compare against** set to its baseline, the page shows
**1 change**. This is a cut of five percentage points.

5. Run the comparison
---------------------

1. Click **Run** in the left menu.
2. Choose **Steady state** under **Analysis**.
3. Select ``PHL tax example`` and ``CIT cut``. Clear any other selections.
4. Leave **Re-run completed selections** unchecked. Click **Run selected**.
5. Stay on this page until both runs say **Completed**.

The baseline runs first. Run time depends on your computer and the model.
If a run fails, follow :doc:`troubleshooting` before continuing.

6. Read and save the results
----------------------------

1. Click **Results**. Choose ``PHL tax example`` under **Case** and
   ``CIT cut`` under **Reform**.
2. In **Overview**, check **Parameter changes**. It should list only
   ``cit_rate``. Read GDP, consumption, labor and tax revenue changes.
3. Under **Lifecycle profiles**, choose **Consumption**. Compare income
   groups to see who may gain or lose.
4. Click **Export SVG** on a chart to save it.
5. Open **Tables**, choose **Macroeconomic**, then click **Export CSV**.

These are long-run comparisons. They do not show the year-by-year path.
For units and interpretation, see :doc:`results`.

When finished, wait for all jobs to end. Return to the terminal and press
**Ctrl+C** to stop the app.

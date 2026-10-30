Quick Guide
===========

This quick guide shows you how to install MUIOGO and run a simulation.
You will compare a baseline with a corporate tax cut from 27% to 20% in
South Africa.

.. include:: ../_includes/install-and-open.rst

2. Open the South Africa workspace
----------------------------------

1. Click **OG-Core** in the top bar.
2. Find **South Africa (ZAF)**. Click **Install** if it is not installed.
3. Wait until the card says **installed** (in green) and then click **Open workspace**.

**Check** that the page title at the top says **South Africa workspace**.

3. Create the baseline
----------------------

1. On **Cases**, click **Create case** in the country bar.
2. Leave **Type** as **Baseline**. Set **Name** to ``ZAF tax example``.
3. Click **Create and edit**. The Parameters screen opens.
4. Keep the default values. Check **Corporate income tax rate**
   (``cit_rate``) under **Frequently Used Parameters**. For this example,
   it should be ``0.27``. Click **Save**.

``0.27`` means 27%. If your installed default differs, keep it.

4. Create the tax reform
------------------------

1. Click the **Cases** icon in the left menu.
2. On the ``ZAF tax example`` baseline row, click **Add reform**.
3. Set **Name** to ``CIT cut``. Check that **Based on** is
   ``ZAF tax example``. Click **Create and edit**.
4. Under **Frequently Used Parameters**, set **Corporate income tax rate**
   (``cit_rate``) to ``0.20`` for every displayed year. Leave the baseline
   unchanged. If its default differs from 27%, see :ref:`og-tax-example`.
5. Keep all other values. Click **Save**.

**Check** that the top of the page says "**1 change** vs Default Baseline".
If you select **Show only changed**, you should see the tax cut.

5. Run the comparison
---------------------

1. Click the **Run** icon in the left menu.
2. Choose **Steady state** under **Analysis**.
3. Select ``ZAF tax example`` and ``CIT cut``. Clear any other selections.
4. Leave **Re-run completed selections** unchecked. Click **Run selected**.
5. Stay on this page until both runs say **Completed**.

The baseline runs first. Run time depends on your computer and the model,
but it can take more than 10 minutes.
If a run fails, follow :doc:`troubleshooting` before continuing.

6. Read and save the results
----------------------------

1. Click **Results**. In the run list, find ``ZAF tax example`` and its
   ``CIT cut`` reform. Click **Compare** on the reform row.
2. In **Report**, open **Policy**. **Policy changes** should list only
   ``cit_rate``, with the baseline and reform values.
3. Read **Summary**, **Macroeconomy** and **Government**. Under
   **Households**, choose **Consumption**. Start with **Population average**,
   then compare income groups.
4. On a chart, open **Download** and choose **Download SVG** or
   **Download PNG**.
5. Open **Explore data**. In **OG-Core tables**, choose **Macro (long run)**,
   wait for it to load, then click **CSV**.

**Check:** the Results title names both the baseline and the reform, and
the analysis says **Long run (steady state) only**. To inspect the baseline
alone, click its **View** button instead of the reform's **Compare** button.

This example uses long-run results. A completed **Transition path** run
also provides year-by-year charts. Read each chart's period and units;
see :doc:`results` for interpretation.

When finished, wait for all jobs to end. Return to the terminal and press
**Ctrl+C** to stop the app.

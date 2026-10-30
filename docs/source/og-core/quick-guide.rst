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

1. Click the **Results** icon in the left menu.
2. In the Results list on the left, find ``ZAF tax example`` and its
   ``CIT cut`` reform. Click **Compare** on the reform row.
3. In **Report**, click on **Policy**. **Policy changes** should list only
   ``cit_rate``, with the baseline and reform values.
4. Check the simulation results **Summary**, **Macroeconomy** and **Government** impacts.
5. Under **Households**, you can see the impacts on **Consumption** and on several other indicators
   using the dropdown box. Start with **Population average**, then click on **All income groups**.
6. You can save any chart by clicking on the 3 dots in the upper left corner of the chart,
   and selecting **Download PNG** (image format) or **Download SVG** (vector format).
7. At the open of the page, click on **Explore data**. This view allows you to explore all the outputs
   generated.
8. At the bottom of the page, under **OG-Core tables**, choose **Gini**,
   wait for it to load, then click on **CSV** to download the data for use in Excel.

To inspect the results of the baseline alone or the reform alone. Just click its **eye** (view) button
next to them instead of the **Compare** button.

This example uses long-run results. A completed **Transition path** run
also provides year-by-year charts. Read each chart's period and units;
see :doc:`results` for interpretation.

When finished, to stop the app return to the Terminal or PowerShell and press
**Ctrl+C** to stop the app.

To launch the app again, open Terminal or PowerShell and go to **your MUIOGO folder**
(``cd "path to your MUIOGO folder"``, replacing the quoted text with the
Location saved during installation). Then run:

**Mac / Linux**

.. code-block:: bash

   ./scripts/start.sh

**Windows — PowerShell**

.. code-block:: powershell

   .\scripts\start.bat

Open the address shown in the terminal if the browser does not open automatically.

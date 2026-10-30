3. Create a baseline and reform
===============================

A country workspace keeps its own cases. Each case holds one baseline and
the reforms compared with it. **Calibration defaults** is a reference row
with the country model's starting values. Create a baseline to run them.

Create the example baseline
---------------------------

1. Click **Create case** in the country bar above the cases list.
2. Select **Baseline** under **Type**.
3. Enter ``ZAF tax example`` under **Name**.
4. Under **Description**, enter ``Unchanged country defaults``.
5. Click **Create and edit**. The Parameters screen opens.
6. Keep the defaults and click **Save**. Return to **Cases**.

**Check:** ``ZAF tax example`` appears with type **baseline**.

Create the example reform
-------------------------

1. On the ``ZAF tax example`` baseline row, click **Add reform**.
   You can also click **Create case**, choose **Reform** under **Type**,
   and select the baseline under **Based on**.
2. Enter ``CIT cut`` under **Name**.
3. Check **Based on**: it must be ``ZAF tax example``.
4. Add the description ``Corporate income tax: 27% to 20%``.
5. Click **Create and edit**.

**Check:** the Parameters bar says **reform**, ``CIT cut``, and the correct
baseline. Continue to :doc:`parameters` to make the tax change.

Case controls
--------------

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Control
     - What it does
   * - Create case
     - Opens the creation window. Choose Baseline or Reform.
   * - Search cases…
     - Filters the list by case, run or parent baseline name. Clear the text to see all rows.
   * - Grouped
     - Places each reform under its baseline.
   * - Separate
     - Displays separate baseline and reform lists.
   * - Row name / small arrow
     - Shows or hides the row's details, including its description.
   * - Run
     - Opens the Run screen with that configuration selected. It does not start a solve.
   * - Edit
     - Opens that baseline's or reform's parameters.
   * - Three-dot menu
     - Opens more actions for the row. Escape or a click outside closes it.
   * - Add reform
     - Creates a policy change linked to that baseline.
   * - Retry setup
     - Creates the missing baseline run after incomplete case creation.
   * - Delete reform
     - Asks to delete the reform and its results.
   * - Delete baseline
     - Asks to delete the baseline, all its reforms and all their results.

In the creation window, **Baseline** starts from country defaults.
**Reform** uses the chosen baseline as its reference. **Based on** appears
for reforms. **Description** is optional. **Create and edit** saves the new
entry and opens its parameters. **Cancel** closes the window.

Reform is disabled until a baseline exists. Use a unique name. If creation
fails, read the message, correct the problem and try again.

.. warning::

   Deletion cannot be undone. In a deletion window, read the names before
   clicking **Delete baseline** or **Delete reform**. **Cancel** keeps the work.

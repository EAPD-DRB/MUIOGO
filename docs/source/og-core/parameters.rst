4. Set and save parameters
==========================

Open **Cases** and click **Edit** on the run you want to change. Check the
country, run name and type at the top of **Parameters** before editing.

.. _og-tax-example:

Make the example tax change
---------------------------

1. Open the ``CIT cut`` reform created in :doc:`cases`.
2. Leave **Compare against** set to its own baseline.
3. In **Frequently Used Parameters**, find **Corporate income tax rate**
   (``cit_rate``). Use the browser's Find command if needed.
4. Check the baseline value. The OG-PHL defaults inspected for this draft
   use ``0.25``, meaning 25%.
5. Enter ``0.20``, meaning 20%. Set every displayed year for this parameter
   to ``0.20``. A later unchanged year would otherwise reverse the cut.
6. Leave all other parameters unchanged. Click **Show only changed**.
7. Check that only ``cit_rate`` differs, then click **Save**.

**Check:** the page shows **1 change** against the baseline and confirms
that it was saved. The counter counts changed parameters, not unsaved
edits. It may still show **1 change** after saving.

If your installed default differs, keep the baseline unchanged. Use
``0.20`` for the reform only if it lowers that rate. Record the actual
baseline and reform values in the description. If the baseline is already
20% or lower, ask your modeller to adapt the exercise.

This changes a model input. It does not set GDP, revenue or another result.
Other policies and the government's budget assumptions remain as specified
in the baseline.

Enter rates correctly
----------------------

Use a decimal point. Enter ``0.20`` for 20%, not ``20`` or ``20%``.
A change from 25% to 20% is **−5 percentage points**. It is a **20% reduction**
in the rate. Those measures are different.

For yearly policy fields, the last value continues into years that you
have not entered. In **Steady state**, this final rate determines the
long-run policy. Earlier years matter for a transition-path analysis.

Page controls
--------------

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Control
     - What it does
   * - Section heading
     - Opens or closes a parameter group. Frequently Used Parameters opens first.
   * - ? help icon
     - Shows the parameter description when you point to it.
   * - Number box / slider
     - Changes a value. Use the number box for an exact value.
   * - Choice list / Yes–No list
     - Selects one of the available options.
   * - Add [next year]
     - Adds the next year's value, copying the previous value.
   * - × beside a year
     - Removes that entry. Later entries shift into earlier year positions; check the full schedule afterward. The first entry cannot be removed.
   * - Compare against
     - Changes the reference used to display differences. It does not change the run's parent baseline or saved policy.
   * - Show only changed
     - Shows parameters that differ from the selected comparison reference.
   * - Curved reset arrow beside a parameter
     - Restores that parameter to its own baseline, or to calibration defaults for a baseline run.
   * - Reset to baseline
     - Removes the reform's differences from its own baseline. Click Save to keep the reset.
   * - Reset to calibration
     - Restores a baseline's editable values to country defaults. Click Save to keep the reset.
   * - Save
     - Saves the run's parameter changes. It does not execute the model.

Reset actions always use the run's own baseline or calibration reference,
even when **Compare against** shows another run.

The groups cover taxes; government spending and pensions; growth and
production; households and preferences; demographics; the open economy;
arrays and reference data; and advanced settings. Some common fields appear
only in **Frequently Used Parameters**.

Allowed ranges appear below fields. Blank, non-numeric or out-of-range
values block saving. Population-group shares marked to total 1 must add to
1. A **read-only** lock means the value cannot be changed here. Some large
calibration tables can be edited; review those with a modeller.

Edit a table
-------------

This is not needed for the tax example.

1. Click **Edit table** beside the parameter preview.
2. Check the parameter name, row and column labels, and allowed range.
3. Double-click a cell to edit. Select a range to copy or paste using
   **Ctrl+C / Ctrl+V**, or **Cmd+C / Cmd+V** on Mac.
4. Check the modified and invalid value counts.
5. Click **Apply changes** to return the edited values to the Parameters
   page. Then click **Save** on that page.

**Cancel**, Escape or a click outside the table window discards edits made
in that window. **Apply changes** is blocked while values are invalid.
It does not add or remove model dimensions.

Save before leaving
--------------------

If you leave with unsaved edits, the app offers **Save** and **Don't save**.
**Save** saves and keeps you on the page; wait for confirmation, then
navigate again. **Don't save** leaves without saving the edits.

Saved parameter changes can make earlier results out of date. A changed
baseline can also require its reforms to be run again. Finish the baseline
before preparing policy comparisons.

Next, :doc:`run`.

5. Run the model
================

Save your parameters first. Then click **Run** in the left menu.

Run the example
----------------

1. Under **Analysis**, choose **Steady state**.
2. Select the checkboxes for ``PHL tax example`` and ``CIT cut``.
   Clear other selections.
3. Leave **Re-run completed selections** unchecked.
4. Click **Run selected**. The number on the button is your selection count.
5. Watch **Current queue**. The baseline runs before its reform.
6. Stay on this screen until both runs show **Completed**.

**Check:** both appear in **Latest outcomes** with a completion time.
Next, :doc:`results`.

Choose an analysis
-------------------

**Steady state** solves the economy's long-run position under the chosen
policy. It is the analysis used in this guide.

**Transition path** also solves the adjustment over time. It can take much
longer. Required baselines use the same analysis as their reforms.

.. note::

   Results labels long-run results separately from the transition path.
   For completed transition-path runs, **Report** includes year-by-year
   macroeconomic charts. In **Explore data**, choose **Period → Over time**
   for an economy-wide variable. A reform comparison needs transition-path
   results for both the reform and its baseline.

Run controls
-------------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Control
     - What it does
   * - Run checkbox
     - Adds or removes one baseline or reform from the selection.
   * - Select all / Clear selection
     - Selects every listed run, or clears the selection.
   * - Analysis
     - Chooses Steady state or Transition path.
   * - Re-run completed selections
     - Recalculates completed selections even when matching saved results can be reused.
   * - Run selected
     - Starts the selected queue. Required baselines are added before their reforms.
   * - Refresh
     - Reloads runs started or changed in another tab. Active runs also update automatically.
   * - Cancel active runs
     - Requests cancellation of active runs in this workspace and stops further submissions from the current selection.
   * - Latest outcomes row / arrow
     - Opens or closes the saved log and any error for that run.

Controls may be disabled while the selected queue is executing.

Understand run states
----------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - State or label
     - Meaning
   * - Not run
     - No completed calculation is available for this run.
   * - Needs run
     - Saved results no longer match the current inputs or baseline. Read the reason below the state.
   * - Planned
     - The run is in the selected plan, but has not been submitted.
   * - Waiting for baseline
     - The reform is waiting for its baseline.
   * - Queued
     - The app has accepted the job. It is waiting to start.
   * - Running
     - The model is calculating. The live log shows progress.
   * - Completed
     - The calculation finished successfully.
   * - Cached result / Reused
     - Matching completed results are available or were reused. No new solve is needed.
   * - Failed
     - The calculation stopped with an error. Open its log.
   * - Blocked
     - A required baseline failed, was cancelled or is unavailable.
   * - Cancelled
     - The run was stopped. It does not provide a completed comparison.

The app checks whether saved results match the inputs, country model and
analysis. It can reuse a completed baseline when only the reform needs to
run. Leave the re-run box unchecked for ordinary use.

An iteration number shows progress through the calculation. It is not a
percentage complete. No fixed run time is promised. If progress stops or
a run fails, see :doc:`troubleshooting`.

Keep MUIOGO running and the computer awake. To stop a run, use
**Cancel active runs**. Closing the browser tab does not cancel a job
already submitted. Returning to Run reloads its recorded state.

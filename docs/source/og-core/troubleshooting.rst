Help and troubleshooting
========================

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - What you see
     - What to do
   * - Git is missing
     - Install Git, reopen Terminal or PowerShell, then repeat the installer.
   * - Installation summary shows a failure
     - Read the first error and keep the installation log. Ask IT for help if a system tool or download is blocked.
   * - Browser cannot open the app
     - Check that the terminal is still running MUIOGO. Open the address shown there. If you stopped it, use the start script.
   * - Conda environment is active
     - Run ``conda deactivate`` until no Conda environment is active, then start MUIOGO again.
   * - Address or port is already in use
     - Check whether another MUIOGO window is already running. Use that instance, or stop it before starting another.
   * - Philippines is missing from the list
     - Check the internet connection and reload. If the catalogue is still unavailable, ask a modeller to help add the official OG-PHL repository.
   * - Country installation fails
     - Open View error. Copy the log, correct the reported problem, then use Retry. Closing the log window does not cancel installation.
   * - Workspace does not open
     - Read the opening error. Use Retry, or Return to OG-Core and check the country's installation state.
   * - No run selected on Parameters
     - Go to Cases and click Edit on the intended baseline or reform.
   * - Save rejects a value
     - Check decimal entry, the allowed range, blank cells and any shares that must total 1.
   * - Apply changes does nothing
     - Check the table's invalid value count. Correct invalid cells, apply again, then save the Parameters page.
   * - Run selected is disabled
     - Select at least one run. If a queue is executing, wait or cancel it.
   * - Waiting for baseline / Blocked
     - Check the linked baseline. It must complete successfully with the same analysis before the reform can run.
   * - Needs run
     - Inputs, the country model or the baseline have changed. Select the affected run and calculate it again.
   * - Failed, including a resource-constraint or convergence error
     - Open the Latest outcomes row and read its log. A modeller must check the inputs and model. Do not treat partial output as a result or change unrelated values just to remove the error.
   * - Run appears slow
     - Check the live log for progress. Transition paths can take much longer. Keep the computer awake; use Cancel active runs if you decide to stop.
   * - View or Compare is disabled on Results
     - Read the reason under the run name. View needs current completed results for that run. Compare needs current completed results for the reform and its linked baseline. Run any missing or out-of-date selections again.
   * - The reform has the same parameters as its baseline
     - Use Edit reform parameters to inspect the saved inputs. For the tax example, only cit_rate should differ. Save the intended change, run the reform again, then return to Results.
   * - Over time is disabled or no year-by-year chart appears
     - Check the analysis label. Steady-state runs provide long-run results only. For a comparison over time, complete both runs with Transition path and choose an economy-wide variable in Explore data.
   * - Household outcomes are unavailable
     - Read the note. Older results may need their age, income-group and population metadata rebuilt. Keep the country model installed; ask your modeller for help if the information cannot be recovered.
   * - Check solution accuracy
     - Review the solver-error information and run log with your modeller before interpreting the results.
   * - A table fails to load
     - Read the displayed error. Check the country model is installed and not updating. Try the table again; keep the message if it fails.

Get help
---------

For a calculation problem, first contact the modeller supporting your
study. For an app problem, use the
`MUIOGO issue tracker <https://github.com/EAPD-DRB/MUIOGO/issues>`_. Include:

* your operating system and what you clicked;
* country, case, reform and analysis names;
* the expected result and the actual message;
* the installation log or run log, and a screenshot if useful.

Keep a copy of important work
-----------------------------

**Save** stores inputs on your computer. Chart and table exports are not
complete case backups. The current OG-Core screens do not offer a case
backup button. Ask IT or your modeller to back up the OG-Core data and
record the country model version before updating or moving computers.

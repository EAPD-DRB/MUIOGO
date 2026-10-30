2. Choose OG-Core and a country
===============================

Choose the model
----------------

On **Select a model**, click **Open OG-Core**. You can also click
**OG-Core** in the top bar. The **CLEWS** button opens the resource model.
Its new manual will be developed separately.

Install OG-PHL
---------------

1. On the OG-Core home screen, find **Philippines**, code **PHL**.
2. Click **Install**. A window shows installation progress.
3. Wait until the country card says **installed**.
4. Click **Open workspace**.

The app checks the installation, opens the country workspace and loads its
cases. **Retry** repeats a failed opening step. **Return to OG-Core**
returns to the country list.

**Check:** the title says **Philippines workspace** and the left menu
shows **Cases**, **Parameters**, **Run** and **Results**.

Country-card buttons
---------------------

Some buttons appear only when needed.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Button
     - What it does
   * - Install
     - Downloads the country model and sets up its tools.
   * - Installing… / progress label
     - Opens the live installation log.
   * - Open workspace
     - Opens the installed country's cases and results.
   * - Check for updates
     - Checks whether a newer country model is available. It does not install it.
   * - Update
     - Downloads and installs the available update. Record the version used for a policy study before updating.
   * - Check again
     - Rechecks a model registered from a local folder. Some local folders must be updated by their owner.
   * - View error / View update error
     - Opens the failure message and available log.
   * - Retry
     - Tries the installation again.
   * - Remove
     - Asks to remove the country registration from MUIOGO. Its files remain on disk.

In the log window, **Copy log** copies the displayed log. **Close** hides
the window; installation continues. **Retry install** or **Retry update**
repeats the failed operation. In a removal window, **Remove** confirms and
**Cancel** returns without removing the registration.

If the catalogue cannot be reached, the app may show its last saved list.
Installing and checking for updates need a connection.

Add a country from another source
---------------------------------

Use **Add calibration** when a modeller gives you a country repository or
an existing model folder. This is not needed for the OG-PHL example.

1. Click **Add calibration**.
2. In **Source**, enter the full local folder path or Git repository URL.
3. In **Label**, enter the country name. In **Code**, enter a short ID.
4. Click **Check**. Read the result and any warnings.
5. Click **Add calibration** after the check passes. **Cancel** closes
   the window without adding it.

Changing any field requires a new check. A valid source check confirms the
package structure; it does not validate the model's policy assumptions.

Move between screens
---------------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Control
     - Use
   * - Cases
     - Create or choose a baseline and its reforms.
   * - Parameters
     - Edit the run last opened from Cases.
   * - Run
     - Select and execute saved runs.
   * - Results
     - Compare a completed baseline and reform.
   * - Home / top model buttons
     - Leave the country workspace. The app asks for confirmation.
   * - Stay
     - Keep the workspace open.
   * - Exit workspace
     - Leave the workspace. Saved work remains; already submitted jobs continue while the app runs.
   * - Menu icon / sidebar arrow
     - Hide, show or reduce the left menu.
   * - Full Screen icon
     - Switch the browser's full-screen display on or off.
   * - Speaker icon
     - Turn notification sounds on or off.
   * - Code versions icon
     - Open the interface's version history.
   * - Settings gear
     - Open shared interface settings. It is not the OG-Core parameter editor. Close the window with its × button.

Stay on **Run** until a selected queue finishes. Jobs already submitted can
continue in the background, but leaving can stop submission of later jobs.

Next, :doc:`cases`.

1. Install, start, stop and update
====================================

MUIOGO runs on your computer and opens in a browser. The supported setup
uses an installation script. You do not need to write model code.

Before you start
----------------

* Use Windows, Mac or Linux with a web browser.
* Connect to the internet for installation and country model downloads.
* Install `Git <https://git-scm.com/downloads>`_. If your organisation
  manages software installation, ask your IT team to help.
* Keep the computer awake during installation and simulations.

The installer adds the required Python tools and app packages. OG-ZAF is
installed separately from inside MUIOGO.

Install Git
------------

Open **Terminal** on Mac or Linux, or **PowerShell** on Windows.
Paste the command for your computer and press Enter. If Git is already
installed, skip this step.

.. include:: ../_includes/install-git.rst

Install MUIOGO
---------------

Follow :ref:`og-install-commands`. Choose a folder where you can save files.
The installer creates a ``MUIOGO`` folder there.

.. _og-install-commands:

Run the installer
~~~~~~~~~~~~~~~~~

Open **Terminal** on Mac or Linux, or **PowerShell** on Windows.
Paste the command for your computer and press Enter. These are the same
commands used in the Quick Guide.

.. include:: ../_includes/install-muiogo.rst

Read the prompts. The installer downloads the app, sets up its tools and
checks the installation. It may also request permission to install system
tools. The shared app setup includes resource-model tools and demo data;
they are not used in this OG-Core exercise.

At the end, check that the summary says **MUIOGO is installed and ready**.
Save the folder path shown under **Location**. You will need this folder
to start MUIOGO again. When asked **Start MUIOGO now?**, enter ``y``.

The browser may open before the app is ready. Wait, then refresh. The
usual address is `http://127.0.0.1:5002/ <http://127.0.0.1:5002/>`_. This
address refers to your own computer. Keep Terminal or PowerShell open.

**Check:** you see **Select a model**, or the model you last opened.
Next, :doc:`workspace`.

Start MUIOGO again
------------------

Open Terminal or PowerShell **in your MUIOGO folder**. You can first type
``cd "path to your MUIOGO folder"``, replacing the quoted text with the
Location saved during installation. Then run:

**Mac / Linux**

.. code-block:: bash

   ./scripts/start.sh

**Windows — PowerShell**

.. code-block:: powershell

   .\scripts\start.bat

Open the address shown in the terminal if the browser does not open.

Stop MUIOGO
------------

1. Wait for installations and runs to finish, or cancel active runs.
2. Save any parameter edits.
3. In Terminal or PowerShell, press **Ctrl+C**.

Closing a browser tab does not stop the app. Stopping the app interrupts
active work. Saved cases remain available next time.

Update MUIOGO
--------------

Open Terminal or PowerShell **in your MUIOGO
folder** (the **Location** saved during installation).

Run each command below in order. Continue only when the previous command
finishes successfully.

**Mac / Linux**

.. code-block:: bash

   git pull --ff-only
   uv sync
   ./scripts/start.sh

**Windows — PowerShell**

.. code-block:: powershell

   git pull --ff-only
   uv sync
   .\scripts\start.bat

``git pull --ff-only`` downloads the latest code from your installation's
tracked branch (normally ``main``). ``uv sync`` installs the package
versions required by the updated code. The final command starts MUIOGO
again. Refresh the browser after the app starts.

If Git reports conflicting local changes or says it cannot fast-forward,
stop and ask your IT support or repository maintainer to help resolve
them before continuing.

Country models such as OG-ZAF are updated separately using the country
card's **Check for updates** and **Update** buttons; see :doc:`workspace`.

Existing source checkout — for IT support
-----------------------------------------

If Git has already downloaded the repository, open its folder and run:

.. code-block:: bash

   uv sync

Then run ``uv run python scripts/setup_dev.py --platform-only`` and use
the start command above.
The app supports Python 3.11–3.12. Country models have their own
environments; the country installer manages those separately.

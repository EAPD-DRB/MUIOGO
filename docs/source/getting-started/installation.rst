################
Installation
################

This repository currently uses a source-based setup flow for development and
contributor onboarding.

Supported Python versions are **3.10 to 3.12**. Python **3.11** is the
recommended version.

Recommended setup
=================

macOS / Linux
-------------

.. code-block:: bash

   ./scripts/setup.sh
   ./scripts/start.sh

Windows
-------

.. code-block:: bat

   scripts\setup.bat
   scripts\start.bat

.. note::

   The setup scripts create the virtual environment, install Python
   dependencies, install solver dependencies, and download demo data.

Manual dependency installation
==============================

For advanced users, you can install Python dependencies manually with
``pip install -r requirements.txt``, but that path still requires a supported
Python version (3.10 to 3.12) and does not add compatibility for newer Python
releases.

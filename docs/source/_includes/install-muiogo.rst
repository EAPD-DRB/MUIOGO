.. container:: installation-options

   **Mac / Linux**

   .. code-block:: bash

      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/EAPD-DRB/MUIOGO/main/scripts/install.sh)"

   **Windows — PowerShell**

   .. code-block:: powershell

      $f = "$env:TEMP\muiogo-install.ps1"; irm https://raw.githubusercontent.com/EAPD-DRB/MUIOGO/main/scripts/install.ps1 -OutFile $f; powershell -ExecutionPolicy Bypass -File $f

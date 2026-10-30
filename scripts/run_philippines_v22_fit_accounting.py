#!/usr/bin/env python3
"""Generate, check, solve and export the Philippines v22 FIT r9 candidate."""

from __future__ import annotations

import run_philippines_v22_integrated_repair as runner


runner.DEFAULT_CASE = ".Philippines_v22-transition-scope-fit-repair-candidate-r9"
runner.DEFAULT_RUN = "FIT_ACCOUNTING_V22_BASE"


if __name__ == "__main__":
    runner.main()

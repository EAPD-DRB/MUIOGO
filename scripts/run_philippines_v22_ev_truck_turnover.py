#!/usr/bin/env python3
"""Generate, check, solve and export the v22 EV/truck-turnover candidate."""

from __future__ import annotations

import run_philippines_v22_integrated_repair as runner


runner.DEFAULT_CASE = ".Philippines_v22-ev-truck-turnover-candidate-20260824"
runner.DEFAULT_RUN = "EV_TRUCK_TURNOVER_V22_BASE"


if __name__ == "__main__":
    runner.main()

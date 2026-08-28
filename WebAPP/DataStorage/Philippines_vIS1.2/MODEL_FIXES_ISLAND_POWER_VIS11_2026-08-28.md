# Philippines vIS1.1 stabilized island-power pilot

## Source change

vIS1.1 is a clean data-only successor to v36. It retains one OSeMOSYS region, represents LUZ, VIS and MIN through node electricity commodities, and keeps OFF isolated. No MUIOGO or OSeMOSYS equation changed. Observed generation and post-2020 capacity additions remain benchmark-only.

Six national sector-delivery accounting technologies now consume the three node electricity commodities simultaneously in sourced geographic proportions. This replaces eighteen node-sector pass-throughs and twelve annual ratio equalities without fixing total electricity use. Fifteen zero-cost, lossless fuel-renaming technologies and their node fuel commodities are omitted; applicable generators consume existing national fuel commodities directly, while natural-gas build envelopes remain Luzon-only.

Capacity allocations below 1e-9 are clamped to exact zero. Sector-bundle capacity is fixed, finite and non-investable. Interconnector total capacity is capped cumulatively. The inactive BASE nuclear equality has explicit zero constants and zero member coefficients, preventing null scenario-overlay cells from inheriting another constraint's value without forcing nuclear capacity. Hydrogen generation receives no firm reserve credit pending a firm-fuel basis.

The inherited COAL_PHASEOUT lower activity bound on `PHL_PRO_IMP_OIL` is removed. It first appeared in the earliest retained v9 case as a linear 184.56-PJ-to-zero trajectory, had no retained source or policy rationale, and contradicted the later classification of oil imports as an open endogenous backstop. COAL_PHASEOUT now inherits BASE's zero lower bound; no import cap, target or share is introduced.

DOE annual grid sales and peaks are retained, but nodes still inherit v36's normalized timeslice shape. Coal, petroleum and biomass delivery remain provisionally national pending spatial delivery/resource evidence. Land and water remain national.

## Validation authorization

One BASE optimization is authorized after deterministic source, application-generation, preprocessing and `glpsol --check` gates, with a hard 360-second deadline. Stop after optimal, infeasible, failure or timeout. Policy scenarios are not authorized in this run.

# Philippines vIS1.2 differentiated island-power candidate

## Equation-first classification and formulation

Observed generation and observed post-2020 additions remain benchmark-only. Published solar/wind cost anchors are economic inputs; grid capacity-factor ranges are continuing physical resource characteristics; gross CREZ potentials are continuing resource ceilings; and published transmission charges are economic network inputs. No activity, generation share or build result is fixed.

The one-region, 3+1 commodity topology and six geographic electricity bundles from vIS1.1 are retained. The active OSeMOSYS formulation uses `CapitalCost`, `FixedCost`, `VariableCost`, `CapacityFactor`, `TotalAnnualMaxCapacity`, and `TotalAnnualMaxCapacityInvestment`; no equation or MUIOGO code changes. OFF remains isolated.

DOE 2024 solar and onshore-wind capital/fixed-O&M anchors replace their inherited 2024 anchors; inherited year-to-2024 ratios preserve the time trajectory. Grid CF timeslice shapes are scaled to DOE grid-range midpoints. Gross CREZ potential replaces the meaningless 1,000,000-GW national placeholder and annual national renewable investment headroom is repartitioned, never duplicated. Node T&D receives only its positive charge increment over the lowest published grid charge; both interconnectors receive a conservative published PDS wheeling proxy.

Six VIS/MIN gas variants are removed because they have zero residual capacity and zero build reachability in every retained scenario under the existing Luzon-only grid-gas boundary. Zero BASE activity alone was not used as a deletion criterion. The inactive BASE nuclear equality carries explicit neutral zero constants and zero coefficients; policy-scenario nuclear milestones remain sparse and unchanged. The cumulative LV capacity correction remains 0.44 GW through 2033 and 0.88 GW from 2034.

The shared data writer resets scenario overlays to each parameter default for every emitted cell and closes each `RYCn` parameter independently. This prevents a null user-defined-constraint cell from inheriting a preceding constraint or year. The source and generated gates additionally require explicit BASE UDC constants, exact active-scenario overlay values, and no nonzero RHS with an all-zero equality LHS.

## Validation authorization

Run source conservation/reachability/stock-vintage/timeslice gates, application generation and preprocessing, semantic generated-data checks, and `glpsol --check` before optimization. If any gate fails, do not solve. Make exactly one BASE CBC attempt with a hard 360-second deadline and stop if it is not optimal. Only after BASE succeeds, make exactly one concurrent CBC attempt for COAL_PHASEOUT, RE and EV, also with a hard 360-second deadline per run, and stop after their first outcomes.

## Inherited oil-import floor correction

COAL_PHASEOUT now inherits BASE's zero `TotalTechnologyAnnualActivityLowerLimit` for the open oil-import backstop. The prior 2020–2034 positive floor had no retained physical or legal basis, contradicted the border-price ledger's endogenous-import classification, and mechanically compelled imports. It was removed rather than converted into an unsupported cap.

## Final validation results

The source preflight, generated-data semantic checks, application preprocessing,
and `glpsol --check` passed for every run. BASE was solved alone first; only after
it returned optimal were the three policy cases run concurrently. Each run made
one CBC optimization attempt with a hard 360-second deadline.

| Scenario | CBC status | Objective (MUSD) | Change from matched v36 | CBC solve time |
|---|---:|---:|---:|---:|
| BASE | Optimal | 892,605.9518 | +3.3137% | 118.28 s |
| COAL_PHASEOUT | Optimal | 910,058.7913 | +2.5744% | 292.89 s |
| RE | Optimal | 907,891.6669 | +3.7986% | 322.98 s |
| EV | Optimal | 874,394.3131 | +4.0278% | 206.51 s |

The EV nuclear equality emitted `0 = 0` rather than inheriting the EV target,
and the RE nuclear equality retained only its intended milestone overlays. The
COAL_PHASEOUT oil-import floor is absent from the generated matrix; imports are
endogenous (789.6732 PJ in 2020, 571.4819 PJ in 2034, and 575.4032 PJ in 2035).

## Known policy-definition limitation

The inherited COAL_PHASEOUT formulation is not a complete coal phaseout. Its
activity ceiling reduces `PHL_POW_CHP_COAL_OLD_{LUZ,VIS,MIN}` to zero in 2040,
but coal capacity built earlier as `PHL_POW_PP_COAL_{LUZ,VIS,MIN}` survives and
continues operating. In 2040 those candidate fleets retain 13.6379, 2.4708 and
2.7087 GW and produce 365.5733, 66.2306 and 72.6089 PJ in Luzon, Visayas and
Mindanao respectively. No additional restriction was added because the present
work only removed an unsupported oil-import floor; changing the coal-policy
boundary requires an explicit decision on whether the intended continuing
constraint covers legacy plants only, all coal generation, or all coal capacity.

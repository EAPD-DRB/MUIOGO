#!/usr/bin/env python3
"""Generic source-level physical-feasibility screen for MUIO/OSeMOSYS cases.

The screen constructs optimistic upper bounds, so a reported shortfall is a
deterministic contradiction.  A pass is not a proof that the complete coupled
LP is feasible: shared technology capacity, user-defined constraints, storage,
trade and route-mix coupling are deliberately relaxed when that favors
feasibility.

No technology or commodity names are assumed.  A historical-stock boundary is
an explicit model-calibration input supplied with --historical-through; it is
never inferred from names or embedded in this program.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


TOL = 1e-7
UNBOUNDED = 9999.0
MAX_PROPAGATIONS = 1_000_000


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def keyed(rows: list[dict[str, Any]], *fields: str) -> dict[tuple[Any, ...], dict[str, Any]]:
    return {tuple(row[field] for field in fields): row for row in rows}


def inherited_rows(table: dict[str, Any], parameter: str, scenario: str, base: str) -> list[dict[str, Any]]:
    """Resolve MUIO's null-valued scenario inheritance at row/year access time."""
    if scenario == base:
        return table[parameter][base]
    base_rows = keyed(table[parameter][base], *row_key_fields(table[parameter][base]))
    result = []
    fields = row_key_fields(table[parameter][scenario])
    for row in table[parameter][scenario]:
        merged = dict(row)
        source = base_rows[tuple(row[field] for field in fields)]
        for name, value in row.items():
            if value is None:
                merged[name] = source[name]
        result.append(merged)
    return result


def row_key_fields(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    if not rows:
        return ()
    preferred = ("TechId", "CommId", "MoId", "TsId", "ConId", "EmisId")
    return tuple(field for field in preferred if field in rows[0])


def scenario_rows(table: dict[str, Any], parameter: str, scenario: str, base: str) -> list[dict[str, Any]]:
    if scenario == base:
        return table[parameter][base]
    fields = row_key_fields(table[parameter][base])
    base_map = keyed(table[parameter][base], *fields)
    resolved = []
    for row in table[parameter][scenario]:
        source = base_map[tuple(row[field] for field in fields)]
        resolved.append({name: source[name] if value is None else value for name, value in row.items()})
    return resolved


def finite_limit(value: float) -> float:
    return math.inf if value >= UNBOUNDED else max(0.0, value)


def active_capacity(
    tech: str,
    year: str,
    years: tuple[str, ...],
    residual: dict[tuple[str], dict[str, Any]],
    max_investment: dict[tuple[str], dict[str, Any]],
    max_total: dict[tuple[str], dict[str, Any]],
    life: dict[str, Any],
    historical_through: int | None,
) -> float:
    capacity = float(residual[(tech,)][year])
    lifetime = int(float(life.get(tech, 100)))
    for vintage in years:
        age = int(year) - int(vintage)
        if not 0 <= age < lifetime:
            continue
        addition = finite_limit(float(max_investment[(tech,)][vintage]))
        historical_vintage = historical_through is not None and int(vintage) <= historical_through
        if historical_vintage and not math.isinf(addition):
            # A finite historical build envelope is not commissioned stock.
            # Unbounded investment is retained because MUIO commonly uses it
            # for capacity-free pass-throughs, conversions and supply borders.
            continue
        if math.isinf(addition):
            return math.inf
        capacity += addition
    total_limit = finite_limit(float(max_total[(tech,)][year]))
    return min(capacity, total_limit)


def minimum_active_capacity(
    tech: str,
    year: str,
    years: tuple[str, ...],
    residual: dict[tuple[str], dict[str, Any]],
    min_investment: dict[tuple[str], dict[str, Any]],
    min_total: dict[tuple[str], dict[str, Any]],
    life: dict[str, Any],
) -> float:
    """Lower bound implied by residual stock and explicit capacity minima."""
    capacity = float(residual[(tech,)][year])
    lifetime = int(float(life.get(tech, 100)))
    for vintage in years:
        age = int(year) - int(vintage)
        if 0 <= age < lifetime:
            capacity += max(0.0, float(min_investment[(tech,)][vintage]))
    return max(capacity, max(0.0, float(min_total[(tech,)][year])))


def allocate_minimum_input(
    demand: float,
    routes: list[dict[str, float]],
    input_commodity: str,
) -> float:
    """Optimistic lower bound on one input needed to produce a commodity."""
    remaining = demand
    used = 0.0
    ordered = sorted(routes, key=lambda route: route["inputs"].get(input_commodity, 0.0))
    for route in ordered:
        take = min(remaining, route["output_capacity"])
        used += take * route["inputs"].get(input_commodity, 0.0)
        remaining -= take
        if remaining <= TOL:
            break
    return used


def evaluate_slice(
    *,
    year: str,
    timeslice: str,
    year_split: float,
    direct_demand: dict[str, float],
    technologies: tuple[str, ...],
    routes_by_output: dict[str, list[tuple[str, Any, float]]],
    inputs_by_route: dict[tuple[str, Any], dict[str, float]],
    activity_ceiling: dict[str, float],
    tech_name: dict[str, str],
    commodity_name: dict[str, str],
) -> dict[str, Any]:
    required = defaultdict(float, direct_demand)
    propagated: dict[tuple[str, str], float] = defaultdict(float)
    queue = deque(commodity for commodity, value in required.items() if value > TOL)
    queued = set(queue)
    failures: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    forced_activity_lower: dict[str, float] = defaultdict(float)
    iterations = 0

    while queue:
        iterations += 1
        if iterations > MAX_PROPAGATIONS:
            failures.append({
                "kind": "propagation_did_not_converge",
                "year": year,
                "timeslice": timeslice,
            })
            break
        commodity = queue.popleft()
        queued.discard(commodity)
        demand = required[commodity]
        if demand <= TOL:
            continue

        route_records = []
        for tech, mode, output_ratio in routes_by_output.get(commodity, []):
            ceiling = activity_ceiling.get(tech, 0.0)
            output_capacity = ceiling * output_ratio
            if output_capacity <= TOL:
                continue
            route_records.append({
                "tech": tech,
                "mode": mode,
                "output_ratio": output_ratio,
                "output_capacity": output_capacity,
                "inputs": {
                    input_commodity: ratio / output_ratio
                    for input_commodity, ratio in inputs_by_route.get((tech, mode), {}).items()
                    if ratio > TOL
                },
            })

        production_upper = sum(route["output_capacity"] for route in route_records)
        headroom = production_upper - demand
        diagnostics.append({
            "commodity": commodity_name.get(commodity, commodity),
            "commodity_id": commodity,
            "required_rate": demand,
            "optimistic_production_upper_rate": production_upper,
            "headroom_rate": headroom,
            "producer_count": len(route_records),
            "producers": [
                {
                    "technology": tech_name.get(route["tech"], route["tech"]),
                    "technology_id": route["tech"],
                    "mode": route["mode"],
                    "output_capacity_rate": route["output_capacity"],
                }
                for route in route_records
            ],
        })
        if production_upper + TOL < demand:
            failures.append({
                "kind": "commodity_timeslice_shortfall",
                "year": year,
                "timeslice": timeslice,
                "commodity": commodity_name.get(commodity, commodity),
                "commodity_id": commodity,
                "required_rate": demand,
                "optimistic_production_upper_rate": production_upper,
                "headroom_rate": headroom,
                "producers": [
                    {
                        "technology": tech_name.get(route["tech"], route["tech"]),
                        "technology_id": route["tech"],
                        "mode": route["mode"],
                        "output_capacity_rate": route["output_capacity"],
                    }
                    for route in route_records
                ],
            })
            continue


        # A producer has a deterministic activity floor only for the portion
        # of demand that every combination of the other routes cannot cover.
        # This remains an optimistic relaxation when routes share capacity.
        for route in route_records:
            other_output = production_upper - route["output_capacity"]
            forced_output = max(0.0, demand - other_output)
            forced_activity_lower[route["tech"]] = max(
                forced_activity_lower[route["tech"]],
                forced_output / route["output_ratio"],
            )

        input_commodities = {
            input_commodity
            for route in route_records
            for input_commodity in route["inputs"]
            if input_commodity != commodity
        }
        for input_commodity in input_commodities:
            lower_bound = allocate_minimum_input(demand, route_records, input_commodity)
            key = (commodity, input_commodity)
            delta = lower_bound - propagated[key]
            if delta > TOL:
                propagated[key] = lower_bound
                required[input_commodity] += delta
                if input_commodity not in queued:
                    queue.append(input_commodity)
                    queued.add(input_commodity)

    worst = min(diagnostics, key=lambda row: row["headroom_rate"], default=None)
    return {
        "year": year,
        "timeslice": timeslice,
        "year_split": year_split,
        "status": "failed" if failures else "passed",
        "worst_commodity": worst,
        "failures": failures,
        "commodity_diagnostics": diagnostics,
        "forced_activity_lower_rate": dict(forced_activity_lower),
        "propagation_iterations": iterations,
    }


def interval_term(coefficient: float, lower: float, upper: float) -> tuple[float, float]:
    if coefficient >= 0:
        return coefficient * lower, coefficient * upper
    return coefficient * upper, coefficient * lower


def validate_case(
    case: Path,
    *,
    scenario: str | None = None,
    historical_through: int | None = None,
) -> dict[str, Any]:
    gen = read_json(case / "genData.json")
    ryt = read_json(case / "RYT.json")
    rytts = read_json(case / "RYTTs.json")
    rytcm = read_json(case / "RYTCM.json")
    ryc = read_json(case / "RYC.json")
    rycts = read_json(case / "RYCTs.json")
    ryts = read_json(case / "RYTs.json")
    rt = read_json(case / "RT.json")
    rytcn = read_json(case / "RYTCn.json")
    rycn = read_json(case / "RYCn.json")

    scenarios = tuple(item["ScenarioId"] for item in gen["osy-scenarios"])
    base = scenarios[0]
    selected = scenario or base
    if selected not in scenarios:
        raise ValueError(f"unknown scenario {selected!r}; expected one of {scenarios}")

    years = tuple(str(year) for year in gen["osy-years"])
    # The "Ts" label is free-form case metadata: numeric in Philippines cases,
    # season/day codes ("S1D2", "SD") in Fiji and CLEWs Demo.  Every timeslice is
    # evaluated independently below, so this ordering is presentational only.
    timeslices = tuple(
        item["TsId"] for item in sorted(gen["osy-ts"], key=lambda row: str(row["Ts"]))
    )
    technologies = tuple(item["TechId"] for item in gen["osy-tech"])
    tech_name = {item["TechId"]: item["Tech"] for item in gen["osy-tech"]}
    commodity_name = {item["CommId"]: item["Comm"] for item in gen["osy-comm"]}

    residual = keyed(scenario_rows(ryt, "RC", selected, base), "TechId")
    max_investment = keyed(scenario_rows(ryt, "TAMaxCI", selected, base), "TechId")
    min_investment = keyed(scenario_rows(ryt, "TAMinCI", selected, base), "TechId")
    max_total = keyed(scenario_rows(ryt, "TAMaxC", selected, base), "TechId")
    min_total = keyed(scenario_rows(ryt, "TAMinC", selected, base), "TechId")
    availability = keyed(scenario_rows(ryt, "AF", selected, base), "TechId")
    activity_limit = keyed(scenario_rows(ryt, "TAU", selected, base), "TechId")
    activity_minimum = keyed(scenario_rows(ryt, "TAL", selected, base), "TechId")
    capacity_factor = keyed(scenario_rows(rytts, "CF", selected, base), "TechId", "TsId")
    iar = scenario_rows(rytcm, "IAR", selected, base)
    oar = scenario_rows(rytcm, "OAR", selected, base)
    specified_demand = keyed(scenario_rows(ryc, "SAD", selected, base), "CommId")
    accumulated_demand = keyed(scenario_rows(ryc, "AAD", selected, base), "CommId")
    demand_profile = keyed(scenario_rows(rycts, "SDP", selected, base), "CommId", "TsId")
    year_splits = keyed(scenario_rows(ryts, "YS", selected, base), "TsId")
    life = rt["OL"][base][0]
    cau = rt["CAU"][base][0]

    inputs_by_route: dict[tuple[str, Any], dict[str, float]] = defaultdict(dict)
    for row in iar:
        inputs_by_route[(row["TechId"], row["MoId"])][row["CommId"]] = row
    output_rows: dict[tuple[str, Any, str], dict[str, Any]] = {}
    for row in oar:
        output_rows[(row["TechId"], row["MoId"], row["CommId"])] = row

    slice_results = []
    all_failures = []
    udc_results = []
    for year in years:
        capacity = {
            tech: active_capacity(
                tech,
                year,
                years,
                residual,
                max_investment,
                max_total,
                life,
                historical_through,
            )
            for tech in technologies
        }
        weighted_cf = {
            tech: sum(
                float(capacity_factor[(tech, ts)][year]) * float(year_splits[(ts,)][year])
                for ts in timeslices
            )
            for tech in technologies
        }
        annual_envelope = {
            tech: capacity[tech]
            * float(cau[tech])
            * float(availability[(tech,)][year])
            * weighted_cf[tech]
            for tech in technologies
        }

        forced_annual_from_slices: dict[str, float] = defaultdict(float)

        for ts in timeslices:
            split = float(year_splits[(ts,)][year])
            if split <= 0:
                continue
            activity_ceiling = {}
            for tech in technologies:
                caa4 = capacity[tech] * float(cau[tech]) * float(capacity_factor[(tech, ts)][year])
                cab1 = annual_envelope[tech] / split
                aac2 = finite_limit(float(activity_limit[(tech,)][year])) / split
                activity_ceiling[tech] = min(caa4, cab1, aac2)

            routes_by_output: dict[str, list[tuple[str, Any, float]]] = defaultdict(list)
            route_inputs: dict[tuple[str, Any], dict[str, float]] = defaultdict(dict)
            for (tech, mode), rows in inputs_by_route.items():
                route_inputs[(tech, mode)] = {
                    commodity: float(row[year]) for commodity, row in rows.items()
                }
            for (tech, mode, commodity), row in output_rows.items():
                ratio = float(row[year])
                if ratio > TOL:
                    routes_by_output[commodity].append((tech, mode, ratio))

            direct_demand = {}
            for (commodity,), row in specified_demand.items():
                annual = float(row[year])
                profile_row = demand_profile.get((commodity, ts))
                profile = float(profile_row[year]) if profile_row else 0.0
                rate = annual * profile / split
                if rate > TOL:
                    direct_demand[commodity] = rate

            result = evaluate_slice(
                year=year,
                timeslice=ts,
                year_split=split,
                direct_demand=direct_demand,
                technologies=technologies,
                routes_by_output=routes_by_output,
                inputs_by_route=route_inputs,
                activity_ceiling=activity_ceiling,
                tech_name=tech_name,
                commodity_name=commodity_name,
            )
            slice_results.append(result)
            all_failures.extend(result["failures"])
            for tech, rate in result["forced_activity_lower_rate"].items():
                forced_annual_from_slices[tech] += rate * split

        # AccumulatedAnnualDemand is governed by the annual balance rather
        # than a demand profile.  Evaluate it independently and combine the
        # resulting technology floors optimistically with the slice floors.
        annual_routes: dict[str, list[tuple[str, Any, float]]] = defaultdict(list)
        annual_inputs: dict[tuple[str, Any], dict[str, float]] = defaultdict(dict)
        for (tech, mode), rows in inputs_by_route.items():
            annual_inputs[(tech, mode)] = {
                commodity: float(row[year]) for commodity, row in rows.items()
            }
        for (tech, mode, commodity), row in output_rows.items():
            ratio = float(row[year])
            if ratio > TOL:
                annual_routes[commodity].append((tech, mode, ratio))
        aad_direct = {
            commodity: float(row[year])
            for (commodity,), row in accumulated_demand.items()
            if float(row[year]) > TOL
        }
        annual_result = evaluate_slice(
            year=year,
            timeslice="ANNUAL",
            year_split=1.0,
            direct_demand=aad_direct,
            technologies=technologies,
            routes_by_output=annual_routes,
            inputs_by_route=annual_inputs,
            activity_ceiling={
                tech: min(
                    annual_envelope[tech],
                    finite_limit(float(activity_limit[(tech,)][year])),
                )
                for tech in technologies
            },
            tech_name=tech_name,
            commodity_name=commodity_name,
        )
        annual_result["kind"] = "accumulated_annual_demand"
        all_failures.extend(annual_result["failures"])

        forced_annual = {
            tech: max(
                forced_annual_from_slices.get(tech, 0.0),
                annual_result["forced_activity_lower_rate"].get(tech, 0.0),
                max(0.0, float(activity_minimum[(tech,)][year])),
            )
            for tech in technologies
        }

        # Generic interval screen for active user-defined constraints.  It
        # proves a contradiction only when even independently favorable
        # capacity/activity bounds cannot reach the required interval.
        constraints = {row["ConId"]: row for row in gen.get("osy-constraints", [])}
        constants = keyed(scenario_rows(rycn, "UCC", selected, base), "ConId")
        multipliers = {
            key: keyed(scenario_rows(rytcn, key, selected, base), "TechId", "ConId")
            for key in ("CCM", "CNCM", "CAM")
        }
        min_capacity = {
            tech: minimum_active_capacity(
                tech, year, years, residual, min_investment, min_total, life
            )
            for tech in technologies
        }
        for con_id, metadata in constraints.items():
            if (con_id,) not in constants:
                continue
            lower_lhs = 0.0
            upper_lhs = 0.0
            for tech in technologies:
                def coefficient(parameter: str) -> float:
                    row = multipliers[parameter].get((tech, con_id))
                    return float(row[year]) if row is not None else 0.0

                variables = (
                    (
                        coefficient("CCM"),
                        min_capacity[tech], capacity[tech],
                    ),
                    (
                        coefficient("CNCM"),
                        max(0.0, float(min_investment[(tech,)][year])),
                        finite_limit(float(max_investment[(tech,)][year])),
                    ),
                    (
                        coefficient("CAM"),
                        forced_annual[tech],
                        min(
                            annual_envelope[tech],
                            finite_limit(float(activity_limit[(tech,)][year])),
                        ),
                    ),
                )
                for coefficient, lower, upper in variables:
                    term_lower, term_upper = interval_term(coefficient, lower, upper)
                    lower_lhs += term_lower
                    upper_lhs += term_upper
            constant = float(constants[(con_id,)][year])
            tag = int(metadata.get("Tag", metadata.get("tag", 0)))
            failed = (
                lower_lhs > constant + TOL if tag == 0
                else constant < lower_lhs - TOL or constant > upper_lhs + TOL
            )
            check = {
                "constraint": metadata.get("Con", con_id),
                "constraint_id": con_id,
                "year": year,
                "tag": tag,
                "optimistic_lhs_interval": [lower_lhs, upper_lhs],
                "constant": constant,
                "status": "failed" if failed else "passed_no_deterministic_contradiction",
            }
            udc_results.append(check)
            if failed:
                all_failures.append({"kind": "user_defined_constraint_interval", **check})

    worst_slices = sorted(
        (
            result for result in slice_results
            if result["worst_commodity"] is not None
        ),
        key=lambda result: result["worst_commodity"]["headroom_rate"],
    )[:20]
    return {
        "schema": "generic-osemosys-physical-gate-v1",
        "case": str(case),
        "scenario": selected,
        "historical_stock_through": historical_through,
        "method": "optimistic recursive source-level capacity and commodity bounds",
        "status": "failed" if all_failures else "passed_no_deterministic_contradiction",
        "optimizer_runs": 0,
        "model_generation_runs": 0,
        "years_checked": len(years),
        "timeslices_checked": len(slice_results),
        "user_defined_constraint_years_checked": len(udc_results),
        "failure_count": len(all_failures),
        "failures": all_failures,
        "user_defined_constraints": udc_results,
        "worst_slices": worst_slices,
        "limitations": [
            "A pass is not a proof of full-model feasibility.",
            "Shared producer capacity and route-mix coupling are relaxed optimistically.",
            "Storage chronology and trade coupling are not yet included.",
            "AccumulatedAnnualDemand and user-defined constraints use optimistic independent-route intervals.",
            "Historical-stock treatment requires an explicit --historical-through classification.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--scenario")
    parser.add_argument("--historical-through", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    report = validate_case(
        args.case.resolve(),
        scenario=args.scenario,
        historical_through=args.historical_through,
    )
    payload = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    if not args.quiet:
        print(payload, end="")
    if report["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

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
        "propagation_iterations": iterations,
    }


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
    max_total = keyed(scenario_rows(ryt, "TAMaxC", selected, base), "TechId")
    availability = keyed(scenario_rows(ryt, "AF", selected, base), "TechId")
    activity_limit = keyed(scenario_rows(ryt, "TAU", selected, base), "TechId")
    capacity_factor = keyed(scenario_rows(rytts, "CF", selected, base), "TechId", "TsId")
    iar = scenario_rows(rytcm, "IAR", selected, base)
    oar = scenario_rows(rytcm, "OAR", selected, base)
    specified_demand = keyed(scenario_rows(ryc, "SAD", selected, base), "CommId")
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
        "failure_count": len(all_failures),
        "failures": all_failures,
        "worst_slices": worst_slices,
        "limitations": [
            "A pass is not a proof of full-model feasibility.",
            "Shared producer capacity and route-mix coupling are relaxed optimistically.",
            "AccumulatedAnnualDemand, storage, trade and user-defined constraints are not yet included.",
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

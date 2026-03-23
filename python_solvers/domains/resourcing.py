"""
Domain: Resource Allocation (IT / Cloud)
Maps raw resource/task input → common schema with CPU/RAM dimensions.
"""
from typing import Any, Dict, List

from python_solvers.domains.ir_utils import finalize_ir


def _safe_list(values: List[Any], length: int, default: float = 0.0) -> List[Any]:
    if not isinstance(values, list):
        return [default] * length
    if len(values) >= length:
        return values[:length]
    return values + [default] * (length - len(values))


def map_params(raw_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map raw resource/task payload to common schema.
    Input can be:
      - Containers/Tasks (list of dicts) with CPU, RAM, Name, Cost
      - Or Items (list of names) + CPU + RAM + Values lists
    """
    items = raw_params.get("Containers", raw_params.get("Tasks", raw_params.get("Items", [])))
    
    if isinstance(items, list) and items and isinstance(items[0], dict):
        names = [x.get("Name", x.get("id", f"Task_{i}")) for i, x in enumerate(items)]
        cpu = [float(x.get("CPU", x.get("Cpu", 0))) for x in items]
        ram = [float(x.get("RAM", x.get("Memory", 0))) for x in items]
        values = [float(x.get("Cost", x.get("Priority", 0))) for x in items]
    else:
        names = list(raw_params.get("Items", []))
        cpu = raw_params.get("CPU", raw_params.get("Cpu", [0] * len(names)))
        ram = raw_params.get("RAM", raw_params.get("Memory", [0] * len(names)))
        values = raw_params.get("Values", raw_params.get("Costs", [0] * len(names)))

    n = len(names)
    servers = raw_params.get("Servers", raw_params.get("Nodes", [{"CPU": 64, "RAM": 128}]))
    if isinstance(servers, dict):
        servers = [servers]
    capacity_cpu = servers[0].get("CPU", servers[0].get("Cpu", 64)) if servers else 64
    capacity_ram = servers[0].get("RAM", servers[0].get("Memory", 128)) if servers else 128
    sense = raw_params.get("Sense", "minimize")

    mapped = {
        "Items": names,
        "Weights": _safe_list(cpu, n),
        "WeightsRAM": _safe_list(ram, n),
        "Values": _safe_list(values, n),
        "Demands": raw_params.get("Demands", {name: 1 for name in names}),
        "Capacity": capacity_cpu,
        "CapacityRAM": capacity_ram,
        "Sense": sense,
        "Servers": servers,
        "Mode": "resourcing",
    }
    mapped["IR"] = build_ir(mapped)
    mapped["ST"] = build_st_spec(mapped, raw_params)
    return mapped


def build_ir(params: Dict[str, Any]) -> Dict[str, Any]:
    items = list(params.get("Items", []))
    cpu = _safe_list(params.get("Weights", []), len(items), 0.0)
    ram = _safe_list(params.get("WeightsRAM", []), len(items), 0.0)
    values = _safe_list(params.get("Values", []), len(items), 0.0)
    demands = params.get("Demands", {}) or {}
    cap_cpu = float(params.get("Capacity", 0))
    cap_ram = float(params.get("CapacityRAM", 0))
    relax = bool(params.get("Relax") or params.get("LP") or params.get("lp_relaxation"))

    variables = []
    objective = []
    constraints = [
        {"name": "cpu_capacity", "type": "linear", "terms": [], "sense": "<=", "rhs": cap_cpu},
        {"name": "ram_capacity", "type": "linear", "terms": [], "sense": "<=", "rhs": cap_ram},
    ]

    for idx, item in enumerate(items):
        name = f"X_{idx}"
        variables.append({"name": name, "type": "Continuous" if relax else "Integer", "lb": 0})
        objective.append({"var": name, "coef": float(values[idx])})
        constraints[0]["terms"].append({"var": name, "coef": float(cpu[idx])})
        constraints[1]["terms"].append({"var": name, "coef": float(ram[idx])})
        constraints.append({
            "name": f"demand_{idx}",
            "type": "linear",
            "terms": [{"var": name, "coef": 1}],
            "sense": "<=",
            "rhs": float(demands.get(item, 1)),
        })

    sense = str(params.get("Sense", "minimize")).lower()
    return finalize_ir(
        {
            "meta": {"domain": "resourcing", "sense": sense},
            "variables": variables,
            "objective": objective,
            "constraints": constraints,
        },
        domain="resourcing",
        sense=sense,
    )


def build_st_spec(params: Dict[str, Any], raw_params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    items = list(params.get("Items", []))
    cpu = _safe_list(params.get("Weights", []), len(items), 0.0)
    ram = _safe_list(params.get("WeightsRAM", []), len(items), 0.0)
    values = _safe_list(params.get("Values", []), len(items), 0.0)
    demands = params.get("Demands", {}) or {}
    cap_cpu = float(params.get("Capacity", 0))
    cap_ram = float(params.get("CapacityRAM", 0))
    scenarios = []
    if isinstance(raw_params, dict):
        scenarios = raw_params.get("Scenarios", []) or raw_params.get("Uncertainty", []) or []

    if not isinstance(scenarios, list) or not scenarios:
        scenarios = [{"Name": "base", "Probability": 1.0}]

    total_prob = sum(float(s.get("Probability", 0) or 0) for s in scenarios if isinstance(s, dict))
    if total_prob <= 0:
        total_prob = float(len(scenarios))

    penalty = 0.0
    if isinstance(raw_params, dict):
        penalty = float(raw_params.get("ShortfallPenalty", raw_params.get("Penalty", 1000.0)) or 1000.0)

    normalized_scenarios = []
    for idx, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            continue
        prob = float(scenario.get("Probability", 0) or 0)
        if prob <= 0 and total_prob > 0:
            prob = 1.0
        weight = prob / total_prob if total_prob > 0 else 0.0
        scenario_values = scenario.get("Values", {}) or scenario.get("Costs", {}) or {}
        scenario_demands = scenario.get("Demands", {}) or {}
        normalized_scenarios.append({
            "name": str(scenario.get("Name", f"scenario_{idx}")),
            "probability": weight,
            "values": {
                item: float(scenario_values.get(item, values[item_idx])) if isinstance(scenario_values, dict) else float(values[item_idx])
                for item_idx, item in enumerate(items)
            },
            "demands": {
                item: float(scenario_demands.get(item, demands.get(item, 1))) if isinstance(scenario_demands, dict) else float(demands.get(item, 1))
                for item in items
            },
        })

    variables = []
    objective = []
    constraints = [
        {"name": "cpu_capacity", "type": "linear", "terms": [], "sense": "<=", "rhs": cap_cpu},
        {"name": "ram_capacity", "type": "linear", "terms": [], "sense": "<=", "rhs": cap_ram},
    ]

    for idx, item in enumerate(items):
        name = f"X_{idx}"
        variables.append({"name": name, "type": "Integer", "lb": 0})
        expected_value = 0.0
        expected_limit = float(demands.get(item, 1))

        for scenario in scenarios:
            if not isinstance(scenario, dict):
                continue
            prob = float(scenario.get("Probability", 0) or 0)
            if prob <= 0 and total_prob > 0:
                prob = 1.0
            weight = prob / total_prob if total_prob > 0 else 0.0

            scenario_values = scenario.get("Values", {}) or scenario.get("Costs", {}) or {}
            scenario_demands = scenario.get("Demands", {}) or {}

            scenario_value = scenario_values.get(item, values[idx]) if isinstance(scenario_values, dict) else values[idx]
            scenario_limit = scenario_demands.get(item, demands.get(item, 1)) if isinstance(scenario_demands, dict) else demands.get(item, 1)

            expected_value += weight * float(scenario_value)
            expected_limit = min(expected_limit, float(scenario_limit))

        objective.append({"var": name, "coef": expected_value})
        constraints[0]["terms"].append({"var": name, "coef": float(cpu[idx])})
        constraints[1]["terms"].append({"var": name, "coef": float(ram[idx])})
        constraints.append({
            "name": f"scenario_demand_{idx}",
            "type": "linear",
            "terms": [{"var": name, "coef": 1}],
            "sense": "<=",
            "rhs": expected_limit,
        })

    sense = str(params.get("Sense", "minimize")).lower()
    st_ir = finalize_ir(
        {
            "meta": {
                "domain": "resourcing",
                "solver": "st",
                "sense": sense,
                "scenario_count": len(normalized_scenarios),
            },
            "variables": variables,
            "objective": objective,
            "constraints": constraints,
        },
        domain="resourcing",
        sense=sense,
    )

    return {
        "meta": {
            "domain": "resourcing",
            "solver": "st",
            "sense": sense,
            "scenario_count": len(normalized_scenarios),
            "ir_stats": st_ir.get("meta", {}).get("stats", {}),
        },
        "items": items,
        "cpu": {items[i]: float(cpu[i]) for i in range(len(items))},
        "ram": {items[i]: float(ram[i]) for i in range(len(items))},
        "values": {items[i]: float(values[i]) for i in range(len(items))},
        "demands": {item: float(demands.get(item, 1)) for item in items},
        "capacity_cpu": cap_cpu,
        "capacity_ram": cap_ram,
        "shortfall_penalty": penalty,
        "scenarios": normalized_scenarios,
        "variables": st_ir.get("variables", []),
        "objective": st_ir.get("objective", []),
        "constraints": st_ir.get("constraints", []),
    }

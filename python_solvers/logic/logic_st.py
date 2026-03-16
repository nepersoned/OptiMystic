"""Stochastic optimization builder with scenario-based Pyomo support for resourcing."""
from typing import Any, Dict, List, Tuple

try:
    import pyomo.environ as pyo
except ImportError:
    pyo = None


def _build_resourcing_model(spec: Dict[str, Any]) -> Any:
    if pyo is None:
        raise ValueError("Pyomo required for stochastic optimization")

    items = list(spec.get("items", []))
    scenarios = list(spec.get("scenarios", []))
    if not scenarios:
        scenarios = [{"name": "base", "probability": 1.0, "values": dict(spec.get("values", {}) or {}), "demands": dict(spec.get("demands", {}) or {})}]
    cap_cpu = float(spec.get("capacity_cpu", 0))
    cap_ram = float(spec.get("capacity_ram", 0))
    cpu = spec.get("cpu", {}) or {}
    ram = spec.get("ram", {}) or {}
    values = spec.get("values", {}) or {}
    penalty = float(spec.get("shortfall_penalty", 1000.0))
    sense = str((spec.get("meta") or {}).get("sense", "minimize")).lower()

    model = pyo.ConcreteModel()
    model.ITEMS = pyo.Set(initialize=items, ordered=True)
    model.SCENARIOS = pyo.Set(initialize=[s.get("name", f"scenario_{i}") for i, s in enumerate(scenarios)], ordered=True)

    probability_map = {s.get("name", f"scenario_{i}"): float(s.get("probability", 0.0)) for i, s in enumerate(scenarios)}
    demand_map = {(s.get("name", f"scenario_{i}"), item): float((s.get("demands") or {}).get(item, 0.0)) for i, s in enumerate(scenarios) for item in items}
    value_map = {(s.get("name", f"scenario_{i}"), item): float((s.get("values") or {}).get(item, values.get(item, 0.0))) for i, s in enumerate(scenarios) for item in items}

    model.X = pyo.Var(model.ITEMS, domain=pyo.NonNegativeIntegers)
    model.Shortfall = pyo.Var(model.SCENARIOS, model.ITEMS, domain=pyo.NonNegativeReals)

    model.CPU_CAPACITY = pyo.Constraint(expr=sum(float(cpu.get(item, 0.0)) * model.X[item] for item in model.ITEMS) <= cap_cpu)
    model.RAM_CAPACITY = pyo.Constraint(expr=sum(float(ram.get(item, 0.0)) * model.X[item] for item in model.ITEMS) <= cap_ram)

    def demand_rule(m, scenario, item):
        return m.X[item] + m.Shortfall[scenario, item] >= demand_map[(scenario, item)]

    model.DEMAND = pyo.Constraint(model.SCENARIOS, model.ITEMS, rule=demand_rule)

    service_value = sum(
        probability_map[scenario] * value_map[(scenario, item)] * model.X[item]
        for scenario in model.SCENARIOS
        for item in model.ITEMS
    )
    shortfall_cost = sum(
        probability_map[scenario] * penalty * model.Shortfall[scenario, item]
        for scenario in model.SCENARIOS
        for item in model.ITEMS
    )

    if sense == "maximize":
        model.OBJ = pyo.Objective(expr=service_value - shortfall_cost, sense=pyo.maximize)
    else:
        model.OBJ = pyo.Objective(expr=shortfall_cost - service_value, sense=pyo.minimize)

    return model


def build_model(domain: str, params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    if not isinstance(params, dict):
        raise ValueError(f"Params missing for domain '{domain}'")

    if domain == "resourcing":
        spec = params.get("ST")
        if not isinstance(spec, dict):
            raise ValueError("ST spec missing for resourcing")
        model = _build_resourcing_model(spec)
        variables = list((spec.get("variables") or []))
        variables.extend(
            {"name": f"Shortfall_{s.get('name', f'scenario_{i}')}_{item}", "type": "Continuous", "lb": 0}
            for i, s in enumerate(spec.get("scenarios", []))
            for item in spec.get("items", [])
        )
        return (model, [], variables)

    ir = params.get("IR")
    if not isinstance(ir, dict):
        raise ValueError(f"IR missing for domain '{domain}'")

    objective = ir.get("objective", [])
    constraints = ir.get("constraints", [])
    variables = ir.get("variables", [])

    if not isinstance(objective, list) or not isinstance(constraints, list) or not isinstance(variables, list):
        raise ValueError("Invalid IR structure")

    return (objective, constraints, variables)


def solve_stochastic(params):
    objective, constraints, variables = build_model(str(params.get("Mode", "")), params)
    return {
        "status": "Ready",
        "engine": "ST",
        "objective": objective,
        "constraints": constraints,
        "variables": variables,
    }

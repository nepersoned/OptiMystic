"""
Domain: Packing / Knapsack (Logistics)
Maps raw packing/cargo input → common schema.
"""
from typing import Any, Dict, List

from python_solvers.domains.ir_utils import finalize_ir


def _safe_list(values: List[Any], length: int, default: float = 0.0) -> List[Any]:
    if not isinstance(values, list):
        return [default] * length
    if len(values) >= length:
        return values[:length]
    return values + [default] * (length - len(values))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def map_params(raw_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map raw packing/cargo payload to common schema.
    Input can be:
      - Items (list of dicts) with Weight, Value, Name
      - Or Items (list of names) + Weights + Values lists
    """
    items = raw_params.get("Items", raw_params.get("Cargo", []))
    
    if isinstance(items, list) and items and isinstance(items[0], dict):
        names = [x.get("Name", x.get("id", f"Item_{i}")) for i, x in enumerate(items)]
        weights = [float(x.get("Weight", x.get("weight", 0))) for x in items]
        values = [float(x.get("Value", x.get("Priority", x.get("priority", 1)))) for x in items]
        item_demands = {
            str(name): max(0.0, _safe_float(item.get("Demand", item.get("demand", 1)), 1.0))
            for name, item in zip(names, items)
            if str(name).strip()
        }
        overrides = raw_params.get("Demands", {})
        normalized_overrides = {}
        if isinstance(overrides, dict):
            normalized_overrides = {
                str(k): max(0.0, _safe_float(v, item_demands.get(str(k), 1.0)))
                for k, v in overrides.items()
                if str(k).strip()
            }
        demands = {**item_demands, **normalized_overrides}
    else:
        names = list(raw_params.get("Items", []))
        weights = raw_params.get("Weights", raw_params.get("Volumes", [0] * len(names)))
        values = raw_params.get("Values", raw_params.get("Priorities", [1] * len(names)))
        demands = raw_params.get("Demands", {})

    if not isinstance(demands, dict):
        demands = {}

    vehicles = raw_params.get("Vehicles", raw_params.get("Trucks", [{"Capacity": 5000, "Cost": 1}]))
    if isinstance(vehicles, (int, float)):
        vehicles = [{"Capacity": float(vehicles), "Cost": 1}]
    capacity = vehicles[0].get("Capacity", vehicles[0].get("MaxWeight", 5000)) if vehicles else 5000
    sense = raw_params.get("Sense", "maximize")

    mapped = {
        "Items": names,
        "Weights": _safe_list(weights, len(names)),
        "Values": _safe_list(values, len(names)),
        "Demands": demands if demands else {n: 1 for n in names},
        "Capacity": capacity,
        "Sense": sense,
        "Vehicles": vehicles,
        "Mode": "packing",
    }
    mapped["IR"] = build_ir(mapped)
    return mapped


def build_ir(params: Dict[str, Any]) -> Dict[str, Any]:
    items = list(params.get("Items", []))
    weights = _safe_list(params.get("Weights", []), len(items), 0.0)
    values = _safe_list(params.get("Values", []), len(items), 0.0)
    demands = params.get("Demands", {}) or {}
    capacity = float(params.get("Capacity", 0))
    relax = bool(params.get("Relax") or params.get("LP") or params.get("lp_relaxation"))

    variables = []
    objective = []
    constraints = [{
        "name": "capacity",
        "type": "linear",
        "terms": [],
        "sense": "<=",
        "rhs": capacity,
    }]

    for idx, item in enumerate(items):
        name = f"X_{idx}"
        variables.append({"name": name, "type": "Continuous" if relax else "Integer", "lb": 0})
        objective.append({"var": name, "coef": float(values[idx])})
        constraints[0]["terms"].append({"var": name, "coef": float(weights[idx])})
        constraints.append({
            "name": f"demand_{idx}",
            "type": "linear",
            "terms": [{"var": name, "coef": 1}],
            "sense": "<=",
            "rhs": float(demands.get(item, 1)),
        })

    sense = str(params.get("Sense", "maximize")).lower()
    return finalize_ir(
        {
            "meta": {"domain": "packing", "sense": sense},
            "variables": variables,
            "objective": objective,
            "constraints": constraints,
        },
        domain="packing",
        sense=sense,
    )

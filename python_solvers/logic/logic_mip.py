"""
MIP model for cutting (and future modes). Pyomo only; same math as legacy logic_cutting.
"""
import re
from typing import Any, Dict, List, Tuple

try:
    import pyomo.environ as pyo
except ImportError:
    pyo = None


def _clean_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "_", str(name))


def _safe_list(values: List[Any], length: int, default: float = 0.0) -> List[Any]:
    if not isinstance(values, list):
        return [default] * length
    if len(values) >= length:
        return values[:length]
    return values + [default] * (length - len(values))


def _is_relaxed(params: Dict[str, Any]) -> bool:
    return bool(params.get("Relax") or params.get("LP") or params.get("lp_relaxation"))


def build_model(domain: str, params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    """
    Build MIP model for given domain.
    Returns (pyomo_model, [], []) for solver_engine compatibility.
    """
    if domain == "cutting":
        return _build_cutting_mip(params)
    if domain == "packing":
        return _build_packing_mip(params)
    if domain == "resourcing":
        return _build_resource_mip(params)
    if domain == "scheduling":
        return _build_scheduling_mip(params)
    
    return [], [], []


def _build_cutting_mip(params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    """
    Build cutting MIP as Pyomo ConcreteModel. Same math: bin use, capacity, demand.
    Returns (model, [], []) so solver_engine can solve(model).
    
    Now compatible with flexible input from domains.cutting.map_params().
    """
    # Only return variable, constraint, objective data for engine assembly
    items = list(params.get("Items", []))
    item_lens = _safe_list(params.get("Weights", params.get("ItemLens", [])), len(items), 1.0)
    demands = params.get("Demands", {})
    prices = params.get("Values", params.get("Prices", {}))
    stocks = params.get("Stocks", [{"Name": "Default", "Length": 1000, "Cost": 1, "Limit": 50}])
    if not stocks:
        stocks = [{"Name": "Default", "Length": 1000, "Cost": 1, "Limit": 50}]
    sense = params.get("Sense", "minimize")
    kerf = float(params.get("Kerf", 0.0))
    n_stocks = len(stocks)
    n_items = len(items)
    max_bins = min(30, max(int(float(s.get("Limit", 30))) for s in stocks)) if stocks else 30
    # Variable definitions
    variables = []
    for s in range(n_stocks):
        for b in range(max_bins):
            variables.append({"name": f"Use_{s}_{b}", "type": "Binary"})
    for i in range(n_items):
        for s in range(n_stocks):
            for b in range(max_bins):
                variables.append({"name": f"Cut_{i}_{s}_{b}", "type": "Integer"})
    # Objective definition
    objective = []
    if sense == "minimize":
        for s in range(n_stocks):
            for b in range(max_bins):
                objective.append({"var": f"Use_{s}_{b}", "coef": float(stocks[s]["Cost"])})
    else:
        for i in range(n_items):
            for s in range(n_stocks):
                for b in range(max_bins):
                    objective.append({"var": f"Cut_{i}_{s}_{b}", "coef": float(prices.get(items[i], 0))})
    # Constraints
    constraints = []
    # Capacity constraints
    for s in range(n_stocks):
        for b in range(max_bins):
            terms = []
            for i in range(n_items):
                terms.append({"var": f"Cut_{i}_{s}_{b}", "coef": float(item_lens[i]) + kerf})
            terms.append({"var": f"Use_{s}_{b}", "coef": -(float(stocks[s]["Length"]) + kerf)})
            constraints.append({"type": "linear", "terms": terms, "sense": "<=", "rhs": 0})
    # Demand constraints
    for i in range(n_items):
        terms = []
        for s in range(n_stocks):
            for b in range(max_bins):
                terms.append({"var": f"Cut_{i}_{s}_{b}", "coef": 1})
        constraints.append({"type": "linear", "terms": terms, "sense": ">=", "rhs": float(demands.get(items[i], 0))})
    return (None, objective, constraints, variables)


def _build_packing_mip(params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    """Build 1D knapsack MIP/LP for packing."""
    # Only return variable, constraint, objective data for engine assembly
    items = list(params.get("Items", []))
    weights = _safe_list(params.get("Weights", []), len(items), 0.0)
    values = _safe_list(params.get("Values", []), len(items), 0.0)
    demands = params.get("Demands", {}) or {}
    capacity = float(params.get("Capacity", 0))
    sense = params.get("Sense", "maximize")
    relax = _is_relaxed(params)
    variables = []
    for i in range(len(items)):
        vtype = "Continuous" if relax else "Integer"
        variables.append({"name": f"X_{i}", "type": vtype})
    # Objective
    objective = []
    for i in range(len(items)):
        objective.append({"var": f"X_{i}", "coef": values[i]})
    # Constraints
    constraints = []
    # Capacity constraint
    terms = []
    for i in range(len(items)):
        terms.append({"var": f"X_{i}", "coef": weights[i]})
    constraints.append({"type": "linear", "terms": terms, "sense": "<=", "rhs": capacity})
    # Demand/limit constraints
    for i in range(len(items)):
        rhs = float(demands.get(items[i], 1))
        constraints.append({"type": "linear", "terms": [{"var": f"X_{i}", "coef": 1}], "sense": "<=", "rhs": rhs})
    return (None, objective, constraints, variables)


def _build_resource_mip(params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    """Build 2D knapsack MIP/LP for resource allocation (CPU/RAM)."""
    # Only return variable, constraint, objective data for engine assembly
    items = list(params.get("Items", []))
    cpu = _safe_list(params.get("Weights", []), len(items), 0.0)
    ram = _safe_list(params.get("WeightsRAM", []), len(items), 0.0)
    values = _safe_list(params.get("Values", []), len(items), 0.0)
    demands = params.get("Demands", {}) or {}
    capacity_cpu = float(params.get("Capacity", 0))
    capacity_ram = float(params.get("CapacityRAM", 0))
    sense = params.get("Sense", "minimize")
    relax = _is_relaxed(params)
    variables = []
    for i in range(len(items)):
        vtype = "Continuous" if relax else "Integer"
        variables.append({"name": f"X_{i}", "type": vtype})
    # Objective
    objective = []
    for i in range(len(items)):
        objective.append({"var": f"X_{i}", "coef": values[i]})
    # Constraints
    constraints = []
    # CPU constraint
    terms_cpu = []
    for i in range(len(items)):
        terms_cpu.append({"var": f"X_{i}", "coef": cpu[i]})
    constraints.append({"type": "linear", "terms": terms_cpu, "sense": "<=", "rhs": capacity_cpu})
    # RAM constraint
    terms_ram = []
    for i in range(len(items)):
        terms_ram.append({"var": f"X_{i}", "coef": ram[i]})
    constraints.append({"type": "linear", "terms": terms_ram, "sense": "<=", "rhs": capacity_ram})
    # Demand/limit constraints
    for i in range(len(items)):
        rhs = float(demands.get(items[i], 1))
        constraints.append({"type": "linear", "terms": [{"var": f"X_{i}", "coef": 1}], "sense": "<=", "rhs": rhs})
    return (None, objective, constraints, variables)


def _build_scheduling_mip(params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    """Build basic scheduling MIP/LP with shift coverage constraints."""
    # Only return variable, constraint, objective data for engine assembly
    employees = list(params.get("Items", []))
    shifts = list(params.get("Shifts", []))
    demands = params.get("Demands", {}) or {}
    values = _safe_list(params.get("Values", []), len(employees), 1.0)
    sense = params.get("Sense", "maximize")
    relax = _is_relaxed(params)
    max_shifts = int(params.get("MaxShiftsPerEmployee", 1))
    if not shifts:
        shifts = list(demands.keys())
    variables = []
    for e in range(len(employees)):
        for s in range(len(shifts)):
            vtype = "Continuous" if relax else "Binary"
            variables.append({"name": f"Assign_{e}_{s}", "type": vtype})
    # Objective
    objective = []
    for e in range(len(employees)):
        for s in range(len(shifts)):
            objective.append({"var": f"Assign_{e}_{s}", "coef": values[e]})
    # Constraints
    constraints = []
    # Shift minimum constraints
    for s in range(len(shifts)):
        terms = []
        for e in range(len(employees)):
            terms.append({"var": f"Assign_{e}_{s}", "coef": 1})
        rhs = float(demands.get(shifts[s], 1))
        constraints.append({"type": "linear", "terms": terms, "sense": ">=", "rhs": rhs})
    # Employee max shift constraints
    for e in range(len(employees)):
        terms = []
        for s in range(len(shifts)):
            terms.append({"var": f"Assign_{e}_{s}", "coef": 1})
        constraints.append({"type": "linear", "terms": terms, "sense": "<=", "rhs": max_shifts})
    return (None, objective, constraints, variables)
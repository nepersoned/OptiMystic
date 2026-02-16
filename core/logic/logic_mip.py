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
    """
    if pyo is None:
        raise RuntimeError("Pyomo is required for logic_mip. Install: pip install pyomo")

    items = params.get("Items", [])
    item_lens = params.get("ItemLens", [])
    demands = params.get("Demands", {})
    prices = params.get("Prices", {})
    stocks = params.get("Stocks", [{"Name": "Default", "Length": 1000, "Cost": 1, "Limit": 50}])
    sense = params.get("Sense", "minimize")
    kerf = float(params.get("Kerf", 0.0))

    model = pyo.ConcreteModel()
    model._optimystic_sense = sense

    # Index sets
    n_stocks = len(stocks)
    n_items = len(items)
    max_bins = min(30, max(int(float(s.get("Limit", 30))) for s in stocks)) if stocks else 30
    model.S = pyo.Set(initialize=range(n_stocks))
    model.B = pyo.Set(initialize=range(max_bins))
    model.I = pyo.Set(initialize=range(n_items))

    # Decision variables: Use_s_b = use bin b of stock s; Cut_i_s_b = pieces of item i in that bin
    model.Use = pyo.Var(model.S, model.B, domain=pyo.Binary)
    model.Cut = pyo.Var(
        [(i, s, b) for i in model.I for s in model.S for b in model.B],
        domain=pyo.NonNegativeIntegers,
    )

    # Objective: minimize cost of bins used, or maximize revenue from cuts
    if sense == "minimize":
        model.OBJ = pyo.Objective(
            expr=sum(
                float(stocks[s]["Cost"]) * model.Use[s, b]
                for s in model.S
                for b in model.B
            ),
            sense=pyo.minimize,
        )
    else:
        model.OBJ = pyo.Objective(
            expr=sum(
                float(prices.get(items[i], 0)) * model.Cut[i, s, b]
                for i in model.I
                for s in model.S
                for b in model.B
            ),
            sense=pyo.maximize,
        )

    # Capacity: sum_i (len_i + kerf) * Cut[i,s,b] - (stock_len + kerf) * Use[s,b] <= 0
    def capacity_rule(m, s, b):
        stock_len = float(stocks[s]["Length"])
        lhs = sum(
            (float(item_lens[i]) + kerf) * m.Cut[i, s, b]
            for i in m.I
        ) - (stock_len + kerf) * m.Use[s, b]
        return lhs <= 0

    model.Capacity = pyo.Constraint(model.S, model.B, rule=capacity_rule)

    # Demand: sum_s,b Cut[i,s,b] >= demands[items[i]]
    def demand_rule(m, i):
        target = float(demands.get(items[i], 0))
        return sum(m.Cut[i, s, b] for s in m.S for b in m.B) >= target

    model.Demand = pyo.Constraint(model.I, rule=demand_rule)

    # Store names for result extraction (solver_engine will build var list from model)
    model._items = items
    model._stocks = stocks
    model._item_lens = item_lens
    model._clean_name = _clean_name

    return (model, [], [])


def _build_packing_mip(params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    """Build 1D knapsack MIP/LP for packing."""
    if pyo is None:
        raise RuntimeError("Pyomo is required for logic_mip. Install: pip install pyomo")

    items = list(params.get("Items", []))
    weights = _safe_list(params.get("Weights", []), len(items), 0.0)
    values = _safe_list(params.get("Values", []), len(items), 0.0)
    demands = params.get("Demands", {}) or {}
    capacity = float(params.get("Capacity", 0))
    sense = params.get("Sense", "maximize")
    relax = _is_relaxed(params)

    model = pyo.ConcreteModel()
    model._optimystic_sense = sense
    model._optimystic_relax = relax

    model.I = pyo.Set(initialize=range(len(items)))
    domain = pyo.NonNegativeReals if relax else pyo.NonNegativeIntegers

    def demand_bound(m, i):
        name = items[i]
        bound = float(demands.get(name, 1))
        return (0, bound) if bound >= 0 else (0, None)

    model.X = pyo.Var(model.I, domain=domain, bounds=demand_bound)

    model.Capacity = pyo.Constraint(
        expr=sum(weights[i] * model.X[i] for i in model.I) <= capacity
    )

    def limit_rule(m, i):
        name = items[i]
        return m.X[i] <= float(demands.get(name, 1))

    model.ItemLimit = pyo.Constraint(model.I, rule=limit_rule)

    obj_expr = sum(values[i] * model.X[i] for i in model.I)
    model.OBJ = pyo.Objective(
        expr=obj_expr,
        sense=pyo.minimize if sense == "minimize" else pyo.maximize,
    )

    model._items = items
    model._weights = weights
    model._values = values
    model._capacity = capacity
    return (model, [], [])


def _build_resource_mip(params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    """Build 2D knapsack MIP/LP for resource allocation (CPU/RAM)."""
    if pyo is None:
        raise RuntimeError("Pyomo is required for logic_mip. Install: pip install pyomo")

    items = list(params.get("Items", []))
    cpu = _safe_list(params.get("Weights", []), len(items), 0.0)
    ram = _safe_list(params.get("WeightsRAM", []), len(items), 0.0)
    values = _safe_list(params.get("Values", []), len(items), 0.0)
    demands = params.get("Demands", {}) or {}
    capacity_cpu = float(params.get("Capacity", 0))
    capacity_ram = float(params.get("CapacityRAM", 0))
    sense = params.get("Sense", "minimize")
    relax = _is_relaxed(params)

    model = pyo.ConcreteModel()
    model._optimystic_sense = sense
    model._optimystic_relax = relax

    model.I = pyo.Set(initialize=range(len(items)))
    domain = pyo.NonNegativeReals if relax else pyo.NonNegativeIntegers

    def demand_bound(m, i):
        name = items[i]
        bound = float(demands.get(name, 1))
        return (0, bound) if bound >= 0 else (0, None)

    model.X = pyo.Var(model.I, domain=domain, bounds=demand_bound)

    model.CapacityCPU = pyo.Constraint(
        expr=sum(cpu[i] * model.X[i] for i in model.I) <= capacity_cpu
    )
    model.CapacityRAM = pyo.Constraint(
        expr=sum(ram[i] * model.X[i] for i in model.I) <= capacity_ram
    )

    def limit_rule(m, i):
        name = items[i]
        return m.X[i] <= float(demands.get(name, 1))

    model.ItemLimit = pyo.Constraint(model.I, rule=limit_rule)

    obj_expr = sum(values[i] * model.X[i] for i in model.I)
    model.OBJ = pyo.Objective(
        expr=obj_expr,
        sense=pyo.minimize if sense == "minimize" else pyo.maximize,
    )

    model._items = items
    model._cpu = cpu
    model._ram = ram
    model._values = values
    model._capacity_cpu = capacity_cpu
    model._capacity_ram = capacity_ram
    return (model, [], [])


def _build_scheduling_mip(params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    """Build basic scheduling MIP/LP with shift coverage constraints."""
    if pyo is None:
        raise RuntimeError("Pyomo is required for logic_mip. Install: pip install pyomo")

    employees = list(params.get("Items", []))
    shifts = list(params.get("Shifts", []))
    demands = params.get("Demands", {}) or {}
    values = _safe_list(params.get("Values", []), len(employees), 1.0)
    sense = params.get("Sense", "maximize")
    relax = _is_relaxed(params)
    max_shifts = int(params.get("MaxShiftsPerEmployee", 1))

    if not shifts:
        shifts = list(demands.keys())

    model = pyo.ConcreteModel()
    model._optimystic_sense = sense
    model._optimystic_relax = relax

    model.E = pyo.Set(initialize=range(len(employees)))
    model.S = pyo.Set(initialize=range(len(shifts)))

    domain = pyo.NonNegativeReals if relax else pyo.Binary
    model.Assign = pyo.Var(model.E, model.S, domain=domain, bounds=(0, 1))

    def shift_min_rule(m, s):
        shift_name = shifts[s]
        return sum(m.Assign[e, s] for e in m.E) >= float(demands.get(shift_name, 1))

    model.ShiftMin = pyo.Constraint(model.S, rule=shift_min_rule)

    def emp_max_rule(m, e):
        return sum(m.Assign[e, s] for s in m.S) <= max_shifts

    model.EmpMax = pyo.Constraint(model.E, rule=emp_max_rule)

    obj_expr = sum(
        values[e] * model.Assign[e, s]
        for e in model.E
        for s in model.S
    )
    model.OBJ = pyo.Objective(
        expr=obj_expr,
        sense=pyo.minimize if sense == "minimize" else pyo.maximize,
    )

    model._employees = employees
    model._shifts = shifts
    model._values = values
    model._max_shifts = max_shifts
    return (model, [], [])
"""Constraint programming builder with OR-Tools support for scheduling."""
import time
from typing import Any, Dict, List, Tuple

try:
    from ortools.sat.python import cp_model
except ImportError:
    cp_model = None


def _parameter_map(parameters: Any) -> Dict[str, Any]:
    if isinstance(parameters, dict):
        return parameters
    if isinstance(parameters, list):
        mapped = {}
        for item in parameters:
            if isinstance(item, dict) and "name" in item:
                mapped[item["name"]] = item.get("data")
        return mapped
    return {}


def _solver_options(parameters: Dict[str, Any]) -> Dict[str, Any]:
    time_limit = parameters.get("time_limit", parameters.get("TimeLimit", 10))
    try:
        seconds = max(1, int(float(time_limit)))
    except (TypeError, ValueError):
        seconds = 10
    seed_raw = parameters.get("seed", parameters.get("Seed", 0))
    workers_raw = parameters.get("workers", parameters.get("Workers", 0))
    try:
        seed = max(0, int(seed_raw))
    except (TypeError, ValueError):
        seed = 0
    try:
        workers = max(0, int(workers_raw))
    except (TypeError, ValueError):
        workers = 0
    return {"seconds": seconds, "seed": seed, "workers": workers}


def build_model(domain: str, params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    if not isinstance(params, dict):
        raise ValueError(f"Params missing for domain '{domain}'")

    if domain == "scheduling":
        spec = params.get("CP")
        if not isinstance(spec, dict):
            raise ValueError("CP spec missing for scheduling")
        variables = spec.get("variables", [])
        if not isinstance(variables, list):
            raise ValueError("Invalid CP variable structure")
        return ({"engine": "ortools_cp_sat", "domain": domain, "spec": spec}, [], variables)

    ir = params.get("IR")
    if not isinstance(ir, dict):
        raise ValueError(f"IR missing for domain '{domain}'")

    objective = ir.get("objective", [])
    constraints = ir.get("constraints", [])
    variables = ir.get("variables", [])

    if not isinstance(objective, list) or not isinstance(constraints, list) or not isinstance(variables, list):
        raise ValueError("Invalid IR structure")

    return (objective, constraints, variables)


def solve_cp(params):
    objective, constraints, variables = build_model(str(params.get("Mode", "")), params)
    return {
        "status": "Ready",
        "engine": "CP",
        "objective": objective,
        "constraints": constraints,
        "variables": variables,
    }


def solve_cp_model(store_data: Dict[str, Any], objective: Any) -> Dict[str, Any]:
    start = time.time()
    if cp_model is None:
        return {
            "status": "Error",
            "error_msg": "OR-Tools required. pip install ortools",
            "solve_time": time.time() - start,
        }

    if not (isinstance(objective, dict) and objective.get("engine") == "ortools_cp_sat"):
        return {
            "status": "Error",
            "error_msg": "Python CP engine expects CP wrapper objective",
            "solve_time": time.time() - start,
        }

    parameters = _parameter_map(store_data.get("parameters", {}))
    spec = objective.get("spec") if isinstance(objective, dict) else None
    if not isinstance(spec, dict):
        return {"status": "Error", "error_msg": "Invalid CP wrapper spec", "solve_time": time.time() - start}

    employees = list(spec.get("employees", []))
    shifts = list(spec.get("shifts", []))
    demands = spec.get("demands", {}) or {}
    values = spec.get("values", {}) or {}
    rules = spec.get("rules", []) or []
    max_shifts = int(spec.get("max_shifts_per_employee", 1))
    min_shifts = int(spec.get("min_shifts_per_employee", 0))
    sense = str((spec.get("meta") or {}).get("sense", "maximize")).lower()

    if not employees:
        return {"status": "Error", "error_msg": "No employees in CP spec", "solve_time": time.time() - start}
    if not shifts:
        return {"status": "Error", "error_msg": "No shifts in CP spec", "solve_time": time.time() - start}
    if max_shifts < min_shifts:
        return {"status": "Error", "error_msg": "max_shifts_per_employee < min_shifts_per_employee", "solve_time": time.time() - start}

    model = cp_model.CpModel()
    assign = {}
    for e_idx, _ in enumerate(employees):
        for s_idx, _ in enumerate(shifts):
            assign[(e_idx, s_idx)] = model.NewBoolVar(f"Assign_{e_idx}_{s_idx}")

    for s_idx, shift in enumerate(shifts):
        model.Add(
            sum(assign[(e_idx, s_idx)] for e_idx in range(len(employees)))
            >= int(round(float(demands.get(shift, 1))))
        )

    for e_idx, _ in enumerate(employees):
        model.Add(sum(assign[(e_idx, s_idx)] for s_idx in range(len(shifts))) <= max_shifts)
        if min_shifts > 0:
            model.Add(sum(assign[(e_idx, s_idx)] for s_idx in range(len(shifts))) >= min_shifts)

    for rule in rules:
        if not isinstance(rule, dict):
            continue
        employee = rule.get("Employee", rule.get("employee"))
        shift = rule.get("Shift", rule.get("shift"))
        if employee not in employees or shift not in shifts:
            continue
        var = assign[(employees.index(employee), shifts.index(shift))]
        kind = str(rule.get("Type", rule.get("type", ""))).lower()
        value = int(round(float(rule.get("Value", rule.get("value", 1)))))
        if kind in ("forbid", "blocked", "ban", "unavailable"):
            model.Add(var == 0)
        elif kind in ("require", "forced", "must"):
            model.Add(var == value)

    objective_expr = sum(
        int(round(float(values.get(employee, 1.0)) * 1000)) * assign[(e_idx, s_idx)]
        for e_idx, employee in enumerate(employees)
        for s_idx in range(len(shifts))
    )
    if sense == "minimize":
        model.Minimize(-objective_expr)
    else:
        model.Maximize(objective_expr)

    solver = cp_model.CpSolver()
    options = _solver_options(parameters)
    solver.parameters.max_time_in_seconds = float(options.get("seconds", 10))
    if int(options.get("seed", 0)) > 0:
        solver.parameters.random_seed = int(options.get("seed", 0))
    if int(options.get("workers", 0)) > 0:
        solver.parameters.num_search_workers = int(options.get("workers", 0))
    status = solver.Solve(model)
    status_map = {
        cp_model.OPTIMAL: "Optimal",
        cp_model.FEASIBLE: "Feasible",
        cp_model.INFEASIBLE: "Infeasible",
        cp_model.MODEL_INVALID: "ModelInvalid",
        cp_model.UNKNOWN: "Unknown",
    }

    feasible_statuses = (cp_model.OPTIMAL, cp_model.FEASIBLE)
    variables = []
    for e_idx, _ in enumerate(employees):
        for s_idx, _ in enumerate(shifts):
            name = f"Assign_{e_idx}_{s_idx}"
            variables.append(
                {
                    "Variable": name,
                    "Value": float(solver.Value(assign[(e_idx, s_idx)])) if status in feasible_statuses else 0.0,
                }
            )

    constraints_data = []
    for s_idx, _ in enumerate(shifts):
        constraints_data.append({"Constraint": f"coverage_{s_idx}", "Shadow Price": 0.0, "Slack": 0.0})
    for e_idx, _ in enumerate(employees):
        constraints_data.append({"Constraint": f"employee_load_{e_idx}", "Shadow Price": 0.0, "Slack": 0.0})

    objective_val = None
    if status in feasible_statuses:
        objective_val = solver.ObjectiveValue() / 1000.0
        if sense == "minimize":
            objective_val = -objective_val

    return {
        "status": status_map.get(status, "Unknown"),
        "objective": objective_val,
        "variables": variables,
        "constraints": constraints_data,
        "solve_time": time.time() - start,
        "lp_sensitivity": False,
    }

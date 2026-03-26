"""CP-only solver engine for Python runtime (OR-Tools CP-SAT)."""
import time
from typing import Any, Dict

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
    return {"seconds": seconds}


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
    sense = str((spec.get("meta") or {}).get("sense", "maximize")).lower()

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
    solver.parameters.max_time_in_seconds = float(_solver_options(parameters).get("seconds", 10))
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

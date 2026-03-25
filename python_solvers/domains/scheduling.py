"""
Domain: Scheduling (HR / Resource Planning)
Maps raw employee/shift input → common schema.
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
    Map raw employee/shift payload to common schema.
    Input can be:
      - Employees/Workers (list of dicts) with Name, Duration, Hours
      - Or Items (list of names) + Durations/Hours
    """
    items = raw_params.get("Employees", raw_params.get("Workers", raw_params.get("Items", [])))
    shifts_raw = raw_params.get("Shifts", raw_params.get("Slots", []))

    if isinstance(items, list) and items and isinstance(items[0], dict):
        names = [x.get("Name", x.get("id", f"E_{i}")) for i, x in enumerate(items)]
        durations = [float(x.get("Duration", x.get("Hours", 8))) for x in items]
    else:
        names = list(raw_params.get("Items", []))
        durations = raw_params.get("Durations", raw_params.get("Hours", [8] * len(names)))

    n = len(names)
    demands = raw_params.get("Demands", raw_params.get("MinStaff", {}))
    sense = raw_params.get("Sense", "maximize")

    shifts: List[str] = []
    derived_demands: Dict[str, float] = {}
    if isinstance(shifts_raw, list) and shifts_raw and isinstance(shifts_raw[0], dict):
        for i, shift in enumerate(shifts_raw):
            shift_name = str(shift.get("Name", shift.get("id", f"S_{i}")))
            shifts.append(shift_name)
            if "Demand" in shift:
                try:
                    derived_demands[shift_name] = float(shift.get("Demand", 1))
                except (TypeError, ValueError):
                    derived_demands[shift_name] = 1.0
    elif isinstance(shifts_raw, list):
        shifts = [str(s) for s in shifts_raw]

    if not isinstance(demands, dict):
        demands = {}
    if derived_demands:
        merged = dict(derived_demands)
        merged.update({str(k): float(v) for k, v in demands.items()})
        demands = merged

    if not shifts:
        shifts = list(demands.keys()) if demands else []

    values_raw = raw_params.get("Values", raw_params.get("Satisfaction", [1] * n))
    values: List[float]
    if isinstance(values_raw, dict):
        values = []
        for employee in names:
            employee_value = values_raw.get(employee, 1)
            if isinstance(employee_value, dict):
                numeric_values = []
                for v in employee_value.values():
                    try:
                        numeric_values.append(float(v))
                    except (TypeError, ValueError):
                        continue
                values.append(sum(numeric_values) / len(numeric_values) if numeric_values else 1.0)
            else:
                try:
                    values.append(float(employee_value))
                except (TypeError, ValueError):
                    values.append(1.0)
    else:
        values = _safe_list(values_raw, n, 1.0)

    mapped = {
        "Items": names,
        "Weights": _safe_list(durations, n),
        "Values": values,
        "Demands": demands,
        "Sense": sense,
        "Shifts": shifts,
        "MaxShiftsPerEmployee": int(raw_params.get("MaxShiftsPerEmployee") or 1),
        "Rules": raw_params.get("Rules", raw_params.get("Constraints", [])),
        "Mode": "scheduling",
    }
    mapped["IR"] = build_ir(mapped)
    mapped["CP"] = build_cp_spec(mapped)
    return mapped


def build_ir(params: Dict[str, Any]) -> Dict[str, Any]:
    employees = list(params.get("Items", []))
    shifts = list(params.get("Shifts", []))
    demands = params.get("Demands", {}) or {}
    values = _safe_list(params.get("Values", []), len(employees), 1.0)
    relax = bool(params.get("Relax") or params.get("LP") or params.get("lp_relaxation"))
    max_shifts = int(params.get("MaxShiftsPerEmployee", 1))
    if not shifts:
        shifts = list(demands.keys())

    variables = []
    objective = []
    constraints = []

    for e_idx, _ in enumerate(employees):
        for s_idx, _ in enumerate(shifts):
            name = f"Assign_{e_idx}_{s_idx}"
            variables.append({"name": name, "type": "Continuous" if relax else "Binary", "lb": 0, "ub": 1})
            objective.append({"var": name, "coef": float(values[e_idx])})

    for s_idx, shift in enumerate(shifts):
        constraints.append({
            "name": f"shift_{s_idx}",
            "type": "linear",
            "terms": [{"var": f"Assign_{e_idx}_{s_idx}", "coef": 1} for e_idx in range(len(employees))],
            "sense": ">=",
            "rhs": float(demands.get(shift, 1)),
        })

    for e_idx, _ in enumerate(employees):
        constraints.append({
            "name": f"employee_{e_idx}",
            "type": "linear",
            "terms": [{"var": f"Assign_{e_idx}_{s_idx}", "coef": 1} for s_idx in range(len(shifts))],
            "sense": "<=",
            "rhs": max_shifts,
        })

    sense = str(params.get("Sense", "maximize")).lower()
    return finalize_ir(
        {
            "meta": {"domain": "scheduling", "sense": sense},
            "variables": variables,
            "objective": objective,
            "constraints": constraints,
        },
        domain="scheduling",
        sense=sense,
    )


def build_cp_spec(params: Dict[str, Any]) -> Dict[str, Any]:
    employees = list(params.get("Items", []))
    shifts = list(params.get("Shifts", []))
    demands = params.get("Demands", {}) or {}
    values = _safe_list(params.get("Values", []), len(employees), 1.0)
    max_shifts = int(params.get("MaxShiftsPerEmployee", 1))
    rules = params.get("Rules", []) or []
    if not shifts:
        shifts = list(demands.keys())

    variables = []
    objective = []
    constraints = []

    for e_idx, _ in enumerate(employees):
        for s_idx, _ in enumerate(shifts):
            name = f"Assign_{e_idx}_{s_idx}"
            variables.append({"name": name, "type": "Binary", "lb": 0, "ub": 1})
            objective.append({"var": name, "coef": float(values[e_idx])})

    for s_idx, shift in enumerate(shifts):
        constraints.append({
            "name": f"coverage_{s_idx}",
            "type": "linear",
            "terms": [{"var": f"Assign_{e_idx}_{s_idx}", "coef": 1} for e_idx in range(len(employees))],
            "sense": ">=",
            "rhs": float(demands.get(shift, 1)),
        })

    for e_idx, _ in enumerate(employees):
        constraints.append({
            "name": f"employee_load_{e_idx}",
            "type": "linear",
            "terms": [{"var": f"Assign_{e_idx}_{s_idx}", "coef": 1} for s_idx in range(len(shifts))],
            "sense": "<=",
            "rhs": float(max_shifts),
        })

    for r_idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        employee = rule.get("Employee", rule.get("employee"))
        shift = rule.get("Shift", rule.get("shift"))
        kind = str(rule.get("Type", rule.get("type", ""))).lower()
        value = float(rule.get("Value", rule.get("value", 1)))
        if employee not in employees or shift not in shifts:
            continue
        var_name = f"Assign_{employees.index(employee)}_{shifts.index(shift)}"
        if kind in ("forbid", "blocked", "ban", "unavailable"):
            constraints.append({"name": f"rule_forbid_{r_idx}", "type": "fix", "var": var_name, "value": 0})
        elif kind in ("require", "forced", "must"):
            constraints.append({"name": f"rule_require_{r_idx}", "type": "fix", "var": var_name, "value": value})

    sense = str(params.get("Sense", "maximize")).lower()
    cp_ir = finalize_ir(
        {
            "meta": {
                "domain": "scheduling",
                "solver": "cp",
                "sense": sense,
            },
            "variables": variables,
            "objective": objective,
            "constraints": constraints,
        },
        domain="scheduling",
        sense=sense,
    )

    return {
        "meta": {
            "domain": "scheduling",
            "solver": "cp",
            "sense": sense,
            "ir_stats": cp_ir.get("meta", {}).get("stats", {}),
        },
        "employees": employees,
        "shifts": shifts,
        "demands": {str(k): float(v) for k, v in demands.items()},
        "values": {employees[i]: float(values[i]) for i in range(len(employees))},
        "max_shifts_per_employee": max_shifts,
        "rules": [rule for rule in rules if isinstance(rule, dict)],
        "variables": cp_ir.get("variables", []),
        "objective": cp_ir.get("objective", []),
        "constraints": cp_ir.get("constraints", []),
    }

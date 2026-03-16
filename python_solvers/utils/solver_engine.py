"""
Solver engine: Auto-Selector + Pyomo. Builds/solves from (objective, constraints, variables)
or solves a pre-built Pyomo model.
All comments are in English only.
"""
import time
from typing import Any, Dict, List

try:
    import pyomo.environ as pyo
except ImportError:
    pyo = None

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


def _normalize_symbol(name: str) -> str:
    return str(name or "").replace("-", "_")


def _solver_options(parameters: Dict[str, Any]) -> Dict[str, Any]:
    time_limit = parameters.get("time_limit", parameters.get("TimeLimit", 10))
    try:
        seconds = max(1, int(float(time_limit)))
    except (TypeError, ValueError):
        seconds = 10
    return {"seconds": seconds}


def _build_solver(parameters: Dict[str, Any], solver_name: str | None = None) -> Any:
    if pyo is None:
        return None
    selected = solver_name or parameters.get("solver_name", "cbc")
    return pyo.SolverFactory(selected)


def _variable_domain(vtype: str) -> Any:
    if vtype == "Binary":
        return pyo.Binary
    if vtype == "Integer":
        return pyo.NonNegativeIntegers
    return pyo.NonNegativeReals


def _is_pyomo_model(obj: Any) -> bool:
    return pyo is not None and hasattr(pyo, "ConcreteModel") and type(obj).__name__ == "ConcreteModel"


def _is_cp_sat_wrapper(obj: Any) -> bool:
    return isinstance(obj, dict) and obj.get("engine") == "ortools_cp_sat"


def _model_has_integer_vars(model: Any) -> bool:
    if pyo is None:
        return False
    for v in model.component_data_objects(pyo.Var, active=True):
        try:
            if v.is_binary() or v.is_integer():
                return True
        except Exception:
            continue
    return False


def _select_algorithm(store_data: Dict[str, Any], sense: str, objective: Any, constraints: List[Any]) -> str:
    """
    Auto-Selector: data size/shape + model type → suggested algorithm.
    Returns one of 'MIP', 'CG', 'GA', 'CP'.
    """
    # Algorithm selection is based on external parameters, default is MIP
    params = _parameter_map(store_data.get("parameters", {}))
    algo = params.get("algorithm") or params.get("Algorithm")
    if algo:
        return algo.upper()
    if _is_cp_sat_wrapper(objective):
        return "CP"
    if _is_pyomo_model(objective):
        return "MIP"
    vars_list = store_data.get("variables", [])
    n_vars = len(vars_list)
    n_constraints = len(constraints) if isinstance(constraints, list) else 0
    if isinstance(params, dict):
        mode = params.get("Mode") or (params.get("data") if isinstance(params.get("data"), str) else None)
        if mode and mode.lower() == "ga":
            return "GA"
        if mode and mode.lower() in ("cp", "constraint_programming"):
            return "CP"
    if n_vars > 1000 and n_constraints > 500:
        return "MIP"
    return "MIP"


def _flatten_var_name(base_name: str, idx: Any) -> str:
    if idx is None:
        return base_name
    if isinstance(idx, tuple):
        return f"{base_name}_" + "_".join(str(i) for i in idx)
    return f"{base_name}_{idx}"


def _solve_cp_sat_model(wrapper: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
    start = time.time()
    if cp_model is None:
        return {"status": "Error", "error_msg": "OR-Tools required. pip install ortools", "solve_time": time.time() - start}

    spec = wrapper.get("spec") if isinstance(wrapper, dict) else None
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
    for e_idx, employee in enumerate(employees):
        for s_idx, shift in enumerate(shifts):
            assign[(e_idx, s_idx)] = model.NewBoolVar(f"Assign_{e_idx}_{s_idx}")

    for s_idx, shift in enumerate(shifts):
        model.Add(sum(assign[(e_idx, s_idx)] for e_idx in range(len(employees))) >= int(round(float(demands.get(shift, 1)))))

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

    objective_expr = sum(int(round(float(values.get(employee, 1.0)) * 1000)) * assign[(e_idx, s_idx)] for e_idx, employee in enumerate(employees) for s_idx in range(len(shifts)))
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

    variables = []
    feasible_statuses = (cp_model.OPTIMAL, cp_model.FEASIBLE)
    for e_idx, _ in enumerate(employees):
        for s_idx, _ in enumerate(shifts):
            name = f"Assign_{e_idx}_{s_idx}"
            variables.append({"Variable": name, "Value": float(solver.Value(assign[(e_idx, s_idx)])) if status in feasible_statuses else 0.0})

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


def _solve_pyomo_model(model: Any, solver_name: str = "cbc") -> Dict[str, Any]:
    """Solve a Pyomo ConcreteModel and return a standard result dictionary."""
    start = time.time()
    try:
        is_mip = _model_has_integer_vars(model)
        if not is_mip and not hasattr(model, "dual"):
            model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

        opt = _build_solver({}, solver_name)
        if opt is None:
            return {"status": "Error", "error_msg": "Pyomo required. pip install pyomo", "solve_time": time.time() - start}
        res = opt.solve(model, tee=False, options={"seconds": 10})

        status = "Optimal"
        if res.solver.termination_condition != pyo.TerminationCondition.optimal:
            status = str(res.solver.termination_condition) if res.solver else "Unknown"

        objective_val = None
        if hasattr(model, "OBJ") and model.OBJ is not None:
            objective_val = float(pyo.value(model.OBJ))

        variables = []
        for v in model.component_objects(pyo.Var, active=True):
            for idx in v:
                try:
                    name = _flatten_var_name(v.name, idx)
                    variables.append({"Variable": name, "Value": pyo.value(v[idx])})
                except Exception:
                    pass

        constraints_data = []
        for c in model.component_objects(pyo.Constraint, active=True):
            for idx in c:
                try:
                    constraints_data.append({
                        "Constraint": f"{c.name}_{idx}",
                        "Shadow Price": float(model.dual[c[idx]]) if hasattr(model, "dual") and c[idx] in model.dual else 0.0,
                        "Slack": 0.0,
                    })
                except Exception:
                    pass

        return {
            "status": status,
            "objective": objective_val,
            "variables": variables,
            "constraints": constraints_data,
            "solve_time": time.time() - start,
            "lp_sensitivity": not is_mip,
        }
    except Exception as e:
        return {"status": "Error", "error_msg": str(e), "solve_time": time.time() - start}


def _build_and_solve_from_lists(
    store_data: Dict[str, Any],
    sense: str,
    objective: List[Dict[str, Any]],
    constraints: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build Pyomo model from (objective_terms, constraints, variables) and solve."""
    if pyo is None:
        return {"status": "Error", "error_msg": "Pyomo required. pip install pyomo"}

    start = time.time()
    model = pyo.ConcreteModel()
    vars_list = store_data.get("variables", [])
    parameters = _parameter_map(store_data.get("parameters", {}))
    is_mip = any(v.get("type") in ("Binary", "Integer") for v in vars_list)
    model._v = {}
    for v in vars_list:
        name = v.get("name", "")
        if not name:
            continue
        vtype = v.get("type", "Continuous")
        domain = _variable_domain(vtype)
        lb = v.get("lb", 0)
        ub = v.get("ub", None)
        normalized_name = _normalize_symbol(name)
        setattr(model, normalized_name, pyo.Var(domain=domain, bounds=(lb, ub)))
        model._v[name] = getattr(model, normalized_name)
    if not is_mip:
        model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)
    # Build objective
    if isinstance(objective, list) and objective:
        obj_expr = sum(
            term.get("coef", 0) * getattr(model, term["var"].replace("-", "_"))
            for term in objective
            if term.get("var") in model._v
        )
        model.OBJ = pyo.Objective(expr=obj_expr, sense=pyo.minimize if sense == "minimize" else pyo.maximize)
    else:
        model.OBJ = pyo.Objective(expr=0, sense=pyo.minimize)
    # Build constraints
    for idx, c in enumerate(constraints or []):
        ctype = c.get("type", "linear")
        if ctype == "fix":
            vname = c["var"]
            if vname in model._v:
                model.add_component(f"C_fix_{idx}", pyo.Constraint(expr=model._v[vname] == c["value"]))
        elif ctype == "linear":
            terms = c.get("terms", [])
            lhs = sum(
                t.get("coef", 0) * model._v[t["var"]]
                for t in terms
                if t.get("var") in model._v
            )
            csense = c.get("sense", "<=")
            rhs = c.get("rhs", 0)
            if csense == "<=":
                model.add_component(f"C_{idx}", pyo.Constraint(expr=lhs <= rhs))
            elif csense == ">=":
                model.add_component(f"C_{idx}", pyo.Constraint(expr=lhs >= rhs))
            else:
                model.add_component(f"C_{idx}", pyo.Constraint(expr=lhs == rhs))
    # Support for solver_name parameter
    solver_name = parameters.get("solver_name", "cbc")
    opt = _build_solver(parameters, solver_name)
    if opt is None:
        return {"status": "Error", "error_msg": "Pyomo required. pip install pyomo", "solve_time": time.time() - start}
    res = opt.solve(model, tee=False, options=_solver_options(parameters))
    status = "Optimal"
    if res.solver.termination_condition != pyo.TerminationCondition.optimal:
        status = str(res.solver.termination_condition) if res.solver else "Unknown"
    objective_val = float(pyo.value(model.OBJ)) if model.OBJ else None
    variables = [{"Variable": name, "Value": pyo.value(v)} for name, v in model._v.items()]
    constraints_data = []
    for i in range(len(constraints or [])):
        cname = f"C_{i}" if f"C_{i}" in [str(x) for x in model.component_objects(pyo.Constraint)] else f"C_fix_{i}"
        try:
            c = getattr(model, cname, None)
            if c is not None and hasattr(model, "dual") and c in model.dual:
                constraints_data.append({"Constraint": cname, "Shadow Price": float(model.dual[c]), "Slack": 0.0})
            else:
                constraints_data.append({"Constraint": cname, "Shadow Price": 0.0, "Slack": 0.0})
        except Exception:
            constraints_data.append({"Constraint": cname, "Shadow Price": 0.0, "Slack": 0.0})
    return {
        "status": status,
        "objective": objective_val,
        "variables": variables,
        "constraints": constraints_data,
        "solve_time": time.time() - start,
        "lp_sensitivity": not is_mip,
    }


def solve_model(
    store_data: Dict[str, Any],
    sense: str,
    objective: Any,
    constraints: Any,
    solver_name: str = None,
) -> Dict[str, Any]:
    """
    Solve: if objective is a Pyomo model, solve it; else build from (objective, constraints, variables) with Pyomo.
    """
    _select_algorithm(store_data, sense, objective, constraints)
    parameters = _parameter_map(store_data.get("parameters", {}))
    if not solver_name:
        solver_name = parameters.get("solver_name", "cbc")
    if _is_cp_sat_wrapper(objective):
        return _solve_cp_sat_model(objective, parameters)
    if _is_pyomo_model(objective):
        return _solve_pyomo_model(objective, solver_name=solver_name)
    return _build_and_solve_from_lists(
        store_data,
        sense,
        objective if isinstance(objective, list) else [],
        constraints if isinstance(constraints, list) else [],
    )

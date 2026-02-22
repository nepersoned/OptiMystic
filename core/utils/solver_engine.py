"""
Solver engine: Auto-Selector + Pyomo. Builds/solves from (objective, constraints, variables)
or solves a pre-built Pyomo model.
"""
import time
from typing import Any, Dict, List

try:
    import pyomo.environ as pyo
except ImportError:
    pyo = None


def _is_pyomo_model(obj: Any) -> bool:
    return pyo is not None and hasattr(pyo, "ConcreteModel") and type(obj).__name__ == "ConcreteModel"


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
    Returns one of 'MIP', 'CG', 'NLP', 'CP'.
    
    Bridge already pre-selects solver, so this is mainly for logging/routing.
    Can override if problem structure suggests better algorithm.
    """
    # If already a Pyomo model, bridge already built it → stick with MIP solve
    if _is_pyomo_model(objective):
        return "MIP"

    # Check store_data for hints
    vars_list = store_data.get("variables", [])
    params = store_data.get("parameters", {})
    n_vars = len(vars_list)
    n_constraints = len(constraints) if isinstance(constraints, list) else 0

    # Domain-specific hints
    if isinstance(params, dict):
        mode = params.get("Mode") or (params.get("data") if isinstance(params.get("data"), str) else None)
        if mode == "nlp":
            return "NLP"
        if mode in ("cp", "constraint_programming"):
            return "CP"
    
    # Size-based heuristics
    if n_vars > 1000 and n_constraints > 500:
        # Very large: consider CG for cutting, but MIP is safer
        return "MIP"

    return "MIP"


def _solve_pyomo_model(model: Any) -> Dict[str, Any]:
    """Solve a Pyomo ConcreteModel and return standard result dict."""
    start = time.time()
    try:
        is_mip = _model_has_integer_vars(model)
        if not is_mip and not hasattr(model, "dual"):
            model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

        opt = pyo.SolverFactory("cbc")
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
                    name = v.name
                    if isinstance(idx, tuple):
                        name += "_" + "_".join(str(i) for i in idx)
                    else:
                        name += f"_{idx}"
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
    is_mip = any(v.get("type") in ("Binary", "Integer") for v in vars_list)

    model._v = {}
    for v in vars_list:
        name = v.get("name", "")
        vtype = v.get("type", "Continuous")
        if vtype == "Binary":
            domain = pyo.Binary
        elif vtype == "Integer":
            domain = pyo.NonNegativeIntegers
        else:
            domain = pyo.NonNegativeReals
        setattr(model, name.replace("-", "_"), pyo.Var(domain=domain, bounds=(0, None)))
        model._v[name] = getattr(model, name.replace("-", "_"))

    if not is_mip:
        model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

    # Objective
    if isinstance(objective, list) and objective:
        obj_expr = sum(
            term.get("coef", 0) * getattr(model, term["var"].replace("-", "_"))
            for term in objective
            if term.get("var") in model._v
        )
        model.OBJ = pyo.Objective(expr=obj_expr, sense=pyo.minimize if sense == "minimize" else pyo.maximize)
    else:
        model.OBJ = pyo.Objective(expr=0, sense=pyo.minimize)

    # Constraints
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

    opt = pyo.SolverFactory("cbc")
    res = opt.solve(model, tee=False, options={"seconds": 10})

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
) -> Dict[str, Any]:
    """
    Solve: if objective is a Pyomo model, solve it; else build from (objective, constraints, variables) with Pyomo.
    Auto-Selector can be used for logging or routing to NLP/CP later.
    """
    algo = _select_algorithm(store_data, sense, objective, constraints)

    if _is_pyomo_model(objective):
        return _solve_pyomo_model(objective)

    return _build_and_solve_from_lists(
        store_data,
        sense,
        objective if isinstance(objective, list) else [],
        constraints if isinstance(constraints, list) else [],
    )
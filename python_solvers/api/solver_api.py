from typing import Any, Dict

from python_solvers.cli_solver import _build_julia_payload, _run_julia_solver
from python_solvers.logic import logic_cp
from python_solvers.logic import logic_vrp
from python_solvers.utils import bridge_logic


def run_optimization(domain: str, solver: str, params: Dict[str, Any]) -> Dict[str, Any]:
    solver_type = (solver or "").strip().lower()
    mapped_params = bridge_logic.map_params_by_mode(domain, params)

    if str(domain or "").strip().lower() == "vrp":
        store_data = {
            "variables": [],
            "parameters": dict(mapped_params or {}),
        }
        result = logic_vrp.solve_vrp_model(store_data)
    elif solver_type == "cp":
        objective, constraints, variables = bridge_logic.generate_logic(domain, params, solver_type)
        store_data = {
            "variables": variables,
            "parameters": dict(mapped_params or {}),
        }
        result = logic_cp.solve_cp_model(store_data, objective)
    else:
        julia_payload = _build_julia_payload(mapped_params)
        result = _run_julia_solver(domain, solver_type or "mip", julia_payload)

    return {
        "status": result.get("status", "Error"),
        "objective": result.get("objective"),
        "variables": result.get("variables", []),
        "constraints": result.get("constraints", []),
        "solve_time": result.get("solve_time", 0),
        "lp_sensitivity": result.get("lp_sensitivity", False),
        "details": result.get("details"),
        "sensitivity": result.get("sensitivity"),
        "error_msg": result.get("error_msg"),
    }
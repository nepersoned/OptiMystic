from typing import Any, Dict

from python_solvers.cli_solver import _build_julia_payload, _run_julia_solver
from python_solvers.utils import bridge_logic


def run_optimization(domain: str, solver: str, params: Dict[str, Any], trace_id: str | None = None) -> Dict[str, Any]:
    solver_type = (solver or "").strip().lower()

    if bridge_logic.should_use_python_runtime(domain, solver_type):
        result = bridge_logic.run_python_runtime(domain, params, solver_type)
    else:
        mapped_params = bridge_logic.map_params_by_mode(domain, params)
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
        "trace_id": trace_id,
    }
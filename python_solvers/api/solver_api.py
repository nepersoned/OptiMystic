from typing import Any, Dict

from python_solvers.utils import bridge_logic
from python_solvers.utils import solver_engine as solver_core
from python_solvers.utils import services


def run_optimization(domain: str, solver: str, params: Dict[str, Any]) -> Dict[str, Any]:
    objective, constraints, variables = bridge_logic.generate_logic(domain, params, solver)
    mapped_params = bridge_logic.map_params_by_mode(domain, params)

    store_data = {
        "variables": variables,
        "parameters": services.build_parameter_store(mapped_params),
    }

    sense = str(mapped_params.get("Sense", "minimize")).lower()

    result = solver_core.solve_model(store_data, sense, objective, constraints)

    processed_data = services.process_results(result, store_data, domain)
    sensitivity_data = services.process_sensitivity(result, store_data, domain)

    return {
        "status": result.get("status", "Error"),
        "objective": result.get("objective"),
        "variables": result.get("variables", []),
        "constraints": result.get("constraints", []),
        "solve_time": result.get("solve_time", 0),
        "lp_sensitivity": result.get("lp_sensitivity", False),
        "details": processed_data,
        "sensitivity": sensitivity_data,
        "error_msg": result.get("error_msg"),
    }
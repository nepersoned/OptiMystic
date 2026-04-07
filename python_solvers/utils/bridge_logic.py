"""
Bridge logic: Domain selector + Solver selector.

Roles:
1. Map template_type -> domain module
2. Route domain output -> logic module based on solver_type
3. Maintain backward compatibility with mode aliases
"""
from typing import Any, Dict, List, Tuple, Union

# Mode aliases
MODES = {
    "cutting": "cutting",
    "packing": "packing",
    "vrp": "vrp",
    "routing": "vrp",
    "vehicle_routing": "vrp",
    "resourcing": "resourcing",
    "scheduling": "scheduling",
    "generic": "generic",
    "formula": "generic",
    "custom": "generic",
    # Backward compat aliases
    "manufacturing": "cutting",
    "logistics": "packing",
    "resource_allocation": "resourcing",
    "resource": "resourcing",
    "it": "resourcing",
    "hr": "scheduling",
    "nsp": "scheduling",
}

SOLVER_TYPES = ["cp"]


def map_params_by_mode(mode: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map raw payload to common solver format by domain mode.
    Routes to domain module's map_params().
    """
    mode = (mode or "").strip().lower()
    normalized_mode = MODES.get(mode, mode)

    if normalized_mode == "cutting":
        from python_solvers.domains import cutting
        mapped = cutting.map_params(params)
    elif normalized_mode == "packing":
        from python_solvers.domains import packing
        mapped = packing.map_params(params)
    elif normalized_mode == "vrp":
        from python_solvers.domains import vrp
        mapped = vrp.map_params(params)
    elif normalized_mode == "resourcing":
        from python_solvers.domains import resourcing
        mapped = resourcing.map_params(params)
    elif normalized_mode == "scheduling":
        from python_solvers.domains import scheduling
        mapped = scheduling.map_params(params)
    elif normalized_mode == "generic":
        from python_solvers.domains import generic
        mapped = generic.map_params(params)
    else:
        mapped = dict(params or {})

    if isinstance(params, dict) and isinstance(params.get("NLP"), dict) and "NLP" not in mapped:
        mapped["NLP"] = params.get("NLP")
    return mapped


def generate_logic(template_type: str, params: Dict[str, Any], solver_type: str = "cp") -> Tuple[Any, Any, Any]:
        """
        Generate (objective_or_model, constraints, variables) for the Python solver path.
        Python runtime is CP-only after Julia migration for non-CP solvers.

        Args:
            template_type: cutting | packing | resourcing | scheduling | generic
            params: Raw or pre-mapped params (domain.map_params assumed)
            solver_type: "cp" only

        Returns:
            (objective_or_model, constraints, variables)
        """
        mapped = map_params_by_mode(template_type, params)
        mode = (template_type or "").strip().lower()
        normalized_mode = MODES.get(mode, mode)

        if solver_type is None:
                solver_type = "cp"
        solver_type = (solver_type or "").strip().lower()

        if solver_type == "cp":
                from python_solvers.logic import logic_cp
                return logic_cp.build_model(normalized_mode, mapped)

        raise ValueError("Python bridge only supports solver_type='cp'. Use Julia runtime for non-CP solvers.")

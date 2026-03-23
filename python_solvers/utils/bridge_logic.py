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
        return cutting.map_params(params)
    if normalized_mode == "packing":
        from python_solvers.domains import packing
        return packing.map_params(params)
    if normalized_mode == "resourcing":
        from python_solvers.domains import resourcing
        return resourcing.map_params(params)
    if normalized_mode == "scheduling":
        from python_solvers.domains import scheduling
        return scheduling.map_params(params)
    if normalized_mode == "generic":
        from python_solvers.domains import generic
        return generic.map_params(params)
    
    return params


def generate_logic(
    template_type: str,
    params: Dict[str, Any],
    solver_type: str | None = None,
) -> Tuple[Union[Any, List], List[Any], List[Dict[str, Any]]]:
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

    # Auto-select solver_type if not provided for backward compatibility.
    if solver_type is None:
        solver_type = "cp"

    solver_type = (solver_type or "").strip().lower()

    # Route to CP logic module only.
    if solver_type == "cp":
        from python_solvers.logic import logic_cp
        return logic_cp.build_model(normalized_mode, mapped)

    raise ValueError("Python bridge only supports solver_type='cp'. Use Julia runtime for non-CP solvers.")

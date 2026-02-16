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
    # Backward compat aliases
    "manufacturing": "cutting",
    "logistics": "packing",
    "resource_allocation": "resourcing",
    "resource": "resourcing",
    "it": "resourcing",
    "hr": "scheduling",
    "nsp": "scheduling",
}

SOLVER_TYPES = ["cg", "mip", "cp", "st", "nlp"]


def map_params_by_mode(mode: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map raw payload to common solver format by domain mode.
    Routes to domain module's map_params().
    """
    mode = (mode or "").strip().lower()
    normalized_mode = MODES.get(mode, mode)

    if normalized_mode == "cutting":
        from core.domains import cutting
        return cutting.map_params(params)
    if normalized_mode == "packing":
        from core.domains import packing
        return packing.map_params(params)
    if normalized_mode == "resourcing":
        from core.domains import resourcing
        return resourcing.map_params(params)
    if normalized_mode == "scheduling":
        from core.domains import scheduling
        return scheduling.map_params(params)
    
    return params


def generate_logic(
    template_type: str,
    params: Dict[str, Any],
    solver_type: str | None = None,
) -> Tuple[Union[Any, List], List[Any], List[Dict[str, Any]]]:
    """
    Generate (objective_or_model, constraints, variables) for the solver.
    Routes domain-mapped params to logic module based on solver_type.
    
    Args:
      template_type: cutting | packing | resourcing | scheduling
      params: Raw or pre-mapped params (domain.map_params assumed)
      solver_type: "cg", "mip", "cp", "st", "nlp" (defaults by mode)
    
    Returns:
      (objective_or_model, constraints, variables)
    """
    mapped = map_params_by_mode(template_type, params)
    mode = (template_type or "").strip().lower()
    normalized_mode = MODES.get(mode, mode)

    # Auto-select solver_type if not provided
    if solver_type is None:
        if normalized_mode == "cutting":
            solver_type = "cg" if mapped.get("Sense", "minimize") == "minimize" else "mip"
        else:
            solver_type = "mip"

    solver_type = (solver_type or "").strip().lower()

    # Route to logic module
    if solver_type == "cg":
        from core.logic import logic_cg
        return logic_cg.build_model(normalized_mode, mapped)
    
    if solver_type == "mip":
        from core.logic import logic_mip
        return logic_mip.build_model(normalized_mode, mapped)
    
    if solver_type == "cp":
        from core.logic import logic_cp
        return logic_cp.build_model(normalized_mode, mapped)
    
    if solver_type == "st":
        from core.logic import logic_st
        return logic_st.build_model(normalized_mode, mapped)
    
    if solver_type == "nlp":
        from core.logic import logic_nlp
        return logic_nlp.build_model(normalized_mode, mapped)

    return [], [], []
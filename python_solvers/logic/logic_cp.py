"""Constraint programming builder with OR-Tools support for scheduling."""
from typing import Any, Dict, List, Tuple


def build_model(domain: str, params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    if not isinstance(params, dict):
        raise ValueError(f"Params missing for domain '{domain}'")

    if domain == "scheduling":
        spec = params.get("CP")
        if not isinstance(spec, dict):
            raise ValueError("CP spec missing for scheduling")
        variables = spec.get("variables", [])
        if not isinstance(variables, list):
            raise ValueError("Invalid CP variable structure")
        return ({"engine": "ortools_cp_sat", "domain": domain, "spec": spec}, [], variables)

    ir = params.get("IR")
    if not isinstance(ir, dict):
        raise ValueError(f"IR missing for domain '{domain}'")

    objective = ir.get("objective", [])
    constraints = ir.get("constraints", [])
    variables = ir.get("variables", [])

    if not isinstance(objective, list) or not isinstance(constraints, list) or not isinstance(variables, list):
        raise ValueError("Invalid IR structure")

    return (objective, constraints, variables)


def solve_cp(params):
    objective, constraints, variables = build_model(str(params.get("Mode", "")), params)
    return {
        "status": "Ready",
        "engine": "CP",
        "objective": objective,
        "constraints": constraints,
        "variables": variables,
    }

"""Generic MIP builder from domain-provided IR."""

from typing import Any, Dict, List, Tuple


def build_model(domain: str, params: Dict[str, Any]) -> Tuple[Any, List[Any], List[Dict[str, Any]]]:
    ir = params.get("IR") if isinstance(params, dict) else None
    if not isinstance(ir, dict):
        raise ValueError(f"IR missing for domain '{domain}'")

    objective = ir.get("objective", [])
    constraints = ir.get("constraints", [])
    variables = ir.get("variables", [])

    if not isinstance(objective, list) or not isinstance(constraints, list) or not isinstance(variables, list):
        raise ValueError("Invalid IR structure")

    return (objective, constraints, variables)
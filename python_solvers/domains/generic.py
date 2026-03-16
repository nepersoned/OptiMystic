"""
Domain: Generic optimization
Accepts expert-provided IR directly with minimal normalization.
"""
from typing import Any, Dict, List


VALID_VAR_TYPES = {"Continuous", "Integer", "Binary"}
VALID_SENSES = {"minimize", "maximize"}
VALID_CONSTRAINT_TYPES = {"linear", "fix"}
VALID_RELATIONS = {"<=", ">=", "==", "="}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _normalize_var(var: Dict[str, Any]) -> Dict[str, Any] | None:
    if not isinstance(var, dict):
        return None
    name = str(var.get("name", "")).strip()
    if not name:
        return None
    vtype = str(var.get("type", "Continuous")).strip().title()
    if vtype not in VALID_VAR_TYPES:
        vtype = "Continuous"
    normalized = {"name": name, "type": vtype, "lb": var.get("lb", 0)}
    if "ub" in var:
        normalized["ub"] = var.get("ub")
    return normalized


def _normalize_objective_term(term: Dict[str, Any]) -> Dict[str, Any] | None:
    if not isinstance(term, dict):
        return None
    name = str(term.get("var", "")).strip()
    if not name:
        return None
    return {"var": name, "coef": float(term.get("coef", 0) or 0)}


def _normalize_constraint(constraint: Dict[str, Any], index: int) -> Dict[str, Any] | None:
    if not isinstance(constraint, dict):
        return None
    ctype = str(constraint.get("type", "linear")).strip().lower()
    if ctype not in VALID_CONSTRAINT_TYPES:
        return None
    name = str(constraint.get("name", f"constraint_{index}")).strip() or f"constraint_{index}"
    if ctype == "fix":
        var_name = str(constraint.get("var", "")).strip()
        if not var_name:
            return None
        return {"name": name, "type": "fix", "var": var_name, "value": float(constraint.get("value", 0) or 0)}

    terms = []
    for term in _as_list(constraint.get("terms", [])):
        if not isinstance(term, dict):
            continue
        var_name = str(term.get("var", "")).strip()
        if not var_name:
            continue
        terms.append({"var": var_name, "coef": float(term.get("coef", 0) or 0)})
    relation = str(constraint.get("sense", "<=")).strip()
    if relation == "=":
        relation = "=="
    if relation not in VALID_RELATIONS:
        relation = "<="
    return {
        "name": name,
        "type": "linear",
        "terms": terms,
        "sense": relation,
        "rhs": float(constraint.get("rhs", 0) or 0),
    }


def map_params(raw_params: Dict[str, Any]) -> Dict[str, Any]:
    raw_params = dict(raw_params or {})
    ir = raw_params.get("IR") if isinstance(raw_params.get("IR"), dict) else {}

    variables = [v for v in (_normalize_var(v) for v in _as_list(ir.get("variables", []))) if v is not None]
    objective = [t for t in (_normalize_objective_term(t) for t in _as_list(ir.get("objective", []))) if t is not None]
    constraints = []
    for idx, raw_constraint in enumerate(_as_list(ir.get("constraints", []))):
        normalized = _normalize_constraint(raw_constraint, idx)
        if normalized is not None:
            constraints.append(normalized)

    sense = str(raw_params.get("Sense", ir.get("meta", {}).get("sense", "minimize"))).strip().lower()
    if sense not in VALID_SENSES:
        sense = "minimize"

    mapped = dict(raw_params)
    mapped.update({
        "Mode": "generic",
        "Sense": sense,
        "IR": {
            "meta": {"domain": "generic", "sense": sense},
            "variables": variables,
            "objective": objective,
            "constraints": constraints,
        },
    })
    return mapped

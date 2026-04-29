"""Shared IR normalization and diagnostics for domain mappers."""
from typing import Any, Dict, List


VALID_VAR_TYPES = {"Continuous", "Integer", "Binary"}
VALID_CONSTRAINT_TYPES = {"linear", "fix"}
VALID_RELATIONS = {"<=", ">=", "==", "="}
VALID_SENSES = {"minimize", "maximize"}


def _safe_list(values: Any, length: int, default: float = 0.0) -> List[Any]:
    if not isinstance(values, list):
        return [default] * length
    if len(values) >= length:
        return values[:length]
    return values + [default] * (length - len(values))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_sense(value: Any, default: str = "minimize") -> str:
    sense = str(value or default).strip().lower()
    if sense not in VALID_SENSES:
        return default
    return sense


def _normalize_var(var: Any, index: int) -> Dict[str, Any] | None:
    if not isinstance(var, dict):
        return None
    name = str(var.get("name", "")).strip()
    if not name:
        return None

    raw_vtype = str(var.get("type", "Continuous")).strip().title()
    vtype = raw_vtype if raw_vtype in VALID_VAR_TYPES else "Continuous"
    lb = _safe_float(var.get("lb", 0.0), 0.0)

    normalized = {
        "name": name,
        "type": vtype,
        "lb": lb,
    }
    if "ub" in var and var.get("ub") is not None:
        normalized["ub"] = _safe_float(var.get("ub"), 0.0)
    return normalized


def _normalize_objective_term(term: Any) -> Dict[str, Any] | None:
    if not isinstance(term, dict):
        return None
    var_name = str(term.get("var", "")).strip()
    if not var_name:
        return None
    return {"var": var_name, "coef": _safe_float(term.get("coef", 0.0), 0.0)}


def _normalize_constraint(constraint: Any, index: int, max_terms_per_constraint: int) -> Dict[str, Any] | None:
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
        return {
            "name": name,
            "type": "fix",
            "var": var_name,
            "value": _safe_float(constraint.get("value", 0.0), 0.0),
        }

    relation = str(constraint.get("sense", "<=")).strip()
    if relation not in VALID_RELATIONS:
        relation = "<="
    if relation == "=":
        relation = "=="

    normalized_terms: List[Dict[str, Any]] = []
    raw_terms = constraint.get("terms", [])
    if isinstance(raw_terms, list):
        for term in raw_terms[:max_terms_per_constraint]:
            if not isinstance(term, dict):
                continue
            var_name = str(term.get("var", "")).strip()
            if not var_name:
                continue
            normalized_terms.append({"var": var_name, "coef": _safe_float(term.get("coef", 0.0), 0.0)})

    return {
        "name": name,
        "type": "linear",
        "terms": normalized_terms,
        "sense": relation,
        "rhs": _safe_float(constraint.get("rhs", 0.0), 0.0),
    }


def finalize_ir(
    ir: Dict[str, Any] | None,
    domain: str,
    sense: str = "minimize",
    max_terms_per_constraint: int = 50000,
) -> Dict[str, Any]:
    """
    Normalize IR schema across domains and attach size diagnostics.
    This makes downstream language/runtime ports deterministic.
    """
    raw = ir if isinstance(ir, dict) else {}
    normalized_sense = _normalize_sense(sense, default="minimize")

    variables: List[Dict[str, Any]] = []
    raw_variables = raw.get("variables", []) if isinstance(raw.get("variables", []), list) else []
    for index, raw_var in enumerate(raw_variables):
        normalized_var = _normalize_var(raw_var, index)
        if normalized_var is not None:
            variables.append(normalized_var)

    variable_names = {v["name"] for v in variables}

    objective: List[Dict[str, Any]] = []
    dropped_objective_terms = 0
    raw_objective = raw.get("objective", [])
    if isinstance(raw_objective, list):
        for term in raw_objective:
            normalized_term = _normalize_objective_term(term)
            if normalized_term is None:
                continue
            if normalized_term["var"] not in variable_names:
                dropped_objective_terms += 1
                continue
            objective.append(normalized_term)

    constraints: List[Dict[str, Any]] = []
    dropped_constraint_terms = 0
    raw_constraints = raw.get("constraints", [])
    if isinstance(raw_constraints, list):
        for index, constraint in enumerate(raw_constraints):
            normalized_constraint = _normalize_constraint(constraint, index, max_terms_per_constraint)
            if normalized_constraint is None:
                continue
            if normalized_constraint["type"] == "linear":
                filtered_terms = [
                    term for term in normalized_constraint.get("terms", []) if term.get("var") in variable_names
                ]
                dropped_constraint_terms += max(0, len(normalized_constraint.get("terms", [])) - len(filtered_terms))
                normalized_constraint["terms"] = filtered_terms
            elif normalized_constraint["type"] == "fix" and normalized_constraint.get("var") not in variable_names:
                dropped_constraint_terms += 1
                continue
            constraints.append(normalized_constraint)

    num_variables = len(variables)
    num_constraints = len(constraints)
    num_objective_terms = len(objective)
    num_constraint_terms = sum(len(c.get("terms", [])) for c in constraints if c.get("type") == "linear")
    complexity_score = num_variables + num_constraints + num_objective_terms + num_constraint_terms
    heavy = (
        num_variables > 5000
        or num_constraints > 5000
        or num_constraint_terms > 200000
        or complexity_score > 250000
    )

    raw_meta = raw.get("meta", {}) if isinstance(raw.get("meta"), dict) else {}
    meta = dict(raw_meta)
    meta["domain"] = str(domain).strip().lower() or "generic"
    meta["sense"] = normalized_sense
    meta["stats"] = {
        "variables": num_variables,
        "constraints": num_constraints,
        "objective_terms": num_objective_terms,
        "constraint_terms": num_constraint_terms,
        "complexity_score": complexity_score,
        "heavy": heavy,
        "dropped_objective_terms": dropped_objective_terms,
        "dropped_constraint_terms": dropped_constraint_terms,
    }

    return {
        "meta": meta,
        "variables": variables,
        "objective": objective,
        "constraints": constraints,
    }

import json
import re
from typing import Any, Dict, List

from .config import MAX_CONTEXT_MESSAGES


def extract_error_code(result: Dict[str, Any]) -> str:
    error = result.get("error") or {}
    return str(error.get("code", "")).strip().lower()


def is_retryable_error(result: Dict[str, Any]) -> bool:
    code = extract_error_code(result)
    return code in {"validation_error", "invalid_mapping_rule", "optimization_infeasible", "optimization_unbounded"}


def _norm_col(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]", "", str(text or "")).lower()


def infer_mapping_rule(domain: str, columns: List[str]) -> Dict[str, str]:
    if (domain or "").strip().lower() != "packing":
        return {}

    aliases: Dict[str, List[str]] = {
        "Name": ["name", "item", "sku", "품목명", "품목", "상품명"],
        "Weight": ["weight", "중량", "무게", "단위중량", "단위중량kg"],
        "Demand": ["demand", "수요", "당일발주량", "발주량", "qty", "quantity", "주문수량"],
    }

    col_norm = {c: _norm_col(c) for c in columns}
    rule: Dict[str, str] = {}
    used_targets: set[str] = set()
    for source_col, source_norm in col_norm.items():
        for target, alias_list in aliases.items():
            if target in used_targets:
                continue
            if source_norm in {_norm_col(a) for a in alias_list}:
                rule[source_col] = target
                used_targets.add(target)
                break
    return rule


def to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return to_jsonable(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            return to_jsonable(value.dict())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return to_jsonable(vars(value))
        except Exception:
            pass
    return str(value)


def summarize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    properties = schema.get("properties") if isinstance(schema, dict) else {}
    required = schema.get("required") if isinstance(schema, dict) else []
    defs = schema.get("$defs") if isinstance(schema, dict) else {}
    return {
        "top_level_fields": sorted(list((properties or {}).keys())),
        "required": required if isinstance(required, list) else [],
        "defs": sorted(list((defs or {}).keys())),
    }


def summarize_tool_result(tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {"ok": False, "error": {"code": "invalid_tool_result", "message": "Tool result is not a dict."}}

    if not result.get("ok"):
        return {"ok": False, "error": result.get("error", {})}

    if tool_name == "read_company_data":
        sample = result.get("sample_data") or []
        return {
            "ok": True,
            "file_name": result.get("file_name"),
            "file_path": result.get("file_path"),
            "total_rows": result.get("total_rows"),
            "columns": result.get("columns", []),
            "sample_data": sample[:2] if isinstance(sample, list) else [],
        }

    if tool_name == "get_target_schema":
        return {
            "ok": True,
            "domain": result.get("domain"),
            "schema_summary": summarize_schema(result.get("schema") or {}),
        }

    if tool_name == "map_to_target_schema":
        payload = result.get("payload") if isinstance(result.get("payload"), dict) else {}
        items = payload.get("Items") if isinstance(payload.get("Items"), list) else []
        return {
            "ok": True,
            "domain": result.get("domain"),
            "mapped_record_count": result.get("mapped_record_count"),
            "mapping_rule": result.get("mapping_rule", {}),
            "payload_summary": {
                "keys": sorted(list(payload.keys())),
                "items_count": len(items),
            },
        }

    if tool_name == "optimize":
        solve_result = result.get("result") if isinstance(result.get("result"), dict) else {}
        return {
            "ok": True,
            "status": solve_result.get("status"),
            "objective": solve_result.get("objective"),
            "solve_time": solve_result.get("solve_time"),
        }

    return result


def trim_messages(messages: List[Dict[str, Any]], max_messages: int = MAX_CONTEXT_MESSAGES) -> List[Dict[str, Any]]:
    if len(messages) <= max_messages:
        return messages
    head = messages[:1]
    tail = messages[-(max_messages - 1) :]
    return head + tail


def normalize_tool_args(raw_args: Any) -> Dict[str, Any]:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def normalize_tool_calls(raw_tool_calls: Any) -> List[Dict[str, Any]]:
    normalized = to_jsonable(raw_tool_calls)
    if not isinstance(normalized, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in normalized:
        if isinstance(item, dict):
            out.append(item)
    return out


_FIELD_CANONICAL: Dict[str, str] = {
    "name": "Name", "weight": "Weight", "value": "Value", "demand": "Demand",
    "capacity": "Capacity", "id": "Id",
    "items": "Items", "vehicles": "Vehicles",
    "nodes": "Nodes", "employees": "Employees", "shifts": "Shifts",
    "containers": "Containers", "servers": "Servers",
    "stocks": "Stocks", "kerf": "Kerf",
    "maxshifts": "MaxShifts",
    "cpu": "CPU", "ram": "RAM", "cost": "Cost",
    "x": "X", "y": "Y",
    "length": "Length", "limit": "Limit",
}


def _canonicalize_key(k: str) -> str:
    return _FIELD_CANONICAL.get(k.lower(), k)


def canonicalize_params(params: Any) -> Any:
    if isinstance(params, dict):
        return {_canonicalize_key(k): canonicalize_params(v) for k, v in params.items()}
    if isinstance(params, list):
        return [canonicalize_params(i) for i in params]
    return params


def normalize_args_for_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(args) if isinstance(args, dict) else {}

    if tool_name == "map_to_target_schema":
        normalized.pop("source_columns", None)
        mapping_rule = normalized.get("mapping_rule")
        if isinstance(mapping_rule, str):
            try:
                parsed = json.loads(mapping_rule)
                if isinstance(parsed, dict):
                    normalized["mapping_rule"] = parsed
            except Exception:
                pass
        return normalized

    if tool_name == "optimize":
        if "request" in normalized and isinstance(normalized.get("request"), dict):
            req = dict(normalized["request"])
            if "params" not in req and "payload" in req:
                req["params"] = req.pop("payload")
            if "solver" not in req:
                req["solver"] = "mip"
            if isinstance(req.get("params"), dict):
                req["params"] = canonicalize_params(req["params"])
            return {"request": req}

        domain = normalized.get("domain")
        params = normalized.get("params")
        payload = normalized.get("payload")
        solver = normalized.get("solver") or "mip"
        if params is None and isinstance(payload, dict):
            params = payload

        if domain and isinstance(params, dict):
            return {
                "request": {
                    "domain": domain,
                    "solver": solver,
                    "params": canonicalize_params(params),
                }
            }
    return normalized

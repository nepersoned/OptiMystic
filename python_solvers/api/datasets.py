from __future__ import annotations

import io
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from python_solvers.api.solver_api import run_optimization
from python_solvers.r_bridge import analyze_with_r as _r_analyze
from python_solvers.db import (
    add_dataset_version,
    create_dataset,
    get_dataset_latest_version,
    get_dataset_version,
    is_database_enabled,
    list_dataset_versions,
    list_datasets,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])

DEFAULT_CHAT_MODEL = "gemma-4-26b-a4b-it"
_CHAT_MODEL_ALIASES = {
    "gemini-2.0-flash": DEFAULT_CHAT_MODEL,
    "models/gemini-2.0-flash": DEFAULT_CHAT_MODEL,
    "gemini-2.0-flash-001": DEFAULT_CHAT_MODEL,
    "models/gemini-2.0-flash-001": DEFAULT_CHAT_MODEL,
    "gemma 4 26b": DEFAULT_CHAT_MODEL,
}


def _resolve_chat_model() -> str:
    raw = os.getenv("OPTIMYSTIC_CHAT_MODEL", DEFAULT_CHAT_MODEL).strip()
    if not raw:
        return DEFAULT_CHAT_MODEL
    return _CHAT_MODEL_ALIASES.get(raw.lower(), raw)


CHAT_MODEL = _resolve_chat_model()


# DATABASE_URL 미설정 환경에서도 UI 기능을 사용할 수 있도록 인메모리 저장소를 제공한다.
_MEM_DATASETS: Dict[int, Dict[str, Any]] = {}
_MEM_NEXT_DATASET_ID = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mem_create_dataset(name: str, filename: str, rows: List[Dict[str, Any]], columns: List[str]) -> int:
    global _MEM_NEXT_DATASET_ID
    dataset_id = _MEM_NEXT_DATASET_ID
    _MEM_NEXT_DATASET_ID += 1
    _MEM_DATASETS[dataset_id] = {
        "dataset_id": dataset_id,
        "name": name,
        "filename": filename,
        "versions": [
            {
                "version": 1,
                "rows": rows,
                "columns": columns,
                "note": "upload",
                "created_at": _now_iso(),
            }
        ],
    }
    return dataset_id


def _mem_get_dataset(dataset_id: int) -> Optional[Dict[str, Any]]:
    return _MEM_DATASETS.get(dataset_id)


def _mem_get_version(dataset_id: int, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
    ds = _mem_get_dataset(dataset_id)
    if ds is None:
        return None
    versions = ds.get("versions") or []
    if not versions:
        return None
    if version is None:
        v = versions[-1]
    else:
        matched = [item for item in versions if int(item.get("version", 0)) == int(version)]
        if not matched:
            return None
        v = matched[-1]
    return {
        "dataset_id": dataset_id,
        "name": ds.get("name", "dataset"),
        "version": int(v.get("version", 1)),
        "columns": list(v.get("columns") or []),
        "rows": list(v.get("rows") or []),
        "row_count": len(v.get("rows") or []),
    }


def _mem_add_version(dataset_id: int, rows: List[Dict[str, Any]], columns: List[str], note: Optional[str] = None) -> int:
    ds = _mem_get_dataset(dataset_id)
    if ds is None:
        raise KeyError(f"Dataset {dataset_id} not found")
    versions = ds.setdefault("versions", [])
    new_version = (int(versions[-1].get("version", 1)) + 1) if versions else 1
    versions.append(
        {
            "version": new_version,
            "rows": rows,
            "columns": columns,
            "note": note,
            "created_at": _now_iso(),
        }
    )
    return new_version


def _mem_list_versions(dataset_id: int) -> List[Dict[str, Any]]:
    ds = _mem_get_dataset(dataset_id)
    if ds is None:
        return []
    out: List[Dict[str, Any]] = []
    for v in ds.get("versions") or []:
        out.append(
            {
                "version": int(v.get("version", 1)),
                "note": v.get("note"),
                "created_at": str(v.get("created_at") or _now_iso()),
            }
        )
    return out


def _require_db() -> None:
    if not is_database_enabled():
        raise HTTPException(
            status_code=503,
            detail={"code": "database_disabled", "message": "Set DATABASE_URL to enable dataset features."},
        )


def _get_tenant(request: Request) -> str:
    from python_solvers.api.main import _require_api_key
    trace_id = str(getattr(request.state, "trace_id", "") or "")
    return _require_api_key(request, trace_id)


def _scope_tenant(tenant_id: str) -> Optional[str]:
    return tenant_id if tenant_id not in {"public", "shared"} else None


def _infer_domain_solver(columns: List[str]) -> tuple[str, str]:
    joined = " ".join(c.lower() for c in columns)
    if any(kw in joined for kw in (
        "vehicle", "route", "node", "depot", "pickup", "delivery", "latitude", "longitude",
        "위도", "경도", "배송", "주문번호", "거래처", "time_window", "배송가능", "마감시간",
    )):
        return "vrp", "mip"
    if any(kw in joined for kw in (
        "shift", "worker", "employee", "schedule", "availability",
        "근무", "시프트", "작업자", "스케줄",
    )):
        return "scheduling", "cp"
    if any(kw in joined for kw in (
        "length", "stock", "cut", "waste", "pattern",
        "절단", "원자재", "재단",
    )):
        return "cutting", "cg"
    if any(kw in joined for kw in (
        "weight", "value", "item", "capacity", "packing",
        "무게", "용량", "적재",
    )):
        return "packing", "mip"
    return "generic", "nlp"


def _safe_num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _parse_number(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        raw = v.strip()
        if not raw:
            return default
        m = re.search(r"[-+]?\d+(?:\.\d+)?", raw.replace(",", ""))
        if m:
            try:
                return float(m.group(0))
            except (TypeError, ValueError):
                return default
    return default


def _parse_time_to_minutes(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    if isinstance(v, (int, float)):
        n = float(v)
        if n >= 100 and float(int(n)) == n:
            hh = int(n) // 100
            mm = int(n) % 100
            if 0 <= hh < 24 and 0 <= mm < 60:
                return float(hh * 60 + mm)
        return n
    if not isinstance(v, str):
        return default

    txt = v.strip().lower()
    if not txt:
        return default

    m = re.match(r"^(\d{1,2})\s*[:시]\s*(\d{1,2})\s*분?$", txt)
    if m:
        hh = int(m.group(1))
        mm = int(m.group(2))
        if 0 <= hh < 24 and 0 <= mm < 60:
            return float(hh * 60 + mm)

    m = re.match(r"^(\d{3,4})$", txt)
    if m:
        n = int(m.group(1))
        hh = n // 100
        mm = n % 100
        if 0 <= hh < 24 and 0 <= mm < 60:
            return float(hh * 60 + mm)

    m = re.match(r"^(\d{1,2})\s*시$", txt)
    if m:
        hh = int(m.group(1))
        if 0 <= hh < 24:
            return float(hh * 60)

    return default


def _shift_hhmm(time_text: Any, delta_hours: int) -> Optional[str]:
    if not isinstance(time_text, str):
        return None
    raw = time_text.strip()
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", raw)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2))
    total = hour * 60 + minute + (delta_hours * 60)
    total %= 24 * 60
    if total < 0:
        total += 24 * 60
    nh = total // 60
    nm = total % 60
    return f"{nh:02d}:{nm:02d}"


def _extract_hour_shift(message: str) -> int:
    msg = (message or "").strip()
    if not msg:
        return 0
    m = re.search(r"(\d+)\s*시간", msg)
    hours = int(m.group(1)) if m else 1
    if any(k in msg for k in ("앞당", "당겨", "이르게", "빨리")):
        return -hours
    if any(k in msg for k in ("늦춰", "미뤄", "뒤로", "지연")):
        return hours
    return 0


def _build_district_time_shift_response(message: str, rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    msg = (message or "").strip()
    if not msg:
        return None
    if not any(k in msg for k in ("시간", "출발", "time_window", "window")):
        return None

    delta_hours = _extract_hour_shift(msg)
    if delta_hours == 0:
        return None

    districts = {str(r.get("district", "")).strip() for r in rows if str(r.get("district", "")).strip()}
    target_district = next((d for d in districts if d and d in msg), None)
    if not target_district:
        return None

    diffs: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if str(row.get("district", "")).strip() != target_district:
            continue
        shifted_open = _shift_hhmm(row.get("time_window_open"), delta_hours)
        shifted_close = _shift_hhmm(row.get("time_window_close"), delta_hours)
        if shifted_open is not None:
            diffs.append({"row": idx, "col": "time_window_open", "value": shifted_open})
        if shifted_close is not None:
            diffs.append({"row": idx, "col": "time_window_close", "value": shifted_close})

    if not diffs:
        return None

    direction = "earlier" if delta_hours < 0 else "later"
    return {
        "reply": f"Shifted time windows for district '{target_district}' by {abs(delta_hours)}h {direction}.",
        "recommended_domain": "vrp",
        "recommended_solver": "mip",
        "reason": f"Applied uniform time window shift to all rows where district='{target_district}'.",
        "suggested_diffs": diffs,
    }


def _normalize_suggested_diffs(result: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return result

    # 데이터가 사실상 비어 있으면 어떤 경우에도 수정 제안을 생성하지 않는다.
    if _rows_effectively_empty(rows):
        result["suggested_diffs"] = []
        return result

    raw_diffs = result.get("suggested_diffs")
    if not isinstance(raw_diffs, list):
        result["suggested_diffs"] = []
        return result

    order_to_idx: Dict[str, int] = {}
    for idx, row in enumerate(rows):
        oid = str(row.get("order_id", "")).strip()
        if oid and oid not in order_to_idx:
            order_to_idx[oid] = idx

    normalized: List[Dict[str, Any]] = []
    for diff in raw_diffs:
        if not isinstance(diff, dict):
            continue
        col = diff.get("col")
        value = diff.get("value")
        row_ref = diff.get("row")
        row_idx: Optional[int] = None

        if isinstance(row_ref, int):
            row_idx = row_ref
        elif isinstance(row_ref, str):
            row_txt = row_ref.strip()
            if row_txt.isdigit():
                row_idx = int(row_txt)
            elif row_txt in order_to_idx:
                row_idx = order_to_idx[row_txt]

        if row_idx is None:
            continue
        if not (0 <= row_idx < len(rows)):
            continue
        if not isinstance(col, str) or not col:
            continue
        normalized.append({"row": row_idx, "col": col, "value": value})

    result["suggested_diffs"] = normalized
    return result


def _rows_effectively_empty(rows: List[Dict[str, Any]]) -> bool:
    if not rows:
        return True

    def _is_blank(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        return False

    for row in rows:
        if not isinstance(row, dict):
            return False
        # 한 셀이라도 값이 있으면 "비어 있음"으로 보지 않는다.
        if any(not _is_blank(v) for v in row.values()):
            return False
    return True


def _rows_to_params(domain: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if domain == "packing":
        return {"Items": rows, "Vehicles": [{"Capacity": 100}]}
    if domain == "cutting":
        return {"Items": rows, "Stocks": [{"Length": 100, "Cost": 1}]}
    if domain == "scheduling":
        return {"Shifts": rows, "Workers": []}
    if domain == "vrp":
        depot_row = next((r for r in rows if str(r.get("order_id", "")).upper() == "DEPOT"), None)
        customer_rows = [r for r in rows if str(r.get("order_id", "")).upper() != "DEPOT"]

        def to_node(row: Dict[str, Any], idx: int) -> Dict[str, Any]:
            demand_val = _parse_number(
                row.get("demand_kg")
                or row.get("demand")
                or row.get("Demand")
                or row.get("배송중량")
                or row.get("배송 중량")
                or row.get("중량")
                or row.get("무게")
            )
            service_val = _parse_number(
                row.get("service_time_min")
                or row.get("service_time")
                or row.get("작업시간(분)")
                or row.get("작업시간")
            )
            ready_time = _parse_time_to_minutes(
                row.get("time_window_open")
                or row.get("배송가능시작")
                or row.get("배송 가능 시작")
            )
            due_time = _parse_time_to_minutes(
                row.get("time_window_close")
                or row.get("마감시간")
                or row.get("배송마감")
            )
            return {
                "Name": str(row.get("customer_name") or row.get("name") or row.get("거래처명") or f"Node_{idx}"),
                "X": _parse_number(row.get("longitude") or row.get("lon") or row.get("X") or row.get("x") or row.get("경도")),
                "Y": _parse_number(row.get("latitude") or row.get("lat") or row.get("Y") or row.get("y") or row.get("위도")),
                "Demand": demand_val,
                "ServiceTime": service_val,
                "ReadyTime": ready_time,
                "DueTime": due_time,
            }

        nodes = [to_node(r, i + 1) for i, r in enumerate(customer_rows)]
        total_demand = sum(n["Demand"] for n in nodes)
        num_vehicles = max(4, min(10, len(nodes) // 5))
        vehicle_capacity = max(500.0, (total_demand / max(1, num_vehicles)) * 1.5)

        if depot_row:
            depot: Dict[str, Any] = {
                "Name": str(depot_row.get("customer_name") or "물류센터"),
                "X": _safe_num(depot_row.get("longitude") or 126.9979),
                "Y": _safe_num(depot_row.get("latitude") or 37.5641),
                "Demand": 0,
            }
        else:
            depot = {"Name": "물류센터", "X": 126.9979, "Y": 37.5641, "Demand": 0}

        return {
            "Nodes": [depot] + nodes,
            "Vehicles": [{"Name": f"차량_{i + 1}", "Capacity": round(vehicle_capacity)} for i in range(num_vehicles)],
        }
    return {"data": rows}


def _top_variable_bar(variables: List[Dict[str, Any]], limit: int = 15) -> Dict[str, Any] | None:
    nonzero = [v for v in variables if isinstance(v, dict) and v.get("Value") not in (None, 0, 0.0)]
    top = sorted(nonzero, key=lambda v: abs(float(v.get("Value", 0))), reverse=True)[:limit]
    if not top:
        return None
    return {
        "categories": [str(v.get("Variable", f"var_{i}")) for i, v in enumerate(top)],
        "series": [{"name": "Value", "data": [round(float(v.get("Value", 0)), 4) for v in top]}],
    }


def _shadow_price_bar(constraints: List[Dict[str, Any]], limit: int = 10) -> Dict[str, Any] | None:
    nonzero = [c for c in constraints if isinstance(c, dict) and c.get("Shadow Price") not in (None, 0, 0.0)]
    top = sorted(nonzero, key=lambda c: abs(float(c.get("Shadow Price", 0))), reverse=True)[:limit]
    if not top:
        return None
    return {
        "categories": [str(c.get("Constraint", f"c_{i}")) for i, c in enumerate(top)],
        "series": [{"name": "Shadow Price", "data": [round(float(c.get("Shadow Price", 0)), 4) for c in top]}],
    }


def _build_chart_data(domain: str, result: Dict[str, Any]) -> Dict[str, Any]:
    variables: List[Dict[str, Any]] = result.get("variables") or []
    constraints: List[Dict[str, Any]] = result.get("constraints") or []
    details: Dict[str, Any] = result.get("details") or {}
    status = result.get("status", "unknown")
    objective = result.get("objective")
    solve_time = result.get("solve_time", 0)

    if domain == "vrp":
        routes = result.get("routes", [])
        if not routes:
            return {}
        return {
            "route_bar": {
                "categories": [r.get("vehicle", f"Vehicle_{i}") for i, r in enumerate(routes)],
                "series": [
                    {"name": "Distance", "data": [round(r.get("distance", 0), 1) for r in routes]},
                    {"name": "Load (kg)", "data": [round(r.get("load", 0), 1) for r in routes]},
                ],
            },
            "kpi": {
                "Total Distance": round(result.get("total_distance", 0), 1),
                "Vehicles Used": result.get("num_vehicles", len(routes)),
                "Unserved Stops": len(result.get("unserved", [])),
                "Total Load (kg)": round(result.get("total_load", 0), 1),
            },
        }

    if domain == "scheduling":
        assigned = [v for v in variables if isinstance(v, dict) and float(v.get("Value", 0)) > 0.5]
        obj_val = int(objective) if objective is not None else len(assigned)
        chart: Dict[str, Any] = {
            "kpi": {
                "Status": status,
                "Assignments Made": len(assigned),
                "Objective": obj_val,
                "Solve Time (s)": round(float(solve_time), 3),
            }
        }
        var_bar = _top_variable_bar(assigned)
        if var_bar:
            chart["assignment_bar"] = var_bar
        shadow = _shadow_price_bar(constraints)
        if shadow:
            chart["shadow_price_bar"] = shadow
        return chart

    if domain == "packing":
        obj_val = int(round(float(objective))) if objective is not None else None
        chart = {
            "kpi": {
                "Status": status,
                "Bins Used": obj_val,
                "Variables": len(variables),
                "Solve Time (s)": round(float(solve_time), 3),
            }
        }
        var_bar = _top_variable_bar(variables)
        if var_bar:
            chart["packing_bar"] = var_bar
        shadow = _shadow_price_bar(constraints)
        if shadow:
            chart["shadow_price_bar"] = shadow
        return chart

    if domain == "cutting":
        pattern_count = details.get("pattern_count")
        iterations = details.get("iterations")
        obj_val = round(float(objective), 4) if objective is not None else None
        chart = {
            "kpi": {
                "Status": status,
                "Objective (waste)": obj_val,
                "Patterns Generated": pattern_count,
                "CG Iterations": iterations,
                "Solve Time (s)": round(float(solve_time), 3),
            }
        }
        var_bar = _top_variable_bar(variables)
        if var_bar:
            chart["pattern_usage_bar"] = var_bar
        shadow = _shadow_price_bar(constraints)
        if shadow:
            chart["shadow_price_bar"] = shadow
        return chart

    if domain == "resourcing":
        scenario_count = details.get("scenario_count")
        hotspot_count = details.get("hotspot_count")
        obj_val = round(float(objective), 4) if objective is not None else None
        chart = {
            "kpi": {
                "Status": status,
                "Objective": obj_val,
                "Scenarios": scenario_count,
                "Hotspots": hotspot_count,
                "Solve Time (s)": round(float(solve_time), 3),
            }
        }
        var_bar = _top_variable_bar(variables)
        if var_bar:
            chart["resource_bar"] = var_bar
        shadow = _shadow_price_bar(constraints)
        if shadow:
            chart["shadow_price_bar"] = shadow
        return chart

    # generic / nlp / minlp
    engine = details.get("engine", details.get("solver", ""))
    var_count = details.get("variable_count") or len(variables)
    nonlinear = details.get("nonlinear_term_count")
    obj_val = round(float(objective), 6) if objective is not None else None
    chart = {
        "kpi": {
            "Status": status,
            "Objective": obj_val,
            "Variables": var_count,
            "Nonlinear Terms": nonlinear,
            "Engine": engine or None,
            "Solve Time (s)": round(float(solve_time), 3),
        }
    }
    var_bar = _top_variable_bar(variables)
    if var_bar:
        chart["variable_bar"] = var_bar
    shadow = _shadow_price_bar(constraints)
    if shadow:
        chart["shadow_price_bar"] = shadow
    return chart


def _build_executive_summary(domain: str, result: Dict[str, Any]) -> Dict[str, Any]:
    status = result.get("status", "unknown")
    objective = result.get("objective")
    solve_time = result.get("solve_time", 0)
    details: Dict[str, Any] = result.get("details") or {}
    feasible = status in ("optimal", "feasible")

    if domain == "vrp":
        unserved = result.get("unserved", [])
        routes = result.get("routes", []) or []
        total_dist = result.get("total_distance", 0)
        total_load = result.get("total_load", 0)
        try:
            num_v = int(result.get("num_vehicles") or 0)
        except (TypeError, ValueError):
            num_v = 0
        if num_v <= 0 and routes:
            num_v = len(routes)
        headline = f"VRP solved: {num_v} vehicles dispatched, total distance {float(total_dist):.1f}"
        if unserved:
            headline += f" — {len(unserved)} stop(s) unserved"
        return {
            "headline": headline,
            "delta_pct": None,
            "kpi_deltas": {},
            "domain_kpi_line": (
                f"Total distance {float(total_dist or 0):.1f}, total load {float(total_load or 0):.1f}kg, "
                f"vehicles used {num_v if num_v > 0 else len(routes)}"
            ),
            "bottleneck": (
                f"Capacity exceeded — {len(unserved)} stop(s) unserved: {', '.join(str(u) for u in unserved[:3])}"
                if unserved else None
            ),
            "recommendation": (
                "Increase vehicle count or capacity to eliminate unserved stops."
                if unserved else "All stops successfully assigned."
            ),
            "feasible_rate": 1.0,
            "run_count": 1,
        }

    if domain == "scheduling":
        variables: List[Dict[str, Any]] = result.get("variables") or []
        assigned = sum(1 for v in variables if isinstance(v, dict) and float(v.get("Value", 0)) > 0.5)
        obj_val = int(objective) if objective is not None else assigned
        infeasible_count = len(variables) - assigned
        return {
            "headline": f"Scheduling solved: {assigned} assignments made (objective {obj_val})",
            "delta_pct": None,
            "kpi_deltas": {},
            "domain_kpi_line": f"{assigned} shifts assigned, solve time {float(solve_time):.2f}s",
            "bottleneck": (
                f"{infeasible_count} variables unassigned — constraints may be over-constrained"
                if infeasible_count > 0 and not feasible else None
            ),
            "recommendation": (
                "All shift requirements satisfied."
                if feasible else "Review constraint tightness — consider relaxing coverage requirements."
            ),
            "feasible_rate": 1.0 if feasible else 0.0,
            "run_count": 1,
        }

    if domain == "packing":
        obj_val = int(round(float(objective))) if objective is not None else None
        bins_str = f"{obj_val} bins" if obj_val is not None else "unknown bins"
        return {
            "headline": f"Bin packing solved: {bins_str} required (status: {status})",
            "delta_pct": None,
            "kpi_deltas": {},
            "domain_kpi_line": f"Optimal bins: {obj_val}, solve time {float(solve_time):.2f}s",
            "bottleneck": None if feasible else f"No feasible packing found (status: {status})",
            "recommendation": (
                f"Minimum {obj_val} bins required to pack all items."
                if feasible else "Check item sizes vs. bin capacity constraints."
            ),
            "feasible_rate": 1.0 if feasible else 0.0,
            "run_count": 1,
        }

    if domain == "cutting":
        pattern_count = details.get("pattern_count")
        iterations = details.get("iterations")
        obj_val = round(float(objective), 4) if objective is not None else None
        pattern_str = f"{pattern_count} patterns" if pattern_count is not None else "patterns"
        return {
            "headline": f"Cutting stock solved: {pattern_str} generated, waste {obj_val} (status: {status})",
            "delta_pct": None,
            "kpi_deltas": {},
            "domain_kpi_line": (
                f"Objective (waste): {obj_val}, patterns: {pattern_count}, "
                f"CG iterations: {iterations}, solve time {float(solve_time):.2f}s"
            ),
            "bottleneck": None if feasible else f"Infeasible cutting plan (status: {status})",
            "recommendation": (
                "Cutting plan is optimal — use generated patterns to minimize material waste."
                if feasible else "Review stock lengths and demand requirements."
            ),
            "feasible_rate": 1.0 if feasible else 0.0,
            "run_count": 1,
        }

    if domain == "resourcing":
        scenario_count = details.get("scenario_count")
        hotspot_count = details.get("hotspot_count")
        obj_val = round(float(objective), 4) if objective is not None else None
        scenario_str = f"{scenario_count} scenarios" if scenario_count is not None else "stochastic scenarios"
        return {
            "headline": f"Resource planning solved across {scenario_str} (objective {obj_val})",
            "delta_pct": None,
            "kpi_deltas": {},
            "domain_kpi_line": (
                f"Expected cost: {obj_val}, scenarios: {scenario_count}, "
                f"hotspots: {hotspot_count}, solve time {float(solve_time):.2f}s"
            ),
            "bottleneck": (
                f"{hotspot_count} hotspot(s) detected — high-variance scenarios requiring attention"
                if hotspot_count else None
            ),
            "recommendation": (
                "Resource plan is robust across all scenarios."
                if feasible and not hotspot_count else
                "Review hotspot scenarios and consider adding buffer capacity."
            ),
            "feasible_rate": 1.0 if feasible else 0.0,
            "run_count": 1,
        }

    # generic / nlp / minlp
    engine = details.get("engine", details.get("solver", domain.upper()))
    obj_val = round(float(objective), 6) if objective is not None else None
    var_count = details.get("variable_count") or len(result.get("variables") or [])
    return {
        "headline": f"Optimization solved via {engine}: objective {obj_val} (status: {status})",
        "delta_pct": None,
        "kpi_deltas": {},
        "domain_kpi_line": (
            f"Objective: {obj_val}, variables: {var_count}, solve time {float(solve_time):.2f}s"
        ),
        "bottleneck": None if feasible else f"Solver returned {status} — problem may be infeasible or unbounded",
        "recommendation": (
            "Solution found — review variable values for business interpretation."
            if feasible else "Check problem formulation: bounds, constraints, and initial values."
        ),
        "feasible_rate": 1.0 if feasible else 0.0,
        "run_count": 1,
    }


def _build_store_for_r(params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "parameters": params if isinstance(params, dict) else {},
        "variables": result.get("variables", []) if isinstance(result, dict) else [],
    }


# ── endpoints ───────────────────────────────────────────────────────────────

@router.get("")
def list_datasets_endpoint(request: Request) -> List[Dict[str, Any]]:
    tenant_id = _get_tenant(request)
    if is_database_enabled():
        return list_datasets(tenant_id=_scope_tenant(tenant_id))
    return [
        {
            "id": ds_id,
            "name": ds.get("name", f"dataset_{ds_id}"),
            "filename": ds.get("filename", "upload.csv"),
            "created_at": (ds.get("versions") or [{}])[0].get("created_at", _now_iso()),
            "latest_version": int((ds.get("versions") or [{}])[-1].get("version", 1)),
        }
        for ds_id, ds in sorted(_MEM_DATASETS.items())
    ]


@router.post("/upload")
async def upload_dataset(request: Request, file: UploadFile = File(...)) -> Dict[str, Any]:
    tenant_id = _get_tenant(request)

    content = await file.read()
    filename = file.filename or "upload"

    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"code": "parse_error", "message": str(exc)})

    df = df.where(pd.notna(df), None)
    columns: List[str] = df.columns.tolist()
    rows: List[Dict[str, Any]] = df.to_dict(orient="records")

    name = filename.rsplit(".", 1)[0]
    if is_database_enabled():
        dataset_id = create_dataset(
            name=name,
            filename=filename,
            tenant_id=_scope_tenant(tenant_id),
            rows=rows,
            columns=columns,
        )
    else:
        dataset_id = _mem_create_dataset(name=name, filename=filename, rows=rows, columns=columns)

    inferred_domain, inferred_solver = _infer_domain_solver(columns)
    return {
        "dataset_id": dataset_id,
        "name": name,
        "version": 1,
        "row_count": len(rows),
        "col_count": len(columns),
        "columns": columns,
        "inferred_domain": inferred_domain,
        "inferred_solver": inferred_solver,
    }


@router.get("/{dataset_id}/grid")
def get_grid(dataset_id: int, request: Request, version: Optional[int] = None) -> Dict[str, Any]:
    _get_tenant(request)

    if is_database_enabled():
        data = get_dataset_version(dataset_id, version) if version is not None else get_dataset_latest_version(dataset_id)
    else:
        data = _mem_get_version(dataset_id, version)
    if data is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Dataset {dataset_id} not found"})
    return data


class CellChange(BaseModel):
    row: int
    col: str
    value: Any


class PatchCellsRequest(BaseModel):
    changes: List[CellChange]
    note: Optional[str] = None


@router.patch("/{dataset_id}/cells")
def patch_cells(dataset_id: int, body: PatchCellsRequest, request: Request) -> Dict[str, Any]:
    _get_tenant(request)

    if is_database_enabled():
        data = get_dataset_latest_version(dataset_id)
    else:
        data = _mem_get_version(dataset_id)
    if data is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Dataset {dataset_id} not found"})

    rows = data["rows"]
    applied = 0
    for change in body.changes:
        if 0 <= change.row < len(rows):
            rows[change.row][change.col] = change.value
            applied += 1

    if is_database_enabled():
        new_version = add_dataset_version(dataset_id, rows, data["columns"], note=body.note or "cell edit")
    else:
        new_version = _mem_add_version(dataset_id, rows, data["columns"], note=body.note or "cell edit")
    return {"dataset_id": dataset_id, "version": new_version, "changes_applied": applied}


@router.get("/{dataset_id}/versions")
def list_versions(dataset_id: int, request: Request) -> List[Dict[str, Any]]:
    _get_tenant(request)
    if is_database_enabled():
        return list_dataset_versions(dataset_id)
    versions = _mem_list_versions(dataset_id)
    if not versions:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Dataset {dataset_id} not found"})
    return versions


@router.post("/{dataset_id}/versions/{version}/restore")
def restore_version(dataset_id: int, version: int, request: Request) -> Dict[str, Any]:
    _get_tenant(request)

    if is_database_enabled():
        data = get_dataset_version(dataset_id, version)
    else:
        data = _mem_get_version(dataset_id, version)
    if data is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Version {version} not found"})

    if is_database_enabled():
        new_version = add_dataset_version(dataset_id, data["rows"], data["columns"], note=f"restored from v{version}")
    else:
        new_version = _mem_add_version(dataset_id, data["rows"], data["columns"], note=f"restored from v{version}")
    return {"dataset_id": dataset_id, "restored_from": version, "new_version": new_version}


class DatasetOptimizeRequest(BaseModel):
    domain: Optional[str] = None
    solver: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


@router.post("/{dataset_id}/optimize")
def optimize_dataset(dataset_id: int, body: DatasetOptimizeRequest, request: Request) -> Dict[str, Any]:
    trace_id = str(getattr(request.state, "trace_id", "") or "")
    _get_tenant(request)

    if is_database_enabled():
        data = get_dataset_latest_version(dataset_id)
    else:
        data = _mem_get_version(dataset_id)
    if data is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Dataset {dataset_id} not found"})

    domain = body.domain
    solver = body.solver
    if not domain or not solver:
        inferred_domain, inferred_solver = _infer_domain_solver(data["columns"])
        domain = domain or inferred_domain
        solver = solver or inferred_solver

    params = body.params or _rows_to_params(domain, data["rows"])

    try:
        result = run_optimization(domain, solver, params, trace_id=trace_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"code": "solver_error", "message": str(exc)})

    chart_data = _build_chart_data(domain, result)
    executive_summary = _build_executive_summary(domain, result)
    r_analysis = _r_analyze(
        mode=domain,
        run_result=result,
        run_results=[result],
        store=_build_store_for_r(params if isinstance(params, dict) else {}, result),
    )

    if r_analysis.get("ok"):
        analysis = r_analysis.get("analysis", {})
        r_chart = analysis.get("chart_data")
        if isinstance(r_chart, dict) and r_chart:
            chart_data = r_chart
        r_summary = analysis.get("executive_summary")
        if isinstance(r_summary, dict) and r_summary:
            executive_summary = r_summary

    return {
        **result,
        "dataset_id": dataset_id,
        "domain_used": domain,
        "solver_used": solver,
        "chart_data": chart_data,
        "executive_summary": executive_summary,
        "r_analysis": r_analysis,
    }


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    version: Optional[int] = None
    history: List[ChatHistoryMessage] = []


@router.post("/{dataset_id}/chat")
async def chat_dataset(dataset_id: int, body: ChatRequest, request: Request) -> Dict[str, Any]:
    import asyncio as _aio
    _get_tenant(request)

    if is_database_enabled():
        data = (
            get_dataset_version(dataset_id, body.version)
            if body.version is not None
            else get_dataset_latest_version(dataset_id)
        )
    else:
        data = _mem_get_version(dataset_id, body.version)
    if data is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Dataset {dataset_id} not found"})

    columns = data["columns"]
    rows = data["rows"]
    inferred_domain, inferred_solver = _infer_domain_solver(columns)

    deterministic = _build_district_time_shift_response(body.message, rows)
    if deterministic is not None:
        return deterministic

    history = [{"role": m.role, "content": m.content} for m in body.history]

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return _chat_heuristic(body.message, columns, inferred_domain, inferred_solver)

    # Full agent loop (has access to MCP tools: forecast, R analysis, optimize)
    try:
        return await _chat_with_agent(body.message, columns, rows, inferred_domain, inferred_solver, api_key, history)
    except Exception:
        pass

    # Fallback: simple Gemini chat (no tools, but still multi-turn)
    try:
        return await _aio.to_thread(
            _chat_with_google, body.message, columns, rows, inferred_domain, inferred_solver, api_key, history
        )
    except Exception as e:
        return _chat_heuristic(body.message, columns, inferred_domain, inferred_solver, error=str(e))


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """모델이 추론 텍스트 앞에 쓰더라도 마지막 JSON 객체를 추출한다."""
    # 1) 전체 텍스트가 바로 JSON인 경우
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    # 2) 텍스트 내 마지막 { ... } 블록 추출
    last_brace = text.rfind("{")
    if last_brace == -1:
        return None
    candidate = text[last_brace:]
    # 닫히는 } 위치 찾기 (중첩 고려)
    depth = 0
    end = -1
    for i, ch in enumerate(candidate):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        return None
    try:
        parsed = json.loads(candidate[:end])
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return None


def _parse_suggested_diffs_from_text(text: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    m = re.search(r'SUGGESTED_DIFFS:\s*(\[.*?\])', text, re.DOTALL)
    if not m:
        return []
    try:
        diffs = json.loads(m.group(1))
        return _normalize_suggested_diffs({"suggested_diffs": diffs}, rows)["suggested_diffs"]
    except Exception:
        return []


_ACTION_KEYWORDS = {
    "최적화", "분석", "최적", "실행", "돌려", "해줘", "해봐", "계산", "구해", "예측", "확인해",
    "운영", "루트", "배차", "스케줄", "적재", "절단", "수요", "재고",
    "optimize", "analyse", "analyze", "run", "compute", "solve", "forecast", "check data",
}


def _has_action_intent(message: str) -> bool:
    msg = message.lower()
    return any(kw in msg for kw in _ACTION_KEYWORDS)


async def _chat_with_agent(
    message: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
    domain: str,
    solver: str,
    api_key: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    import tempfile
    try:
        from agent_core.runner import run_agent_loop
    except ImportError as exc:
        raise RuntimeError("agent_core not available") from exc

    history_ctx = ""
    if history:
        recent = history[-6:]
        history_ctx = "Recent conversation:\n" + "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in recent
        ) + "\n\n"

    action_intent = _has_action_intent(message)

    if not action_intent:
        # 대화/브레인스토밍 — 파일 없이 컨텍스트만 전달
        enriched_query = (
            f"Dataset context: columns={columns}, domain={domain}, rows={len(rows)}\n\n"
            f"{history_ctx}"
            f"User: {message}"
        )
        result = await run_agent_loop(
            user_query=enriched_query,
            model=CHAT_MODEL,
            llm_provider="google",
            max_steps=2,
            chat_timeout_sec=20,
        )
        if not result.get("ok"):
            raise RuntimeError((result.get("error") or {}).get("message") or "Agent failed")
        return {
            "reply": str(result.get("final") or ""),
            "recommended_domain": domain,
            "recommended_solver": solver,
            "reason": "conversation",
            "suggested_diffs": [],
        }

    # 액션 인텐트 — 파일 붙여서 풀 파이프라인
    df = pd.DataFrame(rows)
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='')
    try:
        df.to_csv(tmp, index=False)
        tmp.close()
        temp_path = tmp.name
    except Exception:
        tmp.close()
        os.unlink(tmp.name)
        raise

    try:
        enriched_query = (
            f"Dataset file: {temp_path}\n"
            f"Columns: {columns}\n"
            f"Domain: {domain}, Solver: {solver}, Rows: {len(rows)}\n\n"
            f"{history_ctx}"
            f"User: {message}\n\n"
            f"If you suggest cell edits, append at the end: "
            f"SUGGESTED_DIFFS:[{{\"row\":<int>,\"col\":\"<col>\",\"value\":<val>}},...]\n"
            f"Row indices are 0-based. If rows are empty, suggested_diffs must be []."
        )

        result = await run_agent_loop(
            user_query=enriched_query,
            model=CHAT_MODEL,
            llm_provider="google",
            max_steps=5,
            chat_timeout_sec=30,
        )

        if not result.get("ok"):
            err = ((result.get("error") or {}).get("message") or "")
            raise RuntimeError(err or "Agent failed")

        if result.get("optimization") and result["optimization"].get("ok"):
            opt_res = result["optimization"].get("result") or {}
            status = opt_res.get("status", "?")
            total_dist = opt_res.get("total_distance")
            base = result.get("final") or f"Optimization complete — status: {status}"
            agent_reply = base + (f" (total distance: {total_dist:.1f})" if total_dist else "")
        else:
            agent_reply = str(result.get("final") or "Analysis complete.")

        suggested_diffs = _parse_suggested_diffs_from_text(agent_reply, rows)
        clean_reply = re.sub(r'\s*SUGGESTED_DIFFS:\s*\[.*?\]\s*$', '', agent_reply, flags=re.DOTALL).strip()

        return {
            "reply": clean_reply or agent_reply,
            "recommended_domain": domain,
            "recommended_solver": solver,
            "reason": f"Agent ({result.get('step', '?')} steps)",
            "suggested_diffs": suggested_diffs,
        }
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass


def _chat_with_google(
    message: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
    domain: str,
    solver: str,
    api_key: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    try:
        from google import genai as google_genai
        from google.genai import types as google_types
    except Exception as exc:
        raise RuntimeError("google-genai not available") from exc

    client = google_genai.Client(api_key=api_key)

    indexed_rows = [{"row": idx, **r} for idx, r in enumerate(rows)]

    system_instruction = (
        "You are OptiMystic, an operations optimization assistant.\n"
        "CRITICAL: Your response MUST start immediately with `{`. "
        "Output ONLY a single JSON object — no text before or after it. "
        "NEVER write Role:, Input:, Self-Correction, bullet points, or any reasoning/planning text.\n"
        "CRITICAL: If dataset rows are empty/null, suggested_diffs must be [] and you must not invent sample values.\n"
        f"Dataset columns: {columns}. Domain: {domain}, solver: {solver}.\n"
        "JSON keys:\n"
        "  reply: short natural sentence in user's language (Korean→Korean, English→English). "
        "Talk like a knowledgeable colleague. No analysis narration.\n"
        "  recommended_domain: string\n"
        "  recommended_solver: string\n"
        "  reason: one short sentence\n"
        f"  suggested_diffs: list of {{\"row\": int (0–{len(rows)-1}), \"col\": string, \"value\": any}} or []\n"
        "If unsure about something, ask a single clarifying question in reply."
    )

    chat_history = []
    for msg in (history or []):
        role = "user" if msg.get("role") == "user" else "model"
        chat_history.append(
            google_types.Content(role=role, parts=[google_types.Part(text=msg["content"])])
        )

    config_kwargs: Dict[str, Any] = {
        "temperature": 0.3,
        "system_instruction": system_instruction,
        "response_mime_type": "application/json",
    }
    config = google_types.GenerateContentConfig(**config_kwargs)

    user_message = (
        f"Dataset rows: {json.dumps(indexed_rows, ensure_ascii=False)}\n\n"
        f"User: {message}"
    )

    chat = client.chats.create(model=CHAT_MODEL, config=config, history=chat_history)
    response = chat.send_message(user_message)

    # thinking 파트(내부 추론)는 응답에 포함하지 않음
    text_parts = []
    for cand in getattr(response, "candidates", []) or []:
        cand_content = getattr(cand, "content", None)
        cand_parts = getattr(cand_content, "parts", None) if cand_content is not None else None
        for p in cand_parts or []:
            if getattr(p, "thought", False):
                continue
            txt = getattr(p, "text", None)
            if txt:
                text_parts.append(str(txt))
    text = "\n".join(text_parts).strip()
    if not text:
        text = (response.text or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1].lstrip("json").strip() if len(parts) > 1 else text

    # 모델이 추론 텍스트를 앞에 쓰고 JSON을 나중에 출력하는 경우 처리
    parsed = _extract_json_from_text(text)
    if parsed is not None:
        return _normalize_suggested_diffs(parsed, rows)

    return {
        "reply": text if text else "Sorry, something went wrong processing the response.",
        "recommended_domain": domain,
        "recommended_solver": solver,
        "reason": "Failed to parse LLM response as JSON",
        "suggested_diffs": [],
    }


def _chat_heuristic(message: str, columns: List[str], domain: str, solver: str, error: str = "") -> Dict[str, Any]:
    if error:
        if "no longer available" in error.lower() or "not_found" in error.lower():
            reply = (
                f"[Model error]\n{error}\n\n"
                f"Try setting OPTIMYSTIC_CHAT_MODEL to '{DEFAULT_CHAT_MODEL}'."
            )
        else:
            reply = f"[API key error]\n{error}\n\nPlease check your Google AI Studio API key."
    else:
        reply = (
            f"[No API key — heuristic mode]\n"
            f"Columns: {', '.join(columns)}\n"
            f"Inferred domain: {domain} / solver: {solver}\n\n"
            f"Set GOOGLE_API_KEY to enable AI responses."
        )
    return {
        "reply": reply,
        "recommended_domain": domain,
        "recommended_solver": solver,
        "reason": "Heuristic (GOOGLE_API_KEY not set)",
        "suggested_diffs": [],
    }

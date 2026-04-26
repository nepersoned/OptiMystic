from __future__ import annotations

import io
import json
import os
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from python_solvers.api.solver_api import run_optimization
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

CHAT_MODEL = os.getenv("OPTIMYSTIC_CHAT_MODEL", "gemini-2.0-flash")


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
    if any(kw in joined for kw in ("vehicle", "route", "node", "depot", "pickup", "delivery", "latitude", "longitude")):
        return "vrp", "mip"
    if any(kw in joined for kw in ("shift", "worker", "employee", "schedule", "availability")):
        return "scheduling", "cp"
    if any(kw in joined for kw in ("length", "stock", "cut", "waste", "pattern")):
        return "cutting", "cg"
    if any(kw in joined for kw in ("weight", "value", "item", "capacity", "demand")):
        return "packing", "mip"
    return "generic", "nlp"


def _safe_num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


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
            return {
                "Name": str(row.get("customer_name") or row.get("name") or f"Node_{idx}"),
                "X": _safe_num(row.get("longitude") or row.get("lon") or row.get("X") or row.get("x")),
                "Y": _safe_num(row.get("latitude") or row.get("lat") or row.get("Y") or row.get("y")),
                "Demand": _safe_num(row.get("demand_kg") or row.get("demand") or row.get("Demand")),
                "ServiceTime": _safe_num(row.get("service_time_min") or row.get("service_time")),
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


def _build_chart_data(domain: str, result: Dict[str, Any]) -> Dict[str, Any]:
    if domain == "vrp":
        routes = result.get("routes", [])
        if not routes:
            return {}
        return {
            "route_bar": {
                "categories": [r.get("vehicle", f"차량_{i}") for i, r in enumerate(routes)],
                "series": [
                    {"name": "거리 (단위)", "data": [round(r.get("distance", 0), 1) for r in routes]},
                    {"name": "적재량 (kg)", "data": [round(r.get("load", 0), 1) for r in routes]},
                ],
            },
            "kpi": {
                "총_거리": round(result.get("total_distance", 0), 1),
                "운행_차량_수": result.get("num_vehicles", len(routes)),
                "미배송_건": len(result.get("unserved", [])),
                "총_적재_kg": round(result.get("total_load", 0), 1),
            },
        }
    return {}


def _build_executive_summary(domain: str, result: Dict[str, Any]) -> Dict[str, Any]:
    if domain == "vrp":
        unserved = result.get("unserved", [])
        total_dist = result.get("total_distance", 0)
        num_v = result.get("num_vehicles", 0)
        headline = f"VRP 최적화 완료: {num_v}개 차량 배차, 총 이동거리 {total_dist:.1f}"
        if unserved:
            headline += f" — 미배송 {len(unserved)}건 발생"
        return {
            "headline": headline,
            "delta_pct": None,
            "kpi_deltas": {},
            "bottleneck": (
                f"용량 부족으로 {len(unserved)}개 지점 미배송: {', '.join(str(u) for u in unserved[:3])}"
                if unserved else None
            ),
            "recommendation": (
                "차량 수를 늘리거나 최대 적재량을 높이면 미배송을 줄일 수 있습니다."
                if unserved else "모든 배송지가 할당되었습니다."
            ),
            "feasible_rate": 1.0,
            "run_count": 1,
        }
    return {
        "headline": f"{domain} 최적화 완료 (status: {result.get('status', '?')})",
        "delta_pct": None,
        "kpi_deltas": {},
        "feasible_rate": 1.0,
        "run_count": 1,
    }


# ── endpoints ───────────────────────────────────────────────────────────────

@router.get("")
def list_datasets_endpoint(request: Request) -> List[Dict[str, Any]]:
    _require_db()
    tenant_id = _get_tenant(request)
    return list_datasets(tenant_id=_scope_tenant(tenant_id))


@router.post("/upload")
async def upload_dataset(request: Request, file: UploadFile = File(...)) -> Dict[str, Any]:
    _require_db()
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
    dataset_id = create_dataset(
        name=name,
        filename=filename,
        tenant_id=_scope_tenant(tenant_id),
        rows=rows,
        columns=columns,
    )

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
    _require_db()
    _get_tenant(request)

    data = get_dataset_version(dataset_id, version) if version is not None else get_dataset_latest_version(dataset_id)
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
    _require_db()
    _get_tenant(request)

    data = get_dataset_latest_version(dataset_id)
    if data is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Dataset {dataset_id} not found"})

    rows = data["rows"]
    applied = 0
    for change in body.changes:
        if 0 <= change.row < len(rows):
            rows[change.row][change.col] = change.value
            applied += 1

    new_version = add_dataset_version(dataset_id, rows, data["columns"], note=body.note or "cell edit")
    return {"dataset_id": dataset_id, "version": new_version, "changes_applied": applied}


@router.get("/{dataset_id}/versions")
def list_versions(dataset_id: int, request: Request) -> List[Dict[str, Any]]:
    _require_db()
    _get_tenant(request)
    return list_dataset_versions(dataset_id)


@router.post("/{dataset_id}/versions/{version}/restore")
def restore_version(dataset_id: int, version: int, request: Request) -> Dict[str, Any]:
    _require_db()
    _get_tenant(request)

    data = get_dataset_version(dataset_id, version)
    if data is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Version {version} not found"})

    new_version = add_dataset_version(dataset_id, data["rows"], data["columns"], note=f"restored from v{version}")
    return {"dataset_id": dataset_id, "restored_from": version, "new_version": new_version}


class DatasetOptimizeRequest(BaseModel):
    domain: Optional[str] = None
    solver: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


@router.post("/{dataset_id}/optimize")
def optimize_dataset(dataset_id: int, body: DatasetOptimizeRequest, request: Request) -> Dict[str, Any]:
    _require_db()
    trace_id = str(getattr(request.state, "trace_id", "") or "")
    _get_tenant(request)

    data = get_dataset_latest_version(dataset_id)
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
    return {
        **result,
        "dataset_id": dataset_id,
        "domain_used": domain,
        "solver_used": solver,
        "chart_data": chart_data,
        "executive_summary": executive_summary,
    }


class ChatRequest(BaseModel):
    message: str
    version: Optional[int] = None


@router.post("/{dataset_id}/chat")
def chat_dataset(dataset_id: int, body: ChatRequest, request: Request) -> Dict[str, Any]:
    _require_db()
    _get_tenant(request)

    data = (
        get_dataset_version(dataset_id, body.version)
        if body.version is not None
        else get_dataset_latest_version(dataset_id)
    )
    if data is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Dataset {dataset_id} not found"})

    columns = data["columns"]
    rows = data["rows"]
    inferred_domain, inferred_solver = _infer_domain_solver(columns)

    api_key = os.getenv("GOOGLE_API_KEY", "")
    if api_key:
        try:
            return _chat_with_google(body.message, columns, rows, inferred_domain, inferred_solver, api_key)
        except Exception as e:
            return _chat_heuristic(body.message, columns, inferred_domain, inferred_solver, error=str(e))

    return _chat_heuristic(body.message, columns, inferred_domain, inferred_solver)


def _chat_with_google(
    message: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
    domain: str,
    solver: str,
    api_key: str,
) -> Dict[str, Any]:
    try:
        from google import genai as google_genai
        from google.genai import types as google_types
    except Exception as exc:
        raise RuntimeError("google-genai not available") from exc

    client = google_genai.Client(api_key=api_key)
    preview = rows[:5]
    prompt = (
        f"You are an optimization assistant. Analyze this dataset and respond.\n\n"
        f"Columns: {columns}\n"
        f"Row preview (up to 5): {json.dumps(preview, ensure_ascii=False)}\n"
        f"Inferred domain: {domain}, solver: {solver}\n\n"
        f"User: {message}\n\n"
        f"Reply in JSON with keys: reply (Korean ok), recommended_domain, recommended_solver, reason, "
        f"suggested_diffs (list of {{row, col, value}} or empty list). No markdown, raw JSON only."
    )

    config = google_types.GenerateContentConfig(temperature=0.1)
    response = client.models.generate_content(model=CHAT_MODEL, contents=prompt, config=config)

    text = ""
    for cand in getattr(response, "candidates", []) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", []) or []:
            txt = getattr(part, "text", None)
            if txt:
                text += txt

    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1].lstrip("json").strip() if len(parts) > 1 else text

    try:
        return json.loads(text)
    except Exception:
        return {
            "reply": text,
            "recommended_domain": domain,
            "recommended_solver": solver,
            "reason": "LLM 응답 파싱 실패",
            "suggested_diffs": [],
        }


def _chat_heuristic(message: str, columns: List[str], domain: str, solver: str, error: str = "") -> Dict[str, Any]:
    if error:
        reply = f"[AI 키 오류]\n{error}\n\nAIza로 시작하는 Google AI Studio 키를 사용하세요."
    else:
        reply = (
            f"[AI 키 미설정 — 휴리스틱 모드]\n"
            f"질문: {message}\n\n"
            f"컬럼: {', '.join(columns)}\n"
            f"추천 도메인: {domain} / 솔버: {solver}\n\n"
            f"GOOGLE_API_KEY를 환경변수에 설정하면 실제 AI 응답을 받을 수 있습니다."
        )
    return {
        "reply": reply,
        "recommended_domain": domain,
        "recommended_solver": solver,
        "reason": "컬럼 패턴 기반 휴리스틱 (GOOGLE_API_KEY 미설정)",
        "suggested_diffs": [],
    }

from __future__ import annotations

import io
import json
import os
import re
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
    return {}


def _build_executive_summary(domain: str, result: Dict[str, Any]) -> Dict[str, Any]:
    if domain == "vrp":
        unserved = result.get("unserved", [])
        routes = result.get("routes", []) or []
        total_dist = result.get("total_distance", 0)
        num_v_raw = result.get("num_vehicles", 0)
        try:
            num_v = int(num_v_raw or 0)
        except (TypeError, ValueError):
            num_v = 0
        if num_v <= 0 and routes:
            num_v = len(routes)

        if num_v > 0:
            headline = f"VRP solved: {num_v} vehicles dispatched, total distance {total_dist:.1f}"
        else:
            headline = f"VRP solved: total distance {total_dist:.1f}"
        if unserved:
            headline += f" — {len(unserved)} stop(s) unserved"
        return {
            "headline": headline,
            "delta_pct": None,
            "kpi_deltas": {},
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
    return {
        "headline": f"{domain} optimization complete (status: {result.get('status', '?')})",
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


def _parse_suggested_diffs_from_text(text: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    m = re.search(r'SUGGESTED_DIFFS:\s*(\[.*?\])', text, re.DOTALL)
    if not m:
        return []
    try:
        diffs = json.loads(m.group(1))
        return _normalize_suggested_diffs({"suggested_diffs": diffs}, rows)["suggested_diffs"]
    except Exception:
        return []


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
        history_ctx = ""
        if history:
            recent = history[-6:]
            history_ctx = "Recent conversation:\n" + "\n".join(
                f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
                for m in recent
            ) + "\n\n"

        enriched_query = (
            f"Dataset file: {temp_path}\n"
            f"Columns: {columns}\n"
            f"Domain: {domain}, Solver: {solver}, Rows: {len(rows)}\n\n"
            f"{history_ctx}"
            f"User: {message}\n\n"
            f"If you want to suggest specific cell edits, append at the very end of your response:\n"
            f"SUGGESTED_DIFFS:[{{\"row\":<int>,\"col\":\"<col_name>\",\"value\":<new_value>}},...]\n"
            f"Row indices are 0-based as they appear in the CSV."
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
        "You are OptiMystic, a friendly operations AI assistant. "
        "You help users understand and edit their optimization dataset through natural conversation. "
        f"The dataset has columns: {columns}. Domain: {domain}, solver: {solver}.\n\n"
        "Rules:\n"
        "- Respond ONLY in raw JSON (no markdown, no ```json). No other text outside the JSON.\n"
        "- JSON keys: reply, recommended_domain, recommended_solver, reason, suggested_diffs.\n"
        "- reply: short and natural. Match the language the user writes in (Korean → Korean, English → English). "
        "Talk like a helpful colleague — no analysis narration, no 'I am thinking...', no reasoning steps. Just say what you found or what you changed.\n"
        "- suggested_diffs: list of {row (zero-based integer), col (string), value}. Empty list if no changes.\n"
        f"- row index must come from the indexed rows provided (0 to {len(rows)-1}).\n"
        "- If unsure, ask a clarifying question in reply instead of guessing."
    )

    chat_history = []
    for msg in (history or []):
        role = "user" if msg.get("role") == "user" else "model"
        chat_history.append(
            google_types.Content(role=role, parts=[google_types.Part(text=msg["content"])])
        )

    config = google_types.GenerateContentConfig(
        temperature=0.3,
        system_instruction=system_instruction,
    )

    user_message = (
        f"Dataset rows: {json.dumps(indexed_rows, ensure_ascii=False)}\n\n"
        f"User: {message}"
    )

    chat = client.chats.create(model=CHAT_MODEL, config=config, history=chat_history)
    response = chat.send_message(user_message)

    text = (response.text or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1].lstrip("json").strip() if len(parts) > 1 else text

    try:
        parsed = json.loads(text)
        return _normalize_suggested_diffs(parsed, rows)
    except Exception:
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

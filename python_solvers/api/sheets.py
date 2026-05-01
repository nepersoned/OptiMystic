"""
/sheets/chat          — LLM chat with sheet context
/sheets/analyze       — fast Python/pandas analysis, no LLM
/sheets/optimize-routes — actual VRP solver (no LLM needed)
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re as _re
import urllib.parse
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sheets", tags=["sheets"])


def _get_model() -> str:
    try:
        from agent_core.config import DEFAULT_GOOGLE_MODEL
        return os.getenv("OPTIMYSTIC_CHAT_MODEL", DEFAULT_GOOGLE_MODEL)
    except Exception:
        return os.getenv("OPTIMYSTIC_CHAT_MODEL", "gemini-2.5-flash")


# ── Pydantic models ────────────────────────────────────────────────────────────

class SheetsRequest(BaseModel):
    headers: list[str] = []
    rows: list[list[Any]] = []
    sheet_name: str = "Sheet1"
    # new: backend reads sheet directly when token+id provided
    token: str | None = None
    spreadsheet_id: str | None = None


class SheetsChatRequest(SheetsRequest):
    message: str
    history: list[dict[str, str]] = []
    analysis: dict[str, Any] | None = None


class SheetsChatResponse(BaseModel):
    reply: str
    suggested_changes: list[dict[str, Any]] | None = None


class SheetsAnalysisResponse(BaseModel):
    sheet_name: str
    row_count: int
    col_count: int
    columns: list[dict[str, Any]]   # [{name, type, missing, sample_values}]
    missing_summary: list[str]       # human-readable bullets
    numeric_stats: dict[str, Any]    # {col: {min, max, mean}}
    summary_text: str                # compact text for LLM context


# ── Pure-Python analysis (no LLM) ─────────────────────────────────────────────

def _fetch_sheet_data(token: str, spreadsheet_id: str, sheet_name: str) -> tuple[list[str], list[list[Any]]]:
    import urllib.request
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
        f"/values/{urllib.parse.quote(sheet_name)}?majorDimension=ROWS"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    values = data.get("values", [])
    if not values:
        return [], []
    headers = [str(v) for v in values[0]]
    rows = values[1:]
    return headers, rows


def _analyze(headers: list[str], rows: list[list[Any]], sheet_name: str) -> dict[str, Any]:
    row_count = len(rows)
    col_count = len(headers)

    col_info: list[dict[str, Any]] = []
    missing_summary: list[str] = []
    numeric_stats: dict[str, Any] = {}

    for ci, h in enumerate(headers):
        values = [row[ci] if ci < len(row) else "" for row in rows]
        missing_idx = [ri for ri, v in enumerate(values) if v == "" or v is None]

        # detect numeric
        nums = []
        for v in values:
            if v == "" or v is None:
                continue
            try:
                nums.append(float(str(v).replace("kg", "").replace(",", "")))
            except Exception:
                pass

        is_numeric = len(nums) > len(values) * 0.5
        col_type = "numeric" if is_numeric else "text"

        sample = [str(v) for v in values[:3] if v != "" and v is not None]

        col_info.append({
            "name": h,
            "type": col_type,
            "missing": len(missing_idx),
            "missing_rows": missing_idx[:5],
            "sample_values": sample,
        })

        if missing_idx:
            row_ids = []
            id_col = 0  # use first column as row ID
            for ri in missing_idx[:3]:
                rid = rows[ri][id_col] if rows[ri] else ri + 2
                row_ids.append(str(rid))
            missing_summary.append(
                f"'{h}' 컬럼: {len(missing_idx)}개 결측 (예: {', '.join(row_ids)})"
            )

        if is_numeric and nums:
            numeric_stats[h] = {
                "min": round(min(nums), 2),
                "max": round(max(nums), 2),
                "mean": round(sum(nums) / len(nums), 2),
            }

    # build compact summary text for LLM
    lines = [
        f"Sheet '{sheet_name}': {row_count}행 × {col_count}열",
        "Columns: " + ", ".join(
            f"{c['name']}({'숫자' if c['type']=='numeric' else '텍스트'}"
            + (f", 결측{c['missing']}개" if c['missing'] else "") + ")"
            for c in col_info
        ),
    ]
    if missing_summary:
        lines.append("결측치: " + " | ".join(missing_summary))
    if numeric_stats:
        stats_parts = []
        for col, s in list(numeric_stats.items())[:4]:
            stats_parts.append(f"{col}(평균{s['mean']}, 범위{s['min']}~{s['max']})")
        lines.append("수치 통계: " + ", ".join(stats_parts))
    # full data for LLM (needed for optimization constraints)
    if rows:
        lines.append(f"\n전체 데이터 ({len(rows)}행):")
        lines.append(" | ".join(str(h) for h in headers))
        lines.append("-" * 40)
        for row in rows:
            lines.append(" | ".join(str(v) for v in row))

    return {
        "sheet_name": sheet_name,
        "row_count": row_count,
        "col_count": col_count,
        "columns": col_info,
        "missing_summary": missing_summary,
        "numeric_stats": numeric_stats,
        "summary_text": "\n".join(lines),
    }


def _resolve_sheet_data(req: SheetsRequest) -> tuple[list[str], list[list[Any]]]:
    if req.token and req.spreadsheet_id:
        try:
            return _fetch_sheet_data(req.token, req.spreadsheet_id, req.sheet_name)
        except Exception as e:
            logger.warning(f"Sheets API fetch failed, falling back to inline data: {e}")
    return req.headers, req.rows


@router.post("/analyze", response_model=SheetsAnalysisResponse)
async def sheets_analyze(req: SheetsRequest) -> SheetsAnalysisResponse:
    headers, rows = _resolve_sheet_data(req)
    result = _analyze(headers, rows, req.sheet_name)
    return SheetsAnalysisResponse(**result)


# ── VRP route optimization ────────────────────────────────────────────────────

def _parse_time_min(s: Any) -> int:
    s = str(s).strip()
    m = _re.match(r'^(\d{1,2}):(\d{2})', s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = _re.match(r'^(\d{1,2})시(\d{0,2})', s)
    if m:
        return int(m.group(1)) * 60 + (int(m.group(2)) if m.group(2) else 0)
    digits = _re.sub(r'[^\d]', '', s)
    if not digits:
        return 0
    v = int(digits)
    if v <= 24:
        return v * 60
    return (v // 100) * 60 + (v % 100)


def _parse_weight(s: Any) -> float:
    try:
        return float(str(s).replace('kg', '').replace(',', '').strip())
    except Exception:
        return 0.0


def _col(headers: list[str], *names: str) -> int:
    hl = [h.lower() for h in headers]
    for name in names:
        for i, h in enumerate(hl):
            if name in h:
                return i
    return -1


def _build_vrp_input(
    headers: list[str],
    rows: list[list[Any]],
    depot_lat: float = 37.5704,
    depot_lon: float = 126.9825,
    depot_name: str = "광화문(출발)",
) -> dict[str, Any]:
    name_c = _col(headers, '거래처명', 'name')
    lat_c  = _col(headers, '위도', 'lat')
    lon_c  = _col(headers, '경도', 'lon', 'lng')
    dem_c  = _col(headers, '배송중량', 'weight', 'demand')
    svc_c  = _col(headers, '작업시간', 'service')
    rdy_c  = _col(headers, '배송가능시작', 'ready', '가능시작')
    due_c  = _col(headers, '마감시간', 'due', '마감')

    def get(row: list, c: int, default: Any = "") -> Any:
        return row[c] if 0 <= c < len(row) else default

    nodes: list[dict[str, Any]] = [{
        "Name": depot_name, "X": depot_lon, "Y": depot_lat,
        "Demand": 0.0, "ServiceTime": 0, "ReadyTime": 0, "DueTime": 1440,
    }]
    for row in rows:
        try:
            lat = float(str(get(row, lat_c)).strip())
            lon = float(str(get(row, lon_c)).strip())
        except Exception:
            continue
        nodes.append({
            "Name": str(get(row, name_c, "Unknown")),
            "X": lon, "Y": lat,
            "Demand":      _parse_weight(get(row, dem_c)) if dem_c >= 0 else 0.0,
            "ServiceTime": _parse_time_min(get(row, svc_c)) if svc_c >= 0 else 15,
            "ReadyTime":   _parse_time_min(get(row, rdy_c)) if rdy_c >= 0 else 0,
            "DueTime":     _parse_time_min(get(row, due_c)) if due_c >= 0 else 1440,
        })

    vehicles = (
        [{"Name": f"트럭{i+1}", "Capacity": 2000.0, "StartIndex": 0, "EndIndex": 0} for i in range(3)]
        + [{"Name": f"van{i+1}",  "Capacity": 300.0,  "StartIndex": 0, "EndIndex": 0} for i in range(5)]
    )
    return {"Nodes": nodes, "Vehicles": vehicles, "Depot": 0,
            "TimeLimit": 20, "AllowDropping": True, "DropPenalty": 100000}


class SheetsOptimizeResponse(BaseModel):
    status: str
    report: str
    total_distance_km: float | None = None
    num_vehicles_used: int | None = None
    routes: list[dict[str, Any]] = []
    unserved: list[str] = []
    result_headers: list[str] = []
    result_rows: list[list[Any]] = []


@router.post("/optimize-routes", response_model=SheetsOptimizeResponse)
async def sheets_optimize_routes(req: SheetsRequest) -> SheetsOptimizeResponse:
    from python_solvers.api.solver_api import run_optimization

    headers, rows = req.headers, req.rows
    params = _build_vrp_input(headers, rows)
    if len(params["Nodes"]) < 2:
        return SheetsOptimizeResponse(status="error", report="좌표 있는 배송지가 부족합니다.")

    try:
        result = await asyncio.to_thread(run_optimization, "vrp", "vrp", params)
    except Exception as exc:
        logger.exception("VRP solver failed")
        return SheetsOptimizeResponse(status="error", report=f"솔버 오류: {exc}")

    if result.get("error_msg"):
        return SheetsOptimizeResponse(status="error", report=result["error_msg"])

    details = result.get("details") or {}
    if hasattr(details, "model_dump"):
        details = details.model_dump()

    routes_raw = details.get("routes") or result.get("routes") or []
    unserved   = details.get("unserved") or result.get("unserved") or []
    total_dist = details.get("total_distance") or result.get("total_distance")
    report_txt = details.get("report") or result.get("report") or ""

    result_headers = ["차량", "순서", "거래처명", "도착(분)", "출발(분)"]
    result_rows: list[list[Any]] = []
    routes_out: list[dict[str, Any]] = []

    for r in (routes_raw if isinstance(routes_raw, list) else []):
        if hasattr(r, "model_dump"):
            r = r.model_dump()
        if not isinstance(r, dict):
            continue
        vehicle = r.get("vehicle_name") or r.get("vehicle") or ""
        stops = r.get("stops") or r.get("nodes") or []
        stop_names: list[str] = []
        seq = 1
        for s in stops:
            if hasattr(s, "model_dump"):
                s = s.model_dump()
            if not isinstance(s, dict):
                continue
            name = s.get("name") or s.get("node") or ""
            arr  = s.get("arrival", "")
            dep  = s.get("departure", "")
            stop_names.append(name)
            result_rows.append([vehicle, seq, name, arr, dep])
            seq += 1
        routes_out.append({"vehicle": vehicle, "stops": stop_names})

    if not report_txt:
        report_txt = f"최적화 완료: {len(routes_out)}대 운행, 총 거리 {total_dist or 'N/A'} km"

    return SheetsOptimizeResponse(
        status=result.get("status", "ok"),
        report=report_txt,
        total_distance_km=total_dist,
        num_vehicles_used=len(routes_out),
        routes=routes_out,
        unserved=list(unserved) if isinstance(unserved, list) else [],
        result_headers=result_headers,
        result_rows=result_rows,
    )


# ── LLM chat (uses analysis summary, not raw rows) ────────────────────────────

def _build_system_prompt(summary_text: str) -> str:
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    return (
        f"Today's date is {today}.\n"
        "You are OptiMystic, an AI operations consultant embedded in Google Sheets.\n"
        "The sheet analysis below was computed by a Python data engine (accurate).\n\n"
        "## SHEET ANALYSIS\n"
        f"{summary_text}\n\n"
        "## CAPABILITIES (tell users about these when asked)\n"
        "- 결측치 찾기 & 셀 직접 수정 (✓ 적용 버튼으로 시트에 반영)\n"
        "- 배송 경로 최적화: 사용자가 '최적화 돌려' 또는 '경로 최적화해줘' 입력 시 "
        "실제 VRP 솔버가 자동으로 실행됨 (광화문 출발 기본값, 시간창·중량 제약 반영)\n"
        "- 데이터 분석: 통계, 이상값, 패턴 분석\n"
        "- 결과 시트 자동 생성\n\n"
        "## BEHAVIOR\n"
        "- Answer conversationally. Be concise.\n"
        "- Trust the analysis above — it was computed exactly, not inferred.\n"
        "- IMPORTANT: Whenever the user asks you to fill, fix, update, or change cell values, "
        "you MUST output the actual changes as a JSON block so the user can apply them with one click. "
        "Do NOT just describe what to do — output the block.\n"
        "- Changes block format (append at the end of your reply):\n"
        "```changes\n"
        '[{"row": 0, "col": 0, "value": "new_value"}, ...]\n'
        "```\n"
        "  row/col are 0-indexed (row 0 = first data row below header, col 0 = first column).\n"
        "- For route optimization requests, tell the user the VRP solver is running automatically.\n"
        "- Match the user's language (Korean → Korean, English → English).\n"
        "- Never fabricate data not in the analysis."
    )


def _find_changes_block(text: str) -> tuple[int, int, int] | None:
    """Return (block_start, content_start, content_end) for the first changes/json block containing a list."""
    for marker in ("```changes", "```json"):
        pos = 0
        while True:
            start = text.find(marker, pos)
            if start == -1:
                break
            content_start = start + len(marker)
            end = text.find("```", content_start)
            if end == -1:
                break
            raw = text[content_start:end].strip()
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                    return (start, content_start, end)
            except Exception:
                pass
            pos = end + 3
    return None


def _parse_changes(text: str) -> list[dict[str, Any]] | None:
    found = _find_changes_block(text)
    if not found:
        return None
    _, content_start, end = found
    raw = text[content_start:end].strip()
    try:
        changes = json.loads(raw)
        if isinstance(changes, list):
            return changes
    except Exception:
        pass
    return None


def _strip_changes_block(text: str) -> str:
    found = _find_changes_block(text)
    if not found:
        return text
    block_start, _, end = found
    return (text[:block_start] + text[end + 3:]).strip()


@router.post("/chat", response_model=SheetsChatResponse)
async def sheets_chat(req: SheetsChatRequest) -> SheetsChatResponse:
    try:
        from agent_core.providers import chat_google
    except ImportError:
        return SheetsChatResponse(reply="agent_core not available on this server.")

    # use pre-computed analysis if provided, else fetch + compute
    if req.analysis and req.analysis.get("summary_text"):
        summary_text = req.analysis["summary_text"]
    else:
        headers, rows = _resolve_sheet_data(req)
        analysis = _analyze(headers, rows, req.sheet_name)
        summary_text = analysis["summary_text"]

    system_prompt = _build_system_prompt(summary_text)

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for h in req.history[-12:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": req.message})

    try:
        res = await chat_google(model=_get_model(), messages=messages, tools=[])
        raw_reply = (res.get("message") or {}).get("content") or ""
    except Exception as exc:
        logger.exception("Gemini call failed in sheets_chat")
        return SheetsChatResponse(reply=f"Error: {exc}")

    changes = _parse_changes(raw_reply)
    clean_reply = _strip_changes_block(raw_reply)
    return SheetsChatResponse(reply=clean_reply, suggested_changes=changes)

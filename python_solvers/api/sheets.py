"""
/sheets/chat  — LLM chat with sheet context (summary only, not raw rows)
/sheets/analyze — fast Python/pandas analysis, no LLM
"""
from __future__ import annotations

import json
import logging
import os
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
        "## BEHAVIOR\n"
        "- Answer conversationally. Be concise.\n"
        "- Trust the analysis above — it was computed exactly, not inferred.\n"
        "- If asked to suggest cell edits, output a JSON block at the end:\n"
        "```changes\n"
        '[{"row": 0, "col": 0, "value": "new_value"}, ...]\n'
        "```\n"
        "  row/col are 0-indexed (row 0 = first data row, not header).\n"
        "- Match the user's language (Korean → Korean, English → English).\n"
        "- Never fabricate data not in the analysis."
    )


def _parse_changes(text: str) -> list[dict[str, Any]] | None:
    start = text.find("```changes")
    if start == -1:
        return None
    end = text.find("```", start + 10)
    if end == -1:
        return None
    raw = text[start + 10:end].strip()
    try:
        changes = json.loads(raw)
        if isinstance(changes, list):
            return changes
    except Exception:
        pass
    return None


def _strip_changes_block(text: str) -> str:
    start = text.find("```changes")
    if start == -1:
        return text
    end = text.find("```", start + 10)
    if end == -1:
        return text
    return (text[:start] + text[end + 3:]).strip()


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

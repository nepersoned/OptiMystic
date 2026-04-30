"""
/sheets/chat — Google Sheets add-on chat endpoint.
Accepts inline sheet data so no file upload is needed.
"""
from __future__ import annotations

import json
import logging
import os
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
_MAX_ROWS_CONTEXT = 30


class SheetsChatRequest(BaseModel):
    message: str
    headers: list[str] = []
    rows: list[list[Any]] = []
    sheet_name: str = "Sheet1"
    history: list[dict[str, str]] = []


class SheetsChatResponse(BaseModel):
    reply: str
    suggested_changes: list[dict[str, Any]] | None = None


def _sheet_to_context(headers: list[str], rows: list[list[Any]], sheet_name: str) -> str:
    if not headers and not rows:
        return "(empty sheet)"
    lines = [f"Sheet: {sheet_name}"]
    if headers:
        lines.append("Columns: " + ", ".join(str(h) for h in headers))
    lines.append(f"Rows: {len(rows)}")
    lines.append("")
    sample = rows[:_MAX_ROWS_CONTEXT]
    if headers:
        lines.append(" | ".join(str(h) for h in headers))
        lines.append("-" * 40)
    for row in sample:
        lines.append(" | ".join(str(v) for v in row))
    if len(rows) > _MAX_ROWS_CONTEXT:
        lines.append(f"... ({len(rows) - _MAX_ROWS_CONTEXT} more rows)")
    return "\n".join(lines)


def _build_system_prompt(sheet_context: str) -> str:
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    return (
        f"Today's date is {today}.\n"
        "You are OptiMystic, an AI operations consultant embedded in Google Sheets.\n"
        "The user's current sheet data is shown below. Use it to answer questions, "
        "suggest improvements, and run optimizations when asked.\n\n"
        "## CURRENT SHEET\n"
        f"{sheet_context}\n\n"
        "## BEHAVIOR\n"
        "- Answer conversationally. Be concise.\n"
        "- If the user asks to optimize, analyze or improve the data, "
        "suggest specific cell changes in this exact JSON block at the end of your reply:\n"
        "```changes\n"
        '[{"row": 1, "col": 0, "value": "new_value"}, ...]\n'
        "```\n"
        "  row/col are 0-indexed (row 0 = first data row, not header).\n"
        "- Match the user's language (Korean → Korean, English → English).\n"
        "- Never fabricate data that isn't in the sheet."
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

    sheet_context = _sheet_to_context(req.headers, req.rows, req.sheet_name)
    system_prompt = _build_system_prompt(sheet_context)

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

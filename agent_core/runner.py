import asyncio
import json
from typing import Any, Dict, List

from python_solvers.mcp_server import mcp

from .config import CHAT_TIMEOUT_SEC, DEFAULT_FALLBACK_MODEL, DEFAULT_LLM_PROVIDER, DEFAULT_MODEL, MAX_STEPS, build_system_prompt
from .helpers import (
    infer_mapping_rule,
    is_retryable_error,
    normalize_args_for_tool,
    normalize_tool_args,
    normalize_tool_calls,
    summarize_tool_result,
    to_jsonable,
    trim_messages,
)
from .providers import chat_with_provider


async def get_tools() -> List[Dict[str, Any]]:
    tools = await mcp._tool_manager.get_tools()
    out: List[Dict[str, Any]] = []
    for tool in tools.values():
        out.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.parameters or {"type": "object", "properties": {}},
                },
            }
        )
    return out


async def dispatch_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    safe_args = args if isinstance(args, dict) else {}
    tool_result = await mcp._tool_manager.call_tool(name, safe_args)
    return tool_result.structured_content if hasattr(tool_result, "structured_content") else {}


async def run_agent_loop(
    user_query: str,
    model: str = DEFAULT_MODEL,
    fallback_model: str = DEFAULT_FALLBACK_MODEL,
    llm_provider: str = DEFAULT_LLM_PROVIDER,
    max_steps: int = MAX_STEPS,
    chat_timeout_sec: int = CHAT_TIMEOUT_SEC,
) -> Dict[str, Any]:
    tools = await get_tools()
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_query},
    ]
    trace: List[Dict[str, Any]] = []
    last_columns: List[str] = []
    last_file_path: str = ""

    for step in range(1, max_steps + 1):
        active_model = model
        try:
            llm_res = await asyncio.wait_for(
                chat_with_provider(provider=llm_provider, model=active_model, messages=messages, tools=tools),
                timeout=chat_timeout_sec,
            )
        except Exception as primary_exc:
            if fallback_model and fallback_model != model:
                active_model = fallback_model
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            f"Primary model call failed ({type(primary_exc).__name__}). "
                            f"Switching to fallback model: {fallback_model}."
                        ),
                    }
                )
                messages = trim_messages(messages)
                llm_res = await asyncio.wait_for(
                    chat_with_provider(provider=llm_provider, model=active_model, messages=messages, tools=tools),
                    timeout=chat_timeout_sec,
                )
            else:
                return {
                    "ok": False,
                    "error": {
                        "code": "llm_call_failed",
                        "message": str(primary_exc) or f"{type(primary_exc).__name__}: (empty message)",
                    },
                    "trace": trace,
                    "messages": to_jsonable(messages),
                }

        message = llm_res.get("message") or {}
        content = (message.get("content") or "").strip()
        tool_calls = normalize_tool_calls(message.get("tool_calls") or [])

        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)
        messages = trim_messages(messages)

        if not tool_calls:
            return {
                "ok": True,
                "step": step,
                "final": content,
                "trace": trace,
                "messages": messages,
            }

        for tc in tool_calls:
            tool_call_id = tc.get("id")
            fn = tc.get("function") or {}
            tool_name = str(fn.get("name", "")).strip()
            args = normalize_tool_args(fn.get("arguments"))
            args = normalize_args_for_tool(tool_name, args)

            if tool_name == "map_to_target_schema":
                if not args.get("file_path") and last_file_path:
                    args["file_path"] = last_file_path
                mapping_rule = args.get("mapping_rule")
                mapping_rule_invalid = (
                    not isinstance(mapping_rule, dict)
                    or not mapping_rule
                    or not all(isinstance(v, str) for v in mapping_rule.values())
                )
                if mapping_rule_invalid:
                    inferred = infer_mapping_rule(str(args.get("domain", "")), last_columns)
                    if inferred:
                        args["mapping_rule"] = inferred
                        messages.append(
                            {
                                "role": "system",
                                "content": (
                                    "Auto-filled mapping_rule from observed columns. "
                                    f"mapping_rule={json.dumps(inferred, ensure_ascii=False)}"
                                ),
                            }
                        )

            try:
                result = await dispatch_tool(tool_name, args)
            except Exception as exc:
                result = {
                    "ok": False,
                    "error": {
                        "code": "tool_execution_error",
                        "message": str(exc),
                    },
                }

            trace.append(
                {
                    "step": step,
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                }
            )

            summarized = summarize_tool_result(tool_name, result)
            tool_text = json.dumps(summarized, ensure_ascii=False)
            messages.append(
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": tool_text,
                    **({"tool_call_id": str(tool_call_id)} if tool_call_id else {}),
                }
            )
            messages = trim_messages(messages)

            if tool_name == "read_company_data" and result.get("ok"):
                raw_cols = result.get("columns") or []
                last_columns = [str(c) for c in raw_cols if str(c).strip()]
                last_file_path = str(result.get("file_path") or "").strip()

            if is_retryable_error(result):
                hint = ((result.get("error") or {}).get("retry_hint") or (result.get("error") or {}).get("message") or "").strip()
                if hint:
                    messages.append(
                        {
                            "role": "system",
                            "content": (
                                "Tool returned retryable error. Update mapping/constraints and re-run required tools. "
                                f"Hint: {hint}"
                            ),
                        }
                    )
                    messages = trim_messages(messages)

            if tool_name == "optimize" and result.get("ok"):
                status = str((result.get("result") or {}).get("status", "")).lower()
                if status == "optimal":
                    return {
                        "ok": True,
                        "step": step,
                        "final": "Optimization completed.",
                        "optimization": result,
                        "trace": trace,
                        "messages": to_jsonable(messages),
                    }

    return {
        "ok": False,
        "error": {
            "code": "max_steps_exceeded",
            "message": f"Agent did not finish within {max_steps} steps.",
        },
        "trace": trace,
        "messages": to_jsonable(messages),
    }

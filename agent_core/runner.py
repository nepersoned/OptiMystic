import asyncio
import json
import logging
from typing import Any, Dict, List

from python_solvers.mcp_server import mcp

from .config import (
    CHAT_TIMEOUT_SEC,
    COMPLETION_USD_PER_1M,
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_MODEL,
    MAX_ESTIMATED_COST_USD,
    MAX_STEPS,
    PROMPT_USD_PER_1M,
    build_system_prompt,
)
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


logger = logging.getLogger(__name__)


def _estimate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    prompt_cost = (float(prompt_tokens) / 1_000_000.0) * PROMPT_USD_PER_1M
    completion_cost = (float(completion_tokens) / 1_000_000.0) * COMPLETION_USD_PER_1M
    return round(prompt_cost + completion_cost, 8)


async def get_tools() -> List[Dict[str, Any]]:
    manager = getattr(mcp, "_tool_manager", None)
    if manager is None or not hasattr(manager, "get_tools"):
        raise RuntimeError("FastMCP tool manager is unavailable. Check FastMCP compatibility.")

    tools = await manager.get_tools()
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
    manager = getattr(mcp, "_tool_manager", None)
    if manager is None or not hasattr(manager, "call_tool"):
        raise RuntimeError("FastMCP tool manager is unavailable. Check FastMCP compatibility.")

    tool_result = await manager.call_tool(name, safe_args)
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
    usage_totals: Dict[str, int] = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }

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
        usage = llm_res.get("usage") if isinstance(llm_res.get("usage"), dict) else None
        if usage is not None:
            usage_totals["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
            usage_totals["completion_tokens"] += int(usage.get("completion_tokens") or 0)
            usage_totals["total_tokens"] += int(usage.get("total_tokens") or 0)
            logger.info(
                "LLM usage captured",
                extra={
                    "step": step,
                    "provider": llm_provider,
                    "model": active_model,
                    "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                    "completion_tokens": int(usage.get("completion_tokens") or 0),
                    "total_tokens": int(usage.get("total_tokens") or 0),
                },
            )

        estimated_cost_usd = _estimate_cost_usd(
            usage_totals["prompt_tokens"],
            usage_totals["completion_tokens"],
        )

        if MAX_ESTIMATED_COST_USD > 0 and estimated_cost_usd > MAX_ESTIMATED_COST_USD:
            logger.warning(
                "Estimated LLM budget exceeded",
                extra={
                    "provider": llm_provider,
                    "model": active_model,
                    "estimated_cost_usd": estimated_cost_usd,
                    "budget_usd": MAX_ESTIMATED_COST_USD,
                },
            )
            return {
                "ok": False,
                "error": {
                    "code": "llm_budget_exceeded",
                    "message": (
                        "Estimated LLM cost exceeded configured budget. "
                        f"estimated_cost_usd={estimated_cost_usd}, budget_usd={MAX_ESTIMATED_COST_USD}"
                    ),
                },
                "trace": trace,
                "messages": to_jsonable(messages),
                "usage": {
                    **usage_totals,
                    "estimated_cost_usd": estimated_cost_usd,
                    "prompt_usd_per_1m": PROMPT_USD_PER_1M,
                    "completion_usd_per_1m": COMPLETION_USD_PER_1M,
                },
            }

        trace.append(
            {
                "step": step,
                "llm": {
                    "provider": llm_provider,
                    "model": active_model,
                    "usage": usage,
                    "estimated_cost_usd": estimated_cost_usd,
                },
            }
        )

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
                "usage": {
                    **usage_totals,
                    "estimated_cost_usd": _estimate_cost_usd(
                        usage_totals["prompt_tokens"],
                        usage_totals["completion_tokens"],
                    ),
                    "prompt_usd_per_1m": PROMPT_USD_PER_1M,
                    "completion_usd_per_1m": COMPLETION_USD_PER_1M,
                },
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
                        "usage": {
                            **usage_totals,
                            "estimated_cost_usd": _estimate_cost_usd(
                                usage_totals["prompt_tokens"],
                                usage_totals["completion_tokens"],
                            ),
                            "prompt_usd_per_1m": PROMPT_USD_PER_1M,
                            "completion_usd_per_1m": COMPLETION_USD_PER_1M,
                        },
                    }

    return {
        "ok": False,
        "error": {
            "code": "max_steps_exceeded",
            "message": f"Agent did not finish within {max_steps} steps.",
        },
        "trace": trace,
        "messages": to_jsonable(messages),
        "usage": {
            **usage_totals,
            "estimated_cost_usd": _estimate_cost_usd(
                usage_totals["prompt_tokens"],
                usage_totals["completion_tokens"],
            ),
            "prompt_usd_per_1m": PROMPT_USD_PER_1M,
            "completion_usd_per_1m": COMPLETION_USD_PER_1M,
        },
    }

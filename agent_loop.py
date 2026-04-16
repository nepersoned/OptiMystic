import argparse
import asyncio
import json
import os
import re
from typing import Any, Dict, List

import ollama

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    from google import genai as google_genai
    from google.genai import types as google_types
except Exception:
    google_genai = None
    google_types = None

from python_solvers.mcp_server import mcp


DEFAULT_MODEL = "gemma4:e2b"
DEFAULT_FALLBACK_MODEL = "gemma4:e2b"
DEFAULT_LLM_PROVIDER = "ollama"
DEFAULT_GOOGLE_MODEL = "gemma-4-26b-a4b-it"
MAX_STEPS = 4
CHAT_TIMEOUT_SEC = 45
MAX_CONTEXT_MESSAGES = 24


def build_system_prompt() -> str:
    return (
        "You are OptiMystic AI COO. Your job is to maximize business operations efficiency with tool-first reasoning.\n"
        "Rules:\n"
        "1) If user mentions a file or asks data status, call read_company_data first.\n"
        "2) If source columns differ from target contract, call get_target_schema then map_to_target_schema.\n"
        "3) After valid payload exists, call optimize.\n"
        "4) If tool returns validation_error/optimization_infeasible/optimization_unbounded, self-correct and try again.\n"
        "5) Keep answers concise and execution-focused.\n"
        "6) Never fabricate tool outputs; rely only on tool observations."
    )


def _extract_error_code(result: Dict[str, Any]) -> str:
    error = result.get("error") or {}
    return str(error.get("code", "")).strip().lower()


def _is_retryable_error(result: Dict[str, Any]) -> bool:
    code = _extract_error_code(result)
    return code in {"validation_error", "invalid_mapping_rule", "optimization_infeasible", "optimization_unbounded"}


def _norm_col(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]", "", str(text or "")).lower()


def _infer_mapping_rule(domain: str, columns: List[str]) -> Dict[str, str]:
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


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return _to_jsonable(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            return _to_jsonable(value.dict())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return _to_jsonable(vars(value))
        except Exception:
            pass
    return str(value)


async def get_ollama_tools() -> List[Dict[str, Any]]:
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


async def _chat(model: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    return await _chat_ollama(model=model, messages=messages, tools=tools)


async def _chat_ollama(model: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    return await asyncio.to_thread(
        ollama.chat,
        model=model,
        messages=messages,
        tools=tools,
        options={"temperature": 0.1},
    )


def _build_openai_client() -> Any:
    if OpenAI is None:
        raise RuntimeError("openai package is not installed. Install with: pip install openai")

    base_url = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1")
    api_key = os.getenv("OPENAI_API_KEY", "EMPTY")
    return OpenAI(base_url=base_url, api_key=api_key)


def _normalize_openai_tool_calls(raw_tool_calls: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not raw_tool_calls:
        return out

    for tc in raw_tool_calls:
        fn = getattr(tc, "function", None)
        name = getattr(fn, "name", "") if fn else ""
        arguments = getattr(fn, "arguments", "{}") if fn else "{}"
        out.append(
            {
                "type": "function",
                "function": {
                    "name": str(name),
                    "arguments": arguments if isinstance(arguments, str) else json.dumps(_to_jsonable(arguments), ensure_ascii=False),
                },
            }
        )
    return out


def _chat_openai_sync(model: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    client = _build_openai_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        temperature=0.1,
    )

    choice = response.choices[0]
    msg = choice.message
    tool_calls = _normalize_openai_tool_calls(getattr(msg, "tool_calls", None))
    return {
        "message": {
            "content": getattr(msg, "content", "") or "",
            "tool_calls": tool_calls,
        }
    }


async def _chat_openai(model: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    return await asyncio.to_thread(
        _chat_openai_sync,
        model,
        messages,
        tools,
    )


def _build_google_client() -> Any:
    if google_genai is None:
        raise RuntimeError("google-genai package is not installed. Run: pip install google-genai")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY environment variable is not set.")
    return google_genai.Client(api_key=api_key)


def _convert_tools_to_google(tools: List[Dict[str, Any]]) -> Any:
    """Convert OpenAI-style tools list to a google.genai Tool object."""
    if google_types is None:
        return None
    fn_decls: List[Dict[str, Any]] = []
    for t in tools:
        fn = t.get("function") or {}
        fn_decls.append({
            "name": fn.get("name", ""),
            "description": fn.get("description", ""),
            "parameters": fn.get("parameters") or {"type": "object", "properties": {}},
        })
    return google_types.Tool(function_declarations=fn_decls)


def _convert_messages_to_google(messages: List[Dict[str, Any]]) -> tuple:
    """Convert OpenAI-style messages to (system_instruction_str, contents_list)."""
    if google_types is None:
        return None, []
    system_parts: List[str] = []
    contents: List[Any] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content") or ""
        if role == "system":
            if content:
                system_parts.append(content)
        elif role == "user":
            if content:
                contents.append(google_types.Content(role="user", parts=[google_types.Part(text=content)]))
        elif role == "assistant":
            tool_calls = msg.get("tool_calls") or []
            parts: List[Any] = []
            if content:
                parts.append(google_types.Part(text=content))
            for tc in tool_calls:
                fn = tc.get("function") or {}
                name = fn.get("name", "")
                arguments = fn.get("arguments", "{}")
                if isinstance(arguments, str):
                    try:
                        args: Dict[str, Any] = json.loads(arguments)
                    except Exception:
                        args = {}
                else:
                    args = arguments if isinstance(arguments, dict) else {}
                parts.append(google_types.Part(
                    function_call=google_types.FunctionCall(name=name, args=args)
                ))
            if parts:
                contents.append(google_types.Content(role="model", parts=parts))
        elif role == "tool":
            name = msg.get("name", "")
            try:
                result: Any = json.loads(content) if isinstance(content, str) else content
            except Exception:
                result = {"content": content}
            contents.append(google_types.Content(
                role="user",
                parts=[google_types.Part(
                    function_response=google_types.FunctionResponse(
                        name=name,
                        response=result if isinstance(result, dict) else {"content": str(result)},
                    )
                )],
            ))
    system_instruction = "\n\n".join(system_parts) if system_parts else None
    return system_instruction, contents


def _chat_google_sync(model: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    client = _build_google_client()
    google_tool = _convert_tools_to_google(tools)
    system_instruction, contents = _convert_messages_to_google(messages)
    config_kwargs: Dict[str, Any] = {
        "temperature": 0.1,
    }
    if google_tool:
        config_kwargs["tools"] = [google_tool]
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    config = google_types.GenerateContentConfig(**config_kwargs)
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    tool_calls: List[Dict[str, Any]] = []
    if response.function_calls:
        for fc in response.function_calls:
            tool_calls.append({
                "type": "function",
                "function": {
                    "name": str(fc.name),
                    "arguments": json.dumps(_to_jsonable(dict(fc.args) if fc.args else {}), ensure_ascii=False),
                },
            })
    text_content = ""
    try:
        text_content = response.text or ""
    except Exception:
        pass
    return {
        "message": {
            "content": text_content,
            "tool_calls": tool_calls,
        }
    }


async def _chat_google(model: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    return await asyncio.to_thread(_chat_google_sync, model, messages, tools)


async def _chat_with_provider(
    provider: str,
    model: str,
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
) -> Dict[str, Any]:
    provider_key = (provider or "").strip().lower()
    if provider_key == "openai":
        return await _chat_openai(model=model, messages=messages, tools=tools)
    if provider_key == "google":
        return await _chat_google(model=model, messages=messages, tools=tools)
    return await _chat_ollama(model=model, messages=messages, tools=tools)


def _summarize_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    properties = schema.get("properties") if isinstance(schema, dict) else {}
    required = schema.get("required") if isinstance(schema, dict) else []
    defs = schema.get("$defs") if isinstance(schema, dict) else {}
    return {
        "top_level_fields": sorted(list((properties or {}).keys())),
        "required": required if isinstance(required, list) else [],
        "defs": sorted(list((defs or {}).keys())),
    }


def _summarize_tool_result(tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
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
            "schema_summary": _summarize_schema(result.get("schema") or {}),
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


def _trim_messages(messages: List[Dict[str, Any]], max_messages: int = MAX_CONTEXT_MESSAGES) -> List[Dict[str, Any]]:
    if len(messages) <= max_messages:
        return messages
    head = messages[:1]
    tail = messages[-(max_messages - 1) :]
    return head + tail


def _normalize_tool_args(raw_args: Any) -> Dict[str, Any]:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _normalize_tool_calls(raw_tool_calls: Any) -> List[Dict[str, Any]]:
    normalized = _to_jsonable(raw_tool_calls)
    if not isinstance(normalized, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in normalized:
        if isinstance(item, dict):
            out.append(item)
    return out


async def run_agent_loop(
    user_query: str,
    model: str = DEFAULT_MODEL,
    fallback_model: str = DEFAULT_FALLBACK_MODEL,
    llm_provider: str = DEFAULT_LLM_PROVIDER,
    max_steps: int = MAX_STEPS,
    chat_timeout_sec: int = CHAT_TIMEOUT_SEC,
) -> Dict[str, Any]:
    tools = await get_ollama_tools()
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
                _chat_with_provider(provider=llm_provider, model=active_model, messages=messages, tools=tools),
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
                messages = _trim_messages(messages)
                llm_res = await asyncio.wait_for(
                    _chat_with_provider(provider=llm_provider, model=active_model, messages=messages, tools=tools),
                    timeout=chat_timeout_sec,
                )
            else:
                return {
                    "ok": False,
                    "error": {
                        "code": "llm_call_failed",
                        "message": str(primary_exc),
                    },
                    "trace": trace,
                    "messages": _to_jsonable(messages),
                }
        message = llm_res.get("message") or {}
        content = (message.get("content") or "").strip()
        tool_calls = _normalize_tool_calls(message.get("tool_calls") or [])

        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)
        messages = _trim_messages(messages)

        if not tool_calls:
            return {
                "ok": True,
                "step": step,
                "final": content,
                "trace": trace,
                "messages": messages,
            }

        for tc in tool_calls:
            fn = tc.get("function") or {}
            tool_name = str(fn.get("name", "")).strip()
            args = _normalize_tool_args(fn.get("arguments"))

            if tool_name == "map_to_target_schema":
                if not args.get("file_path") and last_file_path:
                    args["file_path"] = last_file_path
                mapping_rule = args.get("mapping_rule")
                if not isinstance(mapping_rule, dict) or not mapping_rule:
                    inferred = _infer_mapping_rule(str(args.get("domain", "")), last_columns)
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

            summarized = _summarize_tool_result(tool_name, result)
            tool_text = json.dumps(summarized, ensure_ascii=False)
            messages.append(
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": tool_text,
                }
            )
            messages = _trim_messages(messages)

            if tool_name == "read_company_data" and result.get("ok"):
                raw_cols = result.get("columns") or []
                last_columns = [str(c) for c in raw_cols if str(c).strip()]
                last_file_path = str(result.get("file_path") or "").strip()

            # Feed retry guidance back to LLM as explicit planner hint.
            if _is_retryable_error(result):
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
                    messages = _trim_messages(messages)

            if tool_name == "optimize" and result.get("ok"):
                status = str((result.get("result") or {}).get("status", "")).lower()
                if status == "optimal":
                    return {
                        "ok": True,
                        "step": step,
                        "final": "Optimization completed.",
                        "optimization": result,
                        "trace": trace,
                        "messages": _to_jsonable(messages),
                    }

    return {
        "ok": False,
        "error": {
            "code": "max_steps_exceeded",
            "message": f"Agent did not finish within {max_steps} steps.",
        },
        "trace": trace,
        "messages": _to_jsonable(messages),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OptiMystic Phase 3 orchestration loop")
    parser.add_argument(
        "--query",
        default="examples/sample.csv를 먼저 읽고 packing 도메인으로 가능한 최적화까지 진행해줘.",
        help="User request for the agent loop",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Model name (Ollama: 'gemma4:e2b', Google: 'gemma-4-26b-a4b-it', OpenAI-compat: any)",
    )
    parser.add_argument(
        "--llm-provider",
        choices=["ollama", "openai", "google"],
        default=DEFAULT_LLM_PROVIDER,
        help="LLM backend provider: ollama (local), openai (vLLM endpoint), google (Gemini API)",
    )
    parser.add_argument(
        "--fallback-model",
        default=DEFAULT_FALLBACK_MODEL,
        help="Fallback model name when primary model fails or times out",
    )
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS, help="Maximum LLM-tool loop steps")
    parser.add_argument("--chat-timeout-sec", type=int, default=CHAT_TIMEOUT_SEC, help="Per-call timeout for LLM inference")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    # Google provider 지정 시 모델이 기본값(Ollama) 그대로면 Google 기본 모델로 교체
    resolved_model = args.model
    if args.llm_provider == "google" and resolved_model == DEFAULT_MODEL:
        resolved_model = DEFAULT_GOOGLE_MODEL
    resolved_fallback = args.fallback_model
    if args.llm_provider == "google" and resolved_fallback == DEFAULT_FALLBACK_MODEL:
        resolved_fallback = DEFAULT_GOOGLE_MODEL
    outcome = asyncio.run(
        run_agent_loop(
            user_query=args.query,
            model=resolved_model,
            fallback_model=resolved_fallback,
            llm_provider=args.llm_provider,
            max_steps=args.max_steps,
            chat_timeout_sec=args.chat_timeout_sec,
        )
    )
    print(json.dumps(_to_jsonable(outcome), ensure_ascii=False, indent=2))

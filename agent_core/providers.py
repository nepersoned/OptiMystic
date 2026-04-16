import asyncio
import json
import os
from typing import Any, Dict, List, Tuple

import ollama

from .helpers import to_jsonable

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


async def chat_ollama(model: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        tc_id = getattr(tc, "id", None)
        name = getattr(fn, "name", "") if fn else ""
        arguments = getattr(fn, "arguments", "{}") if fn else "{}"
        item: Dict[str, Any] = {
            "type": "function",
            "function": {
                "name": str(name),
                "arguments": arguments if isinstance(arguments, str) else json.dumps(to_jsonable(arguments), ensure_ascii=False),
            },
        }
        if tc_id:
            item["id"] = str(tc_id)
        out.append(item)
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


async def chat_openai(model: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
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


_GOOGLE_SCHEMA_ALLOWED = {
    "type", "description", "properties", "required", "items",
    "enum", "anyOf", "allOf", "oneOf", "not", "format",
    "minimum", "maximum", "minLength", "maxLength",
    "minItems", "maxItems", "additionalProperties",
}


def _clean_schema_for_google(schema: Any) -> Any:
    if isinstance(schema, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in schema.items():
            if k not in _GOOGLE_SCHEMA_ALLOWED:
                continue
            cleaned[k] = _clean_schema_for_google(v)
        if "required" in cleaned and "properties" in cleaned:
            existing = set(cleaned["properties"].keys())
            filtered_req = [r for r in cleaned["required"] if r in existing]
            if filtered_req:
                cleaned["required"] = filtered_req
            else:
                del cleaned["required"]
        elif "required" in cleaned:
            del cleaned["required"]
        return cleaned
    if isinstance(schema, list):
        return [_clean_schema_for_google(i) for i in schema]
    return schema


def _convert_tools_to_google(tools: List[Dict[str, Any]]) -> Any:
    if google_types is None:
        return None
    fn_decls: List[Dict[str, Any]] = []
    for t in tools:
        fn = t.get("function") or {}
        raw_params = fn.get("parameters") or {"type": "object", "properties": {}}
        fn_decls.append({
            "name": fn.get("name", ""),
            "description": fn.get("description", ""),
            "parameters": _clean_schema_for_google(raw_params),
        })
    return google_types.Tool(function_declarations=fn_decls)


def _convert_messages_to_google(messages: List[Dict[str, Any]]) -> Tuple[Any, List[Any]]:
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
                parts.append(
                    google_types.Part(function_call=google_types.FunctionCall(name=name, args=args))
                )
            if parts:
                contents.append(google_types.Content(role="model", parts=parts))
        elif role == "tool":
            name = msg.get("name", "")
            try:
                result: Any = json.loads(content) if isinstance(content, str) else content
            except Exception:
                result = {"content": content}
            contents.append(
                google_types.Content(
                    role="user",
                    parts=[
                        google_types.Part(
                            function_response=google_types.FunctionResponse(
                                name=name,
                                response=result if isinstance(result, dict) else {"content": str(result)},
                            )
                        )
                    ],
                )
            )
    system_instruction = "\n\n".join(system_parts) if system_parts else None
    return system_instruction, contents


def _chat_google_sync(model: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    client = _build_google_client()
    google_tool = _convert_tools_to_google(tools)
    system_instruction, contents = _convert_messages_to_google(messages)
    config_kwargs: Dict[str, Any] = {
        "temperature": 0.1,
    }
    if hasattr(google_types, "ThinkingConfig"):
        try:
            config_kwargs["thinking_config"] = google_types.ThinkingConfig(thinking_level="high")
        except Exception:
            pass
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
            tc: Dict[str, Any] = {
                "type": "function",
                "function": {
                    "name": str(fc.name),
                    "arguments": json.dumps(to_jsonable(dict(fc.args) if fc.args else {}), ensure_ascii=False),
                },
            }
            fc_id = getattr(fc, "id", None)
            if fc_id:
                tc["id"] = str(fc_id)
            tool_calls.append(tc)

    text_chunks: List[str] = []
    for cand in getattr(response, "candidates", []) or []:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) if content is not None else None
        for p in parts or []:
            txt = getattr(p, "text", None)
            if txt:
                text_chunks.append(str(txt))
    text_content = "\n".join(text_chunks).strip()

    return {
        "message": {
            "content": text_content,
            "tool_calls": tool_calls,
        }
    }


async def chat_google(model: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    return await asyncio.to_thread(_chat_google_sync, model, messages, tools)


async def chat_with_provider(
    provider: str,
    model: str,
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
) -> Dict[str, Any]:
    provider_key = (provider or "").strip().lower()
    if provider_key == "openai":
        return await chat_openai(model=model, messages=messages, tools=tools)
    if provider_key == "google":
        return await chat_google(model=model, messages=messages, tools=tools)
    return await chat_ollama(model=model, messages=messages, tools=tools)

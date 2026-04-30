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

try:
    from google.cloud import secretmanager as google_secretmanager
except Exception:
    google_secretmanager = None


async def chat_ollama(model: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    return await asyncio.to_thread(
        ollama.chat,
        model=model,
        messages=messages,
        tools=tools,
        options={"temperature": 0.35},
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
        temperature=0.35,
    )

    choice = response.choices[0]
    msg = choice.message
    tool_calls = _normalize_openai_tool_calls(getattr(msg, "tool_calls", None))
    usage = getattr(response, "usage", None)
    usage_payload = None
    if usage is not None:
        usage_payload = {
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        }
    return {
        "message": {
            "content": getattr(msg, "content", "") or "",
            "tool_calls": tool_calls,
        },
        "usage": usage_payload,
    }


async def chat_openai(model: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    return await asyncio.to_thread(
        _chat_openai_sync,
        model,
        messages,
        tools,
    )


_google_client_cache: Any = None

def _build_google_client() -> Any:
    global _google_client_cache
    if _google_client_cache is not None:
        return _google_client_cache
    if google_genai is None:
        raise RuntimeError("google-genai package is not installed. Run: pip install google-genai")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        secret_name = os.getenv("OPTIMYSTIC_GOOGLE_API_KEY_SECRET", "").strip()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        if secret_name and project_id and google_secretmanager is not None:
            client = google_secretmanager.SecretManagerServiceClient()
            secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            try:
                response = client.access_secret_version(request={"name": secret_path})
                api_key = response.payload.data.decode("utf-8").strip()
            except Exception as exc:
                raise RuntimeError(f"Failed to load GOOGLE_API_KEY from Secret Manager: {exc}") from exc

    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY environment variable is not set.")
    if not api_key.startswith("AIza"):
        print(
            "[CONFIG] GOOGLE_API_KEY does not start with 'AIza'. "
            "If Gemini Developer API auth fails, use an AI Studio key or switch to Vertex AI auth.",
            flush=True,
        )
    _google_client_cache = google_genai.Client(api_key=api_key)
    return _google_client_cache


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
    import time
    client = _build_google_client()
    google_tool = _convert_tools_to_google(tools)
    system_instruction, contents = _convert_messages_to_google(messages)
    config_kwargs: Dict[str, Any] = {
        "temperature": 0.35,
    }
    if google_tool:
        config_kwargs["tools"] = [google_tool]
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    config = google_types.GenerateContentConfig(**config_kwargs)

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            break
        except Exception as exc:
            last_exc = exc
            msg = str(exc)
            if attempt < 2 and ("503" in msg or "429" in msg or "UNAVAILABLE" in msg or "RESOURCE_EXHAUSTED" in msg):
                time.sleep(2 ** attempt * 2)  # 2s, 4s
                continue
            raise
    else:
        raise last_exc  # type: ignore[misc]
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
            # thinking 파트(내부 추론)는 응답에 포함하지 않음
            if getattr(p, "thought", False):
                continue
            txt = getattr(p, "text", None)
            if txt:
                text_chunks.append(str(txt))
    text_content = "\n".join(text_chunks).strip()

    usage_payload = None
    usage_meta = getattr(response, "usage_metadata", None)
    if usage_meta is not None:
        prompt_tokens = int(getattr(usage_meta, "prompt_token_count", 0) or 0)
        completion_tokens = int(getattr(usage_meta, "candidates_token_count", 0) or 0)
        total_tokens = int(getattr(usage_meta, "total_token_count", prompt_tokens + completion_tokens) or 0)
        usage_payload = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    return {
        "message": {
            "content": text_content,
            "tool_calls": tool_calls,
        },
        "usage": usage_payload,
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

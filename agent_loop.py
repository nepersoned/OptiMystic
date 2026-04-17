import argparse
import asyncio
import json

from agent_core import (
    CHAT_TIMEOUT_SEC,
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_GOOGLE_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_MODEL,
    MAX_STEPS,
    run_agent_loop,
)
from agent_core.helpers import to_jsonable
from agent_core.logging_utils import configure_structured_logging


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
        help="LLM backend provider: ollama (local), openai (OpenAI-compatible endpoint), google (Gemini API)",
    )
    parser.add_argument(
        "--fallback-model",
        default=DEFAULT_FALLBACK_MODEL,
        help="Fallback model name when primary model fails or times out",
    )
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS, help="Maximum LLM-tool loop steps")
    parser.add_argument("--chat-timeout-sec", type=int, default=CHAT_TIMEOUT_SEC, help="Per-call timeout for LLM inference")
    return parser.parse_args()


def main() -> None:
    configure_structured_logging()
    args = parse_args()
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
    print(json.dumps(to_jsonable(outcome), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

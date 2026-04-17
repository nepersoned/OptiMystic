from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key in (
            "trace_id",
            "tenant_id",
            "provider",
            "model",
            "step",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "estimated_cost_usd",
            "budget_usd",
            "domain",
            "solver",
            "status",
            "idempotency_key",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


def configure_structured_logging(default_level: str = "INFO") -> None:
    level_name = (os.getenv("OPTIMYSTIC_LOG_LEVEL", default_level) or default_level).upper().strip()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(JsonLogFormatter())

    root.handlers.clear()
    root.addHandler(handler)

import logging
import os
import uuid

from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from agent_core.logging_utils import configure_structured_logging
from python_solvers.api.schemas import HealthResponse, OptimizationRunSummary, OptimizeRequest, OptimizeResponse
from python_solvers.api.solver_api import run_optimization
from python_solvers.db import (
    create_optimization_run,
    get_idempotent_response,
    init_db,
    is_database_enabled,
    list_optimization_runs,
    save_idempotent_response,
)


logger = logging.getLogger(__name__)


TRACE_HEADER = "X-Trace-Id"
API_KEY_HEADER = "X-API-Key"
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"


def _resolve_api_keys() -> set[str]:
    raw = os.getenv("OPTIMYSTIC_API_KEYS", "")
    return {part.strip() for part in raw.split(",") if part and part.strip()}


def _resolve_api_key_tenants() -> dict[str, str]:
    raw = os.getenv("OPTIMYSTIC_API_KEY_TENANTS", "")
    mapping: dict[str, str] = {}
    for part in raw.split(","):
        token = part.strip()
        if not token or ":" not in token:
            continue
        key, tenant = token.split(":", 1)
        key = key.strip()
        tenant = tenant.strip()
        if key and tenant:
            mapping[key] = tenant
    return mapping


def _require_api_key(request: Request, trace_id: str) -> str:
    supplied_key = request.headers.get(API_KEY_HEADER, "").strip()
    tenant_map = _resolve_api_key_tenants()
    if tenant_map:
        tenant_id = tenant_map.get(supplied_key)
        if tenant_id:
            return tenant_id
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "Valid X-API-Key is required.", "trace_id": trace_id},
        )

    valid_keys = _resolve_api_keys()
    if not valid_keys:
        return "public"

    if supplied_key in valid_keys:
        return "shared"

    raise HTTPException(
        status_code=401,
        detail={"code": "unauthorized", "message": "Valid X-API-Key is required.", "trace_id": trace_id},
    )


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_trace_id = request.headers.get(TRACE_HEADER, "").strip()
        trace_id = incoming_trace_id or str(uuid.uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers[TRACE_HEADER] = trace_id
        return response


app = FastAPI(
    title="OptiMystic Python Solvers API",
    version="0.1.0",
    description="FastAPI wrapper for python_solvers runtime",
)
app.add_middleware(TraceIdMiddleware)


@app.on_event("startup")
def startup() -> None:
    configure_structured_logging()
    init_db()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", database_enabled=is_database_enabled())


@app.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest, request: Request) -> OptimizeResponse:
    trace_id = str(getattr(request.state, "trace_id", "") or str(uuid.uuid4()))
    tenant_id = _require_api_key(request, trace_id)

    idempotency_key = request.headers.get(IDEMPOTENCY_KEY_HEADER, "").strip()
    request_payload = req.model_dump()
    request_payload["trace_id"] = trace_id
    request_payload["tenant_id"] = tenant_id

    try:
        if idempotency_key and is_database_enabled():
            idem_state = get_idempotent_response(idempotency_key, request_payload)
            if idem_state.get("state") == "hit":
                replay_payload = dict(idem_state.get("response_payload") or {})
                replay_payload["trace_id"] = trace_id
                replay_payload["tenant_id"] = tenant_id
                logger.info(
                    "Optimization idempotency replay",
                    extra={"trace_id": trace_id, "idempotency_key": idempotency_key, "tenant_id": tenant_id},
                )
                return OptimizeResponse(**replay_payload)
            if idem_state.get("state") == "conflict":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "idempotency_key_conflict",
                        "message": "Idempotency-Key was already used with a different request payload.",
                        "trace_id": trace_id,
                    },
                )

        logger.info(
            "Optimization request received",
            extra={"trace_id": trace_id, "tenant_id": tenant_id, "domain": req.domain, "solver": req.solver},
        )
        result = run_optimization(req.domain, req.solver, req.params, trace_id=trace_id)
        response_payload = dict(result)
        response_payload["tenant_id"] = tenant_id
        if is_database_enabled():
            try:
                run_id = create_optimization_run(request_payload, response_payload)
                if run_id is not None:
                    response_payload["run_id"] = run_id
                if idempotency_key:
                    save_idempotent_response(idempotency_key, request_payload, response_payload, run_id=run_id)
            except Exception:
                logger.exception(
                    "Failed to persist optimization run",
                    extra={"trace_id": trace_id, "tenant_id": tenant_id, "domain": req.domain, "solver": req.solver},
                )
                response_payload.setdefault("error_msg", "database_write_failed")
        elif idempotency_key:
            logger.warning(
                "Idempotency-Key ignored because database is disabled",
                extra={"trace_id": trace_id, "tenant_id": tenant_id, "idempotency_key": idempotency_key},
            )
        logger.info(
            "Optimization request completed",
            extra={"trace_id": trace_id, "tenant_id": tenant_id, "status": response_payload.get("status")},
        )
        return OptimizeResponse(**response_payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_request", "message": str(exc), "trace_id": trace_id},
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "solver_runtime_error", "message": str(exc), "trace_id": trace_id},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "internal_error", "message": str(exc), "trace_id": trace_id},
        ) from exc


@app.get("/runs", response_model=list[OptimizationRunSummary])
def list_runs(limit: int = 20, request: Request | None = None) -> list[OptimizationRunSummary]:
    trace_id = ""
    tenant_id = ""
    if request is not None:
        trace_id = str(getattr(request.state, "trace_id", "") or "")
        tenant_id = _require_api_key(request, trace_id)

    if not is_database_enabled():
        raise HTTPException(
            status_code=503,
            detail={"code": "database_disabled", "message": "Set DATABASE_URL to enable optimization run history."},
        )

    scope_tenant = tenant_id if tenant_id not in {"", "public", "shared"} else None
    return [OptimizationRunSummary(**row) for row in list_optimization_runs(limit=limit, tenant_id=scope_tenant)]
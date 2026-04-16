from fastapi import FastAPI, HTTPException

from python_solvers.api.schemas import HealthResponse, OptimizationRunSummary, OptimizeRequest, OptimizeResponse
from python_solvers.api.solver_api import run_optimization
from python_solvers.db import create_optimization_run, init_db, is_database_enabled, list_optimization_runs


app = FastAPI(
    title="OptiMystic Python Solvers API",
    version="0.1.0",
    description="FastAPI wrapper for python_solvers runtime",
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", database_enabled=is_database_enabled())


@app.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest) -> OptimizeResponse:
    try:
        result = run_optimization(req.domain, req.solver, req.params)
        response_payload = dict(result)
        if is_database_enabled():
            try:
                run_id = create_optimization_run(req.model_dump(), response_payload)
                if run_id is not None:
                    response_payload["run_id"] = run_id
            except Exception:
                response_payload.setdefault("error_msg", "database_write_failed")
        return OptimizeResponse(**response_payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail={"code": "solver_runtime_error", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"code": "internal_error", "message": str(exc)}) from exc


@app.get("/runs", response_model=list[OptimizationRunSummary])
def list_runs(limit: int = 20) -> list[OptimizationRunSummary]:
    if not is_database_enabled():
        raise HTTPException(
            status_code=503,
            detail={"code": "database_disabled", "message": "Set DATABASE_URL to enable optimization run history."},
        )

    return [OptimizationRunSummary(**row) for row in list_optimization_runs(limit=limit)]
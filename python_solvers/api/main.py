from fastapi import FastAPI, HTTPException

from python_solvers.api.schemas import HealthResponse, OptimizeRequest, OptimizeResponse
from python_solvers.api.solver_api import run_optimization


app = FastAPI(
    title="OptiMystic Python Solvers API",
    version="0.1.0",
    description="FastAPI wrapper for python_solvers runtime",
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest) -> OptimizeResponse:
    try:
        result = run_optimization(req.domain, req.solver, req.params)
        return OptimizeResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_request", "message": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail={"code": "solver_runtime_error", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"code": "internal_error", "message": str(exc)}) from exc
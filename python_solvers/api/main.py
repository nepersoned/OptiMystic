API, HTTPException

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
    except Exception as exc:
        # Keep API response shape stable while surfacing solver/build errors.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
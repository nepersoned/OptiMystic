from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OptimizeRequest(BaseModel):
    domain: str = Field(..., description="Optimization domain, e.g. packing, cutting, scheduling")
    solver: str = Field(..., description="Solver type, e.g. mip, cp, st")
    params: Dict[str, Any] = Field(default_factory=dict, description="Domain-specific parameters")


class OptimizeResponse(BaseModel):
    status: str
    objective: Optional[float] = None
    variables: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: List[Dict[str, Any]] = Field(default_factory=list)
    solve_time: float = 0.0
    lp_sensitivity: bool = False
    details: Any = None
    sensitivity: Any = None
    error_msg: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
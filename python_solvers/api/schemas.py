from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class OptimizeRequest(BaseModel):
    domain: str = Field(..., description="Optimization domain, e.g. packing, cutting, scheduling")
    solver: str = Field(..., description="Solver type, e.g. mip, cp, st")
    params: Dict[str, Any] = Field(default_factory=dict, description="Domain-specific parameters")


class CuttingOutput(BaseModel):
    mode: Literal["cutting"] = "cutting"
    total_cost: float = 0.0
    total_waste: float = 0.0
    num_bins: int = 0
    bin_plans: List[Dict[str, Any]] = Field(default_factory=list)
    report: str = ""
    item_counts: Dict[str, int] = Field(default_factory=dict)
    status: str = "unknown"


class PackingOutput(BaseModel):
    mode: Literal["packing"] = "packing"
    total_value: float = 0.0
    used_capacity: float = 0.0
    capacity: float = 0.0
    items: List[Dict[str, Any]] = Field(default_factory=list)
    report: str = ""
    status: str = "unknown"


class ResourcingOutput(BaseModel):
    mode: Literal["resourcing"] = "resourcing"
    total_value: float = 0.0
    used_cpu: float = 0.0
    used_ram: float = 0.0
    capacity_cpu: float = 0.0
    capacity_ram: float = 0.0
    items: List[Dict[str, Any]] = Field(default_factory=list)
    report: str = ""
    status: str = "unknown"


class SchedulingOutput(BaseModel):
    mode: Literal["scheduling"] = "scheduling"
    shift_coverage: Dict[str, int] = Field(default_factory=dict)
    assignments: List[Dict[str, Any]] = Field(default_factory=list)
    report: str = ""
    status: str = "unknown"


class GenericOutput(BaseModel):
    mode: Literal["generic"] = "generic"
    status: str = "unknown"
    report: str = ""
    objective_value: float = 0.0
    variable_count: int = 0
    constraint_count: int = 0
    active_variables: List[Dict[str, Any]] = Field(default_factory=list)


OptimizeDetails = Annotated[
    Union[CuttingOutput, PackingOutput, ResourcingOutput, SchedulingOutput, GenericOutput],
    Field(discriminator="mode"),
]


class OptimizeResponse(BaseModel):
    status: str
    objective: Optional[float] = None
    variables: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: List[Dict[str, Any]] = Field(default_factory=list)
    solve_time: float = 0.0
    lp_sensitivity: bool = False
    details: Optional[OptimizeDetails] = None
    sensitivity: Optional[Dict[str, Any]] = None
    error_msg: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
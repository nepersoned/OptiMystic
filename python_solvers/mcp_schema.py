from __future__ import annotations

from typing import Any, Dict, List, Literal, Type

from pydantic import BaseModel, Field


DomainName = Literal["cutting", "packing", "vrp", "scheduling", "resourcing", "generic"]


class PackingItemInput(BaseModel):
    Name: str = Field(..., description="Item identifier")
    Weight: float | int = Field(..., description="Per-unit weight")
    Value: float | int = Field(..., description="Per-unit value or priority")
    Demand: int = Field(..., ge=1, description="Required quantity (integer >= 1)")

    model_config = {"strict": True}


class PackingVehicleInput(BaseModel):
    Capacity: float | int = Field(..., gt=0, description="Vehicle/bin capacity")

    model_config = {"strict": True}


class PackingParamsInput(BaseModel):
    Items: List[PackingItemInput] = Field(..., min_length=1, description="Items to pack")
    Vehicles: List[PackingVehicleInput] = Field(..., min_length=1, description="Available bins/vehicles")


class VrpNodeInput(BaseModel):
    Name: str = Field(..., description="Node name")
    Demand: float | int = Field(0, description="Load demand at node")
    X: float | int | None = Field(None, description="Optional X coordinate")
    Y: float | int | None = Field(None, description="Optional Y coordinate")

    model_config = {"strict": True}


class VrpVehicleInput(BaseModel):
    Name: str = Field(..., description="Vehicle name")
    Capacity: float | int = Field(..., gt=0, description="Vehicle capacity")

    model_config = {"strict": True}


class VrpParamsInput(BaseModel):
    Nodes: List[VrpNodeInput] = Field(..., min_length=2, description="Depot + customer nodes")
    Vehicles: List[VrpVehicleInput] = Field(..., min_length=1, description="Vehicle fleet")


class SchedulingEmployeeInput(BaseModel):
    Name: str = Field(..., description="Employee identifier")
    MaxShifts: int | None = Field(None, ge=0, description="Optional employee max shifts")

    model_config = {"strict": True}


class SchedulingShiftInput(BaseModel):
    Name: str = Field(..., description="Shift name")
    Demand: int = Field(..., ge=1, description="Required headcount for this shift")

    model_config = {"strict": True}


class SchedulingParamsInput(BaseModel):
    Employees: List[SchedulingEmployeeInput] = Field(..., min_length=1, description="Workforce list")
    Shifts: List[SchedulingShiftInput] = Field(..., min_length=1, description="Shift demand definition")


class StockInput(BaseModel):
    Name: str = Field(..., description="Stock type identifier")
    Length: float | int = Field(..., gt=0, description="Stock length")
    Cost: float | int = Field(1, description="Stock use cost")
    Limit: int = Field(1, ge=1, description="Maximum stock count")

    model_config = {"strict": True}


class CuttingItemInput(BaseModel):
    Name: str = Field(..., description="Piece name")
    Length: float | int = Field(..., gt=0, description="Piece length")
    Demand: int = Field(..., ge=1, description="Required piece quantity")

    model_config = {"strict": True}


class CuttingParamsInput(BaseModel):
    Items: List[CuttingItemInput] = Field(..., min_length=1, description="Demanded pieces")
    Stocks: List[StockInput] = Field(..., min_length=1, description="Available stock types")
    Kerf: float | int = Field(0, ge=0, description="Cutting loss per cut")


class ResourcingTaskInput(BaseModel):
    Name: str = Field(..., description="Task/container name")
    CPU: float | int = Field(..., ge=0, description="CPU requirement")
    RAM: float | int = Field(..., ge=0, description="RAM requirement")
    Cost: float | int = Field(0, description="Objective weight or cost")

    model_config = {"strict": True}


class ResourcingServerInput(BaseModel):
    CPU: float | int = Field(..., gt=0, description="Server CPU capacity")
    RAM: float | int = Field(..., gt=0, description="Server RAM capacity")

    model_config = {"strict": True}


class ResourcingParamsInput(BaseModel):
    Containers: List[ResourcingTaskInput] = Field(..., min_length=1, description="Tasks/containers")
    Servers: List[ResourcingServerInput] = Field(..., min_length=1, description="Server resource pool")


class GenericParamsInput(BaseModel):
    IR: Dict[str, Any] = Field(..., description="Generic IR payload with variables/objective/constraints")


class OptimizationRequest(BaseModel):
    domain: DomainName = Field(
        ...,
        description=(
            "Target optimization domain. Use 'packing' for knapsack/bin-packing style, "
            "'cutting' for cutting-stock, 'vrp' for vehicle routing, 'scheduling' for "
            "shift/workforce assignment, 'resourcing' for resource allocation, and "
            "'generic' for math-programming style custom models. "
            "Choose the domain that best matches business intent before constructing params."
        ),
    )
    solver: Literal["cp", "mip", "ga", "cg", "st", "nlp", "minlp"] = Field(
        ...,
        description=(
            "Optimization engine family. Recommended mapping: scheduling->cp, vrp->mip "
            "(internally routed to OR-Tools VRP), packing/cutting->mip or cg, "
            "resourcing->st, generic nonlinear->nlp or minlp. "
            "If uncertain, prefer mip for linear/mixed-integer structures."
        ),
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Domain payload. Keep business entities and constraints explicit. "
            "Examples: "
            "(packing) Items[{Name, Weight, Value, Demand}], Vehicles[{Capacity}] ; "
            "(vrp) Nodes, Vehicles, DistanceMatrix/coordinates, optional TimeWindows ; "
            "(scheduling) Employees, Shifts, Values, MaxShiftsPerEmployee ; "
            "(cutting) stock sizes and piece demands. "
            "Use numeric values for capacities/costs/time and avoid natural-language strings in numeric fields."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "domain": "packing",
                    "solver": "mip",
                    "params": {
                        "Items": [
                            {"Name": "SKU-A", "Weight": 2, "Value": 8, "Demand": 3},
                            {"Name": "SKU-B", "Weight": 5, "Value": 20, "Demand": 1},
                        ],
                        "Vehicles": [{"Capacity": 7}],
                    },
                }
            ]
        }
    }


DOMAIN_PARAM_MODELS: Dict[str, Type[BaseModel]] = {
    "packing": PackingParamsInput,
    "vrp": VrpParamsInput,
    "scheduling": SchedulingParamsInput,
    "cutting": CuttingParamsInput,
    "resourcing": ResourcingParamsInput,
    "generic": GenericParamsInput,
}

# OptiMystic

Multi-domain optimization service with a Go HTTP layer and Python solver back end.

## Current status

- `MIP`: implemented through a domain-to-IR flow
- `CG`: available for cutting
- `CP`, `ST`, `GA`: present but not implemented end-to-end

## Architecture

```text
HTTP request
  -> Go server (`server/internal/handlers`)
  -> Go/Python bridge (`server/internal/solver/bridge.go`)
  -> Python CLI (`python_solvers/cli_solver.py`)
  -> Domain mapper (`python_solvers/domains/*.py`)
  -> IR-based MIP input (`params["IR"]`)
  -> Solver engine (`python_solvers/utils/solver_engine.py`)
  -> Python result processing (`python_solvers/utils/services.py`)
  -> Go result mapping (`server/internal/services/*.go`)
  -> HTTP response
```

## Key idea

Each domain builds a shared optimization IR.

- Domain layer: normalize input and build IR
- Logic layer: consume IR
- Solver engine: assemble and solve Pyomo model
- Bridge layer: move JSON between Go and Python

## Main folders

```text
OptiMystic/
├── python_solvers/
│   ├── cli_solver.py
│   ├── domains/
│   ├── logic/
│   └── utils/
├── server/
│   ├── cmd/server/main.go
│   └── internal/
├── _legacy/
└── _legacy_django/
```

## API endpoints

- `GET /api/health`
- `GET /api/health/`
- `POST /api/optimize`
- `POST /api/optimize/`

## Request shape

```json
{
  "template_type": "packing",
  "solver_type": "mip",
  "sense": "maximize",
  "params": {
    "Items": [
      {"Name": "A", "Weight": 2, "Value": 10, "Demand": 2},
      {"Name": "B", "Weight": 3, "Value": 12, "Demand": 1}
    ],
    "Vehicles": [
      {"Capacity": 5}
    ]
  }
}
```

## Response shape

```json
{
  "status": "Optimal",
  "objective": 22,
  "solve_time": 0.02,
  "variables": [],
  "constraints": [],
  "details": {},
  "sensitivity": null
}
```

## Local run

```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic\server
go run .\cmd\server\main.go
```

## Python CLI example

```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic
python python_solvers\cli_solver.py --domain packing --solver mip --params "{\"Items\":[{\"Name\":\"A\",\"Weight\":2,\"Value\":10,\"Demand\":2},{\"Name\":\"B\",\"Weight\":3,\"Value\":12,\"Demand\":1}],\"Vehicles\":[{\"Capacity\":5}],\"Sense\":\"maximize\"}"
```

## Notes

- Runtime success still depends on local Python environment and a working MILP solver such as CBC.
- The legacy folders are kept as references and are not the active runtime path.

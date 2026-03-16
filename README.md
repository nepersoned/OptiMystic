# OptiMystic

Multi-domain optimization platform with a Go HTTP API (`server`) and Python solver runtime (`python_solvers`).

This repository is organized for production-like API orchestration, domain-aware modeling, and contract-first optimization payloads.

## What This Repository Delivers

- Stable HTTP entry point for optimization requests (`/api/optimize`)
- Safe Go-to-Python bridge execution with timeout control
- Domain-mapped model generation (`cutting`, `packing`, `resourcing`, `scheduling`, `generic`)
- Multiple solver strategies (MIP, CP, ST, partial CG/GA)
- Standardized JSON output contract for frontend/backend integration

## Architecture

```text
HTTP client
  -> Go API layer (`server/internal/handlers`)
  -> Go/Python bridge (`server/internal/solver/bridge.go`)
  -> Python CLI runtime (`python_solvers/cli_solver.py`)
  -> Domain mapper (`python_solvers/domains/*.py`)
  -> Solver logic (`python_solvers/logic/*.py`)
  -> Solver engine (`python_solvers/utils/solver_engine.py`)
  -> Result shaping (`python_solvers/utils/services.py`)
  -> Go result dispatch (`server/internal/services/*.go`)
  -> HTTP JSON response
```

## Runtime Components

- `server/`  
  Go API service handling routing, validation, subprocess orchestration, timeout, and response mapping.
- `python_solvers/`  
  Python runtime that transforms domain inputs into solver models and returns normalized JSON results.
- `_legacy/`, `_legacy_django/`  
  Reference code only; not the active runtime path.

## Capability Matrix

| Domain      | MIP | CP | ST | CG | GA | Notes |
|-------------|-----|----|----|----|----|-------|
| cutting     | yes | -  | -  | partial | partial | MIP path is IR-driven; CG exists but integration is case-dependent |
| packing     | yes | -  | -  | -  | partial | MIP path implemented |
| resourcing  | partial | - | yes | - | partial | ST path implemented |
| scheduling  | partial | yes | - | - | partial | CP is primary path |
| generic     | yes | - | - | - | - | Direct IR passthrough for advanced/custom models |

> Status reflects current code structure from repository documentation; exact runtime behavior still depends on installed solver backends.

## API Endpoints

- `GET /api/health`
- `GET /api/health/`
- `POST /api/optimize`
- `POST /api/optimize/`

## Quick Start (Windows cmd.exe)

### 1) Install Python dependencies

```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic
pip install -r python_solvers\requirements.txt
```

### 2) Run Go API server

```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic\server
go run .\cmd\server\main.go
```

### 3) Test Python runtime directly (CLI)

```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic
python python_solvers\cli_solver.py --domain packing --solver mip --params "{\"Items\":[{\"Name\":\"A\",\"Weight\":2,\"Value\":10,\"Demand\":2},{\"Name\":\"B\",\"Weight\":3,\"Value\":12,\"Demand\":1}],\"Vehicles\":[{\"Capacity\":5}],\"Sense\":\"maximize\"}"
```

## Request Contract

Minimal API request shape:

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

Minimal response shape:

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

## Generic IR Path (Advanced)

For frontend-transformed or expert-generated models, use `template_type: "generic"` with IR payload in `params.IR`.

```json
{
  "template_type": "generic",
  "solver_type": "mip",
  "sense": "maximize",
  "params": {
    "IR": [
      { "type": "var", "name": "x", "lb": 0 },
      { "type": "objective", "sense": "maximize", "expr": [[1, "x"]] }
    ]
  }
}
```

## Development Notes

- Go server timeout for Python subprocess:
  - Environment variable: `OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS`
  - Default in server README: `30`
- Primary integration flow:
  - `server/internal/handlers/optimize.go`
  - `server/internal/solver/bridge.go`
  - `python_solvers/cli_solver.py`
- Response mapping:
  - Domain-aware dispatch in `server/internal/services/results.go`

## Troubleshooting

- `python not found`  
  Ensure Python is installed and available in `PATH` for the Go server process.
- solver backend missing (`cbc`, `glpk`, etc.)  
  Install required Pyomo backend solver and verify availability in the current environment.
- CP flow errors  
  Confirm OR-Tools is installed from `python_solvers/requirements.txt`.
- timeout on large models  
  Increase `OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS` before running server.
- empty or generic-looking `details`  
  Validate `template_type` + `solver_type` combination and whether typed result mapping exists.

## Repo Structure

```text
OptiMystic/
├── README.md
├── server/
│   ├── README.md
│   ├── cmd/server/main.go
│   └── internal/
├── python_solvers/
│   ├── README.md
│   ├── cli_solver.py
│   ├── domains/
│   ├── logic/
│   └── utils/
├── _legacy/
└── _legacy_django/
```

## Related Docs

- Server details: `server/README.md`
- Python runtime details: `python_solvers/README.md`
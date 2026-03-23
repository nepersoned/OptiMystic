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
     ├─ solver_type == "cp" → logic_cp.solve_cp_model() [OR-Tools]
     └─ solver_type != "cp" → subprocess Julia runtime
        ├─ domains/*.py → IR generation
        └─ julia_solvers/ → routing
            ├─ route_solver() dispatcher
            ├─ mip.jl (JuMP+HiGHS) + GA warmstart
            ├─ cg.jl (Column Generation for cutting)
            ├─ st.jl (Stochastic two-stage for resourcing)
            └─ ga.jl (Evolutionary search)
  -> Result shaping (`python_solvers/utils/services.py`)
  -> Go result dispatch (`server/internal/services/*.go`)
  -> HTTP JSON response
```

**Runtime Split:**
- **Python (OR-Tools CP-SAT)**: Scheduling domain only
- **Julia (JuMP ecosystem)**: All other domains (MIP/GA/CG/ST)

## Runtime Components

- `server/`  
  Go API service handling routing, validation, subprocess orchestration, timeout, and response mapping.
- `python_solvers/`  
  Python runtime that transforms domain inputs into solver models and returns normalized JSON results.
- `_legacy/`, `_legacy_django/`  
  Reference code only; not the active runtime path.

## Solver-Domain Compatibility Matrix

| Domain | CP (OR-Tools) | MIP (JuMP+HiGHS) | GA (Evolutionary) | CG (Column Gen) | ST (Stochastic) |
|--------|---|---|---|---|---|
| **scheduling** | ✅ Primary | ✅ Fallback | ✅ MIP warmstart | ❌ | ❌ |
| **cutting** | ❌ | ✅ Fallback | ✅ MIP warmstart | ✅ Primary (Mode="cutting") | ❌ |
| **packing** | ❌ | ✅ | ✅ MIP warmstart | ❌ | ❌ |
| **resourcing** | ❌ | ✅ Fallback | ✅ MIP warmstart | ❌ | ✅ Primary (Mode="resourcing") |
| **generic** | ❌ | ✅ | ✅ MIP warmstart | ❌ | ❌ |

**Legend:**
- ✅ Primary: Domain-specialized solver path (e.g., CP for scheduling)
- ✅ Fallback: Automatically used if primary not applicable
- ✅ MIP warmstart: GA generates candidate solutions injected into MIP
- 🟡 Partial: Integration available case-by-case (see domain README)
- ❌ Not compatible

## API Endpoints

- `GET /api/health`
- `GET /api/health/`
- `POST /api/optimize`
- `POST /api/optimize/`

## Quick Start (Windows cmd.exe)

### 1) Install Dependencies

**Python:**
```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic
pip install -r python_solvers\requirements.txt
```

**Julia** (Optional, required for non-CP solvers):
```cmd
REM Download Julia from https://julialang.org/downloads/
REM Add julia.exe to PATH, then:
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic\julia_solvers
julia --project=. -e "using Pkg; Pkg.instantiate()"
```

### 2) Run Go API Server

```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic\server
go run .\cmd\server\main.go
```

API listens on `http://localhost:8080/api/optimize`

### 3) Test Solver Dispatch (CLI)

**Scheduling (CP - Python):**
```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic
python python_solvers\cli_solver.py --domain scheduling --solver cp --params "{\"Employees\":[{\"Name\":\"E1\",\"MaxShifts\":5}],\"Shifts\":[{\"Name\":\"Morning\",\"Demand\":2}],\"Values\":{\"E1\":{\"Morning\":1}},\"MaxShiftsPerEmployee\":5}"
```

**Cutting Stock (CG - Julia):**
```cmd
python python_solvers\cli_solver.py --domain cutting --solver cg --params "{\"Mode\":\"cutting\",\"Items\":[{\"Name\":\"A\",\"Length\":10,\"Demand\":5}],\"Stocks\":[{\"Length\":100,\"Cost\":1.0}],\"Kerf\":0.1}"
```

**Packing (MIP - Julia):**
```cmd
python python_solvers\cli_solver.py --domain packing --solver mip --params "{\"Items\":[{\"Name\":\"A\",\"Weight\":2,\"Value\":10}],\"Vehicles\":[{\"Capacity\":5}]}"
```

**Resourcing (ST - Julia):**
```cmd
python python_solvers\cli_solver.py --domain resourcing --solver st --params "{\"Mode\":\"resourcing\",\"Items\":[{\"Name\":\"CPU\",\"Value\":10}],\"Scenarios\":[{\"Name\":\"S1\",\"Probability\":1.0,\"Demands\":{\"CPU\":50}}],\"CPU\":100,\"ShortfallPenalty\":5.0}"
```

### 4) Test via HTTP

```cmd
curl -X POST http://localhost:8080/api/optimize ^
  -H "Content-Type: application/json" ^
  -d "{\"template_type\":\"scheduling\",\"solver_type\":\"cp\",\"params\":{\"Employees\":[{\"Name\":\"E1\",\"MaxShifts\":5}],\"Shifts\":[{\"Name\":\"Morning\",\"Demand\":2}],\"Values\":{\"E1\":{\"Morning\":1}},\"MaxShiftsPerEmployee\":5}}"
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

## Solver & Domain Selection Guide

Consult this table to choose the right solver for your problem domain:

| Goal | Domain | Solver | Why | Runtime |
|------|--------|--------|-----|---------|
| **Schedule employees across shifts** | scheduling | `cp` | OR-Tools CP-SAT specialized for binary assignment | Python |
| Schedule with MIP instead | scheduling | `mip` | LP relaxation via generic MIP path | Julia |
| **Cutting stock (educational)** | cutting | `cg` | Column generation with master/pricing decomposition | Julia |
| Cutting (large scale) | cutting | `mip` | Generic MIP faster when problem scales | Julia |
| **Bin packing / vehicle routing** | packing | `mip` | Generic MIP handles capacity & loading constraints | Julia |
| **Resource allocation under demand uncertainty** | resourcing | `st` | Two-stage stochastic with scenario recourse | Julia |
| Resource allocation (deterministic) | resourcing | `mip` | Simplified to single-stage MIP | Julia |
| **Custom optimization** | generic | `mip` | Direct IR passthrough for expert models | Julia |
| Exploratory search (any problem) | any | `ga` | Pure evolutionary, no MIP refinement | Julia |

**Key distinctions:**
- **Python-only (CP)**: Scheduling domain with CP solver
- **Julia-delegated**: All other `solver_type` values (mip, ga, cg, st)
- **Fallback logic**: If specialized solver unavailable, system automatically chains to next option (e.g., CG→GA+MIP, ST→GA+MIP)

## Documentation Reference

- **Python CP (scheduling)**: [python_solvers/README.md](python_solvers/README.md)
- **Julia solvers (mip, ga, cg, st)**: [julia_solvers/README.md](julia_solvers/README.md)
- **API specification**: See `server/README.md`

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
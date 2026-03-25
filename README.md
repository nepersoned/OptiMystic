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

## Quick Start (One Verified Path)

Use this single flow for demos/evaluation on Windows PowerShell.
It is intentionally minimal and focuses on a known-good end-to-end API call.

### 1) Install Python dependencies with project venv

```powershell
cd C:\Users\kevin\OneDrive\Desktop\OptiMystic
\.venv\Scripts\python.exe -m pip install -r python_solvers\requirements.txt
```

### 2) Start API server (Terminal A)

```powershell
cd C:\Users\kevin\OneDrive\Desktop\OptiMystic\server
$env:OPTIMYSTIC_PYTHON = "C:/Users/kevin/OneDrive/Desktop/OptiMystic/.venv/Scripts/python.exe"
$env:OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS = "180"
$env:OPTIMYSTIC_JULIA_TIMEOUT_SECONDS = "180"
go run .\cmd\server\main.go
```

### 3) Run the verified smoke test set (Terminal B)

```powershell
cd C:\Users\kevin\OneDrive\Desktop\OptiMystic
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1
```

Smoke payload files used by the script:
- `examples/smoke/scheduling-cp-ok.json`
- `examples/smoke/packing-mip-ok.json`

If you need Docker or Julia-only examples, see the submodule READMEs:
- `server/README.md`
- `python_solvers/README.md`
- `julia_solvers/README.md`

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
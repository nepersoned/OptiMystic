# OptiMystic

Multi-domain optimization platform based on Python, Julia, and R.

## What This Repository Delivers

- Interactive development with JupyterLab (Python/Julia/R kernels).
- HTTP optimization API based on FastAPI.
- Domain-mapped solver routing across CP, VRP, MIP, GA, CG, ST, NLP, MINLP.
- Post-analysis analytics and plotting with R (expanding scope).

## Current Architecture

```text
HTTP Client
  -> FastAPI endpoint (python_solvers/api/main.py)
  -> Python solver router (python_solvers/api/solver_api.py)
  -> Python runtime (CP/VRP) or Julia delegation (MIP/GA/CG/ST/NLP/MINLP)
  -> JSON response
```

Runtime split:
- Python (OR-Tools): scheduling (CP), vrp (routing)
- Julia (JuMP ecosystem): mip, ga, cg, st, nlp, minlp
- R: dedicated post-analysis layer for deeper business interpretation, diagnostics, and visualization

## Repository Layout

- `python_solvers/` - Active Python runtime and FastAPI service
- `julia_solvers/` - Julia solver implementations
- `r_solvers/` - R processors and visualization helpers
- `examples/` - Integration and debugging notebooks/scripts
- `_legacy/`, `_legacy_django/`, `_legacy_go/` - Archived implementations (reference only)

## API Endpoints

- `GET /health`
- `POST /optimize`

## Quick Start

### Option 1: JupyterLab

```powershell
cd C:\Your\Path\OptiMystic
pip install -r python_solvers\requirements.txt
pip install jupyterlab
jupyter lab
```

Open `examples/test_jupyterlab_full_pipeline.ipynb` and run the sections for Python, Julia, and R.

### Option 2: FastAPI (Local)

```powershell
cd C:\Your\Path\OptiMystic
pip install -r python_solvers\requirements.txt
uvicorn python_solvers.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Then call `http://localhost:8000/optimize`.

### Option 3: Docker Compose

Container build files are currently being refactored after Go-server decommission.
Use local run paths (Option 1 or Option 2) as the default for now.

## Request Contract

Minimal request example:

```json
{
  "domain": "packing",
  "solver": "mip",
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

Minimal response example:

```json
{
  "status": "Optimal",
  "objective": 22,
  "solve_time": 0.02,
  "variables": {},
  "constraints": {},
  "details": {},
  "sensitivity": null
}
```

## Domain-Solver Guide

| Goal | Domain | Solver | Runtime |
|------|--------|--------|---------|
| Shift scheduling | `scheduling` | `cp` | Python |
| Vehicle routing | `vrp` | `mip` (routed to OR-Tools VRP path) | Python |
| Cutting stock | `cutting` | `cg` / `mip` | Julia |
| Bin packing | `packing` | `mip` | Julia |
| Stochastic resourcing | `resourcing` | `st` | Julia |
| Nonlinear optimization | `generic` | `nlp` | Julia |
| Mixed-integer nonlinear optimization | `generic` | `minlp` | Julia |

## Documentation

- [python_solvers/README.md](python_solvers/README.md)
- [julia_solvers/README.md](julia_solvers/README.md)
- [r_solvers/README.md](r_solvers/README.md)
- [_legacy_go/README.md](_legacy_go/README.md)


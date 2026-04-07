# OptiMystic

Multi-domain optimization platform with dual service architectures:
- **JupyterLab**: Interactive analytics & development environment
- **MCP Server**: Production API orchestration

This repository integrates Go, Python, Julia, and R for domain-aware modeling and contract-first optimization.

## What This Repository Delivers

- **Interactive Development**: JupyterLab with Python/Julia/R notebooks for testing and prototyping
- **Production API**: Go HTTP API (`/api/optimize`) with subprocess orchestration and timeout control
- **Domain-Mapped Solvers**: Multiple strategies (CP, MIP, GA, CG, ST, VRP, NLP) across 7 domains
- **Post-Processing Analytics**: R-based result processing and visualization (ggplot2)
- **Standardized Contracts**: JSON-based request/response formats for frontend integration

## Architecture: Dual Service Model

### Service 1: JupyterLab (Interactive Development)
```text
JupyterLab Interface
├─ Python Kernel
│  └─ python_solvers/ (direct import)
│     ├─ domains/*.py (IR generation)
│     └─ cli_solver.py (solver routing)
│
├─ Julia Kernel
│  └─ julia_solvers/ (direct import)
│     ├─ src/main.jl
│     └─ src/solvers/*.jl
│
├─ R Kernel
│  └─ r_solvers/ (source files)
│     ├─ processors.R (result normalization)
│     ├─ plotting.R (ggplot2 visualization)
│     └─ domains/*.R (domain-specific analysis)
│
└─ Terminal (bash/powershell)
   └─ Go server management
      └─ Go API layer (`server/cmd/server/main.go`)
         └─ HTTP /api/optimize endpoint

** Workflow: Develop, test, and visualize end-to-end in one interface **
```

### Service 2: MCP Server (Production API)
```text
HTTP Client
  -> Go API layer (`server/internal/handlers`)
  -> Go/Python bridge (`server/internal/solver/bridge.go`)
  -> Python CLI runtime (`python_solvers/cli_solver.py`)
     ├─ solver_type == "cp" → logic_cp.solve_cp_model() [OR-Tools]
         ├─ domain == "vrp" → logic_vrp.solve_vrp_model() [OR-Tools routing]
         └─ solver_type != "cp" and domain != "vrp" → subprocess Julia runtime
        ├─ domains/*.py → IR generation
        └─ julia_solvers/ → routing
            ├─ route_solver() dispatcher
            ├─ mip.jl (JuMP+HiGHS) + GA warmstart
            ├─ cg.jl (Column Generation for cutting)
            ├─ st.jl (Stochastic two-stage for resourcing)
           ├─ nlp.jl (Ipopt-backed nonlinear optimization + GA warm start)
            └─ ga.jl (Evolutionary search)
  -> R post-processing (planned subprocess integration)
  -> Go result dispatch (`server/internal/services/*.go`)
  -> HTTP JSON response
```

**Solver Dispatch:**
- **Python (OR-Tools)**: CP scheduling, VRP routing
- **Julia (JuMP)**: MIP, GA, CG, ST, NLP
- **R (tidyverse/ggplot2)**: Result analytics & visualization

## Runtime Components

### For JupyterLab Development
- `python_solvers/` — Python solver runtimes (CP, MIP delegation)
- `julia_solvers/` — Julia optimizer ecosystem (MIP, GA, CG, ST, NLP)
- `r_solvers/` — R analytics & visualization (ggplot2-based post-processing)
- `examples/test_jupyterlab_full_pipeline.ipynb` — Complete end-to-end test notebook

### For MCP Production API
- `server/` — Go HTTP API service with subprocess orchestration
- `python_solvers/` — Solver runtime (shared with JupyterLab)
- `julia_solvers/` — Julia backend (shared with JupyterLab)

### Legacy (Reference Only)
- `_legacy/`, `_legacy_django/` — Old architecture; not active

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

## Quick Start

Choose your workflow:

### Option 1: Interactive Development (JupyterLab)

```powershell
cd C:\Your\Path\OptiMystic

# Install dependencies (one time)
pip install -r python_solvers\requirements.txt
pip install jupyterlab rpy2

# Start JupyterLab
jupyter lab

# Open: examples/test_jupyterlab_full_pipeline.ipynb
```

**In JupyterLab:**
- Notebook tabs: Python, Julia, R kernels side-by-side
- Terminal tab: Launch Go server (`cd server && go run .\cmd\server\main.go`)
- File browser: Edit code and see live results
- First run in notebook: R bridge check cell (`ensure_r_bridge()`) to verify rpy2 + `r_solvers` linkage

### Option 2: Production API (MCP Server)

```powershell
cd C:\Your\Path\OptiMystic\server

# Set environment variables
$env:OPTIMYSTIC_PYTHON = "C:/Your/Path/OptiMystic/.venv/Scripts/python.exe"
$env:OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS = "180"
$env:OPTIMYSTIC_JULIA_TIMEOUT_SECONDS = "180"

# Start API server
go run .\cmd\server\main.go
```

Then POST to `http://localhost:8080/api/optimize` with solver payloads.

### Option 3: Docker (Comprehensive)

```bash
docker-compose up
# Includes: Go API + Python + Julia + R + JupyterLab
```

---

**For detailed setup:** See `server/README.md`, `python_solvers/README.md`, `julia_solvers/README.md`, `r_solvers/README.md`

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
- **Python-only (CP/VRP)**: Scheduling domain with CP solver, VRP with OR-Tools routing
- **Julia-delegated**: All other `solver_type` values (mip, ga, cg, st, nlp)
- **Fallback logic**: If specialized solver unavailable, system automatically chains to next option (e.g., CG→GA+MIP, ST→GA+MIP)

## Documentation & Testing

### Setup Guides
- [Server (Go API)](server/README.md) — HTTP API, subprocess orchestration
- [Python Solvers](python_solvers/README.md) — CP-SAT, MIP delegation, domain handling
- [Julia Solvers](julia_solvers/README.md) — JuMP ecosystem (MIP, GA, CG, ST, NLP)
- [R Analytics](r_solvers/README.md) — Post-processing, visualization framework

### Testing
- **Main Test Suite**: `examples/test_jupyterlab_full_pipeline.ipynb`
  - Helper runner: `examples/jupyter_debug_tools.py`
  - Purpose: integration test/debug notebook (not a Voila deployment notebook)
  - Python-only test (CP scheduling)
  - Julia-only test (MIP packing)
  - R bridge test (`rpy2` + `r_solvers` source load)
  - R post-processing test (Python/Julia output -> `process_results`)
  - Full end-to-end pipeline validation
  - Run in JupyterLab or Jupyter Notebook

## Repo Structure

```text
OptiMystic/
├── docker-compose.yml
├── Dockerfile
├── README.md
├── examples/
│   ├── jupyter_debug_tools.py
│   └── test_jupyterlab_full_pipeline.ipynb  (MAIN TEST - Python + Julia + R)
├── server/
│   ├── README.md
│   ├── cmd/server/main.go
│   ├── go.mod
│   └── internal/
│       ├── handlers/
│       ├── models/
│       ├── router/
│       ├── services/
│       └── solver/
├── julia_solvers/
│   ├── README.md
│   ├── Project.toml
│   ├── Manifest.toml
│   ├── cli_solver.jl
│   └── src/
│       ├── main.jl
│       ├── solvers/
│       │   ├── mip.jl
│       │   ├── ga.jl
│       │   ├── cg.jl
│       │   ├── st.jl
│       │   ├── nlp.jl
│       │   └── router.jl
│       └── utils/
├── python_solvers/
│   ├── README.md
│   ├── requirements.txt
│   ├── cli_solver.py
│   ├── api/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── solver_api.py
│   ├── domains/
│   │   ├── cutting.py
│   │   ├── packing.py
│   │   ├── scheduling.py
│   │   ├── resourcing.py
│   │   ├── vrp.py
│   │   ├── generic.py
│   │   └── ir_utils.py
│   ├── logic/
│   │   ├── logic_cp.py
│   │   └── logic_vrp.py
│   └── utils/
│       └── bridge_logic.py
├── r_solvers/
│   ├── README.md
│   ├── utils.R              (common utilities)
│   ├── processors.R         (domain dispatchers + processing)
│   ├── plotting.R           (ggplot2 visualization framework)
│   └── domains/
│       ├── cutting.R        (cutting domain analysis + plots)
│       ├── packing.R        (packing domain analysis + plots)
│       └── vrp.R            (VRP domain analysis + plots)
├── _legacy/
└── _legacy_django/
```

## Related Docs

- Server details: `server/README.md`
- Python runtime details: `python_solvers/README.md`
- Julia solver details: `julia_solvers/README.md`
- R analytics details: `r_solvers/README.md`
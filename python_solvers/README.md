# Python Solvers Runtime

Python optimization runtime for OptiMystic. 

**Architecture Split (Python/Julia Hybrid):**
- **Python-only**: CP scheduling solver and VRP routing solver (OR-Tools)
- **Julia-delegated**: All other domains (MIP, GA, CG, ST, NLP)

See [julia_solvers/README.md](../julia_solvers/README.md) for Julia solver documentation.

## Capabilities: Python-Only (CP/Scheduling)

| Domain | Solver | Backend | Status | Role |
|--------|--------|---------|--------|------|
| **scheduling** | cp | OR-Tools CP-SAT | ✅ Stable | Primary solver for employee shift allocation |
| **vrp** | mip | OR-Tools Routing | ✅ Stable | Vehicle routing with time windows / pickup-delivery |

> All other domains are handled by Julia runtime. See [julia_solvers/](../julia_solvers/) for MIP, GA, CG, ST, NLP implementations.

## Architecture by Layer (Python-Only)

1. **`cli_solver.py`** (Entry point)
   - Routes by `solver_type` parameter
   - If `solver_type=="cp"`: calls `logic_cp.solve_cp_model()`
   - Else: subprocess call to Julia runtime

2. **`domains/scheduling.py`** (Domain normalization)
   - Converts domain params → CP spec (Employees, Shifts, Demands, MaxShifts, etc.)

3. **`logic/logic_cp.py`** (Solver model)
   - Builds OR-Tools CP-SAT model
   - Applies coverage constraints, per-employee shift limits, rules
   - Configures solver options (seed, workers, time_limit)

4. **R post-processing (`r_solvers/`)**
  - Python returns raw optimization JSON
  - R processors/plots handle analytics and visualization in JupyterLab

## Runtime Flow (Python-Only: CP Scheduling)

```
raw params (scheduling domain)
  -> cli_solver.py: route by solver_type
     ├─ if solver_type == "cp"
     │   -> domains/scheduling.py: normalize params → CP spec
     │   -> logic/logic_cp.py: build_model() → solve_cp_model()
    │   -> return JSON (status, objective, variables, constraints)
     │
     └─ else (non-scheduling or non-cp)
         -> subprocess call to julia_solvers/
```

## Quick Start (One Verified Path)

Primary verification path is the JupyterLab full pipeline notebook:

```powershell
cd C:\Users\kevin\OneDrive\Desktop\OptiMystic
\.venv\Scripts\python.exe -m pip install -r python_solvers\requirements.txt
\.venv\Scripts\python.exe -m pip install jupyterlab
jupyter lab
```

Open `examples/test_jupyterlab_full_pipeline.ipynb` and run Python-only / Julia-only / R-only sections.

### Optional: Direct CP CLI check (Python-only path)

```powershell
cd C:\Users\kevin\OneDrive\Desktop\OptiMystic
\.venv\Scripts\python.exe python_solvers\cli_solver.py --domain scheduling --solver cp --params "{\"Employees\":[{\"Name\":\"E1\",\"MaxShifts\":5},{\"Name\":\"E2\",\"MaxShifts\":5}],\"Shifts\":[{\"Name\":\"Morning\",\"Demand\":1}],\"Values\":{\"E1\":{\"Morning\":1},\"E2\":{\"Morning\":1}},\"MaxShiftsPerEmployee\":5}"
```

**Output:**
```json
{
  "status": "Optimal",
  "objective": 3.3,
  "variables": { "Assign_E1_Morning": 1, "Assign_E1_Evening": 0, ... },
  "constraints": { "coverage_Morning": 1, "coverage_Evening": 1, ... },
  "solve_time": 0.042
}
```

> For other domains (cutting, packing, resourcing, generic), the request is delegated to Julia runtime. See [julia_solvers/README.md](../julia_solvers/README.md)).

## Input Contract (Python CP / Julia Delegation)

### For Scheduling (CP-only path)

```json
{
  "template_type": "scheduling",
  "solver_type": "cp",
  "params": {
    "Employees": [
      { "Name": "E1", "MaxShifts": 5, "MinShifts": 1 }
    ],
    "Shifts": [
      { "Name": "Morning", "Demand": 2 },
      { "Name": "Evening", "Demand": 1 }
    ],
    "Values": {
      "E1": { "Morning": 1.0, "Evening": 0.5 }
    },
    "MaxShiftsPerEmployee": 5,
    "MinShiftsPerEmployee": 1,
    "Rules": [],
    "Seed": 42,
    "Workers": 1,
    "TimeLimit": 10
  }
}
```

### For VRP (Python OR-Tools routing)

Use `"template_type": "vrp"` with `"solver_type": "mip"` or another non-`cp` solver value. The Python runtime handles VRP directly.

### For Other Domains (Delegated to Julia)

Other domains should use `"template_type"` matching the domain (`cutting`, `packing`, `resourcing`, `generic`) and solver from {`mip`, `ga`, `cg`, `st`, `nlp`}. Python will spawn a subprocess to Julia runtime.

See [julia_solvers/README.md](../julia_solvers/README.md) for full Julia solver contract and examples.

## Failure & Safety

- Solver dependencies are required at runtime:
  - Pyomo + compatible backend solver for MIP/ST flows.
  - OR-Tools for CP flow.
  - OR-Tools routing for VRP flow.
- Long-running solves are expected to be bounded by Go bridge timeout (`OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS`) at the server layer.
- Results use status-driven handling:
  - `status` indicates success/failure state.
  - `error` and `error_msg` communicate failure cause when solve/build fails.

## Output Shape

CLI prints JSON fields such as:

- `status`
- `objective`
- `variables`
- `constraints`
- `solve_time`
- `details`
- `sensitivity`

Exact populated fields depend on solver/domain path and failure mode.

## Domain Reference (Python-checked Domains)

### scheduling
- **Python Handler**: [domains/scheduling.py](domains/scheduling.py)
- **Solver (Primary)**: CP (OR-Tools)
- **Solver (Fallback)**: MIP (Julia)
- **Expected Input**: Employees, Shifts, Demands, Values, MaxShiftsPerEmployee, MinShiftsPerEmployee, Rules, Seed, Workers, TimeLimit
- **Model**: Binary assignment (Assign_e_s) with coverage and per-employee shift constraints
- **Output**: Assignment matrix, coverage shadow prices, per-employee loads
- **Example**: `/api/optimize?domain=scheduling&solver_type=cp`

### vrp
- **Python Handler**: [domains/vrp.py](domains/vrp.py)
- **Solver**: OR-Tools Routing
- **Expected Input**: Nodes, Vehicles, DistanceMatrix or coordinates, TimeWindows, PickupDeliveries, DropPenalty, TimeLimit
- **Model**: Capacity + time window + pickup/delivery routing
- **Output**: routes, unserved nodes, arrival_times, total distance
- **Example**: `/api/optimize?domain=vrp&solver_type=mip`

### cutting, packing, resourcing, generic
- **Handled by**: Julia runtime
- **Reference**: See [julia_solvers/README.md](../julia_solvers/README.md)
- **Routing**: cli_solver.py detects non-CP/non-VRP requests → subprocess to Julia
- **Output Format**: Standardized JSON with status, objective, variables

> Python performs **no optimization** for non-scheduling/non-VRP domains. It only normalizes input and delegates to Julia.

## How to Extend

1. Add a new domain mapper in `domains/new_domain.py`.
2. For CP domains: add solver logic in `logic/logic_cp_yourdomain.py`.
3. For VRP: extend `domains/vrp.py` and `logic/logic_vrp.py`.
4. For other domains: register in `utils/bridge_logic.py` and Julia will handle via subprocess.
5. Add post-processing rules in `r_solvers/processors.R` if domain-specific analytics are needed.

This separation keeps new optimization types additive without rewriting the full runtime.
# Python Solvers Runtime

Python optimization runtime for OptiMystic. It receives structured optimization inputs, builds solver models, executes them, and returns standardized JSON outputs.

Core design: domain-based mapping + solver-specific logic + shared execution engine.

Recent strengths: CP via OR-Tools (scheduling), ST via Pyomo scenario modeling (resourcing), and `generic` IR-direct solving for extensible custom models.

## Capabilities Matrix

| Domain      | Solver | Status        | Notes |
|-------------|--------|---------------|-------|
| cutting     | mip    | implemented   | IR-driven MIP flow via Pyomo backend |
| packing     | mip    | implemented   | IR-driven MIP flow via Pyomo backend |
| resourcing  | st     | implemented   | Scenario-based stochastic model in `logic/logic_st.py` |
| scheduling  | cp     | implemented   | OR-Tools CP-SAT model in `logic/logic_cp.py` |
| generic     | mip    | implemented   | Direct IR solve path for expert/front-end transformed inputs |
| cutting     | cg     | partial       | Column-generation logic exists; integration depends on use case |
| scheduling  | mip    | partial       | MIP path can be modeled via IR, but CP is the primary path |

## Architecture by Layer

1. `domains/*`  
   Normalize incoming params and produce IR or solver-specific specs (CP/ST).
2. `logic/*`  
   Build solver models by strategy (`logic_mip.py`, `logic_cp.py`, `logic_st.py`, ...).
3. `utils/solver_engine.py`  
   Shared execution engine for IR lists, Pyomo models, and CP wrappers.
4. `utils/services.py`  
   Post-process raw solver output into domain-friendly result payloads.

Routing and orchestration between domain/solver combinations are coordinated in `utils/bridge_logic.py`.

## Runtime Flow

```text
raw params
  -> domain normalization (`domains/*`)
  -> model build (`logic/*`: IR / CP / ST)
  -> solve (`utils/solver_engine.py`)
  -> result shaping (`utils/services.py`)
  -> JSON stdout
```

## Quick Start (cmd.exe)

```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic
pip install -r python_solvers\requirements.txt
```

### 1) MIP example (packing)

```cmd
python python_solvers\cli_solver.py --domain packing --solver mip --params "{\"Items\":[{\"Name\":\"A\",\"Weight\":2,\"Value\":10,\"Demand\":2},{\"Name\":\"B\",\"Weight\":3,\"Value\":12,\"Demand\":1}],\"Vehicles\":[{\"Capacity\":5}],\"Sense\":\"maximize\"}"
```

### 2) CP example (scheduling, OR-Tools)

```cmd
python python_solvers\cli_solver.py --domain scheduling --solver cp --params "{\"Jobs\":[{\"Name\":\"J1\",\"Duration\":3},{\"Name\":\"J2\",\"Duration\":2}],\"Machines\":[{\"Name\":\"M1\"}],\"Sense\":\"minimize\"}"
```

### 3) ST example (resourcing, scenario model)

```cmd
python python_solvers\cli_solver.py --domain resourcing --solver st --params "{\"Resources\":[{\"Name\":\"R1\",\"Capacity\":10}],\"Tasks\":[{\"Name\":\"T1\",\"Demand\":4}],\"Scenarios\":[{\"Name\":\"S1\",\"Probability\":1.0}],\"Sense\":\"minimize\"}"
```

### 4) Generic example (IR direct, mip)

```cmd
python python_solvers\cli_solver.py --domain generic --solver mip --params "{\"IR\":[{\"type\":\"var\",\"name\":\"x\",\"lb\":0},{\"type\":\"objective\",\"sense\":\"maximize\",\"expr\":[[1,\"x\"]]}],\"Sense\":\"maximize\"}"
```

## Input Contract

This runtime consumes structured input, not raw natural language.

- Frontends can provide formula/constraint UI and transform user intent into IR.
- `generic` domain exists for this contract-first flow.
- Domain-specific paths (`cutting`, `packing`, `resourcing`, `scheduling`) map typed params into internal IR/specs.

Minimal contract example:

```json
{
  "template_type": "generic",
  "solver_type": "mip",
  "params": {
    "IR": [
      { "type": "var", "name": "x", "lb": 0 },
      { "type": "objective", "sense": "maximize", "expr": [[1, "x"]] }
    ]
  }
}
```

## Failure & Safety

- Solver dependencies are required at runtime:
  - Pyomo + compatible backend solver for MIP/ST flows.
  - OR-Tools for CP flow.
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

## How to Extend

1. Add a new domain mapper in `domains/new_domain.py`.
2. Add solver logic in `logic/logic_xx.py`.
3. Register routing in `utils/bridge_logic.py`.
4. Add result summarization in `utils/services.py`.

This separation keeps new optimization types additive without rewriting the full runtime.
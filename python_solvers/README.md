# python_solvers

Python optimization runtime used by the Go server.

## Current role

```text
raw params -> domain mapping -> logic model build (IR / CP / ST) -> solver engine -> result processing -> JSON stdout
```

## Important files

```text
python_solvers/
├── cli_solver.py
├── domains/
│   ├── cutting.py
│   ├── packing.py
│   ├── resourcing.py
│   └── scheduling.py
├── logic/
│   ├── logic_cg.py
│   ├── logic_mip.py
│   ├── logic_cp.py
│   ├── logic_st.py
│   └── logic_ga.py
└── utils/
    ├── bridge_logic.py
    ├── services.py
    └── solver_engine.py
```

## Runtime flow

- domain modules normalize inputs
- each domain builds `IR` and, when needed, solver-specific specs such as `CP` or `ST`
- `logic/logic_mip.py` reads the `IR` only
- `logic/logic_cp.py` builds a scheduling CP model for `solver=cp`
- `logic/logic_st.py` builds a stochastic resourcing model for `solver=st`
- `generic` domain accepts expert-provided `IR` directly for custom optimization models
- `utils/solver_engine.py` solves list IR, Pyomo models, and OR-Tools CP wrappers
- `utils/services.py` shapes domain-friendly result payloads

## CLI example

```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic
python python_solvers\cli_solver.py --domain packing --solver mip --params "{\"Items\":[{\"Name\":\"A\",\"Weight\":2,\"Value\":10,\"Demand\":2},{\"Name\":\"B\",\"Weight\":3,\"Value\":12,\"Demand\":1}],\"Vehicles\":[{\"Capacity\":5}],\"Sense\":\"maximize\"}"
```

## Output

The CLI prints JSON with fields such as:

- `status`
- `objective`
- `variables`
- `constraints`
- `solve_time`
- `details`
- `sensitivity`

## Notes

- `CP` for scheduling uses OR-Tools CP-SAT.
- `ST` for resourcing uses a scenario-based Pyomo model.
- `generic` is intended for frontends that transform formula or natural-language inputs into structured IR.
- Runtime success depends on installed Python dependencies and an available Pyomo solver backend for MIP/ST flows.

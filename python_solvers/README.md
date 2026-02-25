# python_solvers/

Pure Python Pyomo optimization solver.

This is a standalone optimization engine called by Go.

## Role

**Pure Calculator**: JSON in → Pyomo execution → JSON out

Go handles all routing, validation, and result processing.

## Structure

```
python_solvers/
├── solver_engine.py          Entry point (called by Go)
├── requirements.txt          Dependencies (Pyomo, Pandas)
│
├── domains/                  Input mapping (4 modules)
│   ├── cutting.py
│   ├── packing.py
│   ├── resourcing.py
│   └── scheduling.py
│
├── logic/                    Pyomo models (5 modules)
│   ├── logic_cg.py           ✅ Column Generation
│   ├── logic_mip.py          ✅ Mixed Integer
│   ├── logic_cp.py           ⏳ Constraint (stub)
│   ├── logic_st.py           ⏳ Stochastic (stub)
│   └── logic_nlp.py          ⏳ Non-Linear (stub)
│
└── utils/                    Internal utilities
    ├── bridge_logic.py       Domain + solver selection
    ├── services.py           Result processing (Go calls this)
    └── solver_engine.py      Pyomo execution engine
```

## Usage

Go server calls:

```bash
python python_solvers/cli_solver.py \
  --domain cutting \
  --solver mip \
  --params '{"Items": ["A"], ...}'
```

Output: JSON (raw result, no post-processing)

## Notes

- Go handles routing, validation, result processing
- Python only performs pure calculation
- No Django dependency (pure Python)
- Reference original code: `_legacy_django/ORIGINAL_services.py`
# OptiMystic

Multi-domain optimization API with cutting, packing, resourcing, and scheduling domains.

## Architecture

**Flow:** `Bridge` → `Domain` → `Logic` → `Solver` → `Services`

1. **Bridge** (`core/utils/bridge_logic.py`)  
   - Selects domain and solver type  
   - Routes to appropriate modules  

2. **Domains** (`core/domains/`)  
   - `cutting.py`, `packing.py`, `resourcing.py`, `scheduling.py`  
   - Maps raw input to common schema  

3. **Logic** (`core/logic/`)  
   - `logic_cg.py`: Column generation (cutting)  
   - `logic_mip.py`: Mixed-integer programming (all domains)  
   - `logic_cp.py`, `logic_st.py`, `logic_nlp.py`: Stubs (future)  

4. **Solver** (`core/utils/solver_engine.py`)  
   - Executes Pyomo models  
   - Extracts duals (LP only)  

5. **Services** (`core/utils/services.py`)  
   - Domain-specific dashboards  
   - Sensitivity analysis (LP/CG only)  

## Quick Demo

```bash
python scripts/demo_optimize.py
```

## Notes

- Sensitivity requires LP solvers (MIP returns "unsupported")  
- Set `"Relax": true` in payload to solve LP relaxation for sensitivity
- CBC must be installed: ensure Pyomo can find CBC solver


# OptiMystic

Multi-domain optimization API with cutting, packing, resourcing, and scheduling domains.

## What it is (current state)

- Python backend that maps domain-specific inputs to optimization logic and solves with Pyomo
- Supports cutting (CG/MIP) plus basic MIP models for packing, resourcing, and scheduling
- Produces standardized outputs: objective value, variables, constraints, solver status, and solve time

## Architecture

**Flow:** `Bridge` → `Domain` → `Logic` → `Solver` → `Services`

1. **Bridge** (`core/utils/bridge_logic.py`)  
   - Selects domain and solver type  
   - Routes to appropriate modules  

2. **Domains** (`core/domains/`)  
   - `cutting.py`, `packing.py`, `resourcing.py`, `scheduling.py`  
   - Maps raw input to common schema  

3. **Logic** (`core/logic/`)  
   - `logic_cg.py`: Column generation for cutting (master + pricing)  
   - `logic_mip.py`: MIP models for cutting, packing, resourcing, scheduling  

4. **Solver** (`core/utils/solver_engine.py`)  
   - Executes Pyomo models (CBC)  
   - Extracts objective, variables, constraints, and solve time  

5. **Services** (`core/utils/services.py`)  
   - Domain-specific dashboards  
   - Sensitivity analysis for LP only  

## Current domains

- **Cutting**: column generation + MIP alternative
- **Packing**: 1D knapsack (MIP/LP)
- **Resourcing**: 2D knapsack (CPU/RAM) (MIP/LP)
- **Scheduling**: basic shift coverage (MIP/LP)

## Requirements

- Python 3.x
- Pyomo
- CBC solver available to Pyomo

## Quick demo

```bash
python scripts/demo_optimize.py
```

## Notes

- Sensitivity requires LP solvers (MIP returns "unsupported")  
- Set `"Relax": true` in payload to solve LP relaxation for sensitivity  
- CBC must be installed and discoverable by Pyomo
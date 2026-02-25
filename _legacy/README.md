# Legacy Backup (Archive)

Original code before migration from **Dash + PuLP** to **Django/Go + Pyomo**.  
Kept for reference and historical record.

## Files in This Folder

| File | Role | After Migration |
|------|------|-----------------|
| `analytics_cutting.py` | Dash UI + data parsing/result processing | `core/utils/services.py` (logic only), UI removed |
| `app.py` | Dash app entry, layout | Django `core/views` + API (separate app) |
| `bridge_logic.py` | Cutting-specific bridge | `core/utils/bridge_logic.py` (expanded for 4 industries) |
| `global_callbacks.py` | Dash callbacks | Handled in Django views |
| `logic_cutting.py` | Cutting MIP (PuLP) | `core/logic/logic_mip.py` (Pyomo) |
| `logic_cg.py` | Column generation (PuLP) | `core/logic/logic_cg.py` (Pyomo) |
| `solver_engine.py` | PuLP build/solve | `core/utils/solver_engine.py` (Pyomo + Auto-Selector) |
| `styles.py` | Dash CSS/styles | Implement in separate frontend |

## Usage

**Reference & Source Verification**: Original formulas and algorithms are in this code.

**If you want to run Dash again**: Execute `app.py` and add this folder path to PYTHONPATH, or import from project root.

**Current service runs on `python_solvers/` + Go server. This folder does not need modification.**
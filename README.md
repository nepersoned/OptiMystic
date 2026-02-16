# OptiMystic

🚀 **Multi-Domain Optimization API** – Solving cutting, packing, resourcing, and scheduling problems with Pyomo

Transforms business optimization problems into mathematical models and solves them using state-of-the-art optimization algorithms (Column Generation, MIP, LP).

## ✨ What It Does

- **Cutting Stock Optimization**: Minimize material waste and cost (Column Generation + MIP)
- **Packing/Knapsack**: Maximize value within weight/capacity constraints (MIP/LP)
- **Resource Allocation**: Distribute limited CPU/RAM across tasks (2D Knapsack)
- **Shift Scheduling**: Cover shift demand with minimum employees (MIP/LP)

## 🏗️ Architecture

```
User Input → Bridge → Domain → Logic → Pyomo Solver → Services → Result
```

| Layer | Module | Purpose |
|-------|--------|---------|
| **Bridge** | `core/utils/bridge_logic.py` | Domain & solver type selector |
| **Domains** | `core/domains/*.py` | Input schema mapping & validation |
| **Logic** | `core/logic/logic_{cg,mip,cp,st,nlp}.py` | Mathematical model builders |
| **Solver** | `core/utils/solver_engine.py` | Pyomo orchestration & CBC execution |
| **Services** | `core/utils/services.py` | Result parsing, sensitivity analysis, dashboards |

## 🎯 Supported Domains

| Domain | Algorithms | Input Format | Output |
|--------|-----------|--------------|--------|
| **Cutting** | CG, MIP | Items, lengths, demands, stocks, kerf | Cutting patterns, cost, waste |
| **Packing** | MIP, LP | Items, weights, values, capacity, demands | Selection, utilization % |
| **Resourcing** | MIP, LP | Tasks, CPU, RAM, capacity, demands, values | Task allocation, resource usage |
| **Scheduling** | MIP, LP | Employees, shifts, demands, max assignments | Shift assignments, coverage |

## 🔧 Setup

### Requirements

```
Python 3.8+
Django 4.2+
Pyomo 6.0+
CBC Solver (auto-installed with Pyomo)
Pandas (for sensitivity analysis)
```

### Install

```bash
# Clone or navigate to project
cd OptiMystic

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify CBC is available
pyomo --version
```

## 🚀 Quick Start

### 1. Run Demo (All Domains)

```bash
python scripts/demo_optimize.py
```

Expected output: JSON with results for cutting, packing, resourcing, and scheduling.

### 2. Use as Django API

```bash
python manage.py runserver
```

POST to `/api/optimize/`:
```json
{
  "template_type": "cutting",
  "params": {
    "Items": ["A", "B"],
    "ItemLens": [4, 6],
    "Demands": {"A": 2, "B": 1},
    "Stocks": [{"Name": "S1", "Length": 10, "Cost": 5}],
    "Kerf": 0,
    "Sense": "minimize"
  }
}
```

Response:
```json
{
  "status": "Optimal",
  "objective": 10.0,
  "variables": [...],
  "constraints": [...],
  "dashboard": {...},
  "sensitivity": {...}
}
```

### 3. Use as Python Library

```python
from core.utils import bridge_logic, solver_engine, services

# Map inputs
mapped = bridge_logic.map_params_by_mode("cutting", params)

# Generate model
obj, constraints, vars_config = bridge_logic.generate_logic("cutting", params)

# Solve
store = {"variables": vars_config, "parameters": services.build_parameter_store(mapped)}
result = solver_engine.solve_model(store, "minimize", obj, constraints)

# Process results
dashboard = services.process_results(result, store, "cutting")
sensitivity = services.process_sensitivity(result, store, "cutting")
```

## 📊 Features

✅ **Multiple Solvers**: CG (cutting), MIP (all domains), LP relaxation  
✅ **Sensitivity Analysis**: Dual values, shadow prices, bottleneck identification  
✅ **Domain Aliases**: Backward compatibility (manufacturing→cutting, logistics→packing, hr→scheduling)  
✅ **REST API**: Django endpoints for web/mobile integration  
✅ **Flexible Output**: JSON dashboards per domain + raw solver data  

## ⚙️ Configuration

### Enable LP Sensitivity
Add `"Relax": true` to payload to solve LP relaxation for sensitivity analysis:

```json
{
  "template_type": "packing",
  "params": {
    "Items": ["Box1", "Box2"],
    "Weights": [3, 5],
    "Values": [6, 10],
    "Capacity": 10,
    "Relax": true
  }
}
```

### Solver Timeout
Edit `core/utils/solver_engine.py` → `solve_model()` to change CBC timeout (default: 10s)

## 📁 Project Structure

```
OptiMystic/
├── core/
│   ├── domains/           # Input mappers
│   │   ├── cutting.py
│   │   ├── packing.py
│   │   ├── resourcing.py
│   │   └── scheduling.py
│   ├── logic/             # Model builders
│   │   ├── logic_cg.py    # Column generation
│   │   ├── logic_mip.py   # Mixed integer programming
│   │   ├── logic_cp.py    # (Placeholder) Constraint programming
│   │   ├── logic_nlp.py   # (Placeholder) Non-linear programming
│   │   └── logic_st.py    # (Placeholder) Stochastic optimization
│   ├── utils/
│   │   ├── bridge_logic.py     # Router
│   │   ├── solver_engine.py    # Pyomo wrapper
│   │   └── services.py         # Result processing
│   ├── views.py           # Django endpoints
│   └── urls.py
├── optimystic/            # Django config
├── scripts/
│   └── demo_optimize.py   # Quick demo
├── _legacy/               # Reference (PuLP-based, Dash UI)
└── requirements.txt
```

## 🔮 Future Roadmap

- [ ] **C++ Performance Layer** - Hot-path optimization for large-scale problems
- [ ] **JavaScript/TypeScript Client** - Web-based optimization interface
- [ ] Constraint Programming (CP) for complex scheduling
- [ ] Stochastic Optimization (ST) for uncertainty
- [ ] Non-Linear Programming (NLP) for non-linear objectives
- [ ] Web UI (React/Vue)
- [ ] Result visualization dashboard
- [ ] Multi-solve (Pareto frontier)

## 📝 Notes

- **LP Sensitivity**: Only available for LP models. Set `"Relax": true` for MIP relaxation.
- **CBC Solver**: Must be installed. Included with Pyomo by default.
- **Pyomo Models**: All solvers return Pyomo ConcreteModel or structured lists.
- **Variable Naming**: CG uses `A_IT<i>_<bin>` (items), MIP uses `X_<i>` or `Cut_<item>_<bin>`.
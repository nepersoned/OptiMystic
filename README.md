# OptiMystic

**Multi-Domain Optimization API**

Transforms business optimization problems into mathematical models and solves them using state-of-the-art optimization algorithms (Column Generation, MIP, LP, NLP).

**Status:** Python Solver Production Ready | Go Server In Progress
**Limitations:** Go HTTP API is a stub; use the Python solver directly for now.

---

## What It Does

| Problem                | Algorithm                | Input                | Output                |
|------------------------|-------------------------|----------------------|-----------------------|
| Cutting Stock          | Column Generation + MIP | Items, lengths, demands, stocks, kerf | Cutting patterns, cost, waste |
| Packing/Knapsack       | MIP/LP                  | Items, weights, values, capacity | Selection, utilization % |
| Resource Allocation    | MIP/LP                  | Tasks, CPU, RAM, capacity | Task allocation, usage |
| Shift Scheduling       | MIP/LP                  | Employees, shifts, demands | Assignments, coverage |

---

## Architecture

```
HTTP Request (JSON)
    ↓
Go Server (Entry Layer)
├─ server/cmd/server/main.go
├─ server/internal/handlers/
└─ server/internal/router/
    ↓
Bridge (Command Layer)
├─ server/internal/solver/bridge.go
└─ python_solvers/utils/bridge_logic.py
    ↓
Python Solver (Logic + Output Layer)
├─ python_solvers/domains/       (input mapping)
├─ python_solvers/logic/         (Pyomo models)
└─ python_solvers/utils/         (solver execution + result processing)
    ↓
JSON Response
```

---

## Technology Stack

| Layer         | Technology         | Status         |
|---------------|--------------------|---------------|
| API Server    | Go 1.21+ (net/http)| In Progress   |
| Optimization  | Python 3.8+        | Complete      |
| Solver        | Pyomo 6.7+ (CBC)   | Complete      |
| Data          | JSON (stdin/stdout)| Complete      |

---

## Project Structure

```
OptiMystic/
├── python_solvers/          Python Pyomo Solver
│   ├── solver_engine.py     Pyomo execution engine
│   ├── requirements.txt
│   │
│   ├── domains/             input mapping
│   │   ├── cutting.py
│   │   ├── packing.py
│   │   ├── resourcing.py
│   │   └── scheduling.py
│   │
│   ├── logic/               mathematical models
│   │   ├── logic_cg.py      Column Generation
│   │   ├── logic_mip.py     Mixed Integer
│   │   ├── logic_cp.py      Constraint
│   │   ├── logic_st.py      Stochastic
│   │   └── logic_nlp.py     Non-Linear
│   │
│   └── utils/
│       ├── bridge_logic.py  domain/solver selection
│       └── services.py      result processing
│
├── server/                  Go HTTP Server
│   ├── cmd/server/main.go
│   └── internal/
│       ├── handlers/        optimize, health
│       ├── router/
│       ├── services/        results_cutting, results_packing, results_resourcing, results_scheduling
│       └── solver/          Python call
│
├── _legacy_django/          Django backup
├── _legacy/                 Original Dash app
├── scripts/                 Python scripts
└── docs/                    Documentation
```

---

## System Architecture

Below is the overall data flow and layer structure of the OptiMystic Go server and Python solver. All domains (cutting, packing, resourcing, scheduling) are handled at the same domain layer.

```
+-------------------------------+
| server/cmd/server/main.go     |  # Server entry point
+---------------+---------------+
                |
                v
+-------------------------------+
| server/internal/router/router |  # Route registration
+---------------+---------------+
                |
        +-------+-------------------+
        |                           |
        v                           v
+------------------------+   +----------------------------+
| handlers/health.go     |   | handlers/optimize.go       |  # HTTP handlers
+------------------------+   +-------------+--------------+
                                          |
                                          v
                               +----------------------------+
                               | models/optimization.go     |  # Data structures
                               +-------------+--------------+
                                          |
                                          v
                               +----------------------------+
                               | solver/bridge.go           |  # Go ↔ Python bridge
                               +-------------+--------------+
                                          |
                                          v
                               +----------------------------+
                               | python_solvers/cli_solver  |  # Python solver CLI
                               +-------------+--------------+
                                          |
                                          v
                               +----------------------------+
                               | utils/bridge_logic.py      |  # Bridge logic
                               +-------------+--------------+
                                          |
        +----------------------+----------+----------+----------+
        |                      |          |          |          |
        v                      v          v          v          v
+------------------+  +------------------+  +------------------+  +------------------+
| domains/cutting  |  | domains/packing  |  | domains/resourcing|  | domains/scheduling|  # Domain logic
+------------------+  +------------------+  +------------------+  +------------------+
        |                      |                     |                      |
        +-----------+----------+----------+----------+----------+-----------+
                    |                     |                     |
                    v                     v                     v
          +------------------+   +------------------+   +------------------+
          | logic/logic_cg   |   | logic/logic_mip  |   | logic/logic_cp   |  # Solver logic
          +------------------+   +------------------+   +------------------+
                    |                     |                     |
                    +-----------+---------+---------+-----------+
                                |
                                v
                   +----------------------------+
                   | utils/solver_engine.py     |  # Solver engine
                   +-------------+--------------+
                                 |
                                 v
                   +----------------------------+
                   | utils/services.py          |  # Service utilities
                   +-------------+--------------+
                                 |
                                 v
                   +----------------------------+
                   | solver/bridge.go (result)  |  # Bridge result
                   +-------------+--------------+
                                 |
                                 v
                   +----------------------------+
                   | services/results.go        |  # Result processing
                   +------+------+------+-------+
                          |      |      |      |
                          v      v      v      v
          +----------------+ +----------------+ +---------------------+ +---------------------+
          | results_cutting| | results_packing| | results_resourcing  | | results_scheduling  |  # Domain-specific results
          +----------------+ +----------------+ +---------------------+ +---------------------+
```

- main.go: Server entry point, router initialization
- router.go: Endpoint routing
- handlers: Request handling (health, optimize, etc.)
- models: Data structure definitions
- bridge.go: Go ↔ Python bridge
- python_solvers: Actual optimization and domain logic
- services/results.go: Result processing and domain dispatch
- results_*.go: Final domain-specific result generation

---

## Quick Start

### Prerequisites
Python 3.8+
pip / pipenv
Go 1.21+ (optional)

### Installation

1. Clone Repository
   git clone https://github.com/yourusername/optimystic.git
   cd optimystic
2. Setup Python Environment
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r python_solvers/requirements.txt
3. Test Python Solver
   python python_solvers/cli_solver.py --domain cutting --solver mip --params '{...}'

---

## Usage Examples

### Python Solver (Direct)

#### Cutting Stock Problem
```python
from python_solvers.utils import bridge_logic, solver_engine, services

params = {
    "Items": ["A", "B"],
    "Weights": [4, 6],
    "Demands": {"A": 2, "B": 1},
    "Stocks": [{"Name": "S1", "Length": 10, "Cost": 5}],
    "Kerf": 0,
    "Sense": "minimize"
}

# Map params
mapped = bridge_logic.map_params_by_mode("cutting", params)

# Build model
obj, const, vars_config = bridge_logic.generate_logic("cutting", params)

# Solve
store_data = {
    "variables": vars_config,
    "parameters": services.build_parameter_store(mapped)
}
result = solver_engine.solve_model(store_data, "minimize", obj, const)

# Process results
dashboard = services.process_results(result, store_data, "cutting")
sensitivity = services.process_sensitivity(result, store_data, "cutting")
```

#### Packing Problem
```python
params = {
    "Items": ["Item1", "Item2", "Item3"],
    "Weights": [10, 20, 15],
    "Values": [100, 150, 120],
    "Capacity": 40,
    "Sense": "maximize"
}
# Same flow as above with domain="packing"
```

---

## Supported Domains

| Domain                | Algorithm                | Input                | Output                |
|-----------------------|-------------------------|----------------------|-----------------------|
| Cutting Stock         | Column Generation + MIP | Items, lengths, demands, stocks, kerf | Cutting patterns, cost, waste |
| Packing/Knapsack      | MIP/LP                  | Items, weights, values, capacity | Selection, utilization % |
| Resource Allocation   | MIP/LP                  | Tasks, CPU, RAM, capacity | Task allocation, usage |
| Shift Scheduling      | MIP/LP                  | Employees, shifts, demands | Assignments, coverage |

---

## Solver Algorithms

| Algorithm                | Status         | Domains         | Notes         |
|-------------------------|---------------|----------------|--------------|
| Column Generation (CG)  | Complete      | Cutting        | Optimal solution guaranteed |
| Mixed Integer Programming (MIP) | Complete      | All            | General purpose, stable |
| Constraint Programming (CP) | In Progress   | Scheduling     | For constraint-heavy problems |
| Stochastic (ST)         | In Progress   | All            | Handles uncertainty |
| Non-Linear (NLP)        | In Progress   | Packing, Resourcing | For non-linear objectives |

---

## Configuration

### Environment Variables
PYOMO_SOLVER=cbc
DEBUG=False

### Python Requirements
pyomo==6.7.3        # Optimization engine
pandas==2.0.3       # Data processing
numpy==1.24.3       # Numerical computing

---

## Performance

| Problem Type           | Size         | Time         | Status         |
|------------------------|--------------|--------------|---------------|
| Cutting Stock          | 10 items, 5 stocks | < 1s        | Optimal      |
| Packing                | 50 items     | 2-5s         | Optimal       |
| Resourcing             | 100 tasks    | 1-3s         | Optimal       |
| Scheduling             | 20 employees, 30 shifts | 0.5-2s      | Optimal      |

---

## Deployment

### Local Testing (Python Only)
python python_solvers/cli_solver.py --domain cutting --solver mip --params '{...}'

### Go Server (Coming Soon)
cd server
go build -o ./bin/optimystic-server cmd/server/main.go
./bin/optimystic-server

### Docker (Planned)
docker build -t optimystic .
docker run -p 8000:8000 optimystic

---

## Documentation

| Document                | Purpose         |
|-------------------------|----------------|
| FINAL_STRUCTURE.md      | Complete file structure |
| MIGRATION_COMPLETE.md   | Migration completion report |
| MIGRATION_SUMMARY.md    | Final summary   |
| FINAL_STATUS.md         | Current status  |

---

## Development Roadmap

### Phase 1: Python Solver (Complete)
- [x] Column Generation
- [x] Mixed Integer Programming
- [x] Domain input mapping (4 domains)
- [x] Result processing & sensitivity analysis
- [x] Dashboard generation

### Phase 2: Go Server (Complete)
- [x] HTTP server setup
- [x] Request handlers (/api/optimize/, /api/health/)
- [x] Python subprocess invocation
- [x] JSON marshaling
- [x] Error handling & logging
- [x] Unit & integration tests

### Phase 3: Advanced Features
- [ ] Constraint Programming solver
- [ ] Stochastic optimization
- [ ] Non-Linear solver
- [ ] Web Dashboard (React)
- [ ] Database integration
- [ ] Docker & Kubernetes deployment
- [ ] CI/CD pipeline (GitHub Actions)

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## References

- [Pyomo Documentation](https://pyomo.readthedocs.io/)
- [CBC Solver](https://github.com/coin-or/Cbc)
- [Go Documentation](https://golang.org/doc/)

---

**Last Updated**: February 24, 2026 | **Status**: Python Solver Complete | Go Server In Progress
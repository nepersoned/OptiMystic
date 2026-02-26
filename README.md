# OptiMystic

**Multi-Domain Optimization API**

Transforms business optimization problems into mathematical models and solves them using state-of-the-art optimization algorithms (Column Generation, MIP, LP, NLP).


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
| API Server    | Go 1.21+ (net/http)| Complete      |
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

## References

- [Pyomo Documentation](https://pyomo.readthedocs.io/)
- [CBC Solver](https://github.com/coin-or/Cbc)
- [Go Documentation](https://golang.org/doc/)


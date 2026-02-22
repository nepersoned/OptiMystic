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

## 🧭 Go Hybrid Migration (Entry / Command / Exit)

**Status**: 🟡 Planning Phase - Django will be replaced with Go

This project is transitioning to a **Go-first architecture** while keeping Pyomo models intact.

### 3 Layers = 5 Django Files → Go

| Layer | Django Files (2개 이상) | Go Replacement | Purpose |
|-------|------------------------|----------------|---------|
| **Entry** | `core/views.py`<br>`core/urls.py`<br>`optimystic/urls.py`<br>`optimystic/wsgi.py` | `cmd/server/main.go`<br>`internal/handlers/optimize.go`<br>`internal/router/router.go` | HTTP server, request handling, URL routing |
| **Command** | `core/utils/bridge_logic.py` | `internal/solver/bridge.go` | Domain selection & solver orchestration |
| **Exit** | *(stays in Python)*<br>`core/utils/services.py` | `python_solvers/utils/services.py`<br>+ Go JSON marshaling | Result processing & dashboard (called by Go via subprocess) |

### Detail Breakdown

#### Entry Layer (4 Django files → 3 Go files)
- `optimystic/wsgi.py` → `cmd/server/main.go` (서버 시작점)
- `optimystic/urls.py` + `core/urls.py` → `internal/router/router.go` (URL 라우팅 통합)
- `core/views.py` → `internal/handlers/optimize.go` + `internal/handlers/health.go` (요청 처리)

#### Command Layer (1 Django file → 1 Go file)
- `core/utils/bridge_logic.py` → `internal/solver/bridge.go` (도메인 선택 로직)

#### Exit Layer (Python 유지)
- `core/utils/services.py` → `python_solvers/utils/services.py` (결과 파싱, 대시보드)
- Go는 Python subprocess 호출 후 JSON 결과만 클라이언트에게 전달

### JSON Request/Response

- **Input**: JSON in, with Go structs for fast and safe decoding.
- **Output**: JSON out, matching existing dashboard expectations.

### Concurrency Strategy

- Use Go **goroutines** so multiple optimization requests are handled concurrently without blocking the server.
- Django's single-threaded nature will be replaced with Go's native concurrency.

### Pyomo Execution Strategy

- Keep Python models under `core/logic/` unchanged.
- Go invokes Python solver via `os/exec` (e.g., `solver_engine.py`) and captures stdout as JSON result.
- Python remains essential for Pyomo optimization - only the HTTP/API layer moves to Go.

### Migration Scope

- **Keep in Python**: All Pyomo models and solver logic in `core/logic/`, `core/domains/`, `core/utils/`.
- **Move to Go**: Entry + Command + Exit layers (HTTP handlers, routing, JSON marshaling).
- **Django Status**: Will remain for reference during migration, then archived to `_legacy_django/`.

### Django → Go File Mapping (5개 파일)

| Layer | # | Django File | Go Replacement | Action |
|-------|---|-------------|----------------|--------|
| **Entry** | 1 | `optimystic/wsgi.py` | `cmd/server/main.go` | Replace: Server entry point |
| **Entry** | 2 | `optimystic/urls.py` | `internal/router/router.go` | Replace: Root URL config |
| **Entry** | 3 | `core/urls.py` | `internal/router/router.go` | Merge: API URL config |
| **Entry** | 4 | `core/views.py` | `internal/handlers/*.go` | Replace: Request handlers |
| **Command** | 5 | `core/utils/bridge_logic.py` | `internal/solver/bridge.go` | Rewrite: Domain routing |

### Python Files to Copy (변경 없이 이동)

| Category | Files | New Location | Purpose |
|----------|-------|--------------|---------|
| **Domains** | `core/domains/*.py` | `python_solvers/domains/` | Input mapping (4 files) |
| **Logic** | `core/logic/*.py` | `python_solvers/logic/` | Pyomo models (5 files) |
| **Utils** | `core/utils/solver_engine.py` | `python_solvers/utils/` | Pyomo solver wrapper |
| **Utils** | `core/utils/services.py` | `python_solvers/utils/` | Result processing |

**Exit Layer**: `services.py`는 Python에 그대로 두고, Go가 subprocess로 호출

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

### Current (Django - Active)

```
OptiMystic/
├── core/                  # Django app (will be archived)
│   ├── domains/           # Input mapper (will be copied to python_solvers/)
│   │   ├── cutting.py     # Cutting stock domain
│   │   ├── packing.py     # Packing/knapsack domain
│   │   ├── resourcing.py  # Resource allocation domain
│   │   └── scheduling.py  # Shift scheduling domain
│   ├── logic/             # Model builders (will be copied to python_solvers/)
│   │   ├── logic_cg.py    # Column generation
│   │   ├── logic_mip.py   # Mixed integer programming
│   │   ├── logic_cp.py    # Constraint programming
│   │   ├── logic_nlp.py   # Non-linear programming
│   │   └── logic_st.py    # Stochastic optimization
│   ├── utils/             # Core utilities (will be copied to python_solvers/)
│   │   ├── bridge_logic.py     # Domain router (will be rewritten in Go)
│   │   ├── solver_engine.py    # Pyomo solver wrapper
│   │   └── services.py         # Result processing & dashboards
│   ├── views.py           # Django API endpoints (will be replaced by Go handlers)
│   ├── urls.py            # URL routing (will be replaced by Go router)
│   └── models.py          # Database models
├── optimystic/            # Django project config (will be archived)
├── _legacy/               # Original Dash UI (archived)
├── manage.py              # Django management
└── requirements.txt       # Python dependencies (Pyomo only after migration)
```

### Future (Go + Python Hybrid - Planned)

```
OptiMystic/
├── cmd/
│   └── server/
│       └── main.go              # Go HTTP server entry point
├── internal/
│   ├── handlers/                # HTTP request handlers (replaces Django views)
│   │   ├── health.go
│   │   └── optimize.go
│   ├── models/                  # Go structs for JSON
│   │   └── models.go
│   ├── solver/                  # Python subprocess wrapper
│   │   └── solver.go
│   └── router/                  # HTTP routing (replaces Django urls)
│       └── router.go
├── python_solvers/              # Python optimization modules (from core/)
│   ├── domains/                 # Input mapping
│   ├── logic/                   # Pyomo model builders
│   ├── utils/                   # Solver engine, services
│   └── solver_cli.py            # CLI entry point for Go to call
├── _legacy_django/              # Archived Django implementation
│   ├── core/
│   ├── optimystic/
│   └── manage.py
├── go.mod                       # Go module definition
├── go.sum                       # Go dependencies
└── requirements.txt             # Python dependencies (Pyomo, pandas)
```

## 🐳 Deployment

### Current: Django + Gunicorn

#### Docker

```bash
# Build image
docker build -t optimystic:latest .

# Run container
docker run -p 8080:8080 optimystic:latest

# Test
curl http://localhost:8080/api/health/
```

#### Production (Gunicorn)

```bash
# Install production dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run with Gunicorn
gunicorn --bind 0.0.0.0:8080 --workers 4 --timeout 300 optimystic.wsgi:application
```

### Future: Go + Python Hybrid

```bash
# Build Go binary
go build -o optimystic-server cmd/server/main.go

# Run server (Python must be available in PATH)
./optimystic-server

# Or with Docker (multi-stage build)
docker build -f Dockerfile.go -t optimystic-go:latest .
docker run -p 8080:8080 optimystic-go:latest
```

## 🚀 Why Go?

### Performance Benefits
1. **Concurrency**: Handle 1000+ optimization requests simultaneously with goroutines
2. **Fast Startup**: <10ms server startup vs Django's ~500ms
3. **Low Memory**: ~20MB baseline vs Django's ~100MB
4. **Single Binary**: No virtual environments, dependencies bundled

### Operational Benefits
1. **Type Safety**: Compile-time checking for JSON schemas prevents runtime errors
2. **Easy Deployment**: Single binary = simpler CI/CD
3. **Better Monitoring**: Built-in pprof for profiling
4. **Native Concurrency**: No GIL issues like Python

### Why Not Full Go?
- **Pyomo Ecosystem**: 10+ years of optimization research, impossible to rewrite
- **Mathematical Modeling**: Python's expressiveness ideal for complex models
- **Community**: Pyomo has extensive documentation and community support
- **Hybrid Best**: Go for speed (HTTP), Python for math (Pyomo)

## 🔧 Environment Variables

## 🔧 Environment Variables

### Django (Current)

```bash
# .env file
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### Go (Future)

```bash
# .env file
PORT=8080
GIN_MODE=release
PYTHON_PATH=/usr/bin/python3
SOLVER_TIMEOUT=300
LOG_LEVEL=info
```

---

## 📊 Migration Status

| Component | Django (Current) | Go (Future) | Status |
|-----------|-----------------|-------------|--------|
| HTTP Server | ✅ Django/Gunicorn | 🔜 Gin/Echo | Planning |
| Request Validation | ✅ Django Forms | 🔜 Go Structs | Planning |
| Routing | ✅ Django URLs | 🔜 Go Router | Planning |
| Pyomo Solvers | ✅ Direct Import | 🔜 Subprocess | Planning |
| Concurrency | ⚠️ Limited (Workers) | 🔜 Goroutines | Planned |
| Type Safety | ⚠️ Runtime | 🔜 Compile-time | Benefit |
| Deployment | ✅ Docker + Gunicorn | 🔜 Single Binary | Benefit |

**Current Focus**: Django is stable and production-ready. Go migration will begin after feature freeze.

---

## 🔮 Future Roadmap

### Phase 1: Go Migration (In Progress)
- [ ] **Go HTTP Server** - Replace Django with Gin/Echo framework
- [ ] **Go ↔ Python Bridge** - Subprocess wrapper for Pyomo solvers
- [ ] **Goroutine Concurrency** - Parallel optimization request handling
- [ ] **Type-Safe JSON** - Go structs for request/response validation

### Phase 2: Performance & Features
- [ ] **C++ Performance Layer** - Hot-path optimization for large-scale problems (optional)
- [ ] **JavaScript/TypeScript Client** - Web-based optimization interface
- [ ] Constraint Programming (CP) for complex scheduling
- [ ] Stochastic Optimization (ST) for uncertainty modeling
- [ ] Non-Linear Programming (NLP) for non-linear objectives

### Phase 3: Production Features
- [ ] Web UI (React/Vue) with real-time updates
- [ ] Result visualization dashboard with charts
- [ ] Multi-objective optimization (Pareto frontier)
- [ ] Batch processing API for large-scale problems
- [ ] Optimization job queue with Redis/RabbitMQ

## 📝 Notes

- **LP Sensitivity**: Only available for LP models. Set `"Relax": true` for MIP relaxation.
- **CBC Solver**: Must be installed. Included with Pyomo by default.
- **Pyomo Models**: All solvers return Pyomo ConcreteModel or structured lists.
- **Variable Naming**: CG uses `A_IT<i>_<bin>` (items), MIP uses `X_<i>` or `Cut_<item>_<bin>`.
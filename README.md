# OptiMystic

🚀 **Multi-Domain Optimization API** – Solving cutting, packing, resourcing, and scheduling problems with Pyomo + Go

Transforms business optimization problems into mathematical models and solves them using state-of-the-art optimization algorithms (Column Generation, MIP, LP, NLP).

🚀 **다중 도메인 최적화 API** – Pyomo + Go를 활용한 절단, 포장, 리소스, 스케줄링 문제 해결

비즈니스 최적화 문제를 수학 모델로 변환하고 최신 최적화 알고리즘(Column Generation, MIP, LP, NLP)으로 해결합니다.

**Status**: ✅ **Python Solver Production Ready** | ⏳ **Go Server In Progress**

**상태**: ✅ **Python 솔버 운영 준비 완료** | ⏳ **Go 서버 개발 중**

**Limitations**: Go HTTP API is a stub; use the Python solver directly for now.

**제한사항**: Go HTTP API는 스텁 상태이며, 현재는 Python 솔버를 직접 사용하세요.

---

## ✨ What It Does

| Problem | Algorithm | Input | Output |
|---------|-----------|-------|--------|
| **Cutting Stock** 📦 | Column Generation + MIP | Items, lengths, demands, stocks, kerf | Cutting patterns, cost, waste |
| **Packing/Knapsack** 📊 | MIP/LP | Items, weights, values, capacity | Selection, utilization % |
| **Resource Allocation** 💻 | MIP/LP | Tasks, CPU, RAM, capacity | Task allocation, usage |
| **Shift Scheduling** 👥 | MIP/LP | Employees, shifts, demands | Assignments, coverage |

## 어떤 기능인가요

| 문제 | 알고리즘 | 입력 | 출력 |
|------|---------|------|------|
| **절단 재고** 📦 | Column Generation + MIP | 품목, 길이, 수요, 원재료, 절단손실 | 절단 패턴, 비용, 폐기물 |
| **포장/나사** 📊 | MIP/LP | 품목, 무게, 가치, 용량 | 선택, 활용률 |
| **리소스 할당** 💻 | MIP/LP | 작업, CPU, RAM, 용량 | 작업 배분, 사용률 |
| **교대 스케줄** 👥 | MIP/LP | 직원, 교대, 수요 | 배정, 커버율 |

---

## 🏗️ Architecture

### **Layered Design**

```
HTTP Request (JSON)
    ↓
🚀 Go Server (Entry Layer)
├─ server/cmd/server/main.go
├─ server/internal/handlers/
└─ server/internal/router/
    ↓
🔗 Bridge (Command Layer)
├─ server/internal/solver/bridge.go
└─ python_solvers/utils/bridge_logic.py
    ↓
🐍 Python Solver (Logic + Output Layer)
├─ python_solvers/domains/       (input mapping)
├─ python_solvers/logic/         (Pyomo models)
└─ python_solvers/utils/         (solver execution + result processing)
    ↓
JSON Response
```

### **계층 구조**

```
HTTP 요청 (JSON)
    ↓
🚀 Go 서버 (Entry 계층)
├─ server/cmd/server/main.go
├─ server/internal/handlers/
└─ server/internal/router/
    ↓
🔗 Bridge (Command 계층)
├─ server/internal/solver/bridge.go
└─ python_solvers/utils/bridge_logic.py
    ↓
🐍 Python 솔버 (Logic + Output 계층)
├─ python_solvers/domains/       (입력 매핑)
├─ python_solvers/logic/         (Pyomo 모델)
└─ python_solvers/utils/         (솔버 실행 + 결과 처리)
    ↓
JSON 응답
```

### **Technology Stack**

| Layer | Technology | Status |
|-------|-----------|--------|
| **API Server** | Go 1.21+ (net/http) | ⏳ In Progress |
| **Optimization** | Python 3.8+ | ✅ Complete |
| **Solver** | Pyomo 6.7+ (CBC) | ✅ Complete |
| **Data** | JSON (stdin/stdout) | ✅ Complete |

### **기술 스택**

| 계층 | 기술 | 상태 |
|------|------|------|
| **API 서버** | Go 1.21+ (net/http) | ⏳ 개발 중 |
| **최적화 엔진** | Python 3.8+ | ✅ 완성 |
| **솔버** | Pyomo 6.7+ (CBC) | ✅ 완성 |
| **데이터** | JSON (stdin/stdout) | ✅ 완성 |

---

## 📂 Project Structure

```
OptiMystic/
│
├── 🐍 python_solvers/          Python Pyomo Solver (1,643 LOC)
│   ├── solver_engine.py        (237 LOC - Pyomo execution engine)
│   ├── requirements.txt
│   │
│   ├── domains/                (4 modules - input mapping)
│   │   ├── cutting.py          (88 LOC)
│   │   ├── packing.py          (54 LOC)
│   │   ├── resourcing.py       (56 LOC)
│   │   └── scheduling.py       (51 LOC)
│   │
│   ├── logic/                  (5 modules - math models)
│   │   ├── logic_cg.py         (249 LOC - Column Generation ✅)
│   │   ├── logic_mip.py        (293 LOC - Mixed Integer ✅)
│   │   ├── logic_cp.py         (20 LOC - Constraint ⏳)
│   │   ├── logic_st.py         (20 LOC - Stochastic ⏳)
│   │   └── logic_nlp.py        (20 LOC - Non-Linear ⏳)
│   │
│   └── utils/
│       ├── bridge_logic.py     (105 LOC - domain/solver selection)
│       └── services.py         (510 LOC - results & dashboard)
│
├── 🚀 server/                  Go HTTP Server (scaffolding complete)
│   ├── cmd/server/main.go
│   └── internal/
│       ├── handlers/           (optimize, health)
│       ├── router/
│       └── solver/             (Python call)
│
├── 💾 _legacy_django/          Django backup
├── 📦 _legacy/                 original Dash app
├── 📝 scripts/                 Python scripts
└── 📄 docs/                    docs
```

## 📂 프로젝트 구조

```
OptiMystic/
│
├── 🐍 python_solvers/          Python Pyomo 솔버 (1,643줄)
│   ├── solver_engine.py        (237줄 - Pyomo 실행 엔진)
│   ├── requirements.txt
│   │
│   ├── domains/                (4개 모듈 - 입력 매핑)
│   │   ├── cutting.py          (88줄)
│   │   ├── packing.py          (54줄)
│   │   ├── resourcing.py       (56줄)
│   │   └── scheduling.py       (51줄)
│   │
│   ├── logic/                  (5개 모듈 - 수학 모델)
│   │   ├── logic_cg.py         (249줄 - Column Generation ✅)
│   │   ├── logic_mip.py        (293줄 - Mixed Integer ✅)
│   │   ├── logic_cp.py         (20줄 - Constraint ⏳)
│   │   ├── logic_st.py         (20줄 - Stochastic ⏳)
│   │   └── logic_nlp.py        (20줄 - Non-Linear ⏳)
│   │
│   └── utils/
│       ├── bridge_logic.py     (105줄 - 도메인/솔버 선택)
│       └── services.py         (510줄 - 결과 처리 & 대시보드)
│
├── 🚀 server/                  Go HTTP 서버 (구조 완성)
│   ├── cmd/server/main.go
│   └── internal/
│       ├── handlers/           (optimize, health)
│       ├── router/
│       └── solver/             (Python 호출)
│
├── 💾 _legacy_django/          Django 백업
├── 📦 _legacy/                 원본 Dash 앱
├── 📝 scripts/                 Python 스크립트
└── 📄 docs/                    문서
```

### Legacy Folders (Reference Only)
- `_legacy/`: Original Dash app UI (archived; not used in current runtime)
- `_legacy_django/`: Django 2.0 API backup from before the Go migration

### 레거시 폴더 (참고용)
- `_legacy/`: 원본 Dash 앱 UI (보관용, 현재 실행 경로에서 사용하지 않음)
- `_legacy_django/`: Go 마이그레이션 이전 Django 2.0 API 백업

**Full Details**: [FINAL_STRUCTURE.md](FINAL_STRUCTURE.md)

**자세한 내용**: [FINAL_STRUCTURE.md](FINAL_STRUCTURE.md)

---

## 🚀 Quick Start

### Prerequisites
```bash
Python 3.8+
pip / pipenv
Go 1.21+ (optional - for Go server development)
```

### 빠른 시작

### 필수 사항
```bash
Python 3.8+
pip / pipenv
Go 1.21+ (선택사항 - Go 서버 개발용)
```

### Installation

#### 1️⃣ Clone Repository
```bash
git clone https://github.com/yourusername/optimystic.git
cd optimystic
```

#### 2️⃣ Setup Python Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r python_solvers/requirements.txt
```

#### 3️⃣ Test Python Solver
```bash
python python_solvers/solver_engine.py \
  --domain cutting \
  --solver mip \
  --params '{"Items": ["A", "B"], "Demands": {"A": 2, "B": 1}, "Stocks": [{"Name": "S1", "Length": 10, "Cost": 5}], "Kerf": 0}'
```

### 설치

#### 1️⃣ 저장소 복제
```bash
git clone https://github.com/yourusername/optimystic.git
cd optimystic
```

#### 2️⃣ Python 환경 설정
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r python_solvers/requirements.txt
```

#### 3️⃣ Python 솔버 테스트
```bash
python python_solvers/solver_engine.py \
  --domain cutting \
  --solver mip \
  --params '{"Items": ["A", "B"], "Demands": {"A": 2, "B": 1}, "Stocks": [{"Name": "S1", "Length": 10, "Cost": 5}], "Kerf": 0}'
```

---

## 📖 Usage Examples

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

## 사용 예제

### Python 솔버 (직접 사용)

#### 절단 재고 문제
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

# 파라미터 매핑
mapped = bridge_logic.map_params_by_mode("cutting", params)

# 모델 생성
obj, const, vars_config = bridge_logic.generate_logic("cutting", params)

# 풀이
store_data = {
    "variables": vars_config,
    "parameters": services.build_parameter_store(mapped)
}
result = solver_engine.solve_model(store_data, "minimize", obj, const)

# 결과 처리
dashboard = services.process_results(result, store_data, "cutting")
sensitivity = services.process_sensitivity(result, store_data, "cutting")
```

#### 포장 문제
```python
params = {
    "Items": ["Item1", "Item2", "Item3"],
    "Weights": [10, 20, 15],
    "Values": [100, 150, 120],
    "Capacity": 40,
    "Sense": "maximize"
}
# domain="packing"으로 동일하게 사용
```

### Go HTTP API (Coming Soon)

```bash
curl -X POST http://localhost:8000/api/optimize/ \
  -H "Content-Type: application/json" \
  -d '{
    "template_type": "cutting",
    "params": {
      "Items": ["A", "B"],
      "ItemLens": [4, 6],
      "Demands": {"A": 2, "B": 1},
      "Stocks": [{"Name": "S1", "Length": 10, "Cost": 5}],
      "Kerf": 0,
      "Sense": "minimize"
    }
  }'
```

### Go HTTP API (곧 출시 예정)

```bash
curl -X POST http://localhost:8000/api/optimize/ \
  -H "Content-Type: application/json" \
  -d '{
    "template_type": "cutting",
    "params": {
      "Items": ["A", "B"],
      "ItemLens": [4, 6],
      "Demands": {"A": 2, "B": 1},
      "Stocks": [{"Name": "S1", "Length": 10, "Cost": 5}],
      "Kerf": 0,
      "Sense": "minimize"
    }
  }'
```

**Response**:
```json
{
  "status": "Optimal",
  "objective": 10.0,
  "variables": [...],
  "constraints": [...],
  "dashboard": {
    "total_cost": 10.0,
    "total_waste": 0.0,
    "num_bins": 1,
    "bin_plans": [...]
  },
  "sensitivity": [...]
}
```

---

## 🎯 Supported Domains

### 1. **Cutting Stock (Manufacturing)**
- **Algorithm**: Column Generation (✅) + MIP (✅)
- **Problem**: Minimize material cost while meeting demand
- **Input**: Items, Lengths, Demands, Stocks, Kerf
- **Output**: Cutting patterns, Cost, Scrap waste

### 2. **Packing/Knapsack (Logistics)**
- **Algorithm**: MIP (✅) + LP (✅)
- **Problem**: Maximize value within capacity constraints
- **Input**: Items, Weights, Values, Capacity
- **Output**: Selection, Utilization %

### 3. **Resource Allocation (IT/Cloud)**
- **Algorithm**: MIP (✅) + LP (✅)
- **Problem**: Allocate tasks to servers with CPU/RAM constraints
- **Input**: Tasks, CPU, RAM, Capacity
- **Output**: Task allocation, Usage %

### 4. **Shift Scheduling (HR)**
- **Algorithm**: MIP (✅) + LP (✅)
- **Problem**: Meet shift demand with minimum staff
- **Input**: Employees, Shifts, Demands, Max assignments
- **Output**: Assignments, Coverage

## 🎯 지원하는 도메인

### 1. **절단 재고 (제조)**
- **알고리즘**: Column Generation (✅) + MIP (✅)
- **문제**: 수요를 충족하면서 재료 비용 최소화
- **입력**: 품목, 길이, 수요, 원재료, 절단손실
- **출력**: 절단 패턴, 비용, 폐기물

### 2. **포장/나사 (물류)**
- **알고리즘**: MIP (✅) + LP (✅)
- **문제**: 용량 제약 내 최대 가치
- **입력**: 품목, 무게, 가치, 용량
- **출력**: 선택 항목, 활용률

### 3. **리소스 할당 (IT/클라우드)**
- **알고리즘**: MIP (✅) + LP (✅)
- **문제**: CPU/RAM 제약 내 작업 할당
- **입력**: 작업, CPU, RAM, 용량
- **출력**: 작업 배분, 사용률

### 4. **교대 스케줄 (HR)**
- **알고리즘**: MIP (✅) + LP (✅)
- **문제**: 최소 인력으로 교대 수요 충족
- **입력**: 직원, 교대, 수요, 최대 배정
- **출력**: 배정, 커버율

---

## 📊 Solver Algorithms

| Algorithm | Status | Domains | Notes |
|-----------|--------|---------|-------|
| **Column Generation (CG)** | ✅ Complete | Cutting | Optimal solution guaranteed |
| **Mixed Integer Programming (MIP)** | ✅ Complete | All | General purpose, stable |
| **Constraint Programming (CP)** | ⏳ In Progress | Scheduling | For constraint-heavy problems |
| **Stochastic (ST)** | ⏳ In Progress | All | Handles uncertainty |
| **Non-Linear (NLP)** | ⏳ In Progress | Packing, Resourcing | For non-linear objectives |

## 📊 솔버 알고리즘

| 알고리즘 | 상태 | 도메인 | 설명 |
|----------|------|--------|------|
| **Column Generation (CG)** | ✅ 완성 | 절단 | 최적해 보장 |
| **Mixed Integer Programming (MIP)** | ✅ 완성 | 전부 | 범용, 안정적 |
| **Constraint Programming (CP)** | ⏳ 진행중 | 스케줄 | 제약 조건 많은 문제용 |
| **Stochastic (ST)** | ⏳ 진행중 | 전부 | 불확실성 처리 |
| **Non-Linear (NLP)** | ⏳ 진행중 | 포장, 리소스 | 비선형 목적함수용 |

---

## 🔧 Configuration

### Environment Variables
```bash
# .env.example
PYOMO_SOLVER=cbc
DEBUG=False
```

### Python Requirements
```
pyomo==6.7.3        # Optimization engine
pandas==2.0.3       # Data processing
numpy==1.24.3       # Numerical computing
```

## 🔧 설정

### 환경 변수
```bash
# .env.example
PYOMO_SOLVER=cbc
DEBUG=False
```

### Python 의존성
```
pyomo==6.7.3        # 최적화 엔진
pandas==2.0.3       # 데이터 처리
numpy==1.24.3       # 수치 연산
```

---

## 📈 Performance

### Benchmark (CBC Solver, Single Threaded)

| Problem Type | Size | Time | Status |
|--------------|------|------|--------|
| Cutting Stock | 10 items, 5 stocks | < 1s | Optimal |
| Packing | 50 items | 2-5s | Optimal |
| Resourcing | 100 tasks | 1-3s | Optimal |
| Scheduling | 20 employees, 30 shifts | 0.5-2s | Optimal |

**Go Server with Concurrency** (coming soon): Multiple concurrent requests via goroutines

## 📈 성능

### 벤치마크 (CBC 솔버, 단일 스레드)

| 문제 유형 | 크기 | 시간 | 상태 |
|----------|------|------|------|
| 절단 재고 | 10개 품목, 5개 원재료 | < 1초 | 최적해 |
| 포장 | 50개 품목 | 2-5초 | 최적해 |
| 리소스 | 100개 작업 | 1-3초 | 최적해 |
| 스케줄 | 20명 직원, 30개 교대 | 0.5-2초 | 최적해 |

**Go 서버 동시성** (곧 출시 예정): Goroutine을 통한 다중 동시 요청

---

## 🚀 Deployment

### Local Testing (Python Only)
```bash
python python_solvers/solver_engine.py --domain cutting --solver mip --params '{...}'
```

### Go Server (Coming Soon)
```bash
cd server
go build -o ./bin/optimystic-server cmd/server/main.go
./bin/optimystic-server
```

### Docker (Planned)
```bash
docker build -t optimystic .
docker run -p 8000:8000 optimystic
```

## 🚀 배포

### 로컬 테스트 (Python만)
```bash
python python_solvers/solver_engine.py --domain cutting --solver mip --params '{...}'
```

### Go 서버 (곧 출시 예정)
```bash
cd server
go build -o ./bin/optimystic-server cmd/server/main.go
./bin/optimystic-server
```

### Docker (계획 중)
```bash
docker build -t optimystic .
docker run -p 8000:8000 optimystic
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [FINAL_STRUCTURE.md](FINAL_STRUCTURE.md) | Complete file structure |
| [MIGRATION_COMPLETE.md](MIGRATION_COMPLETE.md) | Migration completion report |
| [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) | Final summary |
| [FINAL_STATUS.md](FINAL_STATUS.md) | Current status |

## 📚 문서

| 문서 | 설명 |
|------|------|
| [FINAL_STRUCTURE.md](FINAL_STRUCTURE.md) | 완전한 파일 구조 |
| [MIGRATION_COMPLETE.md](MIGRATION_COMPLETE.md) | 마이그레이션 완료 보고서 |
| [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md) | 최종 요약 |
| [FINAL_STATUS.md](FINAL_STATUS.md) | 현재 상태 |

---

## 🛠️ Development Roadmap

### ✅ Phase 1: Python Solver (Complete)
- [x] Column Generation
- [x] Mixed Integer Programming
- [x] Domain input mapping (4 domains)
- [x] Result processing & sensitivity analysis
- [x] Dashboard generation

### ⏳ Phase 2: Go Server (In Progress)
- [ ] HTTP server setup
- [ ] Request handlers (/api/optimize/, /api/health/)
- [ ] Python subprocess invocation
- [ ] JSON marshaling
- [ ] Error handling & logging
- [ ] Unit & integration tests

### 🔮 Phase 3: Advanced Features
- [ ] Constraint Programming solver
- [ ] Stochastic optimization
- [ ] Non-Linear solver
- [ ] Web Dashboard (React)
- [ ] Database integration
- [ ] Docker & Kubernetes deployment
- [ ] CI/CD pipeline (GitHub Actions)

## 🛠️ 개발 로드맵

### ✅ Phase 1: Python 솔버 (완료)
- [x] Column Generation
- [x] Mixed Integer Programming
- [x] 도메인 입력 매핑 (4개 도메인)
- [x] 결과 처리 & 민감도 분석
- [x] 대시보드 생성

### ⏳ Phase 2: Go 서버 (진행 중)
- [ ] HTTP 서버 설정
- [ ] 요청 핸들러 (/api/optimize/, /api/health/)
- [ ] Python 서브프로세스 호출
- [ ] JSON 마샬링
- [ ] 에러 처리 & 로깅
- [ ] 단위 & 통합 테스트

### 🔮 Phase 3: 고급 기능
- [ ] Constraint Programming 솔버
- [ ] Stochastic 최적화
- [ ] Non-Linear 솔버
- [ ] 웹 대시보드 (React)
- [ ] 데이터베이스 통합
- [ ] Docker & Kubernetes 배포
- [ ] CI/CD 파이프라인 (GitHub Actions)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 🤝 기여하기

1. 저장소를 포크합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feature/your-feature`)
3. 변경사항을 커밋합니다
4. 브랜치로 푸시합니다
5. Pull Request를 엽니다

---

## 🔗 References

- [Pyomo Documentation](https://pyomo.readthedocs.io/)
- [CBC Solver](https://github.com/coin-or/Cbc)
- [Go Documentation](https://golang.org/doc/)

## 🔗 참고자료

- [Pyomo 문서](https://pyomo.readthedocs.io/)
- [CBC 솔버](https://github.com/coin-or/Cbc)
- [Go 문서](https://golang.org/doc/)

---

**Last Updated**: February 23, 2026 | **Status**: ✅ Python Solver Complete | ⏳ Go Server In Progress

**마지막 업데이트**: 2026년 2월 23일 | **상태**: ✅ Python 솔버 완성 | ⏳ Go 서버 진행 중

---

## 🏛️ Go-First Architecture (Option A)

**Status**: ✅ **Python Complete | Go Ready (stub)**

### Current Structure

```
Client → Go (Entry + Command) → Python (Logic Only) → Result
        (routing, validation)       (JSON in/out)
```

### What's Complete ✅

| Layer | Python | Go | Status |
|-------|--------|----|----|
| **Logic** | domains/, logic/, solver_engine.py | - | ✅ Complete |
| **Entry** | (removed) | handlers/, router/ | ⏳ Stub |
| **Command** | bridge_logic.py | bridge.go | ⏳ Stub |
| **Exit** | services.py | services/*.go | ⏳ Stub |

### Python Solver (Standalone)

Pure calculation (JSON in → Pyomo → JSON out):

```bash
python python_solvers/solver_engine.py \
  --domain cutting \
  --solver mip \
  --params '{"Items": ["A"], ...}'

# Returns: {status, objective, variables, constraints, solve_time}
```

### Go Implementation Guide

**Reference files** in `_legacy_django/`:
- `ORIGINAL_services.py` - original result processing logic (reference)
- `REFACTORED_solver_engine.py` - current Python layout
- `views.py`, `bridge_logic.py` - Django legacy

**Go File Structure**:
```
server/
├── cmd/server/main.go           (⏳ HTTP server entry)
└── internal/
    ├── handlers/                (⏳ Request handlers)
    ├── router/                  (⏳ URL routing)
    ├── models/                  (⏳ Struct definitions)
    ├── services/                (⏳ Result processing)
    └── solver/                  (⏳ Python call)
```

**Key Principle**:
> **Go = Conductor, Python = Calculator**
> Go orchestrates the flow; Python performs computation only

---

## 🏛️ Go-First 아키텍처 (옵션 A)

**상태**: ✅ **Python 완성 | Go 준비(스텁)**

### 현재 구조

```
클라이언트 → Go (Entry + Command) → Python (Logic Only) → 결과
           (라우팅, 검증)           (JSON in/out)
```

### 완료된 항목 ✅

| 계층 | Python | Go | 상태 |
|-------|--------|----|------|
| **Logic** | domains/, logic/, solver_engine.py | - | ✅ 완성 |
| **Entry** | (삭제) | handlers/, router/ | ⏳ 스텁 |
| **Command** | bridge_logic.py | bridge.go | ⏳ 스텁 |
| **Exit** | services.py | services/*.go | ⏳ 스텁 |

### Python 솔버 (독립 실행)

순수 계산 (JSON in → Pyomo → JSON out):

```bash
python python_solvers/solver_engine.py \
  --domain cutting \
  --solver mip \
  --params '{"Items": ["A"], ...}'

# 결과: {status, objective, variables, constraints, solve_time}
```

### Go 구현 가이드

`_legacy_django/` 참고 파일:
- `ORIGINAL_services.py` - 원본 결과 처리 로직 (참조용)
- `REFACTORED_solver_engine.py` - 현재 Python 구조
- `views.py`, `bridge_logic.py` - Django 레거시

**Go 파일 구조**:
```
server/
├── cmd/server/main.go           (⏳ HTTP 서버 진입점)
└── internal/
    ├── handlers/                (⏳ 요청 핸들러)
    ├── router/                  (⏳ 라우팅)
    ├── models/                  (⏳ 구조체 정의)
    ├── services/                (⏳ 결과 처리)
    └── solver/                  (⏳ Python 호출)
```

**핵심 원칙**:
> **Go = Conductor (지휘자), Python = Calculator (계산기)**
> Go가 전체 흐름 제어, Python은 명령받은 계산만 수행

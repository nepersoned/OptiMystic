# OptiMystic

🚀 **Multi-Domain Optimization API**

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
│
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

### Phase 2: Go Server (In Progress)
- [ ] HTTP server setup
- [ ] Request handlers (/api/optimize/, /api/health/)
- [ ] Python subprocess invocation
- [ ] JSON marshaling
- [ ] Error handling & logging
- [ ] Unit & integration tests

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

---

# 옵티미스틱 (OptiMystic)

🚀 **다중 도메인 최적화 API**

비즈니스 최적화 문제를 수학 모델로 변환하고 최신 최적화 알고리즘(Column Generation, MIP, LP, NLP)으로 해결합니다.

**상태:** Python 솔버 운영 준비 완료 | Go 서버 개발 중
**제한사항:** Go HTTP API는 스텁 상태이며, 현재는 Python 솔버를 직접 사용하세요.

---

## 어떤 기능인가요

| 문제           | 알고리즘           | 입력           | 출력           |
|----------------|--------------------|----------------|----------------|
| 절단 재고      | Column Generation + MIP | 품목, 길이, 수요, 원재료, 절단손실 | 절단 패턴, 비용, 폐기물 |
| 포장/나사      | MIP/LP             | 품목, 무게, 가치, 용량 | 선택, 활용률 |
| 리소스 할당    | MIP/LP             | 작업, CPU, RAM, 용량 | 작업 배분, 사용률 |
| 교대 스케줄    | MIP/LP             | 직원, 교대, 수요 | 배정, 커버율 |

---

## 아키텍처

```
HTTP 요청 (JSON)
    ↓
Go 서버 (Entry 계층)
├─ server/cmd/server/main.go
├─ server/internal/handlers/
└─ server/internal/router/
    ↓
Bridge (Command 계층)
├─ server/internal/solver/bridge.go
└─ python_solvers/utils/bridge_logic.py
    ↓
Python 솔버 (Logic + Output 계층)
├─ python_solvers/domains/       (입력 매핑)
├─ python_solvers/logic/         (Pyomo 모델)
└─ python_solvers/utils/         (솔버 실행 + 결과 처리)
    ↓
JSON 응답
```

---

## 기술 스택

| 계층         | 기술         | 상태         |
|--------------|--------------|--------------|
| API 서버     | Go 1.21+     | 개발 중      |
| 최적화 엔진  | Python 3.8+  | 완성         |
| 솔버         | Pyomo 6.7+   | 완성         |
| 데이터       | JSON         | 완성         |

---

## 프로젝트 구조

```
OptiMystic/
│
├── python_solvers/          Python Pyomo 솔버
│   ├── solver_engine.py     Pyomo 실행 엔진
│   ├── requirements.txt
│   │
│   ├── domains/             입력 매핑
│   │   ├── cutting.py
│   │   ├── packing.py
│   │   ├── resourcing.py
│   │   └── scheduling.py
│   │
│   ├── logic/               수학 모델
│   │   ├── logic_cg.py      Column Generation
│   │   ├── logic_mip.py     Mixed Integer
│   │   ├── logic_cp.py      Constraint
│   │   ├── logic_st.py      Stochastic
│   │   └── logic_nlp.py     Non-Linear
│   │
│   └── utils/
│       ├── bridge_logic.py  도메인/솔버 선택
│       └── services.py      결과 처리
│
├── server/                  Go HTTP 서버
│   ├── cmd/server/main.go
│   └── internal/
│       ├── handlers/        optimize, health
│       ├── router/
│       ├── services/        results_cutting, results_packing, results_resourcing, results_scheduling
│       └── solver/          Python 호출
│
├── _legacy_django/          Django 백업
├── _legacy/                 원본 Dash 앱
├── scripts/                 Python 스크립트
└── docs/                    문서
```

---

## 빠른 시작

### 필수 사항
Python 3.8+
pip / pipenv
Go 1.21+ (선택사항)

### 설치

1. 저장소 복제
   git clone https://github.com/yourusername/optimystic.git
   cd optimystic
2. Python 환경 설정
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r python_solvers/requirements.txt
3. Python 솔버 테스트
   python python_solvers/cli_solver.py --domain cutting --solver mip --params '{...}'

---

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

---

## 지원 도메인

| 도메인           | 알고리즘           | 입력           | 출력           |
|------------------|--------------------|----------------|----------------|
| 절단 재고        | Column Generation + MIP | 품목, 길이, 수요, 원재료, 절단손실 | 절단 패턴, 비용, 폐기물 |
| 포장/나사        | MIP/LP             | 품목, 무게, 가치, 용량 | 선택, 활용률 |
| 리소스 할당      | MIP/LP             | 작업, CPU, RAM, 용량 | 작업 배분, 사용률 |
| 교대 스케줄      | MIP/LP             | 직원, 교대, 수요 | 배정, 커버율 |

---

## 솔버 알고리즘

| 알고리즘           | 상태         | 도메인         | 설명         |
|--------------------|--------------|----------------|--------------|
| Column Generation  | 완성         | 절단           | 최적해 보장 |
| 혼합정수계획       | 완성         | 전부           | 범용, 안정적 |
| 제약계획           | 진행중       | 스케줄         | 제약 조건 많은 문제용 |
| 확률적             | 진행중       | 전부           | 불확실성 처리 |
| 비선형             | 진행중       | 포장, 리소스   | 비선형 목적함수용 |

---

## 설정

### 환경 변수
PYOMO_SOLVER=cbc
DEBUG=False

### Python 의존성
pyomo==6.7.3        # 최적화 엔진
pandas==2.0.3       # 데이터 처리
numpy==1.24.3       # 수치 연산

---

## 성능

| 문제 유형         | 크기         | 시간         | 상태         |
|------------------|--------------|--------------|--------------|
| 절단 재고        | 10개 품목, 5개 원재료 | < 1초         | 최적해       |
| 포장             | 50개 품목    | 2-5초        | 최적해       |
| 리소스           | 100개 작업   | 1-3초        | 최적해       |
| 스케줄           | 20명 직원, 30개 교대 | 0.5-2초       | 최적해       |

---

## 배포

### 로컬 테스트 (Python만)
python python_solvers/cli_solver.py --domain cutting --solver mip --params '{...}'

### Go 서버 (곧 출시 예정)
cd server
go build -o ./bin/optimystic-server cmd/server/main.go
./bin/optimystic-server

### Docker (계획 중)
docker build -t optimystic .
docker run -p 8000:8000 optimystic

---

## 문서

| 문서         | 목적         |
|--------------|--------------|
| FINAL_STRUCTURE.md      | 전체 파일 구조 |
| MIGRATION_COMPLETE.md   | 마이그레이션 완료 보고 |
| MIGRATION_SUMMARY.md    | 최종 요약    |
| FINAL_STATUS.md         | 현재 상태    |

---

## 개발 로드맵

### 1단계: Python 솔버 (완료)
- [x] Column Generation
- [x] Mixed Integer Programming
- [x] 도메인 입력 매핑 (4개 도메인)
- [x] 결과 처리 & 민감도 분석
- [x] 대시보드 생성

### 2단계: Go 서버 (진행 중)
- [ ] HTTP 서버 구축
- [ ] 요청 핸들러 (/api/optimize/, /api/health/)
- [ ] Python 서브프로세스 호출
- [ ] JSON 직렬화
- [ ] 에러 처리 & 로깅
- [ ] 단위/통합 테스트

### 3단계: 고급 기능
- [ ] 제약계획 솔버
- [ ] 확률적 최적화
- [ ] 비선형 솔버
- [ ] 웹 대시보드 (React)
- [ ] 데이터베이스 연동
- [ ] Docker & Kubernetes 배포
- [ ] CI/CD 파이프라인 (GitHub Actions)

---

## 기여하기

1. 저장소를 포크하세요
2. 기능 브랜치 생성 (`git checkout -b feature/your-feature`)
3. 변경사항 커밋
4. 브랜치에 푸시
5. Pull Request 생성

---

## 참고자료

- [Pyomo Documentation](https://pyomo.readthedocs.io/)
- [CBC Solver](https://github.com/coin-or/Cbc)
- [Go Documentation](https://golang.org/doc/)

---

**마지막 업데이트**: 2026년 2월 24일 | **상태**: Python 솔버 완성 | Go 서버 진행 중

---

# Go-First 아키텍처 (옵션 A)

**상태**: Python 완성 | Go 준비 (stub)

### 현재 구조

```
Client → Go (Entry + Command) → Python (Logic Only) → Result
        (routing, validation)       (JSON in/out)
```

### 완료된 항목

| 계층 | Python | Go | 상태 |
|------|--------|----|------|
| Logic | domains/, logic/, solver_engine.py | - | 완성 |
| Entry | (제거됨) | handlers/, router/ | Stub |
| Command | bridge_logic.py | bridge.go | Stub |
| Exit | services.py | services/*.go | Stub |

### Python 솔버 (독립 실행)

순수 계산 (JSON in → Pyomo → JSON out):

```bash
python python_solvers/cli_solver.py \
  --domain cutting \
  --solver mip \
  --params '{"Items": ["A"], ...}'

# 반환: {status, objective, variables, constraints, solve_time}
```

### Go 구현 가이드

**참고 파일** (`_legacy_django/`):
- `ORIGINAL_services.py` - 원본 결과 처리 로직 (참고)
- `REFACTORED_solver_engine.py` - 현재 Python 레이아웃
- `views.py`, `bridge_logic.py` - Django 레거시

**Go 파일 구조**:
```
server/
├── cmd/server/main.go           (HTTP 서버 진입점)
└── internal/
    ├── handlers/                (요청 핸들러)
    ├── router/                  (URL 라우팅)
    ├── models/                  (구조체 정의)
    ├── services/                (결과 처리)
    └── solver/                  (Python 호출)
```

**핵심 원칙**

> Go = 지휘자, Python = 계산기
> Go가 전체 흐름 제어, Python은 명령받은 계산만 수행

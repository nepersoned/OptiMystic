# OptiMystic Go Server

Go HTTP server for OptiMystic optimization API.
Replaces Django's HTTP layer while Python Pyomo solvers remain unchanged.

OptiMystic 최적화 API용 Go HTTP 서버입니다.
Django의 HTTP 계층을 대체하고 Python Pyomo 솔버는 그대로 유지합니다.

## Structure

```
server/
├── cmd/server/
│   └── main.go              # Server entry point
├── internal/
│   ├── handlers/            # HTTP handlers
│   │   ├── optimize.go      # POST /api/optimize/
│   │   └── health.go        # GET /api/health/
│   ├── router/
│   │   └── router.go        # Route registration
│   ├── models/
│   │   └── optimization.go  # Data structures (structs)
│   ├── services/
│   │   └── results.go       # Result processing
│   └── solver/
│       └── bridge.go        # Domain/solver selector + Python invocation
├── go.mod                   # Go module file
└── README.md                # This file
```

## 구조

```
server/
├── cmd/server/
│   └── main.go              # 서버 진입점
├── internal/
│   ├── handlers/            # HTTP 핸들러
│   │   ├── optimize.go      # POST /api/optimize/
│   │   └── health.go        # GET /api/health/
│   ├── router/
│   │   └── router.go        # 라우트 등록
│   ├── models/
│   │   └── optimization.go  # 데이터 구조 (struct)
│   ├── services/
│   │   └── results.go       # 결과 처리
│   └── solver/
│       └── bridge.go        # 도메인/솔버 선택 + Python 호출
├── go.mod                   # Go 모듈 파일
└── README.md                # 이 파일
```

## Responsibilities

### Entry Layer (HTTP)
- Listen on port (default 8000)
- Parse JSON requests
- Route to appropriate handlers

### Command Layer (Bridge)
- Normalize domain (template_type)
- Select solver type (cg, mip, cp, st, nlp)
- Execute Python solver via subprocess

### Exit Layer (Processing)
- Process Python solver results
- Transform to domain-specific output
- Return JSON response

## 책임

### Entry Layer (HTTP)
- 포트 수신 (기본 8000)
- JSON 요청 파싱
- 적절한 핸들러로 라우팅

### Command Layer (Bridge)
- 도메인 정규화 (template_type)
- 솔버 타입 선택 (cg, mip, cp, st, nlp)
- Python 솔버 subprocess 실행

### Exit Layer (처리)
- Python 솔버 결과 처리
- 도메인별 출력으로 변환
- JSON 응답 반환

## Usage

### Run Server
```bash
cd server
go run cmd/server/main.go
```

### Make Request
```bash
curl -X POST http://localhost:8000/api/optimize/ \
  -H "Content-Type: application/json" \
  -d '{
    "template_type": "cutting",
    "params": { "Items": [...], "ItemLens": [...], ... }
  }'
```

## 사용

### 서버 실행
```bash
cd server
go run cmd/server/main.go
```

### 요청 만들기
```bash
curl -X POST http://localhost:8000/api/optimize/ \
  -H "Content-Type: application/json" \
  -d '{
    "template_type": "cutting",
    "params": { "Items": [...], "ItemLens": [...], ... }
  }'
```

## Integration with Python Solver

Bridge calls:
```bash
python python_solvers/cli_solver.py \
  --domain cutting \
  --solver mip \
  --params '{"Items": [...], ...}'
```

Expects JSON stdout with `{status, objective, variables, constraints, ...}`.

## Python 솔버와의 통합

Bridge가 호출:
```bash
python python_solvers/cli_solver.py \
  --domain cutting \
  --solver mip \
  --params '{"Items": [...], ...}'
```

JSON stdout을 `{status, objective, variables, constraints, ...}` 형태로 반환합니다.

## Build

```bash
cd server
go build -o ./bin/optimystic-server cmd/server/main.go
```

## Notes

- No Django or Python dependencies in Go code
- All Python logic lives in `python_solvers/`
- Standard library used for HTTP (can upgrade to chi/gin if needed)

## 주의

- Go 코드에는 Django/Python 의존성 없음
- 모든 Python 로직은 `python_solvers/`에 위치
- HTTP는 표준 라이브러리 사용 (필요시 chi/gin으로 업그레이드 가능)

## 시스템 아키텍처 / System Architecture

아래는 OptiMystic Go 서버와 Python 솔버 전체 데이터 흐름 및 계층 구조입니다.
Below is the overall data flow and layer structure of the OptiMystic Go server and Python solver.

```
+-------------------------------+
| server/cmd/server/main.go     |
+---------------+---------------+
                |
                v
+-------------------------------+
| server/internal/router/router |
+---------------+---------------+
                |
        +-------+-------------------+
        |                           |
        v                           v
+------------------------+   +----------------------------+
| handlers/health.go     |   | handlers/optimize.go       |
+------------------------+   +-------------+--------------+
                                          |
                                          v
                               +----------------------------+
                               | models/optimization.go     |
                               +-------------+--------------+
                                          |
                                          v
                               +----------------------------+
                               | solver/bridge.go           |
                               +-------------+--------------+
                                          |
                                          v
                               +----------------------------+
                               | python_solvers/cli_solver  |
                               +-------------+--------------+
                                          |
                                          v
                               +----------------------------+
                               | utils/bridge_logic.py      |
                               +-------------+--------------+
                                          |
        +----------------------+----------+----------+----------------------
        |                      |                     |                      |
        v                      v                     v                      v
+------------------+  +------------------+  +------------------+  +------------------+
| domains/cutting  |  | domains/packing  |  | domains/resource |  | domains/sched    |
+------------------+  +------------------+  +------------------+  +------------------+
        |                      |                     |                      |
        +-----------+----------+----------+----------+----------+-----------+
                    |                     |                     |
                    v                     v                     v
          +------------------+   +------------------+   +------------------+
          | logic/logic_cg   |   | logic/logic_mip  |   | logic/logic_cp   |
          +------------------+   +------------------+   +------------------+
                    |                     |                     |
                    +-----------+---------+---------+-----------+
                                |
                                v
                   +----------------------------+
                   | utils/solver_engine.py     |
                   +-------------+--------------+
                                 |
                                 v
                   +----------------------------+
                   | utils/services.py          |
                   +-------------+--------------+
                                 |
                                 v
                   +----------------------------+
                   | solver/bridge.go (result)  |
                   +-------------+--------------+
                                 |
                                 v
                   +----------------------------+
                   | services/results.go        |
                   +------+------+------+-------+
                          |      |      |
                          v      v      v
          +----------------+ +----------------+ +---------------------+
          | results_cutting| | results_packing| | results_resourcing   |
          +----------------+ +----------------+ +---------------------+
                          |
                          v
                +----------------------------+
                | services/results_scheduling|
                +----------------------------+
```

- main.go: 서버 진입점, 라우터 초기화 / Server entry point, router initialization
- router.go: 엔드포인트 라우팅 / Endpoint routing
- handlers: 요청 처리(health, optimize 등) / Request handling (health, optimize, etc.)
- models: 데이터 구조 정의 / Data structure definitions
- bridge.go: Go ↔ Python 연동 / Go ↔ Python bridge
- python_solvers: 실제 최적화 연산 및 도메인별 로직 / Actual optimization and domain logic
- services/results.go: 결과 가공 및 도메인별 분배 / Result processing and domain dispatch
- results_*.go: 도메인별 결과 최종 산출 / Final domain-specific result generation
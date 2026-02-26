# OptiMystic Go Server

Go HTTP server for OptiMystic optimization API.
Replaces Django's HTTP layer while Python Pyomo solvers remain unchanged.

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

## Integration with Python Solver

Bridge calls:
```bash
python python_solvers/cli_solver.py \
  --domain cutting \
  --solver mip \
  --params '{"Items": [...], ...}'
```

Expects JSON stdout with `{status, objective, variables, constraints, ...}`.

## Build

```bash
cd server
go build -o ./bin/optimystic-server cmd/server/main.go
```

## Notes

- No Django or Python dependencies in Go code
- All Python logic lives in `python_solvers/`
- Standard library used for HTTP (can upgrade to chi/gin if needed)
# OptiMystic Go Server

Go API layer for reliability-focused orchestration between HTTP clients and the Python optimization runtime.

It is responsible for subprocess execution safety, domain-aware response typing, and stable API behavior across solver paths.

## Why This Layer Exists

- Orchestrates Python solver subprocess calls from a typed Go API surface.
- Enforces timeout safety for long-running optimization workloads.
- Dispatches domain results into typed outputs for predictable client handling.
- Supports generic/raw passthrough for IR-driven advanced use cases.

## Endpoints

- `GET /api/health`
- `GET /api/health/`
- `POST /api/optimize`
- `POST /api/optimize/`

## One Verified Run Path (PowerShell)

Use this for demo/evaluation. This path is aligned with the root smoke test.

```powershell
cd C:\Users\kevin\OneDrive\Desktop\OptiMystic\server
$env:OPTIMYSTIC_PYTHON = "C:/Users/kevin/OneDrive/Desktop/OptiMystic/.venv/Scripts/python.exe"
$env:OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS = "180"
$env:OPTIMYSTIC_JULIA_TIMEOUT_SECONDS = "180"
go run .\cmd\server\main.go
```

In another terminal:

```powershell
cd C:\Users\kevin\OneDrive\Desktop\OptiMystic
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1
```

If smoke test output is printed for all 3 steps (health, scheduling, packing), server integration is working end-to-end.

## Request/Response Examples

### 1) Domain flow example (`scheduling` + `cp`)

Request:

```json
{
  "template_type": "scheduling",
  "solver_type": "cp",
  "sense": "minimize",
  "params": {
    "Jobs": [
      { "Name": "J1", "Duration": 3 },
      { "Name": "J2", "Duration": 2 }
    ],
    "Machines": [
      { "Name": "M1" }
    ]
  }
}
```

Response (shape example):

```json
{
  "status": "ok",
  "objective": 5,
  "solve_time": 0.02,
  "details": {
    "schedule": []
  },
  "variables": {},
  "constraints": []
}
```

### 2) Generic flow example (`generic` + `mip`, IR passthrough)

Request:

```json
{
  "template_type": "generic",
  "solver_type": "mip",
  "sense": "maximize",
  "params": {
    "IR": [
      { "type": "var", "name": "x", "lb": 0 },
      { "type": "objective", "sense": "maximize", "expr": [[1, "x"]] }
    ]
  }
}
```

Response (shape example):

```json
{
  "status": "ok",
  "objective": 1,
  "details": {
    "kind": "generic"
  },
  "variables": {
    "x": 1
  },
  "constraints": []
}
```

## Timeout Safety

Python subprocess execution timeout is controlled by environment variable:

- `OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS`
- default: `30`

If timeout is reached, the API returns an error response indicating solver execution exceeded allowed time.

Example (cmd.exe):

```cmd
set OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS=45
go run .\cmd\server\main.go
```

## Result Dispatch

`internal/services/results.go` coordinates domain-aware mapping.

- Typed outputs: `cutting`, `packing`, `resourcing`, `scheduling`
- Generic outputs: `GenericOutput`
- Fallback behavior: if typed mapping is unavailable, raw-compatible fields are preserved for client-side handling

This keeps API responses stable while allowing domain-specific detail structures.

## Internal Flow

```text
HTTP handler
  -> solver bridge (`internal/solver/bridge.go`)
  -> python_solvers/cli_solver.py subprocess
  -> raw python result JSON
  -> result dispatch (`DispatchResults`)
  -> API response
```

## Troubleshooting

- `python not found`  
  Ensure Python is installed and available in PATH for the server process.
- `solver backend not installed`  
  Install required Python dependencies and a compatible Pyomo backend solver.
- `timeout too short`  
  Increase `OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS` for heavier models.
- `details empty` or raw-only response  
  Check `template_type`/`solver_type` combination and whether typed mapping exists for that path.

## Notes

- Bridge execution targets `python_solvers/cli_solver.py` from workspace context.
- Domain aliases are normalized before dispatch.
- Generic IR requests are first-class for contract-based frontend integration.
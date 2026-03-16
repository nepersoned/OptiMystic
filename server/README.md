# OptiMystic Go Server

Go HTTP layer for the OptiMystic optimization service.

## Responsibilities

- expose HTTP endpoints
- decode request JSON
- call the Python solver bridge
- map Python details into typed Go outputs
- return a stable API response

## Endpoints

- `GET /api/health`
- `GET /api/health/`
- `POST /api/optimize`
- `POST /api/optimize/`

## Request shape

```json
{
  "template_type": "cutting",
  "solver_type": "mip",
  "sense": "minimize",
  "params": {
    "Items": [],
    "Stocks": []
  }
}
```

## Run

```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic\server
go run .\cmd\server\main.go
```

## Build

```cmd
cd /d c:\Users\kevin\OneDrive\Desktop\OptiMystic\server
go build -o .\bin\optimystic-server .\cmd\server\main.go
```

## Internal flow

```text
handler -> solver bridge -> python cli -> python result -> result dispatcher -> response
```

## Notes

- The bridge executes `python_solvers/cli_solver.py` from the workspace root.
- The response keeps raw `variables` and `constraints` plus domain-shaped `details`.
- Domain aliases are normalized before result mapping.
- Python solver execution is time-limited via `OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS` (default: 30 seconds).
- `template_type = generic` is supported for expert IR-driven optimization requests.

# Python Solvers Runtime

Python runtime layer for OptiMystic API and MCP tools.

## Responsibilities

- FastAPI service (`api/main.py`)
- Domain routing (`api/solver_api.py`)
- Python-native solving paths (CP scheduling, VRP routing)
- Delegation to Julia runtime for non-Python solver families
- FastMCP tool server (`mcp_server.py`)

## MCP Tools

Exposed tools:
- `optimize(request)`
- `read_company_data(file_path, max_rows=3)`
- `get_target_schema(domain)`
- `map_to_target_schema(file_path, mapping_rule, domain)`

Key notes:
- Keep `fastmcp<3.0.0` for compatibility in this repository.
- `optimize` requires the wrapped shape `{"request": {...}}`.

## Local Run

```powershell
cd C:\Projects\OptiMystic
.\.venv\Scripts\python.exe -m pip install -r python_solvers\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn python_solvers.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## MCP Server Run

```powershell
cd C:\Projects\OptiMystic
.\.venv\Scripts\python.exe -m python_solvers.mcp_server
```

## API Contract

Endpoint:
- `POST /optimize`

Minimal payload:

```json
{
  "domain": "packing",
  "solver": "mip",
  "params": {
    "Items": [
      {"Name": "A", "Weight": 2, "Value": 10, "Demand": 2}
    ],
    "Vehicles": [
      {"Capacity": 5}
    ]
  }
}
```

## Runtime Split

Python-native:
- `scheduling` + `cp`
- `vrp` routing path

Delegated to Julia:
- `cutting`, `packing`, `resourcing`, `generic` and solver families such as `mip`, `ga`, `cg`, `st`, `nlp`, `minlp`

See `../julia_solvers/README.md` for Julia-side details.

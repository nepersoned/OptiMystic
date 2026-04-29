# Python Solvers Runtime

Python runtime layer for OptiMystic API and MCP tools.

## Responsibilities

- FastAPI service (`api/main.py`)
- Domain routing (`api/solver_api.py`)
- Dataset CRUD + versioning (`api/datasets.py`)
- Python-native solving paths (CP scheduling, VRP routing)
- Delegation to Julia runtime for non-Python solver families
- R post-analysis bridge (`r_bridge.py`)
- FastMCP tool server (`mcp_server.py`)

## MCP Tools

All 7 tools are fully implemented:

| Tool | Description |
|------|-------------|
| `read_company_data` | Load CSV/XLSX, return metadata + sample |
| `forecast_demand` | AutoARIMA demand forecast (StatsForecast, naive fallback) |
| `bridge_forecast_to_payload` | Inject forecast results into domain solver payload |
| `get_target_schema` | Return Pydantic JSON schema for a domain |
| `map_to_target_schema` | Map source columns → validated domain payload |
| `optimize` | Route and run solver, return standardized result |
| `analyze_with_r` | R post-analysis: sensitivity, decision analytics, executive summary |

## Dataset API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/datasets/upload` | Upload CSV/Excel, infer domain/solver |
| `GET` | `/datasets/{id}/grid` | Versioned rows + columns |
| `PATCH` | `/datasets/{id}/cells` | Apply cell edits, create new version |
| `GET` | `/datasets/{id}/versions` | List version history |
| `POST` | `/datasets/{id}/versions/{v}/restore` | Restore previous version |
| `POST` | `/datasets/{id}/chat` | AI chat with agent loop + fallback chain |
| `POST` | `/datasets/{id}/optimize` | Run solver, return charts + summary + R analysis |

## Chart & Summary Builders

`_build_chart_data()` and `_build_executive_summary()` cover all domains:

| Domain | Chart | Summary |
|--------|-------|---------|
| `vrp` | route_bar (distance + load per vehicle) | vehicles, total distance, unserved |
| `scheduling` | assignment_bar + shadow_price_bar | assignments made, constraint status |
| `packing` | packing_bar + shadow_price_bar | bins used, feasibility |
| `cutting` | pattern_usage_bar + shadow_price_bar | patterns, CG iterations, waste |
| `resourcing` | resource_bar + shadow_price_bar | scenarios, hotspots |
| `generic` | variable_bar + shadow_price_bar | engine, objective, variable count |

## R Bridge

`r_bridge.analyze_with_r()` is the single public entry point for all R post-analysis.
It wraps `ensure_r_bridge()` + `run_r_post_analysis()` with error handling and
cross-platform R_HOME discovery (Windows glob + Linux standard paths).

## Runtime Split

Python-native:
- `scheduling` → CP-SAT
- `vrp` → OR-Tools

Delegated to Julia:
- `cutting` → CG / MIP
- `packing` → MIP
- `resourcing` → ST
- `generic` → NLP / MINLP / MIP

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

# OptiMystic

OptiMystic is a multi-domain optimization platform built on Python, Julia, and R.

## What Is Included

- FastAPI optimization API (`/health`, `/optimize`)
- Optional PostgreSQL-backed optimization run history (`/runs`)
- FastMCP tool server for LLM tool-calling
- Agent orchestration loop (`agent_loop.py`) with multi-provider LLM support
- Docker-based local/cloud runtime
- Domain analytics and visualization layer in R

Current scope note:
- Forecasting baseline is now enabled via `forecast_demand` MCP tool.
- Current priority is optimization + forecasting + post-analysis workflow quality.

## Current Production Direction

Active stack:
- `python_solvers/` (API + MCP + routing)
- `julia_solvers/` (MIP/GA/CG/ST/NLP/MINLP runtime)
- `r_solvers/` (post-analysis and plotting)

Reference-only archives:
- `_legacy/`
- `_legacy_django/`
- `_legacy_go/`

## Implementation Status (As-Is, 2026-04-16)

This section reflects code that is currently present in the repository (not roadmap intent).

### 1) API Layer (`python_solvers/api`)

Implemented:
- `GET /health`: returns service status and DB enable flag.
- `POST /optimize`: executes domain + solver route and returns normalized solve response.
- `GET /runs`: returns recent persisted optimization runs (when `DATABASE_URL` is configured).

Behavior details:
- API startup initializes DB schema via SQLAlchemy.
- `/optimize` attempts to persist run history and injects `run_id` on success.
- If DB write fails, response keeps optimization result and adds `error_msg=database_write_failed`.

### 2) Optimization Routing (`python_solvers/api/solver_api.py`)

Implemented routing logic:
- Domain `vrp` or solver `cp` -> Python runtime path (`bridge_logic.run_python_runtime`).
- Otherwise -> Julia runtime path via `cli_solver` payload bridge.

Supported output normalization fields:
- `status`, `objective`, `variables`, `constraints`, `solve_time`, `lp_sensitivity`, `details`, `sensitivity`, `error_msg`.

### 3) MCP Tool Server (`python_solvers/mcp_server.py`)

Implemented tools:
- `read_company_data`
- `forecast_demand`
- `bridge_forecast_to_payload`
- `get_target_schema`
- `map_to_target_schema`
- `optimize`
- `analyze_with_r`

Validation/guard behavior:
- Domain payload is validated with domain-specific Pydantic models before optimize runtime call.
- Validation errors are transformed into actionable MCP error payloads.
- Infeasible/unbounded solve outcomes are converted to retry hints via logical feedback helpers.

### 4) Forecasting (`python_solvers/forecasting.py`)

Implemented:
- Main engine: StatsForecast `AutoARIMA`.
- Fallback engine: lightweight last-value baseline with statistical CI approximation.
- Multi-item and aggregated single-series modes.

Output contract:
- `forecast_rows` with `item`, `date`, `point`, `lower`, `upper`, `recommended_demand`.
- Metadata: `horizon`, `freq`, `confidence_level`, `series_count`, `engine`.

### 5) Forecast -> Optimization Bridge (`python_solvers/mcp_utils.py`)

Implemented:
- Demand injection into domain payload by forecast bound (`lower|point|upper|recommended_demand`).
- Configurable rounding (`ceil|floor|round`) and `min_demand` floor.
- Name-based matching plus `all` fallback.
- Domain-aware demand update targets:
  - `packing.Items[*].Demand`
  - `cutting.Items[*].Demand`
  - `scheduling.Shifts[*].Demand`
  - `vrp.Nodes[1:].Demand`

### 6) R Post-Analysis Bridge (`python_solvers/r_bridge.py`)

Implemented:
- rpy2 bridge setup with Windows DLL path handling.
- Calls into `r_solvers` pipeline:
  - `process_results`
  - `process_sensitivity`
  - `process_decision_analytics`
  - `build_executive_summary`

Returned analysis bundle:
- `processed_result`, `sensitivity`, `decision_analytics`, `executive_summary`.

### 7) Agent Loop (`agent_loop.py`, `agent_core/*`)

Implemented:
- Providers: `ollama`, `openai`-compatible, `google`.
- Per-call timeout and fallback model failover.
- Tool-call normalization for cross-provider formats.
- Auto-canonicalization of optimize payload keys.
- Auto-inference helper for packing mapping rules.
- Retry guidance insertion on retryable tool errors.

Current guardrails:
- Context trimming (`MAX_CONTEXT_MESSAGES`).
- Max step termination with trace output.
- Successful early-stop on optimal solve.

### 8) Persistence (`python_solvers/db.py`)

Implemented:
- Optional PostgreSQL persistence through `DATABASE_URL`.
- Auto URL normalization to `postgresql+psycopg`.
- Optimization run schema with request/result JSON snapshots.
- Recent run listing endpoint support.

### 9) Deployment Assets

Implemented assets:
- Local compose stack (`docker/docker-compose.yml`).
- Cloud-target compose variants for AWS/Azure/GCP.
- Bootstrap and deploy scripts in `deploy/*`.

### 10) Known Gaps (Not Yet Implemented)

Still pending in codebase:
- End-to-end Trace ID propagation.
- Structured JSON logging standardization across agent + tools.
- Token/cost metering and dashboards.
- Idempotency key enforcement for optimize path.
- AuthN/AuthZ and secrets manager migration.
- Circuit breaker and unified retry policy for external LLM calls.

Use `TODO.md` as the execution checklist for these production-hardening items.

## Architecture

```text
User / App / Agent
  -> python_solvers/api/main.py (FastAPI)
  -> python_solvers/api/solver_api.py (domain/solver routing)
  -> Python OR-Tools path OR Julia runtime path
  -> Structured JSON result

LLM Agent Loop
  -> FastMCP tools (read_company_data, forecast_demand, bridge_forecast_to_payload, get_target_schema, map_to_target_schema, optimize, analyze_with_r)
  -> self-healing retry + mapping auto-fill + argument normalization
```

## LLM Providers in `agent_loop.py`

Supported providers:
- `ollama`
- `openai` (OpenAI-compatible endpoints)
- `google` (Gemini API)

Recommended default for cloud:
- `--llm-provider google`
- model `gemma-4-26b-a4b-it`

## Quick Start (Local)

```powershell
cd C:\Projects\OptiMystic
.\.venv\Scripts\python.exe -m pip install -r python_solvers\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn python_solvers.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```powershell
curl http://127.0.0.1:8000/health
```

Optional PostgreSQL persistence:

```powershell
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/optimystic"
curl http://127.0.0.1:8000/runs
```

## Agent Loop Smoke (Google)

```powershell
$env:GOOGLE_API_KEY="<YOUR_KEY>"
.\.venv\Scripts\python.exe agent_loop.py --llm-provider google --max-steps 10
```

Expected success signal:
- `"ok": true`
- `"status": "Optimal"` in optimize result trace

## R Post-Analysis via MCP

The MCP server now exposes `analyze_with_r` for post-analysis on solver outputs.

- Required: `mode` and one of `run_result` or `run_results`
- Optional: `store`, `confidence`, `n_boot`, `seed`
- Returns: `processed_result`, `sensitivity`, `decision_analytics`, `executive_summary`

This is intended for diagnostics/reporting after optimization, not for forecasting.

## Forecasting via MCP

The MCP server exposes `forecast_demand` powered by StatsForecast AutoARIMA.

- Required: `file_path`, `time_col`, `target_col`
- Optional: `item_col`, `horizon`, `freq`, `confidence_level`
- Returns: point/lower/upper forecast rows and `recommended_demand` (upper bound)

Runtime note:
- If `statsforecast` is available, it uses AutoARIMA.
- If not installed, it falls back to a lightweight CPU baseline (`fallback-last-value`) so the pipeline remains available.

Windows + Python 3.13 note:
- `statsforecast` can fail to install in some Python 3.13 environments.
- Recommended path is a dedicated Python 3.12 env for forecasting engine activation.

```powershell
cd C:\Projects\OptiMystic
.\scripts\setup_py312_forecasting.ps1
```

Windows runtime sanity check (Julia + R):

```powershell
cd C:\Projects\OptiMystic

# 1) Add Rscript path for current user/session (one-time)
.\scripts\setup_r_path.ps1

# 2) Julia module load smoke (quote-safe)
Set-Content -Path .tmp_julia_smoke.jl -Value 'include("julia_solvers/src/main.jl"); println("julia_router_load_ok")'
julia --project=julia_solvers .tmp_julia_smoke.jl
Remove-Item .tmp_julia_smoke.jl -Force

# 3) R processor load smoke
Rscript -e "setwd('r_solvers'); source('utils.R'); source('processors.R'); cat('r_processors_load_ok\n')"
```

Tip:
- On Windows PowerShell, prefer `.jl` temp-file execution over `julia -e` for complex strings.
- For Julia CLI `--params`, pass raw JSON (avoid extra escaping layers).

Recommended integration for optimization:
1. Forecast with `forecast_demand`
2. Bridge with `bridge_forecast_to_payload` using bound=`upper`
3. Run `optimize`

## Docker Local Run

API + Jupyter:

```powershell
docker compose -f docker/docker-compose.yml up --build api jupyterlab
```

Agent smoke (Google):

```powershell
$env:GOOGLE_API_KEY="<YOUR_KEY>"
docker compose -f docker/docker-compose.yml --profile agent run --rm agent-loop
```

## Cloud Deployment

Available runbooks:
- AWS: `deploy/aws/README.md`
- Azure: `deploy/azure/README.md`
- GCP: `deploy/gcp/README.md`

Compose files:
- `docker/docker-compose.aws.yml`
- `docker/docker-compose.azure.yml`
- `docker/docker-compose.gcp.yml`

## Minimal Request Contract

```json
{
  "domain": "packing",
  "solver": "mip",
  "params": {
    "Items": [
      {"Name": "A", "Weight": 2, "Value": 10, "Demand": 2},
      {"Name": "B", "Weight": 3, "Value": 12, "Demand": 1}
    ],
    "Vehicles": [
      {"Capacity": 5}
    ]
  }
}
```

## Domain-Solver Guide

| Goal | Domain | Solver | Runtime |
|------|--------|--------|---------|
| Shift scheduling | `scheduling` | `cp` | Python |
| Vehicle routing | `vrp` | `mip` (routing path) | Python |
| Cutting stock | `cutting` | `cg` / `mip` | Julia |
| Bin packing | `packing` | `mip` | Julia |
| Stochastic resourcing | `resourcing` | `st` | Julia |
| Nonlinear optimization | `generic` | `nlp` | Julia |
| Mixed-integer nonlinear optimization | `generic` | `minlp` | Julia |

## Module Docs

- `python_solvers/README.md`
- `julia_solvers/README.md`
- `r_solvers/README.md`
- `deploy/aws/README.md`
- `deploy/azure/README.md`
- `deploy/gcp/README.md`

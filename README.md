# OptiMystic

OptiMystic is a multi-domain optimization platform built on Python, Julia, and R.

## What Is Included

- FastAPI optimization API (`/health`, `/optimize`)
- Optional PostgreSQL-backed optimization run history (`/runs`)
- FastMCP tool server for LLM tool-calling
- Agent orchestration loop (`agent_loop.py`) with multi-provider LLM support
- Docker-based local/cloud runtime
- Domain analytics and visualization layer in R

## Current Production Direction

Active stack:
- `python_solvers/` (API + MCP + routing)
- `julia_solvers/` (MIP/GA/CG/ST/NLP/MINLP runtime)
- `r_solvers/` (post-analysis and plotting)

Reference-only archives:
- `_legacy/`
- `_legacy_django/`
- `_legacy_go/`

## Architecture

```text
User / App / Agent
  -> python_solvers/api/main.py (FastAPI)
  -> python_solvers/api/solver_api.py (domain/solver routing)
  -> Python OR-Tools path OR Julia runtime path
  -> Structured JSON result

LLM Agent Loop
  -> FastMCP tools (read_company_data, get_target_schema, map_to_target_schema, optimize)
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

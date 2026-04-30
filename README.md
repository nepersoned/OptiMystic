# OptiMystic

**Conversational operations optimization.** Use a Google Sheets sidebar, talk to the AI, get an optimized plan.

OptiMystic lets operations teams solve complex logistics, scheduling, and resource problems through natural conversation — no solver expertise required. The AI reads your data, asks when it needs clarification, and runs the full optimization pipeline on your behalf.

---

## What It Does

**The loop:**

```
User uploads messy Excel/CSV
  → AI reads the data and identifies the problem domain
  → AI asks one clarifying question at a time when data is ambiguous
  → User fills in what only they know (column meanings, constraints, context)
  → AI runs: ARIMA forecast → optimization solver → R post-analysis
  → Results and recommendations delivered in plain language
```

**Example conversation:**

> User: "Our delivery routes are taking way too long."
>
> AI: "I can see order locations, but I don't see a depot row. Which location should trucks start from?"
>
> User: "First row is the depot."
>
> AI: "Got it. Running VRP optimization now... Done. 6 vehicles, total distance reduced by 18%. Route 3 is overloaded — want me to split it?"

---

## Architecture

```
Frontend (Google Sheets Add-on, target)
  └─ Sidebar chat UI — user request, clarification, optimization trigger
  └─ Active sheet I/O — read selected range, write result tables/KPI summary
  └─ Distribution — Google Workspace (internal first, Marketplace later)

Legacy frontend (archived)
  └─ React + TypeScript UI moved to _legacy_frontend (reference only)

Backend (FastAPI + Python)
  └─ Dataset API: upload / grid / cells / versions / optimize / chat
  └─ Chat endpoint  → agent loop (MCP tools) → Gemini fallback → heuristic
  └─ Solver routing: Python (VRP, CP) | Julia (MIP, GA, CG, ST, NLP, MINLP)
  └─ Chart + summary builders for all 6 domains
  └─ R post-analysis bridge: analyze_with_r() — sensitivity, decision analytics,
                              executive summary (all domains)

Agent Core
  └─ Multi-step tool-calling loop (up to 8 steps)
  └─ Tools: read_company_data, forecast_demand, bridge_forecast_to_payload,
            get_target_schema, map_to_target_schema, optimize, analyze_with_r
  └─ LLM providers: Google (Gemini/Gemma), Ollama (local), OpenAI-compatible

LLM Roadmap
  └─ Now: Google Gemini API (cloud)
  └─ Target: Gemma 4 on-device via Ollama (no API cost, no data egress)
```

---

## Domain Coverage

| Problem | Domain | Solver | Runtime |
|---------|--------|--------|---------|
| Vehicle routing | `vrp` | `mip` | Python |
| Shift scheduling | `scheduling` | `cp` | Python |
| Cutting stock | `cutting` | `cg` / `mip` | Julia |
| Bin packing | `packing` | `mip` | Julia |
| Stochastic resourcing | `resourcing` | `st` | Julia |
| Nonlinear optimization | `generic` | `nlp` / `minlp` | Julia |

---

## Quick Start (Local)

**1. Install and run the API:**

```bash
pip install -r python_solvers/requirements.txt
uvicorn python_solvers.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**2. Set environment variables:**

```bash
# Required for AI chat
export GOOGLE_API_KEY="AIza..."

# Required for dataset persistence
export DATABASE_URL="postgresql://user:pass@localhost:5432/optimystic"
```

**3. Health check:**

```bash
curl http://localhost:8000/health
# {"status":"ok","database_enabled":true}
```

---

## Agent Loop (CLI)

Run the full optimization pipeline from the command line:

```bash
export GOOGLE_API_KEY="AIza..."
python agent_loop.py \
  --llm-provider google \
  --model gemini-2.5-flash \
  --max-steps 8
```

The agent will:
1. Read company data from a file
2. Ask clarifying questions if data is ambiguous
3. Run demand forecasting (AutoARIMA via StatsForecast)
4. Map data to the solver schema
5. Run the appropriate solver
6. Run R post-analysis and return an executive summary

---

## Product Direction (2026-04)

- Primary UX is Google Sheets Add-on (documentation finalized, implementation pending).
- Existing React UI is intentionally archived as legacy in _legacy_frontend.
- Backend stack (FastAPI + Python/Julia/R + MCP tools) remains the core execution engine.
- This repository is now managed as Sheets-first, backend-strong architecture.

## Recent Updates (2026-04-30)

- Google Sheets sidebar chat now calls `/sheets/chat` directly from `Sidebar.html` via `fetch`, after loading active sheet data with `google.script.run.getSheetData()`.
- Apps Script server helper was hardened with request timeout settings (`deadline: 30`) and a quick connectivity helper (`pingBackend`).
- Sheets payload size was reduced (`rows.slice(1, 201)` in add-on, `_MAX_ROWS_CONTEXT = 30` in API) to keep chat latency predictable.
- Sheets API model selection now follows `OPTIMYSTIC_CHAT_MODEL`, defaulting to `agent_core.config.DEFAULT_GOOGLE_MODEL` when available.
- Google provider client construction is now cached in-process to avoid repeated client instantiation overhead.
- Added `gsheets_addon/.clasp.json` to bind local add-on files to the Apps Script project for `clasp push` workflow.

---

## API Reference

### Dataset Workflow

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/datasets/upload` | Upload CSV/Excel, infers domain automatically |
| `GET` | `/datasets/{id}/grid` | Fetch dataset rows + columns (with optional version) |
| `PATCH` | `/datasets/{id}/cells` | Apply cell edits, creates new version |
| `GET` | `/datasets/{id}/versions` | List version history |
| `POST` | `/datasets/{id}/versions/{v}/restore` | Restore a previous version |
| `POST` | `/datasets/{id}/chat` | AI chat — multi-turn, agent-powered |
| `POST` | `/datasets/{id}/optimize` | Run solver on current dataset version |

### Direct Optimization

```json
POST /optimize
{
  "domain": "vrp",
  "solver": "mip",
  "params": {
    "Nodes": [
      {"Name": "Depot", "X": 126.99, "Y": 37.56, "Demand": 0},
      {"Name": "Stop A", "X": 127.02, "Y": 37.50, "Demand": 120}
    ],
    "Vehicles": [{"Name": "Truck 1", "Capacity": 500}]
  }
}
```

---

## Chat Endpoint

`POST /datasets/{id}/chat`

```json
{
  "message": "Our Gangnam deliveries are always delayed.",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

**Response:**

```json
{
  "reply": "I can see the time windows for Gangnam are quite tight. Want me to run a VRP solve and see where the bottleneck is?",
  "recommended_domain": "vrp",
  "recommended_solver": "mip",
  "suggested_diffs": []
}
```

The chat endpoint runs a full agent loop with tool access (forecast, optimize, R analysis) first, and falls back to a direct Gemini call if the agent fails.

---

## MCP Tools

The agent uses these tools internally during chat and CLI runs:

| Tool | What it does |
|------|-------------|
| `read_company_data` | Load and inspect a CSV/Excel file |
| `forecast_demand` | AutoARIMA demand forecast (StatsForecast) |
| `bridge_forecast_to_payload` | Inject forecast results into solver input |
| `get_target_schema` | Fetch the required schema for a domain |
| `map_to_target_schema` | Map source columns to target schema |
| `optimize` | Run the solver with validation and retry hints |
| `analyze_with_r` | Post-solve sensitivity and decision analytics |

---

## Forecasting

Powered by StatsForecast AutoARIMA. Falls back to a lightweight last-value baseline if StatsForecast is unavailable.

**Python 3.13 note:** StatsForecast may fail to install. Use Python 3.12:

```bash
.\scripts\setup_py312_forecasting.ps1
```

---

## Docker

```bash
# Local stack (API + JupyterLab) — builds everything from docker/Dockerfile
docker compose -f docker/docker-compose.yml up --build api jupyterlab

# With AI chat and database enabled
GOOGLE_API_KEY="..." DATABASE_URL="postgresql://..." \
  docker compose -f docker/docker-compose.yml up --build api

# Agent smoke test
GOOGLE_API_KEY="..." docker compose -f docker/docker-compose.yml --profile agent run --rm agent-loop
```

**Docker files:**

| File | Purpose |
|------|---------|
| `docker/Dockerfile` | Local dev — all-in-one (deps + code, single build) |
| `Dockerfile.deps` | Production deps layer — pushed to GCR, reused by Cloud Run |
| `Dockerfile` | Production runtime — code only, inherits from deps image |

---

## Cloud Deployment (GCP)

Production runs on Google Cloud Run (`asia-northeast3`), deployed via Cloud Build on every push to `main`.

```bash
# Check build status
gcloud builds list --project optimystic-493605 --limit=5

# Verify deployment
curl https://optimystic-826180130763.asia-northeast3.run.app/health
```

Build config: `cloudbuild.yaml` | App image: `Dockerfile` | Deps image: `Dockerfile.deps`

---

## Project Structure

```
OptiMystic/
├── frontend/          # React + TypeScript + Vite
├── python_solvers/    # FastAPI + MCP server + Python solvers
├── julia_solvers/     # MIP / GA / CG / ST / NLP / MINLP
├── r_solvers/         # Post-analysis and visualization
├── agent_core/        # LLM agent loop + providers
├── deploy/            # AWS / Azure / GCP runbooks
└── docker/            # Compose files
```

Sub-module docs: [`python_solvers/`](python_solvers/README.md) · [`julia_solvers/`](julia_solvers/README.md) · [`r_solvers/`](r_solvers/README.md)

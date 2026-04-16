# OptiMystic

Multi-domain optimization platform based on Python, Julia, and R.

## What This Repository Delivers

- Interactive development with JupyterLab (Python/Julia/R kernels).
- HTTP optimization API based on FastAPI.
- Domain-mapped solver routing across CP, VRP, MIP, GA, CG, ST, NLP, MINLP.
- Post-analysis analytics and plotting with R (expanding scope).

## Current Architecture

```text
HTTP Client
  -> FastAPI endpoint (python_solvers/api/main.py)
  -> Python solver router (python_solvers/api/solver_api.py)
  -> Python runtime (CP/VRP) or Julia delegation (MIP/GA/CG/ST/NLP/MINLP)
  -> JSON response
```

Runtime split:
- Python (OR-Tools): scheduling (CP), vrp (routing)
- Julia (JuMP ecosystem): mip, ga, cg, st, nlp, minlp
- R: dedicated post-analysis layer for deeper business interpretation, diagnostics, and visualization

## Repository Layout

- `python_solvers/` - Active Python runtime and FastAPI service
- `julia_solvers/` - Julia solver implementations
- `r_solvers/` - R processors and visualization helpers
- `examples/` - Integration and debugging notebooks/scripts
- `_legacy/`, `_legacy_django/`, `_legacy_go/` - Archived implementations (reference only)

## API Endpoints

- `GET /health`
- `POST /optimize`

## MCP Endpoint (Phase 1, 1.5, 2)

- `python_solvers/mcp_server.py` exposes OptiMystic optimize runtime as a FastMCP tool.
- Tool names: `optimize`, `read_company_data`, `get_target_schema`
- Input schema: `OptimizationRequest` with highly descriptive field metadata for LLM tool-use guidance.
- Dependency note: keep `fastmcp<3` to avoid FastAPI/Starlette major-version conflicts in this repo.

Phase 1.5 self-healing behavior in `optimize`:
- Validation feedback: catches schema/type errors and returns `validation_error` with structured details.
- Logical feedback: if solver returns `Infeasible` or `Unbounded`, returns actionable retry guidance instead of a silent fail.

Phase 2 data bridge tools:
- `read_company_data(file_path, max_rows=3)`: returns file metadata, row count, columns, and sampled rows.
- `get_target_schema(domain)`: returns domain-specific target JSON schema for mapping.

Run locally:

```powershell
cd C:\Your\Path\OptiMystic
pip install -r python_solvers\requirements.txt
python -m python_solvers.mcp_server
```

Claude Desktop integration (example `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "optimystic": {
      "command": "python",
      "args": ["-m", "python_solvers.mcp_server"],
      "cwd": "C:/Your/Path/OptiMystic"
    }
  }
}
```

Then test in Claude Desktop with prompts such as:
- "수요 10, 용량 5인 포장 문제로 optimize 호출해줘"
- "vrp 도메인으로 기본 라우팅 최적화 실행해줘"

If Claude Desktop is not installed, run a local MCP smoke test directly in Python:

```powershell
cd C:\Your\Path\OptiMystic
.\.venv\Scripts\python.exe -c "import asyncio, json; from python_solvers.mcp_server import mcp; args={'request': {'domain':'scheduling','solver':'cp','params': {'Employees':[{'Name':'E1','MaxShifts':1},{'Name':'E2','MaxShifts':1}], 'Shifts':[{'Name':'Morning','Demand':1}], 'Values': {'E1': {'Morning': 3}, 'E2': {'Morning': 2}}, 'MaxShiftsPerEmployee':1, 'MinShiftsPerEmployee':0, 'Rules':[], 'Seed':42, 'Workers':1, 'TimeLimit':5}}}; res=asyncio.run(mcp._tool_manager.call_tool('optimize', args)); print(json.dumps(res.structured_content, ensure_ascii=False))"
```

Expected signal:
- `ok: True`
- `result.status: Optimal` (or another solver status if your data differs)

Phase 2 smoke examples:

```powershell
cd C:\Your\Path\OptiMystic
.\.venv\Scripts\python.exe -c "import asyncio, json; from python_solvers.mcp_server import mcp; res=asyncio.run(mcp._tool_manager.call_tool('get_target_schema', {'domain':'packing'})); print(json.dumps(res.structured_content, ensure_ascii=False)[:800])"
```

```powershell
cd C:\Your\Path\OptiMystic
.\.venv\Scripts\python.exe -c "import asyncio, json; from python_solvers.mcp_server import mcp; res=asyncio.run(mcp._tool_manager.call_tool('read_company_data', {'file_path':'examples/sample.csv','max_rows':3})); print(json.dumps(res.structured_content, ensure_ascii=False))"
```

## Quick Start

### Option 1: JupyterLab

```powershell
cd C:\Your\Path\OptiMystic
pip install -r python_solvers\requirements.txt
pip install jupyterlab
jupyter lab
```

Open `examples/test_jupyterlab_full_pipeline.ipynb` and run the sections for Python, Julia, and R.

### Option 2: FastAPI (Local)

```powershell
cd C:\Your\Path\OptiMystic
pip install -r python_solvers\requirements.txt
uvicorn python_solvers.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Then call `http://localhost:8000/optimize`.

### Option 3: Docker Compose

Docker Compose is now aligned with the current Python/Julia runtime.

Run API + JupyterLab:

```powershell
cd C:\Your\Path\OptiMystic
docker compose up --build api jupyterlab
```

- API: `http://localhost:8000` (`/health`, `/optimize`)
- JupyterLab: `http://localhost:8888`

Optional agent-loop container (OpenAI-compatible endpoint such as vLLM):

```powershell
cd C:\Your\Path\OptiMystic
docker compose --profile agent run --rm \
  -e OPENAI_BASE_URL=http://<YOUR_VLLM_HOST>:8000/v1 \
  -e OPENAI_API_KEY=EMPTY \
  agent-loop
```

You can also run the same loop against local Ollama by changing runtime args:

```powershell
docker compose run --rm api \
  python3 agent_loop.py --llm-provider ollama --model gemma4:e2b
```

AWS deployment preflight runbook:
- `deploy/aws/README.md`

## Request Contract

Minimal request example:

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

Minimal response example:

```json
{
  "status": "Optimal",
  "objective": 22,
  "solve_time": 0.02,
  "variables": {},
  "constraints": {},
  "details": {},
  "sensitivity": null
}
```

## Domain-Solver Guide

| Goal | Domain | Solver | Runtime |
|------|--------|--------|---------|
| Shift scheduling | `scheduling` | `cp` | Python |
| Vehicle routing | `vrp` | `mip` (routed to OR-Tools VRP path) | Python |
| Cutting stock | `cutting` | `cg` / `mip` | Julia |
| Bin packing | `packing` | `mip` | Julia |
| Stochastic resourcing | `resourcing` | `st` | Julia |
| Nonlinear optimization | `generic` | `nlp` | Julia |
| Mixed-integer nonlinear optimization | `generic` | `minlp` | Julia |

## Documentation

- [python_solvers/README.md](python_solvers/README.md)
- [julia_solvers/README.md](julia_solvers/README.md)
- [r_solvers/README.md](r_solvers/README.md)
- [deploy/aws/README.md](deploy/aws/README.md)
- [deploy/azure/README.md](deploy/azure/README.md)
- [_legacy_go/README.md](_legacy_go/README.md)


# OptiMystic TODO

This document is the single execution checklist until production readiness.

## Release Milestone (2026-04-17)

- [x] Readiness baseline aligned to 90+ across Core, Agent, Infra, and Production

## Usage Rules

- Start work: `[ ]` -> `[~]`
- Complete work: `[~]` -> `[x]`
- Add new tasks directly under the relevant priority section
- If a task is ambiguous, define the completion criteria first

## 0. Immediate Tasks (Top Priority)

- [~] Create and propagate a Trace ID across the full request path
- [~] Standardize agent_loop and tool-call logs into structured JSON
- [~] Track model call cost metrics (tokens/cost per request)
- [~] Design and apply idempotency keys for optimize execution
- [~] Standardize timeout/retry/backoff policy for Google API calls

## 1. Reliability

- [ ] Introduce a circuit breaker for external LLM calls
- [~] Define a standard fallback response for tool execution failures
- [ ] Consolidate common exception handling (consistent error codes)
- [~] Unify timeout policies for long-running tasks
- [ ] Create a retryable vs non-retryable error classification table

Completion Criteria:
- [ ] No duplicate execution or duplicate billing for repeated identical requests
- [ ] Service stays available in degraded mode during external model outages

## 2. Observability

- [ ] Link request-level Trace ID with tool_call_id
- [ ] Break down latency by stage (LLM, tool, solver)
- [ ] Build dashboards for failure rate, latency, and cost
- [ ] Configure threshold alerts (failure, latency, cost spikes)
- [ ] Finalize log retention policy (duration/capacity)

Completion Criteria:
- [ ] Root cause is traceable via Trace ID for at least 90% of incidents

## 3. Security & Ops

- [ ] Migrate secrets (e.g., GOOGLE_API_KEY) to a secret manager
- [~] Apply API authentication (AuthN)
- [~] Apply project/org-level authorization policies (AuthZ)
- [ ] Store audit logs
- [ ] Validate strict environment separation (dev/stage/prod)

Completion Criteria:
- [ ] Zero plaintext secrets in code/config files
- [ ] Unauthorized data access blocking tests pass

## 4. Quality

- [ ] Freeze agent regression test scenarios (core domains)
- [ ] Add MCP tool contract tests
- [ ] Build fixture datasets for failure reproduction
- [ ] Automate performance smoke tests
- [ ] Configure CI quality gates (block merge on test failure)

Completion Criteria:
- [ ] Automated regression covers at least 80% of core scenarios

## 5. Productization

- [ ] Define DB memory schema (session, message, tool_trace, summary)
- [ ] Design a separate natural-language chat endpoint (`/chat`)
- [ ] Connect asynchronous post-processing pipeline for R analytics
- [ ] Add result report retrieval API
- [ ] Provide an operator status page (health/recent errors/cost)
- [x] Add optional PostgreSQL-backed optimization run history endpoint (`/runs`)
- [x] Expose R post-analysis capability as MCP tool (`analyze_with_r`)
- [x] Add StatsForecast-based forecasting MCP tool (`forecast_demand`) baseline
- [x] Add forecast-to-optimization bridge MCP tool (`bridge_forecast_to_payload`)

## 6. Docker/Deployment Operations

- [ ] Standardize documented run commands for the docker folder structure
- [ ] Smoke-validate deployment scripts for AWS/Azure/GCP
- [ ] Add deployment rollback runbook
- [ ] Finalize image tagging policy (commit SHA-based)
- [ ] Finalize production deployment checklist

## 7. Code-Verified Snapshot (2026-04-16)

- [x] API endpoints available: `/health`, `/optimize`, `/runs` (DB optional)
- [x] MCP tools available: `read_company_data`, `get_target_schema`, `map_to_target_schema`, `forecast_demand`, `bridge_forecast_to_payload`, `optimize`, `analyze_with_r`
- [x] Agent multi-provider support (`ollama`, `openai`-compatible, `google`)
- [x] Agent fallback-model switch + max-step guard + context trimming
- [x] Forecasting fallback path when StatsForecast is unavailable
- [x] R post-analysis bridge integrated via `rpy2`
- [x] PostgreSQL persistence model for optimization runs

Partial implementation notes:
- [~] FastAPI `/optimize` and MCP `optimize` now propagate `trace_id` (header/payload/error/result). End-to-end linking with MCP `tool_call_id` is still pending
- [~] `/optimize` and `/runs` now support API-key guard via `X-API-Key` when `OPTIMYSTIC_API_KEYS` is configured
- [~] API key to tenant mapping (`OPTIMYSTIC_API_KEY_TENANTS`) now enables tenant attribution and tenant-scoped `/runs` filtering
- [~] `/optimize` now supports `Idempotency-Key` replay/conflict handling backed by DB (disabled when DB is off)
- [~] Agent loop now collects per-step LLM token usage, estimates USD cost with configurable rates, and supports budget guard via `OPTIMYSTIC_MAX_ESTIMATED_COST_USD`
- [~] Structured JSON logging formatter is applied to API startup and agent loop runtime
- [~] Google API key can be loaded from Secret Manager when `OPTIMYSTIC_GOOGLE_API_KEY_SECRET` and `GOOGLE_CLOUD_PROJECT` are set
- [~] Timeout/fallback exists in agent calls, but unified retry/backoff policy is not standardized yet
- [~] Tool error response shape is mostly standardized as `{ok:false,error:{code,message}}`, but cross-module unification is pending

## Notes

- Use this file as the single source of truth
- Track progress via checkbox state instead of weekly plans

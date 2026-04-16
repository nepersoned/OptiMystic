# OptiMystic TODO

This document is the single execution checklist until production readiness.

## Usage Rules

- Start work: `[ ]` -> `[~]`
- Complete work: `[~]` -> `[x]`
- Add new tasks directly under the relevant priority section
- If a task is ambiguous, define the completion criteria first

## 0. Immediate Tasks (Top Priority)

- [ ] Create and propagate a Trace ID across the full request path
- [ ] Standardize agent_loop and tool-call logs into structured JSON
- [ ] Track model call cost metrics (tokens/cost per request)
- [ ] Design and apply idempotency keys for optimize execution
- [ ] Standardize timeout/retry/backoff policy for Google API calls

## 1. Reliability

- [ ] Introduce a circuit breaker for external LLM calls
- [ ] Define a standard fallback response for tool execution failures
- [ ] Consolidate common exception handling (consistent error codes)
- [ ] Unify timeout policies for long-running tasks
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
- [ ] Apply API authentication (AuthN)
- [ ] Apply project/org-level authorization policies (AuthZ)
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

## 6. Docker/Deployment Operations

- [ ] Standardize documented run commands for the docker folder structure
- [ ] Smoke-validate deployment scripts for AWS/Azure/GCP
- [ ] Add deployment rollback runbook
- [ ] Finalize image tagging policy (commit SHA-based)
- [ ] Finalize production deployment checklist

## Notes

- Use this file as the single source of truth
- Track progress via checkbox state instead of weekly plans

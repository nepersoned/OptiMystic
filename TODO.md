# OptiMystic TODO

This is the single checklist for shipping a usable internal beta (billing excluded).
Current strategy is Google Sheets Add-on first, with React frontend archived.

## Status Legend

- `[ ]` not started
- `[~]` in progress
- `[x]` done

## 0) Today's Wrap-up (2026-04-29)

- [x] React frontend archived to legacy folder
- [x] LLM default moved to Gemini 2.5 Flash path
- [x] Sheets-first direction confirmed (documentation)
- [ ] Google Sheets Add-on implementation (not started)

## 1) Beta North Star (Must Hold)

- [ ] Excel-like UX + strict data quality guardrails
- [ ] Agent proposes diffs only (no auto-apply)
- [ ] Dataset versioning + rollback always available
- [ ] Every optimize result includes business-impact summary line

Completion Criteria:
- [ ] A non-technical tester can run upload -> edit -> optimize in under 10 minutes
- [ ] No silent data mutation without user approval

## 2) Google Sheets Add-on Delivery (Top Priority)

## 2.1 Sidebar UX
- [ ] Sidebar chat UI (KR/EN)
- [ ] Intent split: conversation vs action request
- [ ] Show recommended domain/solver and one-line reason
- [ ] Render and confirm diff proposal (approve/reject)

## 2.2 Sheet Data Bridge
- [ ] Read selected range as structured payload
- [ ] Validate schema and block critical errors
- [ ] Show quality badge (`good/warning/error`)
- [ ] Write normalized/optimized output to target tabs

## 2.3 Result Rendering in Sheets
- [ ] KPI summary block (objective, solve_time, status)
- [ ] KPI delta line (improvement vs baseline)
- [ ] Bottleneck top 3 and next action line
- [ ] Export-ready result tab structure

## 2.4 Packaging and Deployment
- [ ] Apps Script project bootstrap
- [ ] Internal deployment guide (workspace admin)
- [ ] Auth mode decision (API key vs service auth)
- [ ] Marketplace readiness checklist (later)

Completion Criteria:
- [ ] Spreadsheet user can run input -> optimize -> output in under 10 minutes
- [ ] No silent mutation without explicit approval

## 3) API/Product Contract

- [x] `POST /datasets/upload`
- [ ] `POST /datasets/{id}/normalize`
- [x] `GET /datasets/{id}/grid`
- [x] `PATCH /datasets/{id}/cells`
- [x] `POST /datasets/{id}/chat`
- [x] `POST /datasets/{id}/optimize`
- [x] `GET /datasets/{id}/versions`
- [x] `POST /datasets/{id}/versions/{version}/restore`

Completion Criteria:
- [ ] Sheets Add-on can complete full workflow using only documented endpoints

## 4) Data Normalization + Validation Layer

- [ ] Apply rule-based normalization preview before commit
- [ ] Track rule application report (before/after)
- [ ] Implement blocker checks:
  - [ ] Missing process route
  - [ ] Missing machine capacity
  - [ ] Invalid due-date logic
- [ ] Add warnings for non-blocking data issues

Completion Criteria:
- [ ] "Data cannot be scheduled" reason is explicit and actionable

## 5) Optimization + Explainability

- [x] Keep current optimize path stable (`/optimize`)
- [x] Chart + summary builders for all 6 domains
- [x] R post-analysis bridge unified (`analyze_with_r`)
- [ ] Add auto domain/solver recommendation module for UI flow
- [ ] Persist recommendation reason text
- [ ] Add KPI delta renderer for result summary

Completion Criteria:
- [ ] Each run explains: why solver chosen, what improved, what bottleneck remains

## 6) Ops and Monitoring (Postponed by decision)

Decision:
- Deferred until account migration and beta UX stabilization

Deferred tasks:
- [ ] Uptime checks
- [ ] Alert channel/policy
- [ ] Failure/latency/cost dashboards

## 7) Database Integration (Postponed by decision)

Decision:
- Deferred until account migration and schema lock for beta

Deferred tasks:
- [ ] External PostgreSQL provision
- [ ] `DATABASE_URL` production wiring
- [ ] Run history and dataset persistence hardening

## 8) Internal Beta Validation

- [ ] Run 20+ internal workflows using real-like spreadsheets
- [ ] Log top 10 UX frictions
- [ ] Fix top 3 friction points before external testers
- [ ] Freeze beta checklist and demo script

Completion Criteria:
- [ ] Internal tester can complete workflow without developer intervention

## Notes

- Product-first rule: do not add deep solver sophistication before Sheets workflow usability is proven.
- Billing remains out of scope until internal beta flow is stable.

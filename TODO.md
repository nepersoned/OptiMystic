# OptiMystic TODO

This is the single checklist for shipping a usable internal beta (billing excluded).

## Status Legend

- `[ ]` not started
- `[~]` in progress
- `[x]` done

## 0) Today's Wrap-up (2026-04-18)

- [x] Cloud Run startup issue fixed and deployment recovered
- [x] Health endpoint verified (`status=ok`)
- [x] UI beta concept note added (`UI_BETA_IDEA_NOTE.md`)
- [x] TODO reorganized for product-first beta execution
- [ ] Monitoring setup resumed later (explicitly postponed)
- [ ] DB integration resumed later (explicitly postponed)

## 1) Beta North Star (Must Hold)

- [ ] Excel-like UX + strict data quality guardrails
- [ ] Agent proposes diffs only (no auto-apply)
- [ ] Dataset versioning + rollback always available
- [ ] Every optimize result includes business-impact summary line

Completion Criteria:
- [ ] A non-technical tester can run upload -> edit -> optimize in under 10 minutes
- [ ] No silent data mutation without user approval

## 2) UI Delivery (Top Priority)

## 2.1 Upload / Dataset Creation
- [ ] Build file upload UI (xlsx/csv)
- [ ] Show sheet/column inference summary
- [ ] Show quality badge (`good/warning/error`)
- [ ] Block on critical schema errors

## 2.2 Excel-like Grid Editor
- [ ] Grid with edit/filter/sort/paste support
- [ ] Highlight changed cells
- [ ] Save as dataset versions (`v1`, `v2`, ...)
- [ ] Add rollback to previous version

## 2.3 Agent Sidebar
- [ ] Chat panel attached to current dataset version
- [ ] Show AI-selected domain/solver with one-line reason
- [ ] Render proposed diffs
- [ ] Approve/reject per diff batch

## 2.4 Result Dashboard
- [ ] Status/objective/solve_time cards
- [ ] Bottleneck TOP 3 panel
- [ ] Delay KPI (on-time rate, avg delay)
- [ ] Export result CSV/XLSX
- [ ] One-line value summary (delta vs current plan)

Completion Criteria:
- [ ] Four-screen beta flow is usable end-to-end
- [ ] User can understand result without reading raw JSON

## 3) API/Product Contract

- [ ] `POST /datasets/upload`
- [ ] `POST /datasets/{id}/normalize`
- [ ] `GET /datasets/{id}/grid`
- [ ] `PATCH /datasets/{id}/cells`
- [ ] `POST /datasets/{id}/chat`
- [ ] `POST /datasets/{id}/optimize`
- [ ] `GET /datasets/{id}/versions`
- [ ] `POST /datasets/{id}/versions/{version}/restore`

Completion Criteria:
- [ ] Frontend can complete full workflow using only documented endpoints

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

- [ ] Keep current optimize path stable (`/optimize`)
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

- Product-first rule: do not add deep solver sophistication before workflow usability is proven.
- Billing remains out of scope until internal beta flow is stable.

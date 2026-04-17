# OptiMystic UI Beta Idea Note

## Product Direction (Beta)

Goal:
- Keep Excel-like usability
- Keep strict data control for optimization quality
- Keep agent actions approval-based

Core flow:
1. Upload Excel/CSV
2. Rule-based normalization + validation
3. Web spreadsheet editing
4. Agent chat proposes changes as diffs
5. User approves changes
6. Optimize and review KPI/dashboard

## Non-Negotiable Principles

1. Human-in-the-loop only
- Agent never directly mutates data without explicit approval.
- All AI changes are proposed as patch/diff.

2. Versioned datasets
- Every save creates dataset version (`v1`, `v2`, `v3`, ...).
- Full rollback always available.

3. Explainability first
- Show reason for domain/solver auto-selection.
- Show before/after impact line after optimization.

4. Fail-safe UX
- Original uploaded file is immutable.
- Normalization always supports preview before apply.

## Beta UI (4 Screens)

## 1) Upload / Dataset Creation

Main jobs:
- File upload (xlsx/csv)
- Sheet detection
- Column-type inference
- Data quality summary (`good`, `warning`, `error`)

Must show:
- File name, row/col count, detected sheets
- Rule set to be applied
- Validation blockers (if any)

## 2) Data Grid (Excel-like)

Main jobs:
- Cell edit, paste, filter, sort
- Highlight changed cells
- Save as new version

Must show:
- Current version label
- Changed cells count
- Validation panel (missing required fields, invalid types)

## 3) Agent Panel (Right Sidebar)

Main jobs:
- Natural language requests
- Propose data changes as diff
- Let user approve/reject per change set

Must show:
- "Recommended domain/solver" + one-line reason
- Diff preview before apply
- Apply/Reject buttons

## 4) Result Dashboard

Main jobs:
- Run optimize
- Show core KPI and schedule output
- Export results

Must show:
- Status, objective, solve_time
- Bottleneck TOP 3
- Delay KPI (on-time rate, avg delay)
- One-line value statement (example: "Expected delay reduced by 28% vs current plan")

## Backend Contract (Beta)

Suggested endpoints:
- `POST /datasets/upload`
- `POST /datasets/{id}/normalize`
- `GET /datasets/{id}/grid`
- `PATCH /datasets/{id}/cells`
- `POST /datasets/{id}/chat`
- `POST /datasets/{id}/optimize`
- `GET /datasets/{id}/versions`
- `POST /datasets/{id}/versions/{version}/restore`

## Beta Scope (No Billing)

In scope:
- Dataset pipeline (upload -> normalize -> edit -> optimize)
- Agent diff workflow with approvals
- Runs/history visibility
- Basic monitoring and error visibility

Out of scope:
- Billing
- Fine-grained org/project RBAC
- Full multi-tenant self-service onboarding

## Critical Risks and Mitigations

Risk 1: Excel freedom breaks solver quality
- Mitigation: validation gates + required schema warnings + blocker rules

Risk 2: Agent overreach
- Mitigation: approval-only diff application + immutable original

Risk 3: User confusion on value
- Mitigation: KPI delta + one-line business impact in every run

## Success Criteria for Internal Beta

- Upload success rate >= 90%
- First successful optimization within 10 minutes
- At least 1 complete workflow run/day by internal tester
- Zero silent data mutation incidents
- User can explain why selected domain/solver in one sentence

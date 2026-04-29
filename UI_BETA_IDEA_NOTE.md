# OptiMystic UI Beta Idea Note

## Product Direction (Beta)

Goal:
- Operate directly inside Google Sheets (sidebar-first)
- Keep strict data control for optimization quality
- Keep agent actions approval-based

Core flow:
1. User opens sidebar in Google Sheets
2. Sidebar reads selected range and validates schema
3. Agent chat proposes changes as diffs
4. User approves changes
5. Backend optimize + R analysis
6. Results/KPIs are written back to result tabs

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

## Beta UX (Sheets + Sidebar)

## 1) Sheet Input + Validation

Main jobs:
- Read selected range (or named range)
- Column-type inference
- Data quality summary (`good`, `warning`, `error`)

Must show:
- Active sheet and range
- Rule set to be applied
- Validation blockers (if any)

## 2) Sidebar Conversation Panel

Main jobs:
- Natural language requests
- Propose data changes as diff
- Let user approve/reject per change set

Must show:
- Recommended domain/solver + one-line reason
- Diff preview before apply
- Apply/Reject buttons

## 3) Optimization Output Writer

Main jobs:
- Run optimize against backend
- Write results to dedicated tabs/ranges
- Show concise summary in sidebar

Must show:
- Status, objective, solve_time
- Bottleneck TOP 3
- One-line value statement (example: "Expected delay reduced by 28% vs current plan")

## 4) Deployment Shape

Main jobs:
- Internal Workspace deployment first
- External Marketplace distribution later
- Keep backend API as the single compute layer

Must show:
- Environment setup checklist
- Auth mode decision
- Error-handling and retry policy

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
- Sheet range -> normalize -> optimize -> writeback
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

- Selected-range parse success rate >= 90%
- First successful optimization within 10 minutes
- At least 1 complete workflow run/day by internal tester
- Zero silent data mutation incidents
- User can explain why selected domain/solver in one sentence

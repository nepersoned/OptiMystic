# GCP Deployment Runbook

Two deployment tracks are supported:
- Cloud Run (recommended first for speed/low-ops)
- Compute Engine (recommended when long-running workloads or host-level tuning is required)

Before either track, run a local container smoke test first.

```powershell
cd C:\Projects\OptiMystic
./scripts/setup_deploy_tools.ps1
./scripts/preflight_gcp_deploy.ps1
./scripts/docker_smoke.ps1
```

## A) Cloud Run (Recommended)

### 1) Prerequisites

- Google Cloud SDK (`gcloud`)
- Authenticated account (`gcloud auth login`)
- Active project (`gcloud config set project <PROJECT_ID>`)

### 2) Configure env

```bash
cp deploy/gcp/.env.app.example deploy/gcp/.env.app
```

Set required values in `.env.app`:
- `GOOGLE_API_KEY` (or migrate to Secret Manager later)
- optional `DATABASE_URL`

### 3) Deploy

PowerShell:

```powershell
./deploy/gcp/deploy-cloud-run.ps1 -ProjectId <PROJECT_ID> -Region asia-northeast3 -ServiceName optimystic-api -AllowUnauthenticated $false
```

If your first launch needs a quick public smoke test, temporarily set `-AllowUnauthenticated $true` and lock it down after validation.

### 4) Validate

```bash
curl https://<SERVICE_URL>/health
```

If PostgreSQL is enabled:

```bash
curl https://<SERVICE_URL>/runs
```

## B) Compute Engine

Deploy OptiMystic API and optional agent smoke on Compute Engine.

### 1) Provision VM

Recommended baseline:
- Ubuntu 22.04+
- e2-standard-4 (or higher)

Firewall rules:
- `22/tcp` from admin IP
- `8000/tcp` from trusted CIDR

### 2) Bootstrap

```bash
bash deploy/gcp/bootstrap-vm.sh
newgrp docker
```

### 3) Configure env

```bash
cp deploy/gcp/.env.app.example deploy/gcp/.env.app
```

Set `GOOGLE_API_KEY` in `.env.app`.

If you want persistent optimization run history, also set `DATABASE_URL` to a PostgreSQL connection string.

Example:

```bash
DATABASE_URL=postgresql://USER:PASSWORD@PRIVATE_IP:5432/optimystic
```

Recommended GCP targets:
- Cloud SQL for PostgreSQL for standard managed OLTP
- AlloyDB for higher throughput with PostgreSQL compatibility

### 4) Deploy

```bash
bash deploy/gcp/deploy.sh
```

### 5) Validate

```bash
curl http://127.0.0.1:8000/health
```

If PostgreSQL is enabled, validate run persistence too:

```bash
curl http://127.0.0.1:8000/runs
```

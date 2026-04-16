# GCP Deployment Runbook

Deploy OptiMystic API and optional agent smoke on Compute Engine.

## 1) Provision VM

Recommended baseline:
- Ubuntu 22.04+
- e2-standard-4 (or higher)

Firewall rules:
- `22/tcp` from admin IP
- `8000/tcp` from trusted CIDR

## 2) Bootstrap

```bash
bash deploy/gcp/bootstrap-vm.sh
newgrp docker
```

## 3) Configure env

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

## 4) Deploy

```bash
bash deploy/gcp/deploy.sh
```

## 5) Validate

```bash
curl http://127.0.0.1:8000/health
```

If PostgreSQL is enabled, validate run persistence too:

```bash
curl http://127.0.0.1:8000/runs
```

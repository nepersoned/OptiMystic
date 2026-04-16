# AWS Deployment Runbook

Deploy OptiMystic API and optional agent smoke on EC2.

## 1) Provision

Recommended baseline:
- Instance: `c6i.large` (or equivalent)
- OS: Ubuntu 22.04+

Security group inbound:
- `22/tcp` from admin IP
- `8000/tcp` from trusted CIDR

## 2) Bootstrap

```bash
bash deploy/aws/bootstrap-ec2.sh
newgrp docker
```

## 3) Configure env

```bash
cp deploy/aws/.env.app.example deploy/aws/.env.app
```

Edit `deploy/aws/.env.app` and set:
- `GOOGLE_API_KEY`

## 4) Deploy

```bash
bash deploy/aws/deploy.sh
```

## 5) Validate

```bash
curl http://127.0.0.1:8000/health
```

Optional optimize test:

```bash
curl -X POST http://127.0.0.1:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"domain":"packing","solver":"mip","params":{"Items":[{"Name":"A","Weight":2,"Value":10,"Demand":2}],"Vehicles":[{"Capacity":5}]}}'
```

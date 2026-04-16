# Azure Deployment Guide

Deploy OptiMystic API and optional agent smoke on Azure VM.

## 1) VM

Recommended:
- Ubuntu 22.04+
- General-purpose VM for API use

Inbound ports:
- `22/tcp` from admin IP
- `8000/tcp` from trusted CIDR

## 2) Bootstrap

```bash
bash deploy/azure/bootstrap-vm.sh
newgrp docker
```

## 3) Configure env

```bash
cp deploy/azure/.env.app.example deploy/azure/.env.app
```

Set required value in `.env.app`:
- `GOOGLE_API_KEY`

## 4) Deploy

```bash
bash deploy/azure/deploy.sh
```

## 5) Validate

```bash
curl http://127.0.0.1:8000/health
```

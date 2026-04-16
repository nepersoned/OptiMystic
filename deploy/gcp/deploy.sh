#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f deploy/gcp/.env.app ]]; then
  echo "Missing deploy/gcp/.env.app. Copy from deploy/gcp/.env.app.example"
  exit 1
fi

echo "[1/4] build images"
docker compose -f docker-compose.gcp.yml build api

echo "[2/4] start API"
docker compose --env-file deploy/gcp/.env.app -f docker-compose.gcp.yml up -d api

echo "[3/4] health check"
for i in {1..20}; do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "API health check passed"
    break
  fi
  sleep 3
  if [[ "$i" == "20" ]]; then
    echo "API health check timed out"
    exit 1
  fi
done

echo "[4/4] optional agent smoke"
docker compose --env-file deploy/gcp/.env.app -f docker-compose.gcp.yml --profile smoke run --rm agent-smoke || true

echo "Deployment finished"

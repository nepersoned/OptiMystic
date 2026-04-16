#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash deploy/aws/deploy.sh

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f deploy/aws/.env.app ]]; then
  echo "Missing deploy/aws/.env.app. Copy from deploy/aws/.env.app.example"
  exit 1
fi

echo "[1/4] build images"
docker compose -f docker/docker-compose.aws.yml build api

echo "[2/4] start API"
docker compose --env-file deploy/aws/.env.app -f docker/docker-compose.aws.yml up -d api

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

echo "[4/4] optional agent smoke test"
docker compose --env-file deploy/aws/.env.app -f docker/docker-compose.aws.yml --profile smoke run --rm agent-smoke || true

echo "Deployment finished"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f deploy/azure/.env.app ]]; then
  echo "Missing deploy/azure/.env.app. Copy from deploy/azure/.env.app.example"
  exit 1
fi

echo "[1/4] Build and start API"
docker compose --env-file deploy/azure/.env.app -f docker-compose.azure.yml up -d --build api

echo "[2/4] Check API health"
for i in {1..20}; do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "API is healthy"
    break
  fi
  sleep 3
  if [[ "$i" == "20" ]]; then
    echo "API health timeout"
    exit 1
  fi
done

echo "[3/4] Optional agent smoke"
docker compose --env-file deploy/azure/.env.app -f docker-compose.azure.yml --profile smoke run --rm agent-smoke || true

echo "[4/4] done"

echo "Deploy done"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f deploy/azure/.env.vllm ]]; then
  echo "Missing deploy/azure/.env.vllm. Copy from deploy/azure/.env.vllm.example"
  exit 1
fi

if [[ ! -f deploy/azure/.env.app ]]; then
  echo "Missing deploy/azure/.env.app. Copy from deploy/azure/.env.app.example"
  exit 1
fi

echo "[1/5] Start vLLM"
docker compose --env-file deploy/azure/.env.vllm -f docker-compose.vllm.azure.yml up -d vllm

echo "[2/5] Wait for vLLM models endpoint"
for i in {1..40}; do
  if curl -fsS http://127.0.0.1:8001/v1/models >/dev/null 2>&1; then
    echo "vLLM is ready"
    break
  fi
  sleep 3
  if [[ "$i" == "40" ]]; then
    echo "vLLM readiness timeout"
    exit 1
  fi
done

echo "[3/5] Build and start API"
docker compose --env-file deploy/azure/.env.app -f docker-compose.azure.yml up -d --build api

echo "[4/5] Check API health"
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

echo "[5/5] Optional agent smoke"
docker compose --env-file deploy/azure/.env.app -f docker-compose.azure.yml --profile smoke run --rm agent-smoke || true

echo "Deploy done"

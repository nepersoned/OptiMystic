# AWS Pre-Deployment Runbook

This runbook prepares OptiMystic for EC2 deployment with:
- API service (`docker-compose.aws.yml`)
- Optional vLLM inference service (`docker-compose.vllm.aws.yml`)

## 1. Provision AWS resources

Minimum recommendation:
- App host: `c6i.large` (or equivalent)
- Inference host (if same box, use GPU instance): `g5.xlarge`

Security group inbound:
- `22/tcp` from your admin IP
- `8000/tcp` for OptiMystic API (limit to trusted CIDR)
- `8001/tcp` for vLLM only if accessed externally (prefer private-only)

## 2. Bootstrap EC2

```bash
bash deploy/aws/bootstrap-ec2.sh
newgrp docker
```

## 3. Prepare environment files

```bash
cp deploy/aws/.env.app.example deploy/aws/.env.app
cp deploy/aws/.env.vllm.example deploy/aws/.env.vllm
```

Edit values in:
- `deploy/aws/.env.app`
- `deploy/aws/.env.vllm`

Important:
- Set `OPENAI_BASE_URL` in `.env.app` to your vLLM endpoint.
- If model access requires auth, set `HF_TOKEN` in `.env.vllm`.

## 4. Deploy

```bash
bash deploy/aws/deploy.sh
```

## 5. Validate

```bash
curl http://127.0.0.1:8000/health
```

Optional API check:

```bash
curl -X POST http://127.0.0.1:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"domain":"packing","solver":"mip","params":{"Items":[{"Name":"A","Weight":2,"Value":10,"Demand":2}],"Vehicles":[{"Capacity":5}]}}'
```

## 6. Useful operations

Restart app:
```bash
docker compose --env-file deploy/aws/.env.app -f docker-compose.aws.yml restart api
```

Tail app logs:
```bash
docker compose --env-file deploy/aws/.env.app -f docker-compose.aws.yml logs -f api
```

Tail vLLM logs:
```bash
docker compose --env-file deploy/aws/.env.vllm -f docker-compose.vllm.aws.yml logs -f vllm
```

## 7. Go-live checklist

- API `/health` responds `ok`
- `POST /optimize` succeeds with baseline payload
- Agent smoke run completes without `llm_call_failed`
- Security group tightened to trusted CIDR only
- Disk size and log retention reviewed

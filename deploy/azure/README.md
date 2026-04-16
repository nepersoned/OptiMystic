# Azure GPU Deployment Guide (Credit-Aware)

This guide is tuned for Azure free credits and Gemma 4 4B serving.

## 1. Recommended VM sizes

Priority order:
1. `Standard_NC24ads_A10_v4` (A10 24GB) - best balance for vLLM + Gemma 4 4B
2. `Standard_NC6s_v3` (V100 16GB) - stable fallback
3. `Standard_NV6` (M60 8GB) - budget mode, tighter context/settings

Note:
- GPU quota may start at 0. Request regional vCPU/GPU quota in Azure portal first.

## 2. Create VM

- OS: Ubuntu 22.04 LTS
- Authentication: SSH key
- Public IP: set to Static
- NSG inbound:
  - 22/tcp from your admin IP
  - 8000/tcp from trusted CIDR (OptiMystic API)
  - 8001/tcp from trusted CIDR (vLLM OpenAI-compatible endpoint)

## 3. Bootstrap VM

```bash
bash deploy/azure/bootstrap-vm.sh
newgrp docker
```

## 4. Start vLLM

```bash
cp deploy/azure/.env.vllm.example deploy/azure/.env.vllm
# edit deploy/azure/.env.vllm as needed

docker compose --env-file deploy/azure/.env.vllm -f docker-compose.vllm.azure.yml up -d
```

Health check:

```bash
curl http://127.0.0.1:8001/v1/models
```

## 5. Start OptiMystic API + smoke run

```bash
cp deploy/azure/.env.app.example deploy/azure/.env.app
# make sure OPENAI_BASE_URL points to 127.0.0.1:8001/v1

bash deploy/azure/deploy.sh
```

## 6. Connect agent loop from local machine

PowerShell:

```powershell
$env:OPENAI_BASE_URL="http://<AZURE_PUBLIC_IP>:8001/v1"
$env:OPENAI_API_KEY="EMPTY"

.\.venv\Scripts\python.exe agent_loop.py --llm-provider openai --model gemma4 --max-steps 4
```

## 7. Cost control checklist

1. Configure auto-shutdown in Azure VM settings.
2. Stop VM as `Stopped (deallocated)` when not in use.
3. Keep Public IP static to avoid endpoint changes.
4. Limit NSG inbound to trusted IP/CIDR.
5. For low traffic, run vLLM only when needed.

## 8. Common pitfalls (fixed)

- NVIDIA repo file path should be `/etc/apt/sources.list.d/...` (not `/etc/local/...`).
- For plain Docker Compose, use `gpus: all` rather than Swarm-only `deploy.resources` fields.

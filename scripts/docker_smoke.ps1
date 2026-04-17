$ErrorActionPreference = "Stop"

Write-Host "[1/4] Build API image"
docker compose -f docker/docker-compose.yml build api

Write-Host "[2/4] Start API"
docker compose -f docker/docker-compose.yml up -d api

Write-Host "[3/4] Wait for /health"
$ok = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 5
        if ($resp.status -eq "ok") {
            $ok = $true
            break
        }
    }
    catch {
    }
    Start-Sleep -Seconds 2
}

if (-not $ok) {
    Write-Host "API health check failed. Showing logs..."
    docker compose -f docker/docker-compose.yml logs --tail=200 api
    throw "Docker smoke failed"
}

Write-Host "[4/4] Success"
Write-Host "API is healthy at http://127.0.0.1:8000/health"

$ErrorActionPreference = "Stop"

Write-Host "[1/3] Health check"
Invoke-RestMethod -Uri "http://localhost:8000/api/health" | ConvertTo-Json -Depth 10

Write-Host "[2/3] Scheduling CP"
$cpBody = Get-Content "examples/smoke/scheduling-cp-ok.json" -Raw
Invoke-RestMethod -Uri "http://localhost:8000/api/optimize" -Method Post -ContentType "application/json" -Body $cpBody | ConvertTo-Json -Depth 20

Write-Host "[3/3] Packing MIP (Julia warm-up may take time)"
$mipBody = Get-Content "examples/smoke/packing-mip-ok.json" -Raw
try {
	Invoke-RestMethod -Uri "http://localhost:8000/api/optimize" -Method Post -ContentType "application/json" -Body $mipBody | ConvertTo-Json -Depth 20
}
catch {
	Write-Host "[hint] If this fails on first run, increase server timeout before starting server:" -ForegroundColor Yellow
	Write-Host '$env:OPTIMYSTIC_PYTHON_TIMEOUT_SECONDS = "180"' -ForegroundColor Yellow
	throw
}

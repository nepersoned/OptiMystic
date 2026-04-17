$ErrorActionPreference = "Stop"

function Test-RequiredCommand {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing command: $Name"
    }
}

Write-Host "[1/7] Checking required commands"
Test-RequiredCommand gcloud
Test-RequiredCommand docker

Write-Host "[2/7] gcloud version"
gcloud --version | Select-Object -First 1

Write-Host "[3/7] docker version"
docker --version

docker compose version

Write-Host "[4/7] Active gcloud account"
$account = (gcloud auth list --filter=status:ACTIVE --format="value(account)").Trim()
if (-not $account) {
    throw "No active gcloud account. Run: gcloud auth login"
}
Write-Host "Active account: $account"

Write-Host "[5/7] Active gcloud project"
$project = (gcloud config get-value project 2>$null).Trim()
if (-not $project) {
    throw "No active gcloud project. Run: gcloud config set project <PROJECT_ID>"
}
Write-Host "Active project: $project"

Write-Host "[6/7] Required env files"
if (-not (Test-Path "deploy/gcp/.env.app")) {
    throw "Missing deploy/gcp/.env.app"
}
if (-not (Test-Path "deploy/gcp/.env.app.example")) {
    throw "Missing deploy/gcp/.env.app.example"
}

Write-Host "[7/7] Docker daemon health"
docker info | Out-Null
Write-Host "Preflight passed"

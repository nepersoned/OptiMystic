Param(
    [string]$ProjectId,
    [string]$Region = "asia-northeast3",
    [string]$ServiceName = "optimystic-api",
    [string]$Repository = "optimystic",
    [string]$ImageName = "api",
    [string]$ImageTag = "latest",
    [string]$EnvFile = "deploy/gcp/.env.app",
    [bool]$AllowUnauthenticated = $false
)

$ErrorActionPreference = "Stop"

# Define gcloud and docker paths
$gcloudPath = "C:\Users\kevin\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$dockerPath = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"

function Test-RequiredCommand {
    Param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Invoke-Gcloud {
    Param([string[]]$Args)
    & $gcloudPath @Args
}

function Convert-EnvFileToCsv {
    Param([string]$Path)

    if (-not (Test-Path $Path)) {
        throw "Env file not found: $Path"
    }

    $pairs = @()
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ([string]::IsNullOrWhiteSpace($line)) { return }
        if ($line.StartsWith("#")) { return }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { return }

        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1)

        # Cloud Run env var injection keeps plaintext simple; use Secret Manager for real secrets later.
        $pairs += "$key=$val"
    }

    return ($pairs -join ",")
}

Test-RequiredCommand $gcloudPath

if (-not $ProjectId) {
    $ProjectId = (Invoke-Gcloud config get-value project 2>$null).Trim()
}
if (-not $ProjectId) {
    throw "ProjectId is required. Pass -ProjectId or set gcloud default project."
}

$ImageUri = "$Region-docker.pkg.dev/$ProjectId/$Repository/$ImageName`:$ImageTag"
$EnvVarsCsv = Convert-EnvFileToCsv -Path $EnvFile

Write-Host "[1/6] Setting active project"
Invoke-Gcloud config set project $ProjectId | Out-Null

Write-Host "[2/6] Enabling required APIs"
Invoke-Gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

Write-Host "[3/6] Ensuring Artifact Registry repo"
$repoExists = Invoke-Gcloud artifacts repositories list --location $Region --format="value(name)" | Select-String "/$Repository$"
if (-not $repoExists) {
    Invoke-Gcloud artifacts repositories create $Repository --repository-format=docker --location $Region --description "OptiMystic images"
}

Write-Host "[4/6] Building container image"
Invoke-Gcloud builds submit --tag $ImageUri --file docker/Dockerfile .

Write-Host "[5/6] Deploying to Cloud Run"
$deployArgs = @(
    "run", "deploy", $ServiceName,
    "--image", $ImageUri,
    "--region", $Region,
    "--platform", "managed",
    "--port", "8000",
    "--memory", "2Gi",
    "--cpu", "2",
    "--timeout", "900",
    "--concurrency", "4"
)

if (-not [string]::IsNullOrWhiteSpace($EnvVarsCsv)) {
    $deployArgs += @("--set-env-vars", $EnvVarsCsv)
}

if ($AllowUnauthenticated) {
    $deployArgs += "--allow-unauthenticated"
}
else {
    $deployArgs += "--no-allow-unauthenticated"
}

Invoke-Gcloud @deployArgs

Write-Host "[6/6] Deployment finished"
$serviceUrl = Invoke-Gcloud run services describe $ServiceName --region $Region --format="value(status.url)"
Write-Host "Service URL: $serviceUrl"
Write-Host "Health check: $serviceUrl/health"

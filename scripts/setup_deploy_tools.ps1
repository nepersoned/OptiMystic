$ErrorActionPreference = "Stop"

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-CommandExists "winget")) {
    throw "winget is required but not found. Install App Installer from Microsoft Store."
}

Write-Host "[1/3] Installing Google Cloud SDK"
winget install -e --id Google.CloudSDK --accept-source-agreements --accept-package-agreements

Write-Host "[2/3] Installing Docker Desktop"
winget install -e --id Docker.DockerDesktop --accept-source-agreements --accept-package-agreements

Write-Host "[3/3] Done"
Write-Host "Open a NEW PowerShell terminal and run:"
Write-Host "  gcloud --version"
Write-Host "  docker --version"
Write-Host "If Docker Desktop was just installed, start Docker Desktop once before continuing."

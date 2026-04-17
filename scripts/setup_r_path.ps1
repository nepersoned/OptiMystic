$ErrorActionPreference = "Stop"

$base = "C:\Program Files\R"
if (-not (Test-Path $base)) {
    throw "R base directory not found: $base"
}

$candidates = Get-ChildItem -Path $base -Directory -Filter "R-*" | Sort-Object Name -Descending
if (-not $candidates -or $candidates.Count -eq 0) {
    throw "No R installation folder (R-*) found under $base"
}

$rHome = $candidates[0].FullName
$rBinX64 = Join-Path $rHome "bin\x64"
$rBin = Join-Path $rHome "bin"
$target = if (Test-Path $rBinX64) { $rBinX64 } else { $rBin }

if ($true) {
    if ($env:PATH -notlike "*$target*") {
        $env:PATH = "$target;$env:PATH"
    }
}

if ($true) {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ([string]::IsNullOrWhiteSpace($userPath)) {
        $newPath = $target
    }
    elseif ($userPath -notlike "*$target*") {
        $newPath = "$target;$userPath"
    }
    else {
        $newPath = $userPath
    }

    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
}

Write-Host "R home: $rHome"
Write-Host "R bin added: $target"
Write-Host "Validate: where.exe Rscript"
Param(
    [switch]$InstallPython312
)

$ErrorActionPreference = "Stop"

Write-Host "[1/4] Checking Python launcher interpreters..."
$pyList = py -0p 2>$null
if (-not $pyList) {
    throw "Python launcher 'py' not found. Install Python from python.org first."
}

$has312 = $false
foreach ($line in $pyList) {
    if ($line -match "-V:3\.12") {
        $has312 = $true
        break
    }
}

if (-not $has312) {
    Write-Warning "Python 3.12 is not installed."
    if ($InstallPython312) {
        Write-Host "Trying to install Python 3.12 via winget..."
        winget install -e --id Python.Python.3.12
        $pyList = py -0p 2>$null
        foreach ($line in $pyList) {
            if ($line -match "-V:3\.12") {
                $has312 = $true
                break
            }
        }
    }
}

if (-not $has312) {
    throw "Python 3.12 not available. Install it, then re-run this script."
}

Write-Host "[2/4] Creating .venv312..."
py -3.12 -m venv .venv312

Write-Host "[3/4] Upgrading pip/setuptools/wheel..."
.\.venv312\Scripts\python.exe -m pip install --upgrade pip setuptools wheel

Write-Host "[4/4] Installing base + forecasting packages..."
.\.venv312\Scripts\python.exe -m pip install -r python_solvers\requirements.txt
.\.venv312\Scripts\python.exe -m pip install -r python_solvers\requirements-forecasting.txt

Write-Host "Done. Activate with: .\.venv312\Scripts\Activate.ps1"
# Activate or create the project virtual environment for ProWinder_Dynamics in the user profile
# Usage: In PowerShell run: .\scripts\activate_venv.ps1

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
# Venv location: ~/.venvs/ProWinder_Dynamics
$venvRoot = Join-Path $env:USERPROFILE ".venvs"
$venvPath = Join-Path $venvRoot "ProWinder_Dynamics"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

# 1. Ensure .venvs directory exists
if (-not (Test-Path $venvRoot)) {
    New-Item -ItemType Directory -Path $venvRoot | Out-Null
}

# 2. Create venv if it doesn't exist
if (-not (Test-Path $activateScript)) {
    Write-Host "Creating virtual environment at $venvPath..." -ForegroundColor Cyan
    try {
        & python -m venv $venvPath
    }
    catch {
        Write-Error "Failed to create virtual environment. Ensure python is installed and in your PATH."
        exit 1
    }
    Write-Host "Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "Virtual environment found at $venvPath" -ForegroundColor Cyan
}

# 3. Activate venv
if (Test-Path $activateScript) {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    . $activateScript
} else {
    Write-Error "Activation script not found at $activateScript"
    exit 1
}

# 4. Install dependencies if pyproject.toml exists
$pyprojectFile = Join-Path $projectRoot "pyproject.toml"
if (Test-Path $pyprojectFile) {
    Write-Host "Checking dependencies..." -ForegroundColor Cyan
    
    # We navigate to project root to run pip install
    Push-Location $projectRoot
    try {
        python -m pip install --upgrade pip
        python -m pip install -e .
        Write-Host "Dependencies installed/updated." -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
} else {
    Write-Warning "pyproject.toml not found at $pyprojectFile. Skipping dependency installation."
}

Write-Host "Environment is ready! (ProWinder_Dynamics)" -ForegroundColor Green

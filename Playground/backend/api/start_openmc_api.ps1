# Start OpenMC Backend API Server (PowerShell)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "OpenMC Backend API Startup" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Load environment if .env exists
$envFile = "../../.env"
if (Test-Path $envFile) {
    Write-Host "Loading environment from .env..." -ForegroundColor Yellow
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

# Set defaults
if (-not $env:OPENMC_API_HOST) { $env:OPENMC_API_HOST = "0.0.0.0" }
if (-not $env:OPENMC_API_PORT) { $env:OPENMC_API_PORT = "8001" }
if (-not $env:OPENMC_RUNS_DIR) { $env:OPENMC_RUNS_DIR = "../../../runs" }

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  Host: $env:OPENMC_API_HOST"
Write-Host "  Port: $env:OPENMC_API_PORT"
Write-Host "  Runs Directory: $env:OPENMC_RUNS_DIR"
Write-Host ""

# Check dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow

try {
    python -c "import fastapi" 2>$null
    Write-Host "✅ FastAPI found" -ForegroundColor Green
} catch {
    Write-Host "❌ FastAPI not found. Installing..." -ForegroundColor Red
    pip install fastapi uvicorn motor python-dotenv
}

try {
    python -c "import openmc" 2>$null
    Write-Host "✅ OpenMC found" -ForegroundColor Green
} catch {
    Write-Host "⚠️  OpenMC not installed - will use mock execution" -ForegroundColor Yellow
}

if (-not $env:MONGO_URI) {
    Write-Host "⚠️  MONGO_URI not set - database features will be limited" -ForegroundColor Yellow
} else {
    Write-Host "✅ MongoDB configured" -ForegroundColor Green
}

Write-Host ""
Write-Host "Starting OpenMC Backend API..." -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Start server
python openmc_api.py


# AONP Multi-Agent API Server - PowerShell Startup Script

Write-Host "=========================================="
Write-Host "  AONP Multi-Agent API Server"
Write-Host "=========================================="
Write-Host ""

# Load .env file if it exists
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $name = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# Check environment variables
if (-not $env:MONGO_URI) {
    Write-Host "❌ ERROR: MONGO_URI not set" -ForegroundColor Red
    Write-Host "Please set MONGO_URI environment variable or create .env file"
    exit 1
}

Write-Host "✓ MONGO_URI set" -ForegroundColor Green

# Check if FIREWORKS key is set (optional)
if (-not $env:FIREWORKS) {
    Write-Host "⚠️  WARNING: FIREWORKS key not set" -ForegroundColor Yellow
    Write-Host "   LLM routing will be disabled (using fast keyword routing)"
} else {
    Write-Host "✓ FIREWORKS key set" -ForegroundColor Green
}

# Set defaults
if (-not $env:API_HOST) { $env:API_HOST = "0.0.0.0" }
if (-not $env:API_PORT) { $env:API_PORT = "8000" }
if (-not $env:CORS_ORIGINS) { $env:CORS_ORIGINS = "http://localhost:3000,http://localhost:5173" }

Write-Host ""
Write-Host "Configuration:"
Write-Host "  Host: $env:API_HOST"
Write-Host "  Port: $env:API_PORT"
Write-Host "  CORS: $env:CORS_ORIGINS"
Write-Host ""

# Check if in WSL
$inWSL = Test-Path /proc/version -ErrorAction SilentlyContinue
if ($inWSL) {
    Write-Host "Detected WSL environment"
    wsl bash -c "cd /home/ratth/projects/Hackathon_fusion/Hackathon_fusion/Playground/backend && ./start_api.sh"
    exit
}

# Navigate to API directory
Set-Location -Path "$PSScriptRoot\api"

Write-Host "Starting server..."
Write-Host "=========================================="
Write-Host ""
Write-Host "  📡 Server: http://$($env:API_HOST):$($env:API_PORT)"
Write-Host "  📚 API Docs: http://$($env:API_HOST):$($env:API_PORT)/docs"
Write-Host "  📖 ReDoc: http://$($env:API_HOST):$($env:API_PORT)/redoc"
Write-Host ""
Write-Host "=========================================="
Write-Host ""

# Start server
python -m uvicorn main_v2:app --host $env:API_HOST --port $env:API_PORT --reload


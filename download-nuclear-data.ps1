# PowerShell helper script to download nuclear data for OpenMC
# This can be run inside the Docker container or on the host

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "OpenMC Nuclear Data Downloader" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Determine if running in Docker or on host
$isDocker = Test-Path "/.dockerenv" -ErrorAction SilentlyContinue
if ($isDocker) {
    $DATA_DIR = "/app/nuclear_data"
    Write-Host "Detected: Running inside Docker container" -ForegroundColor Yellow
} else {
    $DATA_DIR = "./nuclear_data"
    Write-Host "Detected: Running on host machine" -ForegroundColor Yellow
}

Write-Host "Download directory: $DATA_DIR"
Write-Host ""

# Create directory if it doesn't exist
New-Item -ItemType Directory -Force -Path $DATA_DIR | Out-Null
Set-Location $DATA_DIR

Write-Host "Downloading ENDF-B/VII.1 nuclear data library..."
Write-Host "This may take several minutes (~2-3 GB download)..."
Write-Host ""

# Check if Python and OpenMC are available
try {
    python -c "import openmc" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "OpenMC not available"
    }
} catch {
    Write-Host "❌ ERROR: OpenMC is not installed or not available in Python" -ForegroundColor Red
    Write-Host ""
    Write-Host "If running in Docker, make sure the backend container is running:" -ForegroundColor Yellow
    Write-Host "  docker compose up -d backend"
    Write-Host "  docker compose exec backend bash"
    Write-Host "  Then run this script again"
    Write-Host ""
    exit 1
}

# Download the data
Write-Host "Starting download..."
python -c "import openmc; openmc.data.download_endfb71()"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "✓ Download complete!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Nuclear data location: $DATA_DIR/endfb-vii.1-hdf5/cross_sections.xml"
    Write-Host ""
    
    if ($isDocker) {
        Write-Host "The data is now available in the container."
        Write-Host "Restart the backend service to use it:"
        Write-Host "  docker compose restart backend" -ForegroundColor Yellow
    } else {
        Write-Host "The data is now available on the host."
        Write-Host "If using Docker, restart the backend service:"
        Write-Host "  docker compose restart backend" -ForegroundColor Yellow
    }
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ ERROR: Download failed" -ForegroundColor Red
    Write-Host "Please check your internet connection and try again."
    exit 1
}

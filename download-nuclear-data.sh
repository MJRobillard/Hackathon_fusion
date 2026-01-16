#!/bin/bash
# Helper script to download nuclear data for OpenMC
# This can be run inside the Docker container or on the host

set -e

echo "=========================================="
echo "OpenMC Nuclear Data Downloader"
echo "=========================================="
echo ""

# Determine if running in Docker or on host
if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
    # Running inside Docker container
    DATA_DIR="/app/nuclear_data"
    echo "Detected: Running inside Docker container"
else
    # Running on host
    DATA_DIR="./nuclear_data"
    echo "Detected: Running on host machine"
fi

echo "Download directory: $DATA_DIR"
echo ""

# Create directory if it doesn't exist
mkdir -p "$DATA_DIR"
cd "$DATA_DIR"

echo "Downloading ENDF-B/VII.1 nuclear data library..."
echo "This may take several minutes (~2-3 GB download)..."
echo ""

# Check if Python and OpenMC are available
if ! python -c "import openmc" 2>/dev/null; then
    echo "❌ ERROR: OpenMC is not installed or not available in Python"
    echo ""
    echo "If running in Docker, make sure the backend container is running:"
    echo "  docker compose up -d backend"
    echo "  docker compose exec backend bash"
    echo "  Then run this script again"
    echo ""
    exit 1
fi

# Download the data
echo "Starting download..."
python -c "import openmc; openmc.data.download_endfb71()"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ Download complete!"
    echo "=========================================="
    echo ""
    echo "Nuclear data location: $DATA_DIR/endfb-vii.1-hdf5/cross_sections.xml"
    echo ""
    
    if [ -f /.dockerenv ] || [ -n "$DOCKER_CONTAINER" ]; then
        echo "The data is now available in the container."
        echo "Restart the backend service to use it:"
        echo "  docker compose restart backend"
    else
        echo "The data is now available on the host."
        echo "If using Docker, restart the backend service:"
        echo "  docker compose restart backend"
    fi
    echo ""
else
    echo ""
    echo "❌ ERROR: Download failed"
    echo "Please check your internet connection and try again."
    exit 1
fi

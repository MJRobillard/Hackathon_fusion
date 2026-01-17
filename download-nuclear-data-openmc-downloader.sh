#!/bin/bash
# Helper script to download nuclear data using openmc_data_downloader
# This is easier to use and works better in Docker containers

set -e

echo "=========================================="
echo "OpenMC Nuclear Data Downloader"
echo "Using: openmc_data_downloader"
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

echo "Checking if openmc_data_downloader is available..."
# Try CLI first, then Python module
USE_CLI=false
USE_PYTHON=false

if command -v openmc_data_downloader &> /dev/null; then
    USE_CLI=true
    echo "✓ openmc_data_downloader CLI found"
elif python -c "import openmc_data_downloader" 2>/dev/null; then
    USE_PYTHON=true
    echo "✓ openmc_data_downloader Python module found"
else
    echo "⚠️  WARNING: openmc_data_downloader not found, falling back to openmc.data.download_endfb71()"
    echo "   Install it with: pip install openmc_data_downloader"
    USE_PYTHON=false
fi

echo ""

echo "Downloading ENDF-B/VII.1 nuclear data library..."
echo "This may take several minutes (~2-3 GB download)..."
echo ""

# Download the data
echo "Starting download..."
if [ "$USE_CLI" = true ]; then
    # Try CLI with standard options
    openmc_data_downloader install --dest "$DATA_DIR" 2>/dev/null || \
    openmc_data_downloader -d "$DATA_DIR" 2>/dev/null || \
    openmc_data_downloader "$DATA_DIR" 2>/dev/null || {
        echo "⚠️  CLI format not recognized, trying Python module..."
        python -m openmc_data_downloader install --dest "$DATA_DIR"
    }
elif [ "$USE_PYTHON" = true ]; then
    # Use Python module
    python -m openmc_data_downloader install --dest "$DATA_DIR" || \
    python -c "from openmc_data_downloader import download_endfb71; download_endfb71('$DATA_DIR')"
else
    # Fallback to built-in openmc method
    python -c "import openmc; openmc.data.download_endfb71()"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ Download complete!"
    echo "=========================================="
    echo ""
    echo "Nuclear data downloaded to: $DATA_DIR"
    echo ""
    echo "The cross_sections.xml file should be at:"
    echo "  $DATA_DIR/endfb-vii.1-hdf5/cross_sections.xml"
    echo ""
    echo "Restart your container/server to pick up the new data:"
    echo "  docker compose restart backend"
    echo ""
else
    echo ""
    echo "❌ Download failed. Please check the error messages above."
    echo ""
    exit 1
fi

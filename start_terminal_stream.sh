#!/bin/bash
# Start the terminal streaming server on port 8001

cd "$(dirname "$0")"

# Set nuclear data path (relative to project root)
SCRIPT_DIR="$(pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
NUCLEAR_DATA_PATH="$PROJECT_ROOT/nuclear_data/endfb-vii.1-hdf5/cross_sections.xml"

if [ -f "$NUCLEAR_DATA_PATH" ]; then
    export OPENMC_CROSS_SECTIONS="$NUCLEAR_DATA_PATH"
    echo "✓ OPENMC_CROSS_SECTIONS set to: $NUCLEAR_DATA_PATH"
elif [ -z "$OPENMC_CROSS_SECTIONS" ]; then
    echo "⚠️  WARNING: Nuclear data not found at expected path: $NUCLEAR_DATA_PATH"
    echo "   Please set OPENMC_CROSS_SECTIONS environment variable manually"
fi

echo "Starting AONP Terminal Streaming Server..."
echo ""
echo "This captures ALL backend output from port 8000"
echo "and streams it to the frontend on port 8001"
echo ""

uvicorn aonp.api.main:app --reload --port 8001


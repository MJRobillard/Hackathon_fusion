#!/bin/bash
# Start OpenMC Backend API Server

set -e

echo "========================================="
echo "OpenMC Backend API Startup"
echo "========================================="

# Load environment if .env exists
if [ -f "../../.env" ]; then
    echo "Loading environment from .env..."
    export $(cat ../../.env | grep -v '^#' | xargs)
fi

# Set defaults
export OPENMC_API_HOST=${OPENMC_API_HOST:-0.0.0.0}
export OPENMC_API_PORT=${OPENMC_API_PORT:-8001}
export OPENMC_RUNS_DIR=${OPENMC_RUNS_DIR:-../../../runs}

echo "Configuration:"
echo "  Host: $OPENMC_API_HOST"
echo "  Port: $OPENMC_API_PORT"
echo "  Runs Directory: $OPENMC_RUNS_DIR"
echo ""

# Check dependencies
echo "Checking dependencies..."

if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ FastAPI not found. Installing..."
    pip install fastapi uvicorn motor python-dotenv
fi

if ! python -c "import openmc" 2>/dev/null; then
    echo "⚠️  OpenMC not installed - will use mock execution"
else
    echo "✅ OpenMC found"
fi

if [ -z "$MONGO_URI" ]; then
    echo "⚠️  MONGO_URI not set - database features will be limited"
else
    echo "✅ MongoDB configured"
fi

echo ""
echo "Starting OpenMC Backend API..."
echo "========================================="

# Start server
python openmc_api.py


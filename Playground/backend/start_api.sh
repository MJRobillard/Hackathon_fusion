#!/bin/bash
#
# AONP Multi-Agent API Server - Startup Script
#

echo "=========================================="
echo "  AONP Multi-Agent API Server"
echo "=========================================="
echo ""

# Check environment variables
if [ -z "$MONGO_URI" ]; then
    echo "❌ ERROR: MONGO_URI not set"
    echo "Please set MONGO_URI environment variable or create .env file"
    exit 1
fi

echo "✓ MONGO_URI set"

# Check if FIREWORKS key is set (optional)
if [ -z "$FIREWORKS" ]; then
    echo "⚠️  WARNING: FIREWORKS key not set"
    echo "   LLM routing will be disabled (using fast keyword routing)"
else
    echo "✓ FIREWORKS key set"
fi

# Set defaults
export API_HOST="${API_HOST:-0.0.0.0}"
export API_PORT="${API_PORT:-8000}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000,http://localhost:5173}"

echo ""
echo "Configuration:"
echo "  Host: $API_HOST"
echo "  Port: $API_PORT"
echo "  CORS: $CORS_ORIGINS"
echo ""

# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo "❌ ERROR: uvicorn not found"
    echo "Install with: pip install uvicorn"
    exit 1
fi

# Navigate to API directory
cd "$(dirname "$0")/api" || exit 1

echo "Starting server..."
echo "=========================================="
echo ""
echo "  📡 Server: http://$API_HOST:$API_PORT"
echo "  📚 API Docs: http://$API_HOST:$API_PORT/docs"
echo "  📖 ReDoc: http://$API_HOST:$API_PORT/redoc"
echo ""
echo "=========================================="
echo ""

# Start server
uvicorn main_v2:app --host "$API_HOST" --port "$API_PORT" --reload


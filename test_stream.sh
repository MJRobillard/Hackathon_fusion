#!/bin/bash
# Test script for OpenMC terminal streaming

echo "==================================="
echo "OpenMC Terminal Streaming Test"
echo "==================================="
echo ""

# Check if run_id is provided
if [ -z "$1" ]; then
    echo "Usage: ./test_stream.sh <run_id>"
    echo ""
    echo "Example: ./test_stream.sh run_abc123def456"
    echo ""
    echo "Available runs:"
    ls -1 runs/ 2>/dev/null | grep "^run_" | head -5
    exit 1
fi

RUN_ID="$1"
API_URL="${API_URL:-http://localhost:8000}"
STREAM_ENDPOINT="$API_URL/runs/$RUN_ID/stream"

echo "Testing endpoint: $STREAM_ENDPOINT"
echo ""
echo "Starting stream..."
echo "-----------------------------------"

# Use curl with -N to disable buffering for streaming
curl -N "$STREAM_ENDPOINT" 2>&1

echo ""
echo "-----------------------------------"
echo "Stream ended"


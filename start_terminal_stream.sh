#!/bin/bash
# Start the terminal streaming server on port 8001

cd "$(dirname "$0")"

echo "Starting AONP Terminal Streaming Server..."
echo ""
echo "This captures ALL backend output from port 8000"
echo "and streams it to the frontend on port 8001"
echo ""

uvicorn aonp.api.main:app --reload --port 8001


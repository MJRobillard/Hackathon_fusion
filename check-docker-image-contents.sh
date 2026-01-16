#!/bin/bash
# Script to check if nuclear_data is in the Docker image

echo "=== Checking if nuclear_data exists in Docker image ==="
echo ""

# Check if container is running
if docker compose ps | grep -q "hackathon_fusion-backend"; then
    echo "Checking running container..."
    docker compose exec backend ls -la /app/nuclear_data 2>&1 | head -5
    echo ""
    docker compose exec backend du -sh /app/nuclear_data 2>&1
else
    echo "Container not running. Creating temporary container to check..."
    docker run --rm hackathon_fusion-backend:latest ls -la /app/nuclear_data 2>&1 | head -5
    echo ""
    docker run --rm hackathon_fusion-backend:latest du -sh /app/nuclear_data 2>&1
fi

echo ""
echo "=== Expected: nuclear_data should NOT exist in image ==="
echo "If it shows 'No such file or directory', .dockerignore is working!"
echo "If it shows directory contents, nuclear_data is being included (bad!)"

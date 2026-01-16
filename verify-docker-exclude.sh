#!/bin/bash
# Verify what's being excluded from Docker build

echo "=== Checking .dockerignore ==="
cat .dockerignore | grep -i nuclear

echo ""
echo "=== Checking if nuclear_data would be excluded ==="
if docker build --dry-run . 2>&1 | grep -i "nuclear_data" || \
   docker buildx build --dry-run . 2>&1 | grep -i "nuclear_data"; then
    echo "⚠️  nuclear_data might still be included"
else
    echo "✓ .dockerignore appears to be working (but verify with actual build)"
fi

echo ""
echo "=== Current image size ==="
docker images | grep hackathon_fusion-backend

echo ""
echo "=== To rebuild without cache (excludes nuclear_data): ==="
echo "docker compose build --no-cache backend"

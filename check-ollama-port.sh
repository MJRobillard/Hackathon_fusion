#!/bin/bash
# Check Ollama port configuration and connectivity

echo "=========================================="
echo "Ollama Port Check"
echo "=========================================="
echo ""

echo "1. Check Docker container port mapping:"
docker ps | grep ollama
echo ""

echo "2. Check if port 11435 (host) is listening:"
netstat -tuln | grep 11435 || ss -tuln | grep 11435 || echo "Port 11435 not found listening"
echo ""

echo "3. Test Ollama API from host (port 11435):"
curl -s http://localhost:11435/api/tags | head -20 || echo "Connection failed to localhost:11435"
echo ""

echo "4. Test Ollama API from inside container (port 11434):"
docker exec hackathon_fusion-ollama-1 curl -s http://localhost:11434/api/tags | head -20 || echo "Connection failed inside container"
echo ""

echo "5. Check backend can reach Ollama (from backend container):"
docker exec hackathon_fusion-backend-1 curl -s http://ollama:11434/api/tags | head -20 || echo "Backend cannot reach Ollama at ollama:11434"
echo ""

echo "6. Check Ollama container logs for port binding:"
docker logs hackathon_fusion-ollama-1 2>&1 | grep -i "listen\|port\|11434" | tail -5
echo ""

echo "=========================================="
echo "Port Configuration Summary:"
echo "=========================================="
echo "Host (your machine):     localhost:11435"
echo "Docker network (backend): ollama:11434"
echo "Container internal:      localhost:11434"
echo ""

#!/bin/bash
# Setup script for local DeepSeek via Ollama
# Downloads and installs Ollama, then pulls the smallest DeepSeek model

set -e

echo "========================================="
echo "Local DeepSeek Setup via Ollama"
echo "========================================="
echo ""

# Check if Ollama is already installed
if command -v ollama &> /dev/null; then
    echo "✓ Ollama is already installed"
    ollama --version
else
    echo "Installing Ollama..."
    # Install Ollama using official installer
    curl -fsSL https://ollama.com/install.sh | sh
    
    if ! command -v ollama &> /dev/null; then
        echo "❌ Failed to install Ollama. Please install manually from https://ollama.com"
        exit 1
    fi
    
    echo "✓ Ollama installed successfully"
fi

echo ""
echo "Starting Ollama service..."
# Start Ollama service (runs in background if not already running)
ollama serve &
OLLAMA_PID=$!
sleep 3

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Warning: Ollama service may not be running. Starting..."
    # Try to start it again
    sleep 2
fi

echo ""
echo "Downloading DeepSeek-R1:1.5B model (smallest available, ~1GB)..."
echo "This may take a few minutes depending on your connection."
echo ""

# Pull the smallest DeepSeek model
ollama pull deepseek-r1:1.5b

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Model downloaded: deepseek-r1:1.5b"
echo ""
echo "To use local DeepSeek in your application:"
echo "  1. Set in your .env file:"
echo "     RUN_LOCAL=true"
echo ""
echo "  2. Or export before running:"
echo "     export RUN_LOCAL=true"
echo ""
echo "  3. Ensure Ollama is running:"
echo "     ollama serve"
echo ""
echo "  4. Test the model:"
echo "     ollama run deepseek-r1:1.5b 'Hello, world!'"
echo ""
echo "Optional environment variables:"
echo "  LOCAL_DEEPSEEK_MODEL=deepseek-r1:1.5b  # Model name"
echo "  LOCAL_DEEPSEEK_URL=http://localhost:11434  # Ollama URL"
echo ""

# Test the model
echo "Testing model availability..."
if ollama list | grep -q "deepseek-r1:1.5b"; then
    echo "✓ Model is available and ready to use"
else
    echo "⚠️  Warning: Model not found in list. Try: ollama pull deepseek-r1:1.5b"
fi

echo ""
echo "Done!"

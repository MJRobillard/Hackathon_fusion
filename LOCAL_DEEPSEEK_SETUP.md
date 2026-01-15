# Local DeepSeek Setup Guide

This guide walks you through setting up a local DeepSeek model as a replacement for Fireworks/NVIDIA when `RUN_LOCAL=true` is set in your environment.

## Overview

When `RUN_LOCAL=true` is set, the application will use a local DeepSeek model via Ollama instead of the Fireworks API. This is useful for:
- Offline development
- Avoiding API costs
- Data privacy (no external API calls)
- Custom model fine-tuning

The smallest available DeepSeek model (`deepseek-r1:1.5b`) is used by default (~1GB download).

## Quick Start

### 1. Install Ollama

**Linux/WSL/macOS:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download and install from: https://ollama.com/download/windows

**Verify installation:**
```bash
ollama --version
```

### 2. Run Setup Script

**Linux/WSL/macOS:**
```bash
chmod +x scripts/setup_local_deepseek.sh
./scripts/setup_local_deepseek.sh
```

**Windows:**
```cmd
scripts\setup_local_deepseek.bat
```

This will:
- Verify Ollama is installed
- Download the `deepseek-r1:1.5b` model (~1GB)
- Test that everything works

### 3. Manual Setup (Alternative)

If you prefer to set up manually:

```bash
# 1. Start Ollama service (Linux/WSL/macOS)
ollama serve

# 2. Download the model
ollama pull deepseek-r1:1.5b

# 3. Test it works
ollama run deepseek-r1:1.5b "Hello, world!"
```

### 4. Configure Your Application

Add to your `.env` file:
```bash
RUN_LOCAL=true
```

Or set it as an environment variable:
```bash
export RUN_LOCAL=true  # Linux/WSL/macOS
set RUN_LOCAL=true     # Windows CMD
$env:RUN_LOCAL="true"  # Windows PowerShell
```

### 5. Verify It Works

The application will automatically use local DeepSeek when `RUN_LOCAL=true` is set. You don't need to change any code - it's handled transparently by `aonp/llm/fireworks_client.py`.

## Available Models

The default model is `deepseek-r1:1.5b` (1.5B parameters, ~1GB). Other DeepSeek models available via Ollama:

- `deepseek-r1:1.5b` - Smallest, fastest (default)
- `deepseek-r1:7b` - Better quality, ~4GB
- `deepseek-r1:32b` - Best quality, ~18GB
- `deepseek-r1:70b` - Maximum quality, ~40GB

To use a different model:
```bash
# Download the model
ollama pull deepseek-r1:7b

# Set in your .env
LOCAL_DEEPSEEK_MODEL=deepseek-r1:7b
```

## Configuration

Environment variables for local DeepSeek:

| Variable | Default | Description |
|----------|---------|-------------|
| `RUN_LOCAL` | `false` | Enable local mode (set to `true`, `1`, `yes`, or `on`) |
| `LOCAL_DEEPSEEK_MODEL` | `deepseek-r1:1.5b` | Ollama model name to use |
| `LOCAL_DEEPSEEK_URL` | `http://localhost:11434` | Ollama API base URL |

## Troubleshooting

### Ollama not running

**Linux/WSL/macOS:**
```bash
# Start Ollama service
ollama serve

# Or run in background
ollama serve &
```

**Windows:**
Ollama runs as a service automatically. If it's not working, restart it from the Start menu.

### Model not found

```bash
# List available models
ollama list

# Pull the model again
ollama pull deepseek-r1:1.5b
```

### Connection refused

Ensure Ollama is running and accessible:
```bash
# Test connection
curl http://localhost:11434/api/tags

# Or check if Ollama is listening
# Linux/WSL/macOS
netstat -an | grep 11434

# Windows
netstat -an | findstr 11434
```

### Fallback behavior

If local DeepSeek fails and you have a `FIREWORKS` key set, the system will automatically fall back to Fireworks API. If no `FIREWORKS` key is available, you'll get an error.

## Architecture

The local DeepSeek integration works as follows:

1. `aonp/llm/fireworks_client.py` checks `RUN_LOCAL` environment variable
2. If `RUN_LOCAL=true`, it imports `local_deepseek_client.py`
3. `local_deepseek_client.py` sends HTTP requests to Ollama's OpenAI-compatible API
4. Responses are converted to OpenAI-compatible format for consistency
5. The same interface is used throughout the codebase - no other changes needed

## Performance Notes

- **Model size**: The 1.5B model is tiny but still reasonably capable
- **Memory**: Requires ~2-4GB RAM
- **Speed**: First request may be slow (~10-30s) as model loads into memory
- **GPU**: Ollama will use GPU if available (CUDA/Metal), significantly faster
- **CPU**: Works on CPU, but slower (5-30s per request depending on hardware)

For better performance:
- Use a GPU if available
- Use larger models if you have RAM (7b or 32b)
- Consider quantization for faster CPU inference

## License

DeepSeek-R1 models are licensed under Apache 2.0. Ollama is licensed under MIT.

## Resources

- [Ollama Documentation](https://github.com/ollama/ollama)
- [DeepSeek Models on Ollama](https://ollama.com/search?q=deepseek)
- [DeepSeek Official Site](https://www.deepseek.com/)

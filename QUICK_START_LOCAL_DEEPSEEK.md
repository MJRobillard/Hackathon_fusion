# Quick Start: Local DeepSeek

**TL;DR:** Set up local DeepSeek in 3 steps:

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Download the tiny model (~1GB)
ollama pull deepseek-r1:1.5b

# 3. Set environment variable
export RUN_LOCAL=true

# Done! Your app now uses local DeepSeek instead of Fireworks.
```

## What This Does

When `RUN_LOCAL=true` is set, the application automatically uses a local DeepSeek model running via Ollama instead of the Fireworks API. This is completely transparent - no code changes needed!

## Files Created

- `aonp/llm/local_deepseek_client.py` - Client for local Ollama API
- `scripts/setup_local_deepseek.sh` - Automated setup script (Linux/WSL/macOS)
- `scripts/setup_local_deepseek.bat` - Automated setup script (Windows)
- `scripts/test_local_deepseek.py` - Test script to verify setup
- `LOCAL_DEEPSEEK_SETUP.md` - Full detailed documentation

## Testing

```bash
# Test that everything works
RUN_LOCAL=true python scripts/test_local_deepseek.py
```

## Configuration

Add to your `.env` file:
```bash
RUN_LOCAL=true
```

Or use environment variable:
```bash
export RUN_LOCAL=true  # Linux/WSL/macOS
set RUN_LOCAL=true     # Windows CMD
$env:RUN_LOCAL="true"  # Windows PowerShell
```

## Requirements

- **Ollama** installed (see `LOCAL_DEEPSEEK_SETUP.md`)
- **Model downloaded**: `ollama pull deepseek-r1:1.5b`
- **Ollama running**: `ollama serve` (runs automatically on Windows)

## Model Size

- **deepseek-r1:1.5b**: ~1GB download, ~2-4GB RAM usage
- **Speed**: First request ~10-30s, subsequent ~2-10s (CPU dependent)
- **Quality**: Good enough for development/testing, not production-grade

## Fallback Behavior

If local DeepSeek fails:
- ✅ Falls back to Fireworks API (if `FIREWORKS` key is set)
- ❌ Raises error if no Fireworks key available

See `LOCAL_DEEPSEEK_SETUP.md` for full documentation and troubleshooting.

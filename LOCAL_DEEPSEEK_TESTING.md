# Local DeepSeek Testing Guide

This guide explains how to test that local DeepSeek integration works correctly when `RUN_LOCAL=true`.

## Quick Start

### Prerequisites

1. **Install Ollama** (if not already installed):
   ```bash
   # Linux/WSL/macOS
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Windows: Download from https://ollama.com/download/windows
   ```

2. **Download the 1GB model**:
   ```bash
   ollama pull deepseek-r1:1.5b
   ```

3. **Start Ollama** (if not already running):
   ```bash
   # Linux/WSL/macOS
   ollama serve
   
   # Windows: Ollama runs as a service automatically
   ```

4. **Install langchain-openai** (required for multi-agent system):
   ```bash
   pip install langchain-openai
   ```

### Running Tests

#### Option 1: Integration Script (Recommended for first-time testing)

```bash
# Set RUN_LOCAL=true and run the integration test
RUN_LOCAL=true python scripts/test_local_deepseek_integration.py
```

This will:
- ✅ Check prerequisites (Ollama running, model available)
- ✅ Test LLM creation with RUN_LOCAL=true
- ✅ Verify model name is accessible (not null)
- ✅ Test RouterAgent model name exposure
- ✅ Test actual routing functionality

#### Option 2: Pytest (Recommended for CI/CD)

```bash
# Run all local DeepSeek tests
RUN_LOCAL=true pytest tests/test_local_deepseek_multi_agent.py -v

# Run specific test
RUN_LOCAL=true pytest tests/test_local_deepseek_multi_agent.py::TestLLMCreation::test_llm_model_name_is_set -v
```

#### Option 3: Basic Ollama Test (Quick sanity check)

```bash
# Test Ollama connection and basic functionality
RUN_LOCAL=true python scripts/test_local_deepseek.py
```

## What Gets Tested

### 1. LLM Creation (`TestLLMCreation`)

Tests that when `RUN_LOCAL=true`:
- ✅ `_should_use_local()` returns `True`
- ✅ LLM is created as `ChatOpenAI` (not `ChatFireworks`)
- ✅ Base URL points to Ollama (`http://localhost:11434/v1`)
- ✅ Model name is accessible: `getattr(llm, "model", None)` returns the model name (not `None`)
- ✅ Temperature is accessible: `getattr(llm, "temperature", None)` returns `0.7` (not `None`)
- ✅ Falls back to Fireworks when `RUN_LOCAL` is not set

### 2. RouterAgent Model Name Exposure (`TestRouterAgent`)

Tests that RouterAgent:
- ✅ Exposes model name correctly in planning events
- ✅ `llm_input.model` in reasoning is not `null`
- ✅ `llm_input.model` matches the actual model name (e.g., `"deepseek-r1:1.5b"`)
- ✅ `llm_input.temperature` is also present
- ✅ Actually works for routing queries with local DeepSeek

### 3. StudiesAgent (`TestStudiesAgent`)

Tests that StudiesAgent:
- ✅ Has access to LLM with correct model name
- ✅ Model name is accessible via `getattr(agent.llm, "model", None)`

### 4. Configuration (`TestIntegration`)

Tests:
- ✅ Custom model name via `LOCAL_DEEPSEEK_MODEL` environment variable
- ✅ Custom Ollama URL via `LOCAL_DEEPSEEK_URL` environment variable

## Expected Output

### Successful Test Run

```
================================================================================
Local DeepSeek Multi-Agent Integration Test
================================================================================

✓ RUN_LOCAL is set to true
✓ Ollama is running and model is available

--------------------------------------------------------------------------------
Test 1: LLM Creation
--------------------------------------------------------------------------------
✓ LLM is ChatOpenAI (local DeepSeek)
✓ Model name is accessible: deepseek-r1:1.5b
✓ Temperature is accessible: 0.7
✓ Base URL points to Ollama: http://localhost:11434/v1
✓ Test 1 passed

--------------------------------------------------------------------------------
Test 2: RouterAgent Model Name Exposure
--------------------------------------------------------------------------------
Routing query: Run parameter sweep for enrichment 3% to 5%
Routing result: agent=sweep, intent=sweep
✓ Model name in reasoning: deepseek-r1:1.5b
✓ Temperature in reasoning: 0.7
✓ Test 2 passed

--------------------------------------------------------------------------------
Test 3: RouterAgent Functionality
--------------------------------------------------------------------------------

Testing query: Run parameter sweep for enrichment 3% to 5%
  → Agent: sweep, Intent: sweep, Confidence: 0.90
  ✓ Routing successful

Testing query: Show me recent runs
  → Agent: query, Intent: query, Confidence: 0.90
  ✓ Routing successful

Testing query: Simulate a PWR pin cell
  → Agent: studies, Intent: single_study, Confidence: 0.90
  ✓ Routing successful

✓ Test 3 passed

================================================================================
Test Summary
================================================================================
✓ PASSED: LLM Creation
✓ PASSED: RouterAgent Model Name
✓ PASSED: RouterAgent Functionality

✓ All tests passed!

Local DeepSeek integration is working correctly.
The model name should now show up correctly in agent reasoning.
================================================================================
```

### What This Fixes

Before the fix:
```json
{
  "llm_input": {
    "model": null,  // ❌ Bug: model was null
    "temperature": 0.7
  }
}
```

After the fix:
```json
{
  "llm_input": {
    "model": "deepseek-r1:1.5b",  // ✅ Fixed: model name is now shown
    "temperature": 0.7
  }
}
```

## Troubleshooting

### Error: "langchain-openai not available"

**Solution**: Install langchain-openai:
```bash
pip install langchain-openai
```

Or add to requirements.txt and install:
```bash
pip install -r requirements.txt
```

### Error: "Ollama is not running or model not available"

**Solution**:
1. Start Ollama: `ollama serve`
2. Download model: `ollama pull deepseek-r1:1.5b`
3. Verify: `ollama list` should show `deepseek-r1:1.5b`

### Error: "RUN_LOCAL is not detected as true"

**Solution**:
1. Set environment variable: `export RUN_LOCAL=true` (Linux/WSL/macOS)
2. Or add to `.env` file: `RUN_LOCAL=true`
3. Restart your Python session/application

### Error: "Model name is None"

**Possible causes**:
1. Module cache - Python might be using cached module. Restart Python.
2. Import order - Make sure `RUN_LOCAL` is set before importing `multi_agent_system`
3. Check that `llm.model = model_name` is being set in `_create_llm()`

**Solution**: The tests clear module cache automatically, but if running manually:
```python
# Clear module cache
import sys
if "multi_agent_system" in sys.modules:
    del sys.modules["multi_agent_system"]

# Set RUN_LOCAL before importing
import os
os.environ["RUN_LOCAL"] = "true"

# Now import
from multi_agent_system import llm
```

### Warning: "LLM is ChatFireworks (not using local mode)"

This means `RUN_LOCAL` is not set or not detected. Check:
1. Environment variable is set: `echo $RUN_LOCAL` (should print `true`)
2. `.env` file has `RUN_LOCAL=true`
3. Python can see the environment variable

## Test Files

- **`tests/test_local_deepseek_multi_agent.py`** - Comprehensive pytest tests
- **`scripts/test_local_deepseek_integration.py`** - Integration test script
- **`scripts/test_local_deepseek.py`** - Basic Ollama connection test

## Related Documentation

- **`LOCAL_DEEPSEEK_SETUP.md`** - Full setup guide
- **`QUICK_START_LOCAL_DEEPSEEK.md`** - Quick start guide
- **`tests/README.md`** - General test documentation

## CI/CD Integration

For automated testing in CI/CD:

```yaml
# Example GitHub Actions workflow
- name: Test Local DeepSeek Integration
  run: |
    # Start Ollama (if needed)
    curl -fsSL https://ollama.com/install.sh | sh
    ollama pull deepseek-r1:1.5b
    
    # Run tests
    RUN_LOCAL=true pytest tests/test_local_deepseek_multi_agent.py -v
  env:
    RUN_LOCAL: true
```

Note: For CI/CD, you might want to skip tests if Ollama is not available (the tests handle this automatically).

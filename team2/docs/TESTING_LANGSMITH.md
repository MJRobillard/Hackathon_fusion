# Testing LangSmith Tracing

This guide walks through setting up and verifying LangSmith tracing for your multi-agent system.

## Prerequisites

1. **LangSmith Account**: Sign up at [smith.langchain.com](https://smith.langchain.com)
2. **API Key**: Get your API key from LangSmith settings

## Setup Steps

### 1. Create `.env` file

Create a `.env` file in the project root with:

```bash
# Required for agent execution
FIREWORKS=your_fireworks_api_key
VOYAGE=your_voyage_api_key

# Required for LangSmith tracing
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=multi-agent-openmc-poc
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Verify setup

Run the setup test to verify all environment variables:

```bash
python test_setup.py
```

Expected output:
```
[OK] FIREWORKS key found: fw_xxx...
[OK] VOYAGE key found: pa_xxx...
[OK] LANGCHAIN_API_KEY found: ls__xxx...
[OK] LANGCHAIN_TRACING_V2 enabled: true
[OK] LANGCHAIN_PROJECT set: multi-agent-openmc-poc
```

## Testing Tracing

### Quick Test (Recommended)

Run the dedicated tracing test:

```bash
python test_langsmith_tracing.py
```

This will:
1. Verify LangSmith configuration
2. Run 3 simple agents in sequence
3. Generate traces you can view in LangSmith UI

### Test with Full Multi-Agent System

Run your actual multi-agent workflow:

```bash
python multi_agent_with_memory.py
```

## Viewing Traces

1. Go to [https://smith.langchain.com/](https://smith.langchain.com/)
2. Navigate to your project (e.g., `multi-agent-openmc-poc`)
3. You should see traces appear in real-time

### What to Look For

**Successful trace will show:**
- **Run name**: "LangGraph" or your workflow name
- **Duration**: Time taken for the entire workflow
- **Child runs**: Each agent and LLM call
- **Input/Output**: State changes between agents
- **Metadata**: Model used, tokens, etc.

**Trace hierarchy example:**
```
LangGraph Run (1.2s)
├─ memory_retrieval (0.3s)
│  └─ VoyageAI Embed (0.2s)
├─ planner (0.5s)
│  └─ ChatFireworks (0.4s)
├─ validator (0.4s)
│  └─ ChatFireworks (0.3s)
└─ runner (0.3s)
```

## Troubleshooting

### Traces not appearing?

**Check 1: Environment variables**
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Tracing:', os.getenv('LANGCHAIN_TRACING_V2')); print('API Key:', os.getenv('LANGCHAIN_API_KEY')[:10] if os.getenv('LANGCHAIN_API_KEY') else 'NOT SET')"
```

**Check 2: API Key validity**
- Go to LangSmith settings
- Regenerate API key if needed
- Update `.env` file

**Check 3: Network/firewall**
- LangSmith needs to send data to `api.smith.langchain.com`
- Check if your firewall blocks this

### Traces delayed?

- Traces can take 5-10 seconds to appear in UI
- Refresh the page
- Check the correct project is selected

### Partial traces?

- If agents crash, you'll see incomplete traces
- This is actually useful for debugging!
- Check the error messages in LangSmith UI

## Advanced: Custom Trace Names

You can customize trace names for better organization:

```python
from langsmith import traceable

@traceable(run_name="My Custom Agent")
def my_agent(state):
    # agent logic
    return state
```

## Benefits of Tracing

### 1. **Debugging**
- See exactly where agents fail
- View intermediate states
- Check LLM inputs/outputs

### 2. **Performance**
- Identify slow agents
- Optimize bottlenecks
- Track token usage

### 3. **Monitoring**
- Track production runs
- Set up alerts
- Analyze patterns

### 4. **Collaboration**
- Share traces with team
- Add comments/annotations
- Create datasets from traces

## Example Trace Views

### Simple Test (`test_langsmith_tracing.py`)
```
Run: test_langsmith_tracing
├─ agent_1: Say hello (0.4s)
│  └─ ChatFireworks: Hello response
├─ agent_2: Physics question (0.5s)
│  └─ ChatFireworks: Fission explanation
└─ agent_3: Goodbye (0.3s)
   └─ ChatFireworks: Farewell
```

### Full System (`multi_agent_with_memory.py`)
```
Run: multi_agent_with_memory
├─ memory_retrieval (0.3s)
│  └─ voyage_embed: Semantic search
├─ planner (0.5s)
│  └─ fireworks_llm: Generate spec
├─ validator (0.4s)
│  └─ fireworks_llm: Validate spec
├─ runner (0.3s)
│  └─ openmc_simulate: Execute
├─ analyzer (0.4s)
│  └─ fireworks_llm: Interpret results
└─ memory_storage (0.2s)
   └─ voyage_embed: Store simulation
```

## Next Steps

Once tracing is working:

1. **Add custom metadata** to track specific metrics
2. **Create datasets** from successful runs
3. **Set up monitoring** for production
4. **Use feedback API** to improve agents

## Resources

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangGraph Tracing Guide](https://langchain-ai.github.io/langgraph/how-tos/tracing/)
- [LangChain Tracing Tutorial](https://python.langchain.com/docs/langsmith/walkthrough)


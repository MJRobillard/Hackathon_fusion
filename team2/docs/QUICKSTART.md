# Quick Start Guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify setup
python test_setup.py
```

## Run Examples

### Example 1: Basic Multi-Agent Flow
```bash
python multi_agent_poc.py
```

**What happens:**
1. 🎯 Planner creates simulation spec from natural language
2. ✅ Validator checks spec for correctness
3. 🚀 Runner executes mock OpenMC simulation
4. 📊 Analyzer interprets keff results

### Example 2: Multi-Agent with Memory
```bash
python multi_agent_with_memory.py
```

**What happens:**
1. 🧠 Memory searches past simulations (using Voyage embeddings)
2. 🎯 Planner uses past context to inform new spec
3. ✅ Validator checks spec
4. 🚀 Runner executes simulation
5. 📊 Analyzer interprets results
6. 💾 Memory stores simulation for future retrieval

**Key feature:** After running multiple simulations, the system learns from past runs and can suggest optimizations based on semantic similarity.

## Agent Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT FLOW                         │
└─────────────────────────────────────────────────────────────┘

User: "Simulate a PWR fuel pin with 4.5% enriched UO2"
  │
  ▼
┌─────────────────────┐
│  MEMORY AGENT       │  Searches past sims (Voyage embeddings)
│  [Optional]         │  → "Found 2 similar past PWR simulations"
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  PLANNER AGENT      │  Creates simulation spec
│  (Fireworks LLM)    │  {
└──────┬──────────────┘    "geometry": "PWR pin cell",
       │                    "materials": ["UO2", "Zircaloy"],
       │                    "particles": 10000,
       ▼                    "batches": 50
┌─────────────────────┐  }
│  VALIDATOR AGENT    │  Reviews spec
│  (Fireworks LLM)    │  → "APPROVED: Realistic PWR parameters"
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  RUNNER AGENT       │  Executes mock OpenMC
│  (Mock Simulation)  │  → keff = 1.28734 ± 0.00028
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  ANALYZER AGENT     │  Interprets results
│  (Fireworks LLM)    │  → "System is supercritical.
└──────┬──────────────┘     Recommend control rods..."
       │
       ▼
┌─────────────────────┐
│  MEMORY STORAGE     │  Stores for future retrieval
│  (Voyage embeddings)│  → Saved to vector memory
└─────────────────────┘
       │
       ▼
   Results returned to user
```

## Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM Calls | Fireworks API | Agent reasoning and text generation |
| Embeddings | Voyage.ai | Semantic search over past simulations |
| Orchestration | LangGraph | State management and agent routing |
| Schema | Pydantic | Type-safe data models |
| Simulation | Mock OpenMC | Placeholder for real nuclear sim |

## Customization

### Add a New Agent

```python
def my_custom_agent(state: AgentState) -> AgentState:
    """Your agent logic here"""
    print("\n🔧 [MY AGENT] Doing something...")
    
    # Do work...
    result = some_function()
    
    return {
        **state,
        "new_field": result,
        "next_action": "next_agent_name"
    }

# Add to graph
workflow.add_node("my_agent", my_custom_agent)
workflow.add_conditional_edges("previous_agent", route, {"my_agent": "my_agent"})
```

### Change LLM Model

```python
llm = ChatFireworks(
    api_key=os.getenv("FIREWORKS"),
    model="accounts/fireworks/models/llama-v3p1-405b-instruct",  # Bigger model
    temperature=0.5  # Lower temperature = more deterministic
)
```

### Use Different Embedding Model

```python
embedding = voyage_client.embed(
    texts,
    model="voyage-large-2",  # Different model
    input_type="document"
)
```

## Architecture Decisions

### Why LangGraph?
- ✅ Built-in state persistence
- ✅ Conditional routing between agents
- ✅ Checkpointing for long-running workflows
- ✅ Native LangChain integration

### Why Fireworks?
- ✅ Fast inference (optimized for production)
- ✅ Multiple model options
- ✅ Good for agentic workflows

### Why Voyage?
- ✅ State-of-art embedding quality
- ✅ Optimized for semantic search
- ✅ Different input types (query vs document)

## Next Steps

1. **Replace mock OpenMC** with real simulation calls
2. **Add persistent storage** for memory (currently in-memory)
3. **Implement error recovery** in agent routing
4. **Add more agents** (e.g., Cost Estimator, Safety Checker)
5. **Create UI** for visualization


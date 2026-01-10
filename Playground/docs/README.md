# Multi-Agent Orchestration POC

Minimal proof-of-concept demonstrating multi-agent orchestration using:
- **Fireworks API** for LLM calls
- **Voyage.ai** for embeddings
- **LangGraph** for agent orchestration and state management
- Mock OpenMC simulation calls

## Architecture

```
User Request
     ↓
[PLANNER AGENT] ────→ Creates simulation specification
     ↓
[VALIDATOR AGENT] ───→ Validates spec for safety/correctness
     ↓
[RUNNER AGENT] ──────→ Executes mock OpenMC simulation
     ↓
[ANALYZER AGENT] ────→ Interprets results and provides insights
     ↓
Final Report
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure `.env` file has your API keys:
```
FIREWORKS=your_fireworks_api_key
VOYAGE=your_voyage_api_key
```

## Run

### Basic Multi-Agent Flow
```bash
python multi_agent_poc.py
```

### With Memory/Embeddings
```bash
python multi_agent_with_memory.py
```

## What Each Agent Does

1. **Planner Agent**: Takes natural language request and designs a simulation spec
2. **Validator Agent**: Reviews spec for physical correctness and computational feasibility
3. **Runner Agent**: Executes the (mock) OpenMC simulation
4. **Analyzer Agent**: Interprets keff results and provides recommendations

## Key Features

- ✅ State management via LangGraph
- ✅ Conditional routing between agents
- ✅ Mock OpenMC execution (realistic keff values)
- ✅ Structured outputs with Pydantic
- ✅ Persistent conversation memory
- ✅ Semantic search over past simulations (embeddings)

## Example Output

```
🎯 [PLANNER AGENT] Designing simulation...
✅ [VALIDATOR AGENT] Checking specification...
🚀 [RUNNER AGENT] Executing simulation...
📊 [ANALYZER AGENT] Analyzing results...

📈 Simulation Results:
{
  "keff": 1.28734,
  "keff_std": 0.00028,
  "runtime_seconds": 0.5,
  "status": "completed"
}

💡 Analysis:
The keff value of 1.287 indicates a supercritical system, typical for fresh 
PWR fuel. The low uncertainty (0.00028) demonstrates good statistical 
convergence. Recommend adding control rods for criticality control.
```


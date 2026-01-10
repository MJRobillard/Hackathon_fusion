# AONP Agents - Quick Start

## What You Have

A complete AI agent system that:
- Takes natural language requests
- Designs and executes nuclear simulations
- Analyzes results and suggests next experiments
- Stores everything in MongoDB with full provenance

## Files

```
📁 Core System
├── aonp_agents.py          # 8-agent LangGraph workflow
├── agent_tools.py          # 5 MongoDB-backed tools
└── inspect_mongodb.py      # Database inspector

📁 Testing & Demo
├── test_aonp_agents.py     # 10 comprehensive tests
└── demo_aonp_agents.py     # 3-example quick demo

📁 Documentation
├── AONP_AGENTS_GUIDE.md    # Complete guide (THIS IS DETAILED)
├── AONP_AGENT_SETUP.md     # Setup documentation
└── QUICKSTART_AGENTS.md    # This file
```

## Run It Now

### Option 1: Quick Demo (2 minutes)
```bash
python demo_aonp_agents.py
```

### Option 2: Full Tests (10 minutes)
```bash
python test_aonp_agents.py
```

### Option 3: Single Request
```bash
python aonp_agents.py
```

Or in code:
```python
from aonp_agents import run_aonp_agent

run_aonp_agent("Run a PWR pin cell with 4.5% enriched UO2 at 600K")
```

## Example Requests

**Single Study:**
- "Simulate a PWR pin cell with 4.5% enriched UO2 at 600K"
- "Run a BWR assembly at 560K"

**Parameter Sweep:**
- "Enrichment sweep from 3% to 5% for PWR at 600K"
- "Temperature sweep from 300K to 900K"

**Query:**
- "Show me all PWR simulations"
- "Which systems are critical?"

## What Happens

```
Your Request
    ↓
Intent Classifier (Agent 1)
    ↓
Planner (Agent 2-3)
    ↓
Executor (Agent 4-6)
    ↓
Analyzer (Agent 7)
    ↓
Suggester (Agent 8)
    ↓
Results + Analysis + Suggestions
```

## Output Example

```
[ANALYSIS]
Keff = 1.03625 ± 0.000419 (supercritical).
Low uncertainty confirms consistent neutron multiplication.
High confidence in results.

[SUGGESTIONS]
1. Validate: Repeat at 4% and 5% enrichment
2. Explore: Temperature sweep 500-700K
3. Test: Different coolant compositions

[RESULTS]
keff = 1.03625 +/- 0.000419
```

## Current Status

✅ **Working:** Natural language → execution → analysis → suggestions  
🔶 **Mocked:** OpenMC execution (returns realistic fake data)  
⏳ **Next:** Swap mock for real OpenMC (see AONP_AGENTS_GUIDE.md)

## Quick Architecture

```
Natural Language
    ↓
LangGraph Agents (8 agents)
    ↓
Agent Tools (5 tools)
    ↓
MongoDB (studies, runs, summaries)
    ↓
[Mock] OpenMC Execution
```

## Replace Mock with Real OpenMC

Edit `agent_tools.py` line 80-110, replace `mock_openmc_execution()` with your bundler → runner → extractor workflow.

## Need Help?

- **Detailed docs:** `AONP_AGENTS_GUIDE.md`
- **Setup info:** `AONP_AGENT_SETUP.md`
- **Test issues:** Check MongoDB connection with `python inspect_mongodb.py`
- **Agent issues:** Check `.env` has `FIREWORKS`, `MONGO_URI`, `VOYAGE` keys

## Dependencies

Already in `requirements.txt`:
- langgraph
- langchain
- langchain-fireworks
- pymongo
- voyageai
- pydantic
- python-dotenv

## That's It!

Run `python demo_aonp_agents.py` to see it in action.


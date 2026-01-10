# 🚀 START HERE - AONP AI Agents

## What You Have Now

A **complete AI agent system** that takes natural language requests and executes nuclear simulations.

```
"Run a PWR pin cell with 4.5% enriched UO2 at 600K"
                    ↓
        [8 AI Agents Process]
                    ↓
    Execution + Analysis + Suggestions
```

---

## Quick Test (30 seconds)

```bash
python -c "from aonp_agents import run_aonp_agent; run_aonp_agent('Simulate a PWR pin cell with 4.5% enriched UO2 at 600K')"
```

## Quick Demo (2 minutes)

```bash
python demo_aonp_agents.py
```

## Full Tests (10 minutes)

```bash
python test_aonp_agents.py
```

---

## What It Does

### Input: Natural Language
- "Simulate a PWR pin cell with 4.5% enriched UO2 at 600K"
- "Enrichment sweep from 3% to 5% for PWR"
- "Show me all critical systems"

### Output: Complete Analysis
```
[RESULTS]
keff = 1.03625 +/- 0.000419

[ANALYSIS]
Supercritical system. High confidence due to low uncertainty.
Neutron multiplication exceeds losses by 3.6%.

[SUGGESTIONS]
1. Validate at 4% and 5% enrichment
2. Test temperature dependence 500-700K
3. Explore coolant composition effects
```

---

## Architecture

```
Natural Language Request
        ↓
┌─────────────────┐
│  8 AI Agents    │  Intent → Plan → Execute → Analyze → Suggest
└─────────────────┘
        ↓
┌─────────────────┐
│   5 Tools       │  submit_study, generate_sweep, query_results...
└─────────────────┘
        ↓
┌─────────────────┐
│   MongoDB       │  studies, runs, summaries
└─────────────────┘
        ↓
┌─────────────────┐
│   OpenMC        │  [Currently Mocked - Easy to Replace]
└─────────────────┘
```

---

## Files You Need

### Core System
- **aonp_agents.py** - 8-agent LangGraph workflow (main system)
- **agent_tools.py** - 5 MongoDB-backed tools

### Testing
- **test_aonp_agents.py** - 10 comprehensive tests
- **demo_aonp_agents.py** - 3-example demo

### Documentation
- **AONP_AGENTS_GUIDE.md** ⭐ - Complete technical guide (READ THIS)
- **QUICKSTART_AGENTS.md** - Quick reference
- **IMPLEMENTATION_SUMMARY.md** - What we built today

### Utilities
- **inspect_mongodb.py** - Database inspector

---

## Example Requests

| Type | Example |
|------|---------|
| **Single Study** | "Simulate a PWR pin cell with 4.5% enriched UO2 at 600K" |
| **Parameter Sweep** | "Enrichment sweep from 3% to 5% for PWR at 600K" |
| **Temperature Sweep** | "Temperature sweep from 300K to 900K for BWR" |
| **Query** | "Show me all PWR simulations" |
| **Query Critical** | "Which systems are critical?" |

---

## System Status

### ✅ Working
- Natural language understanding
- Intent classification (4 types)
- Study specification extraction
- Parameter sweep generation
- MongoDB persistence (3 collections)
- Results analysis (LLM-powered)
- Experiment suggestions (LLM-powered)
- Spec deduplication (hash-based)
- Mock execution (realistic keff values)

### 🔶 Mocked
- OpenMC execution (returns realistic fake data)
- **Location to replace:** `agent_tools.py` line 80-110

### ⏳ Next (Optional)
- Connect real OpenMC
- Add Plotly visualizations
- Memory system (semantic search)
- FastAPI wrapper

---

## Quick Reference

### Run Custom Request
```python
from aonp_agents import run_aonp_agent

final_state = run_aonp_agent("Your request here")

print(final_state['intent'])      # single_study, sweep, query, compare
print(final_state['results'])     # Simulation results
print(final_state['analysis'])    # LLM analysis
print(final_state['suggestion'])  # Next experiment ideas
```

### Use Tools Directly
```python
from agent_tools import submit_study, generate_sweep, query_results

# Single study
result = submit_study({
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Zircaloy", "Water"],
    "enrichment_pct": 4.5,
    "temperature_K": 600,
    "particles": 10000,
    "batches": 50
})

# Parameter sweep
run_ids = generate_sweep(
    base_spec={...},
    param_name="enrichment_pct",
    param_values=[3.0, 3.5, 4.0, 4.5, 5.0]
)

# Query past results
results = query_results({"spec.geometry": "PWR pin cell"})
```

---

## Database State (Verified Working)

```
MongoDB Atlas (AONP)
├── studies (5 unique specs)
│   └── Index: spec_hash (unique)
├── runs (13 executions)
│   └── Indexes: run_id, (spec_hash, created_at)
└── summaries (13 results)
    └── Index: run_id (unique)
```

Inspect anytime:
```bash
python inspect_mongodb.py
```

---

## Performance

| Operation | Time |
|-----------|------|
| Single study | ~5-10s (LLM latency) |
| 5-point sweep | ~15-20s |
| Query | ~2-3s |
| Mock execution | 0.1s per run |
| Real OpenMC | 30-300s per run (expected) |

---

## Hackathon Ready ✅

### What Works Now
✅ Natural language → simulation execution  
✅ Analysis and suggestions  
✅ Database persistence  
✅ Deduplication  
✅ Demo script  
✅ Test suite  
✅ Documentation  

### 5-Minute Demo Flow
1. Show natural language request (30s)
2. Demo single study (90s)
3. Demo parameter sweep (90s)
4. Show database/provenance (30s)
5. Highlight suggestions (30s)

### If You Have Extra Time
- Replace mock with real OpenMC
- Add Plotly charts for sweeps
- Integrate memory/embeddings
- Build FastAPI wrapper

---

## Troubleshooting

**Database connection error?**
```bash
python inspect_mongodb.py
```
Check `MONGO_URI` in `.env`

**Agent not working?**
Check `.env` has:
- `FIREWORKS` - LLM API key
- `MONGO_URI` - MongoDB connection string
- `VOYAGE` - Embeddings API key (optional)

**Want to see what's in the database?**
```bash
python inspect_mongodb.py
```

---

## Next Steps

### Option 1: Test It
```bash
python test_aonp_agents.py
```

### Option 2: Demo It
```bash
python demo_aonp_agents.py
```

### Option 3: Use It
```python
from aonp_agents import run_aonp_agent
run_aonp_agent("Your experiment request")
```

### Option 4: Read Docs
Open `AONP_AGENTS_GUIDE.md` for complete technical details.

---

## Summary

**Built Today:**
- 8-agent LangGraph workflow
- 5 MongoDB-backed tools
- 10 comprehensive tests
- Complete documentation

**Status:** Hackathon ready ✅

**Run:** `python demo_aonp_agents.py`

**Read:** `AONP_AGENTS_GUIDE.md`


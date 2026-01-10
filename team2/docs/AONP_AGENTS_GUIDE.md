# AONP Multi-Agent System - Complete Guide

## Overview

You now have a **fully functional AI agent system** for nuclear simulation experiment design, execution, and analysis. The agents take natural language requests, translate them to simulation specs, execute them via MongoDB-backed tools, analyze results, and suggest next experiments.

---

## Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                    Natural Language Request                       │
│  "Run a PWR pin cell with 4.5% enriched UO2 at 600K"            │
└─────────────────────────┬─────────────────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────────────────┐
│                    AGENT WORKFLOW (LangGraph)                     │
│                                                                   │
│  1. Intent Classifier  → Determine action type                   │
│  2. Planner           → Extract parameters                       │
│  3. Executor          → Run simulation(s)                        │
│  4. Analyzer          → Interpret results                        │
│  5. Suggester         → Recommend next experiments               │
└─────────────────────────┬─────────────────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────────────────┐
│                    AGENT TOOLS (agent_tools.py)                   │
│                                                                   │
│  submit_study()       → Submit single simulation                 │
│  generate_sweep()     → Create parameter sweeps                  │
│  query_results()      → Search past results                      │
│  compare_runs()       → Statistical comparison                   │
│  get_study_statistics() → Database overview                      │
└─────────────────────────┬─────────────────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────────────────┐
│                    MongoDB Atlas (AONP)                           │
│                                                                   │
│  studies   → Unique specs (deduplicated by hash)                │
│  runs      → Execution records                                   │
│  summaries → Results with keff values                            │
└───────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
aonp_agents.py          # Main multi-agent system (LangGraph)
agent_tools.py          # MongoDB-backed simulation tools
test_aonp_agents.py     # Comprehensive test suite (10 tests)
demo_aonp_agents.py     # Quick demo (3 examples)
inspect_mongodb.py      # Database inspection utility
```

---

## Quick Start

### 1. Run a Quick Demo (3 examples, ~2 minutes)

```bash
python demo_aonp_agents.py
```

Shows:
- Single study submission
- Parameter sweep
- Query past results

### 2. Run Comprehensive Tests (10 tests, ~5-10 minutes)

```bash
python test_aonp_agents.py
```

Tests:
1. Single study submission
2. Enrichment sweep
3. Temperature sweep
4. Query past results
5. Complex multi-parameter request
6. Criticality query
7. Suggestion quality
8. Database state verification
9. Deduplication
10. Sweep trend analysis

### 3. Use Directly in Code

```python
from aonp_agents import run_aonp_agent

# Natural language request
final_state = run_aonp_agent(
    "Run an enrichment sweep from 3% to 5% for a PWR at 600K"
)

# Access results
print(f"Intent: {final_state['intent']}")
print(f"Results: {final_state['results']}")
print(f"Analysis: {final_state['analysis']}")
print(f"Suggestions: {final_state['suggestion']}")
```

---

## Supported Request Types

### 1. Single Study
**Examples:**
- "Simulate a PWR pin cell with 4.5% enriched UO2 at 600K"
- "Run a BWR assembly at 560K with 3.8% enrichment"
- "I need a fast reactor simulation with MOX fuel at 800K"

**Intent:** `single_study`

**What Happens:**
1. Planner extracts geometry, materials, enrichment, temperature
2. Executor calls `submit_study()`
3. Single simulation runs
4. Analysis and suggestions generated

### 2. Parameter Sweep
**Examples:**
- "Run an enrichment sweep from 3% to 5% for a PWR at 600K"
- "Do a temperature sweep from 300K to 900K for a BWR"
- "I need to vary enrichment in 0.5% steps from 2.5% to 5.5%"

**Intent:** `sweep`

**What Happens:**
1. Sweep planner extracts base spec + parameter to vary
2. Executor calls `generate_sweep()`
3. Multiple simulations run
4. Results compared statistically
5. Trend analysis and suggestions

### 3. Query Past Results
**Examples:**
- "Show me all PWR simulations"
- "Which simulations resulted in critical systems?"
- "Find BWR runs with high enrichment"

**Intent:** `query`

**What Happens:**
1. Query keywords extracted
2. MongoDB query constructed
3. Past results retrieved
4. Analysis of trends

### 4. Compare Runs
**Examples:**
- "Compare my recent PWR runs"
- "Show differences between BWR and PWR criticality"

**Intent:** `compare`

**What Happens:**
- Similar to query, but focused on comparison

---

## Agent Workflow Details

### Agent 1: Intent Classifier
**Input:** Natural language request  
**Output:** Intent category (`single_study`, `sweep`, `query`, `compare`)  
**LLM Used:** Yes

### Agent 2: Study Planner
**Input:** Request (for single study intent)  
**Output:** Study specification JSON  
**LLM Used:** Yes  
**Example Output:**
```json
{
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Zircaloy", "Water"],
    "enrichment_pct": 4.5,
    "temperature_K": 600,
    "particles": 10000,
    "batches": 50
}
```

### Agent 3: Sweep Planner
**Input:** Request (for sweep intent)  
**Output:** Sweep configuration  
**LLM Used:** Yes  
**Example Output:**
```json
{
    "base_spec": { /* study spec */ },
    "param_name": "enrichment_pct",
    "param_values": [3.0, 3.5, 4.0, 4.5, 5.0]
}
```

### Agent 4: Study Executor
**Input:** Study spec  
**Output:** Run ID and results  
**LLM Used:** No  
**Tool Called:** `submit_study()`

### Agent 5: Sweep Executor
**Input:** Sweep config  
**Output:** Multiple run IDs and comparison  
**LLM Used:** No  
**Tools Called:** `generate_sweep()`, `compare_runs()`

### Agent 6: Query Executor
**Input:** Request with query keywords  
**Output:** Past results  
**LLM Used:** No  
**Tool Called:** `query_results()`

### Agent 7: Analyzer
**Input:** Results from executor  
**Output:** Technical analysis  
**LLM Used:** Yes  
**Analysis Includes:**
- Key findings (keff, trends, anomalies)
- Physical interpretation
- Confidence assessment

### Agent 8: Suggester
**Input:** Request + Analysis + Results  
**Output:** 2-3 specific follow-up experiments  
**LLM Used:** Yes  
**Suggestions Cover:**
- Validation experiments
- Trend exploration
- Knowledge gap filling

---

## Example Outputs

### Single Study Output

```
[ANALYSIS]
Keff = 1.03625 ± 0.000419 (supercritical). Low statistical 
uncertainty indicates consistent neutron multiplication. 
Supercriticality implies net neutron gain, risking uncontrolled 
power rise. High confidence due to std < 0.05% of keff.

[SUGGESTIONS]
1. Validate enrichment sensitivity: Repeat with 4% and 5% 
   enriched UO2 at 600K to confirm keff trends.
   
2. Explore temperature dependence: Vary fuel temperature 
   (500K, 600K, 700K) at 4.5% enrichment to assess thermal effects.
   
3. Test coolant interaction: Simulate with different coolant 
   compositions (H2O vs borated water) at 4.5% enrichment.

[RESULTS SUMMARY]
  keff = 1.03625 +/- 0.000419
```

### Parameter Sweep Output

```
[SWEEP RESULTS]
  Enrichment sweep: 5 runs
  keff range: [0.97996, 1.08369]
  keff mean: 1.02227

[ENRICHMENT vs KEFF]
  3.0% -> keff = 0.97996
  3.5% -> keff = 0.98230
  4.0% -> keff = 1.02973
  4.5% -> keff = 1.03565
  5.0% -> keff = 1.08369

[ANALYSIS]
Positive correlation between enrichment and keff confirmed.
Criticality threshold crossed between 3.5% and 4.0%.
Trend consistent with expected fission rate increase.

[SUGGESTIONS]
1. Refine critical enrichment: Sweep 3.5-4.0% in 0.1% steps
2. Temperature coefficient: Repeat sweep at 300K and 900K
3. Burnup effects: Model time-dependent keff decay
```

---

## Database Schema (Verified Working)

### `studies` Collection
```python
{
    "spec_hash": "539daca2732e...",  # SHA256 of canonical spec
    "canonical_spec": { /* full spec */ },
    "created_at": "2026-01-10T20:01:10Z"
}
```
**Index:** `spec_hash` (unique) - Ensures deduplication

### `runs` Collection
```python
{
    "run_id": "run_8e742c47",
    "spec_hash": "539daca2732e...",
    "status": "completed",
    "created_at": "2026-01-10T20:01:10Z"
}
```
**Indexes:**
- `run_id` (unique)
- `(spec_hash, created_at)` (compound, descending)

### `summaries` Collection
```python
{
    "run_id": "run_8e742c47",
    "spec_hash": "539daca2732e...",
    "keff": 1.02741,
    "keff_std": 0.000293,
    "runtime_seconds": 0.1,
    "status": "completed",
    "created_at": "2026-01-10T20:01:10Z",
    "spec": { /* full spec embedded for easy querying */ }
}
```
**Index:** `run_id` (unique)

---

## Current Status & Next Steps

### ✅ Working
- Natural language → study spec extraction
- Intent classification (4 types)
- Parameter sweep generation
- Database persistence (MongoDB)
- Results analysis (LLM-powered)
- Experiment suggestions (LLM-powered)
- Spec deduplication (hash-based)
- Mock execution (realistic keff values)

### 🔶 Mocked (Replace for Production)
- **OpenMC Execution** - Currently in `mock_openmc_execution()`
  - Replace with: `bundler → runner → extractor` workflow
  - Location: `agent_tools.py` line ~80

### 🚀 Hackathon Ready Features
1. **Demo script** - Shows capabilities in 2 minutes
2. **Test suite** - Validates all functionality
3. **Documentation** - This guide
4. **Integration point** - Easy to swap mock for real OpenMC

### 📋 Hackathon TODO (If Time Permits)
1. **Visualization** - Plotly charts for sweep results
2. **Advanced queries** - LLM-powered MongoDB filter generation
3. **Memory system** - Add Voyage embeddings (like your existing code)
4. **Real OpenMC** - Connect actual bundler/runner/extractor
5. **FastAPI wrapper** - REST API for agents

---

## Integration with Real OpenMC

### Current (Mock):
```python
def mock_openmc_execution(spec: StudySpec) -> Dict[str, Any]:
    # Returns fake but realistic keff
    return {"keff": 1.02, "keff_std": 0.0003, ...}
```

### Replace With:
```python
def real_openmc_execution(spec: StudySpec) -> Dict[str, Any]:
    from aonp.core.bundler import stage_bundle
    from aonp.core.runner import execute
    from aonp.core.extractor import extract
    
    # Bundle inputs
    run_id = f"run_{uuid4().hex[:8]}"
    bundle_path = Path(f"/tmp/bundles/{run_id}")
    manifest = stage_bundle(spec, run_id, bundle_path)
    
    # Execute OpenMC
    execute(manifest, bundle_path)
    
    # Extract results
    statepoint_path = bundle_path / "outputs" / "statepoint.h5"
    summary = extract(statepoint_path)
    
    return {
        "keff": summary.keff,
        "keff_std": summary.keff_std,
        "runtime_seconds": summary.runtime_seconds,
        "status": "completed"
    }
```

**Location:** `agent_tools.py` line 80-110

---

## Troubleshooting

### LLM Output Issues
**Symptom:** Agents use fallback specs  
**Cause:** LLM output includes thinking tags or non-JSON text  
**Solution:** Current code has try/except with fallbacks. If needed, improve prompt or parsing.

### Database Connection
**Symptom:** Connection errors  
**Check:** `MONGO_URI` in `.env`  
**Test:** `python inspect_mongodb.py`

### Agent Too Verbose
**Symptom:** LLM outputs thinking process  
**Solution:** Add "Output ONLY the answer, no thinking process" to prompts

---

## Performance Notes

- **Single study:** ~5-10 seconds (LLM latency)
- **5-point sweep:** ~15-20 seconds (5 studies + comparison)
- **Query:** ~2-3 seconds (MongoDB + analysis)
- **Mock execution:** 0.1 seconds per run
- **Real OpenMC:** ~30-300 seconds per run (depends on particles/batches)

---

## Key Design Decisions

### 1. Mock Execution First
✓ Allows rapid agent development  
✓ Realistic output for testing  
✓ Easy to swap for real execution

### 2. MongoDB Embedding in Summaries
✓ Full spec in summaries collection enables rich queries  
✓ No joins needed for analysis  
✓ Slight denormalization for performance

### 3. LLM for Planning + Analysis
✓ Natural language understanding  
✓ Technical analysis generation  
✓ Experiment suggestions  
✗ Not for execution (use tools)

### 4. Deterministic Hashing
✓ Same spec → same hash → deduplication  
✓ Canonical JSON serialization  
✓ Provenance tracking

---

## Hackathon Demo Script

**5-Minute Demo Flow:**

1. **Introduction** (30 sec)
   - "AI agents for nuclear simulation experiment design"

2. **Demo 1: Natural Language** (90 sec)
   - Show: "Simulate a PWR pin cell with 4.5% enriched UO2 at 600K"
   - Highlight: Intent classification, spec extraction, execution

3. **Demo 2: Parameter Sweep** (90 sec)
   - Show: "Run an enrichment sweep from 3% to 5%"
   - Highlight: Automatic sweep generation, results comparison

4. **Demo 3: Suggestions** (60 sec)
   - Show: Analysis and suggested next experiments
   - Highlight: AI-powered experiment design

5. **Database/Provenance** (30 sec)
   - Show: MongoDB with deduplicated studies, full provenance

6. **Conclusion** (30 sec)
   - "Same inputs → same hash → reproducible science"

---

## Summary

✅ **Agents:** 8 agents in LangGraph workflow  
✅ **Tools:** 5 MongoDB-backed tools  
✅ **Database:** 3 collections with indexes  
✅ **Tests:** 10 comprehensive tests  
✅ **Demo:** Quick 3-example demo  
✅ **Docs:** This guide + AONP_AGENT_SETUP.md  

**Status:** Ready for hackathon. Swap mock execution for real OpenMC when ready.

**Next:** Run tests, refine prompts, add visualizations, or integrate real OpenMC.


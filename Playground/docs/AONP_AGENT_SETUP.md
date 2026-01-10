# AONP Agent Tools - Setup Complete

## What We Built

### 1. MongoDB Connection ✓
- Connected to AONP database with 3 collections:
  - `studies` - Unique study specifications (deduplicated by spec_hash)
  - `runs` - Individual execution records
  - `summaries` - Simulation results with keff values

### 2. Agent Tools ✓ (`agent_tools.py`)

Five core tools for AI agents to interact with the simulation system:

#### `submit_study(study_spec)`
Submits a new simulation study to the database.

**Input:**
```python
{
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Zircaloy", "Water"],
    "enrichment_pct": 4.5,
    "temperature_K": 600,
    "particles": 10000,
    "batches": 50
}
```

**Output:**
```python
{
    "run_id": "run_8e742c47",
    "spec_hash": "539daca2732e...",
    "keff": 1.02741,
    "keff_std": 0.000293,
    "status": "completed"
}
```

**What it does:**
1. Hashes study spec (SHA256 of canonical JSON)
2. Upserts to `studies` collection (deduplication)
3. Creates run record in `runs` collection
4. Executes simulation (currently mocked)
5. Stores results in `summaries` collection

#### `query_results(filter_params, limit=10)`
Queries past simulation results.

**Examples:**
```python
# All PWR simulations
query_results({"spec.geometry": "PWR pin cell"})

# Supercritical systems
query_results({"keff": {"$gt": 1.0}})

# High enrichment
query_results({"spec.enrichment_pct": {"$gte": 4.5}})
```

#### `generate_sweep(base_spec, param_name, param_values)`
Generates and executes parameter sweeps.

**Example:**
```python
sweep_run_ids = generate_sweep(
    base_spec={
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Zircaloy", "Water"],
        "temperature_K": 600,
        "particles": 10000,
        "batches": 50
    },
    param_name="enrichment_pct",
    param_values=[3.0, 3.5, 4.0, 4.5, 5.0]
)
# Returns: ['run_548e8ad2', 'run_b29af257', ...]
```

#### `compare_runs(run_ids)`
Compares multiple runs and returns statistics.

**Output:**
```python
{
    "num_runs": 5,
    "keff_values": [0.97996, 0.98230, 1.02973, 1.03565, 1.08369],
    "keff_mean": 1.02227,
    "keff_min": 0.97996,
    "keff_max": 1.08369,
    "runs": [...]
}
```

#### `get_study_statistics()`
Gets database statistics and recent runs.

**Output:**
```python
{
    "total_studies": 5,
    "total_runs": 13,
    "total_summaries": 13,
    "completed_runs": 13,
    "recent_runs": [...]
}
```

---

## Current Status

### ✓ Working
- MongoDB connection and schema
- Study spec hashing (deterministic deduplication)
- All 5 agent tools functional
- Mock OpenMC execution (realistic results)
- Proper error handling

### 🔶 Mocked (Replace Later)
- **OpenMC execution** - Currently returns mock results
  - Realistic keff values based on enrichment/temperature
  - ~0.1s execution time
  - To replace: Call actual `bundler → runner → extractor` workflow

### ⏳ Next Steps

1. **Integrate with LangGraph agents** (your `multi_agent_with_memory.py` pattern)
2. **Add analysis agent** - Suggests next experiments based on results
3. **Connect real OpenMC** - Replace `mock_openmc_execution()` with actual workflow
4. **Add sweep visualization** - Plotly charts for parameter studies

---

## Testing

### Run the demo:
```bash
python agent_tools.py
```

This executes:
1. Single study submission
2. Query PWR simulations
3. 5-point enrichment sweep (3.0% → 5.0%)
4. Compare sweep results
5. Database statistics

### Inspect the database:
```bash
python inspect_mongodb.py
```

Shows all collections, sample documents, and indexes.

---

## Integration Pattern for LangGraph Agents

Based on your `multi_agent_with_memory.py`, here's how to integrate:

```python
from agent_tools import submit_study, query_results, generate_sweep, compare_runs

def experiment_planner_agent(state: AgentState) -> AgentState:
    """Agent that designs and submits experiments"""
    
    # Parse user request into study spec
    spec = {
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Zircaloy", "Water"],
        "enrichment_pct": 4.5,
        "temperature_K": 600,
        "particles": 10000,
        "batches": 50
    }
    
    # Submit to database
    result = submit_study(spec)
    
    return {
        **state,
        "run_id": result["run_id"],
        "keff": result["keff"],
        "next_action": "analyze"
    }

def sweep_generator_agent(state: AgentState) -> AgentState:
    """Agent that generates parameter sweeps"""
    
    # Check if similar sweeps exist
    past_results = query_results({"spec.geometry": "PWR pin cell"})
    
    # Generate new sweep
    run_ids = generate_sweep(
        base_spec=state["base_spec"],
        param_name="enrichment_pct",
        param_values=[3.0, 3.5, 4.0, 4.5, 5.0]
    )
    
    # Compare results
    comparison = compare_runs(run_ids)
    
    return {
        **state,
        "sweep_results": comparison,
        "next_action": "suggest_next"
    }
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI AGENTS (LangGraph)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Planner  │  │  Sweep   │  │ Analyzer │  │Suggester │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │             │              │             │         │
│       └─────────────┴──────────────┴─────────────┘         │
│                          ↓                                  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              AGENT TOOLS (agent_tools.py)                   │
│   submit_study  |  query_results  |  generate_sweep         │
│   compare_runs  |  get_study_statistics                     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   MongoDB Atlas (AONP)                      │
│   studies  |  runs  |  summaries                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│          WORKFLOW (Replace Mock Later)                      │
│   bundler → runner (OpenMC) → extractor                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema (Verified)

### `studies` Collection
```python
{
    "spec_hash": "539daca2732e...",  # SHA256 of canonical spec
    "canonical_spec": {
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Zircaloy", "Water"],
        "enrichment_pct": 4.5,
        # ...
    },
    "created_at": datetime(2026, 1, 10, ...)
}
```
**Index:** `spec_hash` (unique)

### `runs` Collection
```python
{
    "run_id": "run_8e742c47",
    "spec_hash": "539daca2732e...",
    "status": "completed",
    "created_at": datetime(2026, 1, 10, ...)
}
```
**Indexes:** 
- `run_id` (unique)
- `(spec_hash, created_at)` (compound, descending on created_at)

### `summaries` Collection
```python
{
    "run_id": "run_8e742c47",
    "spec_hash": "539daca2732e...",
    "keff": 1.02741,
    "keff_std": 0.000293,
    "runtime_seconds": 0.1,
    "status": "completed",
    "created_at": datetime(2026, 1, 10, ...),
    "spec": {
        # Full spec embedded for easy querying
        "geometry": "PWR pin cell",
        "enrichment_pct": 4.5,
        # ...
    }
}
```
**Index:** `run_id` (unique)

---

## Next: Agent Integration

**You're ready to build the agent layer.** The tools are tested and working.

### Recommended approach:
1. Start with a simple agent that takes natural language → submits study
2. Add memory retrieval (like your existing `multi_agent_with_memory.py`)
3. Add sweep generation agent
4. Add results analysis + suggestions agent

### Example natural language requests the agents should handle:
- "Run a PWR pin cell simulation with 4.5% enriched UO2 at 600K"
- "Do a temperature sweep from 300K to 900K for a BWR assembly"
- "What's the effect of enrichment on keff for fast reactors?"
- "Suggest the next experiment based on my recent PWR results"

**Want to proceed with building the agent layer now, or need to refine the tools first?**


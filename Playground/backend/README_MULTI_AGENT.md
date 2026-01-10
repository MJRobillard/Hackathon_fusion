# AONP Multi-Agent System

**Router + Specialist Agents for Nuclear Simulation**

This implementation follows the architecture from `plan.md` with local execution.

---

## Architecture

```
User Query → Router Agent → Specialist Agents → Tools → OpenMC/MongoDB
                ↓
         [Studies | Sweep | Query | Analysis]
```

### Agents

| Agent | Purpose | Tools |
|-------|---------|-------|
| **Router** | Classify intent & delegate | None (pure routing) |
| **Studies** | Single simulations | submit_study, get_run_by_id, validate_physics |
| **Sweep** | Parameter sweeps | generate_sweep, compare_runs, validate_physics |
| **Query** | Database searches | query_results, get_study_statistics, get_recent_runs |
| **Analysis** | Result comparisons | compare_runs, get_run_by_id |

### Tools (8 total)

**Phase 1 (MVP) - Implemented ✅**
1. `submit_study` - Submit single simulation
2. `query_results` - Search historical data
3. `generate_sweep` - Create parameter sweep
4. `compare_runs` - Compare multiple runs
5. `get_study_statistics` - Database stats
6. `get_run_by_id` - Fetch specific run
7. `get_recent_runs` - Get latest runs
8. `validate_physics` - Check spec validity

---

## File Structure

```
Playground/backend/
├── agent_tools.py              # 8 tools for agents
├── multi_agent_system.py       # Router + 4 specialist agents
├── api/
│   ├── main_v2.py             # FastAPI server v2
│   └── tests/
│       └── test_api_v2.py     # API endpoint tests
└── tests/
    ├── test_agent_tools.py    # Tool tests
    └── test_multi_agent_system.py  # Agent tests
```

---

## API Endpoints

### Natural Language Query (Main Interface)

```bash
# Submit query
POST /api/v1/query
{
  "query": "Simulate PWR at 4.5% enrichment",
  "options": {"stream": false}
}

# Get status
GET /api/v1/query/{query_id}

# Stream progress (SSE)
GET /api/v1/query/{query_id}/stream
```

### Direct Tool Access (Bypass Agents)

```bash
# Submit study directly
POST /api/v1/studies
{
  "geometry": "PWR pin cell",
  "materials": ["UO2", "Zircaloy", "Water"],
  "enrichment_pct": 4.5,
  "temperature_K": 600
}

# Get study by ID
GET /api/v1/studies/{run_id}

# Submit sweep directly
POST /api/v1/sweeps
{
  "base_spec": {...},
  "param_name": "enrichment_pct",
  "param_values": [3.0, 4.0, 5.0]
}

# Query runs
GET /api/v1/runs?geometry=PWR&enrichment_min=3.0&limit=20

# Compare runs
POST /api/v1/runs/compare
{
  "run_ids": ["run_abc123", "run_def456"]
}

# Statistics
GET /api/v1/statistics

# Health check
GET /api/v1/health
```

---

## Setup

### 1. Install Dependencies

```bash
cd Playground/backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```bash
# MongoDB
MONGO_URI=mongodb://localhost:27017

# Fireworks API (for LLM)
FIREWORKS=your_api_key_here

# OpenMC execution mode
USE_REAL_OPENMC=false  # Set to true for real simulations

# API settings (optional)
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
```

### 3. Start MongoDB

```bash
# Local MongoDB
mongod --dbpath /path/to/data

# Or use MongoDB Atlas (cloud)
```

---

## Usage

### Option 1: Run API Server

```bash
cd Playground/backend/api
python main_v2.py
```

Then access:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Option 2: Use Python Directly

```python
from multi_agent_system import run_multi_agent_query

# Single study
result = run_multi_agent_query("Simulate PWR pin with 4.5% enriched UO2 at 600K")
print(result["results"])

# Parameter sweep
result = run_multi_agent_query("Compare enrichments from 3% to 5%")
print(result["results"]["comparison"])

# Query database
result = run_multi_agent_query("Show me the 10 most recent simulations")
print(result["results"]["results"])

# Analysis
result = run_multi_agent_query("Compare run_abc123 and run_def456")
print(result["results"]["interpretation"])
```

### Option 3: Use Tools Directly

```python
from agent_tools import submit_study, generate_sweep, compare_runs

# Single study
result = submit_study({
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Zircaloy", "Water"],
    "enrichment_pct": 4.5,
    "temperature_K": 600
})
print(f"keff = {result['keff']:.5f}")

# Parameter sweep
run_ids = generate_sweep(
    base_spec={
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Zircaloy", "Water"],
        "temperature_K": 600
    },
    param_name="enrichment_pct",
    param_values=[3.0, 3.5, 4.0, 4.5, 5.0]
)

# Compare results
comparison = compare_runs(run_ids)
print(f"keff range: [{comparison['keff_min']:.5f}, {comparison['keff_max']:.5f}]")
```

---

## Testing

### Run All Tests

```bash
cd Playground/backend

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_agent_tools.py -v
pytest tests/test_multi_agent_system.py -v

# Run API tests
pytest api/tests/test_api_v2.py -v

# Skip slow tests
pytest tests/ -v -m "not slow"
```

### Test Coverage

```bash
# Install coverage
pip install pytest-cov

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# View report
open htmlcov/index.html
```

### Manual Testing with curl

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Submit query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Simulate PWR pin with 4.5% enriched UO2"}'

# Get query status
curl http://localhost:8000/api/v1/query/q_abc12345

# Submit study directly
curl -X POST http://localhost:8000/api/v1/studies \
  -H "Content-Type: application/json" \
  -d '{
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Water"],
    "enrichment_pct": 4.5
  }'

# Query runs
curl "http://localhost:8000/api/v1/runs?geometry=PWR&limit=10"

# Statistics
curl http://localhost:8000/api/v1/statistics
```

---

## Example Workflows

### Workflow 1: Single Study

```
User: "Simulate PWR at 4.5% enrichment"
  ↓
Router: intent=single_study → Studies Agent
  ↓
Studies Agent:
  1. validate_physics(spec)
  2. submit_study(spec)
  3. Return results
  ↓
Response: {run_id, keff, interpretation}
```

### Workflow 2: Parameter Sweep

```
User: "Compare enrichments 3-5%"
  ↓
Router: intent=sweep → Sweep Agent
  ↓
Sweep Agent:
  1. generate_sweep(base, "enrichment_pct", [3.0, 3.5, 4.0, 4.5, 5.0])
  2. compare_runs(run_ids)
  ↓
Response: {run_ids, comparison, trend}
```

### Workflow 3: Database Query

```
User: "Show me recent PWR simulations"
  ↓
Router: intent=query → Query Agent
  ↓
Query Agent:
  1. query_results({"spec.geometry": "PWR"})
  2. Format results
  ↓
Response: {results, count, summary}
```

### Workflow 4: Analysis

```
User: "Compare run_abc123 and run_def456"
  ↓
Router: intent=analysis → Analysis Agent
  ↓
Analysis Agent:
  1. get_run_by_id(run_abc123)
  2. get_run_by_id(run_def456)
  3. compare_runs([...])
  4. Generate interpretation
  ↓
Response: {comparison, interpretation}
```

---

## Performance

### With Mock OpenMC (USE_REAL_OPENMC=false)

| Operation | Time | Cost |
|-----------|------|------|
| Single study | ~2s | $0.01 |
| Sweep (5x) | ~3s | $0.02 |
| Query | ~1s | $0.01 |
| Analysis | ~2s | $0.01 |

### With Real OpenMC (USE_REAL_OPENMC=true)

| Operation | Time | Cost |
|-----------|------|------|
| Single study | ~6s | $0.02 |
| Sweep (5x) | ~25s | $0.03 |
| Query | ~1s | $0.01 |
| Analysis | ~2s | $0.02 |

---

## Troubleshooting

### MongoDB Connection Error

```bash
# Check MongoDB is running
mongosh

# Or check connection string
echo $MONGO_URI
```

### Fireworks API Error

```bash
# Check API key is set
echo $FIREWORKS

# Test connection
python -c "from langchain_fireworks import ChatFireworks; llm = ChatFireworks(); print(llm.invoke('test'))"
```

### OpenMC Import Error

OpenMC only works on Linux/macOS. On Windows, use WSL or set `USE_REAL_OPENMC=false`.

```bash
# Install OpenMC (Linux/macOS)
conda install -c conda-forge openmc

# Or use mock mode
export USE_REAL_OPENMC=false
```

### Test Failures

```bash
# Run tests with verbose output
pytest tests/ -v -s

# Run single test
pytest tests/test_agent_tools.py::test_submit_study_success -v

# Check MongoDB has data
python -c "from pymongo import MongoClient; print(MongoClient('mongodb://localhost:27017')['aonp'].list_collection_names())"
```

---

## Next Steps

### Phase 2: Parallelization (Future)

- `parallel_submit(specs)` - Submit multiple studies at once
- `batch_status(run_ids)` - Check status of multiple runs
- `cancel_run(run_id)` - Stop running simulation
- `adaptive_sweep(param, target)` - Smart sweep that narrows based on results

### Phase 3: Intelligence (Future)

- `find_similar_runs(spec)` - Semantic search for related sims
- `estimate_runtime(spec)` - Predict simulation duration
- `suggest_next_experiments(run_ids)` - Recommend follow-up studies
- `physics_explanation(keff, spec)` - Explain why keff is what it is
- `benchmark_comparison(run_id)` - Compare to known benchmarks

---

## Contributing

### Adding a New Tool

1. Add function to `agent_tools.py`
2. Add to `AGENT_TOOLS` registry
3. Write tests in `tests/test_agent_tools.py`
4. Update agent to use tool
5. Update this README

### Adding a New Agent

1. Create agent class in `multi_agent_system.py`
2. Add to `MultiAgentOrchestrator.agents`
3. Update router to route to new agent
4. Write tests in `tests/test_multi_agent_system.py`
5. Update this README

---

## License

MIT License - See LICENSE file for details


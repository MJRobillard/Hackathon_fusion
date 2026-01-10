# AONP Multi-Agent System - Quick Start

Get up and running in 5 minutes!

---

## Step 1: Install Dependencies (1 min)

```bash
cd Playground/backend
pip install -r requirements.txt
```

---

## Step 2: Configure Environment (1 min)

Create `.env` file:

```bash
# MongoDB (required)
MONGO_URI=mongodb://localhost:27017

# Fireworks API (required for LLM)
FIREWORKS=your_api_key_here

# OpenMC mode (optional)
USE_REAL_OPENMC=false  # Use 'true' for real simulations
```

**Get Fireworks API Key:**
1. Go to https://fireworks.ai
2. Sign up / Log in
3. Get API key from dashboard

---

## Step 3: Start MongoDB (1 min)

### Option A: Local MongoDB

```bash
# Install MongoDB (if not installed)
# macOS: brew install mongodb-community
# Ubuntu: sudo apt install mongodb

# Start MongoDB
mongod --dbpath /path/to/data
```

### Option B: MongoDB Atlas (Cloud)

1. Go to https://www.mongodb.com/cloud/atlas
2. Create free cluster
3. Get connection string
4. Use in `.env` as `MONGO_URI`

---

## Step 4: Run Demo (1 min)

```bash
python demo_multi_agent.py
```

This will:
- Test all 4 agents (Studies, Sweep, Query, Analysis)
- Create sample simulations
- Show database statistics

---

## Step 5: Start API Server (1 min)

```bash
cd api
python main_v2.py
```

Then open:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

---

## Quick Test

### Test 1: Submit Query via API

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Simulate PWR pin with 4.5% enriched UO2"}'
```

Response:
```json
{
  "query_id": "q_abc12345",
  "status": "queued",
  "assigned_agent": "routing",
  "estimated_duration": 30
}
```

### Test 2: Check Query Status

```bash
curl http://localhost:8000/api/v1/query/q_abc12345
```

### Test 3: Submit Study Directly

```bash
curl -X POST http://localhost:8000/api/v1/studies \
  -H "Content-Type: application/json" \
  -d '{
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Water"],
    "enrichment_pct": 4.5
  }'
```

Response:
```json
{
  "run_id": "run_def67890",
  "keff": 1.05234,
  "keff_std": 0.000345,
  "status": "completed"
}
```

---

## Run Tests

```bash
# Run all tests
python run_tests.py

# Run specific test suite
pytest tests/test_agent_tools.py -v
pytest tests/test_multi_agent_system.py -v
pytest api/tests/test_api_v2.py -v
```

---

## Example Usage

### Python API

```python
from multi_agent_system import run_multi_agent_query

# Single study
result = run_multi_agent_query("Simulate PWR at 4.5% enrichment")
print(result["results"]["keff"])

# Parameter sweep
result = run_multi_agent_query("Compare enrichments 3% to 5%")
print(result["results"]["comparison"])

# Query database
result = run_multi_agent_query("Show me recent PWR simulations")
print(result["results"]["results"])
```

### Direct Tools

```python
from agent_tools import submit_study, generate_sweep

# Single study
result = submit_study({
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Water"],
    "enrichment_pct": 4.5
})

# Parameter sweep
run_ids = generate_sweep(
    base_spec={"geometry": "PWR", "materials": ["UO2", "Water"]},
    param_name="enrichment_pct",
    param_values=[3.0, 4.0, 5.0]
)
```

---

## Troubleshooting

### "MONGO_URI not found"
→ Create `.env` file with `MONGO_URI=mongodb://localhost:27017`

### "Connection refused to MongoDB"
→ Start MongoDB: `mongod --dbpath /path/to/data`

### "FIREWORKS API key not set"
→ Add `FIREWORKS=your_key` to `.env` file

### "openmc module not found"
→ Set `USE_REAL_OPENMC=false` in `.env` (or install OpenMC on Linux/macOS)

### Tests failing
→ Make sure MongoDB is running and `.env` is configured

---

## Next Steps

1. **Read Full Documentation**: `README_MULTI_AGENT.md`
2. **Explore API**: http://localhost:8000/docs
3. **Run Tests**: `python run_tests.py`
4. **Customize Agents**: Edit `multi_agent_system.py`
5. **Add Tools**: Edit `agent_tools.py`

---

## Architecture Overview

```
User Query → Router Agent → Specialist Agent → Tools → OpenMC/MongoDB
                ↓
         [Studies | Sweep | Query | Analysis]
```

**Agents:**
- **Router**: Classifies intent, delegates to specialist
- **Studies**: Single simulations
- **Sweep**: Parameter sweeps
- **Query**: Database searches
- **Analysis**: Result comparisons

**Tools (8):**
- submit_study, query_results, generate_sweep, compare_runs
- get_study_statistics, get_run_by_id, get_recent_runs, validate_physics

---

## Support

- **Documentation**: `README_MULTI_AGENT.md`
- **Architecture**: `plan.md`
- **Issues**: Check MongoDB logs, API logs, test output

---

**Ready to go!** 🚀

Start with: `python demo_multi_agent.py`


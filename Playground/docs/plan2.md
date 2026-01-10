# AONP Agent Orchestration Plan 🚀

**Quick Guide**: How to orchestrate agents to design and execute nuclear experiments

---

## 🎯 System Architecture

```
┌─────────────┐      HTTP POST       ┌──────────────────┐
│   Frontend  │ ──────────────────> │   FastAPI Server │
│  (Next.js)  │                      │   (port 8000)    │
└─────────────┘                      └────────┬─────────┘
                                              │
                                              ▼
                    ┌──────────────────────────────────────┐
                    │      LangGraph Multi-Agent           │
                    │   (aonp_agents.py)                   │
                    └──────────────┬───────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
    ┌──────────┐           ┌──────────┐           ┌──────────┐
    │ Intent   │           │ Planner  │           │Executor  │
    │Classifier│──────────>│  Agent   │──────────>│  Agent   │
    └──────────┘           └──────────┘           └──────────┘
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │ OpenMC Adapter  │
                                              │ (Real/Mock)     │
                                              └────────┬────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │    MongoDB      │
                                              │    (Results)    │
                                              └─────────────────┘
```

---

## 🚀 Quick Start (3 Steps)

### Step 1: Start API Server
```bash
cd Playground/backend/api
python main.py
```
**Output**: Server at `http://localhost:8000`

### Step 2: Send Request
```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Simulate a PWR pin cell with 4.5% enriched UO2 at 900K",
    "options": {"stream": false}
  }'
```

### Step 3: Check Results
```bash
curl http://localhost:8000/api/v1/requests/req_abc123
```

---

## 📡 Core API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/requests` | POST | Submit natural language query |
| `/api/v1/requests/{id}` | GET | Check request status |
| `/api/v1/requests/{id}/stream` | GET | Real-time progress (SSE) |
| `/api/v1/runs` | GET | Query simulation runs |
| `/api/v1/runs/compare` | POST | Compare multiple runs |
| `/api/v1/statistics` | GET | System statistics |
| `/api/v1/health` | GET | Health check |

---

## 🎭 Agent Workflow Patterns

### Pattern 1: Single Study
**User Query**: "Run a simulation of PWR fuel at 4.5% enrichment"

**Agent Flow**:
```
1. Intent Classifier   → "single_study"
2. Study Planner      → Creates spec
3. Executor           → Runs OpenMC
4. Analyzer           → Interprets keff
5. Suggester          → Recommends next steps
```

**API Call**:
```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Simulate PWR pin cell with 4.5% enriched UO2 at 900K"
  }'
```

**Response**:
```json
{
  "request_id": "req_a1b2c3d4",
  "status": "queued",
  "estimated_duration_seconds": 15,
  "stream_url": "/api/v1/requests/req_a1b2c3d4/stream"
}
```

---

### Pattern 2: Parameter Sweep
**User Query**: "Compare different enrichments from 3% to 5%"

**Agent Flow**:
```
1. Intent Classifier   → "sweep"
2. Sweep Planner      → Defines parameter range
3. Executor           → Runs multiple simulations
4. Analyzer           → Compares keff trends
5. Suggester          → Optimal enrichment
```

**API Call**:
```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Run enrichment sweep from 3% to 5% in 0.5% steps for PWR fuel"
  }'
```

---

### Pattern 3: Query Historical Data
**User Query**: "What simulations have we run with high-enriched fuel?"

**Agent Flow**:
```
1. Intent Classifier   → "query"
2. Query Executor     → Searches MongoDB
3. Analyzer           → Summarizes findings
4. Suggester          → Related analyses
```

**API Call**:
```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me all PWR simulations with enrichment above 4%"
  }'
```

---

### Pattern 4: Compare Specific Runs
**User Query**: "Compare runs ABC and XYZ"

**Agent Flow**:
```
1. Intent Classifier   → "compare"
2. Compare Executor   → Loads run data
3. Analyzer           → Statistical comparison
4. Suggester          → Which design is better
```

**API Call**:
```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare run_abc123 with run_xyz789"
  }'
```

---

## 🐍 Python Client Examples

### Example 1: Submit and Wait
```python
import requests
import time

# Submit request
response = requests.post(
    "http://localhost:8000/api/v1/requests",
    json={
        "query": "Simulate PWR pin cell with 4.5% enriched UO2",
        "options": {"stream": False}
    }
)

request_id = response.json()["request_id"]
print(f"Request ID: {request_id}")

# Poll for completion
while True:
    status = requests.get(
        f"http://localhost:8000/api/v1/requests/{request_id}"
    ).json()
    
    print(f"Status: {status['status']}")
    
    if status["status"] in ["completed", "failed"]:
        break
    
    time.sleep(2)

# Show results
if status["status"] == "completed":
    print(f"k-eff: {status['results']['results']['keff']}")
    print(f"Analysis: {status['analysis']}")
    print(f"Suggestions: {status['suggestions']}")
```

---

### Example 2: Real-Time Streaming
```python
import sseclient
import requests
import json

response = requests.post(
    "http://localhost:8000/api/v1/requests",
    json={"query": "Run enrichment sweep from 3% to 5%"},
    stream=False
)

request_id = response.json()["request_id"]

# Connect to SSE stream
stream_url = f"http://localhost:8000/api/v1/requests/{request_id}/stream"
messages = sseclient.SSEClient(stream_url)

for msg in messages:
    if msg.event in ['request_start', 'agent_start', 'agent_complete', 'request_complete']:
        data = json.loads(msg.data)
        print(f"[{msg.event}] {data}")
```

---

### Example 3: Automated Experiment Campaign
```python
import requests

class AONPClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def submit_query(self, query):
        """Submit natural language query"""
        response = requests.post(
            f"{self.base_url}/api/v1/requests",
            json={"query": query}
        )
        return response.json()["request_id"]
    
    def wait_for_completion(self, request_id, poll_interval=2):
        """Wait for request to complete"""
        import time
        while True:
            status = self.get_status(request_id)
            if status["status"] in ["completed", "failed"]:
                return status
            time.sleep(poll_interval)
    
    def get_status(self, request_id):
        """Get request status"""
        response = requests.get(
            f"{self.base_url}/api/v1/requests/{request_id}"
        )
        return response.json()
    
    def query_runs(self, **filters):
        """Query simulation runs"""
        response = requests.get(
            f"{self.base_url}/api/v1/runs",
            params=filters
        )
        return response.json()

# Usage
client = AONPClient()

# Run experiment campaign
experiments = [
    "Simulate PWR pin cell at 3.5% enrichment",
    "Simulate PWR pin cell at 4.0% enrichment",
    "Simulate PWR pin cell at 4.5% enrichment",
    "Simulate PWR pin cell at 5.0% enrichment",
]

results = []
for exp in experiments:
    print(f"Running: {exp}")
    request_id = client.submit_query(exp)
    result = client.wait_for_completion(request_id)
    results.append(result)
    print(f"  k-eff: {result['results']['results']['keff']}")

print(f"\nCompleted {len(results)} experiments!")
```

---

## 🔄 Advanced Orchestration Patterns

### Pattern A: Iterative Refinement
```python
client = AONPClient()

# Initial exploration
req1 = client.submit_query("Simulate PWR pin cell at 4.5% enrichment")
result1 = client.wait_for_completion(req1)

keff1 = result1['results']['results']['keff']

# Refine based on results
if keff1 < 1.0:
    req2 = client.submit_query(
        "Run enrichment sweep from 4.5% to 6% to find critical enrichment"
    )
    result2 = client.wait_for_completion(req2)
elif keff1 > 1.2:
    req2 = client.submit_query(
        "Reduce enrichment - try sweep from 3% to 4.5%"
    )
    result2 = client.wait_for_completion(req2)
```

---

### Pattern B: Multi-Parameter Optimization
```python
# Temperature sweep at fixed enrichment
temp_sweep = client.submit_query(
    "Run temperature sweep from 600K to 1200K for 4.5% enriched PWR fuel"
)

# Enrichment sweep at fixed temperature
enr_sweep = client.submit_query(
    "Run enrichment sweep from 3% to 5% at 900K"
)

# Wait for both
temp_result = client.wait_for_completion(temp_sweep)
enr_result = client.wait_for_completion(enr_sweep)

# Analyze combined
compare_req = client.submit_query(
    f"Compare temperature vs enrichment effects on reactivity"
)
```

---

### Pattern C: Design Space Exploration
```python
# Define design space
enrichments = [3.0, 3.5, 4.0, 4.5, 5.0]
temperatures = [600, 750, 900, 1050, 1200]

# Run full factorial
for enr in enrichments:
    for temp in temperatures:
        query = f"Simulate PWR pin cell at {enr}% enrichment and {temp}K"
        request_id = client.submit_query(query)
        print(f"Submitted: {enr}% @ {temp}K → {request_id}")

# Query all results
runs = client.query_runs(
    geometry="PWR",
    enrichment_min=3.0,
    enrichment_max=5.0,
    limit=100
)

print(f"Completed {runs['total']} design points")
```

---

## ⚙️ Configuration

### Enable Real OpenMC Execution
```bash
# In .env file or environment
USE_REAL_OPENMC=true
OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml
```

### Configure Agent Behavior
```python
# In aonp_agents.py (if needed)
llm = ChatFireworks(
    api_key=os.getenv("FIREWORKS"),
    model="your-model-here",
    temperature=0.7  # Adjust creativity
)
```

---

## 📊 Monitoring & Debugging

### Check System Health
```bash
curl http://localhost:8000/api/v1/health
```

### Get Statistics
```bash
curl http://localhost:8000/api/v1/statistics
```

### View Recent Runs
```bash
curl http://localhost:8000/api/v1/runs?limit=10
```

### Compare Runs
```bash
curl -X POST http://localhost:8000/api/v1/runs/compare \
  -H "Content-Type: application/json" \
  -d '{
    "run_ids": ["run_abc123", "run_xyz789"]
  }'
```

---

## 🎯 Example Workflows

### Workflow 1: Quick Test
```bash
# 1. Start server
cd Playground/backend/api && python main.py &

# 2. Submit test query
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{"query": "Test PWR simulation at 4.5% enrichment"}'

# 3. Check status (replace with actual ID)
curl http://localhost:8000/api/v1/requests/req_abc123
```

---

### Workflow 2: Research Campaign
```python
#!/usr/bin/env python3
"""Research campaign: Find optimal enrichment"""

from aonp_client import AONPClient

client = AONPClient()

# Phase 1: Coarse sweep
print("Phase 1: Coarse enrichment sweep...")
coarse = client.submit_query(
    "Run enrichment sweep from 3% to 6% in 1% steps"
)
coarse_result = client.wait_for_completion(coarse)

# Analyze coarse results to find interesting region
# (In production, parse results and find peak)

# Phase 2: Fine sweep around interesting region
print("Phase 2: Fine sweep around 4-5%...")
fine = client.submit_query(
    "Run enrichment sweep from 4% to 5% in 0.1% steps"
)
fine_result = client.wait_for_completion(fine)

# Phase 3: Temperature sensitivity at optimal enrichment
print("Phase 3: Temperature sensitivity...")
temp_sens = client.submit_query(
    "Run temperature sweep at 4.5% enrichment from 600K to 1200K"
)
temp_result = client.wait_for_completion(temp_sens)

print("Campaign complete!")
```

---

### Workflow 3: Automated Analysis
```python
#!/usr/bin/env python3
"""Daily automated analysis of new results"""

import schedule
import time

def daily_analysis():
    client = AONPClient()
    
    # Query today's runs
    runs = client.query_runs(limit=100)
    
    # Submit analysis request
    analysis = client.submit_query(
        f"Analyze the {runs['total']} simulations run today and identify trends"
    )
    
    result = client.wait_for_completion(analysis)
    
    # Email results (or save to report)
    print(result['analysis'])
    print(result['suggestions'])

# Schedule daily at 5 PM
schedule.every().day.at("17:00").do(daily_analysis)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 🚦 Best Practices

### 1. **Use Natural Language**
✅ Good: "Compare PWR and BWR geometries at 4% enrichment"  
❌ Bad: `{"geometry": ["PWR", "BWR"], "enrichment": 4.0}`

### 2. **Let Agents Handle Details**
✅ Good: "Find optimal enrichment for criticality"  
❌ Bad: Manually specify every parameter

### 3. **Leverage History**
✅ Good: "What's the best enrichment we've tested?"  
✅ Good: "Re-run last week's simulation with higher temperature"

### 4. **Iterate Based on Results**
- Start with broad sweeps
- Refine based on agent suggestions
- Let analysis guide next experiments

### 5. **Use Streaming for Long Runs**
```python
# For real OpenMC (can take minutes)
response = requests.post(
    url,
    json={"query": query, "options": {"stream": True}}
)
```

---

## 📚 Quick Reference

### Start Everything
```bash
# Terminal 1: API Server
cd Playground/backend/api
python main.py

# Terminal 2: MongoDB (if local)
mongod --dbpath ./data

# Terminal 3: Test
curl http://localhost:8000/api/v1/health
```

### API Base URL
```
http://localhost:8000
```

### Key Files
- **API**: `Playground/backend/api/main.py`
- **Agents**: `Playground/backend/aonp_agents.py`
- **Tools**: `Playground/backend/agent_tools.py`
- **Adapter**: `Playground/backend/openmc_adapter.py`

### Environment Variables
```bash
MONGO_URI=mongodb+srv://...
FIREWORKS=your_api_key
USE_REAL_OPENMC=true  # or false
OPENMC_CROSS_SECTIONS=/path/to/data
```

---

## 🎉 You're Ready!

**Next Steps**:
1. ✅ Start the API: `python Playground/backend/api/main.py`
2. ✅ Submit a query: Use curl or Python client
3. ✅ Let agents design experiments
4. ✅ Iterate based on results

**The agents will**:
- Understand your natural language queries
- Design appropriate experiments
- Execute simulations (mock or real)
- Analyze results
- Suggest next steps

**You just need to ask questions!** 🚀


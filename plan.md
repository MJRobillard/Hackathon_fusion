# Multi-Agent AONP Orchestration Plan

**Architecture**: LangChain Multi-Agent with Tool Delegation  
**Max 200 lines** | **Practical Implementation**

---

## System Flow

```
User Query → FastAPI → Router Agent → Specialist Agents → Tools → OpenMC/MongoDB
                ↓
         [Studies Agent | Sweep Agent | Query Agent | Analysis Agent]
```

---

## Agent Architecture Table

| Agent | Handles | Responsibilities | Current Tools | Potential Tools |
|-------|---------|------------------|---------------|-----------------|
| **Router** | All requests | • Parse user intent<br>• Route to specialist<br>• Aggregate results | None (pure routing) | • `detect_intent(query)` |
| **Studies Agent** | "Simulate X"<br>"Run study Y"<br>"Create reactor Z" | • Parse reactor specs<br>• Submit single studies<br>• Return keff results | • `submit_study(spec)`<br>• `get_run_by_id(run_id)` | • `validate_physics(spec)`<br>• `estimate_runtime(spec)`<br>• `suggest_particles(geometry)` |
| **Sweep Agent** | "Compare A vs B"<br>"Vary X from Y to Z"<br>"Optimize parameter P" | • Generate param ranges<br>• Submit batch studies<br>• Coordinate parallel runs | • `generate_sweep(base, param, values)`<br>• `compare_runs(run_ids)` | • `parallel_submit(specs)`<br>• `adaptive_sweep(param, target)`<br>• `latin_hypercube_sample(params)` |
| **Query Agent** | "What have we run?"<br>"Show me X results"<br>"Find studies where Y" | • Parse filters<br>• Query MongoDB<br>• Format results | • `query_results(filters, limit)`<br>• `get_study_statistics()` | • `semantic_search(description)`<br>• `find_similar_runs(spec)`<br>• `aggregate_by_param(field)` |
| **Analysis Agent** | "Analyze run X"<br>"Why is keff Y?"<br>"Explain results" | • Interpret physics<br>• Compare to benchmarks<br>• Suggest next steps | • `compare_runs(run_ids)` | • `plot_trends(run_ids)`<br>• `physics_explanation(keff, spec)`<br>• `benchmark_comparison(run_id)` |

---

## API Design

### Core Endpoints

```python
POST   /api/v1/query              # Natural language → Router → Agents
GET    /api/v1/query/{id}         # Check query status
GET    /api/v1/query/{id}/stream  # SSE progress updates

# Direct tool access (bypass agents for speed/cost)
POST   /api/v1/studies            # Direct submit_study()
GET    /api/v1/studies/{id}       # Direct get_run_by_id()
POST   /api/v1/sweeps             # Direct generate_sweep()
GET    /api/v1/runs               # Direct query_results()
POST   /api/v1/runs/compare       # Direct compare_runs()
```

### Request/Response Format

```json
// POST /api/v1/query
{
  "query": "Compare PWR enrichments from 3% to 5%",
  "options": {"stream": false, "timeout": 300}
}

// Response
{
  "query_id": "q_abc123",
  "status": "routing",
  "assigned_agent": "sweep_agent",
  "estimated_duration": 30
}

// GET /api/v1/query/q_abc123
{
  "query_id": "q_abc123",
  "status": "completed",
  "agent_path": ["router", "sweep_agent"],
  "tool_calls": ["generate_sweep", "compare_runs"],
  "results": {
    "run_ids": ["run_1", "run_2", "run_3"],
    "comparison": {...},
    "interpretation": "keff increases with enrichment..."
  },
  "cost": {"llm_tokens": 1200, "openmc_seconds": 18}
}
```

---

## LangChain Implementation Pattern

```python
# Playground/backend/multi_agent_system.py

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate
from langchain_fireworks import ChatFireworks

# 1. Define specialized agents
class StudiesAgent:
    tools = [submit_study, get_run_by_id, validate_physics]
    prompt = "You run single nuclear reactor simulations..."
    
class SweepAgent:
    tools = [generate_sweep, compare_runs, parallel_submit]
    prompt = "You coordinate parameter sweeps..."

class QueryAgent:
    tools = [query_results, get_study_statistics, find_similar_runs]
    prompt = "You search historical simulation data..."

class AnalysisAgent:
    tools = [compare_runs, physics_explanation, benchmark_comparison]
    prompt = "You interpret simulation results..."

# 2. Router orchestrates
class RouterAgent:
    def route_query(self, query: str) -> dict:
        """Classify intent and delegate to specialist"""
        
        intent = self.classify(query)  # LLM call
        
        if "simulate" in query.lower() or "run" in query.lower():
            return {"agent": "studies", "context": self.extract_specs(query)}
            
        elif "compare" in query.lower() or "sweep" in query.lower():
            return {"agent": "sweep", "context": self.extract_params(query)}
            
        elif "show" in query.lower() or "find" in query.lower():
            return {"agent": "query", "context": self.extract_filters(query)}
            
        elif "why" in query.lower() or "explain" in query.lower():
            return {"agent": "analysis", "context": self.extract_run_ids(query)}
        
        else:
            return {"agent": "studies", "context": {}}  # Default
```

---

## Tool Expansion Roadmap

### Phase 1: MVP (Current + 3 new)
```python
# Current (5 tools) ✅
submit_study(spec)
query_results(filters, limit)
generate_sweep(base, param, values)
compare_runs(run_ids)
get_study_statistics()

# Add (3 tools) 🔧
get_run_by_id(run_id)           # Fetch specific run
get_recent_runs(limit)          # Latest N runs
validate_physics(spec)          # Check if spec is physically reasonable
```

### Phase 2: Parallelization (4 new)
```python
parallel_submit(specs)          # Submit multiple studies at once
batch_status(run_ids)           # Check status of multiple runs
cancel_run(run_id)              # Stop running simulation
adaptive_sweep(param, target)   # Smart sweep that narrows based on results
```

### Phase 3: Intelligence (5 new)
```python
find_similar_runs(spec)         # Semantic search for related sims
estimate_runtime(spec)          # Predict how long sim will take
suggest_next_experiments(run_ids) # Recommend follow-up studies
physics_explanation(keff, spec) # Explain why keff is what it is
benchmark_comparison(run_id)    # Compare to known benchmarks
```

---

## Example Query Flows

### Flow 1: Single Study
```
User: "Simulate PWR at 4.5% enrichment"
  ↓
Router: intent=single_study → Studies Agent
  ↓
Studies Agent: 
  1. validate_physics({"geometry": "PWR", "enrichment": 4.5})
  2. submit_study(spec)
  3. get_run_by_id(run_id)
  ↓
Response: {run_id, keff, interpretation}
```

### Flow 2: Parameter Sweep
```
User: "Compare enrichments 3-5%"
  ↓
Router: intent=sweep → Sweep Agent
  ↓
Sweep Agent:
  1. generate_sweep(base_spec, "enrichment_pct", [3.0, 3.5, 4.0, 4.5, 5.0])
  2. compare_runs([run_1, run_2, run_3, run_4, run_5])
  ↓
Response: {run_ids, comparison, trend="keff increases monotonically"}
```

### Flow 3: Historical Query
```
User: "What PWR simulations have we done?"
  ↓
Router: intent=query → Query Agent
  ↓
Query Agent:
  1. query_results({"spec.geometry": "PWR"}, limit=50)
  2. get_study_statistics()
  ↓
Response: {runs, summary="Found 57 PWR simulations..."}
```

### Flow 4: Analysis Request
```
User: "Why is keff so high in run_abc123?"
  ↓
Router: intent=analysis → Analysis Agent
  ↓
Analysis Agent:
  1. get_run_by_id("run_abc123")
  2. physics_explanation(keff=1.43, spec={...})
  3. find_similar_runs(spec)
  ↓
Response: {explanation, similar_runs, recommendations}
```

---

## FastAPI Implementation

```python
# Playground/backend/api/main.py

from fastapi import FastAPI, BackgroundTasks
from multi_agent_system import RouterAgent, StudiesAgent, SweepAgent, QueryAgent, AnalysisAgent

app = FastAPI()
router = RouterAgent()
agents = {
    "studies": StudiesAgent(),
    "sweep": SweepAgent(),
    "query": QueryAgent(),
    "analysis": AnalysisAgent()
}

queries_db = {}  # Use MongoDB in production

@app.post("/api/v1/query")
async def submit_query(query: str, background: BackgroundTasks):
    query_id = f"q_{uuid4().hex[:8]}"
    
    # Route to specialist
    routing = router.route_query(query)
    
    queries_db[query_id] = {
        "status": "routed",
        "query": query,
        "assigned_agent": routing["agent"],
        "context": routing["context"]
    }
    
    # Execute in background
    background.add_task(execute_agent, query_id, routing)
    
    return {"query_id": query_id, "assigned_agent": routing["agent"]}

async def execute_agent(query_id: str, routing: dict):
    try:
        agent_name = routing["agent"]
        agent = agents[agent_name]
        
        queries_db[query_id]["status"] = "running"
        result = agent.execute(routing["context"])
        
        queries_db[query_id].update({
            "status": "completed",
            "results": result
        })
    except Exception as e:
        queries_db[query_id].update({
            "status": "failed",
            "error": str(e)
        })
```

---

## Agent Communication Protocol

Agents can delegate to each other:

```python
# Sweep Agent needs Studies Agent to run individual sims
class SweepAgent:
    def execute(self, context):
        specs = self.generate_specs(context)
        
        # Delegate to Studies Agent for each spec
        run_ids = []
        for spec in specs:
            result = agents["studies"].execute({"spec": spec})
            run_ids.append(result["run_id"])
        
        # Then compare
        return compare_runs(run_ids)
```

---

## Cost & Performance Estimates

| Operation | Agent | Tools | LLM Calls | OpenMC Time | Total | Cost |
|-----------|-------|-------|-----------|-------------|-------|------|
| Single sim | Router → Studies | 2 | 2 | 4s | 6s | $0.02 |
| Sweep (5x) | Router → Sweep | 6 | 2 | 20s | 24s | $0.03 |
| Query history | Router → Query | 1 | 1 | 0s | 2s | $0.01 |
| Analysis | Router → Analysis | 3 | 2 | 0s | 4s | $0.02 |

---

## Next Steps

1. **Implement Router** (2 hours) - Intent classification + delegation
2. **Implement 4 Specialist Agents** (4 hours) - Each with 2-3 tools
3. **Add 3 missing tools** (2 hours) - get_run_by_id, validate_physics, etc
4. **Wire up FastAPI** (2 hours) - Async execution + status tracking
5. **Test end-to-end** (2 hours) - All 4 flow patterns

**Total**: ~12 hours to full multi-agent system
## Deployment Architecture

### Where Everything Runs

```
┌─────────────────────────────────────────────────────────────┐
│ LOCAL DEVELOPMENT (Your Machine)                            │
│                                                              │
│  Terminal 1: FastAPI Server                                 │
│  └─ python Playground/backend/api/main.py                   │
│     └─ Agents (in-process)                                  │
│        └─ Tools (in-process)                                │
│           └─ OpenMC (subprocess, local nuclear data)        │
│                                                              │
│  Terminal 2: MongoDB (or Atlas remote)                      │
│  Terminal 3: Testing                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PRODUCTION (Cloud Deployment)                               │
│                                                              │
│  [Frontend] ──HTTP──> [Load Balancer]                       │
│                            │                                 │
│                            ▼                                 │
│               ┌──────────────────────────┐                  │
│               │   FastAPI Servers (2-4x) │                  │
│               │   (Agents run in-process)│                  │
│               └────────────┬─────────────┘                  │
│                            │                                 │
│         ┌──────────────────┼──────────────────┐            │
│         ▼                  ▼                  ▼             │
│    [Job Queue]       [OpenMC API]      [MongoDB Atlas]      │
│    Redis/Celery      GPU Cluster       Shared DB            │
│                      (if needed)                             │
└─────────────────────────────────────────────────────────────┘
```

---

## OpenMC Execution Modes

### Mode 1: Local (Development) ✅ Current
**Where**: Same process as FastAPI  
**When**: Development, testing, small studies  
**How**: Direct Python API calls

```python
# agent_tools.py (line 116-238)
def real_openmc_execution(spec, run_id):
    import openmc
    temp_dir = tempfile.mkdtemp()
    # ... build model ...
    openmc.run()  # Blocks for 3-6 seconds
    return {"keff": ..., "keff_std": ...}
```

**Pros**: Simple, no networking, fast for single jobs  
**Cons**: Blocks API thread, doesn't scale, CPU-bound

---

### Mode 2: Job Queue (Production) 🎯 Recommended
**Where**: Separate worker processes  
**When**: Production, concurrent requests  
**How**: Celery + Redis

```python
# Playground/backend/workers/openmc_worker.py
from celery import Celery

app = Celery('openmc_tasks', broker='redis://localhost:6379')

@app.task(bind=True)
def run_openmc_async(self, spec, run_id):
    """Execute OpenMC in separate worker process"""
    return real_openmc_execution(spec, run_id)

# In agent_tools.py
def submit_study(spec):
    run_id = f"run_{uuid4().hex[:8]}"
    
    # Queue job instead of blocking
    task = run_openmc_async.delay(spec.dict(), run_id)
    
    # Store task_id for status checking
    runs_col.insert_one({
        "run_id": run_id,
        "task_id": task.id,
        "status": "queued"
    })
    
    return {"run_id": run_id, "status": "queued"}
```

**Start workers**:
```bash
# Terminal 1: API server
python Playground/backend/api/main.py

# Terminal 2: Celery workers (3x for parallel execution)
celery -A Playground.backend.workers.openmc_worker worker --concurrency=3

# Terminal 3: Redis
redis-server
```

---

### Mode 3: OpenMC Microservice API (Future)
**Where**: Dedicated OpenMC server(s)  
**When**: Heavy workloads, GPU acceleration  
**How**: Separate HTTP API

```python
# Playground/backend/openmc_service/main.py
from fastapi import FastAPI

app = FastAPI()

@app.post("/openmc/run")
async def run_simulation(spec: dict):
    """Dedicated OpenMC execution service"""
    run_id = f"run_{uuid4().hex[:8]}"
    result = real_openmc_execution(spec, run_id)
    return result

# Start on dedicated port
# uvicorn openmc_service.main:app --port 8001

# In agent_tools.py
def submit_study(spec):
    response = requests.post(
        "http://openmc-service:8001/openmc/run",
        json=spec.dict()
    )
    return response.json()
```

**When to use**:
- Need GPU-accelerated OpenMC builds
- Want to scale OpenMC workers independently
- Running on compute cluster (SLURM, HPC)

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test-agents.yml
name: Test Multi-Agent System

on: [push, pull_request]

jobs:
  test-agents:
    runs-on: ubuntu-latest
    
    services:
      mongodb:
        image: mongo:7
        ports:
          - 27017:27017
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install OpenMC
        run: |
          conda install -c conda-forge openmc
          # Or: pip install openmc
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Download nuclear data (small test library)
        run: |
          wget https://anl.box.com/shared/static/xxx.h5
          export OPENMC_CROSS_SECTIONS=$PWD/cross_sections.xml
      
      - name: Run agent tests (mock mode)
        env:
          MONGO_URI: mongodb://localhost:27017
          USE_REAL_OPENMC: false
        run: |
          pytest tests/test_agents.py -v
      
      - name: Run full integration test (real OpenMC)
        env:
          MONGO_URI: mongodb://localhost:27017
          USE_REAL_OPENMC: true
          OPENMC_CROSS_SECTIONS: ${{ github.workspace }}/cross_sections.xml
        run: |
          python Playground/backend/agent_tools.py
          # Should complete successfully with 5 sweeps
      
      - name: Test API endpoints
        run: |
          # Start server in background
          python Playground/backend/api/main.py &
          sleep 5
          
          # Test query endpoint
          curl -X POST http://localhost:8000/api/v1/query \
            -H "Content-Type: application/json" \
            -d '{"query": "Simulate PWR at 4.5%"}'
          
          # Check results
          pytest tests/test_api.py -v
```

---

### Docker Compose (Local Development)

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MONGO_URI=mongodb://mongo:27017
      - REDIS_URL=redis://redis:6379
      - USE_REAL_OPENMC=true
      - OPENMC_CROSS_SECTIONS=/app/nuclear_data/cross_sections.xml
    volumes:
      - ./Playground:/app/Playground
      - ./nuclear_data:/app/nuclear_data
    depends_on:
      - mongo
      - redis
  
  worker:
    build: .
    command: celery -A Playground.backend.workers.openmc_worker worker --concurrency=3
    environment:
      - MONGO_URI=mongodb://mongo:27017
      - REDIS_URL=redis://redis:6379
      - OPENMC_CROSS_SECTIONS=/app/nuclear_data/cross_sections.xml
    volumes:
      - ./nuclear_data:/app/nuclear_data
    depends_on:
      - redis
      - mongo
  
  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
  
  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  mongo_data:
```

**Usage**:
```bash
# Start everything
docker-compose up

# Scale workers
docker-compose up --scale worker=5

# Run tests
docker-compose run api pytest tests/
```

---

## Execution Environment Variables

```bash
# .env file
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/aonp
FIREWORKS_API_KEY=your_key_here

# OpenMC execution mode
USE_REAL_OPENMC=true              # false = mock, true = real
OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml

# Job queue (if using Celery)
REDIS_URL=redis://localhost:6379
CELERY_CONCURRENCY=3              # Number of parallel OpenMC workers

# OpenMC service (if using microservice mode)
OPENMC_SERVICE_URL=http://openmc-cluster:8001

# Performance tuning
OPENMC_DEFAULT_PARTICLES=10000
OPENMC_DEFAULT_BATCHES=50
OPENMC_MAX_RUNTIME=300            # seconds, kill if exceeds
```

---

## Recommended Deployment

### Development
```bash
# Single machine, local OpenMC
cd Playground/backend
python api/main.py
```

### Staging/Testing
```bash
# Docker Compose with 3 workers
docker-compose up --scale worker=3
```

### Production
```bash
# Kubernetes cluster
kubectl apply -f k8s/api-deployment.yaml       # 4 replicas
kubectl apply -f k8s/worker-deployment.yaml    # 10 replicas
kubectl apply -f k8s/openmc-service.yaml       # GPU nodes
```

---

## Next Steps

1. **Implement Router** (2 hours) - Intent classification + delegation
2. **Implement 4 Specialist Agents** (4 hours) - Each with 2-3 tools
3. **Add 3 missing tools** (2 hours) - get_run_by_id, validate_physics, etc
4. **Wire up FastAPI** (2 hours) - Async execution + status tracking
5. **Add Celery workers** (2 hours) - Job queue for OpenMC
6. **Test end-to-end** (2 hours) - All 4 flow patterns + CI

**Total**: ~14 hours to full production-ready multi-agent system

# AONP Multi-Agent API Server

**Fast, production-ready API for nuclear reactor simulations with AI agents**

---

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Install dependencies
pip install fastapi uvicorn motor pymongo python-dotenv langchain langchain-fireworks

# Set environment variables
export MONGO_URI="mongodb://localhost:27017"  # Required
export FIREWORKS="your_api_key_here"          # Optional (for LLM routing)
```

### 2. Start the Server

**Option A: Using startup script (recommended)**
```bash
cd Playground/backend
chmod +x start_api.sh
./start_api.sh
```

**Option B: Direct Python**
```bash
cd Playground/backend/api
python main_v2.py
```

**Option C: Using uvicorn**
```bash
cd Playground/backend/api
uvicorn main_v2:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Test the API

```bash
# Test without starting server (unit tests)
cd Playground/backend
python test_api_quick.py

# Test live API (requires server running)
chmod +x test_api_live.sh
./test_api_live.sh

# Or use pytest
python -m pytest tests/test_multi_agent_system.py -v
```

### 4. Access Documentation

- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

---

## 📡 API Architecture

```
User Request (Natural Language)
       ↓
   Router Agent ──────→ Intent Classification
       ↓                (keyword or LLM-based)
       ↓
   ┌───┴──────────────────────┐
   ↓          ↓        ↓       ↓
Studies    Sweep    Query   Analysis
Agent      Agent    Agent    Agent
   ↓          ↓        ↓       ↓
   └──────────┴────────┴───────┘
              ↓
        Agent Tools
       (8 functions)
              ↓
      OpenMC + MongoDB
```

---

## 🎯 Core Features

### ✅ What Works Now

1. **Natural Language Interface**
   - Submit queries in plain English
   - Automatic intent classification
   - Async processing with progress tracking

2. **Four Specialist Agents**
   - **Studies Agent**: Single simulations
   - **Sweep Agent**: Parameter sweeps
   - **Query Agent**: Database searches
   - **Analysis Agent**: Result comparisons

3. **Two Routing Modes**
   - **Keyword** (default): 10ms, no API key, 85% accuracy
   - **LLM**: 2-5s, requires API key, 95% accuracy

4. **Direct Tool Access**
   - Bypass agents for maximum speed
   - Direct study submission
   - Direct sweep execution
   - Database queries

5. **Real-time Progress**
   - Server-Sent Events (SSE)
   - Query status polling
   - Background task execution

6. **Frontend-Ready**
   - CORS enabled for localhost:3000, localhost:5173
   - RESTful design
   - Comprehensive error handling

---

## 🔧 Configuration

### Environment Variables

```bash
# Required
MONGO_URI="mongodb://localhost:27017"

# Optional
FIREWORKS="your_api_key"                    # For LLM routing (optional)
API_HOST="0.0.0.0"                          # Default: 0.0.0.0
API_PORT="8000"                             # Default: 8000
CORS_ORIGINS="http://localhost:3000,..."    # Comma-separated list
USE_REAL_OPENMC="false"                     # true for real OpenMC, false for mock
```

### .env File (Recommended)

Create `Playground/backend/.env`:

```bash
MONGO_URI=mongodb://localhost:27017
FIREWORKS=fw_xxxxxxxxxxxxx
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
USE_REAL_OPENMC=false
```

---

## 📝 API Endpoints Summary

### Main Interface
- `POST /api/v1/query` - Submit natural language query
- `GET /api/v1/query/{query_id}` - Get query status
- `GET /api/v1/query/{query_id}/stream` - Stream progress (SSE)

### Agent Endpoints
- `POST /api/v1/agents/studies` - Run Studies Agent
- `POST /api/v1/agents/sweep` - Run Sweep Agent
- `POST /api/v1/agents/query` - Run Query Agent
- `POST /api/v1/agents/analysis` - Run Analysis Agent
- `POST /api/v1/router` - Test routing only

### Direct Tools
- `POST /api/v1/studies` - Submit study directly
- `GET /api/v1/studies/{run_id}` - Get study by ID
- `POST /api/v1/sweeps` - Submit sweep directly
- `GET /api/v1/runs` - Query runs with filters
- `POST /api/v1/runs/compare` - Compare runs

### Utilities
- `GET /api/v1/health` - Health check
- `GET /api/v1/statistics` - Database statistics

**Full documentation**: See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

---

## 🧪 Testing

### Unit Tests (No Server Required)

```bash
# Test multi-agent system
python test_api_quick.py

# Test with pytest
python -m pytest tests/test_multi_agent_system.py -v

# Test agent tools
python -m pytest tests/test_agent_tools.py -v
```

### Integration Tests (Server Required)

```bash
# Start server in one terminal
./start_api.sh

# In another terminal, run live tests
./test_api_live.sh
```

### Example curl Commands

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Submit query (fast keyword routing)
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Simulate PWR at 4.5% enrichment", "use_llm": false}'

# Get query status
curl http://localhost:8000/api/v1/query/q_abc12345

# Submit direct study
curl -X POST http://localhost:8000/api/v1/studies \
  -H "Content-Type: application/json" \
  -d '{
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Zircaloy", "Water"],
    "enrichment_pct": 4.5,
    "temperature_K": 600
  }'

# Query runs
curl "http://localhost:8000/api/v1/runs?geometry=PWR&keff_min=1.0&limit=10"
```

---

## 🎨 Frontend Integration

### React Example

```javascript
// Submit query
const response = await fetch('http://localhost:8000/api/v1/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'Simulate PWR at 4.5% enrichment',
    use_llm: false  // Fast keyword routing
  })
});

const { query_id } = await response.json();

// Poll for results
const checkStatus = async () => {
  const res = await fetch(`http://localhost:8000/api/v1/query/${query_id}`);
  const data = await res.json();
  
  if (data.status === 'completed') {
    console.log('k-eff:', data.results.keff);
  } else if (data.status === 'processing') {
    setTimeout(checkStatus, 1000);
  }
};

checkStatus();
```

### SSE (Real-time Updates)

```javascript
const eventSource = new EventSource(
  `http://localhost:8000/api/v1/query/${query_id}/stream`
);

eventSource.addEventListener('query_complete', (e) => {
  const data = JSON.parse(e.data);
  console.log('Completed!', data);
  eventSource.close();
});
```

**Full examples**: See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md#frontend-integration-examples)

---

## 🚦 Performance

### Routing Speed

| Mode | Speed | API Key Required | Accuracy |
|------|-------|------------------|----------|
| Keyword | ~10ms | No | ~85% |
| LLM | ~2-5s | Yes (FIREWORKS) | ~95% |

**Recommendation**: Use keyword routing (default) for production. It's fast enough and accurate enough for most queries.

### Simulation Speed

| Mode | Particles | Batches | Time |
|------|-----------|---------|------|
| Mock | Any | Any | ~50ms |
| Real OpenMC | 10,000 | 50 | ~10-30s |
| Real OpenMC | 100,000 | 100 | ~5-10min |

### Caching

Identical simulations (same spec_hash) return instantly from cache.

---

## 🔒 Production Deployment

### Security Checklist

- [ ] Add authentication (JWT, API keys, etc.)
- [ ] Enable HTTPS (use nginx/traefik reverse proxy)
- [ ] Add rate limiting (slowapi, nginx)
- [ ] Configure CORS properly for production domains
- [ ] Use production MongoDB with auth enabled
- [ ] Set strong `SECRET_KEY` for sessions
- [ ] Enable request logging and monitoring
- [ ] Add input validation and sanitization
- [ ] Configure firewall rules
- [ ] Use environment secrets management (not .env in production)

### Production Server

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn + uvicorn workers
gunicorn main_v2:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --log-level info \
  --access-logfile - \
  --error-logfile -
```

### Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main_v2:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📊 Monitoring

### Health Check

```bash
# Check if service is healthy
curl http://localhost:8000/api/v1/health

# Response shows:
# - mongodb: connected/disconnected
# - fireworks_api: available/missing_key
# - openmc: ready
# - overall status: healthy/degraded/unhealthy
```

### Statistics

```bash
# Get database statistics
curl http://localhost:8000/api/v1/statistics

# Returns:
# - total_studies
# - total_runs
# - completed_runs
# - total_queries
# - recent_runs (last 5)
```

---

## 🐛 Troubleshooting

### Common Issues

**Issue**: "MONGO_URI not found"
- **Solution**: Set `MONGO_URI` environment variable or create `.env` file

**Issue**: "LLM routing fails"
- **Solution**: Either set `FIREWORKS` key or use keyword routing (`use_llm: false`)

**Issue**: "CORS errors in frontend"
- **Solution**: Add your frontend URL to `CORS_ORIGINS` env var

**Issue**: "Slow responses"
- **Solution**: Use keyword routing (`use_llm: false`) and mock OpenMC (`USE_REAL_OPENMC=false`)

**Issue**: "Tests fail"
- **Solution**: Make sure MongoDB is running and accessible

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=debug

# Run with verbose output
python api/main_v2.py
```

---

## 📚 Documentation

- **API Reference**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - Complete endpoint docs
- **Multi-Agent System**: [README_MULTI_AGENT.md](./README_MULTI_AGENT.md) - System architecture
- **Test Fixes**: [FIXES_APPLIED.md](./FIXES_APPLIED.md) - Recent improvements
- **Agent Tools**: [agent_tools.py](./agent_tools.py) - Tool implementations
- **API Server**: [api/main_v2.py](./api/main_v2.py) - Server code

---

## 🛣️ Roadmap

### Phase 1 (MVP) - ✅ COMPLETE
- [x] Router Agent with keyword routing
- [x] 4 Specialist Agents (Studies, Sweep, Query, Analysis)
- [x] 8 Agent Tools
- [x] FastAPI server with async support
- [x] Natural language interface
- [x] Direct tool access
- [x] SSE for progress tracking
- [x] CORS for frontend
- [x] Comprehensive tests

### Phase 2 (Enhancements)
- [ ] WebSocket support for real-time updates
- [ ] Authentication & authorization
- [ ] User sessions and history
- [ ] Advanced query optimization
- [ ] Result caching layer
- [ ] Batch processing
- [ ] Export to various formats (CSV, JSON, HDF5)

### Phase 3 (Advanced Features)
- [ ] Multi-user support
- [ ] Collaboration features
- [ ] Visualization generation
- [ ] Advanced analytics
- [ ] Machine learning integration
- [ ] Automatic report generation

---

## 📄 License

Part of the AONP (AI for OpenMC Nuclear Physics) Hackathon project.

---

## 🤝 Contributing

This is a hackathon project. For improvements:

1. Test your changes: `python test_api_quick.py`
2. Update documentation if adding features
3. Follow existing code style
4. Add tests for new functionality

---

## 📞 Support

- **API Docs**: http://localhost:8000/docs
- **Debug Script**: `python debug_router.py`
- **Test Script**: `python test_api_quick.py`
- **Live Tests**: `./test_api_live.sh`

---

**Ready to integrate with frontend!** 🚀

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for complete frontend integration guide.


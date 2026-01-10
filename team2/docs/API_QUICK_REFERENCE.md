# AONP API Quick Reference

**Quick Links**: [Full Design Doc](API_DESIGN_DOCUMENT.md) | [Implementation Sample](api/main.py)

---

## Quick Start

### 1. Start API Server
```bash
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Test Basic Endpoint
```bash
curl http://localhost:8000/api/v1/health
```

### 3. Submit a Request
```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Simulate PWR pin with 4.5% enriched UO2 at 600K"
  }'
```

---

## Essential Endpoints

### Requests
```
POST   /api/v1/requests              Create new simulation request
GET    /api/v1/requests/{id}         Get request status
GET    /api/v1/requests/{id}/stream  Stream agent progress (SSE)
DELETE /api/v1/requests/{id}         Cancel request
```

### Runs
```
GET    /api/v1/runs                  Query simulation runs
GET    /api/v1/runs/{id}             Get run details
POST   /api/v1/runs/compare          Compare multiple runs
```

### Sweeps
```
POST   /api/v1/sweeps                Create parameter sweep
GET    /api/v1/sweeps/{id}           Get sweep status/results
```

### System
```
GET    /api/v1/health                Health check
GET    /api/v1/statistics            System statistics
```

---

## Common Request Bodies

### Create Request
```json
{
  "query": "Simulate PWR pin with 4.5% enriched UO2",
  "options": {
    "stream": true,
    "priority": "normal"
  }
}
```

### Create Sweep
```json
{
  "base_spec": {
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Zircaloy", "Water"],
    "temperature_K": 600,
    "particles": 10000,
    "batches": 50
  },
  "sweep_parameter": "enrichment_pct",
  "sweep_values": [3.0, 3.5, 4.0, 4.5, 5.0]
}
```

### Compare Runs
```json
{
  "run_ids": ["run_abc123", "run_def456", "run_ghi789"]
}
```

---

## Response Examples

### Request Created (202)
```json
{
  "request_id": "req_a3f7c8b2",
  "status": "queued",
  "created_at": "2026-01-10T14:23:45Z",
  "estimated_duration_seconds": 15,
  "stream_url": "/api/v1/requests/req_a3f7c8b2/stream"
}
```

### Request Status (200)
```json
{
  "request_id": "req_a3f7c8b2",
  "status": "completed",
  "intent": "single_study",
  "results": {
    "run_ids": ["run_f7a2c1e3"],
    "keff": 1.28734,
    "keff_std": 0.00028
  },
  "analysis": "The keff value indicates a supercritical system...",
  "suggestions": ["Vary temperature...", "Add control rods..."]
}
```

### Error (400)
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid study specification",
    "details": {"field": "enrichment_pct", "issue": "Must be 0-100"},
    "timestamp": "2026-01-10T14:23:45Z"
  }
}
```

---

## Frontend Integration

### JavaScript Fetch
```javascript
async function createRequest(query) {
  const response = await fetch('http://localhost:8000/api/v1/requests', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query})
  });
  return await response.json();
}
```

### Server-Sent Events
```javascript
function streamProgress(requestId) {
  const eventSource = new EventSource(
    `http://localhost:8000/api/v1/requests/${requestId}/stream`
  );
  
  eventSource.addEventListener('agent_start', (e) => {
    const {agent} = JSON.parse(e.data);
    console.log(`${agent} started`);
  });
  
  eventSource.addEventListener('request_complete', (e) => {
    console.log('Request completed');
    eventSource.close();
  });
  
  return eventSource;
}
```

### React Hook
```javascript
import { useState, useEffect } from 'react';

function useAONPRequest(query) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    if (!query) return;
    
    setLoading(true);
    fetch('http://localhost:8000/api/v1/requests', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query})
    })
      .then(res => res.json())
      .then(data => {
        setStatus(data);
        // Start polling or SSE here
      })
      .catch(err => setError(err))
      .finally(() => setLoading(false));
  }, [query]);
  
  return {status, loading, error};
}
```

---

## Testing Commands

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### Create Request (Simple)
```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{"query": "Simulate PWR pin with 4.5% enriched UO2"}'
```

### Get Request Status
```bash
REQUEST_ID="req_a3f7c8b2"
curl http://localhost:8000/api/v1/requests/$REQUEST_ID
```

### Stream with curl
```bash
curl -N http://localhost:8000/api/v1/requests/req_a3f7c8b2/stream
```

### Query Runs
```bash
curl "http://localhost:8000/api/v1/runs?geometry=PWR&limit=5"
```

### Compare Runs
```bash
curl -X POST http://localhost:8000/api/v1/runs/compare \
  -H "Content-Type: application/json" \
  -d '{
    "run_ids": ["run_abc123", "run_def456"]
  }'
```

### Create Sweep
```bash
curl -X POST http://localhost:8000/api/v1/sweeps \
  -H "Content-Type: application/json" \
  -d '{
    "base_spec": {
      "geometry": "PWR pin cell",
      "materials": ["UO2", "Zircaloy", "Water"],
      "temperature_K": 600,
      "particles": 10000,
      "batches": 50
    },
    "sweep_parameter": "enrichment_pct",
    "sweep_values": [3.0, 4.0, 5.0]
  }'
```

---

## Error Codes

| Code | HTTP | Meaning | Action |
|------|------|---------|--------|
| `VALIDATION_ERROR` | 400 | Bad request data | Check request format |
| `NOT_FOUND` | 404 | Resource missing | Verify ID is correct |
| `AGENT_FAILED` | 500 | Agent error | Check logs, retry |
| `LLM_ERROR` | 502 | Fireworks API issue | Check API key |
| `DATABASE_ERROR` | 503 | MongoDB down | Check connection |
| `TIMEOUT` | 504 | Request too slow | Increase timeout |
| `RATE_LIMIT` | 429 | Too many requests | Wait and retry |

---

## Environment Setup

### .env File
```bash
# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/aonp

# API Keys
FIREWORKS_API_KEY=your_fireworks_key
VOYAGE_API_KEY=your_voyage_key

# Server
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# CORS (frontend URLs)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Install Dependencies
```bash
pip install fastapi uvicorn motor pymongo pydantic python-dotenv slowapi
```

---

## Development Workflow

### 1. Start MongoDB (if local)
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 2. Start API Server
```bash
cd api
uvicorn main:app --reload
```

### 3. View Auto-Generated Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

### 4. Run Tests
```bash
pytest tests/
```

### 5. Load Testing
```bash
locust -f tests/locustfile.py --host=http://localhost:8000
```

---

## Troubleshooting

### API won't start
```bash
# Check if port is in use
netstat -an | grep 8000

# Try different port
uvicorn main:app --port 8001
```

### MongoDB connection fails
```bash
# Test connection string
python -c "from pymongo import MongoClient; client = MongoClient('your_uri'); print(client.server_info())"
```

### CORS errors in browser
- Check `CORS_ORIGINS` in .env matches your frontend URL
- Ensure `http://` or `https://` prefix is correct
- Try adding `*` temporarily for debugging (not for production!)

### SSE not working
- Check browser dev tools → Network → EventStream
- Ensure no proxy/load balancer is buffering responses
- Add `X-Accel-Buffering: no` header

---

## Performance Tips

1. **Connection Pooling**: MongoDB connection pool configured in `db_service.py`
2. **Async All The Way**: Use `async def` for all I/O operations
3. **Caching**: Add Redis for frequently accessed runs
4. **Pagination**: Always use `limit` and `offset` for queries
5. **Indexes**: Ensure MongoDB indexes on `spec_hash`, `run_id`, `created_at`

---

## Security Checklist

- [ ] CORS origins restricted to known frontend URLs
- [ ] Rate limiting enabled (10 req/min for MVP)
- [ ] Input validation via Pydantic models
- [ ] Request size limits (max 1MB)
- [ ] Error messages don't leak sensitive info
- [ ] MongoDB connection uses authentication
- [ ] API keys stored in environment variables (not code)
- [ ] HTTPS in production (not HTTP)

---

## Monitoring

### Health Check
```bash
# Simple availability check
curl http://localhost:8000/api/v1/health
```

### Response Time
```bash
# Measure latency
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/v1/health

# curl-format.txt:
time_total: %{time_total}s
```

### Logs
```bash
# Follow logs
tail -f logs/api.log

# Search for errors
grep ERROR logs/api.log
```

---

## Next Steps

1. Review [API_DESIGN_DOCUMENT.md](API_DESIGN_DOCUMENT.md) for full specification
2. Check [api/main.py](api/main.py) for implementation starter
3. Set up MongoDB Atlas connection
4. Configure environment variables
5. Start building frontend integration

---

**Last Updated**: 2026-01-10  
**Version**: 1.0


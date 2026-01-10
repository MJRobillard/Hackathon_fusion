# AONP Multi-Agent API

FastAPI server for the AONP nuclear simulation multi-agent system.

## Quick Start

### 1. Install Dependencies

```bash
cd api
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in the project root (one level up from `api/`):

```bash
# MongoDB
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/aonp

# API Keys
FIREWORKS=your_fireworks_api_key
VOYAGE=your_voyage_api_key

# Server (optional)
API_HOST=0.0.0.0
API_PORT=8000

# CORS (frontend URLs, comma-separated)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 3. Start Server

```bash
cd api
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. View Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## API Endpoints

### Requests

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/requests` | Submit new simulation request |
| GET | `/api/v1/requests/{id}` | Get request status |
| GET | `/api/v1/requests/{id}/stream` | Stream agent progress (SSE) |

### Runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/runs` | Query simulation runs |
| GET | `/api/v1/runs/{id}` | Get run details |
| POST | `/api/v1/runs/compare` | Compare multiple runs |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/statistics` | System statistics |

---

## Usage Examples

### Submit Request

```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Simulate PWR pin with 4.5% enriched UO2 at 600K"
  }'
```

Response:
```json
{
  "request_id": "req_a3f7c8b2",
  "status": "queued",
  "created_at": "2026-01-10T14:23:45Z",
  "estimated_duration_seconds": 15
}
```

### Get Request Status

```bash
curl http://localhost:8000/api/v1/requests/req_a3f7c8b2
```

### Stream Progress (SSE)

```bash
curl -N http://localhost:8000/api/v1/requests/req_a3f7c8b2/stream
```

### Query Runs

```bash
curl "http://localhost:8000/api/v1/runs?geometry=PWR&limit=10"
```

### Compare Runs

```bash
curl -X POST http://localhost:8000/api/v1/runs/compare \
  -H "Content-Type: application/json" \
  -d '{
    "run_ids": ["run_abc123", "run_def456"]
  }'
```

---

## Frontend Integration

### JavaScript Fetch

```javascript
async function submitRequest(query) {
  const response = await fetch('http://localhost:8000/api/v1/requests', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query})
  });
  return await response.json();
}

// Usage
const result = await submitRequest('Simulate PWR pin with 4.5% enriched UO2');
console.log('Request ID:', result.request_id);
```

### Server-Sent Events

```javascript
function streamProgress(requestId) {
  const eventSource = new EventSource(
    `http://localhost:8000/api/v1/requests/${requestId}/stream`
  );
  
  eventSource.addEventListener('agent_start', (e) => {
    const data = JSON.parse(e.data);
    console.log(`Agent ${data.agent} started`);
  });
  
  eventSource.addEventListener('request_complete', (e) => {
    console.log('Completed!');
    eventSource.close();
  });
  
  eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    eventSource.close();
  };
  
  return eventSource;
}

// Usage
const es = streamProgress('req_a3f7c8b2');
```

### React Hook

```javascript
import { useState, useEffect } from 'react';

function useAONPRequest(query) {
  const [data, setData] = useState(null);
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
      .then(result => {
        setData(result);
        // Poll for completion or use SSE
        const interval = setInterval(async () => {
          const status = await fetch(
            `http://localhost:8000/api/v1/requests/${result.request_id}`
          ).then(r => r.json());
          
          if (status.status === 'completed' || status.status === 'failed') {
            setData(status);
            setLoading(false);
            clearInterval(interval);
          }
        }, 2000);
      })
      .catch(err => {
        setError(err);
        setLoading(false);
      });
  }, [query]);
  
  return { data, loading, error };
}

// Usage in component
function SimulationForm() {
  const [query, setQuery] = useState('');
  const { data, loading, error } = useAONPRequest(query);
  
  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Enter simulation request"
      />
      {loading && <p>Processing...</p>}
      {data?.results && <pre>{JSON.stringify(data.results, null, 2)}</pre>}
      {error && <p>Error: {error.message}</p>}
    </div>
  );
}
```

---

## Architecture

```
api/
├── main.py                    # FastAPI application
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── tests/
    ├── test_requests.py       # Request endpoint tests
    ├── test_runs.py           # Run endpoint tests
    └── test_integration.py    # End-to-end tests
```

### Key Components

1. **FastAPI App**: Main application with route definitions
2. **Event Bus**: Pub/sub system for SSE streaming
3. **Database**: Motor (async MongoDB driver) for database access
4. **Agent Integration**: Calls existing `aonp_agents.py` workflow
5. **Background Tasks**: Async execution of agent workflows

---

## Testing

### Run Tests

```bash
pytest tests/
```

### Manual Testing

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Statistics
curl http://localhost:8000/api/v1/statistics

# Submit test request
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{"query": "test simulation"}'
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Mac/Linux

# Use different port
uvicorn main:app --port 8001
```

### MongoDB Connection Failed

```bash
# Test connection
python -c "from pymongo import MongoClient; client = MongoClient('your_uri'); print(client.server_info())"

# Check .env file exists in parent directory
ls ../.env
```

### CORS Errors

- Ensure `CORS_ORIGINS` in `.env` includes your frontend URL
- Check browser console for exact error
- Temporarily set to `*` for debugging (not for production!)

### SSE Not Working

- Check browser Network tab → EventStream
- Ensure no proxy is buffering responses
- Test with curl: `curl -N http://localhost:8000/api/v1/requests/{id}/stream`

---

## Development

### Code Structure

```python
# main.py structure
# 1. Imports
# 2. Configuration
# 3. Pydantic Models
# 4. Event Bus
# 5. Database Connection
# 6. FastAPI App
# 7. Error Handlers
# 8. Agent Execution
# 9. Routes (Requests, Runs, Statistics)
# 10. Main
```

### Adding New Endpoints

1. Define Pydantic models for request/response
2. Create route function with appropriate decorator
3. Add to relevant router group
4. Update OpenAPI docs (automatic with FastAPI)
5. Write tests

Example:
```python
@app.get("/api/v1/custom", response_model=CustomResponse)
async def custom_endpoint(mongodb = Depends(get_database)):
    """Custom endpoint description"""
    # Implementation
    return CustomResponse(...)
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

@app.post("/api/v1/requests")
async def create_request(...):
    logger.info(f"Creating request: {body.query}")
    # ...
```

---

## Production Deployment

### Environment Variables

Set these in your production environment:

```bash
MONGO_URI=mongodb+srv://...
FIREWORKS=...
VOYAGE=...
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://yourdomain.com
```

### Run with Gunicorn

```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t aonp-api .
docker run -p 8000:8000 --env-file .env aonp-api
```

### Azure App Service

1. Create App Service (Python 3.13)
2. Set environment variables in Configuration
3. Deploy via GitHub Actions or Azure CLI

```bash
az webapp up --name aonp-api --resource-group mygroup --runtime "PYTHON:3.13"
```

---

## Performance

### Optimization Tips

1. **Connection Pooling**: Already configured for MongoDB
2. **Async Operations**: Use `async def` for all I/O
3. **Caching**: Add Redis for frequently accessed data
4. **Rate Limiting**: Configured via `slowapi`
5. **Pagination**: Always use `limit` and `offset`

### Monitoring

Add Prometheus metrics:

```python
from prometheus_client import Counter, Histogram

request_count = Counter('aonp_requests_total', 'Total requests')
request_duration = Histogram('aonp_request_duration_seconds', 'Request duration')

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    with request_duration.time():
        response = await call_next(request)
    request_count.inc()
    return response
```

---

## Security

### Current (MVP)

- CORS restricted to configured origins
- Input validation via Pydantic
- Basic rate limiting
- No authentication (single-user)

### Production Additions

- JWT authentication
- API key management
- Request signing
- HTTPS only
- Secrets management (Azure Key Vault)

---

## Documentation

- **Full Design**: [../API_DESIGN_DOCUMENT.md](../API_DESIGN_DOCUMENT.md)
- **Quick Reference**: [../API_QUICK_REFERENCE.md](../API_QUICK_REFERENCE.md)
- **OpenAPI**: http://localhost:8000/openapi.json

---

## Support

For issues:
1. Check logs: `logs/api.log`
2. Test health endpoint: `/api/v1/health`
3. Review MongoDB connection
4. Check environment variables

---

**Last Updated**: 2026-01-10  
**Version**: 1.0.0


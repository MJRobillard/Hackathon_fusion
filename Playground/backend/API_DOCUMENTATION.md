# AONP Multi-Agent API - Frontend Integration Guide

**Version:** 2.0.0  
**Base URL:** `http://localhost:8000`  
**API Docs:** `http://localhost:8000/docs`

---

## Quick Start

### 1. Start the Server

**Linux/Mac/WSL:**
```bash
cd Playground/backend
chmod +x start_api.sh
./start_api.sh
```

**Windows (PowerShell):**
```powershell
cd Playground\backend
.\start_api.ps1
```

**Direct Python:**
```bash
cd Playground/backend/api
python main_v2.py
```

### 2. Test the API

```bash
curl http://localhost:8000/api/v1/health
```

---

## Core Endpoints

### 🚀 Main Endpoint: Natural Language Query

The primary way users interact with the system.

**POST** `/api/v1/query`

```json
{
  "query": "Simulate a PWR pin cell with 4.5% enriched UO2 at 600K",
  "use_llm": false,
  "options": {
    "stream": true
  }
}
```

**Response:**
```json
{
  "query_id": "q_a3b2c1d0",
  "status": "queued",
  "assigned_agent": "routing",
  "estimated_duration": 30,
  "stream_url": "/api/v1/query/q_a3b2c1d0/stream"
}
```

**Parameters:**
- `query` (string, required): Natural language request
- `use_llm` (boolean, default=false): 
  - `false`: Fast keyword routing (~10ms, no API key needed)
  - `true`: LLM routing (~2-5s, more accurate, requires FIREWORKS key)
- `options.stream` (boolean): Enable Server-Sent Events for progress updates

---

### 📊 Get Query Status

**GET** `/api/v1/query/{query_id}`

```bash
curl http://localhost:8000/api/v1/query/q_a3b2c1d0
```

**Response:**
```json
{
  "query_id": "q_a3b2c1d0",
  "status": "completed",
  "query": "Simulate a PWR...",
  "agent_path": ["router", "studies"],
  "tool_calls": ["submit_study", "validate_physics"],
  "results": {
    "status": "success",
    "run_id": "run_abc12345",
    "keff": 1.045,
    "keff_std": 0.002,
    "spec": {...}
  }
}
```

**Statuses:**
- `queued`: Waiting to process
- `processing`: Currently running
- `completed`: Finished successfully
- `failed`: Error occurred (see `error` field)

---

### 🌊 Stream Progress (SSE)

**GET** `/api/v1/query/{query_id}/stream`

Server-Sent Events endpoint for real-time progress.

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/query/q_a3b2c1d0/stream'
);

eventSource.addEventListener('query_start', (e) => {
  const data = JSON.parse(e.data);
  console.log('Started:', data);
});

eventSource.addEventListener('routing', (e) => {
  const data = JSON.parse(e.data);
  console.log('Routing:', data.message);
});

eventSource.addEventListener('query_complete', (e) => {
  const data = JSON.parse(e.data);
  console.log('Completed:', data);
  eventSource.close();
});

eventSource.addEventListener('query_error', (e) => {
  const data = JSON.parse(e.data);
  console.error('Error:', data.error);
  eventSource.close();
});
```

---

## Agent-Specific Endpoints

For direct access to specific agents (bypasses router).

### 📝 Studies Agent

**POST** `/api/v1/agents/studies`

For single simulation requests.

```json
{
  "query": "Simulate PWR pin with 4.5% enriched UO2 at 600K"
}
```

---

### 🔄 Sweep Agent

**POST** `/api/v1/agents/sweep`

For parameter sweep requests.

```json
{
  "query": "Compare enrichments from 3% to 5%"
}
```

**Response:**
```json
{
  "status": "success",
  "run_ids": ["run_abc123", "run_def456", "run_ghi789"],
  "comparison": {
    "num_runs": 3,
    "keff_mean": 1.042,
    "keff_min": 1.035,
    "keff_max": 1.048
  },
  "sweep_config": {
    "param_name": "enrichment_pct",
    "param_values": [3.0, 4.0, 5.0]
  }
}
```

---

### 🔍 Query Agent

**POST** `/api/v1/agents/query`

For database searches.

```json
{
  "query": "Show me all PWR simulations"
}
```

---

### 📈 Analysis Agent

**POST** `/api/v1/agents/analysis`

For comparing specific runs.

```json
{
  "query": "Compare run_abc123 and run_def456"
}
```

---

### 🧭 Router Test

**POST** `/api/v1/router`

Test routing without execution (useful for debugging).

```json
{
  "query": "Simulate PWR",
  "use_llm": false
}
```

**Response:**
```json
{
  "agent": "studies",
  "intent": "single_study",
  "confidence": 0.8,
  "method": "keyword",
  "context": {"query": "Simulate PWR"}
}
```

---

## Direct Tool Access

Bypass agents entirely for maximum speed.

### 🔬 Submit Study

**POST** `/api/v1/studies`

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

**Response:**
```json
{
  "run_id": "run_abc12345",
  "spec_hash": "a1b2c3...",
  "keff": 1.045,
  "keff_std": 0.002,
  "runtime_seconds": 15.3,
  "status": "completed"
}
```

---

### 🔬 Get Study by ID

**GET** `/api/v1/studies/{run_id}`

```bash
curl http://localhost:8000/api/v1/studies/run_abc12345
```

---

### 🔄 Submit Sweep

**POST** `/api/v1/sweeps`

```json
{
  "base_spec": {
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Zircaloy", "Water"],
    "temperature_K": 600,
    "particles": 10000,
    "batches": 50
  },
  "param_name": "enrichment_pct",
  "param_values": [3.0, 3.5, 4.0, 4.5, 5.0]
}
```

---

### 🔍 Query Runs

**GET** `/api/v1/runs`

Query simulation results with filters.

**Query Parameters:**
- `geometry` (string): Filter by geometry (e.g., "PWR")
- `enrichment_min` (float): Minimum enrichment %
- `enrichment_max` (float): Maximum enrichment %
- `keff_min` (float): Minimum k-eff
- `keff_max` (float): Maximum k-eff
- `limit` (int, default=20): Max results
- `offset` (int, default=0): Pagination offset

**Example:**
```bash
curl "http://localhost:8000/api/v1/runs?geometry=PWR&keff_min=1.0&limit=10"
```

**Response:**
```json
{
  "total": 42,
  "limit": 10,
  "offset": 0,
  "runs": [
    {
      "run_id": "run_abc123",
      "spec_hash": "a1b2c3...",
      "geometry": "PWR pin cell",
      "enrichment_pct": 4.5,
      "temperature_K": 600,
      "keff": 1.045,
      "keff_std": 0.002,
      "status": "completed",
      "created_at": "2026-01-10T12:30:00Z"
    }
  ]
}
```

---

### 📊 Compare Runs

**POST** `/api/v1/runs/compare`

```json
{
  "run_ids": ["run_abc123", "run_def456", "run_ghi789"]
}
```

**Response:**
```json
{
  "num_runs": 3,
  "keff_values": [1.035, 1.042, 1.048],
  "keff_mean": 1.042,
  "keff_min": 1.035,
  "keff_max": 1.048,
  "runs": [...]
}
```

---

## Utility Endpoints

### 📊 Statistics

**GET** `/api/v1/statistics`

Get database statistics.

```json
{
  "total_studies": 150,
  "total_runs": 450,
  "completed_runs": 445,
  "total_queries": 89,
  "recent_runs": [
    {
      "run_id": "run_xyz789",
      "keff": 1.045,
      "geometry": "PWR pin cell",
      "created_at": "2026-01-10T14:30:00Z"
    }
  ]
}
```

---

### ❤️ Health Check

**GET** `/api/v1/health`

Check server status.

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2026-01-10T14:30:00Z",
  "services": {
    "mongodb": "connected",
    "fireworks_api": "available",
    "openmc": "ready"
  }
}
```

**Status Values:**
- `healthy`: All systems operational
- `degraded`: Partial functionality (e.g., LLM unavailable but keyword routing works)
- `unhealthy`: Critical services down (e.g., MongoDB)

---

## Frontend Integration Examples

### React Hook Example

```typescript
import { useState, useEffect } from 'react';

function useQuery(query: string) {
  const [status, setStatus] = useState('idle');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!query) return;

    const submitQuery = async () => {
      setStatus('loading');
      
      // Submit query
      const response = await fetch('http://localhost:8000/api/v1/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query,
          use_llm: false,  // Fast keyword routing
          options: { stream: false }
        })
      });
      
      const { query_id } = await response.json();
      
      // Poll for results
      const pollInterval = setInterval(async () => {
        const statusResponse = await fetch(
          `http://localhost:8000/api/v1/query/${query_id}`
        );
        const statusData = await statusResponse.json();
        
        if (statusData.status === 'completed') {
          setData(statusData.results);
          setStatus('success');
          clearInterval(pollInterval);
        } else if (statusData.status === 'failed') {
          setError(statusData.error);
          setStatus('error');
          clearInterval(pollInterval);
        }
      }, 1000);
      
      return () => clearInterval(pollInterval);
    };
    
    submitQuery();
  }, [query]);

  return { status, data, error };
}

// Usage
function App() {
  const { status, data } = useQuery("Simulate PWR at 4.5% enrichment");
  
  return (
    <div>
      {status === 'loading' && <p>Running simulation...</p>}
      {status === 'success' && <p>k-eff: {data.keff}</p>}
    </div>
  );
}
```

---

### Vue 3 Composition API Example

```vue
<script setup>
import { ref } from 'vue';

const query = ref('');
const results = ref(null);
const loading = ref(false);

async function submitQuery() {
  loading.value = true;
  
  const response = await fetch('http://localhost:8000/api/v1/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      query: query.value,
      use_llm: false 
    })
  });
  
  const { query_id } = await response.json();
  
  // Poll for completion
  const poll = setInterval(async () => {
    const statusRes = await fetch(
      `http://localhost:8000/api/v1/query/${query_id}`
    );
    const data = await statusRes.json();
    
    if (data.status === 'completed') {
      results.value = data.results;
      loading.value = false;
      clearInterval(poll);
    }
  }, 1000);
}
</script>

<template>
  <div>
    <input v-model="query" placeholder="Enter query..." />
    <button @click="submitQuery">Submit</button>
    <div v-if="loading">Loading...</div>
    <div v-if="results">k-eff: {{ results.keff }}</div>
  </div>
</template>
```

---

## Performance Tips

### Fast vs. Accurate Routing

| Mode | Speed | Accuracy | Use Case |
|------|-------|----------|----------|
| **Keyword** (`use_llm: false`) | ~10ms | ~85% | Production, user-facing |
| **LLM** (`use_llm: true`) | ~2-5s | ~95% | Complex queries, batch processing |

**Recommendation:** Use keyword routing by default. LLM routing is overkill for most queries.

### Caching

The system automatically caches identical simulations using spec hashing. Repeated queries with same parameters return instantly.

### Direct Tool Access

For maximum speed, use direct tool endpoints (`/api/v1/studies`) instead of natural language interface.

---

## CORS Configuration

The API allows requests from:
- `http://localhost:3000` (React default)
- `http://localhost:5173` (Vite default)

To add more origins, set `CORS_ORIGINS` env var:

```bash
export CORS_ORIGINS="http://localhost:3000,http://localhost:5173,http://myapp.com"
```

---

## Error Handling

All endpoints return standard error responses:

```json
{
  "detail": "Error message here"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `202`: Accepted (async operation started)
- `400`: Bad Request (invalid input)
- `404`: Not Found
- `500`: Internal Server Error

---

## Rate Limiting & Production

For production deployment:

1. Add rate limiting (e.g., `slowapi`)
2. Use production ASGI server (e.g., `gunicorn + uvicorn`)
3. Add authentication
4. Enable HTTPS
5. Configure MongoDB connection pooling
6. Add request logging

---

## Support

- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Source: `Playground/backend/api/main_v2.py`


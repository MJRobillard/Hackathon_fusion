# Frontend Integration - Quick Start Guide

**Get your frontend connected to the AONP API in 5 minutes**

---

## 🚀 Step 1: Start the API Server

```bash
cd Playground/backend
./start_api.sh
```

**Expected output:**
```
✓ MONGO_URI set
⚠️  WARNING: FIREWORKS key not set (using fast keyword routing)

📡 Server: http://0.0.0.0:8000
📚 API Docs: http://0.0.0.0:8000/docs
```

**Verify it's running:**
```bash
curl http://localhost:8000/api/v1/health
```

---

## 💡 Step 2: Test with curl

### Simple Query

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Simulate PWR at 4.5% enrichment",
    "use_llm": false
  }'
```

**Response:**
```json
{
  "query_id": "q_a1b2c3d4",
  "status": "queued",
  "assigned_agent": "routing",
  "estimated_duration": 30
}
```

### Check Status

```bash
curl http://localhost:8000/api/v1/query/q_a1b2c3d4
```

**Response (when complete):**
```json
{
  "query_id": "q_a1b2c3d4",
  "status": "completed",
  "results": {
    "status": "success",
    "run_id": "run_xyz789",
    "keff": 1.045,
    "keff_std": 0.002
  }
}
```

---

## 🎨 Step 3: Frontend Code

### React Example

```typescript
// src/hooks/useAONP.ts
import { useState } from 'react';

interface QueryResult {
  status: string;
  keff?: number;
  run_id?: string;
  error?: string;
}

export function useAONP() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);

  const runQuery = async (query: string) => {
    setLoading(true);
    
    try {
      // Submit query
      const response = await fetch('http://localhost:8000/api/v1/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query,
          use_llm: false  // Fast keyword routing
        })
      });
      
      const { query_id } = await response.json();
      
      // Poll for results
      const poll = async () => {
        const statusRes = await fetch(
          `http://localhost:8000/api/v1/query/${query_id}`
        );
        const data = await statusRes.json();
        
        if (data.status === 'completed') {
          setResult(data.results);
          setLoading(false);
        } else if (data.status === 'failed') {
          setResult({ status: 'error', error: data.error });
          setLoading(false);
        } else {
          setTimeout(poll, 1000);
        }
      };
      
      poll();
    } catch (error) {
      setResult({ status: 'error', error: String(error) });
      setLoading(false);
    }
  };

  return { runQuery, loading, result };
}

// Usage in component
function SimulationForm() {
  const { runQuery, loading, result } = useAONP();
  const [query, setQuery] = useState('');

  return (
    <div>
      <input 
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Simulate PWR at 4.5% enrichment"
      />
      <button onClick={() => runQuery(query)} disabled={loading}>
        {loading ? 'Running...' : 'Run Simulation'}
      </button>
      
      {result && (
        <div>
          <h3>Results</h3>
          <p>Status: {result.status}</p>
          {result.keff && <p>k-eff: {result.keff}</p>}
          {result.run_id && <p>Run ID: {result.run_id}</p>}
          {result.error && <p>Error: {result.error}</p>}
        </div>
      )}
    </div>
  );
}
```

### Vue 3 Example

```vue
<!-- SimulationForm.vue -->
<script setup lang="ts">
import { ref } from 'vue';

const query = ref('');
const loading = ref(false);
const result = ref<any>(null);

async function runQuery() {
  loading.value = true;
  
  // Submit query
  const response = await fetch('http://localhost:8000/api/v1/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      query: query.value,
      use_llm: false 
    })
  });
  
  const { query_id } = await response.json();
  
  // Poll for results
  const poll = async () => {
    const statusRes = await fetch(
      `http://localhost:8000/api/v1/query/${query_id}`
    );
    const data = await statusRes.json();
    
    if (data.status === 'completed') {
      result.value = data.results;
      loading.value = false;
    } else if (data.status === 'failed') {
      result.value = { status: 'error', error: data.error };
      loading.value = false;
    } else {
      setTimeout(poll, 1000);
    }
  };
  
  poll();
}
</script>

<template>
  <div>
    <input 
      v-model="query"
      placeholder="Simulate PWR at 4.5% enrichment"
    />
    <button @click="runQuery" :disabled="loading">
      {{ loading ? 'Running...' : 'Run Simulation' }}
    </button>
    
    <div v-if="result">
      <h3>Results</h3>
      <p>Status: {{ result.status }}</p>
      <p v-if="result.keff">k-eff: {{ result.keff }}</p>
      <p v-if="result.run_id">Run ID: {{ result.run_id }}</p>
      <p v-if="result.error">Error: {{ result.error }}</p>
    </div>
  </div>
</template>
```

### Vanilla JavaScript

```javascript
// Simple vanilla JS example
async function runSimulation(query) {
  const statusDiv = document.getElementById('status');
  statusDiv.textContent = 'Running...';
  
  // Submit query
  const response = await fetch('http://localhost:8000/api/v1/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, use_llm: false })
  });
  
  const { query_id } = await response.json();
  
  // Poll for results
  const checkStatus = async () => {
    const res = await fetch(`http://localhost:8000/api/v1/query/${query_id}`);
    const data = await res.json();
    
    if (data.status === 'completed') {
      statusDiv.innerHTML = `
        <h3>Completed!</h3>
        <p>k-eff: ${data.results.keff}</p>
        <p>Run ID: ${data.results.run_id}</p>
      `;
    } else if (data.status === 'failed') {
      statusDiv.textContent = `Error: ${data.error}`;
    } else {
      setTimeout(checkStatus, 1000);
    }
  };
  
  checkStatus();
}

// Usage
document.getElementById('runBtn').addEventListener('click', () => {
  const query = document.getElementById('queryInput').value;
  runSimulation(query);
});
```

---

## 🌊 Step 4: Real-time Updates (SSE)

For real-time progress updates, use Server-Sent Events:

```javascript
function runSimulationWithUpdates(query) {
  // Submit query
  fetch('http://localhost:8000/api/v1/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      query,
      use_llm: false,
      options: { stream: true }  // Enable streaming
    })
  })
  .then(res => res.json())
  .then(({ query_id, stream_url }) => {
    // Connect to SSE stream
    const eventSource = new EventSource(
      `http://localhost:8000${stream_url}`
    );
    
    eventSource.addEventListener('query_start', (e) => {
      console.log('Started:', JSON.parse(e.data));
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
  });
}
```

---

## 🎯 Common Query Examples

### Single Simulation
```javascript
runQuery("Simulate PWR pin cell with 4.5% enriched UO2 at 600K")
```

### Parameter Sweep
```javascript
runQuery("Compare enrichments from 3% to 5%")
```

### Database Query
```javascript
runQuery("Show me all PWR simulations")
```

### Analysis
```javascript
runQuery("Compare run_abc123 and run_def456")
```

---

## 🔧 API Endpoints Cheat Sheet

### Main Query
```
POST /api/v1/query
Body: { "query": "...", "use_llm": false }
→ Returns: { "query_id": "..." }

GET /api/v1/query/{query_id}
→ Returns: { "status": "...", "results": {...} }
```

### Direct Study (Fast)
```
POST /api/v1/studies
Body: {
  "geometry": "PWR pin cell",
  "materials": ["UO2", "Water"],
  "enrichment_pct": 4.5,
  "temperature_K": 600
}
→ Returns: { "run_id": "...", "keff": 1.045 }
```

### Query Runs
```
GET /api/v1/runs?geometry=PWR&keff_min=1.0&limit=10
→ Returns: { "runs": [...], "total": 42 }
```

### Health Check
```
GET /api/v1/health
→ Returns: { "status": "healthy", "services": {...} }
```

---

## 🐛 Troubleshooting

### CORS Error

**Error:** "Access to fetch has been blocked by CORS policy"

**Solution:** Add your frontend URL to CORS_ORIGINS:
```bash
export CORS_ORIGINS="http://localhost:3000,http://localhost:5173,http://yourdomain.com"
```

### Connection Refused

**Error:** "Failed to fetch"

**Solution:** Make sure API server is running:
```bash
curl http://localhost:8000/api/v1/health
```

### Slow Responses

**Solution:** Make sure you're using keyword routing:
```javascript
{ "query": "...", "use_llm": false }  // ← Fast!
```

---

## 📊 Performance Tips

1. **Use keyword routing** (default): Fast and accurate enough
2. **Direct tool access**: Bypass agents for max speed
3. **Batch operations**: Submit multiple queries if needed
4. **Cache awareness**: Identical specs return instantly

---

## 🎨 UI/UX Recommendations

### Loading States
```
"Analyzing query..." (routing)
"Running simulation..." (processing)
"Completed!" (done)
```

### Error Handling
```javascript
if (result.status === 'error') {
  // Show user-friendly error message
  // Offer retry button
  // Log details for debugging
}
```

### Progress Indicators
- Use SSE for real-time updates
- Show estimated time (30s for studies, 60s for sweeps)
- Display which agent is running
- Show tool calls being executed

---

## 📚 Full Documentation

- **Complete API Reference**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **Server Setup**: [README_API.md](./README_API.md)
- **Architecture**: [README_MULTI_AGENT.md](./README_MULTI_AGENT.md)

---

## ✅ Checklist

- [ ] API server running (`./start_api.sh`)
- [ ] Health check passes (`curl localhost:8000/api/v1/health`)
- [ ] CORS configured for your frontend URL
- [ ] Tested with curl
- [ ] Frontend code integrated
- [ ] Error handling implemented
- [ ] Loading states added

---

**You're ready to build!** 🚀

The API is fast, reliable, and frontend-ready. Start building your UI!


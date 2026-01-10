# OpenMC Integration Specification (⚠️ SUPERSEDED)

**Version**: 1.0  
**Date**: 2026-01-10  
**Status**: ⚠️ **This spec was written before discovering the actual codebase architecture**

---

## ⚠️ IMPORTANT: USE THE NEW INTEGRATION GUIDE INSTEAD

**This document is preserved for reference only.**

**For the actual integration strategy, see:**
- **[INTEGRATION_BRIDGE.md](./INTEGRATION_BRIDGE.md)** ← **USE THIS**

---

## Why This Spec Was Wrong

This spec assumed:
- Natural language specs (like `"geometry": "PWR pin cell"`)
- Simple HTTP API
- Separate OpenMC service

**Reality:**
- OpenMC team has structured schemas (`aonp/schemas/study.py`)
- Agent team has simplified schemas (`Playground/backend/agent_tools.py`)
- Need an **adapter layer** to translate between them

---

## Original Spec (For Reference Only)

### Architecture Overview

```
┌─────────────────┐
│  AONP Agents    │
│  (FastAPI)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Redis Queue    │ ← Recommended coordination layer
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  OpenMC Backend │─────▶│   MongoDB    │
│  (Your service) │      │   (shared)   │
└─────────────────┘      └──────────────┘
```

**Data Ownership**:
- **AONP Agents** write to: `requests`, `agent_traces`
- **OpenMC Backend** writes to: `runs`, `summaries`
- Both read from all collections

---

## Required Endpoints

### 1. Submit Simulation

**Endpoint**: `POST /api/v1/simulations`

**Request Body**:
```json
{
  "run_id": "run_abc123",
  "spec": {
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Zircaloy", "Water"],
    "enrichment_pct": 4.5,
    "temperature_K": 600,
    "particles": 10000,
    "batches": 50
  },
  "callback_url": "http://aonp-backend/api/v1/callbacks/simulation-complete"
}
```

**Response** (202 Accepted):
```json
{
  "run_id": "run_abc123",
  "status": "queued",
  "estimated_duration_seconds": 5
}
```

---

### 2. Get Simulation Status

**Endpoint**: `GET /api/v1/simulations/{run_id}`

**Response** (200 OK):
```json
{
  "run_id": "run_abc123",
  "status": "running|completed|failed",
  "progress_percent": 65,
  "started_at": "2026-01-10T14:23:45Z",
  "completed_at": null,
  "error": null
}
```

---

### 3. Health Check

**Endpoint**: `GET /api/v1/health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "openmc_version": "0.14.0",
  "queue_size": 3,
  "active_simulations": 1
}
```

---

## MongoDB Schema (Write Contract)

### Collection: `runs`

**OpenMC writes to this collection:**

```json
{
  "run_id": "run_abc123",
  "spec_hash": "7a3f9c2e...",
  "status": "queued|running|completed|failed",
  "started_at": "2026-01-10T14:23:45Z",
  "completed_at": "2026-01-10T14:23:50Z",
  "error": null,
  "spec": { /* same as request */ },
  "raw_results": {
    "keff": 1.28734,
    "keff_std": 0.00028,
    "statepoint_path": "/path/to/statepoint.h5"
  }
}
```

### Collection: `summaries`

**OpenMC writes to this collection:**

```json
{
  "run_id": "run_abc123",
  "spec_hash": "7a3f9c2e...",
  "keff": 1.28734,
  "keff_std": 0.00028,
  "status": "completed",
  "created_at": "2026-01-10T14:23:50Z",
  "spec": {
    "geometry": "PWR pin cell",
    "enrichment_pct": 4.5,
    "temperature_K": 600
  }
}
```

**Index requirements**: 
- `run_id` (unique)
- `spec_hash` (for deduplication)
- `spec.geometry`, `spec.enrichment_pct`, `keff` (for queries)

---

## Alternative: Redis Queue Integration (Recommended)

Instead of HTTP APIs, use Redis queue for better reliability:

### Queue Setup

**Queue name**: `openmc:simulation_queue`

**Message format**:
```json
{
  "run_id": "run_abc123",
  "spec": { /* study spec */ },
  "priority": "normal|high",
  "submitted_at": "2026-01-10T14:23:45Z"
}
```

### OpenMC Worker Process

```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379)

while True:
    # Pop job from queue
    job = redis_client.blpop('openmc:simulation_queue', timeout=5)
    if job:
        data = json.loads(job[1])
        run_simulation(data['run_id'], data['spec'])
```

### AONP Agents Push Jobs

```python
import redis

redis_client = redis.Redis(host='localhost', port=6379)

redis_client.rpush('openmc:simulation_queue', json.dumps({
    "run_id": run_id,
    "spec": spec.dict()
}))
```

**Why queue over API?**
- ✅ More reliable (survives restarts)
- ✅ Built-in retry logic
- ✅ Easy to scale workers
- ✅ No HTTP overhead

---

## Error Handling

**OpenMC should write errors to MongoDB:**

```json
{
  "run_id": "run_abc123",
  "status": "failed",
  "error": "Geometry validation failed: overlapping cells",
  "error_code": "GEOMETRY_ERROR",
  "completed_at": "2026-01-10T14:23:47Z"
}
```

**Error codes**:
- `GEOMETRY_ERROR`: Invalid geometry specification
- `MATERIAL_ERROR`: Invalid material definition
- `OPENMC_CRASH`: OpenMC internal error
- `TIMEOUT`: Simulation exceeded time limit

---

## Minimal MVP Implementation

If you want the **absolute minimum** to get started:

### Option 1: Direct MongoDB (No API)

1. **AONP writes**: `{"run_id": "...", "spec": {...}, "status": "queued"}` to `runs` collection
2. **OpenMC polls MongoDB**: Find runs with `status: "queued"`
3. **OpenMC updates**: Set `status: "running"`, run sim, write results, set `status: "completed"`

**Pros**: Zero API code needed  
**Cons**: Polling is inefficient

### Option 2: Redis Queue (Recommended)

1. **AONP pushes** to Redis queue: `redis.rpush('sim_queue', json.dumps({...}))`
2. **OpenMC pops** from queue: `redis.blpop('sim_queue')`
3. **OpenMC writes results** to MongoDB

**Pros**: Efficient, scalable  
**Cons**: Requires Redis (but it's 5-min setup)

---

## Connection Details

**MongoDB URI**: (you already have this from `.env`)

**Redis** (if using queue):
```bash
# Install Redis
docker run -d -p 6379:6379 redis:alpine

# Or use Redis Cloud free tier
# https://redis.com/try-free/
```

**Environment variables** for OpenMC backend:
```bash
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/aonp
REDIS_URL=redis://localhost:6379  # if using queue
CALLBACK_URL=http://aonp-backend:8000/api/v1/callbacks  # if using HTTP
```

---

## Testing

**Test simulation request**:
```json
{
  "run_id": "test_run_001",
  "spec": {
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Zircaloy", "Water"],
    "enrichment_pct": 4.5,
    "temperature_K": 600,
    "particles": 1000,
    "batches": 10
  }
}
```

**Expected result in MongoDB `runs`**:
```json
{
  "run_id": "test_run_001",
  "status": "completed",
  "raw_results": {
    "keff": 1.287,
    "keff_std": 0.0003
  }
}
```

---

## Questions?

1. **Prefer HTTP API or Redis queue?** (Queue recommended)
2. **Can you use Python?** (for easy Redis integration)
3. **Simulation time limits?** (suggest max 60 seconds for MVP)
4. **Max concurrent simulations?** (impacts worker count)

---

**Contact**: Share your MongoDB URI and preferred integration method (HTTP vs Queue)


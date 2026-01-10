# AONP Multi-Agent API Design Document

**Version**: 1.0  
**Date**: 2026-01-10  
**Status**: Draft for Review  
**Purpose**: Define REST API specification for frontend integration with AONP multi-agent nuclear simulation system

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [API Overview](#api-overview)
4. [Core Endpoints](#core-endpoints)
5. [Data Models](#data-models)
6. [Real-time Communication](#real-time-communication)
7. [Error Handling](#error-handling)
8. [Security Considerations](#security-considerations)
9. [Implementation Plan](#implementation-plan)
10. [Testing Strategy](#testing-strategy)
11. [Future Enhancements](#future-enhancements)

---

## 1. Executive Summary

### Purpose
Create a RESTful API to expose the AONP multi-agent system to a frontend application, enabling users to:
- Submit natural language simulation requests
- Execute single studies and parameter sweeps
- Query past simulation results
- Track agent execution progress in real-time
- Visualize results and comparisons

### Technology Stack
- **Framework**: FastAPI (async support, automatic OpenAPI docs, Pydantic integration)
- **Database**: MongoDB Atlas (existing setup)
- **Real-time**: Server-Sent Events (SSE) or WebSockets
- **Agent Orchestration**: LangGraph (existing)
- **LLM**: Fireworks API (existing)
- **Language**: Python 3.13

### Key Design Principles
1. **Async-first**: All endpoints use async/await for non-blocking I/O
2. **Stateless**: Each request is independent (state in MongoDB)
3. **Progressive enhancement**: Works without real-time updates, enhanced with SSE
4. **Schema-driven**: Pydantic models ensure type safety
5. **Idempotent operations**: Same request → same result (via spec hashing)

---

## 2. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│                  (React/Vue/Vanilla JS)                         │
└────────────┬────────────────────────────────────┬───────────────┘
             │                                    │
             │ REST API                           │ SSE/WebSocket
             │ (JSON)                             │ (Agent Progress)
             │                                    │
┌────────────▼────────────────────────────────────▼───────────────┐
│                      FASTAPI SERVER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Routes     │  │  Middleware  │  │   WebSocket  │         │
│  │  /api/v1/*   │  │   - CORS     │  │   Manager    │         │
│  │              │  │   - Auth     │  │              │         │
│  └──────┬───────┘  └──────────────┘  └──────┬───────┘         │
│         │                                    │                  │
│  ┌──────▼─────────────────────────────────┐  │                 │
│  │      AONP Agent Orchestrator           │  │                 │
│  │         (LangGraph)                    │◄─┘                 │
│  │                                        │                     │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ │                     │
│  │  │ Intent  │→│Planner  │→│Executor │ │                     │
│  │  │Classify │ │ Agent   │ │ Agent   │ │                     │
│  │  └─────────┘ └─────────┘ └─────────┘ │                     │
│  │  ┌─────────┐ ┌─────────┐             │                     │
│  │  │Analyzer │ │Suggester│             │                     │
│  │  └─────────┘ └─────────┘             │                     │
│  └────────────────┬───────────────────┬─┘                     │
│                   │                   │                        │
└───────────────────┼───────────────────┼────────────────────────┘
                    │                   │
         ┌──────────▼──────────┐ ┌──────▼───────────┐
         │   MongoDB Atlas     │ │   Agent Tools    │
         │                     │ │                  │
         │ - studies           │ │ - submit_study   │
         │ - runs              │ │ - query_results  │
         │ - summaries         │ │ - generate_sweep │
         │                     │ │ - compare_runs   │
         └─────────────────────┘ └──────────────────┘
```

### Data Flow for Typical Request

```
1. Frontend → POST /api/v1/requests
   {
     "query": "Simulate PWR pin with 4.5% enriched UO2",
     "options": {}
   }

2. API validates request → generates request_id

3. API invokes agent orchestrator asynchronously

4. Agent progress streamed via SSE:
   - "Intent Classifier: detected 'single_study'"
   - "Study Planner: created spec"
   - "Executor: running simulation..."
   - "Analyzer: keff = 1.287..."

5. Final result stored in MongoDB

6. Frontend polls GET /api/v1/requests/{request_id}
   or receives completion via SSE

7. Frontend displays results + analysis + suggestions
```

---

## 3. API Overview

### Base URL
```
http://localhost:8000/api/v1
```

### Versioning Strategy
- URL-based versioning (`/api/v1/`, `/api/v2/`)
- Maintains backward compatibility
- Deprecation warnings in headers

### Content Types
- **Request**: `application/json`
- **Response**: `application/json`
- **Streaming**: `text/event-stream` (SSE)

### Authentication (Future)
- Bearer token in `Authorization` header
- API keys for programmatic access
- **MVP**: No auth (single-user mode)

### Rate Limiting (Future)
- 100 requests/minute per IP
- 10 concurrent simulations per user

---

## 4. Core Endpoints

### 4.1 Request Management

#### `POST /api/v1/requests`

Submit a natural language simulation request to the multi-agent system.

**Request Body**:
```json
{
  "query": "string (required)",
  "options": {
    "stream": "boolean (default: false)",
    "priority": "string (low|normal|high, default: normal)"
  },
  "metadata": {
    "user_id": "string (optional)",
    "session_id": "string (optional)"
  }
}
```

**Response** (202 Accepted):
```json
{
  "request_id": "req_a3f7c8b2",
  "status": "queued",
  "created_at": "2026-01-10T14:23:45Z",
  "estimated_duration_seconds": 15,
  "stream_url": "/api/v1/requests/req_a3f7c8b2/stream"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Simulate a PWR pin cell with 4.5% enriched UO2 at 600K",
    "options": {"stream": true}
  }'
```

---

#### `GET /api/v1/requests/{request_id}`

Get the current status and results of a request.

**Path Parameters**:
- `request_id`: Unique request identifier

**Response** (200 OK):
```json
{
  "request_id": "req_a3f7c8b2",
  "status": "completed",
  "query": "Simulate a PWR pin cell with 4.5% enriched UO2 at 600K",
  "intent": "single_study",
  "created_at": "2026-01-10T14:23:45Z",
  "completed_at": "2026-01-10T14:24:02Z",
  "duration_seconds": 17.3,
  "agent_trace": [
    {
      "agent": "intent_classifier",
      "started_at": "2026-01-10T14:23:45Z",
      "completed_at": "2026-01-10T14:23:47Z",
      "output": "Detected intent: single_study"
    },
    {
      "agent": "study_planner",
      "started_at": "2026-01-10T14:23:47Z",
      "completed_at": "2026-01-10T14:23:50Z",
      "output": "Created study spec with geometry: PWR pin cell"
    }
  ],
  "results": {
    "run_ids": ["run_f7a2c1e3"],
    "spec_hash": "7a3f9c2e8b1d4f5a6c7e9b8d3f2a1c5e",
    "keff": 1.28734,
    "keff_std": 0.00028,
    "status": "completed"
  },
  "analysis": "The keff value of 1.287 indicates a supercritical system...",
  "suggestions": [
    "Vary fuel temperature from 500K to 700K to study reactivity coefficient",
    "Add control rods to achieve criticality",
    "Compare with different enrichment levels (3.0% to 5.0%)"
  ]
}
```

**Status Values**:
- `queued`: Waiting to start
- `processing`: Agent workflow in progress
- `completed`: Finished successfully
- `failed`: Error occurred
- `cancelled`: User cancelled

---

#### `GET /api/v1/requests/{request_id}/stream`

Server-Sent Events stream for real-time agent progress.

**Response** (200 OK, `text/event-stream`):
```
event: agent_start
data: {"agent": "intent_classifier", "timestamp": "2026-01-10T14:23:45Z"}

event: agent_progress
data: {"agent": "intent_classifier", "message": "Analyzing request..."}

event: agent_complete
data: {"agent": "intent_classifier", "output": "Detected intent: single_study"}

event: agent_start
data: {"agent": "study_planner", "timestamp": "2026-01-10T14:23:47Z"}

event: agent_complete
data: {"agent": "study_planner", "output": "Created study spec"}

event: simulation_start
data: {"run_id": "run_f7a2c1e3"}

event: simulation_complete
data: {"run_id": "run_f7a2c1e3", "keff": 1.28734}

event: request_complete
data: {"request_id": "req_a3f7c8b2", "status": "completed"}
```

**Frontend JavaScript Example**:
```javascript
const eventSource = new EventSource('/api/v1/requests/req_a3f7c8b2/stream');

eventSource.addEventListener('agent_start', (e) => {
  const data = JSON.parse(e.data);
  console.log(`Agent ${data.agent} started`);
});

eventSource.addEventListener('request_complete', (e) => {
  eventSource.close();
});
```

---

#### `DELETE /api/v1/requests/{request_id}`

Cancel a running request.

**Response** (200 OK):
```json
{
  "request_id": "req_a3f7c8b2",
  "status": "cancelled",
  "message": "Request cancelled successfully"
}
```

---

### 4.2 Run Management

#### `GET /api/v1/runs/{run_id}`

Get detailed information about a specific simulation run.

**Response** (200 OK):
```json
{
  "run_id": "run_f7a2c1e3",
  "spec_hash": "7a3f9c2e8b1d4f5a6c7e9b8d3f2a1c5e",
  "status": "completed",
  "created_at": "2026-01-10T14:23:50Z",
  "completed_at": "2026-01-10T14:23:55Z",
  "spec": {
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Zircaloy", "Water"],
    "enrichment_pct": 4.5,
    "temperature_K": 600,
    "particles": 10000,
    "batches": 50
  },
  "results": {
    "keff": 1.28734,
    "keff_std": 0.00028,
    "runtime_seconds": 0.5
  },
  "artifacts": {
    "statepoint_url": "/api/v1/runs/run_f7a2c1e3/artifacts/statepoint.h5",
    "summary_parquet_url": "/api/v1/runs/run_f7a2c1e3/artifacts/summary.parquet"
  }
}
```

---

#### `GET /api/v1/runs`

Query and search simulation runs.

**Query Parameters**:
- `geometry`: Filter by geometry type (e.g., "PWR pin cell")
- `enrichment_min`: Minimum enrichment percentage
- `enrichment_max`: Maximum enrichment percentage
- `keff_min`: Minimum keff value
- `keff_max`: Maximum keff value
- `limit`: Number of results (default: 20, max: 100)
- `offset`: Pagination offset (default: 0)
- `sort`: Sort field (default: "created_at")
- `order`: Sort order ("asc" or "desc", default: "desc")

**Response** (200 OK):
```json
{
  "total": 156,
  "limit": 20,
  "offset": 0,
  "runs": [
    {
      "run_id": "run_f7a2c1e3",
      "geometry": "PWR pin cell",
      "enrichment_pct": 4.5,
      "keff": 1.28734,
      "created_at": "2026-01-10T14:23:50Z"
    }
  ]
}
```

**Example**:
```bash
curl "http://localhost:8000/api/v1/runs?geometry=PWR&keff_min=1.0&limit=10"
```

---

#### `POST /api/v1/runs/compare`

Compare multiple simulation runs.

**Request Body**:
```json
{
  "run_ids": [
    "run_f7a2c1e3",
    "run_a8b3c9d2",
    "run_e4f1g7h3"
  ]
}
```

**Response** (200 OK):
```json
{
  "num_runs": 3,
  "keff_values": [1.28734, 1.29102, 1.28456],
  "keff_mean": 1.28764,
  "keff_min": 1.28456,
  "keff_max": 1.29102,
  "keff_std_dev": 0.00271,
  "runs": [
    {
      "run_id": "run_f7a2c1e3",
      "keff": 1.28734,
      "enrichment_pct": 4.5,
      "temperature_K": 600
    }
  ],
  "comparison_chart_url": "/api/v1/runs/compare/chart?run_ids=run_f7a2c1e3,run_a8b3c9d2"
}
```

---

### 4.3 Sweep Management

#### `POST /api/v1/sweeps`

Create and execute a parameter sweep.

**Request Body**:
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
  "sweep_values": [3.0, 3.5, 4.0, 4.5, 5.0],
  "options": {
    "parallel": false,
    "stream": true
  }
}
```

**Response** (202 Accepted):
```json
{
  "sweep_id": "sweep_b2c9d4e7",
  "status": "running",
  "total_runs": 5,
  "completed_runs": 0,
  "run_ids": [
    "run_a1b2c3d4",
    "run_e5f6g7h8",
    "run_i9j0k1l2",
    "run_m3n4o5p6",
    "run_q7r8s9t0"
  ],
  "stream_url": "/api/v1/sweeps/sweep_b2c9d4e7/stream"
}
```

---

#### `GET /api/v1/sweeps/{sweep_id}`

Get sweep status and results.

**Response** (200 OK):
```json
{
  "sweep_id": "sweep_b2c9d4e7",
  "status": "completed",
  "total_runs": 5,
  "completed_runs": 5,
  "created_at": "2026-01-10T14:30:00Z",
  "completed_at": "2026-01-10T14:30:45Z",
  "sweep_parameter": "enrichment_pct",
  "results": {
    "keff_min": 1.23456,
    "keff_max": 1.31234,
    "keff_mean": 1.27345,
    "runs": [
      {
        "run_id": "run_a1b2c3d4",
        "enrichment_pct": 3.0,
        "keff": 1.23456
      }
    ]
  },
  "visualization_url": "/api/v1/sweeps/sweep_b2c9d4e7/chart"
}
```

---

### 4.4 Statistics and Metadata

#### `GET /api/v1/statistics`

Get database statistics and system status.

**Response** (200 OK):
```json
{
  "total_studies": 42,
  "total_runs": 158,
  "completed_runs": 155,
  "failed_runs": 3,
  "total_requests": 67,
  "average_runtime_seconds": 5.3,
  "most_common_geometry": "PWR pin cell",
  "recent_runs": [
    {
      "run_id": "run_f7a2c1e3",
      "geometry": "PWR pin cell",
      "keff": 1.28734,
      "created_at": "2026-01-10T14:23:50Z"
    }
  ]
}
```

---

#### `GET /api/v1/health`

Health check endpoint for monitoring.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-10T14:35:20Z",
  "services": {
    "mongodb": "connected",
    "fireworks_api": "available",
    "openmc": "ready"
  }
}
```

---

## 5. Data Models

### 5.1 Core Models (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

# ============================================================================
# REQUEST MODELS
# ============================================================================

class CreateRequestRequest(BaseModel):
    """Request to create a new simulation request"""
    query: str = Field(..., description="Natural language simulation request")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class CreateRequestResponse(BaseModel):
    """Response after creating a request"""
    request_id: str
    status: Literal["queued", "processing", "completed", "failed", "cancelled"]
    created_at: datetime
    estimated_duration_seconds: int
    stream_url: Optional[str] = None

class AgentTraceEntry(BaseModel):
    """Single agent execution trace"""
    agent: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    output: Optional[str] = None
    error: Optional[str] = None

class RequestStatus(BaseModel):
    """Full status of a request"""
    request_id: str
    status: Literal["queued", "processing", "completed", "failed", "cancelled"]
    query: str
    intent: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    agent_trace: List[AgentTraceEntry] = []
    results: Optional[Dict[str, Any]] = None
    analysis: Optional[str] = None
    suggestions: Optional[List[str]] = None
    error: Optional[str] = None

# ============================================================================
# RUN MODELS
# ============================================================================

class StudySpec(BaseModel):
    """Study specification (matches agent_tools.py)"""
    geometry: str
    materials: List[str]
    enrichment_pct: Optional[float] = None
    temperature_K: Optional[float] = None
    particles: int = 10000
    batches: int = 50

class RunSummary(BaseModel):
    """Summary of a simulation run"""
    run_id: str
    spec_hash: str
    geometry: str
    enrichment_pct: Optional[float]
    temperature_K: Optional[float]
    keff: float
    keff_std: float
    status: str
    created_at: datetime

class RunDetail(BaseModel):
    """Detailed run information"""
    run_id: str
    spec_hash: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    spec: StudySpec
    results: Dict[str, Any]
    artifacts: Dict[str, str]

class RunQueryResponse(BaseModel):
    """Response for run queries"""
    total: int
    limit: int
    offset: int
    runs: List[RunSummary]

class CompareRunsRequest(BaseModel):
    """Request to compare multiple runs"""
    run_ids: List[str] = Field(..., min_items=2)

class CompareRunsResponse(BaseModel):
    """Comparison results"""
    num_runs: int
    keff_values: List[float]
    keff_mean: float
    keff_min: float
    keff_max: float
    keff_std_dev: float
    runs: List[Dict[str, Any]]

# ============================================================================
# SWEEP MODELS
# ============================================================================

class CreateSweepRequest(BaseModel):
    """Request to create a parameter sweep"""
    base_spec: StudySpec
    sweep_parameter: str
    sweep_values: List[Any]
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

class CreateSweepResponse(BaseModel):
    """Response after creating sweep"""
    sweep_id: str
    status: str
    total_runs: int
    completed_runs: int
    run_ids: List[str]
    stream_url: Optional[str] = None

class SweepStatus(BaseModel):
    """Sweep status and results"""
    sweep_id: str
    status: str
    total_runs: int
    completed_runs: int
    created_at: datetime
    completed_at: Optional[datetime]
    sweep_parameter: str
    results: Optional[Dict[str, Any]]

# ============================================================================
# STATISTICS MODELS
# ============================================================================

class Statistics(BaseModel):
    """Database and system statistics"""
    total_studies: int
    total_runs: int
    completed_runs: int
    failed_runs: int
    total_requests: int
    average_runtime_seconds: float
    most_common_geometry: Optional[str]
    recent_runs: List[RunSummary]

class HealthCheck(BaseModel):
    """System health status"""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: datetime
    services: Dict[str, str]
```

---

## 6. Real-time Communication

### 6.1 Server-Sent Events (SSE) - RECOMMENDED

**Pros**:
- Simple to implement (standard HTTP)
- Auto-reconnect built-in
- Works through firewalls/proxies
- One-way (server → client) is sufficient for our use case

**Implementation**:
```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio
import json

@app.get("/api/v1/requests/{request_id}/stream")
async def stream_request_progress(request_id: str):
    async def event_generator():
        # Subscribe to agent events
        async for event in agent_event_bus.subscribe(request_id):
            yield f"event: {event['type']}\n"
            yield f"data: {json.dumps(event['data'])}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
```

**Frontend Usage**:
```javascript
const eventSource = new EventSource('/api/v1/requests/req_123/stream');

eventSource.addEventListener('agent_start', (e) => {
  const data = JSON.parse(e.data);
  updateUI(`Agent ${data.agent} started...`);
});

eventSource.addEventListener('request_complete', (e) => {
  eventSource.close();
  fetchFinalResults();
});

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  eventSource.close();
};
```

### 6.2 WebSocket Alternative

**Use if**:
- Need bidirectional communication
- Want to send commands during execution (pause, cancel)
- Need lower latency

**Implementation**:
```python
from fastapi import WebSocket

@app.websocket("/api/v1/ws/requests/{request_id}")
async def websocket_request_progress(websocket: WebSocket, request_id: str):
    await websocket.accept()
    try:
        async for event in agent_event_bus.subscribe(request_id):
            await websocket.send_json(event)
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
```

### 6.3 Event Bus Architecture

```python
import asyncio
from collections import defaultdict
from typing import Dict, Set, AsyncIterator

class AgentEventBus:
    """Pub/sub for agent events"""
    
    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
    
    def subscribe(self, request_id: str) -> AsyncIterator[dict]:
        """Subscribe to events for a request"""
        queue = asyncio.Queue()
        self._subscribers[request_id].add(queue)
        
        async def generator():
            try:
                while True:
                    event = await queue.get()
                    if event is None:  # Sentinel for completion
                        break
                    yield event
            finally:
                self._subscribers[request_id].discard(queue)
        
        return generator()
    
    async def publish(self, request_id: str, event: dict):
        """Publish event to all subscribers"""
        for queue in self._subscribers[request_id]:
            await queue.put(event)
    
    async def complete(self, request_id: str):
        """Signal completion"""
        for queue in self._subscribers[request_id]:
            await queue.put(None)

# Global instance
event_bus = AgentEventBus()
```

---

## 7. Error Handling

### 7.1 Error Response Format

All errors follow this structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid study specification",
    "details": {
      "field": "enrichment_pct",
      "issue": "Value must be between 0 and 100"
    },
    "request_id": "req_a3f7c8b2",
    "timestamp": "2026-01-10T14:23:45Z"
  }
}
```

### 7.2 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `NOT_FOUND` | 404 | Resource not found |
| `AGENT_FAILED` | 500 | Agent execution error |
| `LLM_ERROR` | 502 | Fireworks API error |
| `DATABASE_ERROR` | 503 | MongoDB connection issue |
| `TIMEOUT` | 504 | Request timeout |
| `RATE_LIMIT` | 429 | Too many requests |

### 7.3 Error Handling Implementation

```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from datetime import datetime

class AONPException(Exception):
    """Base exception for AONP errors"""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}

@app.exception_handler(AONPException)
async def aonp_exception_handler(request: Request, exc: AONPException):
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": request.state.request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the error
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request.state.request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
```

---

## 8. Security Considerations

### 8.1 MVP (Current Scope)

**Assumptions**:
- Single-user environment
- Trusted internal network
- No sensitive data

**Minimal Security**:
- CORS configuration for frontend
- Input validation via Pydantic
- Rate limiting (basic)
- Request size limits

```python
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/requests")
@limiter.limit("10/minute")
async def create_request(request: Request, body: CreateRequestRequest):
    # ...
```

### 8.2 Production Enhancements

**Authentication**:
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Verify JWT token
    if not is_valid_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return get_user_from_token(token)

@app.post("/api/v1/requests")
async def create_request(
    body: CreateRequestRequest,
    user = Depends(verify_token)
):
    # ...
```

**Input Sanitization**:
- Limit query length (e.g., 500 chars)
- Sanitize file uploads
- Validate numeric ranges

---

## 9. Implementation Plan

### Phase 1: Core API (Week 1)

**Day 1-2**: Setup and Basic Endpoints
- [ ] Create FastAPI project structure
- [ ] Setup MongoDB connection pooling
- [ ] Implement `POST /api/v1/requests`
- [ ] Implement `GET /api/v1/requests/{id}`
- [ ] Basic error handling

**Day 3-4**: Agent Integration
- [ ] Integrate LangGraph agent orchestrator
- [ ] Add request → agent workflow pipeline
- [ ] Store request state in MongoDB
- [ ] Implement agent trace logging

**Day 5**: Testing and Documentation
- [ ] Write integration tests
- [ ] Generate OpenAPI documentation
- [ ] Deploy locally and test end-to-end

### Phase 2: Real-time and Queries (Week 2)

**Day 1-2**: SSE Implementation
- [ ] Implement event bus
- [ ] Add agent event publishing
- [ ] Implement `GET /api/v1/requests/{id}/stream`
- [ ] Test with frontend

**Day 3-4**: Run and Sweep Endpoints
- [ ] Implement `GET /api/v1/runs`
- [ ] Implement `POST /api/v1/runs/compare`
- [ ] Implement `POST /api/v1/sweeps`
- [ ] Implement `GET /api/v1/sweeps/{id}`

**Day 5**: Polish
- [ ] Add pagination
- [ ] Optimize queries
- [ ] Add caching where appropriate

### Phase 3: Production Ready (Week 3)

- [ ] Add authentication
- [ ] Implement proper logging
- [ ] Add monitoring (Prometheus metrics)
- [ ] Deploy to cloud (Azure App Service)
- [ ] Load testing

---

## 10. Testing Strategy

### 10.1 Unit Tests

```python
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_create_request():
    response = client.post("/api/v1/requests", json={
        "query": "Simulate PWR pin with 4.5% enriched UO2"
    })
    assert response.status_code == 202
    data = response.json()
    assert "request_id" in data
    assert data["status"] == "queued"

def test_get_request_status():
    # Create request
    create_response = client.post("/api/v1/requests", json={
        "query": "Test query"
    })
    request_id = create_response.json()["request_id"]
    
    # Get status
    status_response = client.get(f"/api/v1/requests/{request_id}")
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["request_id"] == request_id

def test_invalid_request():
    response = client.post("/api/v1/requests", json={
        "query": ""  # Empty query
    })
    assert response.status_code == 400
```

### 10.2 Integration Tests

```python
import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.mark.asyncio
async def test_full_request_workflow():
    # Submit request
    response = client.post("/api/v1/requests", json={
        "query": "Simulate PWR pin with 3.5% enriched UO2"
    })
    request_id = response.json()["request_id"]
    
    # Wait for completion (with timeout)
    for _ in range(30):  # 30 seconds max
        status = client.get(f"/api/v1/requests/{request_id}").json()
        if status["status"] == "completed":
            break
        await asyncio.sleep(1)
    
    # Verify results
    assert status["status"] == "completed"
    assert status["results"] is not None
    assert "keff" in status["results"]
    assert status["analysis"] is not None
```

### 10.3 Load Testing

```python
# locustfile.py
from locust import HttpUser, task, between

class AONPUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def create_request(self):
        self.client.post("/api/v1/requests", json={
            "query": "Simulate PWR pin with 4.5% enriched UO2"
        })
    
    @task(3)
    def query_runs(self):
        self.client.get("/api/v1/runs?limit=10")
```

Run with:
```bash
locust -f locustfile.py --host=http://localhost:8000
```

---

## 11. Future Enhancements

### 11.1 Short-term (Next 3 Months)

1. **Visualization Endpoints**
   - `GET /api/v1/sweeps/{id}/chart` → PNG/SVG
   - `GET /api/v1/runs/{id}/plot` → Interactive Plotly JSON

2. **Batch Operations**
   - Submit multiple requests at once
   - Bulk export to CSV/Parquet

3. **Advanced Queries**
   - GraphQL endpoint for flexible queries
   - Full-text search on analyses

4. **Notifications**
   - Email/Slack when long-running requests complete
   - Webhook callbacks

### 11.2 Long-term (6+ Months)

1. **Multi-tenancy**
   - User workspaces
   - Team collaboration

2. **Scheduling**
   - Cron-like scheduled sweeps
   - Recurring experiments

3. **ML Integration**
   - Suggest optimal parameters
   - Anomaly detection in results

4. **Distributed Execution**
   - Parallel sweep execution
   - HPC cluster integration

---

## Appendices

### A. Sample FastAPI Application Structure

```
api/
├── main.py                 # FastAPI app entry point
├── config.py               # Configuration (env vars, MongoDB URI)
├── dependencies.py         # Dependency injection (DB, auth)
├── models/
│   ├── requests.py         # Request Pydantic models
│   ├── runs.py             # Run Pydantic models
│   └── sweeps.py           # Sweep Pydantic models
├── routes/
│   ├── requests.py         # Request endpoints
│   ├── runs.py             # Run endpoints
│   ├── sweeps.py           # Sweep endpoints
│   └── statistics.py       # Statistics endpoints
├── services/
│   ├── agent_service.py    # Agent orchestration logic
│   ├── db_service.py       # MongoDB operations
│   └── event_bus.py        # SSE event pub/sub
├── middleware/
│   ├── error_handler.py    # Global error handling
│   └── logging.py          # Request logging
└── tests/
    ├── test_requests.py
    ├── test_runs.py
    └── test_integration.py
```

### B. Environment Variables

```bash
# .env file
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/aonp
FIREWORKS_API_KEY=your_fireworks_key
VOYAGE_API_KEY=your_voyage_key
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### C. OpenAPI Documentation

FastAPI auto-generates:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### D. Deployment Checklist

```
□ Environment variables configured
□ MongoDB Atlas connection tested
□ CORS origins set correctly
□ Rate limiting enabled
□ Error handling tested
□ Logging configured
□ Health check endpoint working
□ API documentation accessible
□ SSL/TLS certificate (production)
□ Monitoring/alerting setup
```

---

## Questions for Review

1. **Real-time Updates**: Should we use SSE or WebSockets? SSE is simpler for one-way communication.

2. **Authentication**: Do we need it for MVP, or can we defer to production phase?

3. **Database Schema**: Are the existing MongoDB collections (studies, runs, summaries) sufficient, or do we need a `requests` collection?

4. **Pagination**: What's the default page size for queries? Suggested: 20 items.

5. **File Uploads**: Will users upload geometry files via API, or only through agent tools?

6. **Caching**: Should we cache query results? If so, what's the invalidation strategy?

7. **Async Execution**: Should long-running requests use background tasks (Celery) or FastAPI BackgroundTasks?

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-10 | AI Assistant | Initial draft |

---

**Next Steps**:
1. Review this document with the team
2. Clarify open questions
3. Prioritize Phase 1 tasks
4. Create GitHub issues/tickets
5. Begin implementation



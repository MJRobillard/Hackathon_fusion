"""
AONP Multi-Agent API Server
FastAPI implementation for frontend integration
"""

import os
import sys
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4
import asyncio

from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Import existing AONP components
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from aonp_agents import run_aonp_agent, create_aonp_graph, AONPAgentState

# Import terminal streaming from parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from terminal_streamer import terminal_broadcaster, install_terminal_interceptor


load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

MONGODB_URI = os.getenv("MONGO_URI")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class CreateRequestRequest(BaseModel):
    """Request to create a new simulation request"""
    query: str = Field(..., min_length=1, max_length=500, description="Natural language simulation request")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class CreateRequestResponse(BaseModel):
    """Response after creating a request"""
    request_id: str
    status: str
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
    status: str
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
    runs: List[Dict[str, Any]]

class Statistics(BaseModel):
    """Database and system statistics"""
    total_studies: int
    total_runs: int
    completed_runs: int
    total_requests: int
    recent_runs: List[Dict[str, Any]]

class HealthCheck(BaseModel):
    """System health status"""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: Dict[str, Any]

# ============================================================================
# EVENT BUS FOR SSE
# ============================================================================

class AgentEventBus:
    """Simple pub/sub for agent events"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
    
    def subscribe(self, request_id: str) -> asyncio.Queue:
        """Subscribe to events for a request"""
        queue = asyncio.Queue()
        if request_id not in self._subscribers:
            self._subscribers[request_id] = []
        self._subscribers[request_id].append(queue)
        return queue
    
    async def publish(self, request_id: str, event: dict):
        """Publish event to all subscribers"""
        if request_id in self._subscribers:
            for queue in self._subscribers[request_id]:
                await queue.put(event)
    
    async def complete(self, request_id: str):
        """Signal completion (sends None sentinel)"""
        if request_id in self._subscribers:
            for queue in self._subscribers[request_id]:
                await queue.put(None)
    
    def unsubscribe(self, request_id: str, queue: asyncio.Queue):
        """Remove subscriber"""
        if request_id in self._subscribers:
            self._subscribers[request_id].remove(queue)
            if not self._subscribers[request_id]:
                del self._subscribers[request_id]

event_bus = AgentEventBus()

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

class Database:
    client: AsyncIOMotorClient = None
    
db = Database()

async def get_database():
    """Dependency for database access"""
    return db.client["aonp"]

async def startup_db():
    """Initialize MongoDB connection"""
    db.client = AsyncIOMotorClient(MONGODB_URI)
    # Test connection
    await db.client.admin.command('ping')
    print(f"✅ Connected to MongoDB")

async def shutdown_db():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        print("✅ Closed MongoDB connection")

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="AONP Multi-Agent API",
    description="API for nuclear simulation multi-agent system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    await startup_db()
    
    # Initialize terminal streaming
    loop = asyncio.get_event_loop()
    terminal_broadcaster.set_event_loop(loop)
    install_terminal_interceptor()
    print("🚀 AONP Multi-Agent API Server Started")
    print("📡 Terminal streaming enabled - output being broadcast")

@app.on_event("shutdown")
async def shutdown_event():
    await shutdown_db()

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    print(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    )

# ============================================================================
# AGENT EXECUTION (Background Task)
# ============================================================================

async def execute_agent_workflow(request_id: str, query: str, mongodb):
    """Execute agent workflow and update database"""
    try:
        # Publish start event
        await event_bus.publish(request_id, {
            "type": "request_start",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Update status to processing
        await mongodb.requests.update_one(
            {"request_id": request_id},
            {"$set": {"status": "processing"}}
        )
        
        # Create agent graph
        app_graph = create_aonp_graph()
        
        # Initial state
        initial_state = AONPAgentState(
            messages=[],
            user_request=query,
            intent=None,
            study_spec=None,
            sweep_config=None,
            run_ids=None,
            results=None,
            analysis=None,
            suggestion=None,
            next_action="classify"
        )
        
        # Execute agent workflow
        # Note: This is synchronous - ideally we'd use async agents
        final_state = app_graph.invoke(initial_state)
        
        # Extract results
        results = {
            "intent": final_state.get("intent"),
            "run_ids": final_state.get("run_ids"),
            "results": final_state.get("results"),
            "analysis": final_state.get("analysis"),
            "suggestion": final_state.get("suggestion")
        }
        
        # Parse suggestions into list
        suggestions = []
        if final_state.get("suggestion"):
            # Simple parsing - split by numbers
            suggestion_text = final_state.get("suggestion")
            import re
            suggestions = re.findall(r'\d+\.\s*(.+?)(?=\d+\.|$)', suggestion_text, re.DOTALL)
            suggestions = [s.strip() for s in suggestions if s.strip()]
        
        # Update database
        completed_at = datetime.now(timezone.utc)
        created_at_doc = await mongodb.requests.find_one({"request_id": request_id})
        created_at = created_at_doc["created_at"]
        duration = (completed_at - created_at).total_seconds()
        
        await mongodb.requests.update_one(
            {"request_id": request_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": completed_at,
                    "duration_seconds": duration,
                    "intent": results["intent"],
                    "results": results["results"],
                    "analysis": results["analysis"],
                    "suggestions": suggestions
                }
            }
        )
        
        # Publish completion event
        await event_bus.publish(request_id, {
            "type": "request_complete",
            "status": "completed",
            "timestamp": completed_at.isoformat()
        })
        
    except Exception as e:
        print(f"❌ Agent execution failed: {e}")
        
        # Update status to failed
        await mongodb.requests.update_one(
            {"request_id": request_id},
            {
                "$set": {
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # Publish error event
        await event_bus.publish(request_id, {
            "type": "request_error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    finally:
        # Signal completion to all subscribers
        await event_bus.complete(request_id)

# ============================================================================
# ROUTES: REQUEST MANAGEMENT
# ============================================================================

@app.post("/api/v1/requests", response_model=CreateRequestResponse, status_code=202)
async def create_request(
    body: CreateRequestRequest,
    background_tasks: BackgroundTasks,
    mongodb = Depends(get_database)
):
    """
    Submit a natural language simulation request to the multi-agent system.
    
    The request is processed asynchronously by multiple agents:
    1. Intent Classifier
    2. Study Planner / Sweep Planner
    3. Executor
    4. Analyzer
    5. Suggester
    
    Use the returned request_id to check status or stream progress.
    """
    # Generate request ID
    request_id = f"req_{uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc)
    
    # Store in database
    request_doc = {
        "request_id": request_id,
        "query": body.query,
        "status": "queued",
        "created_at": created_at,
        "options": body.options,
        "metadata": body.metadata,
        "intent": None,
        "results": None,
        "analysis": None,
        "suggestions": None,
        "error": None
    }
    
    await mongodb.requests.insert_one(request_doc)
    
    # Start agent execution in background
    background_tasks.add_task(execute_agent_workflow, request_id, body.query, mongodb)
    
    # Prepare response
    stream_url = None
    if body.options.get("stream"):
        stream_url = f"/api/v1/requests/{request_id}/stream"
    
    return CreateRequestResponse(
        request_id=request_id,
        status="queued",
        created_at=created_at,
        estimated_duration_seconds=15,
        stream_url=stream_url
    )


@app.get("/api/v1/requests/{request_id}", response_model=RequestStatus)
async def get_request_status(
    request_id: str,
    mongodb = Depends(get_database)
):
    """
    Get the current status and results of a request.
    
    Status values:
    - queued: Waiting to start
    - processing: Agent workflow in progress
    - completed: Finished successfully
    - failed: Error occurred
    """
    # Find request in database
    request_doc = await mongodb.requests.find_one({"request_id": request_id})
    
    if not request_doc:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
    
    # Remove MongoDB _id
    request_doc.pop("_id", None)
    request_doc.pop("options", None)
    request_doc.pop("metadata", None)
    
    # Calculate duration if completed
    duration_seconds = None
    if request_doc.get("completed_at") and request_doc.get("created_at"):
        duration_seconds = (request_doc["completed_at"] - request_doc["created_at"]).total_seconds()
    
    return RequestStatus(
        request_id=request_doc["request_id"],
        status=request_doc["status"],
        query=request_doc["query"],
        intent=request_doc.get("intent"),
        created_at=request_doc["created_at"],
        completed_at=request_doc.get("completed_at"),
        duration_seconds=duration_seconds,
        agent_trace=[],  # TODO: Implement agent trace logging
        results=request_doc.get("results"),
        analysis=request_doc.get("analysis"),
        suggestions=request_doc.get("suggestions"),
        error=request_doc.get("error")
    )


@app.get("/api/v1/requests/{request_id}/stream")
async def stream_request_progress(request_id: str):
    """
    Server-Sent Events stream for real-time agent progress.
    
    Events:
    - agent_start: Agent begins execution
    - agent_progress: Agent status update
    - agent_complete: Agent finished
    - request_complete: Full workflow finished
    - request_error: Error occurred
    
    Frontend usage:
    ```javascript
    const eventSource = new EventSource('/api/v1/requests/{id}/stream');
    eventSource.addEventListener('agent_start', (e) => {
      const data = JSON.parse(e.data);
      console.log(`Agent ${data.agent} started`);
    });
    ```
    """
    async def event_generator():
        # Subscribe to events for this request
        queue = event_bus.subscribe(request_id)
        
        try:
            while True:
                # Wait for next event (or timeout after 30 seconds)
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ": keepalive\n\n"
                    continue
                
                if event is None:  # Sentinel for completion
                    break
                
                # Format as SSE
                import json
                yield f"event: {event['type']}\n"
                yield f"data: {json.dumps(event)}\n\n"
        
        finally:
            event_bus.unsubscribe(request_id, queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

# ============================================================================
# ROUTES: RUN MANAGEMENT
# ============================================================================

@app.get("/api/v1/runs", response_model=RunQueryResponse)
async def query_runs(
    geometry: Optional[str] = None,
    enrichment_min: Optional[float] = None,
    enrichment_max: Optional[float] = None,
    keff_min: Optional[float] = None,
    keff_max: Optional[float] = None,
    limit: int = 20,
    offset: int = 0,
    mongodb = Depends(get_database)
):
    """
    Query and search simulation runs.
    
    Supports filtering by:
    - geometry: Filter by geometry type
    - enrichment_min/max: Filter by enrichment percentage
    - keff_min/max: Filter by keff value
    
    Returns paginated results.
    """
    # Build MongoDB filter
    filter_query = {}
    
    if geometry:
        filter_query["spec.geometry"] = {"$regex": geometry, "$options": "i"}
    if enrichment_min is not None:
        filter_query.setdefault("spec.enrichment_pct", {})["$gte"] = enrichment_min
    if enrichment_max is not None:
        filter_query.setdefault("spec.enrichment_pct", {})["$lte"] = enrichment_max
    if keff_min is not None:
        filter_query.setdefault("keff", {})["$gte"] = keff_min
    if keff_max is not None:
        filter_query.setdefault("keff", {})["$lte"] = keff_max
    
    # Get total count
    total = await mongodb.summaries.count_documents(filter_query)
    
    # Query with pagination
    cursor = mongodb.summaries.find(filter_query).sort("created_at", -1).skip(offset).limit(limit)
    results = await cursor.to_list(length=limit)
    
    # Format results
    runs = []
    for r in results:
        runs.append(RunSummary(
            run_id=r["run_id"],
            spec_hash=r["spec_hash"],
            geometry=r["spec"].get("geometry", "unknown"),
            enrichment_pct=r["spec"].get("enrichment_pct"),
            temperature_K=r["spec"].get("temperature_K"),
            keff=r["keff"],
            keff_std=r["keff_std"],
            status=r["status"],
            created_at=r["created_at"]
        ))
    
    return RunQueryResponse(
        total=total,
        limit=limit,
        offset=offset,
        runs=runs
    )


@app.post("/api/v1/runs/compare", response_model=CompareRunsResponse)
async def compare_runs(
    body: CompareRunsRequest,
    mongodb = Depends(get_database)
):
    """
    Compare multiple simulation runs.
    
    Returns statistical comparison including:
    - keff values for each run
    - Mean, min, max keff
    - Standard deviation
    """
    # Import compare_runs tool
    from agent_tools import compare_runs as compare_runs_tool
    
    # Call existing tool
    comparison = compare_runs_tool(body.run_ids)
    
    if "error" in comparison:
        raise HTTPException(status_code=404, detail=comparison["error"])
    
    return CompareRunsResponse(
        num_runs=comparison["num_runs"],
        keff_values=comparison["keff_values"],
        keff_mean=comparison["keff_mean"],
        keff_min=comparison["keff_min"],
        keff_max=comparison["keff_max"],
        runs=comparison["runs"]
    )

# ============================================================================
# ROUTES: STATISTICS
# ============================================================================

@app.get("/api/v1/statistics", response_model=Statistics)
async def get_statistics(mongodb = Depends(get_database)):
    """
    Get database statistics and system status.
    
    Returns:
    - Total studies, runs, requests
    - Completion statistics
    - Recent runs
    """
    total_studies = await mongodb.studies.count_documents({})
    total_runs = await mongodb.runs.count_documents({})
    completed_runs = await mongodb.runs.count_documents({"status": "completed"})
    total_requests = await mongodb.requests.count_documents({})
    
    # Get recent runs
    cursor = mongodb.summaries.find().sort("created_at", -1).limit(5)
    recent_runs_docs = await cursor.to_list(length=5)
    
    recent_runs = [
        {
            "run_id": r["run_id"],
            "keff": r["keff"],
            "geometry": r["spec"].get("geometry", "unknown"),
            "created_at": r["created_at"].isoformat()
        }
        for r in recent_runs_docs
    ]
    
    return Statistics(
        total_studies=total_studies,
        total_runs=total_runs,
        completed_runs=completed_runs,
        total_requests=total_requests,
        recent_runs=recent_runs
    )


@app.get("/api/v1/terminal/stream")
async def stream_terminal_output():
    """
    Stream ALL backend terminal output in real-time (stdout + stderr).
    
    Captures everything including agent execution, OpenMC output, API logs, etc.
    
    Returns:
        SSE stream of all terminal output
    """
    async def event_generator():
        """Generate SSE events from terminal output."""
        queue = terminal_broadcaster.subscribe()
        
        try:
            # Send initial connection message
            init_msg = {
                'timestamp': datetime.utcnow().isoformat(),
                'stream': 'system',
                'content': '[Connected to terminal stream]\n'
            }
            yield f"data: {json.dumps(init_msg)}\n\n"
            
            while True:
                try:
                    # Wait for next event (30 second timeout for keepalive)
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
                    
        except asyncio.CancelledError:
            pass
        finally:
            terminal_broadcaster.unsubscribe(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/v1/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Checks:
    - API server status
    - MongoDB connection
    - LLM API availability
    """
    # Check MongoDB
    mongodb_status = "connected"
    try:
        await db.client.admin.command('ping')
    except Exception:
        mongodb_status = "disconnected"
    
    # Check Fireworks API
    fireworks_status = "available" if os.getenv("FIREWORKS") else "missing_key"
    
    # Overall status
    status = "healthy"
    if mongodb_status != "connected":
        status = "unhealthy"
    elif fireworks_status != "available":
        status = "degraded"
    
    return HealthCheck(
        status=status,
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        services={
            "mongodb": mongodb_status,
            "fireworks_api": fireworks_status,
            "openmc": "ready"
        }
    )

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 80)
    print("AONP MULTI-AGENT API SERVER")
    print("=" * 80)
    print(f"Server: http://{API_HOST}:{API_PORT}")
    print(f"Docs: http://{API_HOST}:{API_PORT}/docs")
    print(f"ReDoc: http://{API_HOST}:{API_PORT}/redoc")
    print("=" * 80)
    
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )


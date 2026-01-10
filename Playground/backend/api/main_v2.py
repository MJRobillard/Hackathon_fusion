"""
AONP Multi-Agent API Server v2
Implements the architecture from plan.md with Router + Specialist Agents
"""

import os
import sys
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

# Import multi-agent system
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from multi_agent_system import MultiAgentOrchestrator
from agent_tools import compare_runs as compare_runs_tool

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

class QueryRequest(BaseModel):
    """Natural language query request"""
    query: str = Field(..., min_length=1, max_length=500)
    use_llm: bool = Field(default=False, description="Use LLM for routing (slower but more accurate). False = fast keyword routing")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

class QueryResponse(BaseModel):
    """Query response"""
    query_id: str
    status: str
    assigned_agent: str
    estimated_duration: int
    stream_url: Optional[str] = None

class QueryStatusResponse(BaseModel):
    """Query status response"""
    query_id: str
    status: str
    query: str
    agent_path: List[str]
    tool_calls: List[str]
    results: Optional[Dict[str, Any]] = None
    interpretation: Optional[str] = None
    cost: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class StudySubmitRequest(BaseModel):
    """Direct study submission (bypass agents)"""
    geometry: str
    materials: List[str]
    enrichment_pct: Optional[float] = None
    temperature_K: Optional[float] = None
    particles: int = 10000
    batches: int = 50

class SweepRequest(BaseModel):
    """Direct sweep request (bypass agents)"""
    base_spec: Dict[str, Any]
    param_name: str
    param_values: List[Any]

class CompareRunsRequest(BaseModel):
    """Compare runs request"""
    run_ids: List[str] = Field(..., min_items=2)

class RunQueryParams(BaseModel):
    """Run query parameters"""
    geometry: Optional[str] = None
    enrichment_min: Optional[float] = None
    enrichment_max: Optional[float] = None
    keff_min: Optional[float] = None
    keff_max: Optional[float] = None
    limit: int = 20
    offset: int = 0

class RunSummary(BaseModel):
    """Run summary"""
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
    """Run query response"""
    total: int
    limit: int
    offset: int
    runs: List[RunSummary]

class CompareRunsResponse(BaseModel):
    """Compare runs response"""
    num_runs: int
    keff_values: List[float]
    keff_mean: float
    keff_min: float
    keff_max: float
    runs: List[Dict[str, Any]]

class Statistics(BaseModel):
    """Statistics response"""
    total_studies: int
    total_runs: int
    completed_runs: int
    total_queries: int
    recent_runs: List[Dict[str, Any]]

class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]

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
    await db.client.admin.command('ping')
    print(f"✅ Connected to MongoDB")

async def shutdown_db():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        print("✅ Closed MongoDB connection")

# ============================================================================
# EVENT BUS FOR SSE
# ============================================================================

class EventBus:
    """Simple pub/sub for query events"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
    
    def subscribe(self, query_id: str) -> asyncio.Queue:
        """Subscribe to events for a query"""
        queue = asyncio.Queue()
        if query_id not in self._subscribers:
            self._subscribers[query_id] = []
        self._subscribers[query_id].append(queue)
        return queue
    
    async def publish(self, query_id: str, event: dict):
        """Publish event to all subscribers"""
        if query_id in self._subscribers:
            for queue in self._subscribers[query_id]:
                await queue.put(event)
    
    async def complete(self, query_id: str):
        """Signal completion"""
        if query_id in self._subscribers:
            for queue in self._subscribers[query_id]:
                await queue.put(None)
    
    def unsubscribe(self, query_id: str, queue: asyncio.Queue):
        """Remove subscriber"""
        if query_id in self._subscribers:
            self._subscribers[query_id].remove(queue)
            if not self._subscribers[query_id]:
                del self._subscribers[query_id]

event_bus = EventBus()

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="AONP Multi-Agent API v2",
    description="Router + Specialist Agents for nuclear simulation",
    version="2.0.0",
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

@app.on_event("shutdown")
async def shutdown_event():
    await shutdown_db()

# ============================================================================
# BACKGROUND TASK: EXECUTE MULTI-AGENT QUERY
# ============================================================================

async def execute_multi_agent_query(query_id: str, query: str, mongodb, use_llm: bool = True):
    """Execute multi-agent workflow in background"""
    try:
        # Publish start event
        await event_bus.publish(query_id, {
            "type": "query_start",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Update status
        await mongodb.queries.update_one(
            {"query_id": query_id},
            {"$set": {"status": "processing"}}
        )
        
        # Publish routing event
        await event_bus.publish(query_id, {
            "type": "routing",
            "message": "Analyzing query intent...",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Create orchestrator and process query
        from multi_agent_system import MultiAgentOrchestrator, RouterAgent
        orchestrator = MultiAgentOrchestrator()
        # Override router with configured LLM setting
        orchestrator.router = RouterAgent(use_llm=use_llm)
        
        # Run in thread pool since it's synchronous
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, orchestrator.process_query, query)
        
        # Extract results
        routing = result.get("routing", {})
        agent_results = result.get("results", {})
        
        # Update database
        completed_at = datetime.now(timezone.utc)
        created_at_doc = await mongodb.queries.find_one({"query_id": query_id})
        created_at = created_at_doc["created_at"]
        duration = (completed_at - created_at).total_seconds()
        
        await mongodb.queries.update_one(
            {"query_id": query_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": completed_at,
                    "duration_seconds": duration,
                    "assigned_agent": routing.get("agent"),
                    "intent": routing.get("intent"),
                    "results": agent_results,
                    "agent_path": ["router", routing.get("agent")],
                    "tool_calls": list(agent_results.keys()) if isinstance(agent_results, dict) else []
                }
            }
        )
        
        # Publish completion
        await event_bus.publish(query_id, {
            "type": "query_complete",
            "status": "completed",
            "timestamp": completed_at.isoformat()
        })
        
    except Exception as e:
        print(f"❌ Query execution failed: {e}")
        import traceback
        traceback.print_exc()
        
        await mongodb.queries.update_one(
            {"query_id": query_id},
            {
                "$set": {
                    "status": "failed",
                    "error": str(e),
                    "completed_at": datetime.now(timezone.utc)
                }
            }
        )
        
        await event_bus.publish(query_id, {
            "type": "query_error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    finally:
        await event_bus.complete(query_id)

# ============================================================================
# ROUTES: NATURAL LANGUAGE QUERY (MAIN ENDPOINT)
# ============================================================================

@app.post("/api/v1/query", response_model=QueryResponse, status_code=202)
async def submit_query(
    body: QueryRequest,
    background_tasks: BackgroundTasks,
    mongodb = Depends(get_database)
):
    """
    Submit natural language query to multi-agent system
    
    The query is routed to the appropriate specialist agent:
    - Studies Agent: Single simulations
    - Sweep Agent: Parameter sweeps
    - Query Agent: Database searches
    - Analysis Agent: Result comparisons
    """
    query_id = f"q_{uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc)
    
    # Store in database
    query_doc = {
        "query_id": query_id,
        "query": body.query,
        "status": "queued",
        "created_at": created_at,
        "options": body.options
    }
    
    await mongodb.queries.insert_one(query_doc)
    
    # Start execution in background
    background_tasks.add_task(execute_multi_agent_query, query_id, body.query, mongodb, body.use_llm)
    
    # Prepare response
    stream_url = None
    if body.options.get("stream"):
        stream_url = f"/api/v1/query/{query_id}/stream"
    
    return QueryResponse(
        query_id=query_id,
        status="queued",
        assigned_agent="routing",
        estimated_duration=30,
        stream_url=stream_url
    )


@app.get("/api/v1/query/{query_id}", response_model=QueryStatusResponse)
async def get_query_status(
    query_id: str,
    mongodb = Depends(get_database)
):
    """
    Get status and results of a query
    """
    query_doc = await mongodb.queries.find_one({"query_id": query_id})
    
    if not query_doc:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    
    query_doc.pop("_id", None)
    query_doc.pop("options", None)
    
    return QueryStatusResponse(
        query_id=query_doc["query_id"],
        status=query_doc["status"],
        query=query_doc["query"],
        agent_path=query_doc.get("agent_path", []),
        tool_calls=query_doc.get("tool_calls", []),
        results=query_doc.get("results"),
        interpretation=query_doc.get("interpretation"),
        cost=query_doc.get("cost"),
        error=query_doc.get("error")
    )


@app.get("/api/v1/query/{query_id}/stream")
async def stream_query_progress(query_id: str):
    """
    Server-Sent Events stream for query progress
    """
    async def event_generator():
        queue = event_bus.subscribe(query_id)
        
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                
                if event is None:
                    break
                
                import json
                yield f"event: {event['type']}\n"
                yield f"data: {json.dumps(event)}\n\n"
        
        finally:
            event_bus.unsubscribe(query_id, queue)
    
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
# ROUTES: AGENT-SPECIFIC ENDPOINTS
# ============================================================================

@app.post("/api/v1/agents/studies")
async def run_studies_agent(body: QueryRequest):
    """
    Run Studies Agent directly (for single simulations)
    """
    from multi_agent_system import StudiesAgent
    
    agent = StudiesAgent()
    result = agent.execute({"query": body.query})
    
    return result


@app.post("/api/v1/agents/sweep")
async def run_sweep_agent(body: QueryRequest):
    """
    Run Sweep Agent directly (for parameter sweeps)
    """
    from multi_agent_system import SweepAgent
    
    agent = SweepAgent()
    result = agent.execute({"query": body.query})
    
    return result


@app.post("/api/v1/agents/query")
async def run_query_agent(body: QueryRequest):
    """
    Run Query Agent directly (for database searches)
    """
    from multi_agent_system import QueryAgent
    
    agent = QueryAgent()
    result = agent.execute({"query": body.query})
    
    return result


@app.post("/api/v1/agents/analysis")
async def run_analysis_agent(body: QueryRequest):
    """
    Run Analysis Agent directly (for result comparisons)
    """
    from multi_agent_system import AnalysisAgent
    
    agent = AnalysisAgent()
    result = agent.execute({"query": body.query})
    
    return result


@app.post("/api/v1/router")
async def route_query(body: QueryRequest):
    """
    Test router only (doesn't execute, just shows which agent would be selected)
    """
    from multi_agent_system import RouterAgent
    
    router = RouterAgent(use_llm=body.use_llm)
    result = router.route_query(body.query)
    
    return result

# ============================================================================
# ROUTES: DIRECT TOOL ACCESS (BYPASS AGENTS)
# ============================================================================

@app.post("/api/v1/studies")
async def submit_study_direct(body: StudySubmitRequest):
    """
    Direct study submission (bypasses agents for speed)
    """
    from agent_tools import submit_study
    
    spec = body.dict()
    result = submit_study(spec)
    
    return result


@app.get("/api/v1/studies/{run_id}")
async def get_study_by_id(run_id: str):
    """
    Get specific study by ID
    """
    from agent_tools import get_run_by_id
    
    result = get_run_by_id(run_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    return result


@app.post("/api/v1/sweeps")
async def submit_sweep_direct(body: SweepRequest):
    """
    Direct sweep submission (bypasses agents)
    """
    from agent_tools import generate_sweep
    
    run_ids = generate_sweep(
        base_spec=body.base_spec,
        param_name=body.param_name,
        param_values=body.param_values
    )
    
    return {"run_ids": run_ids}


@app.get("/api/v1/runs")
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
    Query simulation runs with filters
    """
    # Build filter
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
async def compare_runs(body: CompareRunsRequest):
    """
    Compare multiple runs
    """
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
# ROUTES: STATISTICS & HEALTH
# ============================================================================

@app.get("/api/v1/statistics", response_model=Statistics)
async def get_statistics(mongodb = Depends(get_database)):
    """
    Get database statistics
    """
    total_studies = await mongodb.studies.count_documents({})
    total_runs = await mongodb.runs.count_documents({})
    completed_runs = await mongodb.runs.count_documents({"status": "completed"})
    total_queries = await mongodb.queries.count_documents({})
    
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
        total_queries=total_queries,
        recent_runs=recent_runs
    )


@app.get("/api/v1/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint
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
        version="2.0.0",
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
    print("AONP MULTI-AGENT API SERVER V2")
    print("=" * 80)
    print(f"Server: http://{API_HOST}:{API_PORT}")
    print(f"Docs: http://{API_HOST}:{API_PORT}/docs")
    print(f"ReDoc: http://{API_HOST}:{API_PORT}/redoc")
    print("=" * 80)
    
    uvicorn.run(
        "main_v2:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )


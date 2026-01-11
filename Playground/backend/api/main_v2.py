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
import json
import random
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import httpx

# Ensure imports work when running this file directly:
# - add Playground/backend (for multi_agent_system, openmc_adapter, etc.)
# - add repo root (for the `aonp` package)
_BACKEND_DIR = Path(__file__).resolve().parent.parent  # Playground/backend
_REPO_ROOT = _BACKEND_DIR.parent.parent  # repo root
sys.path.insert(0, str(_BACKEND_DIR))
sys.path.insert(0, str(_REPO_ROOT))
from agent_tools import compare_runs as compare_runs_tool
from terminal_streamer import terminal_broadcaster, install_terminal_interceptor
from orchestration_config import get_orchestration_config, patch_orchestration_config, OrchestrationConfig
from graphs.query_graph import build_query_graph, QueryGraphContext

# Compile once (graph is stateless; per-run context is passed in state)
QUERY_GRAPH = build_query_graph()

# Import RAG endpoints
try:
    from rag_endpoints import rag_router, init_rag_system
    RAG_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  RAG system not available: {e}")
    RAG_AVAILABLE = False

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

class BatchConvergenceData(BaseModel):
    """Batch convergence visualization data"""
    batch_numbers: List[int]
    batch_keff: List[float]
    entropy: Optional[List[float]] = None
    n_inactive: int
    final_keff: float
    final_keff_std: float

class VisualizationResponse(BaseModel):
    """Visualization response"""
    type: str  # "batch_convergence", "parameter_sweep", "comparison"
    data: Dict[str, Any]

class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]


class OrchestrationConfigPatch(BaseModel):
    """Partial patch for OrchestrationConfig (nested dict)."""
    tool_prompts: Optional[Dict[str, Any]] = None
    convergence: Optional[Dict[str, Any]] = None


# ============================================================================
# OPENMC (single-backend) - run + stream from THIS server (no :8001 required)
# ============================================================================

RUNS_DIR = Path(os.getenv("OPENMC_RUNS_DIR", "runs_openmc")).resolve()


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

# Include RAG router if available
if RAG_AVAILABLE:
    app.include_router(rag_router)
    print("✅ RAG Copilot endpoints registered")

# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    await startup_db()

    # Initialize global terminal streaming (stdout/stderr -> SSE)
    loop = asyncio.get_event_loop()
    terminal_broadcaster.set_event_loop(loop)
    install_terminal_interceptor()
    print("📡 Terminal streaming enabled at /api/v1/terminal/stream")
    
    # Initialize RAG system if available
    if RAG_AVAILABLE:
        try:
            init_rag_system(mongo_uri=MONGODB_URI)
        except Exception as e:
            print(f"⚠️  RAG system initialization failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    await shutdown_db()

# ============================================================================
# TERMINAL STREAMING (SSE)
# ============================================================================


@app.get("/api/v1/terminal/stream")
async def stream_terminal_output():
    """
    Stream ALL backend terminal output in real-time (stdout + stderr).
    """

    async def event_generator():
        queue = terminal_broadcaster.subscribe()
        try:
            init_msg = {
                "timestamp": datetime.utcnow().isoformat(),
                "stream": "system",
                "content": "[Connected to terminal stream]\n",
            }
            yield f"data: {json.dumps(init_msg)}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
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
        },
    )


# ============================================================================
# ORCHESTRATION CONFIG (runtime-tunable prompts + convergence defaults)
# ============================================================================


@app.get("/api/v1/orchestration/config", response_model=OrchestrationConfig)
async def get_config():
    return get_orchestration_config()


@app.patch("/api/v1/orchestration/config", response_model=OrchestrationConfig)
async def patch_config(body: OrchestrationConfigPatch):
    patch: Dict[str, Any] = {}
    if body.tool_prompts is not None:
        patch["tool_prompts"] = body.tool_prompts
    if body.convergence is not None:
        patch["convergence"] = body.convergence
    return patch_orchestration_config(patch)


# ============================================================================
# OPENMC (single-backend) - submit/status/query/stream from THIS server
# ============================================================================


class RunEventBus:
    """Pub/sub for OpenMC run streaming events (per run_id)."""

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(run_id, []).append(q)
        return q

    async def publish(self, run_id: str, event: Dict[str, Any]) -> None:
        for q in self._subscribers.get(run_id, []):
            await q.put(event)

    async def complete(self, run_id: str) -> None:
        for q in self._subscribers.get(run_id, []):
            await q.put(None)

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        if run_id in self._subscribers:
            self._subscribers[run_id].remove(queue)
            if not self._subscribers[run_id]:
                del self._subscribers[run_id]


run_event_bus = RunEventBus()


class RunEventPublisher:
    """Thread-safe publisher for OpenMC run events."""

    def __init__(self, *, loop: asyncio.AbstractEventLoop, run_id: str):
        self.loop = loop
        self.run_id = run_id

    def _emit(self, event: Dict[str, Any]) -> None:
        asyncio.run_coroutine_threadsafe(run_event_bus.publish(self.run_id, event), self.loop)

    def openmc_log(self, content: str) -> None:
        self._emit(
            {
                "type": "openmc_log",
                "run_id": self.run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content": content,
            }
        )

    def tool_call(self, tool_name: str, message: str, args: Dict[str, Any]) -> None:
        self._emit(
            {
                "type": "tool_call",
                "run_id": self.run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "OpenMC Engine",
                "tool_name": tool_name,
                "message": message,
                "args": args,
            }
        )

    def tool_result(self, tool_name: str, result: Dict[str, Any]) -> None:
        self._emit(
            {
                "type": "tool_result",
                "run_id": self.run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "OpenMC Engine",
                "tool_name": tool_name,
                "message": f"{tool_name} completed",
                "result": result,
            }
        )

    def error(self, error: str) -> None:
        self._emit(
            {
                "type": "openmc_error",
                "run_id": self.run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": error,
            }
        )


def _stream_execute_openmc_local(spec_dict: Dict[str, Any], run_id: str, publisher: RunEventPublisher) -> Dict[str, Any]:
    """
    Synchronous worker that:
    - Creates an AONP bundle from simplified spec
    - Streams OpenMC stdout via StreamingSimulationRunner
    - Extracts keff from outputs
    """
    from openmc_adapter import OpenMCAdapter  # Playground/backend/openmc_adapter.py
    from aonp.core.bundler import create_run_bundle
    from aonp.core.extractor import extract_results
    from aonp.runner.streaming_runner import StreamingSimulationRunner

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    adapter = OpenMCAdapter(runs_dir=RUNS_DIR)

    publisher.tool_call(
        "translate_simple_to_openmc",
        "Translating simplified spec to full StudySpec",
        {"spec": spec_dict},
    )
    study = adapter.translate_simple_to_openmc(spec_dict, run_id)

    publisher.tool_call(
        "create_run_bundle",
        "Creating OpenMC XML inputs bundle",
        {"run_id": run_id},
    )
    run_dir, spec_hash = create_run_bundle(study=study, run_id=run_id, base_dir=RUNS_DIR)

    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    log_path = outputs_dir / "openmc_stdout.log"

    publisher.tool_call(
        "openmc.run",
        "Starting OpenMC run (streaming stdout)",
        {"run_id": run_id, "run_dir": str(run_dir)},
    )

    runner = StreamingSimulationRunner(run_dir)
    with open(log_path, "a", encoding="utf-8") as logf:
        for line in runner.stream_simulation():
            # stream_simulation yields raw stdout lines plus status lines
            logf.write(line if line.endswith("\n") else (line + "\n"))
            publisher.openmc_log(line)

    statepoints = sorted((run_dir / "outputs").glob("statepoint.*.h5"))
    if not statepoints:
        return {
            "status": "failed",
            "error": "No statepoint file found",
            "run_id": run_id,
            "spec_hash": spec_hash,
            "run_dir": str(run_dir),
            "keff": 0.0,
            "keff_std": 0.0,
            "runtime_seconds": 0.0,
        }

    results = extract_results(statepoints[-1])

    manifest_path = run_dir / "run_manifest.json"
    runtime_seconds = 0.0
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        runtime_seconds = float(manifest.get("runtime_seconds", 0.0) or 0.0)
    except Exception:
        runtime_seconds = 0.0

    return {
        "status": "completed",
        "run_id": run_id,
        "spec_hash": spec_hash,
        "run_dir": str(run_dir),
        "keff": float(results.get("keff", 0.0)),
        "keff_std": float(results.get("keff_std", 0.0)),
        "uncertainty_pcm": float(results.get("keff_uncertainty_pcm", 0.0)),
        "runtime_seconds": runtime_seconds,
    }


async def _execute_openmc_background(run_id: str, spec_dict: Dict[str, Any], mongodb) -> None:
    """
    Background task that runs OpenMC locally and updates mongodb.openmc_runs.
    """
    try:
        if mongodb is not None:
            await mongodb.openmc_runs.update_one(
                {"run_id": run_id},
                {"$set": {"status": "running", "started_at": datetime.now(timezone.utc)}},
            )

        loop = asyncio.get_event_loop()
        publisher = RunEventPublisher(loop=loop, run_id=run_id)

        result = await loop.run_in_executor(None, _stream_execute_openmc_local, spec_dict, run_id, publisher)

        if mongodb is not None:
            await mongodb.openmc_runs.update_one(
                {"run_id": run_id},
                {
                    "$set": {
                        "status": result.get("status"),
                        "keff": result.get("keff", 0.0),
                        "keff_std": result.get("keff_std", 0.0),
                        "uncertainty_pcm": result.get("uncertainty_pcm", 0.0),
                        "runtime_seconds": result.get("runtime_seconds", 0.0),
                        "run_dir": result.get("run_dir", ""),
                        "completed_at": datetime.now(timezone.utc),
                        "error": result.get("error"),
                        "spec": spec_dict,
                    }
                },
            )

            # Keep parity with existing compare/query flows: insert into summaries if completed
            if result.get("status") == "completed":
                await mongodb.summaries.insert_one(
                    {
                        "run_id": run_id,
                        "spec_hash": result.get("spec_hash"),
                        "keff": result.get("keff"),
                        "keff_std": result.get("keff_std"),
                        "status": result.get("status"),
                        "runtime_seconds": result.get("runtime_seconds"),
                        "created_at": datetime.now(timezone.utc),
                        "spec": spec_dict,
                    }
                )

        publisher.tool_result("openmc.run", {"summary": result.get("status"), **result})
        await run_event_bus.complete(run_id)

    except Exception as e:
        if mongodb is not None:
            await mongodb.openmc_runs.update_one(
                {"run_id": run_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.now(timezone.utc),
                    }
                },
            )
        await run_event_bus.publish(
            run_id,
            {
                "type": "openmc_error",
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            },
        )
        await run_event_bus.complete(run_id)


@app.post("/api/v1/openmc/simulations")
async def openmc_submit_simulation(payload: Dict[str, Any], background_tasks: BackgroundTasks, mongodb=Depends(get_database)):
    """
    Submit a simulation to OpenMC (single-backend).
    Payload shape matches the former OpenMC backend:
      { "spec": {...}, "run_id": optional }
    """
    spec = payload.get("spec") or {}
    run_id = payload.get("run_id") or f"run_{uuid4().hex[:12]}"
    submitted_at = datetime.now(timezone.utc)

    if mongodb is not None:
        await mongodb.openmc_runs.insert_one(
            {
                "run_id": run_id,
                "spec_hash": "",
                "status": "queued",
                "spec": spec,
                "submitted_at": submitted_at,
                "started_at": None,
                "completed_at": None,
            }
        )

    background_tasks.add_task(_execute_openmc_background, run_id, spec, mongodb)

    return {
        "run_id": run_id,
        "spec_hash": "",
        "status": "queued",
        "submitted_at": submitted_at.isoformat(),
        "estimated_duration_seconds": 30,
    }


@app.get("/api/v1/openmc/simulations/{run_id}")
async def openmc_get_simulation(run_id: str, mongodb=Depends(get_database)):
    if mongodb is None:
        raise HTTPException(status_code=503, detail="Database not available")
    doc = await mongodb.openmc_runs.find_one({"run_id": run_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    doc.pop("_id", None)
    # Normalize datetime fields to isoformat for frontend convenience
    for k in ("submitted_at", "started_at", "completed_at"):
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat()
    return doc


@app.delete("/api/v1/openmc/simulations/{run_id}")
async def openmc_cancel_simulation(run_id: str, mongodb=Depends(get_database)):
    if mongodb is None:
        raise HTTPException(status_code=503, detail="Database not available")
    res = await mongodb.openmc_runs.update_one(
        {"run_id": run_id, "status": {"$in": ["queued", "running"]}},
        {"$set": {"status": "cancelled", "completed_at": datetime.now(timezone.utc)}},
    )
    if res.modified_count == 0:
        raise HTTPException(status_code=404, detail="Run not found or cannot be cancelled")
    return {"run_id": run_id, "status": "cancelled"}


@app.get("/api/v1/openmc/simulations/{run_id}/stream")
async def openmc_stream(run_id: str):
    """
    SSE stream for OpenMC run output.
    Events:
      - openmc_log
      - tool_call
      - tool_result
      - openmc_error
    """
    run_dir = RUNS_DIR / run_id

    async def event_generator():
        q = run_event_bus.subscribe(run_id)

        # Replay log tail (best-effort)
        log_path = run_dir / "outputs" / "openmc_stdout.log"
        if log_path.exists():
            try:
                tail = log_path.read_text(encoding="utf-8").splitlines()[-200:]
                for line in tail:
                    event = {
                        "type": "openmc_log",
                        "run_id": run_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "content": line + "\n",
                    }
                    yield "event: openmc_log\n"
                    yield f"data: {json.dumps(event)}\n\n"
            except Exception:
                pass

        try:
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if ev is None:
                    break
                yield f"event: {ev['type']}\n"
                yield f"data: {json.dumps(ev)}\n\n"
        finally:
            run_event_bus.unsubscribe(run_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/v1/openmc/health")
async def openmc_health(mongodb=Depends(get_database)):
    # basic health: DB + openmc import
    status = "healthy"
    openmc_available = True
    try:
        import openmc  # type: ignore
        _ = openmc.__version__
    except Exception:
        openmc_available = False
        status = "degraded"

    db_ok = True
    try:
        if mongodb is not None:
            await db.client.admin.command("ping")
    except Exception:
        db_ok = False
        status = "unhealthy"

    return {
        "status": status,
        "openmc_available": openmc_available,
        "mongodb": "connected" if db_ok else "disconnected",
        "runs_dir": str(RUNS_DIR),
    }


@app.get("/api/v1/openmc/statistics")
async def openmc_statistics(mongodb=Depends(get_database)):
    if mongodb is None:
        raise HTTPException(status_code=503, detail="Database not available")
    total = await mongodb.openmc_runs.count_documents({})
    completed = await mongodb.openmc_runs.count_documents({"status": "completed"})
    running = await mongodb.openmc_runs.count_documents({"status": "running"})
    failed = await mongodb.openmc_runs.count_documents({"status": "failed"})
    return {
        "total_runs": total,
        "completed_runs": completed,
        "running_runs": running,
        "failed_runs": failed,
    }


@app.get("/api/v1/openmc/runs")
async def openmc_query_runs(request: Request, mongodb=Depends(get_database)):
    if mongodb is None:
        raise HTTPException(status_code=503, detail="Database not available")
    limit = int(request.query_params.get("limit", "20"))
    offset = int(request.query_params.get("offset", "0"))
    cursor = mongodb.openmc_runs.find().sort("submitted_at", -1).skip(offset).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d.pop("_id", None)
    return {"total": await mongodb.openmc_runs.count_documents({}), "limit": limit, "offset": offset, "runs": docs}


@app.post("/api/v1/openmc/runs/compare")
async def openmc_compare_runs(payload: Dict[str, Any], mongodb=Depends(get_database)):
    run_ids = payload.get("run_ids") or []
    if not isinstance(run_ids, list) or len(run_ids) < 2:
        raise HTTPException(status_code=400, detail="run_ids must be an array of 2+ ids")
    # Reuse existing compare tool which reads from summaries collection
    comparison = compare_runs_tool(run_ids)
    return comparison

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

        # LangGraph orchestration (traceable in LangSmith via LANGCHAIN_* env vars)
        from agent_thinking_events import AgentThinkingCallback

        thinking_callback = AgentThinkingCallback(event_bus, query_id)
        ctx = QueryGraphContext(
            query_id=query_id,
            event_bus=event_bus,
            mongodb=mongodb,
            use_llm=use_llm,
            thinking_callback=thinking_callback,
        )

        await QUERY_GRAPH.ainvoke({"ctx": ctx, "query": query})
        
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
# ROUTES: VISUALIZATIONS
# ============================================================================

@app.get("/api/v1/visualizations/run/{run_id}", response_model=VisualizationResponse)
async def get_run_visualization(run_id: str, mongodb=Depends(get_database)):
    """
    Get visualization data for a single run.
    Returns batch convergence data if available, otherwise summary stats.
    """
    # Try to get from summaries first
    summary = await mongodb.summaries.find_one({"run_id": run_id})
    if not summary:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    # Try to get batch data from statepoint file if available
    batch_data = None
    try:
        # Check if we have run_dir stored
        run_doc = await mongodb.openmc_runs.find_one({"run_id": run_id})
        if run_doc and run_doc.get("run_dir"):
            run_dir = Path(run_doc["run_dir"])
            # Look for statepoint file
            outputs_dir = run_dir / "outputs"
            if outputs_dir.exists():
                statepoint_files = list(outputs_dir.glob("statepoint.*.h5"))
                if statepoint_files:
                    try:
                        from aonp.core.extractor import extract_results
                        batch_data = extract_results(statepoint_files[0])
                    except Exception as e:
                        print(f"Could not extract batch data: {e}")
    except Exception as e:
        print(f"Error getting batch data: {e}")
    
    # Generate batch convergence visualization data
    if batch_data and "batch_keff" in batch_data:
        n_batches = len(batch_data["batch_keff"])
        n_inactive = batch_data.get("n_inactive", 0)
        
        return VisualizationResponse(
            type="batch_convergence",
            data={
                "batch_numbers": list(range(1, n_batches + 1)),
                "batch_keff": batch_data["batch_keff"],
                "entropy": batch_data.get("entropy"),
                "n_inactive": n_inactive,
                "final_keff": summary["keff"],
                "final_keff_std": summary["keff_std"],
                "run_id": run_id,
                "spec": summary.get("spec", {}),
            }
        )
    else:
        # Generate mock batch data for visualization (approximate)
        n_batches = summary.get("spec", {}).get("batches", 50)
        n_inactive = summary.get("spec", {}).get("inactive")
        if n_inactive is None:
            n_inactive = n_batches // 5  # Default to 20% inactive
        final_keff = summary["keff"]
        final_std = summary["keff_std"]
        
        # Generate approximate batch convergence (smooth convergence curve)
        random.seed(hash(run_id) % (2**32))  # Deterministic based on run_id
        
        # Create a convergence curve
        batches = list(range(1, n_batches + 1))
        start_keff = final_keff + random.uniform(-0.1, 0.1)
        
        batch_keff = []
        import math
        for batch in batches:
            if batch <= n_inactive:
                # Inactive batches: approaching steady state
                progress = batch / n_inactive
                exp_term = 1.0 - (math.exp(-3 * progress))
                value = start_keff + (final_keff - start_keff) * exp_term
            else:
                # Active batches: around final value with noise
                u1 = random.random()
                u2 = random.random()
                z = math.sqrt(-2 * math.log(max(u1, 1e-10))) * math.cos(2 * math.pi * u2)
                value = final_keff + z * final_std * 0.5
            batch_keff.append(float(value))
        
        return VisualizationResponse(
            type="batch_convergence",
            data={
                "batch_numbers": batches,
                "batch_keff": batch_keff,
                "entropy": None,
                "n_inactive": n_inactive,
                "final_keff": final_keff,
                "final_keff_std": final_std,
                "run_id": run_id,
                "spec": summary.get("spec", {}),
                "note": "Generated approximate batch data (statepoint file not available)",
            }
        )


@app.get("/api/v1/visualizations/sweep", response_model=VisualizationResponse)
async def get_sweep_visualization(
    run_ids: str,  # Comma-separated run IDs
    mongodb=Depends(get_database)
):
    """
    Get parameter sweep visualization data.
    Analyzes runs to detect which parameter is varying.
    """
    run_id_list = [r.strip() for r in run_ids.split(",") if r.strip()]
    if len(run_id_list) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 run IDs for sweep visualization")
    
    # Get all runs
    runs = []
    for run_id in run_id_list:
        summary = await mongodb.summaries.find_one({"run_id": run_id})
        if summary:
            runs.append(summary)
    
    if len(runs) < 2:
        raise HTTPException(status_code=404, detail="Not enough runs found")
    
    # Detect which parameter is varying
    first_spec = runs[0].get("spec", {})
    varying_param = None
    param_values = []
    
    # Check common parameters
    for param in ["enrichment_pct", "temperature_K", "particles", "batches"]:
        values = [r.get("spec", {}).get(param) for r in runs]
        if all(v is not None for v in values) and len(set(values)) > 1:
            varying_param = param
            param_values = values
            break
    
    if not varying_param:
        # Default to enrichment if it exists, otherwise use run index
        if all("enrichment_pct" in r.get("spec", {}) for r in runs):
            varying_param = "enrichment_pct"
            param_values = [r.get("spec", {}).get("enrichment_pct", 0) for r in runs]
        else:
            varying_param = "run_index"
            param_values = list(range(len(runs)))
    
    # Extract k-eff values with uncertainties
    keff_values = [r["keff"] for r in runs]
    keff_stds = [r["keff_std"] for r in runs]
    
    # Sort by parameter value
    sorted_data = sorted(zip(param_values, keff_values, keff_stds, runs), key=lambda x: x[0])
    param_values, keff_values, keff_stds, runs = zip(*sorted_data)
    
    # Calculate trend line (simple linear regression)
    trend_line = None
    if len(param_values) > 1 and all(isinstance(p, (int, float)) for p in param_values):
        try:
            # Simple linear regression
            n = len(param_values)
            sum_x = sum(param_values)
            sum_y = sum(keff_values)
            sum_xy = sum(x * y for x, y in zip(param_values, keff_values))
            sum_x2 = sum(x * x for x in param_values)
            
            denominator = n * sum_x2 - sum_x * sum_x
            if abs(denominator) > 1e-10:
                slope = (n * sum_xy - sum_x * sum_y) / denominator
                intercept = (sum_y - slope * sum_x) / n
                
                trend_line = {
                    "slope": float(slope),
                    "intercept": float(intercept),
                    "values": [float(slope * p + intercept) for p in param_values],
                }
        except Exception as e:
            print(f"Could not calculate trend line: {e}")
            trend_line = None
    
    return VisualizationResponse(
        type="parameter_sweep",
        data={
            "parameter_name": varying_param,
            "parameter_values": list(param_values),
            "keff_values": list(keff_values),
            "keff_stds": list(keff_stds),
            "trend_line": trend_line,
            "runs": [
                {
                    "run_id": r["run_id"],
                    "keff": keff,
                    "keff_std": keff_std,
                    "spec": r.get("spec", {}),
                }
                for r, keff, keff_std in zip(runs, keff_values, keff_stds)
            ],
        }
    )


@app.post("/api/v1/visualizations/comparison", response_model=VisualizationResponse)
async def get_comparison_visualization(
    request: CompareRunsRequest,
    mongodb=Depends(get_database)
):
    """
    Get comparison visualization data for multiple runs.
    """
    comparison = compare_runs_tool(request.run_ids)
    
    if "error" in comparison:
        raise HTTPException(status_code=404, detail=comparison["error"])
    
    return VisualizationResponse(
        type="comparison",
        data={
            "num_runs": comparison["num_runs"],
            "keff_values": comparison["keff_values"],
            "keff_mean": comparison["keff_mean"],
            "keff_min": comparison["keff_min"],
            "keff_max": comparison["keff_max"],
            "runs": comparison["runs"],
        }
    )


@app.get("/api/v1/runs/similar/{run_id}")
async def find_similar_runs(
    run_id: str,
    limit: int = 10,
    mongodb=Depends(get_database)
):
    """
    Find similar runs based on specification parameters.
    Compares geometry, materials, and similar parameter ranges.
    """
    # Get the reference run
    reference = await mongodb.summaries.find_one({"run_id": run_id})
    if not reference:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    ref_spec = reference.get("spec", {})
    ref_geometry = ref_spec.get("geometry", "")
    ref_enrichment = ref_spec.get("enrichment_pct")
    ref_temp = ref_spec.get("temperature_K")
    
    # Build similarity query
    similarity_query = {
        "run_id": {"$ne": run_id},  # Exclude the reference run
        "status": "completed",  # Only completed runs
    }
    
    # Match geometry (exact or similar)
    if ref_geometry:
        similarity_query["spec.geometry"] = {"$regex": ref_geometry.split()[0], "$options": "i"}
    
    # Match enrichment within ±1% if specified
    if ref_enrichment is not None:
        similarity_query["spec.enrichment_pct"] = {
            "$gte": ref_enrichment - 1.0,
            "$lte": ref_enrichment + 1.0,
        }
    
    # Match temperature within ±100K if specified
    if ref_temp is not None:
        similarity_query["spec.temperature_K"] = {
            "$gte": ref_temp - 100,
            "$lte": ref_temp + 100,
        }
    
    # Query and sort by similarity score (closer enrichment/temp first)
    cursor = mongodb.summaries.find(similarity_query).sort("created_at", -1).limit(limit * 2)
    candidates = await cursor.to_list(length=limit * 2)
    
    # Calculate similarity scores and sort
    def similarity_score(candidate: dict) -> float:
        score = 0.0
        cand_spec = candidate.get("spec", {})
        
        # Geometry match (binary)
        if cand_spec.get("geometry", "").lower() == ref_geometry.lower():
            score += 10.0
        
        # Enrichment proximity (if both have it)
        cand_enrichment = cand_spec.get("enrichment_pct")
        if ref_enrichment is not None and cand_enrichment is not None:
            enrichment_diff = abs(cand_enrichment - ref_enrichment)
            score += max(0, 5.0 - enrichment_diff * 2)  # Max 5 points, decreases with distance
        
        # Temperature proximity (if both have it)
        cand_temp = cand_spec.get("temperature_K")
        if ref_temp is not None and cand_temp is not None:
            temp_diff = abs(cand_temp - ref_temp) / 100.0  # Normalize to 100K units
            score += max(0, 3.0 - temp_diff * 1.5)  # Max 3 points
        
        return score
    
    # Sort by similarity and take top N
    scored = [(candidate, similarity_score(candidate)) for candidate in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    similar_runs = [run for run, score in scored[:limit]]
    
    # Format results
    results = []
    for run in similar_runs:
        results.append({
            "run_id": run["run_id"],
            "spec_hash": run["spec_hash"],
            "geometry": run["spec"].get("geometry", "unknown"),
            "enrichment_pct": run["spec"].get("enrichment_pct"),
            "temperature_K": run["spec"].get("temperature_K"),
            "keff": run["keff"],
            "keff_std": run["keff_std"],
            "status": run["status"],
            "created_at": run["created_at"].isoformat(),
        })
    
    return {
        "reference_run_id": run_id,
        "similar_runs": results,
        "total_found": len(results),
    }

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


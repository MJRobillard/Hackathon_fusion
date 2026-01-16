"""
AONP Multi-Agent API Server (v2)

Implements the API contract used by the Next.js frontend:
- POST /api/v1/query
- GET  /api/v1/query/{query_id}
- GET  /api/v1/query/{query_id}/stream  (SSE)
- POST /api/v1/router                    (routing-only)
- GET  /api/v1/statistics
- GET  /api/v1/health

Key feature: emits *detailed* agent thinking + tool-call events over SSE so the
"Agent Reasoning" panel can show each tool call and decision as the agents run.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

load_dotenv()

# Ensure we can import from Playground/backend (agents + graph live one dir up)
API_DIR = Path(__file__).resolve().parent
BACKEND_DIR = API_DIR.parent
REPO_ROOT = BACKEND_DIR.parent.parent
for path in (BACKEND_DIR, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aonp.api.openmc_router import router as openmc_router, set_event_loop as set_openmc_event_loop, RUN_RECORDS
from aonp.api.terminal_streamer import terminal_broadcaster, install_terminal_interceptor
from aonp.core.extractor import extract_results


# ============================================================================
# CONFIG
# ============================================================================

MONGO_URI = os.getenv("MONGO_URI")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")


# ============================================================================
# DB
# ============================================================================


class Database:
    client: Optional[AsyncIOMotorClient] = None


db = Database()


# ============================================================================
# RAG STATE (lazy init)
# ============================================================================

RAG_STATE: Dict[str, Any] = {
    "ready": False,
    "error": None,
    "agent": None,
    "vector_store": None,
    "pdf_indexer": None,
    "sim_indexer": None,
}


def _ensure_rag_ready() -> Dict[str, Any]:
    if RAG_STATE["ready"] or RAG_STATE["error"]:
        return RAG_STATE

    try:
        from rag_components import setup_rag_components  # type: ignore
        from rag_agent import RAGCopilotAgent  # type: ignore
        from pymongo import MongoClient  # type: ignore
    except Exception as exc:
        RAG_STATE["error"] = f"RAG dependencies not available: {exc}"
        return RAG_STATE

    voyage_key = os.getenv("VOYAGE_API_KEY")
    if not voyage_key:
        RAG_STATE["error"] = "VOYAGE_API_KEY is not configured"
        return RAG_STATE

    if not MONGO_URI:
        RAG_STATE["error"] = "MONGO_URI is not configured"
        return RAG_STATE

    try:
        chroma_dir = str(BACKEND_DIR / "rag" / "chroma_db")
        embedder, vector_store, pdf_indexer, sim_indexer = setup_rag_components(
            voyage_api_key=voyage_key,
            mongo_uri=MONGO_URI,
            chroma_dir=chroma_dir,
        )
        mongo_client = MongoClient(MONGO_URI)
        agent = RAGCopilotAgent(
            embedder=embedder,
            vector_store=vector_store,
            mongo_client=mongo_client,
        )
        RAG_STATE.update(
            {
                "ready": True,
                "error": None,
                "agent": agent,
                "vector_store": vector_store,
                "pdf_indexer": pdf_indexer,
                "sim_indexer": sim_indexer,
            }
        )
    except Exception as exc:
        RAG_STATE["error"] = f"RAG initialization failed: {exc}"

    return RAG_STATE


async def get_database():
    if not db.client:
        raise HTTPException(status_code=503, detail="MongoDB is not connected")
    return db.client["aonp"]


async def startup_db():
    if not MONGO_URI:
        # Keep server up for UI dev; endpoints that need DB will 503.
        print("[WARN] MONGO_URI not set; database-backed endpoints will be unavailable.")
        return
    db.client = AsyncIOMotorClient(MONGO_URI)
    await db.client.admin.command("ping")
    print("✅ Connected to MongoDB")


async def shutdown_db():
    if db.client:
        db.client.close()
        db.client = None
        print("✅ Closed MongoDB connection")


# ============================================================================
# SSE EVENT BUS
# ============================================================================


class AgentEventBus:
    """
    Per-query pub/sub for SSE.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, query_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subscribers.setdefault(query_id, []).append(q)
        return q

    def unsubscribe(self, query_id: str, q: asyncio.Queue) -> None:
        subs = self._subscribers.get(query_id)
        if not subs:
            return
        try:
            subs.remove(q)
        except ValueError:
            return
        if not subs:
            self._subscribers.pop(query_id, None)

    async def publish(self, query_id: str, event: Dict[str, Any]) -> None:
        subs = self._subscribers.get(query_id, [])
        if not subs:
            return
        for q in list(subs):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Drop if a client is too slow; keep system responsive.
                pass

    async def complete(self, query_id: str) -> None:
        subs = self._subscribers.get(query_id, [])
        for q in list(subs):
            try:
                q.put_nowait(None)
            except asyncio.QueueFull:
                pass


event_bus = AgentEventBus()

MAIN_LOOP: Optional[asyncio.AbstractEventLoop] = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentThinkingCallback:
    """
    Callback used by agents to emit UI-friendly trace events.
    """

    bus: AgentEventBus
    query_id: str

    async def _publish(self, payload: Dict[str, Any]) -> None:
        await self.bus.publish(self.query_id, payload)

    def _fire_and_forget(self, payload: Dict[str, Any]) -> None:
        # Agents run in thread executor; event loop-safe publish.
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._publish(payload))
        except RuntimeError:
            # No running loop in this thread → schedule on main loop.
            if MAIN_LOOP is None:
                print(f"[WARN] AgentThinkingCallback: MAIN_LOOP not set, dropping event: {payload.get('type')}")
                return
            # Use run_coroutine_threadsafe for proper async execution from thread
            try:
                future = asyncio.run_coroutine_threadsafe(self._publish(payload), MAIN_LOOP)
                # Don't wait for completion, but log errors if they occur
                def log_error(fut):
                    try:
                        fut.result()
                    except Exception as e:
                        print(f"[ERROR] AgentThinkingCallback publish failed: {e}")
                future.add_done_callback(log_error)
            except Exception as e:
                print(f"[ERROR] AgentThinkingCallback failed to schedule event: {e}")

    def thinking(self, agent: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._fire_and_forget(
            {
                "type": "agent_thinking",
                "agent": agent,
                "content": content,
                "metadata": metadata or {},
                "timestamp": _utc_now_iso(),
            }
        )

    def planning(self, agent: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._fire_and_forget(
            {
                "type": "agent_planning",
                "agent": agent,
                "content": content,
                "metadata": metadata or {},
                "timestamp": _utc_now_iso(),
            }
        )

    def decision(self, agent: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._fire_and_forget(
            {
                "type": "agent_decision",
                "agent": agent,
                "content": content,
                "metadata": metadata or {},
                "timestamp": _utc_now_iso(),
            }
        )

    def observation(self, agent: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._fire_and_forget(
            {
                "type": "agent_observation",
                "agent": agent,
                "content": content,
                "metadata": metadata or {},
                "timestamp": _utc_now_iso(),
            }
        )

    def tool_call(self, agent: str, tool_name: str, args: Any, message: Optional[str] = None) -> None:
        self._fire_and_forget(
            {
                "type": "tool_call",
                "agent": agent,
                "tool_name": tool_name,
                "args": args,
                "message": message or f"Calling tool {tool_name}",
                "timestamp": _utc_now_iso(),
            }
        )

    def tool_result(self, agent: str, tool_name: str, result: Any, message: Optional[str] = None) -> None:
        self._fire_and_forget(
            {
                "type": "tool_result",
                "agent": agent,
                "tool_name": tool_name,
                "result": result,
                "message": message or f"Tool {tool_name} returned",
                "timestamp": _utc_now_iso(),
            }
        )


# ============================================================================
# API SCHEMAS
# ============================================================================


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    use_llm: bool = False


class QueryResponse(BaseModel):
    query_id: str
    status: str
    stream_url: Optional[str] = None


class RouterRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    use_llm: bool = False


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)


class RAGLiteratureRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    n_results: int = Field(default=5, ge=1, le=20)


class RAGSimilarRunsRequest(BaseModel):
    query: Optional[str] = None
    geometry: Optional[str] = None
    enrichment: Optional[float] = None
    n_results: int = Field(default=5, ge=1, le=20)


class RAGSuggestRequest(BaseModel):
    context: str = Field(..., min_length=1, max_length=6000)
    current_results: Optional[Dict[str, Any]] = None
    n_suggestions: int = Field(default=3, ge=1, le=10)


class RAGIndexPapersRequest(BaseModel):
    directory: Optional[str] = None


class RAGIndexRunsRequest(BaseModel):
    limit: Optional[int] = Field(default=None, ge=1)


# ============================================================================
# APP
# ============================================================================


app = FastAPI(
    title="AONP Multi-Agent API (v2)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(openmc_router)


@app.on_event("startup")
async def _startup():
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_running_loop()
    set_openmc_event_loop(MAIN_LOOP)
    terminal_broadcaster.set_event_loop(MAIN_LOOP)
    install_terminal_interceptor()
    await startup_db()


@app.on_event("shutdown")
async def _shutdown():
    await shutdown_db()


@app.get("/api/v1/health")
async def health():
    mongodb_status = "disconnected"
    if db.client:
        try:
            await db.client.admin.command("ping")
            mongodb_status = "connected"
        except Exception:
            mongodb_status = "disconnected"

    return {
        "status": "healthy" if mongodb_status == "connected" else "degraded",
        "services": {"mongodb": mongodb_status == "connected"},
        "timestamp": _utc_now_iso(),
        "version": "2.0.0",
    }


@app.get("/api/v1/statistics")
async def statistics(mongodb=Depends(get_database)):
    # Best-effort; keep UI stable even if collections are empty.
    total_studies = await mongodb.studies.count_documents({})
    total_runs = await mongodb.runs.count_documents({})
    completed_runs = await mongodb.runs.count_documents({"status": {"$in": ["completed", "succeeded"]}})
    total_queries = await mongodb.queries.count_documents({})
    return {
        "total_studies": total_studies,
        "total_runs": total_runs,
        "completed_runs": completed_runs,
        "total_queries": total_queries,
        "mongodb_status": "connected",
    }


@app.get("/api/v1/runs")
async def get_runs(
    limit: int = 50,
    offset: int = 0,
    mongodb=Depends(get_database),
):
    """
    Query simulation runs from MongoDB summaries collection.
    
    Returns paginated list of runs matching the frontend RunSummary format.
    """
    # Query summaries collection (this is where agent_tools.py stores results)
    summaries_col = mongodb.summaries
    
    # Get total count
    total = await summaries_col.count_documents({})
    
    # Query with pagination (sorted by created_at descending)
    cursor = summaries_col.find({}).sort("created_at", -1).skip(offset).limit(limit)
    results = await cursor.to_list(length=limit)
    
    # Format results to match RunSummary interface
    runs = []
    for r in results:
        # Extract geometry and other fields from spec if available
        geometry = "unknown"
        enrichment_pct = None
        temperature_K = None
        if "spec" in r and isinstance(r["spec"], dict):
            geometry = r["spec"].get("geometry", "unknown")
            enrichment_pct = r["spec"].get("enrichment_pct")
            temperature_K = r["spec"].get("temperature_K")
        
        # Format created_at (handle both datetime and string)
        created_at_str = r.get("created_at")
        if hasattr(created_at_str, "isoformat"):
            created_at_str = created_at_str.isoformat()
        elif created_at_str is None:
            created_at_str = datetime.now(timezone.utc).isoformat()
        
        run_obj = {
            "run_id": r.get("run_id", "unknown"),
            "geometry": geometry,
            "keff": r.get("keff"),
            "keff_std": r.get("keff_std"),
            "status": r.get("status", "unknown"),
            "created_at": created_at_str,
        }
        
        # Add optional fields if present
        if enrichment_pct is not None:
            run_obj["enrichment_pct"] = enrichment_pct
        if temperature_K is not None:
            run_obj["temperature_K"] = temperature_K
        
        runs.append(run_obj)
    
    return {
        "runs": runs,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _get_run_dir_from_openmc(run_id: str) -> Optional[Path]:
    """Try to get run directory from OpenMC router's RUN_RECORDS."""
    record = RUN_RECORDS.get(run_id)
    if record and record.run_dir:
        return Path(record.run_dir)
    # Also check default runs directory
    runs_dir = Path(os.getenv("OPENMC_RUNS_DIR", "runs"))
    run_dir = runs_dir / run_id
    if run_dir.exists():
        return run_dir
    return None


@app.get("/api/v1/runs/{run_id}/visualization")
async def get_run_visualization(run_id: str, mongodb=Depends(get_database)):
    """
    Get batch convergence visualization data for a run.
    
    Returns batch convergence data in the format expected by BatchConvergenceChart:
    - batch_numbers: [1, 2, 3, ...]
    - batch_keff: [keff1, keff2, ...]
    - n_inactive: number of inactive batches
    - final_keff: final k-effective
    - final_keff_std: final k-effective std dev
    """
    # Try to find run directory from OpenMC router
    run_dir = _get_run_dir_from_openmc(run_id)
    
    # Try to load statepoint file
    if run_dir:
        outputs_dir = run_dir / "outputs"
        statepoint_files = sorted(outputs_dir.glob("statepoint.*.h5"))
        
        if statepoint_files:
            try:
                import openmc  # type: ignore
                sp = openmc.StatePoint(str(statepoint_files[-1]))
                
                # Extract batch data
                batch_numbers = list(range(1, sp.n_batches + 1))
                batch_keff = sp.k_generation.tolist()
                n_inactive = sp.n_inactive
                final_keff = float(sp.keff.nominal_value)
                final_keff_std = float(sp.keff.std_dev)
                
                # Extract entropy if available
                entropy = None
                if hasattr(sp, "entropy"):
                    entropy = sp.entropy.tolist()
                
                return {
                    "type": "batch_convergence",
                    "data": {
                        "batch_numbers": batch_numbers,
                        "batch_keff": batch_keff,
                        "entropy": entropy,
                        "n_inactive": n_inactive,
                        "final_keff": final_keff,
                        "final_keff_std": final_keff_std,
                    },
                }
            except Exception as e:
                # If statepoint read fails, fall through to MongoDB/mock
                pass
    
    # Fallback: check MongoDB for run data
    summary = await mongodb.summaries.find_one({"run_id": run_id})
    if summary and summary.get("keff") is not None:
        # Generate simple mock batch convergence data
        n_batches = summary.get("batches", 50)
        keff = summary["keff"]
        keff_std = summary.get("keff_std", 0.001)
        n_inactive = summary.get("inactive", 10)
        
        # Generate synthetic batch data (simple linear convergence)
        batch_numbers = list(range(1, n_batches + 1))
        batch_keff = [keff + (keff_std * 2) * (1 - i / n_batches) for i in range(n_batches)]
        
        return {
            "type": "batch_convergence",
            "data": {
                "batch_numbers": batch_numbers,
                "batch_keff": batch_keff,
                "entropy": None,
                "n_inactive": n_inactive,
                "final_keff": keff,
                "final_keff_std": keff_std,
            },
        }
    
    # No data available
    return {"status": "not_available", "run_id": run_id, "data": []}


@app.post("/api/v1/runs/sweep/visualization")
async def get_sweep_visualization(body: Dict[str, Any], mongodb=Depends(get_database)):
    """
    Get parameter sweep visualization data for multiple runs.
    
    Expects: {"run_ids": ["run1", "run2", ...]}
    """
    run_ids = body.get("run_ids", [])
    if len(run_ids) < 2:
        return {"status": "error", "message": "At least 2 run IDs required"}
    
    # Query MongoDB for run data
    summaries = await mongodb.summaries.find({"run_id": {"$in": run_ids}}).to_list(length=100)
    
    if not summaries:
        return {"status": "not_available", "run_ids": run_ids, "data": []}
    
    # Extract parameter values and keff from runs
    # Try to infer parameter from differences in spec
    parameter = "enrichment_pct"  # Default
    values = []
    keff_values = []
    keff_stds = []
    
    for run in summaries:
        spec = run.get("spec", {})
        if "enrichment_pct" in spec:
            values.append(spec["enrichment_pct"])
        keff_values.append(run.get("keff", 0.0))
        keff_stds.append(run.get("keff_std", 0.001))
    
    # Sort by parameter value
    sorted_data = sorted(zip(values, keff_values, keff_stds))
    values, keff_values, keff_stds = zip(*sorted_data) if sorted_data else ([], [], [])
    
    if not values:
        return {"status": "not_available", "run_ids": run_ids, "data": []}
    
    return {
        "type": "parameter_sweep",
        "data": {
            "parameter": parameter,
            "values": list(values),
            "keff": list(keff_values),
            "keff_std": list(keff_stds),
        },
    }


@app.post("/api/v1/runs/comparison/visualization")
async def get_comparison_visualization(body: Dict[str, Any], mongodb=Depends(get_database)):
    """
    Get comparison visualization data for multiple runs.
    
    Expects: {"run_ids": ["run1", "run2", ...]}
    """
    run_ids = body.get("run_ids", [])
    if len(run_ids) < 2:
        return {"status": "error", "message": "At least 2 run IDs required"}
    
    # Query MongoDB for run data
    summaries = await mongodb.summaries.find({"run_id": {"$in": run_ids}}).to_list(length=100)
    
    if not summaries:
        return {"status": "not_available", "run_ids": run_ids, "data": []}
    
    # Format comparison data
    comparison_data = {
        "run_ids": run_ids,
        "parameters": {
            "enrichment_pct": [r.get("spec", {}).get("enrichment_pct") for r in summaries],
            "temperature_K": [r.get("spec", {}).get("temperature_K") for r in summaries],
        },
        "results": {
            "keff": [r.get("keff", 0.0) for r in summaries],
            "keff_std": [r.get("keff_std", 0.001) for r in summaries],
        },
    }
    
    return {
        "type": "comparison",
        "data": comparison_data,
    }


@app.get("/api/v1/runs/{run_id}/similar")
async def find_similar_runs(run_id: str, limit: int = 10, mongodb=Depends(get_database)):
    """
    Find similar runs to a given run_id.
    
    Returns runs with similar geometry/enrichment from MongoDB.
    """
    # Get the target run
    target_run = await mongodb.summaries.find_one({"run_id": run_id})
    if not target_run:
        return {"status": "error", "message": f"Run {run_id} not found", "similar_runs": [], "total_found": 0}
    
    target_spec = target_run.get("spec", {})
    target_geometry = target_spec.get("geometry", "")
    target_enrichment = target_spec.get("enrichment_pct")
    
    # Build similarity query
    query = {}
    if target_geometry:
        query["spec.geometry"] = {"$regex": target_geometry.split()[0], "$options": "i"}  # Match first word (e.g., "PWR")
    if target_enrichment is not None:
        query["spec.enrichment_pct"] = {"$gte": target_enrichment - 1.0, "$lte": target_enrichment + 1.0}
    
    # Query similar runs (exclude the target run)
    query["run_id"] = {"$ne": run_id}
    similar_runs_cursor = mongodb.summaries.find(query).sort("created_at", -1).limit(limit)
    similar_runs_list = await similar_runs_cursor.to_list(length=limit)
    total = await mongodb.summaries.count_documents(query)
    
    # Format results
    similar_runs = []
    for r in similar_runs_list:
        spec = r.get("spec", {})
        similar_runs.append({
            "run_id": r.get("run_id"),
            "geometry": spec.get("geometry", "unknown"),
            "enrichment_pct": spec.get("enrichment_pct"),
            "temperature_K": spec.get("temperature_K"),
            "keff": r.get("keff"),
            "keff_std": r.get("keff_std"),
            "status": r.get("status", "unknown"),
        })
    
    return {
        "status": "success",
        "similar_runs": similar_runs,
        "total_found": total,
    }


@app.post("/api/v1/router")
async def test_router(body: RouterRequest):
    """
    Route-only endpoint used by the frontend to preview routing decisions.
    """
    from multi_agent_system import RouterAgent  # type: ignore

    cb = AgentThinkingCallback(event_bus, query_id=f"route_{uuid4().hex[:8]}")
    router = RouterAgent(use_llm=body.use_llm, thinking_callback=cb)
    routing = router.route_query(body.query)
    return routing


async def _execute_query(query_id: str, query: str, use_llm: bool, mongodb) -> None:
    """
    Execute the multi-agent graph and persist results.
    """
    from graphs.query_graph import QueryGraphContext, build_query_graph  # type: ignore

    cb = AgentThinkingCallback(event_bus, query_id=query_id)

    await mongodb.queries.update_one(
        {"query_id": query_id},
        {"$set": {"status": "processing"}},
    )

    try:
        g = build_query_graph()
        ctx = QueryGraphContext(
            query_id=query_id,
            event_bus=event_bus,
            mongodb=mongodb,
            use_llm=use_llm,
            thinking_callback=cb,
        )

        # Run graph
        final_state = await g.ainvoke({"ctx": ctx, "query": query})

        # Persist whatever remains (graph already stores core result fields)
        await mongodb.queries.update_one(
            {"query_id": query_id},
            {"$set": {"final_state": final_state}},
        )

    except Exception as e:
        await mongodb.queries.update_one(
            {"query_id": query_id},
            {"$set": {"status": "failed", "error": str(e), "completed_at": datetime.now(timezone.utc)}},
        )
        await event_bus.publish(
            query_id,
            {"type": "query_error", "error": str(e), "timestamp": _utc_now_iso()},
        )
    finally:
        await event_bus.complete(query_id)


@app.post("/api/v1/query", response_model=QueryResponse, status_code=202)
async def submit_query(
    body: QueryRequest,
    background_tasks: BackgroundTasks,
    mongodb=Depends(get_database),
):
    query_id = f"q_{uuid4().hex[:10]}"
    created_at = datetime.now(timezone.utc)

    await mongodb.queries.insert_one(
        {
            "query_id": query_id,
            "query": body.query,
            "status": "queued",
            "created_at": created_at,
            "routing": None,
            "results": None,
            "analysis": None,
            "suggestions": None,
            "error": None,
        }
    )

    background_tasks.add_task(_execute_query, query_id, body.query, body.use_llm, mongodb)

    return QueryResponse(
        query_id=query_id,
        status="queued",
        stream_url=f"/api/v1/query/{query_id}/stream",
    )


@app.get("/api/v1/query/{query_id}")
async def get_query(query_id: str, mongodb=Depends(get_database)):
    doc = await mongodb.queries.find_one({"query_id": query_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    doc.pop("_id", None)

    # Normalize datetimes to ISO strings for the frontend.
    for k in ["created_at", "completed_at"]:
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat()
    return JSONResponse(content=doc)


@app.get("/api/v1/query/{query_id}/stream")
async def stream_query(query_id: str):
    """
    SSE stream of routing/agent/tool/thinking events.
    """

    async def gen():
        q = event_bus.subscribe(query_id)
        try:
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                if evt is None:
                    break

                evt_type = evt.get("type", "message")
                yield f"event: {evt_type}\n"
                yield f"data: {json.dumps(evt, default=str)}\n\n"
        finally:
            event_bus.unsubscribe(query_id, q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/v1/terminal/stream")
async def stream_terminal_output():
    """
    Stream ALL backend terminal output in real-time (stdout + stderr) over SSE.

    The frontend expects this endpoint at `/api/v1/terminal/stream`.
    """

    async def gen():
        q = terminal_broadcaster.subscribe()
        try:
            # Initial connection message
            content_msg = '[Connected to terminal stream]\n'
            yield f"data: {json.dumps({'timestamp': _utc_now_iso(), 'stream': 'system', 'content': content_msg})}\n\n"
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield f"data: {json.dumps(evt, default=str)}\n\n"
        finally:
            terminal_broadcaster.unsubscribe(q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/v1/rag/health")
async def rag_health():
    state = _ensure_rag_ready()
    if not state["ready"]:
        return {"status": "disabled", "error": state["error"]}
    vector_store = state["vector_store"]
    return {
        "status": "ready",
        "papers_indexed": vector_store.get_collection_count("papers"),
        "runs_indexed": vector_store.get_collection_count("runs"),
    }


@app.get("/api/v1/rag/stats")
async def rag_stats():
    state = _ensure_rag_ready()
    if not state["ready"]:
        return {"status": "disabled", "error": state["error"]}
    vector_store = state["vector_store"]
    papers_count = vector_store.get_collection_count("papers")
    runs_count = vector_store.get_collection_count("runs")
    return {
        "status": "ready",
        "collections": {
            "papers": {
                "count": papers_count,
                "description": "Research papers indexed in vector store",
            },
            "runs": {
                "count": runs_count,
                "description": "Simulation runs indexed in vector store",
            },
        },
        "vector_store": {
            "type": "ChromaDB",
            "location": str(BACKEND_DIR / "rag" / "chroma_db"),
        },
    }


@app.post("/api/v1/rag/query")
async def rag_query(body: RAGQueryRequest):
    state = _ensure_rag_ready()
    if not state["ready"]:
        return {"status": "disabled", "error": state["error"]}
    agent = state["agent"]
    return await agent.invoke(body.query)


@app.post("/api/v1/rag/search/literature")
async def rag_search_literature(body: RAGLiteratureRequest):
    state = _ensure_rag_ready()
    if not state["ready"]:
        return {"status": "disabled", "error": state["error"]}
    agent = state["agent"]
    result = agent.search_literature(body.query, n_results=body.n_results)
    return {"status": "completed", "result": result}


@app.post("/api/v1/rag/search/similar_runs")
async def rag_search_similar_runs(body: RAGSimilarRunsRequest):
    state = _ensure_rag_ready()
    if not state["ready"]:
        return {"status": "disabled", "error": state["error"]}
    agent = state["agent"]
    result = agent.search_similar_runs(
        geometry=body.geometry,
        enrichment=body.enrichment,
        query=body.query,
        n_results=body.n_results,
    )
    return {"status": "completed", "result": result}


@app.get("/api/v1/rag/reproducibility/{run_id}")
async def rag_reproducibility(run_id: str):
    state = _ensure_rag_ready()
    if not state["ready"]:
        return {"status": "disabled", "error": state["error"]}
    agent = state["agent"]
    result = agent.check_reproducibility(run_id)
    return {"status": "completed", "result": result, "run_id": run_id}


@app.post("/api/v1/rag/suggest")
async def rag_suggest(body: RAGSuggestRequest):
    state = _ensure_rag_ready()
    if not state["ready"]:
        return {"status": "disabled", "error": state["error"]}
    agent = state["agent"]
    result = agent.suggest_experiments(
        body.context,
        current_results=body.current_results,
        n_suggestions=body.n_suggestions,
    )
    return {"status": "completed", "result": result}


@app.post("/api/v1/rag/index/papers")
async def rag_index_papers(body: RAGIndexPapersRequest):
    state = _ensure_rag_ready()
    if not state["ready"]:
        return {"status": "disabled", "error": state["error"]}
    pdf_indexer = state["pdf_indexer"]
    if pdf_indexer is None:
        return {"status": "disabled", "error": "PDF indexer unavailable"}
    directory = Path(body.directory) if body.directory else (REPO_ROOT / "RAG" / "docs")
    if not directory.exists():
        return {"status": "error", "error": f"Directory not found: {directory}"}
    pdf_indexer.index_directory(directory)
    return {"status": "completed", "indexed_dir": str(directory)}


@app.post("/api/v1/rag/index/runs")
async def rag_index_runs(body: RAGIndexRunsRequest):
    state = _ensure_rag_ready()
    if not state["ready"]:
        return {"status": "disabled", "error": state["error"]}
    sim_indexer = state["sim_indexer"]
    if sim_indexer is None:
        return {"status": "disabled", "error": "Simulation indexer unavailable"}
    sim_indexer.index_all_runs(limit=body.limit)
    return {"status": "completed", "limit": body.limit}


@app.get("/")
async def root():
    return {
        "name": "AONP Multi-Agent API (v2)",
        "version": "2.0.0",
        "server_time": _utc_now_iso(),
        "endpoints": {
            "query": "/api/v1/query",
            "stream": "/api/v1/query/{query_id}/stream",
            "router": "/api/v1/router",
            "statistics": "/api/v1/statistics",
            "health": "/api/v1/health",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main_v2:app", host=API_HOST, port=API_PORT, reload=True, log_level="info")


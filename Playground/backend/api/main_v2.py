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

from aonp.api.openmc_router import router as openmc_router, set_event_loop as set_openmc_event_loop
from aonp.api.terminal_streamer import terminal_broadcaster, install_terminal_interceptor


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
                return
            MAIN_LOOP.call_soon_threadsafe(asyncio.create_task, self._publish(payload))

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
            yield f"data: {json.dumps({'timestamp': _utc_now_iso(), 'stream': 'system', 'content': '[Connected to terminal stream]\\n'})}\n\n"
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
    return {
        "status": "ready",
        "papers_indexed": vector_store.get_collection_count("papers"),
        "runs_indexed": vector_store.get_collection_count("runs"),
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


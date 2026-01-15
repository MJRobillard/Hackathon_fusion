"""
Compatibility API for query/agent-style endpoints expected by the frontend.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from aonp.api.openmc_router import (
    RUN_RECORDS,
    RUNS_DIR,
    RunRecord,
    get_statistics as get_openmc_stats,
    SimulationSpec,
    SimulationSubmitRequest,
    run_event_bus,
)
import threading
import aonp.api.openmc_router as openmc_router


@dataclass
class QueryRecord:
    query_id: str
    query: str
    status: str = "running"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    routing: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None


QUERY_RECORDS: Dict[str, QueryRecord] = {}


class QueryEventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, query_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(query_id, []).append(queue)
        return queue

    async def publish(self, query_id: str, event: dict):
        if query_id in self._subscribers:
            for queue in list(self._subscribers[query_id]):
                await queue.put(event)

    async def complete(self, query_id: str):
        if query_id in self._subscribers:
            for queue in list(self._subscribers[query_id]):
                await queue.put(None)

    def unsubscribe(self, query_id: str, queue: asyncio.Queue):
        if query_id in self._subscribers:
            self._subscribers[query_id].remove(queue)
            if not self._subscribers[query_id]:
                del self._subscribers[query_id]


query_event_bus = QueryEventBus()
_event_loop: Optional[asyncio.AbstractEventLoop] = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _event_loop
    _event_loop = loop


def _publish_event(query_id: str, event: dict) -> None:
    if _event_loop is None:
        return
    asyncio.run_coroutine_threadsafe(query_event_bus.publish(query_id, event), _event_loop)


def _publish_complete(query_id: str) -> None:
    if _event_loop is None:
        return
    asyncio.run_coroutine_threadsafe(query_event_bus.complete(query_id), _event_loop)


class QueryRequest(BaseModel):
    query: str
    use_llm: bool = Field(default=False)


class QueryResponse(BaseModel):
    query_id: str
    status: str
    routing: Optional[Dict[str, Any]] = None


class RoutingResponse(BaseModel):
    agent: str
    intent: str
    confidence: float
    mode: str


router = APIRouter(prefix="/api/v1", tags=["query"])


def _classify_query(query: str) -> Dict[str, Any]:
    q = query.lower()
    if "sweep" in q or "parameter" in q:
        return {"agent": "sweep", "intent": "parameter_sweep", "confidence": 0.72, "mode": "keyword"}
    if "compare" in q or "analysis" in q:
        return {"agent": "analysis", "intent": "compare_runs", "confidence": 0.7, "mode": "keyword"}
    if "query" in q or "history" in q:
        return {"agent": "query", "intent": "query_results", "confidence": 0.65, "mode": "keyword"}
    return {"agent": "studies", "intent": "run_simulation", "confidence": 0.8, "mode": "keyword"}


def _parse_simulation_params(query: str) -> Dict[str, Any]:
    """Extract simulation parameters from natural language query."""
    q = query.lower()
    
    # Default values
    spec = {
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Water"],
        "enrichment_pct": 4.5,
        "temperature_K": 900.0,
        "particles": 10000,
        "batches": 50,
    }
    
    # Extract enrichment
    import re
    enrichment_match = re.search(r"(\d+\.?\d*)\s*%", q)
    if enrichment_match:
        spec["enrichment_pct"] = float(enrichment_match.group(1))
    
    # Extract temperature
    temp_match = re.search(r"(\d+)\s*k", q)
    if temp_match:
        spec["temperature_K"] = float(temp_match.group(1))
    
    # Extract particles
    particles_match = re.search(r"(\d+)\s*particles?", q)
    if particles_match:
        spec["particles"] = int(particles_match.group(1))
    
    # Extract batches
    batches_match = re.search(r"(\d+)\s*batches?", q)
    if batches_match:
        spec["batches"] = int(batches_match.group(1))
    
    # Geometry detection
    if "bwr" in q:
        spec["geometry"] = "BWR pin cell"
    elif "vver" in q:
        spec["geometry"] = "VVER pin cell"
    
    return spec


async def _simulate_query_flow(query_id: str) -> None:
    query_record = QUERY_RECORDS[query_id]
    routing = query_record.routing or _classify_query(query_record.query)
    query_record.routing = routing

    print(f"[Agent] Query {query_id}: Routing to {routing['agent']} agent (routing={routing})")
    _publish_event(
        query_id,
        {"type": "routing", "message": "Routing query...", "query_id": query_id},
    )
    await asyncio.sleep(0.2)
    _publish_event(
        query_id,
        {
            "type": "routing_complete",
            "agent": routing["agent"],
            "intent": routing["intent"],
            "duration": 0.2,
        },
    )
    await asyncio.sleep(0.2)
    _publish_event(
        query_id,
        {"type": "agent_start", "agent": routing["agent"]},
    )
    await asyncio.sleep(0.2)
    
    # Add agent thinking: analyzing the query
    _publish_event(
        query_id,
        {
            "type": "agent_thinking",
            "agent": routing["agent"],
            "content": f"Analyzing query: '{query_record.query}'",
            "metadata": {"query": query_record.query, "intent": routing["intent"]},
        },
    )
    await asyncio.sleep(0.2)
    
    _publish_event(
        query_id,
        {
            "type": "agent_progress",
            "agent": routing["agent"],
            "message": "Preparing execution plan...",
        },
    )
    await asyncio.sleep(0.2)
    
    # For studies agent, actually execute OpenMC
    agent_name = str(routing.get("agent", "")).lower().strip()
    print(f"[Agent] Checking agent type: '{agent_name}' == 'studies'? {agent_name == 'studies'}")
    print(f"[Agent] Full routing dict: {routing}")
    if agent_name == "studies":
        print(f"[Agent] Studies agent: Parsing query and submitting OpenMC simulation")
        
        # Agent thinking: parsing the query
        _publish_event(
            query_id,
            {
                "type": "agent_thinking",
                "agent": routing["agent"],
                "content": "Parsing query to extract simulation parameters (geometry, enrichment, temperature, etc.)",
                "metadata": {"query": query_record.query},
            },
        )
        await asyncio.sleep(0.2)
        
        spec_dict = _parse_simulation_params(query_record.query)
        
        # Agent planning: execution plan generated
        print(f"[Agent] Generated execution plan: {spec_dict}")
        _publish_event(
            query_id,
            {
                "type": "agent_planning",
                "agent": routing["agent"],
                "content": f"Generated execution plan: {spec_dict['geometry']} with {spec_dict['enrichment_pct']}% enrichment, {spec_dict['particles']} particles, {spec_dict['batches']} batches",
                "metadata": {"spec": spec_dict},
            },
        )
        await asyncio.sleep(0.2)
        
        # Agent decision: deciding to submit
        _publish_event(
            query_id,
            {
                "type": "agent_decision",
                "agent": routing["agent"],
                "content": "Decision: Submit OpenMC simulation with parsed parameters",
                "metadata": {"spec": spec_dict},
            },
        )
        await asyncio.sleep(0.2)
        
        _publish_event(
            query_id,
            {
                "type": "tool_call",
                "agent": routing["agent"],
                "tool_name": "submit_study",
                "message": f"Submitting OpenMC simulation: {spec_dict['geometry']} with {spec_dict['enrichment_pct']}% enrichment",
                "args": {"spec": spec_dict, "query": query_record.query},
            },
        )
        await asyncio.sleep(0.2)
        
        try:
            # Submit actual OpenMC simulation
            spec = SimulationSpec(**spec_dict)
            run_id = f"q_{query_id}_run_{uuid4().hex[:8]}"
            
            # Create run record (use different variable name to avoid shadowing)
            run_record = RunRecord(run_id=run_id, spec=spec_dict)
            RUN_RECORDS[run_id] = run_record
            
            print(f"[Agent] OpenMC simulation submitted: {run_id}")
            print(f"[Agent] Spec: {spec_dict}")
            
            # Start execution in background thread (access private function via module)
            thread = threading.Thread(
                target=openmc_router._execute_openmc_run, args=(run_id, spec_dict), daemon=True
            )
            thread.start()
            
            _publish_event(
                query_id,
                {
                    "type": "tool_result",
                    "agent": routing["agent"],
                    "tool_name": "submit_study",
                    "message": f"OpenMC simulation {run_id} submitted successfully",
                    "result": {
                        "run_id": run_id,
                        "status": "queued",
                        "summary": f"OpenMC simulation {run_id} submitted successfully",
                    },
                },
            )
            
            # Agent observation: simulation submitted
            _publish_event(
                query_id,
                {
                    "type": "agent_observation",
                    "agent": routing["agent"],
                    "content": f"Simulation {run_id} queued and starting execution",
                    "metadata": {"run_id": run_id, "status": "queued"},
                },
            )
            
            # Monitor run completion and forward OpenMC events to query stream
            await asyncio.sleep(1.0)
            _publish_event(
                query_id,
                {
                    "type": "agent_thinking",
                    "agent": routing["agent"],
                    "content": "Monitoring simulation execution...",
                    "metadata": {"run_id": run_id},
                },
            )
            
            # Subscribe to OpenMC run events and forward tool calls/results to query stream
            async def forward_openmc_events():
                queue = run_event_bus.subscribe(run_id)
                try:
                    while run_id in RUN_RECORDS and RUN_RECORDS[run_id].status in {"queued", "running"}:
                        try:
                            event = await asyncio.wait_for(queue.get(), timeout=1.0)
                            if event is None:
                                break
                            # Forward tool_call and tool_result events to query stream
                            if event.get("type") in {"tool_call", "tool_result"}:
                                _publish_event(query_id, event)
                        except asyncio.TimeoutError:
                            continue
                finally:
                    run_event_bus.unsubscribe(run_id, queue)
            
            # Start forwarding in background
            forward_task = asyncio.create_task(forward_openmc_events())
            
            while run_id in RUN_RECORDS and RUN_RECORDS[run_id].status == "running":
                await asyncio.sleep(2.0)
            
            # Cancel forwarding task
            forward_task.cancel()
            try:
                await forward_task
            except asyncio.CancelledError:
                pass
            
            if run_id in RUN_RECORDS:
                completed_run_record = RUN_RECORDS[run_id]
                if completed_run_record.status == "completed":
                    _publish_event(
                        query_id,
                        {
                            "type": "agent_progress",
                            "agent": routing["agent"],
                            "message": f"Simulation completed: k-eff = {completed_run_record.keff:.5f} ± {completed_run_record.keff_std:.5f}",
                        },
                    )
                    _publish_event(
                        query_id,
                        {
                            "type": "agent_observation",
                            "agent": routing["agent"],
                            "content": f"Simulation completed successfully: k-eff = {completed_run_record.keff:.5f} ± {completed_run_record.keff_std:.5f}",
                            "metadata": {
                                "run_id": run_id,
                                "keff": completed_run_record.keff,
                                "keff_std": completed_run_record.keff_std,
                            },
                        },
                    )
                    query_record.result = {
                        "message": f"Simulation completed successfully",
                        "run_id": run_id,
                        "keff": completed_run_record.keff,
                        "keff_std": completed_run_record.keff_std,
                        "agent": routing["agent"],
                        "intent": routing["intent"],
                    }
                elif completed_run_record.status == "failed":
                    _publish_event(
                        query_id,
                        {
                            "type": "agent_progress",
                            "agent": routing["agent"],
                            "message": f"Simulation failed: {completed_run_record.error}",
                        },
                    )
                    _publish_event(
                        query_id,
                        {
                            "type": "agent_observation",
                            "agent": routing["agent"],
                            "content": f"Simulation failed: {completed_run_record.error}",
                            "metadata": {"run_id": run_id, "error": completed_run_record.error},
                        },
                    )
                    query_record.result = {
                        "message": f"Simulation failed: {completed_run_record.error}",
                        "run_id": run_id,
                        "agent": routing["agent"],
                        "intent": routing["intent"],
                    }
        except Exception as exc:
            import traceback
            print(f"[Agent] Error submitting OpenMC: {exc}")
            print(f"[Agent] Traceback: {traceback.format_exc()}")
            _publish_event(
                query_id,
                {
                    "type": "tool_result",
                    "agent": routing["agent"],
                    "tool_name": "submit_study",
                    "result": {"error": str(exc), "summary": f"Failed to submit simulation: {exc}"},
                },
            )
            query_record.result = {
                "message": f"Error: {exc}",
                "agent": routing["agent"],
                "intent": routing["intent"],
            }
    else:
        # For other agents, just simulate
        print(f"[Agent] Non-studies agent ({routing['agent']}), using plan_execution")
        _publish_event(
            query_id,
            {
                "type": "agent_thinking",
                "agent": routing["agent"],
                "content": f"Processing query with {routing['agent']} agent for intent: {routing['intent']}",
                "metadata": {"query": query_record.query, "intent": routing["intent"]},
            },
        )
        await asyncio.sleep(0.2)
        
        _publish_event(
            query_id,
            {
                "type": "tool_call",
                "agent": routing["agent"],
                "tool_name": "plan_execution",
                "message": "Generated execution plan",
                "args": {"query": query_record.query},
            },
        )
        await asyncio.sleep(0.2)
        _publish_event(
            query_id,
            {
                "type": "tool_result",
                "agent": routing["agent"],
                "tool_name": "plan_execution",
                "message": "Execution plan ready",
                "result": {"summary": "Execution plan ready."},
            },
        )
        await asyncio.sleep(0.2)
        
        query_record.result = {
            "message": "Query processed in compatibility mode.",
            "agent": routing["agent"],
            "intent": routing["intent"],
        }

    query_record.status = "completed"
    _publish_event(query_id, {"type": "query_complete"})
    _publish_complete(query_id)


@router.post("/query", response_model=QueryResponse)
async def submit_query(request: QueryRequest):
    query_id = f"q_{uuid4().hex[:12]}"
    routing = _classify_query(request.query)
    record = QueryRecord(query_id=query_id, query=request.query, routing=routing)
    QUERY_RECORDS[query_id] = record

    if _event_loop is not None:
        asyncio.run_coroutine_threadsafe(_simulate_query_flow(query_id), _event_loop)

    return QueryResponse(query_id=query_id, status=record.status, routing=routing)


@router.get("/query/{query_id}")
def get_query(query_id: str):
    record = QUERY_RECORDS.get(query_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    return {
        "query_id": record.query_id,
        "status": record.status,
        "routing": record.routing,
        "result": record.result,
    }


@router.get("/query/{query_id}/stream")
async def stream_query_events(query_id: str):
    if query_id not in QUERY_RECORDS:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")

    async def event_generator():
        queue = query_event_bus.subscribe(query_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                if event is None:
                    break

                event_type = event.get("type", "message")
                payload = dict(event)
                payload.pop("type", None)
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(payload)}\n\n"
        finally:
            query_event_bus.unsubscribe(query_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/router", response_model=RoutingResponse)
def test_router(request: QueryRequest):
    routing = _classify_query(request.query)
    return RoutingResponse(**routing)


@router.get("/statistics")
def get_statistics():
    openmc_stats = get_openmc_stats()
    return {
        "total_studies": 0,
        "total_runs": openmc_stats.get("total_runs", 0),
        "completed_runs": openmc_stats.get("completed_runs", 0),
        "running_runs": openmc_stats.get("running_runs", 0),
        "failed_runs": openmc_stats.get("failed_runs", 0),
    }


@router.get("/health")
def health_check():
    openmc_available = True
    try:
        import openmc  # type: ignore
    except Exception:
        openmc_available = False
    return {
        "status": "healthy",
        "services": {
            "mongodb": False,
            "openmc": openmc_available,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_runs": len([r for r in RUN_RECORDS.values() if r.status == "running"]),
    }


@router.get("/orchestration/config")
def get_orchestration_config():
    return {
        "convergence": {"enabled": False},
        "tool_prompts": {},
    }


@router.patch("/orchestration/config")
def patch_orchestration_config(patch: Dict[str, Any]):
    return {"status": "ok", "applied": patch}


@router.get("/visualizations/run/{run_id}")
def visualization_run(run_id: str):
    return {"status": "not_available", "run_id": run_id, "data": []}


@router.get("/visualizations/sweep")
def visualization_sweep(run_ids: str):
    return {"status": "not_available", "run_ids": run_ids.split(","), "data": []}


@router.post("/visualizations/comparison")
def visualization_comparison(payload: Dict[str, Any]):
    return {"status": "not_available", "run_ids": payload.get("run_ids", []), "data": []}


@router.get("/db/collections")
def db_collections():
    return []


@router.get("/db/{collection}")
def db_documents(collection: str, limit: int = 50, skip: int = 0):
    return []


@router.get("/db/{collection}/{doc_id}")
def db_document(collection: str, doc_id: str):
    raise HTTPException(status_code=404, detail="Document not found")


@router.get("/db/{collection}/count")
def db_collection_count(collection: str):
    return {"count": 0}


@router.post("/rag/query")
def rag_query(payload: Dict[str, Any]):
    return {"status": "disabled", "message": "RAG is not configured."}


@router.post("/rag/search/literature")
def rag_search_literature(payload: Dict[str, Any]):
    return {"status": "disabled", "results": []}


@router.post("/rag/search/similar_runs")
def rag_search_similar_runs(payload: Dict[str, Any]):
    return {"status": "disabled", "results": []}


@router.get("/rag/reproducibility/{run_id}")
def rag_reproducibility(run_id: str):
    return {"status": "disabled", "run_id": run_id}


@router.post("/rag/suggest")
def rag_suggest(payload: Dict[str, Any]):
    return {"status": "disabled", "suggestions": []}


@router.get("/rag/stats")
def rag_stats():
    return {"status": "disabled"}


@router.get("/rag/health")
def rag_health():
    return {"status": "disabled"}


@router.post("/rag/index/papers")
def rag_index_papers(payload: Dict[str, Any]):
    return {"status": "disabled"}


@router.post("/rag/index/runs")
def rag_index_runs(payload: Dict[str, Any]):
    return {"status": "disabled"}

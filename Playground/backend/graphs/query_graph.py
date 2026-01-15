"""
LangGraph-based orchestration for the multi-agent query pipeline.

This replaces the monolithic `MultiAgentOrchestrator.process_query` call with an
explicit state machine that:
- Emits the same SSE events the frontend expects (routing/agent_start/etc.)
- Is traceable in LangSmith via `LANGCHAIN_*` environment variables
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    # Optional LangSmith tracing decorator
    from langsmith import traceable  # type: ignore
except Exception:  # pragma: no cover

    def traceable(*args, **kwargs):  # type: ignore
        def _wrap(fn):
            return fn

        return _wrap


try:
    from typing_extensions import TypedDict
except Exception:  # pragma: no cover
    from typing import TypedDict  # type: ignore


try:
    from langgraph.graph import StateGraph, END  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "langgraph is required for query_graph. Install `langgraph`."
    ) from e


@dataclass
class QueryGraphContext:
    query_id: str
    event_bus: Any
    mongodb: Any
    use_llm: bool
    thinking_callback: Any

    async def publish(self, event: Dict[str, Any]) -> None:
        await self.event_bus.publish(self.query_id, event)


class QueryGraphState(TypedDict, total=False):
    ctx: QueryGraphContext
    query: str

    routing: Dict[str, Any]
    assigned_agent: str
    intent: str

    results: Dict[str, Any]
    agent_path: List[str]
    tool_calls: List[str]

    error: str


@traceable(name="route_query")
async def route_node(state: QueryGraphState) -> QueryGraphState:
    ctx = state["ctx"]
    query = state["query"]

    from multi_agent_system import RouterAgent

    # Emit a lightweight routing progress event (frontend shows this as "Routing query...")
    await ctx.publish(
        {
            "type": "routing",
            "message": "Routing query...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    await ctx.publish(
        {
            "type": "agent_start",
            "agent": "router",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    router = RouterAgent(use_llm=ctx.use_llm, thinking_callback=ctx.thinking_callback)
    loop = asyncio.get_running_loop()
    routing = await loop.run_in_executor(None, router.route_query, query)

    await ctx.publish(
        {
            "type": "routing_complete",
            "agent": routing.get("agent"),
            "intent": routing.get("intent"),
            "duration": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    agent = routing.get("agent") or "studies"
    intent = routing.get("intent") or "unknown"

    return {
        "routing": routing,
        "assigned_agent": agent,
        "intent": intent,
        "agent_path": ["router", agent],
    }


def _route_to_agent_node(state: QueryGraphState) -> str:
    agent = (state.get("assigned_agent") or state.get("routing", {}).get("agent") or "studies").lower()
    if agent in {"studies", "sweep", "query", "analysis", "rag_copilot"}:
        return agent
    return "studies"


async def _run_agent(
    *,
    ctx: QueryGraphContext,
    agent_key: str,
    query_context: Dict[str, Any],
) -> Dict[str, Any]:
    from multi_agent_system import StudiesAgent, SweepAgent, QueryAgent, AnalysisAgent

    await ctx.publish(
        {
            "type": "agent_start",
            "agent": agent_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    # Instantiate agent (best-effort pass thinking_callback when supported)
    if agent_key == "studies":
        agent = StudiesAgent(thinking_callback=ctx.thinking_callback)
    elif agent_key == "sweep":
        agent = SweepAgent(thinking_callback=ctx.thinking_callback)
    elif agent_key == "query":
        agent = QueryAgent(thinking_callback=ctx.thinking_callback)
    elif agent_key == "analysis":
        agent = AnalysisAgent(thinking_callback=ctx.thinking_callback)
    else:
        # Unknown → treat as studies for safety
        agent = StudiesAgent(thinking_callback=ctx.thinking_callback)

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, agent.execute, query_context)
    return result if isinstance(result, dict) else {"result": result}


@traceable(name="run_studies_agent")
async def studies_node(state: QueryGraphState) -> QueryGraphState:
    ctx = state["ctx"]
    routing = state.get("routing", {})
    results = await _run_agent(ctx=ctx, agent_key="studies", query_context=routing.get("context", {"query": state["query"]}))
    return {"results": results}


@traceable(name="run_sweep_agent")
async def sweep_node(state: QueryGraphState) -> QueryGraphState:
    ctx = state["ctx"]
    routing = state.get("routing", {})
    results = await _run_agent(ctx=ctx, agent_key="sweep", query_context=routing.get("context", {"query": state["query"]}))
    return {"results": results}


@traceable(name="run_query_agent")
async def query_node(state: QueryGraphState) -> QueryGraphState:
    ctx = state["ctx"]
    routing = state.get("routing", {})
    results = await _run_agent(ctx=ctx, agent_key="query", query_context=routing.get("context", {"query": state["query"]}))
    return {"results": results}


@traceable(name="run_analysis_agent")
async def analysis_node(state: QueryGraphState) -> QueryGraphState:
    ctx = state["ctx"]
    routing = state.get("routing", {})
    results = await _run_agent(ctx=ctx, agent_key="analysis", query_context=routing.get("context", {"query": state["query"]}))
    return {"results": results}


@traceable(name="finalize_query")
async def finalize_node(state: QueryGraphState) -> QueryGraphState:
    """
    Persist final status/results to MongoDB and emit query_complete.
    """
    ctx = state["ctx"]

    # Compute duration from created_at (stored when query was submitted)
    completed_at = datetime.now(timezone.utc)
    created_at_doc = await ctx.mongodb.queries.find_one({"query_id": ctx.query_id})
    created_at = created_at_doc.get("created_at") if created_at_doc else None
    if created_at and getattr(created_at, "tzinfo", None) is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    duration = (completed_at - created_at).total_seconds() if created_at else None

    results = state.get("results")
    tool_calls = list(results.keys()) if isinstance(results, dict) else []

    await ctx.mongodb.queries.update_one(
        {"query_id": ctx.query_id},
        {
            "$set": {
                "status": "completed",
                "completed_at": completed_at,
                "duration_seconds": duration,
                "assigned_agent": state.get("assigned_agent"),
                "intent": state.get("intent"),
                "results": results,
                "agent_path": state.get("agent_path", []),
                "tool_calls": tool_calls,
            }
        },
    )

    await ctx.publish(
        {
            "type": "query_complete",
            "status": "completed",
            "timestamp": completed_at.isoformat(),
        }
    )

    return {"tool_calls": tool_calls}


def build_query_graph():
    g: StateGraph = StateGraph(QueryGraphState)

    g.add_node("route", route_node)
    g.add_node("studies", studies_node)
    g.add_node("sweep", sweep_node)
    g.add_node("query", query_node)
    g.add_node("analysis", analysis_node)
    g.add_node("finalize", finalize_node)

    g.set_entry_point("route")
    g.add_conditional_edges(
        "route",
        _route_to_agent_node,
        {
            "studies": "studies",
            "sweep": "sweep",
            "query": "query",
            "analysis": "analysis",
            # rag_copilot not yet supported in this graph path
            "rag_copilot": "query",
        },
    )

    # All agent nodes flow to finalize
    g.add_edge("studies", "finalize")
    g.add_edge("sweep", "finalize")
    g.add_edge("query", "finalize")
    g.add_edge("analysis", "finalize")

    g.add_edge("finalize", END)

    return g.compile()



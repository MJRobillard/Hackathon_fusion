"""
AONP Multi-Agent System with LangGraph
AI agents for nuclear simulation experiment design, execution, and analysis
"""

import os
import json
from typing import TypedDict, Annotated, Sequence, Literal
import operator

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_fireworks import ChatFireworks
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

# Import our agent tools
from agent_tools import (
    submit_study,
    query_results,
    generate_sweep,
    compare_runs,
    get_study_statistics
)

load_dotenv()

# ============================================================================
# LLM SETUP
# ============================================================================

llm = ChatFireworks(
    api_key=os.getenv("FIREWORKS"),
    model="accounts/robillard-matthew22/deployedModels/nvidia-nemotron-nano-9b-v2-nsoeqcp4",
    temperature=0.7
)

# ============================================================================
# STATE DEFINITION
# ============================================================================

class AONPAgentState(TypedDict):
    """State for AONP multi-agent workflow"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_request: str
    intent: str | None  # "single_study", "sweep", "query", "compare"
    study_spec: dict | None
    sweep_config: dict | None
    run_ids: list[str] | None
    results: dict | None
    analysis: str | None
    suggestion: str | None
    next_action: str

# ============================================================================
# AGENT 1: INTENT CLASSIFIER
# ============================================================================

def intent_classifier_agent(state: AONPAgentState) -> AONPAgentState:
    """
    Agent 1: Classify user intent
    Determines what type of action the user wants
    """
    print("\n>> [INTENT CLASSIFIER] Analyzing request...")
    
    system_prompt = """You are an intent classifier for nuclear simulation requests.
    
Classify the user's request into ONE of these intents:
- "single_study" - User wants to run one specific simulation
- "sweep" - User wants to vary a parameter and run multiple simulations
- "query" - User wants to search/analyze past results
- "compare" - User wants to compare specific runs

Respond with ONLY the intent category, nothing else."""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User request: {state['user_request']}")
    ]
    
    response = llm.invoke(messages)
    intent = response.content.strip().lower().replace('"', '')
    
    print(f"   Detected intent: {intent}")
    
    # Route to appropriate next agent
    next_action_map = {
        "single_study": "plan_study",
        "sweep": "plan_sweep",
        "query": "execute_query",
        "compare": "execute_compare"
    }
    
    next_action = next_action_map.get(intent, "plan_study")
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "intent": intent,
        "next_action": next_action
    }

# ============================================================================
# AGENT 2: STUDY PLANNER
# ============================================================================

def study_planner_agent(state: AONPAgentState) -> AONPAgentState:
    """
    Agent 2: Plan a single study
    Extracts study specification from natural language
    """
    print("\n>> [STUDY PLANNER] Designing study spec...")
    
    system_prompt = """You are a nuclear reactor physics expert.
    
Extract a simulation study specification from the user's request.
Output ONLY valid JSON with this structure:
{
    "geometry": "description (e.g., PWR pin cell, BWR assembly)",
    "materials": ["list", "of", "materials"],
    "enrichment_pct": float or null,
    "temperature_K": float or null,
    "particles": int (default 10000),
    "batches": int (default 50)
}

Use reasonable defaults if not specified. Output JSON only, no explanation."""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User request: {state['user_request']}")
    ]
    
    response = llm.invoke(messages)
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        spec = json.loads(content.strip())
    except Exception as e:
        print(f"   [WARNING] Failed to parse LLM output: {e}")
        # Fallback spec
        spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Zircaloy", "Water"],
            "enrichment_pct": 4.5,
            "temperature_K": 600,
            "particles": 10000,
            "batches": 50
        }
    
    print(f"   Geometry: {spec.get('geometry')}")
    print(f"   Enrichment: {spec.get('enrichment_pct')}%")
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "study_spec": spec,
        "next_action": "execute_study"
    }

# ============================================================================
# AGENT 3: SWEEP PLANNER
# ============================================================================

def sweep_planner_agent(state: AONPAgentState) -> AONPAgentState:
    """
    Agent 3: Plan parameter sweep
    Extracts base spec and sweep parameters
    """
    print("\n>> [SWEEP PLANNER] Designing parameter sweep...")
    
    system_prompt = """You are a nuclear reactor physics expert.
    
Extract a parameter sweep configuration from the user's request.
Output ONLY valid JSON with this structure:
{
    "base_spec": {
        "geometry": "description",
        "materials": ["list"],
        "enrichment_pct": float or null,
        "temperature_K": float or null,
        "particles": int,
        "batches": int
    },
    "param_name": "name of parameter to vary (e.g., enrichment_pct, temperature_K)",
    "param_values": [list, of, values, to, sweep]
}

Generate sensible sweep ranges (e.g., 3-5% enrichment, 300-900K temperature).
Output JSON only, no explanation."""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User request: {state['user_request']}")
    ]
    
    response = llm.invoke(messages)
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        sweep_config = json.loads(content.strip())
    except Exception as e:
        print(f"   [WARNING] Failed to parse LLM output: {e}")
        # Fallback sweep
        sweep_config = {
            "base_spec": {
                "geometry": "PWR pin cell",
                "materials": ["UO2", "Zircaloy", "Water"],
                "temperature_K": 600,
                "particles": 10000,
                "batches": 50
            },
            "param_name": "enrichment_pct",
            "param_values": [3.0, 3.5, 4.0, 4.5, 5.0]
        }
    
    print(f"   Sweeping: {sweep_config['param_name']}")
    print(f"   Range: {sweep_config['param_values']}")
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "sweep_config": sweep_config,
        "next_action": "execute_sweep"
    }

# ============================================================================
# AGENT 4: STUDY EXECUTOR
# ============================================================================

def study_executor_agent(state: AONPAgentState) -> AONPAgentState:
    """
    Agent 4: Execute single study
    Calls submit_study tool
    """
    print("\n>> [EXECUTOR] Running simulation...")
    
    try:
        result = submit_study(state["study_spec"])
        
        return {
            **state,
            "run_ids": [result["run_id"]],
            "results": result,
            "messages": state["messages"] + [AIMessage(
                content=f"Simulation complete: keff = {result['keff']:.5f} +/- {result['keff_std']:.6f}"
            )],
            "next_action": "analyze"
        }
    except Exception as e:
        print(f"   [ERROR] Execution failed: {e}")
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=f"Error: {e}")],
            "next_action": "end"
        }

# ============================================================================
# AGENT 5: SWEEP EXECUTOR
# ============================================================================

def sweep_executor_agent(state: AONPAgentState) -> AONPAgentState:
    """
    Agent 5: Execute parameter sweep
    Calls generate_sweep tool
    """
    print("\n>> [SWEEP EXECUTOR] Running parameter sweep...")
    
    try:
        config = state["sweep_config"]
        run_ids = generate_sweep(
            base_spec=config["base_spec"],
            param_name=config["param_name"],
            param_values=config["param_values"]
        )
        
        # Get comparison
        comparison = compare_runs(run_ids)
        
        return {
            **state,
            "run_ids": run_ids,
            "results": comparison,
            "messages": state["messages"] + [AIMessage(
                content=f"Sweep complete: {len(run_ids)} runs, keff range [{comparison['keff_min']:.5f}, {comparison['keff_max']:.5f}]"
            )],
            "next_action": "analyze"
        }
    except Exception as e:
        print(f"   [ERROR] Sweep failed: {e}")
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=f"Error: {e}")],
            "next_action": "end"
        }

# ============================================================================
# AGENT 6: QUERY EXECUTOR
# ============================================================================

def query_executor_agent(state: AONPAgentState) -> AONPAgentState:
    """
    Agent 6: Execute query on past results
    """
    print("\n>> [QUERY EXECUTOR] Searching database...")
    
    # For now, use simple keyword matching to construct filter
    # In production, use LLM to parse query into MongoDB filter
    request_lower = state["user_request"].lower()
    
    filter_params = {}
    if "pwr" in request_lower:
        filter_params["spec.geometry"] = {"$regex": "PWR", "$options": "i"}
    if "bwr" in request_lower:
        filter_params["spec.geometry"] = {"$regex": "BWR", "$options": "i"}
    if "critical" in request_lower:
        filter_params["keff"] = {"$gte": 1.0}
    
    try:
        results = query_results(filter_params, limit=10)
        
        summary = f"Found {len(results)} matching results"
        if results:
            summary += f"\nAverage keff: {sum(r['keff'] for r in results) / len(results):.5f}"
        
        return {
            **state,
            "results": {"query_results": results, "count": len(results)},
            "messages": state["messages"] + [AIMessage(content=summary)],
            "next_action": "analyze"
        }
    except Exception as e:
        print(f"   [ERROR] Query failed: {e}")
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=f"Error: {e}")],
            "next_action": "end"
        }

# ============================================================================
# AGENT 7: ANALYZER
# ============================================================================

def analyzer_agent(state: AONPAgentState) -> AONPAgentState:
    """
    Agent 7: Analyze results
    Interprets simulation outcomes
    """
    print("\n>> [ANALYZER] Analyzing results...")
    
    system_prompt = """You are a nuclear reactor physicist analyzing simulation results.

Provide a brief analysis (under 100 words) covering:
1. Key findings (criticality, trends, anomalies)
2. Physical interpretation
3. Confidence in results

Be technical but concise."""
    
    # Format results for analysis
    results_text = json.dumps(state.get("results", {}), indent=2)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Results to analyze:\n{results_text}")
    ]
    
    response = llm.invoke(messages)
    analysis = response.content
    
    print(f"   {analysis[:100]}...")
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "analysis": analysis,
        "next_action": "suggest"
    }

# ============================================================================
# AGENT 8: SUGGESTION ENGINE
# ============================================================================

def suggestion_agent(state: AONPAgentState) -> AONPAgentState:
    """
    Agent 8: Suggest next experiments
    Recommends follow-up studies
    """
    print("\n>> [SUGGESTER] Generating recommendations...")
    
    system_prompt = """You are a nuclear reactor physicist suggesting follow-up experiments.

Based on the results and analysis, suggest 2-3 specific next experiments that would:
1. Validate/refine findings
2. Explore interesting trends
3. Fill knowledge gaps

Format as a numbered list, be specific about parameters."""
    
    context = f"""
User request: {state['user_request']}
Analysis: {state.get('analysis', 'N/A')}
Results summary: {json.dumps(state.get('results', {}), indent=2)[:500]}
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=context)
    ]
    
    response = llm.invoke(messages)
    suggestion = response.content
    
    print(f"   Generated {suggestion.count('1.')} suggestions")
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "suggestion": suggestion,
        "next_action": "end"
    }

# ============================================================================
# ROUTING
# ============================================================================

def route_next_agent(state: AONPAgentState) -> str:
    """Route to next agent based on state"""
    routing = {
        "classify": "intent_classifier",
        "plan_study": "study_planner",
        "plan_sweep": "sweep_planner",
        "execute_study": "study_executor",
        "execute_sweep": "sweep_executor",
        "execute_query": "query_executor",
        "execute_compare": "query_executor",  # Same handler
        "analyze": "analyzer",
        "suggest": "suggester",
        "end": END
    }
    
    next_action = state.get("next_action", "end")
    return routing.get(next_action, END)

# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_aonp_graph():
    """Build the AONP multi-agent graph"""
    workflow = StateGraph(AONPAgentState)
    
    # Add all agents
    workflow.add_node("intent_classifier", intent_classifier_agent)
    workflow.add_node("study_planner", study_planner_agent)
    workflow.add_node("sweep_planner", sweep_planner_agent)
    workflow.add_node("study_executor", study_executor_agent)
    workflow.add_node("sweep_executor", sweep_executor_agent)
    workflow.add_node("query_executor", query_executor_agent)
    workflow.add_node("analyzer", analyzer_agent)
    workflow.add_node("suggester", suggestion_agent)
    
    # Set entry point
    workflow.set_entry_point("intent_classifier")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "intent_classifier",
        route_next_agent,
        {
            "study_planner": "study_planner",
            "sweep_planner": "sweep_planner",
            "query_executor": "query_executor"
        }
    )
    
    workflow.add_conditional_edges("study_planner", route_next_agent, {"study_executor": "study_executor"})
    workflow.add_conditional_edges("sweep_planner", route_next_agent, {"sweep_executor": "sweep_executor"})
    workflow.add_conditional_edges("study_executor", route_next_agent, {"analyzer": "analyzer", END: END})
    workflow.add_conditional_edges("sweep_executor", route_next_agent, {"analyzer": "analyzer", END: END})
    workflow.add_conditional_edges("query_executor", route_next_agent, {"analyzer": "analyzer", END: END})
    workflow.add_conditional_edges("analyzer", route_next_agent, {"suggester": "suggester"})
    workflow.add_conditional_edges("suggester", route_next_agent, {END: END})
    
    return workflow.compile()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_aonp_agent(user_request: str):
    """Execute AONP agent workflow"""
    print("=" * 80)
    print("AONP MULTI-AGENT SYSTEM")
    print("=" * 80)
    print(f"\n[USER REQUEST] {user_request}\n")
    
    app = create_aonp_graph()
    
    initial_state = AONPAgentState(
        messages=[],
        user_request=user_request,
        intent=None,
        study_spec=None,
        sweep_config=None,
        run_ids=None,
        results=None,
        analysis=None,
        suggestion=None,
        next_action="classify"
    )
    
    final_state = app.invoke(initial_state)
    
    print("\n" + "=" * 80)
    print("FINAL OUTPUT")
    print("=" * 80)
    
    if final_state.get("analysis"):
        print("\n[ANALYSIS]")
        print(final_state["analysis"])
    
    if final_state.get("suggestion"):
        print("\n[SUGGESTIONS]")
        print(final_state["suggestion"])
    
    if final_state.get("results"):
        print("\n[RESULTS SUMMARY]")
        results = final_state["results"]
        if "keff" in results:
            print(f"  keff = {results['keff']:.5f} +/- {results['keff_std']:.6f}")
        elif "keff_mean" in results:
            print(f"  keff range: [{results['keff_min']:.5f}, {results['keff_max']:.5f}]")
            print(f"  keff mean: {results['keff_mean']:.5f}")
    
    print("\n" + "=" * 80)
    return final_state


if __name__ == "__main__":
    # Example usage
    run_aonp_agent("Simulate a PWR pin cell with 4.5% enriched UO2 at 600K")


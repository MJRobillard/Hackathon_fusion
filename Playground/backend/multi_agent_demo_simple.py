"""
Simplified Multi-Agent Demo
Works even without Fireworks API (uses mock LLM responses)
"""

import os
import json
import random
import time
from typing import TypedDict, Annotated, Sequence
import operator

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Try to import real APIs, fallback to mocks
try:
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
    from langchain_fireworks import ChatFireworks
    from langgraph.graph import StateGraph, END
    import voyageai
    
    load_dotenv()
    
    # Check if Fireworks key exists
    FIREWORKS_KEY = os.getenv("FIREWORKS")
    USE_REAL_LLM = bool(FIREWORKS_KEY)
    
    if USE_REAL_LLM:
        llm = ChatFireworks(
            api_key=FIREWORKS_KEY,
            model="accounts/robillard-matthew22/deployedModels/nvidia-nemotron-nano-9b-v2-nsoeqcp4",
            temperature=0.7
        )
    
    # Check Voyage
    VOYAGE_KEY = os.getenv("VOYAGE")
    USE_REAL_EMBEDDINGS = bool(VOYAGE_KEY)
    
    if USE_REAL_EMBEDDINGS:
        voyage_client = voyageai.Client(api_key=VOYAGE_KEY)
    
except ImportError:
    USE_REAL_LLM = False
    USE_REAL_EMBEDDINGS = False
    print("[WARNING] Using mock responses - install dependencies for full functionality")

# ============================================================================
# MOCK LLM
# ============================================================================

class MockAIMessage:
    def __init__(self, content: str):
        self.content = content

def mock_llm_call(prompt: str) -> MockAIMessage:
    """Mock LLM responses for demo purposes"""
    if "simulation specification" in prompt.lower():
        spec = {
            "geometry": "PWR pin cell with fuel pellet and cladding",
            "materials": ["UO2 fuel (4.5% enrichment)", "Zircaloy cladding", "Light water coolant"],
            "particles": 10000,
            "batches": 50
        }
        return MockAIMessage(json.dumps(spec))
    
    elif "validate" in prompt.lower() or "review" in prompt.lower():
        return MockAIMessage("APPROVED: Realistic PWR parameters with appropriate particle count and batch size.")
    
    elif "analyze" in prompt.lower() or "interpret" in prompt.lower():
        return MockAIMessage(
            "The keff value of 1.287 indicates a supercritical system, typical for fresh PWR fuel. "
            "The low standard deviation demonstrates good statistical convergence. "
            "Recommend adding control rods for criticality control."
        )
    
    return MockAIMessage("Mock response")

# ============================================================================
# SIMULATION MODELS
# ============================================================================

class SimulationSpec(BaseModel):
    geometry: str
    materials: list[str]
    particles: int
    batches: int

class SimulationResult(BaseModel):
    keff: float
    keff_std: float
    runtime_seconds: float
    status: str

def mock_openmc_run(spec: SimulationSpec) -> SimulationResult:
    """Mock OpenMC execution"""
    time.sleep(0.5)
    base_keff = 1.285
    keff = base_keff + random.uniform(-0.05, 0.05)
    keff_std = 0.00023 + random.uniform(0, 0.0001)
    
    return SimulationResult(
        keff=keff,
        keff_std=keff_std,
        runtime_seconds=0.5,
        status="completed"
    )

# ============================================================================
# STATE
# ============================================================================

class AgentState(TypedDict):
    messages: Annotated[Sequence, operator.add]
    user_request: str
    simulation_spec: dict | None
    validation_passed: bool
    simulation_result: dict | None
    analysis: str | None
    next_action: str

# ============================================================================
# AGENTS
# ============================================================================

def planner_agent(state: AgentState) -> AgentState:
    print("\n>> [PLANNER AGENT] Designing simulation...")
    
    prompt = f"Create simulation specification for: {state['user_request']}"
    
    if USE_REAL_LLM:
        response = llm.invoke([
            SystemMessage(content="Create a simulation spec as JSON."),
            HumanMessage(content=prompt)
        ])
    else:
        response = mock_llm_call(prompt)
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        spec = json.loads(content.strip())
    except:
        spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2 fuel", "Zircaloy", "Water"],
            "particles": 10000,
            "batches": 50
        }
    
    print(f"   Created spec: {spec['geometry']}")
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "simulation_spec": spec,
        "next_action": "validate"
    }

def validator_agent(state: AgentState) -> AgentState:
    print("\n>> [VALIDATOR AGENT] Checking specification...")
    
    if USE_REAL_LLM:
        response = llm.invoke([
            SystemMessage(content="Validate simulation spec. Reply APPROVED or REJECTED."),
            HumanMessage(content=json.dumps(state["simulation_spec"]))
        ])
    else:
        response = mock_llm_call("validate spec")
    
    validation_passed = "APPROVED" in response.content.upper()
    print(f"   Validation: {'PASSED' if validation_passed else 'FAILED'}")
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "validation_passed": validation_passed,
        "next_action": "run" if validation_passed else "end"
    }

def runner_agent(state: AgentState) -> AgentState:
    print("\n>> [RUNNER AGENT] Executing simulation...")
    
    spec = SimulationSpec(**state["simulation_spec"])
    result = mock_openmc_run(spec)
    
    print(f"   Result: keff = {result.keff:.5f} +/- {result.keff_std:.5f}")
    
    return {
        **state,
        "messages": state["messages"] + [f"Simulation completed: keff = {result.keff:.5f}"],
        "simulation_result": result.model_dump(),
        "next_action": "analyze"
    }

def analyzer_agent(state: AgentState) -> AgentState:
    print("\n>> [ANALYZER AGENT] Analyzing results...")
    
    if USE_REAL_LLM:
        response = llm.invoke([
            SystemMessage(content="Analyze simulation results briefly."),
            HumanMessage(content=json.dumps(state["simulation_result"]))
        ])
    else:
        response = mock_llm_call("analyze results")
    
    print(f"   Analysis complete")
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "analysis": response.content,
        "next_action": "end"
    }

# ============================================================================
# ROUTING
# ============================================================================

def route_next_agent(state: AgentState) -> str:
    routing = {
        "plan": "planner",
        "validate": "validator",
        "run": "runner",
        "analyze": "analyzer",
        "end": END
    }
    return routing.get(state.get("next_action", "end"), END)

# ============================================================================
# GRAPH
# ============================================================================

def create_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("planner", planner_agent)
    workflow.add_node("validator", validator_agent)
    workflow.add_node("runner", runner_agent)
    workflow.add_node("analyzer", analyzer_agent)
    
    workflow.set_entry_point("planner")
    
    workflow.add_conditional_edges("planner", route_next_agent, {"validator": "validator", END: END})
    workflow.add_conditional_edges("validator", route_next_agent, {"runner": "runner", END: END})
    workflow.add_conditional_edges("runner", route_next_agent, {"analyzer": "analyzer"})
    workflow.add_conditional_edges("analyzer", route_next_agent, {END: END})
    
    return workflow.compile()

# ============================================================================
# MAIN
# ============================================================================

def run_simulation(user_request: str):
    print("=" * 70)
    print("MULTI-AGENT SIMULATION POC")
    print("=" * 70)
    print(f"\nMode: {'REAL LLM' if USE_REAL_LLM else 'MOCK LLM'}")
    print(f"[USER REQUEST] {user_request}\n")
    
    app = create_graph()
    
    initial_state = AgentState(
        messages=[],
        user_request=user_request,
        simulation_spec=None,
        validation_passed=False,
        simulation_result=None,
        analysis=None,
        next_action="plan"
    )
    
    final_state = app.invoke(initial_state)
    
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    
    if final_state.get("simulation_result"):
        print("\n[SIMULATION RESULTS]")
        print(json.dumps(final_state["simulation_result"], indent=2))
    
    if final_state.get("analysis"):
        print("\n[ANALYSIS]")
        print(final_state["analysis"])
    
    print("\n" + "=" * 70)
    
    return final_state

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SETUP INFO")
    print("="*70)
    print(f"Real LLM Available: {USE_REAL_LLM}")
    print(f"Real Embeddings Available: {USE_REAL_EMBEDDINGS}")
    
    if not USE_REAL_LLM:
        print("\nNote: Using mock LLM responses. To use real Fireworks API:")
        print("  1. Add FIREWORKS=your_key to .env file")
        print("  2. Rerun this script")
    
    print("="*70)
    
    # Run example
    result = run_simulation("Simulate a PWR fuel pin with 4.5% enriched UO2")


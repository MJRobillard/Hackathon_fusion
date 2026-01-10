"""
Multi-Agent Orchestration POC with LangGraph
Demonstrates agents coordinating on mock OpenMC simulation tasks
"""

import os
import json
from typing import TypedDict, Annotated, Sequence
from datetime import datetime
import operator

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_fireworks import ChatFireworks
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Initialize Fireworks LLM
llm = ChatFireworks(
    api_key=os.getenv("FIREWORKS"),
    model="accounts/robillard-matthew22/deployedModels/nvidia-nemotron-nano-9b-v2-nsoeqcp4",
    temperature=0.7
)

# ============================================================================
# MOCK OpenMC SIMULATION
# ============================================================================

class SimulationSpec(BaseModel):
    """Mock OpenMC simulation specification"""
    geometry: str = Field(description="Geometry description")
    materials: list[str] = Field(description="Material definitions")
    particles: int = Field(description="Number of particles")
    batches: int = Field(description="Number of batches")
    
class SimulationResult(BaseModel):
    """Mock OpenMC simulation result"""
    keff: float = Field(description="Effective multiplication factor")
    keff_std: float = Field(description="Standard deviation")
    runtime_seconds: float = Field(description="Simulation runtime")
    status: str = Field(description="Run status")

def mock_openmc_run(spec: SimulationSpec) -> SimulationResult:
    """Mock OpenMC execution - simulates running a reactor physics calculation"""
    import random
    import time
    
    # Simulate some computation time
    time.sleep(0.5)
    
    # Mock keff calculation (realistic for PWR pin cell: ~1.2-1.4)
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
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """Shared state passed between agents"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_request: str
    simulation_spec: dict | None
    validation_passed: bool
    simulation_result: dict | None
    analysis: str | None
    next_action: str

# ============================================================================
# AGENT DEFINITIONS
# ============================================================================

def planner_agent(state: AgentState) -> AgentState:
    """
    Agent 1: Planner
    Takes user request and creates a simulation specification
    """
    print("\n>> [PLANNER AGENT] Designing simulation...")
    
    system_prompt = """You are a nuclear reactor physics expert. 
    Given a user request, create a detailed OpenMC simulation specification.
    
    Output your response as JSON with this structure:
    {
        "geometry": "description of the geometry",
        "materials": ["list", "of", "materials"],
        "particles": integer,
        "batches": integer
    }
    
    Only respond with valid JSON, no other text."""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User request: {state['user_request']}")
    ]
    
    response = llm.invoke(messages)
    
    # Parse the LLM response to extract simulation spec
    try:
        # Try to extract JSON from response
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        spec = json.loads(content.strip())
    except:
        # Fallback if LLM doesn't follow format
        spec = {
            "geometry": "PWR pin cell with fuel pellet and cladding",
            "materials": ["UO2 fuel (4.5% enrichment)", "Zircaloy cladding", "Light water coolant"],
            "particles": 10000,
            "batches": 50
        }
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "simulation_spec": spec,
        "next_action": "validate"
    }

def validator_agent(state: AgentState) -> AgentState:
    """
    Agent 2: Validator
    Reviews simulation spec for correctness and safety
    """
    print("\n>> [VALIDATOR AGENT] Checking specification...")
    
    system_prompt = """You are a simulation validation expert.
    Review the provided simulation specification for basic correctness.
    
    This is a POC, so be lenient. Only reject if there are critical errors.
    
    Respond with either:
    - "APPROVED: [brief reason]" if the spec is reasonable
    - "REJECTED: [critical issues]" if there are major problems
    
    Keep your response under 30 words."""
    
    spec_text = json.dumps(state["simulation_spec"], indent=2)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Simulation spec:\n{spec_text}")
    ]
    
    response = llm.invoke(messages)
    validation_passed = "APPROVED" in response.content.upper()
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "validation_passed": validation_passed,
        "next_action": "run" if validation_passed else "end"
    }

def runner_agent(state: AgentState) -> AgentState:
    """
    Agent 3: Runner
    Executes the mock OpenMC simulation
    """
    print("\n>> [RUNNER AGENT] Executing simulation...")
    
    spec = SimulationSpec(**state["simulation_spec"])
    result = mock_openmc_run(spec)
    
    result_dict = result.model_dump()
    
    message = AIMessage(
        content=f"Simulation completed: keff = {result.keff:.5f} ± {result.keff_std:.5f}"
    )
    
    return {
        **state,
        "messages": state["messages"] + [message],
        "simulation_result": result_dict,
        "next_action": "analyze"
    }

def analyzer_agent(state: AgentState) -> AgentState:
    """
    Agent 4: Analyzer
    Interprets simulation results and provides insights
    """
    print("\n>> [ANALYZER AGENT] Analyzing results...")
    
    system_prompt = """You are a reactor physics analyst.
    Given simulation results, provide a brief technical interpretation.
    
    Focus on:
    - What the keff value indicates about the system
    - Whether the uncertainty is acceptable
    - Any recommendations
    
    Keep response under 100 words."""
    
    result_text = json.dumps(state["simulation_result"], indent=2)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Simulation results:\n{result_text}")
    ]
    
    response = llm.invoke(messages)
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "analysis": response.content,
        "next_action": "end"
    }

# ============================================================================
# ROUTING LOGIC
# ============================================================================

def route_next_agent(state: AgentState) -> str:
    """Determines which agent to call next"""
    next_action = state.get("next_action", "plan")
    
    routing = {
        "plan": "planner",
        "validate": "validator",
        "run": "runner",
        "analyze": "analyzer",
        "end": END
    }
    
    return routing.get(next_action, END)

# ============================================================================
# BUILD GRAPH
# ============================================================================

def create_multi_agent_graph():
    """Constructs the LangGraph workflow"""
    
    workflow = StateGraph(AgentState)
    
    # Add agent nodes
    workflow.add_node("planner", planner_agent)
    workflow.add_node("validator", validator_agent)
    workflow.add_node("runner", runner_agent)
    workflow.add_node("analyzer", analyzer_agent)
    
    # Set entry point
    workflow.set_entry_point("planner")
    
    # Add conditional edges based on routing logic
    workflow.add_conditional_edges(
        "planner",
        route_next_agent,
        {
            "validator": "validator",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "validator",
        route_next_agent,
        {
            "runner": "runner",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "runner",
        route_next_agent,
        {
            "analyzer": "analyzer",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "analyzer",
        route_next_agent,
        {
            END: END
        }
    )
    
    return workflow.compile()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_multi_agent_simulation(user_request: str):
    """Execute the multi-agent workflow"""
    
    print("=" * 80)
    print("MULTI-AGENT ORCHESTRATION POC")
    print("=" * 80)
    print(f"\n[USER REQUEST] {user_request}\n")
    
    # Create the graph
    app = create_multi_agent_graph()
    
    # Initial state
    initial_state = AgentState(
        messages=[],
        user_request=user_request,
        simulation_spec=None,
        validation_passed=False,
        simulation_result=None,
        analysis=None,
        next_action="plan"
    )
    
    # Run the workflow
    final_state = app.invoke(initial_state)
    
    # Display results
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    if final_state.get("simulation_spec"):
        print("\n[SIMULATION SPEC]")
        print(json.dumps(final_state["simulation_spec"], indent=2))
    
    if final_state.get("simulation_result"):
        print("\n[SIMULATION RESULTS]")
        print(json.dumps(final_state["simulation_result"], indent=2))
    
    if final_state.get("analysis"):
        print("\n[ANALYSIS]")
        print(final_state["analysis"])
    
    print("\n" + "=" * 80)
    
    return final_state


if __name__ == "__main__":
    # Example usage
    user_request = "I need to simulate a PWR fuel pin with 4.5% enriched UO2 at 600K temperature"
    
    result = run_multi_agent_simulation(user_request)


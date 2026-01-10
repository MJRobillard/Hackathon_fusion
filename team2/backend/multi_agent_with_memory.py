"""
Enhanced Multi-Agent POC with Voyage Embeddings
Demonstrates semantic memory and retrieval capabilities
"""

import os
import json
from typing import TypedDict, Annotated, Sequence
import operator

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_fireworks import ChatFireworks
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
import voyageai

# Load environment variables
load_dotenv()

# Initialize LLM and Embeddings
llm = ChatFireworks(
    api_key=os.getenv("FIREWORKS"),
    model="accounts/robillard-matthew22/deployedModels/nvidia-nemotron-nano-9b-v2-nsoeqcp4",
    temperature=0.7
)

voyage_client = voyageai.Client(api_key=os.getenv("VOYAGE"))

# ============================================================================
# MEMORY SYSTEM WITH EMBEDDINGS
# ============================================================================

class SimulationMemory:
    """Simple in-memory vector store for past simulations"""
    
    def __init__(self):
        self.memories = []  # List of (embedding, metadata) tuples
    
    def add(self, text: str, metadata: dict):
        """Store a simulation with its embedding"""
        embedding = voyage_client.embed(
            [text], 
            model="voyage-2",
            input_type="document"
        ).embeddings[0]
        
        self.memories.append({
            "text": text,
            "embedding": embedding,
            "metadata": metadata
        })
    
    def search(self, query: str, top_k: int = 3):
        """Semantic search over past simulations"""
        if not self.memories:
            return []
        
        query_embedding = voyage_client.embed(
            [query], 
            model="voyage-2",
            input_type="query"
        ).embeddings[0]
        
        # Calculate cosine similarity
        similarities = []
        for memory in self.memories:
            similarity = self._cosine_similarity(query_embedding, memory["embedding"])
            similarities.append((similarity, memory))
        
        # Sort by similarity and return top_k
        similarities.sort(reverse=True, key=lambda x: x[0])
        return [(score, mem["text"], mem["metadata"]) for score, mem in similarities[:top_k]]
    
    @staticmethod
    def _cosine_similarity(vec1, vec2):
        """Calculate cosine similarity between two vectors"""
        import math
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        return dot_product / (magnitude1 * magnitude2)

# Global memory instance
sim_memory = SimulationMemory()

# ============================================================================
# MOCK SIMULATION
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
    import random
    import time
    time.sleep(0.3)
    
    base_keff = 1.285
    keff = base_keff + random.uniform(-0.05, 0.05)
    keff_std = 0.00023 + random.uniform(0, 0.0001)
    
    return SimulationResult(
        keff=keff,
        keff_std=keff_std,
        runtime_seconds=0.3,
        status="completed"
    )

# ============================================================================
# STATE WITH MEMORY
# ============================================================================

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_request: str
    similar_past_runs: list | None
    simulation_spec: dict | None
    validation_passed: bool
    simulation_result: dict | None
    analysis: str | None
    next_action: str

# ============================================================================
# AGENTS WITH MEMORY AWARENESS
# ============================================================================

def memory_retrieval_agent(state: AgentState) -> AgentState:
    """
    Agent 0: Memory Retrieval
    Searches past simulations for relevant context
    """
    print("\n>> [MEMORY AGENT] Searching past simulations...")
    
    similar_runs = sim_memory.search(state["user_request"], top_k=3)
    
    if similar_runs:
        print(f"   Found {len(similar_runs)} similar past runs")
        for i, (score, text, metadata) in enumerate(similar_runs, 1):
            print(f"   {i}. Similarity: {score:.3f} - {text[:60]}...")
    else:
        print("   No past simulations found (memory empty)")
    
    return {
        **state,
        "similar_past_runs": similar_runs,
        "next_action": "plan"
    }

def planner_agent_with_memory(state: AgentState) -> AgentState:
    """
    Agent 1: Planner (memory-aware)
    Uses past simulations to inform new specs
    """
    print("\n>> [PLANNER AGENT] Designing simulation with memory context...")
    
    system_prompt = """You are a nuclear reactor physics expert.
    Create a simulation specification based on the user request.
    """
    
    context = ""
    if state.get("similar_past_runs"):
        context = "\n\nPast similar simulations:\n"
        for score, text, metadata in state["similar_past_runs"]:
            context += f"- {text}\n  Result: keff={metadata.get('keff', 'N/A')}\n"
    
    system_prompt += context
    system_prompt += """
    
    Output JSON only:
    {
        "geometry": "description",
        "materials": ["list"],
        "particles": int,
        "batches": int
    }"""
    
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
    except:
        spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2 fuel", "Zircaloy", "Water"],
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
    """Agent 2: Validator"""
    print("\n>> [VALIDATOR AGENT] Validating...")
    
    system_prompt = """Validate this simulation spec.
    Respond: "APPROVED: reason" or "REJECTED: reason" (under 40 words)"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(state["simulation_spec"]))
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
    """Agent 3: Runner"""
    print("\n>> [RUNNER AGENT] Executing...")
    
    spec = SimulationSpec(**state["simulation_spec"])
    result = mock_openmc_run(spec)
    
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=f"keff = {result.keff:.5f}")],
        "simulation_result": result.model_dump(),
        "next_action": "analyze"
    }

def analyzer_agent(state: AgentState) -> AgentState:
    """Agent 4: Analyzer"""
    print("\n>> [ANALYZER AGENT] Analyzing...")
    
    system_prompt = """Analyze these results briefly (under 80 words)."""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(state["simulation_result"]))
    ]
    
    response = llm.invoke(messages)
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "analysis": response.content,
        "next_action": "store_memory"
    }

def memory_storage_agent(state: AgentState) -> AgentState:
    """
    Agent 5: Memory Storage
    Saves this simulation to memory for future retrieval
    """
    print("\n>> [MEMORY STORAGE] Saving to memory...")
    
    # Create summary text for embedding
    spec = state["simulation_spec"]
    result = state["simulation_result"]
    
    summary = f"Simulation: {spec['geometry']} with {', '.join(spec['materials'])}. " \
              f"Particles: {spec['particles']}, Batches: {spec['batches']}"
    
    metadata = {
        "spec": spec,
        "keff": result["keff"],
        "keff_std": result["keff_std"],
        "user_request": state["user_request"]
    }
    
    sim_memory.add(summary, metadata)
    print(f"   Stored in memory (total memories: {len(sim_memory.memories)})")
    
    return {
        **state,
        "next_action": "end"
    }

# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def route_next_agent(state: AgentState) -> str:
    routing = {
        "retrieve": "memory_retrieval",
        "plan": "planner",
        "validate": "validator",
        "run": "runner",
        "analyze": "analyzer",
        "store_memory": "memory_storage",
        "end": END
    }
    return routing.get(state.get("next_action", "end"), END)

def create_graph_with_memory():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("memory_retrieval", memory_retrieval_agent)
    workflow.add_node("planner", planner_agent_with_memory)
    workflow.add_node("validator", validator_agent)
    workflow.add_node("runner", runner_agent)
    workflow.add_node("analyzer", analyzer_agent)
    workflow.add_node("memory_storage", memory_storage_agent)
    
    workflow.set_entry_point("memory_retrieval")
    
    workflow.add_conditional_edges("memory_retrieval", route_next_agent, {"planner": "planner"})
    workflow.add_conditional_edges("planner", route_next_agent, {"validator": "validator", END: END})
    workflow.add_conditional_edges("validator", route_next_agent, {"runner": "runner", END: END})
    workflow.add_conditional_edges("runner", route_next_agent, {"analyzer": "analyzer"})
    workflow.add_conditional_edges("analyzer", route_next_agent, {"memory_storage": "memory_storage"})
    workflow.add_conditional_edges("memory_storage", route_next_agent, {END: END})
    
    return workflow.compile()

# ============================================================================
# MAIN
# ============================================================================

def run_with_memory(user_request: str):
    print("=" * 80)
    print("MULTI-AGENT WITH MEMORY POC")
    print("=" * 80)
    print(f"\n[USER REQUEST] {user_request}\n")
    
    app = create_graph_with_memory()
    
    initial_state = AgentState(
        messages=[],
        user_request=user_request,
        similar_past_runs=None,
        simulation_spec=None,
        validation_passed=False,
        simulation_result=None,
        analysis=None,
        next_action="retrieve"
    )
    
    final_state = app.invoke(initial_state)
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    if final_state.get("simulation_result"):
        print("\n[SIMULATION RESULTS]")
        print(json.dumps(final_state["simulation_result"], indent=2))
    
    if final_state.get("analysis"):
        print("\n[ANALYSIS]")
        print(final_state["analysis"])
    
    print("\n" + "=" * 80)
    return final_state


if __name__ == "__main__":
    # Run multiple simulations to build memory
    requests = [
        "Simulate a PWR fuel pin with 4.5% enriched UO2",
        "I need a BWR assembly simulation at 560K",
        "Run a fast reactor with MOX fuel"
    ]
    
    for i, req in enumerate(requests, 1):
        print(f"\n\n{'='*80}")
        print(f"RUN {i}/{len(requests)}")
        print(f"{'='*80}")
        run_with_memory(req)
    
    # Now do a query that should retrieve relevant past simulations
    print(f"\n\n{'='*80}")
    print(f"FINAL RUN - Testing Memory Retrieval")
    print(f"{'='*80}")
    run_with_memory("I want to simulate another PWR pin cell")


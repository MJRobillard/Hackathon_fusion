"""
Agent Thinking Events - Backend Enhancement
============================================

This module shows how to emit detailed agent reasoning events
for the Mission Control frontend to display the agent thought process.

INTEGRATION STEPS:
------------------

1. Add this callback system to multi_agent_system.py
2. Inject event_bus into the orchestrator
3. Emit events at key decision points in agents

"""

from datetime import datetime, timezone
from typing import Callable, Optional, Dict, Any
import asyncio


class AgentThinkingCallback:
    """
    Callback system to capture and emit agent reasoning events
    """
    
    def __init__(self, event_bus, query_id: str):
        self.event_bus = event_bus
        self.query_id = query_id
        self.loop = asyncio.get_event_loop()
    
    def _emit_async(self, event_type: str, data: dict):
        """Helper to emit event from sync code"""
        asyncio.run_coroutine_threadsafe(
            self.event_bus.publish(self.query_id, {
                "type": event_type,
                **data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }),
            self.loop
        )
    
    def thinking(self, agent: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Agent is thinking/reasoning"""
        self._emit_async("agent_thinking", {
            "agent": agent,
            "content": content,
            "metadata": metadata or {}
        })
    
    def decision(self, agent: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Agent made a decision"""
        self._emit_async("agent_decision", {
            "agent": agent,
            "content": content,
            "metadata": metadata or {}
        })
    
    def planning(self, agent: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Agent is planning next steps"""
        self._emit_async("agent_planning", {
            "agent": agent,
            "content": content,
            "metadata": metadata or {}
        })
    
    def tool_call(self, agent: str, tool_name: str, args: Dict[str, Any]):
        """Agent is calling a tool"""
        self._emit_async("tool_call", {
            "agent": agent,
            "tool_name": tool_name,
            "message": f"Calling {tool_name}",
            "args": args
        })
    
    def observation(self, agent: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Agent observed something"""
        self._emit_async("agent_thinking", {
            "agent": agent,
            "type": "observation",
            "content": content,
            "metadata": metadata or {}
        })


# ============================================================================
# EXAMPLE: How to integrate into RouterAgent
# ============================================================================

def example_router_agent_with_thinking():
    """
    Example showing how to add thinking events to RouterAgent
    """
    
    # In multi_agent_system.py RouterAgent class:
    
    class RouterAgent:
        def __init__(self, use_llm=False, thinking_callback=None):
            self.use_llm = use_llm
            self.thinking_callback = thinking_callback
        
        def route(self, query: str) -> dict:
            # Emit thinking event
            if self.thinking_callback:
                self.thinking_callback.thinking(
                    "Router",
                    f"Analyzing query: '{query}'",
                    {"query_length": len(query)}
                )
            
            if self.use_llm:
                if self.thinking_callback:
                    self.thinking_callback.planning(
                        "Router",
                        "Using LLM for intelligent routing",
                        {"method": "llm"}
                    )
                
                # ... LLM routing logic ...
                intent = "run_simulation"
                agent = "studies"
                
                if self.thinking_callback:
                    self.thinking_callback.decision(
                        "Router",
                        f"Decided to route to {agent} agent",
                        {
                            "intent": intent,
                            "confidence": 0.95,
                            "reasoning": "Query contains simulation keywords"
                        }
                    )
            else:
                if self.thinking_callback:
                    self.thinking_callback.planning(
                        "Router",
                        "Using fast keyword matching",
                        {"method": "keyword"}
                    )
                
                # ... Keyword routing logic ...
                
            return {"agent": agent, "intent": intent}


# ============================================================================
# EXAMPLE: How to integrate into StudiesAgent
# ============================================================================

def example_studies_agent_with_thinking():
    """
    Example showing how to add thinking events to StudiesAgent
    """
    
    class StudiesAgent:
        def __init__(self, thinking_callback=None):
            self.thinking_callback = thinking_callback
        
        def execute(self, state: dict) -> dict:
            query = state.get("query", "")
            
            if self.thinking_callback:
                self.thinking_callback.thinking(
                    "Studies Agent",
                    "Extracting simulation parameters from query",
                    {"query": query}
                )
            
            # Extract parameters
            params = self._extract_params(query)
            
            if self.thinking_callback:
                self.thinking_callback.observation(
                    "Studies Agent",
                    f"Extracted parameters: enrichment={params.get('enrichment')}%, geometry={params.get('geometry')}",
                    {"params": params}
                )
            
            # Validate
            if self.thinking_callback:
                self.thinking_callback.planning(
                    "Studies Agent",
                    "Validating simulation parameters"
                )
            
            is_valid = self._validate(params)
            
            if is_valid:
                if self.thinking_callback:
                    self.thinking_callback.decision(
                        "Studies Agent",
                        "Parameters validated. Proceeding with simulation",
                        {"params": params}
                    )
                
                # Call OpenMC tool
                if self.thinking_callback:
                    self.thinking_callback.tool_call(
                        "Studies Agent",
                        "run_openmc_simulation",
                        params
                    )
                
                result = self._run_simulation(params)
                
                if self.thinking_callback:
                    self.thinking_callback.observation(
                        "Studies Agent",
                        f"Simulation complete. k-eff: {result['keff']} ± {result['keff_std']}",
                        {"result": result}
                    )
            else:
                if self.thinking_callback:
                    self.thinking_callback.decision(
                        "Studies Agent",
                        "Invalid parameters. Cannot proceed",
                        {"errors": params.get("errors")}
                    )
            
            return result


# ============================================================================
# INTEGRATION: Update execute_multi_agent_query in main_v2.py
# ============================================================================

"""
In main_v2.py, modify execute_multi_agent_query function:

async def execute_multi_agent_query(query_id: str, query: str, mongodb, use_llm: bool = True):
    try:
        # ... existing code ...
        
        # Create thinking callback
        from agent_thinking_events import AgentThinkingCallback
        thinking_callback = AgentThinkingCallback(event_bus, query_id)
        
        # Create orchestrator with callback
        orchestrator = MultiAgentOrchestrator(thinking_callback=thinking_callback)
        orchestrator.router = RouterAgent(use_llm=use_llm, thinking_callback=thinking_callback)
        
        # Run in thread pool since it's synchronous
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, orchestrator.process_query, query)
        
        # ... rest of existing code ...

"""


# ============================================================================
# NEW EVENTS THAT FRONTEND WILL LISTEN FOR:
# ============================================================================

"""
The frontend useEventStream hook now listens for these new events:

1. agent_thinking
   - When agent is reasoning/thinking
   - Example: "Analyzing query for simulation parameters"

2. agent_decision
   - When agent makes a decision
   - Example: "Decided to route to Studies Agent with 95% confidence"

3. agent_planning
   - When agent is planning next steps
   - Example: "Planning to run simulation with extracted parameters"

4. Enhanced tool_call events
   - Include more context about what tool is being called
   - Example: "Calling run_openmc_simulation with enrichment=4.5%"

Each event includes:
- agent: Which agent emitted it
- content: Human-readable description
- metadata: Additional context (optional)
- timestamp: When it occurred
"""


# ============================================================================
# QUICK START EXAMPLE
# ============================================================================

if __name__ == "__main__":
    print("""
    TO ENABLE AGENT THINKING DISPLAY:
    ===================================
    
    1. Copy this file to: Playground/backend/api/agent_thinking_events.py
    
    2. Modify multi_agent_system.py:
       - Add thinking_callback parameter to __init__
       - Pass callback to all agents
       - Add thinking/decision/planning calls at key points
    
    3. Modify api/main_v2.py execute_multi_agent_query:
       - Import AgentThinkingCallback
       - Create callback instance with event_bus and query_id
       - Pass to orchestrator
    
    4. Frontend will automatically display agent reasoning in the
       "Agent Reasoning" panel (already implemented!)
    
    Example agent reasoning you'll see:
    
    🤔 THINKING - Router
       "Analyzing query: 'Simulate PWR at 4.5% enrichment'"
    
    📋 PLANNING - Router
       "Using LLM for intelligent routing"
    
    ⚡ DECISION - Router
       "Decided to route to Studies Agent"
       Metadata: {"intent": "run_simulation", "confidence": 0.95}
    
    🤔 THINKING - Studies Agent
       "Extracting simulation parameters from query"
    
    👁️ OBSERVATION - Studies Agent
       "Extracted parameters: enrichment=4.5%, geometry=PWR"
    
    🔧 TOOL CALL - Studies Agent
       "Calling run_openmc_simulation"
    
    👁️ OBSERVATION - Studies Agent
       "Simulation complete. k-eff: 1.00245 ± 0.00012"
    """)


"""
AONP Multi-Agent System - Router + Specialist Agents
Implements the architecture from plan.md with tool delegation
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_fireworks import ChatFireworks
from pydantic import BaseModel, Field

# Import agent tools
from agent_tools import (
    submit_study,
    query_results,
    generate_sweep,
    compare_runs,
    get_study_statistics,
    get_run_by_id,
    get_recent_runs,
    validate_physics
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
# ROUTER AGENT
# ============================================================================

class RouterAgent:
    """
    Router Agent: Classifies intent and delegates to specialist agents
    
    Intents:
    - single_study: Run one simulation
    - sweep: Parameter sweep with multiple runs
    - query: Search historical data
    - analysis: Analyze/compare specific runs
    """
    
    def __init__(self):
        self.llm = llm
    
    def route_query(self, query: str) -> Dict[str, Any]:
        """
        Classify user intent and extract context
        
        Returns:
            {
                "agent": "studies" | "sweep" | "query" | "analysis",
                "intent": str,
                "context": dict,
                "confidence": float
            }
        """
        print(f"\n[ROUTER] Analyzing query: {query[:60]}...")
        
        system_prompt = """You are a routing agent for nuclear simulation requests.

Classify the user's request into ONE of these categories:
1. "single_study" - User wants to run ONE specific simulation
2. "sweep" - User wants to VARY a parameter and run MULTIPLE simulations
3. "query" - User wants to SEARCH or LIST past results
4. "analysis" - User wants to ANALYZE or COMPARE specific runs

Respond with ONLY the category name, nothing else."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User request: {query}")
        ]
        
        response = self.llm.invoke(messages)
        intent = response.content.strip().lower().replace('"', '').replace("'", "")
        
        # Map intent to agent
        intent_to_agent = {
            "single_study": "studies",
            "sweep": "sweep",
            "query": "query",
            "analysis": "analysis"
        }
        
        agent = intent_to_agent.get(intent, "studies")  # Default to studies
        
        print(f"[ROUTER] Intent: {intent} → Agent: {agent}")
        
        return {
            "agent": agent,
            "intent": intent,
            "context": {"query": query},
            "confidence": 0.9  # Placeholder
        }


# ============================================================================
# STUDIES AGENT
# ============================================================================

class StudiesAgent:
    """
    Studies Agent: Handles single simulation requests
    
    Tools:
    - submit_study
    - get_run_by_id
    - validate_physics
    """
    
    def __init__(self):
        self.llm = llm
        self.tools = {
            "submit_study": submit_study,
            "get_run_by_id": get_run_by_id,
            "validate_physics": validate_physics
        }
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute single study workflow
        
        Steps:
        1. Parse query into study spec
        2. Validate physics
        3. Submit study
        4. Return results
        """
        print(f"\n[STUDIES AGENT] Executing single study...")
        
        query = context.get("query", "")
        
        # Step 1: Extract study specification
        spec = self._extract_spec(query)
        
        # Step 2: Validate physics
        validation = validate_physics(spec)
        if not validation["valid"]:
            return {
                "status": "error",
                "error": f"Invalid physics: {validation['errors']}",
                "warnings": validation["warnings"]
            }
        
        # Step 3: Submit study
        try:
            result = submit_study(spec)
            
            return {
                "status": "success",
                "run_id": result["run_id"],
                "keff": result["keff"],
                "keff_std": result["keff_std"],
                "spec": spec,
                "warnings": validation["warnings"]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _extract_spec(self, query: str) -> Dict[str, Any]:
        """Extract study specification from natural language"""
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
            HumanMessage(content=f"User request: {query}")
        ]
        
        response = self.llm.invoke(messages)
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            spec = json.loads(content.strip())
            return spec
        except Exception as e:
            print(f"[STUDIES AGENT] Failed to parse spec: {e}")
            # Fallback spec
            return {
                "geometry": "PWR pin cell",
                "materials": ["UO2", "Zircaloy", "Water"],
                "enrichment_pct": 4.5,
                "temperature_K": 600,
                "particles": 10000,
                "batches": 50
            }


# ============================================================================
# SWEEP AGENT
# ============================================================================

class SweepAgent:
    """
    Sweep Agent: Handles parameter sweep requests
    
    Tools:
    - generate_sweep
    - compare_runs
    - validate_physics
    """
    
    def __init__(self):
        self.llm = llm
        self.tools = {
            "generate_sweep": generate_sweep,
            "compare_runs": compare_runs,
            "validate_physics": validate_physics
        }
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute parameter sweep workflow
        
        Steps:
        1. Parse query into sweep config
        2. Validate base spec
        3. Generate sweep
        4. Compare results
        5. Return analysis
        """
        print(f"\n[SWEEP AGENT] Executing parameter sweep...")
        
        query = context.get("query", "")
        
        # Step 1: Extract sweep configuration
        sweep_config = self._extract_sweep_config(query)
        
        # Step 2: Validate base spec
        validation = validate_physics(sweep_config["base_spec"])
        if not validation["valid"]:
            return {
                "status": "error",
                "error": f"Invalid base spec: {validation['errors']}"
            }
        
        # Step 3: Generate sweep
        try:
            run_ids = generate_sweep(
                base_spec=sweep_config["base_spec"],
                param_name=sweep_config["param_name"],
                param_values=sweep_config["param_values"]
            )
            
            # Step 4: Compare results
            comparison = compare_runs(run_ids)
            
            return {
                "status": "success",
                "run_ids": run_ids,
                "comparison": comparison,
                "sweep_config": sweep_config,
                "warnings": validation["warnings"]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _extract_sweep_config(self, query: str) -> Dict[str, Any]:
        """Extract sweep configuration from natural language"""
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
            HumanMessage(content=f"User request: {query}")
        ]
        
        response = self.llm.invoke(messages)
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            config = json.loads(content.strip())
            return config
        except Exception as e:
            print(f"[SWEEP AGENT] Failed to parse config: {e}")
            # Fallback config
            return {
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


# ============================================================================
# QUERY AGENT
# ============================================================================

class QueryAgent:
    """
    Query Agent: Handles database search requests
    
    Tools:
    - query_results
    - get_study_statistics
    - get_recent_runs
    """
    
    def __init__(self):
        self.llm = llm
        self.tools = {
            "query_results": query_results,
            "get_study_statistics": get_study_statistics,
            "get_recent_runs": get_recent_runs
        }
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute query workflow
        
        Steps:
        1. Parse query into filters
        2. Query database
        3. Format results
        """
        print(f"\n[QUERY AGENT] Searching database...")
        
        query = context.get("query", "")
        
        # Step 1: Extract filters from query
        filters = self._extract_filters(query)
        
        # Step 2: Query database
        try:
            if filters.get("recent_only"):
                results = get_recent_runs(limit=filters.get("limit", 10))
            elif filters.get("statistics_only"):
                results = get_study_statistics()
            else:
                results = query_results(
                    filter_params=filters.get("mongo_filter", {}),
                    limit=filters.get("limit", 10)
                )
            
            return {
                "status": "success",
                "results": results,
                "count": len(results) if isinstance(results, list) else 1,
                "filters": filters
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """Extract search filters from natural language"""
        query_lower = query.lower()
        
        filters = {
            "mongo_filter": {},
            "limit": 10,
            "recent_only": False,
            "statistics_only": False
        }
        
        # Check for statistics request
        if any(word in query_lower for word in ["statistics", "stats", "summary", "overview"]):
            filters["statistics_only"] = True
            return filters
        
        # Check for recent request
        if any(word in query_lower for word in ["recent", "latest", "last"]):
            filters["recent_only"] = True
            # Extract limit if specified
            import re
            match = re.search(r'(\d+)', query_lower)
            if match:
                filters["limit"] = int(match.group(1))
            return filters
        
        # Build MongoDB filter
        if "pwr" in query_lower:
            filters["mongo_filter"]["spec.geometry"] = {"$regex": "PWR", "$options": "i"}
        if "bwr" in query_lower:
            filters["mongo_filter"]["spec.geometry"] = {"$regex": "BWR", "$options": "i"}
        if "critical" in query_lower:
            filters["mongo_filter"]["keff"] = {"$gte": 1.0}
        if "subcritical" in query_lower:
            filters["mongo_filter"]["keff"] = {"$lt": 1.0}
        
        return filters


# ============================================================================
# ANALYSIS AGENT
# ============================================================================

class AnalysisAgent:
    """
    Analysis Agent: Handles result analysis and comparison
    
    Tools:
    - compare_runs
    - get_run_by_id
    """
    
    def __init__(self):
        self.llm = llm
        self.tools = {
            "compare_runs": compare_runs,
            "get_run_by_id": get_run_by_id
        }
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute analysis workflow
        
        Steps:
        1. Extract run IDs from query
        2. Fetch run data
        3. Compare/analyze
        4. Generate interpretation
        """
        print(f"\n[ANALYSIS AGENT] Analyzing results...")
        
        query = context.get("query", "")
        
        # Step 1: Extract run IDs
        run_ids = self._extract_run_ids(query)
        
        if not run_ids:
            return {
                "status": "error",
                "error": "No run IDs found in query"
            }
        
        # Step 2: Compare runs
        try:
            comparison = compare_runs(run_ids)
            
            # Step 3: Generate interpretation
            interpretation = self._generate_interpretation(comparison)
            
            return {
                "status": "success",
                "comparison": comparison,
                "interpretation": interpretation,
                "run_ids": run_ids
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _extract_run_ids(self, query: str) -> List[str]:
        """Extract run IDs from query"""
        import re
        # Match run_XXXXXXXX pattern
        run_ids = re.findall(r'run_[a-f0-9]{8}', query)
        return run_ids
    
    def _generate_interpretation(self, comparison: Dict[str, Any]) -> str:
        """Generate physics interpretation of comparison"""
        system_prompt = """You are a nuclear reactor physicist analyzing simulation results.

Provide a brief analysis (under 100 words) covering:
1. Key findings (criticality, trends, anomalies)
2. Physical interpretation
3. Confidence in results

Be technical but concise."""
        
        results_text = json.dumps(comparison, indent=2)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Results to analyze:\n{results_text}")
        ]
        
        response = self.llm.invoke(messages)
        return response.content


# ============================================================================
# MULTI-AGENT ORCHESTRATOR
# ============================================================================

class MultiAgentOrchestrator:
    """
    Main orchestrator that coordinates all agents
    """
    
    def __init__(self):
        self.router = RouterAgent()
        self.agents = {
            "studies": StudiesAgent(),
            "sweep": SweepAgent(),
            "query": QueryAgent(),
            "analysis": AnalysisAgent()
        }
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process user query through multi-agent system
        
        Returns:
            {
                "query": str,
                "routing": dict,
                "results": dict,
                "timestamp": str
            }
        """
        print("=" * 80)
        print("MULTI-AGENT ORCHESTRATOR")
        print("=" * 80)
        
        # Step 1: Route query
        routing = self.router.route_query(query)
        
        # Step 2: Execute specialist agent
        agent_name = routing["agent"]
        agent = self.agents[agent_name]
        
        results = agent.execute(routing["context"])
        
        # Step 3: Return complete response
        return {
            "query": query,
            "routing": routing,
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def run_multi_agent_query(query: str) -> Dict[str, Any]:
    """
    Convenience function to run a query through the multi-agent system
    """
    orchestrator = MultiAgentOrchestrator()
    return orchestrator.process_query(query)


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("AONP MULTI-AGENT SYSTEM DEMO")
    print("=" * 80)
    
    # Test 1: Single study
    print("\n[TEST 1] Single study request")
    result1 = run_multi_agent_query("Simulate a PWR pin cell with 4.5% enriched UO2 at 600K")
    print(f"Result: {result1['results']['status']}")
    
    # Test 2: Parameter sweep
    print("\n[TEST 2] Parameter sweep request")
    result2 = run_multi_agent_query("Compare PWR enrichments from 3% to 5%")
    print(f"Result: {result2['results']['status']}")
    
    # Test 3: Query
    print("\n[TEST 3] Query request")
    result3 = run_multi_agent_query("Show me the 5 most recent simulations")
    print(f"Result: {result3['results']['status']}")
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


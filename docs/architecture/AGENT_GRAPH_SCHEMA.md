# Agent Graph Architecture Schema

## Overview

This document describes the architecture for a testable, customizable multi-agent system using LangGraph with prompt customization and validation layers.

## LangGraph Capabilities

**Yes, LangGraph provides exactly what we need:**
- ✅ **StateGraph**: Explicit agent workflow graphs
- ✅ **Conditional Edges**: Dynamic routing based on state
- ✅ **State Management**: TypedDict state that flows through nodes
- ✅ **Observability**: Built-in tracing with LangSmith
- ✅ **Customizable Nodes**: Each node can have custom prompts/logic

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query Layer                          │
│  "Run parameter sweep for enrichment 3% to 5%"              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Prompt Configuration Layer                      │
│  - System prompts per agent                                  │
│  - Few-shot examples                                         │
│  - Output constraints (JSON schemas)                        │
│  - Temperature/token limits                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              LangGraph Workflow Layer                        │
│                                                              │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐          │
│  │  Router  │─────▶│  Agent   │─────▶│ Validate │          │
│  │  Node    │      │  Node    │      │  Node    │          │
│  └──────────┘      └──────────┘      └──────────┘          │
│       │                 │                  │                │
│       └─────────────────┴──────────────────┘                │
│                       │                                      │
│                       ▼                                      │
│              ┌──────────────┐                                │
│              │ Tool Execute │                                │
│              └──────────────┘                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Validation Layer                                │
│  - Schema validation (Pydantic)                             │
│  - Parameter range checks                                    │
│  - Dependency validation                                     │
│  - Physical constraint checks                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Tool Execution Layer                            │
│  - OpenMC adapter                                            │
│  - MongoDB queries                                           │
│  - Result aggregation                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Test & Validation Layer                         │
│  - Test specifications (YAML/JSON)                          │
│  - Expected vs actual comparison                             │
│  - Behavior validation                                       │
└─────────────────────────────────────────────────────────────┘
```

## LangGraph State Schema

```python
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

class AgentGraphState(TypedDict, total=False):
    # Input
    query: str
    user_context: Dict[str, Any]
    
    # Routing
    intent: str
    assigned_agent: str
    routing_confidence: float
    
    # Agent Reasoning (captured checkpoints)
    reasoning_checkpoints: List[Dict[str, Any]]  # thinking, planning, observation, decision
    
    # Tool Calls (before execution)
    planned_tool_calls: List[Dict[str, Any]]  # tool_name, params, validation_status
    validated_tool_calls: List[Dict[str, Any]]  # after validation
    
    # Execution
    tool_results: List[Dict[str, Any]]  # tool_name, result, success, error
    
    # Output
    final_results: Dict[str, Any]
    agent_path: List[str]  # ["router", "studies", "validator", "executor"]
    
    # Metadata
    errors: List[str]
    warnings: List[str]
    execution_time: float
```

## Graph Structure

```python
def build_enhanced_agent_graph():
    """Enhanced graph with validation and testability"""
    
    graph = StateGraph(AgentGraphState)
    
    # Nodes
    graph.add_node("router", router_node)
    graph.add_node("validator", validation_node)  # NEW: Pre-execution validation
    graph.add_node("studies", studies_agent_node)
    graph.add_node("sweep", sweep_agent_node)
    graph.add_node("query", query_agent_node)
    graph.add_node("analysis", analysis_agent_node)
    graph.add_node("tool_executor", tool_executor_node)  # NEW: Centralized tool execution
    graph.add_node("result_aggregator", result_aggregator_node)  # NEW: Combine results
    
    # Entry point
    graph.set_entry_point("router")
    
    # Conditional routing
    graph.add_conditional_edges(
        "router",
        route_to_agent,
        {
            "studies": "validator",
            "sweep": "validator",
            "query": "query",
            "analysis": "analysis",
        }
    )
    
    # Validation before execution
    graph.add_conditional_edges(
        "validator",
        validate_and_route,
        {
            "valid": "tool_executor",  # Proceed to execution
            "invalid": "result_aggregator",  # Return validation errors
            "needs_clarification": END,  # Ask user for clarification
        }
    )
    
    # Tool execution
    graph.add_edge("tool_executor", "result_aggregator")
    graph.add_edge("result_aggregator", END)
    
    return graph.compile()
```

## Prompt Configuration Schema

```yaml
# prompts/config.yaml
agents:
  router:
    system_prompt: |
      You are a routing agent for nuclear simulation requests.
      Classify the user's request into ONE category.
      Respond with ONLY the category name, nothing else.
    
    output_constraint:
      type: "enum"
      values: ["single_study", "sweep", "query", "analysis"]
      strict: true
    
    temperature: 0.2
    max_tokens: 10
    few_shot_examples:
      - input: "Run parameter sweep for enrichment 3% to 5%"
        output: "sweep"
      - input: "Show me recent runs"
        output: "query"
  
  studies_agent:
    system_prompt: |
      You are a nuclear reactor physics expert.
      Extract simulation parameters from the user's request.
      Output ONLY valid JSON.
    
    output_constraint:
      type: "json_schema"
      schema:
        type: object
        properties:
          geometry:
            type: string
          enrichment_pct:
            type: number
            minimum: 0
            maximum: 20
          temperature_K:
            type: number
            minimum: 300
            maximum: 1500
          particles:
            type: integer
            minimum: 1000
          batches:
            type: integer
            minimum: 10
        required: ["geometry"]
    
    temperature: 0.3
    max_tokens: 500
```

## Validation Node Schema

```python
async def validation_node(state: AgentGraphState) -> AgentGraphState:
    """Validate planned tool calls before execution"""
    
    planned_calls = state.get("planned_tool_calls", [])
    validated_calls = []
    errors = []
    warnings = []
    
    for call in planned_calls:
        tool_name = call["tool_name"]
        params = call["params"]
        
        # Schema validation
        schema = get_tool_schema(tool_name)
        try:
            validated_params = schema(**params)
            validated_calls.append({
                "tool_name": tool_name,
                "params": validated_params.dict(),
                "validation_status": "valid"
            })
        except ValidationError as e:
            errors.append(f"{tool_name}: {e}")
            continue
        
        # Range checks
        if tool_name == "submit_study":
            if params.get("enrichment_pct", 0) < 0 or params.get("enrichment_pct", 0) > 20:
                warnings.append(f"Enrichment {params['enrichment_pct']}% outside typical range (0-20%)")
        
        # Dependency checks
        if tool_name == "compare_runs":
            run_ids = params.get("run_ids", [])
            for run_id in run_ids:
                if not await run_exists(run_id):
                    errors.append(f"Run {run_id} does not exist")
    
    return {
        "validated_tool_calls": validated_calls,
        "errors": errors,
        "warnings": warnings,
        "validation_status": "valid" if not errors else "invalid"
    }
```

## Test Specification Schema

```yaml
# tests/specs/enrichment_sweep.yaml
test_name: "enrichment_sweep_extraction"
description: "Test that enrichment sweep queries are correctly parsed"

query: "Run parameter sweep for enrichment 3% to 5%"

expected_behavior:
  routing:
    intent: "sweep"
    agent: "sweep"
    confidence_threshold: 0.8
  
  reasoning_checkpoints:
    - checkpoint: "planning"
      agent: "Router"
      must_contain: ["sweep", "enrichment"]
      must_not_contain: ["single_study"]
    
    - checkpoint: "tool_call"
      agent: "Sweep Agent"
      tool: "generate_sweep"
      params:
        param_name: "enrichment_pct"
        param_values:
          length: 5
          min: 3.0
          max: 5.0
          step: 0.5
  
  validation:
    - check: "param_values_length"
      expected: 5
      tolerance: 0
    
    - check: "param_values_range"
      min: 3.0
      max: 5.0
  
  execution:
    expected_tool_calls: ["generate_sweep", "compare_runs"]
    min_runs_generated: 3
    max_runs_generated: 10

acceptance_criteria:
  - routing_correct: true
  - all_tool_calls_valid: true
  - no_physical_violations: true
  - execution_succeeds: true
  - results_meet_expectations: true

failure_modes:
  - description: "Model returns verbose explanation instead of category"
    expected_error: "Output format violation"
    recovery: "Retry with stricter prompt"
  
  - description: "Invalid enrichment range"
    expected_error: "ValidationError: enrichment_pct out of range"
    recovery: "Clamp to valid range and warn user"
```

## Customizable Prompt System

```python
# prompts/prompt_manager.py
class PromptManager:
    """Manages customizable prompts per agent"""
    
    def __init__(self, config_path: str = "prompts/config.yaml"):
        self.config = self._load_config(config_path)
        self.prompt_cache = {}
    
    def get_prompt(self, agent_name: str, prompt_type: str = "system") -> str:
        """Get prompt for agent, with caching"""
        cache_key = f"{agent_name}:{prompt_type}"
        if cache_key not in self.prompt_cache:
            agent_config = self.config["agents"][agent_name]
            prompt = agent_config[f"{prompt_type}_prompt"]
            
            # Inject few-shot examples if available
            if "few_shot_examples" in agent_config:
                examples = self._format_examples(agent_config["few_shot_examples"])
                prompt = f"{prompt}\n\nExamples:\n{examples}"
            
            self.prompt_cache[cache_key] = prompt
        
        return self.prompt_cache[cache_key]
    
    def get_output_constraint(self, agent_name: str) -> Dict[str, Any]:
        """Get output constraint (JSON schema, enum, etc.)"""
        return self.config["agents"][agent_name].get("output_constraint", {})
    
    def reload(self):
        """Reload prompts (useful for testing prompt changes)"""
        self.config = self._load_config(self.config_path)
        self.prompt_cache.clear()
```

## Test Runner Schema

```python
# tests/test_runner.py
class AgentTestRunner:
    """Runs test specifications against agent graph"""
    
    def __init__(self, graph, prompt_manager):
        self.graph = graph
        self.prompt_manager = prompt_manager
    
    async def run_test(self, test_spec: Dict[str, Any]) -> TestResult:
        """Run a single test specification"""
        
        # Capture reasoning checkpoints
        checkpoints = []
        
        def capture_checkpoint(agent, event_type, message, metadata):
            checkpoints.append({
                "agent": agent,
                "event_type": event_type,
                "message": message,
                "metadata": metadata,
                "timestamp": datetime.now()
            })
        
        # Initialize state
        initial_state = {
            "query": test_spec["query"],
            "reasoning_checkpoints": [],
            "planned_tool_calls": [],
            "validated_tool_calls": [],
            "tool_results": [],
        }
        
        # Run graph
        result = await self.graph.ainvoke(
            initial_state,
            config={"callbacks": [capture_checkpoint]}
        )
        
        # Validate against spec
        validation = self._validate_result(result, test_spec)
        
        return TestResult(
            test_name=test_spec["test_name"],
            passed=validation.all_passed,
            details=validation,
            checkpoints=checkpoints,
            execution_time=result.get("execution_time", 0)
        )
    
    def _validate_result(self, result: Dict, spec: Dict) -> ValidationResult:
        """Validate result against test specification"""
        expected = spec["expected_behavior"]
        validation = ValidationResult()
        
        # Check routing
        if "routing" in expected:
            routing_spec = expected["routing"]
            if result["intent"] != routing_spec["intent"]:
                validation.add_failure("routing", f"Expected {routing_spec['intent']}, got {result['intent']}")
        
        # Check reasoning checkpoints
        if "reasoning_checkpoints" in expected:
            for checkpoint_spec in expected["reasoning_checkpoints"]:
                matching = [c for c in result["reasoning_checkpoints"] 
                           if self._checkpoint_matches(c, checkpoint_spec)]
                if not matching:
                    validation.add_failure("reasoning", f"Missing checkpoint: {checkpoint_spec}")
        
        # Check tool calls
        if "tool_calls" in expected:
            for tool_spec in expected["tool_calls"]:
                matching = [t for t in result["validated_tool_calls"]
                           if t["tool_name"] == tool_spec["tool"]]
                if not matching:
                    validation.add_failure("tool_call", f"Missing tool call: {tool_spec['tool']}")
        
        return validation
```

## Quick Wins Implementation

### 1. Prompt Versioning
```python
# Track prompt versions for A/B testing
prompt_version = "v1.2.3"
prompt_manager = PromptManager(f"prompts/{prompt_version}/config.yaml")
```

### 2. Structured Output Enforcement
```python
# Use JSON schema to force structured outputs
from langchain.output_parsers import PydanticOutputParser

schema = PydanticOutputParser(pydantic_object=StudySpec)
prompt = prompt_manager.get_prompt("studies_agent")
prompt = f"{prompt}\n\n{schema.get_format_instructions()}"
```

### 3. Validation Middleware
```python
# Wrap tool calls with validation
def validated_tool_call(tool_func, schema):
    def wrapper(*args, **kwargs):
        validated = schema(**kwargs)
        return tool_func(**validated.dict())
    return wrapper
```

## Benefits

1. **Testability**: Test specs define expected behavior, easy to validate
2. **Customizability**: Prompts in YAML, easy to modify without code changes
3. **Observability**: All reasoning checkpoints captured
4. **Validation**: Pre-execution validation prevents errors
5. **Versioning**: Track prompt versions, A/B test improvements
6. **Debugging**: Clear failure modes and recovery strategies

## Next Steps

1. Implement `PromptManager` class
2. Add validation node to graph
3. Create test specification format
4. Build test runner
5. Add prompt versioning system

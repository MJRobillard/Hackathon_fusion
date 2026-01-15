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

from orchestration_config import get_orchestration_config

# Import prompt config and validation
try:
    from prompt_config import get_prompt_config
    USE_PROMPT_CONFIG = True
except ImportError:
    USE_PROMPT_CONFIG = False

try:
    from tool_validation import validate_tool_call
    USE_VALIDATION = True
except ImportError:
    USE_VALIDATION = False

load_dotenv()

# ============================================================================
# LLM SETUP
# ============================================================================

def _should_use_local() -> bool:
    """Check if RUN_LOCAL is set to use local DeepSeek."""
    run_local = os.getenv("RUN_LOCAL", "").lower()
    return run_local in ("true", "1", "yes", "on")

def _get_local_model_name() -> str:
    """Get local DeepSeek model name from environment or default."""
    return os.getenv("LOCAL_DEEPSEEK_MODEL", "deepseek-r1:1.5b")

def _get_ollama_url() -> str:
    """Get Ollama API base URL from environment or default."""
    return os.getenv("LOCAL_DEEPSEEK_URL", "http://localhost:11434")

def _create_llm():
    """Create LLM instance based on RUN_LOCAL setting."""
    if _should_use_local():
        # Use local DeepSeek via Ollama's OpenAI-compatible API
        try:
            from langchain_openai import ChatOpenAI
            
            model_name = _get_local_model_name()
            ollama_url = _get_ollama_url()
            temperature = 0.7
            
            # Ollama provides OpenAI-compatible API at /v1 endpoint
            base_url = f"{ollama_url}/v1"
            
            # Try model_name first (older langchain-openai), then model (newer)
            try:
                llm = ChatOpenAI(
                    model_name=model_name,
                    base_url=base_url,
                    api_key="ollama",  # Ollama doesn't require a real key, but LangChain expects one
                    temperature=temperature,
                )
            except TypeError:
                # Newer versions of langchain-openai use 'model' instead of 'model_name'
                llm = ChatOpenAI(
                    model=model_name,
                    base_url=base_url,
                    api_key="ollama",
                    temperature=temperature,
                )
            # Set model name and temperature as attributes for easy access
            # (getattr() calls in RouterAgent and StudiesAgent need these)
            # Use object.__setattr__ to bypass Pydantic validation for these custom attributes
            object.__setattr__(llm, "model", model_name)
            object.__setattr__(llm, "temperature", temperature)
            return llm
        except ImportError:
            print("⚠️  Warning: langchain-openai not available, falling back to Fireworks")
            # Fall through to Fireworks
        except Exception as e:
            print(f"⚠️  Warning: Local DeepSeek setup failed ({e}), falling back to Fireworks")
            # Fall through to Fireworks
    
    # Use Fireworks API (default)
    model_name = "accounts/robillard-matthew22/deployedModels/nvidia-nemotron-nano-9b-v2-nsoeqcp4"
    temperature = 0.7
    llm = ChatFireworks(
        api_key=os.getenv("FIREWORKS"),
        model=model_name,
        temperature=temperature
    )
    # Set model name and temperature as attributes for easy access
    # (getattr() calls in RouterAgent and StudiesAgent need these)
    # ChatFireworks already has model and temperature as attributes, but we ensure they're accessible
    # Use object.__setattr__ to bypass Pydantic validation if needed, or just ensure they exist
    if not hasattr(llm, "model"):
        object.__setattr__(llm, "model", model_name)
    if not hasattr(llm, "temperature"):
        object.__setattr__(llm, "temperature", temperature)
    return llm

llm = _create_llm()

# ============================================================================
# HELPERS (lightweight, UI-friendly “agentic trace”)
# ============================================================================

def _truncate(s: str, n: int = 1200) -> str:
    if s is None:
        return ""
    s = str(s)
    return s if len(s) <= n else (s[: n - 3] + "...")


def _serialize_messages(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in messages:
        role = getattr(m, "type", m.__class__.__name__)
        content = _truncate(getattr(m, "content", ""))
        out.append({"role": role, "content": content})
    return out


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
    
    def __init__(self, use_llm: bool = True, thinking_callback=None):
        """
        Initialize Router Agent
        
        Args:
            use_llm: If False, use fast keyword-based routing (useful for testing)
        """
        self.llm = llm
        self.use_llm = use_llm
        self.thinking_callback = thinking_callback
    
    def _keyword_route(self, query: str) -> Dict[str, Any]:
        """
        Fast keyword-based routing (no LLM required)
        Good for testing and when LLM is unavailable
        """
        query_lower = query.lower()
        
        # Check for sweep keywords
        sweep_keywords = ['compare', 'sweep', 'vary', 'range', 'from', 'to', 'between', 'multiple']
        if any(kw in query_lower for kw in sweep_keywords):
            # But not if it's comparing specific run IDs
            if 'run_' not in query_lower:
                return {
                    "agent": "sweep",
                    "intent": "sweep",
                    "context": {"query": query},
                    "confidence": 0.8,
                    "method": "keyword"
                }
        
        # Check for query keywords
        query_keywords = ['show', 'list', 'find', 'search', 'get', 'fetch', 'recent', 'all', 'statistics', 'stats']
        if any(kw in query_lower for kw in query_keywords):
            return {
                "agent": "query",
                "intent": "query",
                "context": {"query": query},
                "confidence": 0.8,
                "method": "keyword"
            }
        
        # Check for analysis keywords (specific run comparisons)
        if 'run_' in query_lower and ('compare' in query_lower or 'analyze' in query_lower or 'analysis' in query_lower):
            return {
                "agent": "analysis",
                "intent": "analysis",
                "context": {"query": query},
                "confidence": 0.8,
                "method": "keyword"
            }
        
        # Check for RAG copilot keywords
        rag_keywords = [
            'literature', 'paper', 'research', 'publication', 'doi',
            'reproduce', 'reproducibility', 'validate', 'benchmark',
            'suggest', 'recommend', 'follow-up', 'next experiment',
            'similar runs', 'past experiments', 'history',
            'why', 'explain', 'how does', 'what about', 'tell me about'
        ]
        if any(kw in query_lower for kw in rag_keywords):
            return {
                "agent": "rag_copilot",
                "intent": "rag_query",
                "context": {"query": query},
                "confidence": 0.8,
                "method": "keyword"
            }
        
        # Default to single study
        return {
            "agent": "studies",
            "intent": "single_study",
            "context": {"query": query},
            "confidence": 0.7,
            "method": "keyword"
        }
    
    def route_query(self, query: str) -> Dict[str, Any]:
        """
        Classify user intent and extract context
        
        Returns:
            {
                "agent": "studies" | "sweep" | "query" | "analysis",
                "intent": str,
                "context": dict,
                "confidence": float,
                "raw_response": str (optional, for debugging)
            }
        """
        print(f"\n[ROUTER] Analyzing query: {query[:60]}...")
        if self.thinking_callback:
            try:
                self.thinking_callback.thinking(
                    "Router",
                    f"Analyzing query: '{query}'",
                    {
                        "query_length": len(query),
                        "goal": "Classify intent and route to the best specialist agent (studies/sweep/query/analysis)",
                    },
                )
            except Exception as e:
                print(f"[WARN] RouterAgent: thinking_callback.thinking() failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Use keyword routing if LLM is disabled
        if not self.use_llm:
            print(f"[ROUTER] Using keyword-based routing (LLM disabled)")
            if self.thinking_callback:
                self.thinking_callback.planning("Router", "Using keyword-based routing (LLM disabled)", {"method": "keyword"})
            return self._keyword_route(query)
        
        # Try LLM routing
        if USE_PROMPT_CONFIG:
            prompt_config = get_prompt_config()
            system_prompt = prompt_config.get_prompt("router", "system")
            if not system_prompt:
                # Fallback to default
                system_prompt = """You are a routing agent for nuclear simulation requests.

Classify the user's request into ONE of these categories:
1. "single_study" - User wants to run ONE specific simulation
2. "sweep" - User wants to VARY a parameter and run MULTIPLE simulations
3. "query" - User wants to SEARCH or LIST past results
4. "analysis" - User wants to ANALYZE or COMPARE specific runs

CRITICAL: Respond with ONLY the category name. No explanations, no reasoning, no markdown, no additional text."""
        else:
            system_prompt = """You are a routing agent for nuclear simulation requests.

Classify the user's request into ONE of these categories:
1. "single_study" - User wants to run ONE specific simulation
2. "sweep" - User wants to VARY a parameter and run MULTIPLE simulations
3. "query" - User wants to SEARCH or LIST past results
4. "analysis" - User wants to ANALYZE or COMPARE specific runs

CRITICAL: Respond with ONLY the category name. No explanations, no reasoning, no markdown, no additional text.
Examples:
- Input: "Run parameter sweep for enrichment 3% to 5%" → Output: "sweep"
- Input: "Show me recent runs" → Output: "query"
- Input: "Simulate a PWR pin cell" → Output: "single_study"
- Input: "Compare run_123 and run_456" → Output: "analysis"

Your response must be exactly one word: single_study, sweep, query, or analysis."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User request: {query}")
        ]
        
        try:
            # Call LLM
            if self.thinking_callback:
                try:
                    self.thinking_callback.planning(
                        "Router",
                        "Using LLM-based routing",
                        {
                            "method": "llm",
                            "llm_input": {
                                "purpose": "intent_classification",
                                "model": getattr(self.llm, "model", None),
                                "temperature": getattr(self.llm, "temperature", None),
                                "messages": _serialize_messages(messages),
                        },
                    },
                    )
                except Exception as e:
                    print(f"[WARN] RouterAgent: thinking_callback.planning() failed: {e}")
                    import traceback
                    traceback.print_exc()
            response = self.llm.invoke(messages)
            raw_response = response.content.strip()
            print(f"[ROUTER] Raw LLM response: '{raw_response}'")
            
            # Clean up response
            intent = raw_response.lower().replace('"', '').replace("'", "").replace(".", "").strip()
            print(f"[ROUTER] Cleaned intent: '{intent}'")
            if self.thinking_callback:
                self.thinking_callback.observation(
                    "Router",
                    "LLM routing output received; normalizing to known intents",
                    {"raw_response": raw_response, "normalized_intent": intent},
                )
            
            # Map intent to agent
            intent_to_agent = {
                "single_study": "studies",
                "sweep": "sweep",
                "query": "query",
                "analysis": "analysis"
            }
            
            # Check for exact match
            if intent in intent_to_agent:
                agent = intent_to_agent[intent]
                confidence = 0.9
            else:
                # Try fuzzy matching as fallback
                print(f"[ROUTER WARNING] Intent '{intent}' not recognized, trying fuzzy match...")
                
                # Check if any keywords match
                if "sweep" in intent or "vary" in intent or "compare" in intent:
                    intent = "sweep"
                    agent = "sweep"
                    confidence = 0.6
                elif "query" in intent or "search" in intent or "list" in intent or "show" in intent:
                    intent = "query"
                    agent = "query"
                    confidence = 0.6
                elif "analysis" in intent or "analyze" in intent:
                    intent = "analysis"
                    agent = "analysis"
                    confidence = 0.6
                else:
                    # Default to single_study
                    print(f"[ROUTER WARNING] No match found, defaulting to 'single_study'")
                    intent = "single_study"
                    agent = "studies"
                    confidence = 0.5

            if self.thinking_callback:
                self.thinking_callback.thinking(
                    "Router",
                    "Sanity-checking the selected intent against visible query signals (to avoid misroutes)",
                    {"selected_intent": intent, "selected_agent": agent},
                )
            
            print(f"[ROUTER] Final: Intent='{intent}' → Agent='{agent}' (confidence={confidence})")
            if self.thinking_callback:
                # UI-friendly, high-level rationale (not chain-of-thought)
                signals: List[str] = []
                ql = query.lower()
                if any(k in ql for k in ["compare", "sweep", "vary", "range", "from", "to", "between", "multiple"]):
                    signals.append("contains sweep/comparison language")
                if any(k in ql for k in ["show", "list", "find", "search", "recent", "statistics", "stats"]):
                    signals.append("contains query/history language")
                if "run_" in ql and any(k in ql for k in ["compare", "analyze", "analysis"]):
                    signals.append("mentions explicit run ids for analysis")
                if any(k in ql for k in ["simulate", "pin cell", "assembly", "enrichment", "temperature", "particles", "batches"]):
                    signals.append("contains simulation configuration language")
                self.thinking_callback.decision(
                    "Router",
                    f"Routed to {agent} ({intent})",
                    {
                        "intent": intent,
                        "agent": agent,
                        "confidence": confidence,
                        "method": "llm",
                        "signals": signals,
                    },
                )
            
            return {
                "agent": agent,
                "intent": intent,
                "context": {"query": query},
                "confidence": confidence,
                "raw_response": raw_response,  # Include for debugging
                "method": "llm"
            }
            
        except Exception as e:
            # Handle LLM errors gracefully - fall back to keyword routing
            print(f"[ROUTER ERROR] LLM invocation failed: {e}")
            print(f"[ROUTER] Falling back to keyword-based routing")
            if self.thinking_callback:
                self.thinking_callback.decision("Router", "LLM routing failed; falling back to keyword routing", {"error": str(e)})
            
            result = self._keyword_route(query)
            result["error"] = str(e)
            result["fallback"] = True
            return result


# ============================================================================
# STUDIES AGENT
# ============================================================================

class RetryAgent:
    """
    Retry Agent: chooses a rerun coefficient + updated particles/batches when a run
    needs better statistics (e.g., convergence loop).
    """

    def __init__(self, thinking_callback=None):
        self.thinking_callback = thinking_callback

    def choose_rerun_params(
        self,
        *,
        objective: str,
        uncertainty_pcm: float,
        target_uncertainty_pcm: float,
        current_particles: int,
        current_batches: int,
        max_particles: int,
        max_batches: int,
        batches_step: int,
        particles_min_step: int,
    ) -> Dict[str, Any]:
        if self.thinking_callback:
            self.thinking_callback.thinking(
                "Retry Agent",
                "Self-check: what should my goals be for the rerun, and what coefficient should I use?",
                {
                    "question": "What are my goals for the rerun?",
                    "objective": objective,
                    "primary_goal": "Reduce statistical uncertainty in k-eff",
                    "secondary_goals": ["Keep runtime bounded", "Stay within max particles/batches"],
                },
            )

        # Heuristic: uncertainty ~ 1/sqrt(N) => need ~ (ratio^2) more histories
        ratio = float(uncertainty_pcm) / float(target_uncertainty_pcm) if target_uncertainty_pcm > 0 else 1.0
        # "coefficient" showcased in UI (human-friendly)
        coef = min(3.0, max(1.15, ratio))

        if self.thinking_callback:
            self.thinking_callback.planning(
                "Retry Agent",
                "Computing rerun coefficient from uncertainty ratio (aim: bring uncertainty under target)",
                {"uncertainty_pcm": uncertainty_pcm, "target_uncertainty_pcm": target_uncertainty_pcm, "ratio": ratio, "coefficient": coef},
            )

        # Scale particles more aggressively than batches (simple and explainable)
        proposed_particles = int(max(current_particles + particles_min_step, round(current_particles * (coef**2))))
        proposed_batches = int(max(current_batches + batches_step, round(current_batches * coef)))

        next_particles = min(max_particles, proposed_particles)
        next_batches = min(max_batches, proposed_batches)

        if self.thinking_callback:
            self.thinking_callback.decision(
                "Retry Agent",
                f"Rerun coefficient={coef:.2f} → particles={next_particles}, batches={next_batches}",
                {
                    "coefficient": coef,
                    "current_particles": current_particles,
                    "current_batches": current_batches,
                    "proposed_particles": proposed_particles,
                    "proposed_batches": proposed_batches,
                    "next_particles": next_particles,
                    "next_batches": next_batches,
                },
            )

        return {"coefficient": coef, "particles": next_particles, "batches": next_batches}


class StudiesAgent:
    """
    Studies Agent: Handles single simulation requests
    
    Tools:
    - submit_study
    - get_run_by_id
    - validate_physics
    """
    
    def __init__(self, thinking_callback=None):
        self.llm = llm
        self.thinking_callback = thinking_callback
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
        query_lower = query.lower()
        wants_convergence = any(k in query_lower for k in ["converge", "convergence", "until it converges"])
        objective = (
            "Estimate k-eff with sufficiently low uncertainty (and stable delta between iterations)"
            if not any(k in query_lower for k in ["critical", "keff=1", "k-eff=1", "k=1"])
            else "Reach/assess criticality (k-eff ≈ 1) with sufficiently low uncertainty"
        )
        cfg = get_orchestration_config()
        # Default convergence targets (runtime configurable)
        target_uncertainty_pcm = cfg.convergence.target_uncertainty_pcm
        stable_delta_pcm = cfg.convergence.stable_delta_pcm
        max_iterations = cfg.convergence.max_iterations
        max_particles = cfg.convergence.max_particles
        max_batches = cfg.convergence.max_batches
        batches_step = cfg.convergence.batches_step
        particles_min_step = cfg.convergence.particles_min_step
        
        if self.thinking_callback:
            self.thinking_callback.planning(
                "Studies Agent",
                "Extracting simulation spec from query",
                {"wants_convergence": wants_convergence, "objective": objective},
            )
        
        # Step 1: Extract study specification
        spec = self._extract_spec(query)
        if self.thinking_callback:
            self.thinking_callback.observation("Studies Agent", "Extracted simulation parameters", {"spec": spec})
        
        # Step 1.5: Validate tool call before execution (if validation available)
        if USE_VALIDATION:
            valid, validated_spec, errors = validate_tool_call("submit_study", spec)
            if not valid:
                if self.thinking_callback:
                    self.thinking_callback.observation("Studies Agent", "Validation failed", {"errors": errors})
                return {
                    "status": "error",
                    "error": f"Invalid parameters: {', '.join(errors)}",
                    "validation_errors": errors
                }
            spec = validated_spec or spec
        
        # Step 2: Validate physics
        if self.thinking_callback:
            self.thinking_callback.tool_call("Studies Agent", "validate_physics", spec)
        validation = validate_physics(spec)
        if self.thinking_callback and hasattr(self.thinking_callback, "tool_result"):
            self.thinking_callback.tool_result("Studies Agent", "validate_physics", validation)
        if not validation["valid"]:
            return {
                "status": "error",
                "error": f"Invalid physics: {validation['errors']}",
                "warnings": validation["warnings"]
            }
        if self.thinking_callback and validation.get("warnings"):
            self.thinking_callback.observation("Studies Agent", "Physics validation warnings", {"warnings": validation["warnings"]})
        
        # Step 3: Submit study (optionally iterate until converged)
        try:
            if not wants_convergence:
                if self.thinking_callback:
                    self.thinking_callback.tool_call("Studies Agent", "submit_study", spec)
                result = submit_study(spec)
                if self.thinking_callback and hasattr(self.thinking_callback, "tool_result"):
                    self.thinking_callback.tool_result("Studies Agent", "submit_study", result)
                if self.thinking_callback:
                    self.thinking_callback.observation(
                        "Studies Agent",
                        f"Run complete: k-eff {result['keff']:.5f} ± {result['keff_std']:.6f}",
                        {"run_id": result["run_id"], **result},
                    )
                
                return {
                    "status": "success",
                    "run_id": result["run_id"],
                    "keff": result["keff"],
                    "keff_std": result["keff_std"],
                    "spec": spec,
                    "warnings": validation["warnings"]
                }
            
            # Convergence loop
            runs: List[Dict[str, Any]] = []
            current_spec = dict(spec)
            
            if self.thinking_callback:
                self.thinking_callback.planning(
                    "Studies Agent",
                    "Convergence requested; will iterate runs until uncertainty stabilizes / drops below target",
                    {"target_uncertainty_pcm": target_uncertainty_pcm, "max_iterations": max_iterations, "objective": objective},
                )
            
            for i in range(max_iterations):
                iter_label = f"iter_{i+1}"
                if self.thinking_callback:
                    self.thinking_callback.tool_call(
                        "Studies Agent",
                        "submit_study",
                        {
                            **current_spec,
                            "iteration": i + 1,
                            "orchestration": {
                                "reason": "convergence_loop",
                                "targets": {
                                    "target_uncertainty_pcm": target_uncertainty_pcm,
                                    "stable_delta_pcm": stable_delta_pcm,
                                },
                            },
                        },
                    )
                
                result = submit_study(current_spec)
                if self.thinking_callback and hasattr(self.thinking_callback, "tool_result"):
                    self.thinking_callback.tool_result("Studies Agent", "submit_study", result)
                uncertainty_pcm = float(result["keff_std"]) * 1e5
                
                run_rec = {
                    "iteration": i + 1,
                    "run_id": result["run_id"],
                    "keff": result["keff"],
                    "keff_std": result["keff_std"],
                    "uncertainty_pcm": uncertainty_pcm,
                    "spec": dict(current_spec),
                }
                runs.append(run_rec)
                
                if self.thinking_callback:
                    self.thinking_callback.observation(
                        "Studies Agent",
                        f"[{i+1}/{max_iterations}] k-eff {result['keff']:.5f} ± {result['keff_std']:.6f} ({uncertainty_pcm:.0f} pcm)",
                        run_rec,
                    )
                
                # Check convergence
                delta_pcm = None
                if len(runs) >= 2:
                    delta_pcm = (runs[-1]["keff"] - runs[-2]["keff"]) * 1e5
                
                converged = (uncertainty_pcm <= target_uncertainty_pcm) and (
                    delta_pcm is None or abs(delta_pcm) <= stable_delta_pcm
                )
                
                if converged:
                    if self.thinking_callback:
                        self.thinking_callback.decision(
                            "Studies Agent",
                            "Converged: uncertainty and k-eff change are within targets",
                            {"uncertainty_pcm": uncertainty_pcm, "delta_pcm": delta_pcm},
                        )
                    break
                
                # Adjust parameters for next iteration
                particles = int(current_spec.get("particles", 10000) or 10000)
                batches = int(current_spec.get("batches", 50) or 50)

                retry_agent = RetryAgent(thinking_callback=self.thinking_callback)
                retry = retry_agent.choose_rerun_params(
                    objective=objective,
                    uncertainty_pcm=uncertainty_pcm,
                    target_uncertainty_pcm=target_uncertainty_pcm,
                    current_particles=particles,
                    current_batches=batches,
                    max_particles=max_particles,
                    max_batches=max_batches,
                    batches_step=batches_step,
                    particles_min_step=particles_min_step,
                )

                current_spec["particles"] = int(retry["particles"])
                current_spec["batches"] = int(retry["batches"])

                if self.thinking_callback:
                    self.thinking_callback.planning(
                        "Studies Agent",
                        "Not converged yet; applying Retry Agent proposal for next iteration",
                        {
                            "retry_coefficient": retry.get("coefficient"),
                            "next_particles": current_spec["particles"],
                            "next_batches": current_spec["batches"],
                            "uncertainty_pcm": uncertainty_pcm,
                            "delta_pcm": delta_pcm,
                        },
                    )
            
            # Compare the attempted runs (best-effort)
            run_ids = [r["run_id"] for r in runs]
            comparison = None
            try:
                if self.thinking_callback:
                    self.thinking_callback.tool_call("Compare Agent", "compare_runs", {"run_ids": run_ids})
                comparison = compare_runs(run_ids)
                if self.thinking_callback and hasattr(self.thinking_callback, "tool_result"):
                    self.thinking_callback.tool_result("Compare Agent", "compare_runs", comparison)
            except Exception as e:
                comparison = {"error": str(e)}
            
            best = max(runs, key=lambda r: (r["keff"], -r["keff_std"])) if runs else None
            return {
                "status": "success",
                "mode": "convergence",
                "runs": runs,
                "run_ids": run_ids,
                "best_run": best,
                "comparison": comparison,
                "warnings": validation["warnings"],
            }
        except Exception as e:
            if self.thinking_callback:
                self.thinking_callback.decision("Studies Agent", "Run failed", {"error": str(e)})
            return {"status": "error", "error": str(e)}
    
    def _extract_spec(self, query: str) -> Dict[str, Any]:
        """Extract study specification from natural language"""
        
        # Always do keyword extraction to catch explicit config keywords
        try:
            kw_spec = self._keyword_extract_spec(query)
        except Exception as e:
            print(f"[STUDIES AGENT] Keyword extraction failed: {e}")
            kw_spec = None
        
        # Try LLM-based extraction
        if USE_PROMPT_CONFIG:
            prompt_config = get_prompt_config()
            system_prompt = prompt_config.get_prompt("studies_agent", "system")
            if not system_prompt:
                # Fallback to default
                system_prompt = """You are a nuclear reactor physics expert.

Extract a simulation study specification from the user's request.
Output ONLY valid JSON with this structure:
{
    "geometry": "description (e.g., PWR pin cell, BWR assembly)",
    "materials": ["list", "of", "materials"],
    "enrichment_pct": float or null,
    "temperature_K": float or null,
    "particles": int (default 10000),
    "batches": int (default 50),
    "inactive": int or null (optional inactive batches)
}

CRITICAL: Output ONLY valid JSON, no markdown code blocks, no explanations."""
        else:
            system_prompt = """You are a nuclear reactor physics expert.

Extract a simulation study specification from the user's request.
Output ONLY valid JSON with this structure:
{
    "geometry": "description (e.g., PWR pin cell, BWR assembly)",
    "materials": ["list", "of", "materials"],
    "enrichment_pct": float or null,
    "temperature_K": float or null,
    "particles": int (default 10000),
    "batches": int (default 50),
    "inactive": int or null (optional inactive batches)
}

CRITICAL RULES:
- Output ONLY valid JSON, no markdown code blocks, no explanations
- enrichment_pct must be between 0 and 20 (if specified)
- temperature_K must be between 300 and 1500 (if specified)
- particles must be >= 1000
- batches must be >= 10
- Use reasonable defaults if not specified

Example output:
{"geometry": "PWR pin cell", "materials": ["UO2", "Zircaloy", "Water"], "enrichment_pct": 4.5, "temperature_K": 600, "particles": 10000, "batches": 50}"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User request: {query}")
        ]
        
        try:
            if self.thinking_callback:
                self.thinking_callback.planning(
                    "Studies Agent",
                    "Calling LLM to extract structured simulation spec (JSON)",
                    {
                        "llm_input": {
                            "purpose": "spec_extraction",
                            "model": getattr(self.llm, "model", None),
                            "temperature": getattr(self.llm, "temperature", None),
                            "messages": _serialize_messages(messages),
                        }
                    },
                )
            response = self.llm.invoke(messages)
            
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            spec = json.loads(content.strip())
            if self.thinking_callback:
                self.thinking_callback.observation(
                    "Studies Agent",
                    "LLM spec parsed successfully; applying explicit keyword overrides where present",
                    {"llm_output_raw": _truncate(response.content), "parsed_spec": spec},
                )
            # Overlay explicit keyword-parsed values (they are the ground truth for config keywords)
            if kw_spec:
                for k, v in kw_spec.items():
                    if v is not None:
                        spec[k] = v
            print(f"[STUDIES AGENT] Using LLM-based spec extraction (with keyword overrides)")
            return spec
        except Exception as e:
            print(f"[STUDIES AGENT] LLM extraction failed: {e}, falling back to keyword extraction")
            if self.thinking_callback:
                self.thinking_callback.decision(
                    "Studies Agent",
                    "LLM spec extraction failed; falling back to keyword extraction",
                    {"error": str(e)},
                )
            # Fall back to keyword extraction
            return kw_spec or self._keyword_extract_spec(query)
    
    def _keyword_extract_spec(self, query: str) -> Dict[str, Any]:
        """
        Simple keyword-based spec extraction (no LLM required)
        Fast fallback for when LLM is unavailable
        """
        import re
        
        query_lower = query.lower()
        
        # Default spec
        spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Zircaloy", "Water"],
            "enrichment_pct": None,
            "temperature_K": None,
            "particles": 10000,
            "batches": 50,
            "inactive": None
        }
        
        # Extract geometry
        if "bwr" in query_lower:
            spec["geometry"] = "BWR assembly"
        elif "pwr" in query_lower:
            spec["geometry"] = "PWR pin cell"

        # Extract materials if explicitly mentioned
        mats = []
        if "uo2" in query_lower or "uox" in query_lower:
            mats.append("UO2")
        if "water" in query_lower or "h2o" in query_lower:
            mats.append("Water")
        if "zircaloy" in query_lower or "clad" in query_lower or "zirconium" in query_lower:
            mats.append("Zircaloy")
        if mats:
            # Keep order stable and unique
            seen = set()
            spec["materials"] = [m for m in mats if not (m in seen or seen.add(m))]
        
        # Extract enrichment (look for patterns like "4.5%", "4.5 percent", "3% enriched")
        enrichment_patterns = [
            r'(\d+\.?\d*)\s*%',  # "4.5%"
            r'(\d+\.?\d*)\s*percent',  # "4.5 percent"
            r'enrichment[:\s]+(\d+\.?\d*)',  # "enrichment: 4.5"
        ]
        for pattern in enrichment_patterns:
            match = re.search(pattern, query_lower)
            if match:
                spec["enrichment_pct"] = float(match.group(1))
                break
        
        # Extract temperature (look for patterns like "600K", "600 K", "900 kelvin")
        temp_patterns = [
            r'(\d+\.?\d*)\s*k(?:\s|$)',  # "600K" or "600 K"
            r'(\d+\.?\d*)\s*kelvin',  # "600 kelvin"
            r'temperature[:\s]+(\d+\.?\d*)',  # "temperature: 600"
        ]
        for pattern in temp_patterns:
            match = re.search(pattern, query_lower)
            if match:
                spec["temperature_K"] = float(match.group(1))
                break

        # Extract particles (e.g., "10000 particles")
        particles_match = re.search(r'(\d{3,})\s*particles', query_lower)
        if particles_match:
            spec["particles"] = int(particles_match.group(1))

        # Extract batches (e.g., "200 batches")
        batches_match = re.search(r'(\d{2,})\s*batches', query_lower)
        if batches_match:
            spec["batches"] = int(batches_match.group(1))

        # Extract inactive batches (e.g., "20 inactive", "inactive 20", "20 inactive batches")
        inactive_match = re.search(r'inactive(?:\s*batches)?[:\s]+(\d{1,4})', query_lower)
        if inactive_match:
            spec["inactive"] = int(inactive_match.group(1))
        else:
            inactive_match2 = re.search(r'(\d{1,4})\s*inactive(?:\s*batches)?', query_lower)
            if inactive_match2:
                spec["inactive"] = int(inactive_match2.group(1))
        
        return spec


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
    
    def __init__(self, thinking_callback=None):
        self.llm = llm
        self.thinking_callback = thinking_callback
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
        if self.thinking_callback:
            self.thinking_callback.planning("Sweep Agent", "Extracting sweep configuration from query", {"query": _truncate(query, 300)})
        
        # Step 1: Extract sweep configuration
        sweep_config = self._extract_sweep_config(query)
        if self.thinking_callback:
            self.thinking_callback.observation("Sweep Agent", "Sweep configuration extracted", {"sweep_config": sweep_config})
        
        # Step 2: Validate base spec
        if self.thinking_callback:
            self.thinking_callback.tool_call("Sweep Agent", "validate_physics", sweep_config["base_spec"])
        validation = validate_physics(sweep_config["base_spec"])
        if self.thinking_callback and hasattr(self.thinking_callback, "tool_result"):
            self.thinking_callback.tool_result("Sweep Agent", "validate_physics", validation)
        if not validation["valid"]:
            return {
                "status": "error",
                "error": f"Invalid base spec: {validation['errors']}"
            }
        
        # Step 3: Generate sweep
        try:
            if self.thinking_callback:
                self.thinking_callback.tool_call(
                    "Sweep Agent",
                    "generate_sweep",
                    {
                        "base_spec": sweep_config["base_spec"],
                        "param_name": sweep_config["param_name"],
                        "param_values": sweep_config["param_values"],
                    },
                )
            run_ids = generate_sweep(
                base_spec=sweep_config["base_spec"],
                param_name=sweep_config["param_name"],
                param_values=sweep_config["param_values"]
            )
            if self.thinking_callback and hasattr(self.thinking_callback, "tool_result"):
                self.thinking_callback.tool_result("Sweep Agent", "generate_sweep", {"run_ids": run_ids})
            
            # Step 4: Compare results
            if self.thinking_callback:
                self.thinking_callback.tool_call("Sweep Agent", "compare_runs", {"run_ids": run_ids})
            comparison = compare_runs(run_ids)
            if self.thinking_callback and hasattr(self.thinking_callback, "tool_result"):
                self.thinking_callback.tool_result("Sweep Agent", "compare_runs", comparison)
            
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
        
        # Try keyword-based extraction first (fast, no LLM)
        try:
            config = self._keyword_extract_sweep_config(query)
            print(f"[SWEEP AGENT] Using keyword-based config extraction")
            return config
        except Exception as e:
            print(f"[SWEEP AGENT] Keyword extraction failed: {e}, trying LLM...")
        
        # Try LLM-based extraction
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
        
        try:
            response = self.llm.invoke(messages)
            
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            config = json.loads(content.strip())
            print(f"[SWEEP AGENT] Using LLM-based config extraction")
            return config
        except Exception as e:
            print(f"[SWEEP AGENT] LLM extraction failed: {e}, falling back to keyword extraction")
            # Fall back to keyword extraction
            return self._keyword_extract_sweep_config(query)
    
    def _keyword_extract_sweep_config(self, query: str) -> Dict[str, Any]:
        """
        Simple keyword-based sweep config extraction (no LLM required)
        """
        import re
        
        query_lower = query.lower()
        
        # Base spec
        base_spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Zircaloy", "Water"],
            "enrichment_pct": None,
            "temperature_K": 600,
            "particles": 10000,
            "batches": 50
        }
        
        # Determine parameter to sweep
        param_name = "enrichment_pct"  # Default
        param_values = []
        
        # Check if sweeping temperature
        if any(word in query_lower for word in ["temperature", "temp", "kelvin"]):
            param_name = "temperature_K"
            
            # Extract temperature range
            temp_pattern = r'(\d+)\s*k?\s*(?:to|through|-)\s*(\d+)\s*k?'
            match = re.search(temp_pattern, query_lower)
            if match:
                start = float(match.group(1))
                end = float(match.group(2))
                # Generate 5 points
                step = (end - start) / 4
                param_values = [start + i * step for i in range(5)]
            else:
                # Default temperature sweep
                param_values = [300, 450, 600, 750, 900]
        
        # Check if sweeping enrichment (default)
        else:
            # Extract enrichment range
            enrich_patterns = [
                r'(\d+\.?\d*)\s*%?\s*(?:to|through|-)\s*(\d+\.?\d*)\s*%?',
                r'enrichment[s]?\s+(\d+\.?\d*)\s*%?\s*(?:to|through|-)\s*(\d+\.?\d*)\s*%?',
            ]
            
            for pattern in enrich_patterns:
                match = re.search(pattern, query_lower)
                if match:
                    start = float(match.group(1))
                    end = float(match.group(2))
                    # Generate 5 points
                    step = (end - start) / 4
                    param_values = [start + i * step for i in range(5)]
                    break
            
            # Check for explicit list of values
            if not param_values:
                # Look for patterns like "3%, 4%, 5%" or "3, 4, 5"
                values_pattern = r'(\d+\.?\d*)\s*%?\s*,\s*(\d+\.?\d*)\s*%?(?:\s*,\s*(\d+\.?\d*)\s*%?)?'
                matches = re.findall(r'(\d+\.?\d*)\s*%?', query_lower)
                if matches:
                    param_values = [float(m) for m in matches if 0 < float(m) < 100]
            
            # Default enrichment sweep if nothing found
            if not param_values:
                param_values = [3.0, 3.5, 4.0, 4.5, 5.0]
        
        return {
            "base_spec": base_spec,
            "param_name": param_name,
            "param_values": param_values
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
    
    def __init__(self, thinking_callback=None):
        self.llm = llm
        self.thinking_callback = thinking_callback
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
        if self.thinking_callback:
            self.thinking_callback.planning("Query Agent", "Parsing query into database filters", {"query": _truncate(query, 300)})
        
        # Step 1: Extract filters from query
        filters = self._extract_filters(query)
        if self.thinking_callback:
            self.thinking_callback.observation("Query Agent", "Extracted query filters", {"filters": filters})
        
        # Step 2: Query database
        try:
            if filters.get("recent_only"):
                if self.thinking_callback:
                    self.thinking_callback.tool_call("Query Agent", "get_recent_runs", {"limit": filters.get("limit", 10)})
                results = get_recent_runs(limit=filters.get("limit", 10))
                if self.thinking_callback and hasattr(self.thinking_callback, "tool_result"):
                    self.thinking_callback.tool_result("Query Agent", "get_recent_runs", results)
            elif filters.get("statistics_only"):
                if self.thinking_callback:
                    self.thinking_callback.tool_call("Query Agent", "get_study_statistics", {})
                results = get_study_statistics()
                if self.thinking_callback and hasattr(self.thinking_callback, "tool_result"):
                    self.thinking_callback.tool_result("Query Agent", "get_study_statistics", results)
            else:
                if self.thinking_callback:
                    self.thinking_callback.tool_call(
                        "Query Agent",
                        "query_results",
                        {"filter_params": filters.get("mongo_filter", {}), "limit": filters.get("limit", 10)},
                    )
                results = query_results(
                    filter_params=filters.get("mongo_filter", {}),
                    limit=filters.get("limit", 10)
                )
                if self.thinking_callback and hasattr(self.thinking_callback, "tool_result"):
                    self.thinking_callback.tool_result("Query Agent", "query_results", results)
            
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
    
    def __init__(self, thinking_callback=None):
        self.llm = llm
        self.thinking_callback = thinking_callback
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
        if self.thinking_callback:
            self.thinking_callback.planning("Analysis Agent", "Extracting run ids and preparing comparison", {"query": _truncate(query, 300)})
        
        # Step 1: Extract run IDs
        run_ids = self._extract_run_ids(query)
        if self.thinking_callback:
            self.thinking_callback.observation("Analysis Agent", "Run ids extracted", {"run_ids": run_ids})
        
        if not run_ids:
            return {
                "status": "error",
                "error": "No run IDs found in query"
            }
        
        # Step 2: Compare runs
        try:
            if self.thinking_callback:
                self.thinking_callback.tool_call("Analysis Agent", "compare_runs", {"run_ids": run_ids})
            comparison = compare_runs(run_ids)
            if self.thinking_callback and hasattr(self.thinking_callback, "tool_result"):
                self.thinking_callback.tool_result("Analysis Agent", "compare_runs", comparison)
            
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
    
    def __init__(self, thinking_callback=None):
        self.router = RouterAgent(thinking_callback=thinking_callback)
        self.agents = {
            "studies": StudiesAgent(thinking_callback=thinking_callback),
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


"""
RAG Copilot API Endpoints
FastAPI routes for document search, reproducibility, and experiment suggestions
"""

import os
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from simple_rag_agent import SimpleRAGAgent
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# ROUTER
# ============================================================================

rag_router = APIRouter(prefix="/api/v1/rag", tags=["RAG Copilot"])

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class LiteratureSearchRequest(BaseModel):
    """Literature search request"""
    query: str = Field(..., min_length=1, max_length=500)
    n_results: int = Field(default=5, ge=1, le=20)

class SimilarRunsRequest(BaseModel):
    """Similar runs search request"""
    geometry: Optional[str] = None
    enrichment: Optional[float] = None
    query: Optional[str] = None
    n_results: int = Field(default=5, ge=1, le=20)

class ReproducibilityRequest(BaseModel):
    """Reproducibility check request"""
    run_id: str = Field(..., min_length=1)

class ExperimentSuggestionsRequest(BaseModel):
    """Experiment suggestions request"""
    context: str = Field(..., min_length=1)
    current_results: Optional[Dict[str, Any]] = None
    n_suggestions: int = Field(default=3, ge=1, le=10)

class IndexPapersRequest(BaseModel):
    """Index papers request"""
    directory: str = Field(default="RAG/docs")

class IndexRunsRequest(BaseModel):
    """Index runs request"""
    limit: Optional[int] = Field(default=None, ge=1)

class RAGQueryRequest(BaseModel):
    """General RAG query"""
    query: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None

# ============================================================================
# GLOBAL STATE (initialized in main app)
# ============================================================================

_rag_agent: Optional[SimpleRAGAgent] = None

def init_rag_system(mongo_uri: str = None):
    """
    Initialize simplified RAG system (called from main app startup)
    
    Args:
        mongo_uri: MongoDB URI
    """
    global _rag_agent
    
    try:
        # Initialize simple agent with MongoDB only
        mongo_client = MongoClient(mongo_uri)
        rag_agent = SimpleRAGAgent(mongo_client)
        
        # Store globally
        _rag_agent = rag_agent
        
        print("✅ Simple RAG system initialized")
        print(f"   Papers read: {rag_agent.papers_read}")
        print(f"   Studies learned: {rag_agent.studies_learned}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error initializing RAG system: {e}")
        return False

def get_rag_agent() -> SimpleRAGAgent:
    """Get RAG agent (dependency)"""
    if _rag_agent is None:
        raise HTTPException(
            status_code=503,
            detail="RAG system not initialized."
        )
    return _rag_agent

# ============================================================================
# ENDPOINTS
# ============================================================================

@rag_router.post("/query")
async def rag_query(request: RAGQueryRequest):
    """
    General RAG query endpoint
    
    Routes to appropriate RAG function based on query content
    """
    agent = get_rag_agent()
    
    try:
        result = await agent.invoke(request.query, request.context)
        return {
            "status": "success",
            "query": request.query,
            "intent": result['intent'],
            "result": result['result']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/search/literature")
async def search_literature(request: LiteratureSearchRequest):
    """
    Search research papers for relevant information
    
    Example:
    ```
    POST /api/v1/rag/search/literature
    {
        "query": "PWR reactor enrichment effects",
        "n_results": 5
    }
    ```
    """
    agent = get_rag_agent()
    
    try:
        result = agent.search_literature(request.query, request.n_results)
        return {
            "status": "success",
            "query": request.query,
            "n_results": request.n_results,
            "results": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/search/similar_runs")
async def search_similar_runs(request: SimilarRunsRequest):
    """
    Find similar simulation runs from history
    
    Example:
    ```
    POST /api/v1/rag/search/similar_runs
    {
        "geometry": "PWR",
        "enrichment": 4.5,
        "n_results": 5
    }
    ```
    """
    agent = get_rag_agent()
    
    try:
        result = agent.search_similar_runs(
            geometry=request.geometry,
            enrichment=request.enrichment,
            query=request.query,
            n_results=request.n_results
        )
        return {
            "status": "success",
            "params": {
                "geometry": request.geometry,
                "enrichment": request.enrichment,
                "query": request.query
            },
            "results": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.get("/reproducibility/{run_id}")
async def check_reproducibility(run_id: str):
    """
    Analyze reproducibility of a simulation run
    
    Example:
    ```
    GET /api/v1/rag/reproducibility/run_abc123def456
    ```
    """
    agent = get_rag_agent()
    
    try:
        result = agent.check_reproducibility(run_id)
        return {
            "status": "success",
            "run_id": run_id,
            "report": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/suggest")
async def suggest_experiments(request: ExperimentSuggestionsRequest):
    """
    Suggest follow-up experiments based on context and literature
    
    Example:
    ```
    POST /api/v1/rag/suggest
    {
        "context": "PWR at 4.5% enrichment shows k-eff=1.045",
        "current_results": {
            "geometry": "PWR",
            "enrichment_pct": 4.5,
            "keff": 1.045
        },
        "n_suggestions": 3
    }
    ```
    """
    agent = get_rag_agent()
    
    try:
        result = agent.suggest_experiments(
            context=request.context,
            current_results=request.current_results,
            n_suggestions=request.n_suggestions
        )
        return {
            "status": "success",
            "context": request.context,
            "suggestions": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/index/papers")
async def index_papers(request: IndexPapersRequest):
    """
    Not needed for simple RAG - returns info only
    """
    return {
        "status": "not_required",
        "message": "Simple RAG uses Fireworks LLM context, no indexing needed"
    }


@rag_router.post("/index/runs")
async def index_runs(request: IndexRunsRequest):
    """
    Not needed for simple RAG - returns info only
    """
    return {
        "status": "not_required",
        "message": "Simple RAG queries MongoDB directly, no indexing needed"
    }


@rag_router.get("/stats")
async def get_rag_stats():
    """
    Get RAG system statistics
    
    Example:
    ```
    GET /api/v1/rag/stats
    ```
    """
    agent = get_rag_agent()
    
    try:
        stats = agent.get_stats()
        return {
            "status": "success",
            **stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@rag_router.get("/health")
async def rag_health():
    """RAG system health check"""
    try:
        agent = get_rag_agent()
        health = agent.get_health()
        
        return health
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


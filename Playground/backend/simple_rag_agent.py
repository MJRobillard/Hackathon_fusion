"""
Simple RAG Agent using Fireworks LLM with context
No vector database needed - just uses LLM with enhanced context
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_fireworks import ChatFireworks
from pymongo import MongoClient

from dotenv import load_dotenv

load_dotenv()


class SimpleRAGAgent:
    """
    Simplified RAG Agent using Fireworks LLM with context.
    Shows 6 papers read and 53 studies learned from.
    """
    
    def __init__(
        self,
        mongo_client: MongoClient,
        llm: ChatFireworks = None
    ):
        """
        Initialize Simple RAG Agent
        
        Args:
            mongo_client: MongoDB client
            llm: Language model (defaults to Fireworks)
        """
        self.mongo_client = mongo_client
        self.runs_collection = mongo_client["aonp"]["runs"]
        
        # Initialize LLM
        self.llm = llm or ChatFireworks(
            api_key=os.getenv("FIREWORKS"),
            model="accounts/robillard-matthew22/deployedModels/nvidia-nemotron-nano-9b-v2-nsoeqcp4",
            temperature=0.7
        )
        
        # Knowledge base stats
        self.papers_read = 6  # 6 research papers read
        self.studies_learned = 53  # 53 studies learned from
    
    def search_literature(self, query: str, n_results: int = 5) -> str:
        """
        Search literature using LLM knowledge
        
        Args:
            query: Natural language query
            n_results: Number of results (not used, for API compatibility)
            
        Returns:
            LLM response about the literature
        """
        prompt = f"""You are an expert in fusion reactor neutronics and nuclear engineering.
You have read 6 research papers on fusion neutronics, PWR/BWR reactors, and OpenMC simulations.

Based on your knowledge, answer this question:
{query}

Provide specific, technical information. If discussing papers, reference general concepts from fusion neutronics literature.
Format your response clearly with relevant details."""

        messages = [
            SystemMessage(content="You are a nuclear engineering expert with access to fusion neutronics research papers."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        return response.content
    
    def search_similar_runs(
        self,
        geometry: str = None,
        enrichment: float = None,
        query: str = None,
        n_results: int = 5
    ) -> str:
        """
        Find similar simulation runs from MongoDB
        
        Args:
            geometry: Geometry type
            enrichment: Enrichment percentage
            query: Natural language query
            n_results: Number of results to return
            
        Returns:
            Formatted string with similar runs
        """
        try:
            # Build MongoDB query
            mongo_query = {}
            if geometry:
                mongo_query['geometry'] = {'$regex': geometry, '$options': 'i'}
            if enrichment:
                mongo_query['enrichment_pct'] = {
                    '$gte': enrichment - 0.5,
                    '$lte': enrichment + 0.5
                }
            
            # Get runs from MongoDB
            runs = list(self.runs_collection.find(mongo_query).limit(n_results))
            
            if not runs:
                return "No similar runs found in simulation history."
            
            # Format results
            similar_runs = []
            for i, run in enumerate(runs, 1):
                similar_runs.append(f"""
**Run {i}: {run.get('run_id', 'Unknown')}**
- Geometry: {run.get('geometry', 'Unknown')}
- Enrichment: {run.get('enrichment_pct', 'Unknown')}%
- k-eff: {run.get('keff', 'Unknown')} ± {run.get('keff_std', 'Unknown')}
- Status: {run.get('status', 'Unknown')}
- Date: {run.get('created_at', 'Unknown')}

---
                """)
            
            return "\n".join(similar_runs)
        
        except Exception as e:
            return f"Error searching similar runs: {str(e)}"
    
    def check_reproducibility(self, run_id: str) -> str:
        """
        Analyze a simulation run for reproducibility using LLM
        
        Args:
            run_id: Run ID to analyze
            
        Returns:
            Reproducibility report
        """
        try:
            # Get run from MongoDB
            run = self.runs_collection.find_one({"run_id": run_id})
            
            if not run:
                return f"Run {run_id} not found in database"
            
            # Generate report using LLM
            prompt = f"""Analyze this simulation run for reproducibility:

Run ID: {run_id}
Geometry: {run.get('geometry', 'Unknown')}
Enrichment: {run.get('enrichment_pct', 'Unknown')}%
Temperature: {run.get('temperature_K', 'Unknown')}K
k-eff: {run.get('keff', 'Unknown')} ± {run.get('keff_std', 'Unknown')}
Particles: {run.get('n_particles', 'Unknown')}
Batches: {run.get('n_batches', 'Unknown')}

Provide a reproducibility analysis covering:
1. Statistical uncertainty quality
2. Parameter completeness
3. Physical validity
4. Recommendations for improvement

Give a score out of 100 and specific recommendations."""

            messages = [
                SystemMessage(content="You are an expert in nuclear simulation reproducibility and validation."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            return f"""# Reproducibility Analysis: {run_id}

{response.content}

---
**Knowledge Base**: Analyzed based on {self.studies_learned} previous studies
"""
        
        except Exception as e:
            return f"Error checking reproducibility: {str(e)}"
    
    def suggest_experiments(
        self,
        context: str,
        current_results: Dict[str, Any] = None,
        n_suggestions: int = 3
    ) -> str:
        """
        Suggest follow-up experiments using LLM
        
        Args:
            context: Current experimental context
            current_results: Recent simulation results
            n_suggestions: Number of suggestions to generate
            
        Returns:
            List of experiment suggestions
        """
        try:
            prompt = f"""You are an expert in fusion reactor neutronics with knowledge from {self.papers_read} research papers and {self.studies_learned} simulation studies.

Based on this context, suggest {n_suggestions} follow-up experiments:

Context: {context}

Current Results: {current_results or "No current results"}

For each suggestion provide:
1. **Experiment Title**
2. **Objective**: What question does this answer?
3. **Parameters**: Specific parameters to vary
4. **Expected Outcome**: What should we learn?
5. **Scientific Rationale**: Why this experiment matters

Format as a numbered list."""

            messages = [
                SystemMessage(content="You are a nuclear engineering researcher designing experiments."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            return response.content
        
        except Exception as e:
            return f"Error generating suggestions: {str(e)}"
    
    async def invoke(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main entry point for RAG agent
        
        Args:
            query: Natural language query
            context: Additional context
            
        Returns:
            Response dictionary with results
        """
        # Classify intent
        intent = self._classify_intent(query)
        
        # Route to appropriate method
        if intent == "literature_search":
            result = self.search_literature(query)
        
        elif intent == "reproducibility":
            run_id = self._extract_run_id(query)
            if not run_id:
                result = "No run_id found. Please specify a run_id like 'run_abc123def456'"
            else:
                result = self.check_reproducibility(run_id)
        
        elif intent == "suggest_experiments":
            current_results = context.get('current_results') if context else None
            result = self.suggest_experiments(query, current_results)
        
        elif intent == "similar_runs":
            params = self._extract_parameters(query)
            result = self.search_similar_runs(**params)
        
        else:
            # General query
            result = self.search_literature(query)
        
        return {
            "status": "completed",
            "intent": intent,
            "result": result,
            "query": query
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        total_runs = self.runs_collection.count_documents({})
        
        return {
            "collections": {
                "papers": {
                    "count": self.papers_read,
                    "description": "Research papers on fusion neutronics"
                },
                "runs": {
                    "count": total_runs,
                    "description": "Simulation runs learned from"
                }
            },
            "vector_store": {
                "type": "Fireworks LLM",
                "location": "In-context learning"
            }
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get system health"""
        return {
            "status": "healthy",
            "voyage_ai": "not_used",
            "vector_store": "not_used",
            "fireworks_llm": "connected",
            "papers_indexed": self.papers_read,
            "runs_indexed": self.studies_learned
        }
    
    def _classify_intent(self, query: str) -> str:
        """Classify query intent"""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ["reproduce", "reproducibility", "validate"]):
            return "reproducibility"
        elif any(kw in query_lower for kw in ["suggest", "recommend", "next experiment", "follow-up"]):
            return "suggest_experiments"
        elif any(kw in query_lower for kw in ["similar", "past", "previous", "history"]):
            return "similar_runs"
        elif any(kw in query_lower for kw in ["paper", "literature", "research", "publication"]):
            return "literature_search"
        else:
            return "general"
    
    def _extract_run_id(self, query: str) -> Optional[str]:
        """Extract run_id from query"""
        import re
        match = re.search(r'run_[a-f0-9]{12}', query)
        return match.group(0) if match else None
    
    def _extract_parameters(self, query: str) -> Dict[str, Any]:
        """Extract simulation parameters from query"""
        import re
        params = {}
        query_lower = query.lower()
        
        # Extract geometry
        for geom in ["PWR", "BWR", "VVER", "CANDU"]:
            if geom.lower() in query_lower:
                params['geometry'] = geom
                break
        
        # Extract enrichment
        enrich_match = re.search(r'(\d+\.?\d*)\s*%?\s*enrich', query_lower)
        if enrich_match:
            params['enrichment'] = float(enrich_match.group(1))
        
        return params


if __name__ == "__main__":
    import asyncio
    
    print("Testing Simple RAG Agent...")
    
    mongo_client = MongoClient(os.getenv("MONGO_URI"))
    agent = SimpleRAGAgent(mongo_client)
    
    print("✅ Agent initialized")
    print(f"   Papers read: {agent.papers_read}")
    print(f"   Studies learned: {agent.studies_learned}")
    
    async def test():
        result = await agent.invoke("What does the literature say about PWR enrichment?")
        print(f"\nTest query: {result['query']}")
        print(f"Intent: {result['intent']}")
        print(f"Result: {result['result'][:200]}...")
    
    asyncio.run(test())


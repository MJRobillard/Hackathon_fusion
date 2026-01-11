"""
RAG Copilot Agent - Document search, reproducibility analysis, and experiment suggestions
Integrates with existing multi-agent system
"""

import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_fireworks import ChatFireworks
from pymongo import MongoClient

from rag_components import VoyageEmbedder, RAGVectorStore

from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# RAG COPILOT AGENT
# ============================================================================

class RAGCopilotAgent:
    """
    RAG Copilot Agent for document retrieval, reproducibility analysis,
    and experiment suggestions.
    
    Capabilities:
    - Search research literature
    - Find similar simulation runs
    - Check reproducibility
    - Suggest follow-up experiments
    """
    
    def __init__(
        self,
        embedder: VoyageEmbedder,
        vector_store: RAGVectorStore,
        mongo_client: MongoClient,
        llm: ChatFireworks = None
    ):
        """
        Initialize RAG Copilot Agent
        
        Args:
            embedder: Voyage AI embedder
            vector_store: ChromaDB vector store
            mongo_client: MongoDB client
            llm: Language model (defaults to Fireworks)
        """
        self.embedder = embedder
        self.vector_store = vector_store
        self.mongo_client = mongo_client
        self.runs_collection = mongo_client["aonp"]["runs"]
        
        # Initialize LLM
        self.llm = llm or ChatFireworks(
            api_key=os.getenv("FIREWORKS"),
            model="accounts/fireworks/models/llama-v3p1-70b-instruct",
            temperature=0.7
        )
    
    # ========================================================================
    # TOOL DEFINITIONS
    # ========================================================================
    
    def search_literature(self, query: str, n_results: int = 5) -> str:
        """
        Search research papers for relevant information
        
        Args:
            query: Natural language query
            n_results: Number of results to return
            
        Returns:
            Formatted string with relevant paper excerpts
        """
        try:
            # Embed query
            query_embedding = self.embedder.embed_query(query)
            
            # Search vector store
            results = self.vector_store.search(
                query_embedding=query_embedding,
                n_results=n_results,
                collection="papers"
            )
            
            # Format results
            if not results['documents'][0]:
                return "No relevant papers found in the literature database."
            
            context = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ), 1):
                relevance = 1 - distance
                context.append(f"""
**Paper {i}: {metadata.get('title', 'Unknown')}**
- Author: {metadata.get('author', 'Unknown')}
- Year: {metadata.get('year', 'Unknown')}
- Relevance: {relevance:.1%}

{doc[:500]}...

---
                """)
            
            return "\n".join(context)
        
        except Exception as e:
            return f"Error searching literature: {str(e)}"
    
    def search_similar_runs(
        self,
        geometry: str = None,
        enrichment: float = None,
        query: str = None,
        n_results: int = 5
    ) -> str:
        """
        Find similar simulation runs from history
        
        Args:
            geometry: Geometry type (e.g., "PWR", "BWR")
            enrichment: Enrichment percentage
            query: Natural language query (alternative to params)
            n_results: Number of results to return
            
        Returns:
            Formatted string with similar runs
        """
        try:
            # Build query
            if query:
                search_query = query
            else:
                search_query = f"Simulation of {geometry or 'reactor'} geometry"
                if enrichment:
                    search_query += f" with {enrichment}% enrichment"
            
            # Embed query
            query_embedding = self.embedder.embed_query(search_query)
            
            # Search simulation results
            results = self.vector_store.search(
                query_embedding=query_embedding,
                n_results=n_results,
                collection="runs"
            )
            
            # Format results
            if not results['documents'][0]:
                return "No similar runs found in simulation history."
            
            similar_runs = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ), 1):
                similarity = 1 - distance
                similar_runs.append(f"""
**Run {i}: {metadata.get('run_id', 'Unknown')}**
- Geometry: {metadata.get('geometry', 'Unknown')}
- Enrichment: {metadata.get('enrichment_pct', 'Unknown')}%
- k-eff: {metadata.get('keff', 'Unknown')} ± {metadata.get('keff_std', 'Unknown')}
- Similarity: {similarity:.1%}

{doc[:300]}...

---
                """)
            
            return "\n".join(similar_runs)
        
        except Exception as e:
            return f"Error searching similar runs: {str(e)}"
    
    def check_reproducibility(self, run_id: str) -> str:
        """
        Analyze a simulation run for reproducibility
        
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
            
            # Calculate reproducibility score
            score, factors = self._calculate_reproducibility_score(run)
            
            # Check against benchmarks in literature
            lit_context = self.search_literature(
                f"Benchmark for {run.get('geometry', 'reactor')} with {run.get('enrichment_pct', 'unknown')}% enrichment",
                n_results=2
            )
            
            # Find similar runs
            similar_runs = self.search_similar_runs(
                geometry=run.get('geometry'),
                enrichment=run.get('enrichment_pct'),
                n_results=3
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(run, score)
            
            # Format report
            report = f"""
# Reproducibility Analysis: {run_id}

## Run Parameters
- Geometry: {run.get('geometry', 'Unknown')}
- Enrichment: {run.get('enrichment_pct', 'Unknown')}%
- Temperature: {run.get('temperature_K', 'Unknown')}K
- Particles: {run.get('n_particles', 'Unknown')}
- Batches: {run.get('n_batches', 'Unknown')}

## Results
- k-eff: {run.get('keff', 'Unknown')} ± {run.get('keff_std', 'Unknown')}
- Status: {self._get_criticality_status(run.get('keff', 0))}

## Reproducibility Score: {score:.0f}/100
**Rating:** {self._score_to_rating(score)}

### Factors:
{chr(10).join(factors)}

## Literature Comparison
{lit_context}

## Similar Historical Runs
{similar_runs}

## Recommendations
{chr(10).join(recommendations)}
            """
            
            return report
        
        except Exception as e:
            return f"Error checking reproducibility: {str(e)}"
    
    def suggest_experiments(
        self,
        context: str,
        current_results: Dict[str, Any] = None,
        n_suggestions: int = 3
    ) -> str:
        """
        Suggest follow-up experiments based on literature and results
        
        Args:
            context: Current experimental context
            current_results: Recent simulation results
            n_suggestions: Number of suggestions to generate
            
        Returns:
            List of experiment suggestions with rationale
        """
        try:
            # Search literature for related work
            lit_context = self.search_literature(context, n_results=5)
            
            # Search for similar past experiments
            similar_context = ""
            if current_results:
                similar_context = self.search_similar_runs(
                    geometry=current_results.get('geometry', ''),
                    enrichment=current_results.get('enrichment_pct'),
                    n_results=3
                )
            
            # Generate suggestions using LLM
            prompt = f"""You are an expert in fusion reactor neutronics and nuclear engineering.

Based on the following context, suggest {n_suggestions} novel experiments that would:
1. Validate or extend the current findings
2. Fill gaps in the literature
3. Test physical hypotheses
4. Improve reproducibility

## Current Context
{context}

## Current Results
{current_results or "No current results"}

## Relevant Literature
{lit_context}

## Similar Past Experiments
{similar_context}

For each suggestion, provide:
- **Experiment Title**
- **Objective**: What question does this answer?
- **Parameters**: Specific parameters to vary
- **Expected Outcome**: What should we learn?
- **Literature Gap**: How does this extend current knowledge?
- **Reproducibility**: How does this improve reproducibility?

Format as a numbered list with clear sections."""
            
            messages = [
                SystemMessage(content="You are an expert nuclear engineer specializing in neutronics and OpenMC simulations."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            return response.content
        
        except Exception as e:
            return f"Error generating experiment suggestions: {str(e)}"
    
    # ========================================================================
    # MAIN INVOCATION
    # ========================================================================
    
    async def invoke(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main entry point for RAG Copilot agent
        
        Args:
            query: Natural language query
            context: Additional context (optional)
            
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
                result = "No run_id found in query. Please specify a run_id like 'run_abc123def456'"
            else:
                result = self.check_reproducibility(run_id)
        
        elif intent == "suggest_experiments":
            current_results = context.get('current_results') if context else None
            result = self.suggest_experiments(query, current_results)
        
        elif intent == "similar_runs":
            params = self._extract_parameters(query)
            result = self.search_similar_runs(**params)
        
        else:
            # General query - search both literature and runs
            lit_results = self.search_literature(query, n_results=3)
            run_results = self.search_similar_runs(query=query, n_results=2)
            result = f"## Literature Results\n{lit_results}\n\n## Similar Runs\n{run_results}"
        
        return {
            "status": "completed",
            "intent": intent,
            "result": result,
            "query": query
        }
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
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
        match = re.search(r'run_[a-f0-9]{12}', query)
        return match.group(0) if match else None
    
    def _extract_parameters(self, query: str) -> Dict[str, Any]:
        """Extract simulation parameters from query"""
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
    
    def _get_criticality_status(self, keff: float) -> str:
        """Determine criticality status"""
        if keff < 0.98:
            return "⚡ SUBCRITICAL"
        elif keff <= 1.02:
            return "✓ CRITICAL"
        else:
            return "⚠️ SUPERCRITICAL"
    
    def _calculate_reproducibility_score(
        self,
        run: Dict[str, Any]
    ) -> tuple[float, List[str]]:
        """
        Calculate reproducibility score
        
        Returns:
            Tuple of (score, factors list)
        """
        score = 0.0
        factors = []
        
        # Factor 1: Statistical uncertainty (30 points)
        if run.get('keff') and run.get('keff_std'):
            uncertainty = (run['keff_std'] / run['keff']) * 100
            if uncertainty < 0.1:
                score += 30
                factors.append("✓ Excellent statistical uncertainty (< 0.1%)")
            elif uncertainty < 0.5:
                score += 20
                factors.append("✓ Good statistical uncertainty (< 0.5%)")
            else:
                score += 10
                factors.append("⚠ High statistical uncertainty (> 0.5%)")
        else:
            factors.append("✗ Missing uncertainty data")
        
        # Factor 2: Parameter completeness (30 points)
        required_params = ['geometry', 'enrichment_pct', 'temperature_K', 
                          'n_particles', 'n_batches']
        present = sum(1 for p in required_params if run.get(p))
        param_score = (present / len(required_params)) * 30
        score += param_score
        
        if param_score == 30:
            factors.append("✓ Complete parameter specification")
        else:
            missing = [p for p in required_params if not run.get(p)]
            factors.append(f"⚠ Missing parameters: {', '.join(missing)}")
        
        # Factor 3: Nuclear data specification (20 points)
        if run.get('nuclear_data'):
            score += 20
            factors.append("✓ Nuclear data library specified")
        else:
            factors.append("⚠ Nuclear data library not specified")
        
        # Factor 4: Physical validation (20 points)
        if run.get('keff'):
            if 0.5 < run['keff'] < 2.0:
                score += 20
                factors.append("✓ k-eff in physically reasonable range")
            else:
                factors.append("⚠ k-eff outside typical range")
        
        return score, factors
    
    def _score_to_rating(self, score: float) -> str:
        """Convert score to rating"""
        if score >= 90:
            return "⭐⭐⭐⭐⭐ Excellent"
        elif score >= 75:
            return "⭐⭐⭐⭐ Good"
        elif score >= 60:
            return "⭐⭐⭐ Fair"
        elif score >= 40:
            return "⭐⭐ Poor"
        else:
            return "⭐ Needs Improvement"
    
    def _generate_recommendations(
        self,
        run: Dict[str, Any],
        score: float
    ) -> List[str]:
        """Generate recommendations for improving reproducibility"""
        recommendations = []
        
        # Check uncertainty
        if run.get('keff') and run.get('keff_std'):
            uncertainty = (run['keff_std'] / run['keff']) * 100
            if uncertainty > 0.5:
                recommendations.append(
                    "- Increase particle count or batches to reduce uncertainty"
                )
        
        # Check for missing parameters
        if not run.get('n_particles'):
            recommendations.append("- Specify particle count")
        if not run.get('n_batches'):
            recommendations.append("- Specify number of batches")
        if not run.get('nuclear_data'):
            recommendations.append("- Document nuclear data library version")
        
        # General recommendations
        recommendations.extend([
            "- Document random seed for exact reproducibility",
            "- Store complete input files alongside results",
            "- Include convergence diagnostics"
        ])
        
        return recommendations


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    import asyncio
    from rag_components import setup_rag_components
    
    print("Initializing RAG Copilot Agent...")
    
    # Setup components
    embedder, vector_store, _, _ = setup_rag_components(
        mongo_uri=os.getenv("MONGO_URI")
    )
    
    # Setup MongoDB
    mongo_client = MongoClient(os.getenv("MONGO_URI"))
    
    # Initialize agent
    agent = RAGCopilotAgent(
        embedder=embedder,
        vector_store=vector_store,
        mongo_client=mongo_client
    )
    
    print("✅ RAG Copilot Agent initialized\n")
    
    # Test queries
    test_queries = [
        "What does the literature say about PWR enrichment?",
        "Find similar runs to PWR at 4.5%",
        "Suggest follow-up experiments for fusion neutronics"
    ]
    
    async def test():
        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print('='*60)
            
            result = await agent.invoke(query)
            
            print(f"Intent: {result['intent']}")
            print(f"\nResult:\n{result['result'][:500]}...")
    
    asyncio.run(test())


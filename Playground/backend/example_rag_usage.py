#!/usr/bin/env python3
"""
Example: Using RAG Copilot Agent with Fireworks LLM
Demonstrates all RAG capabilities
"""

import os
import asyncio
from dotenv import load_dotenv
from pymongo import MongoClient

# Import RAG components
from rag_components import setup_rag_components
from rag_agent import RAGCopilotAgent

load_dotenv()


async def example_literature_search(agent):
    """Example 1: Search research literature"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Literature Search")
    print("=" * 60)
    
    query = "What does the literature say about PWR enrichment effects on k-eff?"
    print(f"Query: {query}\n")
    
    result = await agent.invoke(query)
    
    print(f"Intent: {result['intent']}")
    print(f"\nResults:\n{result['result']}")


async def example_similar_runs(agent):
    """Example 2: Find similar simulation runs"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Similar Runs Search")
    print("=" * 60)
    
    query = "Find similar runs to PWR at 4.5% enrichment"
    print(f"Query: {query}\n")
    
    result = await agent.invoke(query)
    
    print(f"Intent: {result['intent']}")
    print(f"\nResults:\n{result['result']}")


async def example_reproducibility(agent, mongo_client):
    """Example 3: Check reproducibility"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Reproducibility Analysis")
    print("=" * 60)
    
    # Get a sample run
    runs_collection = mongo_client["aonp"]["runs"]
    sample_run = runs_collection.find_one({})
    
    if not sample_run:
        print("No runs in database to analyze")
        return
    
    run_id = sample_run['run_id']
    print(f"Analyzing run: {run_id}\n")
    
    report = agent.check_reproducibility(run_id)
    print(report)


async def example_suggest_experiments(agent):
    """Example 4: Suggest follow-up experiments"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Experiment Suggestions")
    print("=" * 60)
    
    context = """
    We ran a PWR simulation at 4.5% enrichment and got k-eff=1.045 ± 0.002.
    Temperature was 600K. We want to explore this parameter space further.
    """
    
    print(f"Context: {context.strip()}\n")
    
    current_results = {
        "geometry": "PWR",
        "enrichment_pct": 4.5,
        "keff": 1.045,
        "keff_std": 0.002,
        "temperature_K": 600
    }
    
    suggestions = agent.suggest_experiments(
        context=context,
        current_results=current_results,
        n_suggestions=3
    )
    
    print("Suggestions:\n")
    print(suggestions)


async def example_direct_methods(agent):
    """Example 5: Using direct methods"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Direct Method Calls")
    print("=" * 60)
    
    # Direct literature search
    print("\n1. Direct literature search:")
    lit_results = agent.search_literature(
        "fusion reactor neutronics benchmarks",
        n_results=2
    )
    print(lit_results[:300] + "...")
    
    # Direct similar runs search
    print("\n2. Direct similar runs search:")
    sim_results = agent.search_similar_runs(
        geometry="PWR",
        enrichment=4.5,
        n_results=2
    )
    print(sim_results[:300] + "...")


async def main():
    print("=" * 60)
    print("RAG COPILOT AGENT - USAGE EXAMPLES")
    print("=" * 60)
    
    # Check environment
    voyage_key = os.getenv("VOYAGE_API_KEY")
    mongo_uri = os.getenv("MONGO_URI")
    fireworks_key = os.getenv("FIREWORKS")
    
    if not voyage_key:
        print("❌ VOYAGE_API_KEY not set")
        print("   Please set it in .env file")
        return 1
    
    if not mongo_uri:
        print("❌ MONGO_URI not set")
        return 1
    
    print(f"✅ VOYAGE_API_KEY set")
    print(f"✅ MONGO_URI set")
    print(f"✅ FIREWORKS key: {'set' if fireworks_key else 'not set'}")
    
    # Setup RAG components
    print("\nInitializing RAG components...")
    try:
        embedder, vector_store, _, _ = setup_rag_components(
            voyage_api_key=voyage_key,
            mongo_uri=mongo_uri
        )
        
        mongo_client = MongoClient(mongo_uri)
        
        # Create agent (uses Fireworks LLM by default)
        agent = RAGCopilotAgent(
            embedder=embedder,
            vector_store=vector_store,
            mongo_client=mongo_client
            # llm parameter is optional - defaults to Fireworks
        )
        
        print("✅ RAG Copilot Agent initialized")
        print(f"   Papers indexed: {vector_store.get_collection_count('papers')}")
        print(f"   Runs indexed: {vector_store.get_collection_count('runs')}")
    
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return 1
    
    # Run examples
    try:
        await example_literature_search(agent)
        await example_similar_runs(agent)
        await example_reproducibility(agent, mongo_client)
        await example_suggest_experiments(agent)
        await example_direct_methods(agent)
    
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user")
        return 0
    
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    print("EXAMPLES COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start API server: python start_server.py")
    print("2. Access endpoints: http://localhost:8000/api/v1/rag/")
    print("3. View docs: http://localhost:8000/docs")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))


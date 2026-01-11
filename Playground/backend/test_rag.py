#!/usr/bin/env python3
"""
RAG System Test Script
Test Voyage AI embeddings, vector search, and RAG agent
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from rag_components import setup_rag_components
from rag_agent import RAGCopilotAgent
from pymongo import MongoClient


async def test_embedder(embedder):
    """Test Voyage AI embedder"""
    print("\n" + "=" * 60)
    print("TEST 1: Voyage AI Embedder")
    print("=" * 60)
    
    try:
        # Test query embedding
        query = "PWR reactor enrichment effects on k-eff"
        embedding = embedder.embed_query(query)
        
        print(f"✅ Query embedded successfully")
        print(f"   Query: {query}")
        print(f"   Embedding dimension: {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")
        
        # Test document embedding
        docs = ["This is document 1", "This is document 2"]
        embeddings = embedder.embed_documents(docs)
        
        print(f"✅ Documents embedded successfully")
        print(f"   Number of documents: {len(docs)}")
        print(f"   Embeddings generated: {len(embeddings)}")
        
        return True
    
    except Exception as e:
        print(f"❌ Embedder test failed: {e}")
        return False


def test_vector_store(vector_store):
    """Test ChromaDB vector store"""
    print("\n" + "=" * 60)
    print("TEST 2: Vector Store")
    print("=" * 60)
    
    try:
        papers_count = vector_store.get_collection_count("papers")
        runs_count = vector_store.get_collection_count("runs")
        
        print(f"✅ Vector store connected")
        print(f"   Papers collection: {papers_count} documents")
        print(f"   Runs collection: {runs_count} documents")
        
        if papers_count == 0:
            print(f"   ⚠️  No papers indexed yet. Run: python setup_rag.py")
        
        if runs_count == 0:
            print(f"   ⚠️  No runs indexed yet. Run: python setup_rag.py")
        
        return True
    
    except Exception as e:
        print(f"❌ Vector store test failed: {e}")
        return False


async def test_rag_agent(agent):
    """Test RAG Copilot Agent"""
    print("\n" + "=" * 60)
    print("TEST 3: RAG Copilot Agent")
    print("=" * 60)
    
    test_queries = [
        {
            "query": "What does the literature say about PWR enrichment?",
            "expected_intent": "literature_search"
        },
        {
            "query": "Find similar runs to PWR at 4.5%",
            "expected_intent": "similar_runs"
        },
        {
            "query": "Suggest follow-up experiments for fusion neutronics",
            "expected_intent": "suggest_experiments"
        }
    ]
    
    all_passed = True
    
    for i, test in enumerate(test_queries, 1):
        print(f"\nTest Query {i}: {test['query']}")
        print("-" * 60)
        
        try:
            result = await agent.invoke(test['query'])
            
            print(f"✅ Query processed")
            print(f"   Intent: {result['intent']}")
            print(f"   Expected: {test['expected_intent']}")
            
            if result['intent'] == test['expected_intent']:
                print(f"   ✅ Intent classification correct")
            else:
                print(f"   ⚠️  Intent mismatch")
                all_passed = False
            
            # Show first 200 chars of result
            result_preview = result['result'][:200]
            print(f"   Result preview: {result_preview}...")
        
        except Exception as e:
            print(f"   ❌ Query failed: {e}")
            all_passed = False
    
    return all_passed


async def test_search_functionality(agent, vector_store):
    """Test search with real data"""
    print("\n" + "=" * 60)
    print("TEST 4: Search Functionality")
    print("=" * 60)
    
    papers_count = vector_store.get_collection_count("papers")
    runs_count = vector_store.get_collection_count("runs")
    
    if papers_count == 0:
        print("⚠️  No papers indexed - skipping literature search test")
        print("   Run 'python setup_rag.py' to index papers")
    else:
        print(f"\nTesting literature search ({papers_count} papers indexed)...")
        try:
            result = agent.search_literature("fusion reactor neutronics", n_results=2)
            if "Paper 1:" in result:
                print("✅ Literature search working")
                print(f"   Result preview: {result[:200]}...")
            else:
                print("⚠️  No results found")
        except Exception as e:
            print(f"❌ Literature search failed: {e}")
    
    if runs_count == 0:
        print("\n⚠️  No runs indexed - skipping similarity search test")
        print("   Run 'python setup_rag.py' to index runs")
    else:
        print(f"\nTesting similarity search ({runs_count} runs indexed)...")
        try:
            result = agent.search_similar_runs(geometry="PWR", n_results=2)
            if "Run 1:" in result:
                print("✅ Similarity search working")
                print(f"   Result preview: {result[:200]}...")
            else:
                print("⚠️  No results found")
        except Exception as e:
            print(f"❌ Similarity search failed: {e}")


async def test_reproducibility(agent, mongo_client):
    """Test reproducibility analysis"""
    print("\n" + "=" * 60)
    print("TEST 5: Reproducibility Analysis")
    print("=" * 60)
    
    # Find a run to test
    runs_collection = mongo_client["aonp"]["runs"]
    sample_run = runs_collection.find_one({})
    
    if not sample_run:
        print("⚠️  No runs in database - skipping reproducibility test")
        return
    
    run_id = sample_run['run_id']
    print(f"Testing with run: {run_id}")
    
    try:
        report = agent.check_reproducibility(run_id)
        
        if "Reproducibility Score:" in report:
            print("✅ Reproducibility analysis working")
            
            # Extract score
            import re
            score_match = re.search(r'Score: (\d+)/100', report)
            if score_match:
                score = score_match.group(1)
                print(f"   Score: {score}/100")
        else:
            print("⚠️  Report format unexpected")
    
    except Exception as e:
        print(f"❌ Reproducibility analysis failed: {e}")


async def main():
    print("=" * 60)
    print("RAG SYSTEM TESTS")
    print("=" * 60)
    
    # Check environment
    voyage_key = os.getenv("VOYAGE_API_KEY")
    mongo_uri = os.getenv("MONGO_URI")
    
    if not voyage_key:
        print("❌ VOYAGE_API_KEY not set")
        return 1
    
    if not mongo_uri:
        print("❌ MONGO_URI not set")
        return 1
    
    print(f"✅ VOYAGE_API_KEY: {voyage_key[:20]}...")
    print(f"✅ MONGO_URI: {mongo_uri}")
    
    # Setup components
    print("\nInitializing RAG components...")
    try:
        embedder, vector_store, pdf_indexer, sim_indexer = setup_rag_components(
            voyage_api_key=voyage_key,
            mongo_uri=mongo_uri,
            chroma_dir="./rag/chroma_db"
        )
        
        mongo_client = MongoClient(mongo_uri)
        
        agent = RAGCopilotAgent(
            embedder=embedder,
            vector_store=vector_store,
            mongo_client=mongo_client
        )
        
        print("✅ All components initialized\n")
    
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return 1
    
    # Run tests
    results = []
    
    results.append(await test_embedder(embedder))
    results.append(test_vector_store(vector_store))
    results.append(await test_rag_agent(agent))
    
    await test_search_functionality(agent, vector_store)
    await test_reproducibility(agent, mongo_client)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


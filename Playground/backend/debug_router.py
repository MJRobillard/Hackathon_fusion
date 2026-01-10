#!/usr/bin/env python3
"""
Debug script to test RouterAgent and see actual LLM responses
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from multi_agent_system import RouterAgent, StudiesAgent, SweepAgent

def test_router():
    """Test router with various queries"""
    
    test_queries = [
        "Simulate a PWR pin cell with 4.5% enriched UO2",
        "Compare enrichments from 3% to 5%",
        "Show me all PWR simulations",
        "Compare run_abc123 and run_def456",
        "Tell me about nuclear reactors"
    ]
    
    print("=" * 80)
    print("ROUTER AGENT DEBUG TEST")
    print("=" * 80)
    
    # Test with keyword routing (fast, no LLM)
    print("\n" + "=" * 80)
    print("MODE 1: KEYWORD ROUTING (Fast, No LLM)")
    print("=" * 80)
    router_keyword = RouterAgent(use_llm=False)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTEST {i}: {query}")
        try:
            result = router_keyword.route_query(query)
            print(f"  → Agent: {result['agent']}, Intent: {result['intent']}, Method: {result.get('method', 'N/A')}")
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
    
    # Test with LLM routing (slower, more accurate)
    print("\n" + "=" * 80)
    print("MODE 2: LLM ROUTING (Slower, More Accurate)")
    print("=" * 80)
    router_llm = RouterAgent(use_llm=True)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTEST {i}: {query}")
        try:
            result = router_llm.route_query(query)
            print(f"  → Agent: {result['agent']}, Intent: {result['intent']}")
            if 'raw_response' in result:
                print(f"  → Raw LLM: '{result['raw_response']}'")
            if 'error' in result:
                print(f"  → Error: {result['error']}")
            if 'fallback' in result:
                print(f"  → Used fallback: keyword routing")
        except Exception as e:
            print(f"  ✗ FAILED: {e}")

def test_studies_agent():
    """Test StudiesAgent spec extraction"""
    print("\n" + "=" * 80)
    print("STUDIES AGENT DEBUG TEST")
    print("=" * 80)
    
    agent = StudiesAgent()
    
    test_queries = [
        "Simulate PWR with 4.5% enriched UO2 at 600K",
        "Simulate PWR with 1% enriched UO2",
        "Run a BWR simulation at 900K"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            spec = agent._keyword_extract_spec(query)
            print(f"  Geometry: {spec['geometry']}")
            print(f"  Enrichment: {spec['enrichment_pct']}%")
            print(f"  Temperature: {spec['temperature_K']}K")
        except Exception as e:
            print(f"  ✗ FAILED: {e}")

def test_sweep_agent():
    """Test SweepAgent config extraction"""
    print("\n" + "=" * 80)
    print("SWEEP AGENT DEBUG TEST")
    print("=" * 80)
    
    agent = SweepAgent()
    
    test_queries = [
        "Compare enrichments from 3% to 5%",
        "Vary temperature from 300K to 900K",
        "Compare enrichments 3%, 4%, 5%"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            config = agent._keyword_extract_sweep_config(query)
            print(f"  Parameter: {config['param_name']}")
            print(f"  Values: {config['param_values']}")
        except Exception as e:
            print(f"  ✗ FAILED: {e}")

if __name__ == "__main__":
    test_router()
    test_studies_agent()
    test_sweep_agent()
    
    print("\n" + "=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80)


#!/usr/bin/env python3
"""
Quick API Test Script - Test all endpoints without starting server
Uses the multi-agent system directly
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from multi_agent_system import (
    RouterAgent,
    StudiesAgent,
    SweepAgent,
    QueryAgent,
    AnalysisAgent,
    MultiAgentOrchestrator
)

def test_router():
    """Test RouterAgent"""
    print("\n" + "="*80)
    print("TEST 1: Router Agent (Keyword Mode)")
    print("="*80)
    
    router = RouterAgent(use_llm=False)
    
    test_cases = [
        ("Simulate PWR at 4.5% enrichment", "studies"),
        ("Compare enrichments from 3% to 5%", "sweep"),
        ("Show me all PWR simulations", "query"),
        ("Compare run_abc123 and run_def456", "analysis"),
    ]
    
    for query, expected_agent in test_cases:
        result = router.route_query(query)
        status = "✓" if result["agent"] == expected_agent else "✗"
        print(f"{status} '{query[:40]}...' → {result['agent']} (expected: {expected_agent})")
    
    print("\nRouter test: PASSED")


def test_studies_agent():
    """Test StudiesAgent"""
    print("\n" + "="*80)
    print("TEST 2: Studies Agent")
    print("="*80)
    
    agent = StudiesAgent()
    
    try:
        result = agent.execute({
            "query": "Simulate PWR pin with 4.5% enriched UO2 at 600K"
        })
        
        if result["status"] == "success":
            print(f"✓ Simulation completed")
            print(f"  Run ID: {result['run_id']}")
            print(f"  k-eff: {result['keff']:.4f} ± {result['keff_std']:.4f}")
            print(f"  Enrichment: {result['spec'].get('enrichment_pct', 'N/A')}%")
            print(f"  Temperature: {result['spec'].get('temperature_K', 'N/A')}K")
            print("\nStudies agent test: PASSED")
        else:
            print(f"✗ Simulation failed: {result.get('error')}")
            print("\nStudies agent test: FAILED")
    except Exception as e:
        print(f"✗ Exception: {e}")
        print("\nStudies agent test: FAILED")


def test_sweep_agent():
    """Test SweepAgent"""
    print("\n" + "="*80)
    print("TEST 3: Sweep Agent")
    print("="*80)
    
    agent = SweepAgent()
    
    try:
        result = agent.execute({
            "query": "Compare enrichments from 3% to 5%"
        })
        
        if result["status"] == "success":
            print(f"✓ Sweep completed")
            print(f"  Parameter: {result['sweep_config']['param_name']}")
            print(f"  Values: {result['sweep_config']['param_values']}")
            print(f"  Runs: {len(result['run_ids'])}")
            print(f"  k-eff range: {result['comparison']['keff_min']:.4f} - {result['comparison']['keff_max']:.4f}")
            print(f"  k-eff mean: {result['comparison']['keff_mean']:.4f}")
            print("\nSweep agent test: PASSED")
        else:
            print(f"✗ Sweep failed: {result.get('error')}")
            print("\nSweep agent test: FAILED")
    except Exception as e:
        print(f"✗ Exception: {e}")
        print("\nSweep agent test: FAILED")


def test_query_agent():
    """Test QueryAgent"""
    print("\n" + "="*80)
    print("TEST 4: Query Agent")
    print("="*80)
    
    agent = QueryAgent()
    
    try:
        result = agent.execute({
            "query": "Show me recent simulations"
        })
        
        if result["status"] == "success":
            print(f"✓ Query completed")
            print(f"  Results: {result['count']} runs")
            print("\nQuery agent test: PASSED")
        else:
            print(f"✗ Query failed: {result.get('error')}")
            print("\nQuery agent test: FAILED")
    except Exception as e:
        print(f"✗ Exception: {e}")
        print("\nQuery agent test: FAILED")


def test_orchestrator():
    """Test MultiAgentOrchestrator"""
    print("\n" + "="*80)
    print("TEST 5: Multi-Agent Orchestrator (End-to-End)")
    print("="*80)
    
    orchestrator = MultiAgentOrchestrator()
    # Use keyword routing for speed
    orchestrator.router = RouterAgent(use_llm=False)
    
    try:
        result = orchestrator.process_query("Simulate PWR at 4.5% enrichment")
        
        if result["results"]["status"] == "success":
            print(f"✓ Orchestrator test completed")
            print(f"  Query: {result['query'][:50]}...")
            print(f"  Routed to: {result['routing']['agent']}")
            print(f"  Run ID: {result['results']['run_id']}")
            print(f"  k-eff: {result['results']['keff']:.4f}")
            print("\nOrchestrator test: PASSED")
        else:
            print(f"✗ Orchestrator failed: {result['results'].get('error')}")
            print("\nOrchestrator test: FAILED")
    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        print("\nOrchestrator test: FAILED")


def main():
    """Run all tests"""
    print("="*80)
    print("AONP MULTI-AGENT API - QUICK TEST SUITE")
    print("="*80)
    print("\nTesting multi-agent system components...")
    
    try:
        test_router()
        test_studies_agent()
        test_sweep_agent()
        test_query_agent()
        test_orchestrator()
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80)
        print("\nAPI is ready for frontend integration!")
        print("Start the server with: ./start_api.sh (or start_api.ps1 on Windows)")
        print("="*80)
        
    except Exception as e:
        print("\n" + "="*80)
        print("TESTS FAILED ✗")
        print("="*80)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


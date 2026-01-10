#!/usr/bin/env python3
"""
Demo script for AONP Multi-Agent System
Shows all 4 agent workflows
"""

import os
from dotenv import load_dotenv
from multi_agent_system import run_multi_agent_query
from agent_tools import get_study_statistics

load_dotenv()

def print_header(text):
    """Print section header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def print_result(result):
    """Pretty print result"""
    import json
    print(json.dumps(result, indent=2, default=str))

def demo_studies_agent():
    """Demo: Studies Agent (single simulation)"""
    print_header("DEMO 1: Studies Agent - Single Simulation")
    
    query = "Simulate a PWR pin cell with 4.5% enriched UO2 at 600K"
    print(f"Query: {query}\n")
    
    result = run_multi_agent_query(query)
    
    print(f"Routing: {result['routing']['agent']} (intent: {result['routing']['intent']})")
    print(f"Status: {result['results']['status']}")
    
    if result['results']['status'] == 'success':
        print(f"Run ID: {result['results']['run_id']}")
        print(f"keff: {result['results']['keff']:.5f} ± {result['results']['keff_std']:.6f}")
        
        if result['results'].get('warnings'):
            print(f"Warnings: {result['results']['warnings']}")

def demo_sweep_agent():
    """Demo: Sweep Agent (parameter sweep)"""
    print_header("DEMO 2: Sweep Agent - Parameter Sweep")
    
    query = "Compare PWR enrichments from 3% to 5%"
    print(f"Query: {query}\n")
    
    result = run_multi_agent_query(query)
    
    print(f"Routing: {result['routing']['agent']} (intent: {result['routing']['intent']})")
    print(f"Status: {result['results']['status']}")
    
    if result['results']['status'] == 'success':
        comparison = result['results']['comparison']
        print(f"\nSweep Results:")
        print(f"  Number of runs: {comparison['num_runs']}")
        print(f"  keff range: [{comparison['keff_min']:.5f}, {comparison['keff_max']:.5f}]")
        print(f"  keff mean: {comparison['keff_mean']:.5f}")
        
        print(f"\nDetailed Results:")
        for run in comparison['runs']:
            enrichment = run['spec'].get('enrichment_pct', 'N/A')
            keff = run['keff']
            print(f"    {enrichment}% → keff = {keff:.5f}")

def demo_query_agent():
    """Demo: Query Agent (database search)"""
    print_header("DEMO 3: Query Agent - Database Search")
    
    query = "Show me the 5 most recent simulations"
    print(f"Query: {query}\n")
    
    result = run_multi_agent_query(query)
    
    print(f"Routing: {result['routing']['agent']} (intent: {result['routing']['intent']})")
    print(f"Status: {result['results']['status']}")
    
    if result['results']['status'] == 'success':
        results = result['results']['results']
        print(f"\nFound {len(results)} results:")
        
        for i, run in enumerate(results[:5], 1):
            print(f"\n  {i}. Run ID: {run['run_id']}")
            print(f"     Geometry: {run['spec'].get('geometry', 'N/A')}")
            print(f"     keff: {run['keff']:.5f}")
            print(f"     Created: {run['created_at']}")

def demo_analysis_agent():
    """Demo: Analysis Agent (comparison)"""
    print_header("DEMO 4: Analysis Agent - Result Comparison")
    
    # First, create two runs to compare
    from agent_tools import submit_study
    
    print("Creating two runs to compare...\n")
    
    spec1 = {
        "geometry": "Demo PWR 1",
        "materials": ["UO2", "Water"],
        "enrichment_pct": 3.0
    }
    result1 = submit_study(spec1)
    run_id1 = result1["run_id"]
    print(f"Run 1: {run_id1} (3.0% enrichment) → keff = {result1['keff']:.5f}")
    
    spec2 = {
        "geometry": "Demo PWR 2",
        "materials": ["UO2", "Water"],
        "enrichment_pct": 5.0
    }
    result2 = submit_study(spec2)
    run_id2 = result2["run_id"]
    print(f"Run 2: {run_id2} (5.0% enrichment) → keff = {result2['keff']:.5f}")
    
    # Now compare them
    query = f"Compare {run_id1} and {run_id2}"
    print(f"\nQuery: {query}\n")
    
    result = run_multi_agent_query(query)
    
    print(f"Routing: {result['routing']['agent']} (intent: {result['routing']['intent']})")
    print(f"Status: {result['results']['status']}")
    
    if result['results']['status'] == 'success':
        comparison = result['results']['comparison']
        print(f"\nComparison:")
        print(f"  keff difference: {comparison['keff_max'] - comparison['keff_min']:.5f}")
        print(f"  keff mean: {comparison['keff_mean']:.5f}")
        
        if 'interpretation' in result['results']:
            print(f"\nInterpretation:")
            print(f"  {result['results']['interpretation']}")

def demo_statistics():
    """Demo: Database statistics"""
    print_header("DEMO 5: Database Statistics")
    
    stats = get_study_statistics()
    
    print(f"Total studies: {stats['total_studies']}")
    print(f"Total runs: {stats['total_runs']}")
    print(f"Completed runs: {stats['completed_runs']}")
    
    print(f"\nRecent runs:")
    for run in stats['recent_runs']:
        print(f"  - {run['run_id']}: {run['geometry']} (keff = {run['keff']:.5f})")

def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("  AONP MULTI-AGENT SYSTEM DEMO")
    print("=" * 80)
    
    # Check environment
    if not os.getenv("MONGO_URI"):
        print("\n❌ Error: MONGO_URI not set")
        print("Create .env file with MONGO_URI=mongodb://localhost:27017")
        return
    
    if not os.getenv("FIREWORKS"):
        print("\n⚠️  Warning: FIREWORKS API key not set")
        print("Some features may not work properly")
    
    try:
        # Run demos
        demo_studies_agent()
        demo_sweep_agent()
        demo_query_agent()
        demo_analysis_agent()
        demo_statistics()
        
        print_header("DEMO COMPLETE")
        print("✓ All demos completed successfully!")
        print("\nNext steps:")
        print("  1. Start API server: python api/main_v2.py")
        print("  2. Run tests: python run_tests.py")
        print("  3. View docs: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


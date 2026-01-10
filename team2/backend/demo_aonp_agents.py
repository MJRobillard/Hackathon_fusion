"""
Quick Demo of AONP Multi-Agent System
Run this for a fast demonstration of capabilities
"""

from aonp_agents import run_aonp_agent
from agent_tools import get_study_statistics
import time


def demo():
    """Quick demo of key features"""
    print("=" * 80)
    print("AONP MULTI-AGENT SYSTEM - QUICK DEMO")
    print("=" * 80)
    print("\nThis demo shows the AI agents handling different types of requests.\n")
    time.sleep(1)
    
    # Demo 1: Single study
    print("\n" + "─" * 80)
    print("DEMO 1: Single Study Request")
    print("─" * 80)
    print("\nUser: 'Simulate a PWR pin cell with 4.5% enriched UO2 at 600K'\n")
    time.sleep(1)
    
    state1 = run_aonp_agent("Simulate a PWR pin cell with 4.5% enriched UO2 at 600K")
    
    input("\n\nPress Enter to continue to Demo 2...")
    
    # Demo 2: Parameter sweep
    print("\n" + "─" * 80)
    print("DEMO 2: Parameter Sweep")
    print("─" * 80)
    print("\nUser: 'Run an enrichment sweep from 3% to 5% for a PWR at 600K'\n")
    time.sleep(1)
    
    state2 = run_aonp_agent("Run an enrichment sweep from 3% to 5% for a PWR at 600K")
    
    input("\n\nPress Enter to continue to Demo 3...")
    
    # Demo 3: Query
    print("\n" + "─" * 80)
    print("DEMO 3: Query Past Results")
    print("─" * 80)
    print("\nUser: 'Show me all PWR simulations'\n")
    time.sleep(1)
    
    state3 = run_aonp_agent("Show me all PWR simulations")
    
    # Final stats
    print("\n\n" + "=" * 80)
    print("DATABASE SUMMARY")
    print("=" * 80)
    
    stats = get_study_statistics()
    print(f"\nTotal unique studies: {stats['total_studies']}")
    print(f"Total runs executed: {stats['total_runs']}")
    print(f"Total results stored: {stats['total_summaries']}")
    
    print("\n\nRecent simulations:")
    for i, run in enumerate(stats['recent_runs'][:5], 1):
        print(f"  {i}. {run['geometry']}: keff = {run['keff']:.5f}")
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nKey Features Demonstrated:")
    print("  ✓ Natural language understanding")
    print("  ✓ Automatic intent classification")
    print("  ✓ Study specification extraction")
    print("  ✓ Parameter sweep generation")
    print("  ✓ Database queries")
    print("  ✓ Results analysis")
    print("  ✓ Experiment suggestions")
    print("\nThe system is ready for the hackathon!")


if __name__ == "__main__":
    demo()


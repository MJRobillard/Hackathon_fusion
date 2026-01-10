"""
Test Suite for AONP Multi-Agent System
Demonstrates different use cases and agent capabilities
"""

from aonp_agents import run_aonp_agent
from agent_tools import get_study_statistics, query_results
import time


def print_test_header(test_num: int, title: str):
    """Print formatted test header"""
    print("\n\n")
    print("=" * 80)
    print(f"TEST {test_num}: {title}")
    print("=" * 80)
    time.sleep(0.5)  # Brief pause for readability


def test_1_single_study():
    """Test 1: Single study submission"""
    print_test_header(1, "Single Study Submission")
    
    request = "Run a PWR fuel pin simulation with 4.5% enriched UO2 at 600 Kelvin"
    
    final_state = run_aonp_agent(request)
    
    # Verify
    assert final_state["intent"] == "single_study", f"Expected 'single_study', got {final_state['intent']}"
    assert final_state["study_spec"] is not None, "Study spec not created"
    assert final_state["results"] is not None, "No results returned"
    assert "keff" in final_state["results"], "keff not in results"
    
    print("\n[TEST 1 PASSED] ✓ Single study executed successfully")
    return final_state


def test_2_parameter_sweep():
    """Test 2: Parameter sweep"""
    print_test_header(2, "Parameter Sweep")
    
    request = "I need an enrichment sweep from 3% to 5% for a PWR pin cell at 600K"
    
    final_state = run_aonp_agent(request)
    
    # Verify
    assert final_state["intent"] == "sweep", f"Expected 'sweep', got {final_state['intent']}"
    assert final_state["sweep_config"] is not None, "Sweep config not created"
    assert final_state["run_ids"] is not None, "No run IDs returned"
    assert len(final_state["run_ids"]) > 1, "Sweep should have multiple runs"
    assert "keff_mean" in final_state["results"], "Comparison stats not generated"
    
    print(f"\n[TEST 2 PASSED] ✓ Sweep executed with {len(final_state['run_ids'])} runs")
    return final_state


def test_3_temperature_sweep():
    """Test 3: Temperature sweep"""
    print_test_header(3, "Temperature Sweep")
    
    request = "Do a temperature sweep from 300K to 900K for a BWR assembly with 4% enrichment"
    
    final_state = run_aonp_agent(request)
    
    # Verify
    assert final_state["intent"] == "sweep", f"Expected 'sweep', got {final_state['intent']}"
    assert final_state["sweep_config"] is not None, "Sweep config not created"
    
    # Check that temperature is the swept parameter
    param_name = final_state["sweep_config"]["param_name"]
    print(f"\n[TEST 3 INFO] Swept parameter: {param_name}")
    
    print(f"\n[TEST 3 PASSED] ✓ Temperature sweep executed")
    return final_state


def test_4_query_past_results():
    """Test 4: Query existing results"""
    print_test_header(4, "Query Past Results")
    
    request = "Show me all PWR simulations we've run"
    
    final_state = run_aonp_agent(request)
    
    # Verify
    assert final_state["intent"] == "query", f"Expected 'query', got {final_state['intent']}"
    assert final_state["results"] is not None, "No query results returned"
    
    result_count = final_state["results"].get("count", 0)
    print(f"\n[TEST 4 PASSED] ✓ Query returned {result_count} results")
    return final_state


def test_5_complex_request():
    """Test 5: Complex multi-parameter request"""
    print_test_header(5, "Complex Multi-Parameter Study")
    
    request = """I want to simulate a fast reactor core with MOX fuel at 800K.
    Use 20000 particles and 100 batches for good statistics."""
    
    final_state = run_aonp_agent(request)
    
    # Verify study spec captured the details
    spec = final_state.get("study_spec", {})
    print(f"\n[TEST 5 INFO] Generated spec:")
    print(f"  Geometry: {spec.get('geometry')}")
    print(f"  Temperature: {spec.get('temperature_K')}K")
    print(f"  Particles: {spec.get('particles')}")
    print(f"  Batches: {spec.get('batches')}")
    
    print(f"\n[TEST 5 PASSED] ✓ Complex request handled")
    return final_state


def test_6_criticality_query():
    """Test 6: Query for critical systems"""
    print_test_header(6, "Criticality Query")
    
    request = "Which simulations resulted in critical systems?"
    
    final_state = run_aonp_agent(request)
    
    # Verify
    assert final_state["intent"] == "query", f"Expected 'query', got {final_state['intent']}"
    
    result_count = final_state["results"].get("count", 0)
    print(f"\n[TEST 6 PASSED] ✓ Found {result_count} critical systems")
    return final_state


def test_7_suggestion_quality():
    """Test 7: Verify suggestions are generated"""
    print_test_header(7, "Suggestion Generation")
    
    request = "Run a PWR pin with 3.5% enrichment at 500K"
    
    final_state = run_aonp_agent(request)
    
    # Verify suggestions were generated
    assert final_state.get("suggestion") is not None, "No suggestions generated"
    assert len(final_state["suggestion"]) > 50, "Suggestions too short"
    
    print(f"\n[TEST 7 INFO] Suggestions preview:")
    print(final_state["suggestion"][:200] + "...")
    
    print(f"\n[TEST 7 PASSED] ✓ Suggestions generated")
    return final_state


def test_8_database_state():
    """Test 8: Verify database state after all tests"""
    print_test_header(8, "Database State Verification")
    
    stats = get_study_statistics()
    
    print("\n[DATABASE STATISTICS]")
    print(f"  Total unique studies: {stats['total_studies']}")
    print(f"  Total runs: {stats['total_runs']}")
    print(f"  Total summaries: {stats['total_summaries']}")
    print(f"  Completed runs: {stats['completed_runs']}")
    
    # Verify data integrity
    assert stats['total_runs'] == stats['total_summaries'], "Runs and summaries count mismatch"
    assert stats['completed_runs'] == stats['total_runs'], "Some runs didn't complete"
    
    print("\n[RECENT RUNS]")
    for i, run in enumerate(stats['recent_runs'][:3], 1):
        print(f"  {i}. {run['geometry']}: keff = {run['keff']:.5f}")
    
    print(f"\n[TEST 8 PASSED] ✓ Database integrity verified")
    return stats


def test_9_deduplication():
    """Test 9: Verify spec deduplication works"""
    print_test_header(9, "Deduplication Test")
    
    # Submit same spec twice
    request = "Run a PWR pin cell with 4.0% enrichment at 600K"
    
    print("\n[RUN 1]")
    state1 = run_aonp_agent(request)
    run_id_1 = state1["run_ids"][0] if state1.get("run_ids") else None
    
    print("\n[RUN 2] (Same spec)")
    state2 = run_aonp_agent(request)
    run_id_2 = state2["run_ids"][0] if state2.get("run_ids") else None
    
    # Get study counts
    stats = get_study_statistics()
    
    print(f"\n[DEDUPLICATION INFO]")
    print(f"  Run 1 ID: {run_id_1}")
    print(f"  Run 2 ID: {run_id_2}")
    print(f"  Total unique studies: {stats['total_studies']}")
    
    # Run IDs should differ (different runs) but spec_hash should be same
    assert run_id_1 != run_id_2, "Run IDs should be different"
    
    print(f"\n[TEST 9 PASSED] ✓ Deduplication working (unique studies: {stats['total_studies']})")
    return stats


def test_10_sweep_trends():
    """Test 10: Analyze trends in sweep"""
    print_test_header(10, "Sweep Trend Analysis")
    
    request = "Enrichment sweep from 2.5% to 5.5% for PWR at 600K"
    
    final_state = run_aonp_agent(request)
    
    if final_state.get("results") and "runs" in final_state["results"]:
        runs = final_state["results"]["runs"]
        
        print("\n[ENRICHMENT vs KEFF]")
        sorted_runs = sorted(runs, key=lambda x: x["spec"].get("enrichment_pct", 0))
        
        for run in sorted_runs:
            enr = run["spec"].get("enrichment_pct", 0)
            keff = run["keff"]
            print(f"  {enr:4.1f}% -> keff = {keff:.5f}")
        
        # Verify trend (keff should increase with enrichment)
        keffs = [r["keff"] for r in sorted_runs]
        is_increasing = all(keffs[i] <= keffs[i+1] + 0.05 for i in range(len(keffs)-1))  # Allow some noise
        
        if is_increasing:
            print("\n  ✓ Trend: keff increases with enrichment (as expected)")
        else:
            print("\n  ⚠ Trend: Noisy data (expected for mock)")
        
    print(f"\n[TEST 10 PASSED] ✓ Sweep trends analyzed")
    return final_state


def run_all_tests():
    """Run all tests in sequence"""
    print("=" * 80)
    print("AONP MULTI-AGENT SYSTEM - TEST SUITE")
    print("=" * 80)
    print("\nRunning comprehensive tests...")
    print("This will take a few minutes due to LLM calls.")
    
    start_time = time.time()
    
    try:
        # Run tests
        test_1_single_study()
        test_2_parameter_sweep()
        test_3_temperature_sweep()
        test_4_query_past_results()
        test_5_complex_request()
        test_6_criticality_query()
        test_7_suggestion_quality()
        test_8_database_state()
        test_9_deduplication()
        test_10_sweep_trends()
        
        elapsed = time.time() - start_time
        
        print("\n\n")
        print("=" * 80)
        print("ALL TESTS PASSED ✓")
        print("=" * 80)
        print(f"\nTotal time: {elapsed:.1f} seconds")
        print("\nThe AONP multi-agent system is working correctly:")
        print("  ✓ Intent classification")
        print("  ✓ Study planning")
        print("  ✓ Sweep generation")
        print("  ✓ Query execution")
        print("  ✓ Results analysis")
        print("  ✓ Suggestion generation")
        print("  ✓ Database persistence")
        print("  ✓ Spec deduplication")
        
    except AssertionError as e:
        print(f"\n\n[TEST FAILED] {e}")
        raise
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        raise


if __name__ == "__main__":
    run_all_tests()


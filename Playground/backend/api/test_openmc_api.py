#!/usr/bin/env python3
"""
Test script for OpenMC Backend API

Tests all major endpoints with sample data.
"""

import requests
import time
import json
from typing import Dict, Any

# API configuration
BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api/v1"


def print_section(title: str):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_response(response: requests.Response):
    """Pretty print response"""
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, default=str))
    except:
        print(response.text)


def test_health():
    """Test health endpoint"""
    print_section("Health Check")
    response = requests.get(f"{API_BASE}/health")
    print_response(response)
    return response.status_code == 200


def test_root():
    """Test root endpoint"""
    print_section("Root Endpoint")
    response = requests.get(BASE_URL)
    print_response(response)
    return response.status_code == 200


def test_submit_simulation() -> str:
    """Test simulation submission"""
    print_section("Submit Simulation")
    
    spec = {
        "spec": {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "enrichment_pct": 4.5,
            "temperature_K": 900.0,
            "particles": 1000,
            "batches": 20
        },
        "priority": "normal",
        "metadata": {
            "test": "api_test",
            "description": "Test simulation"
        }
    }
    
    response = requests.post(f"{API_BASE}/simulations", json=spec)
    print_response(response)
    
    if response.status_code == 202:
        data = response.json()
        return data["run_id"]
    return None


def test_get_simulation(run_id: str):
    """Test getting simulation status"""
    print_section(f"Get Simulation: {run_id}")
    
    # Poll for completion (up to 60 seconds)
    max_attempts = 12
    for attempt in range(max_attempts):
        response = requests.get(f"{API_BASE}/simulations/{run_id}")
        print_response(response)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            
            if status in ["completed", "failed"]:
                print(f"\n✅ Simulation {status}")
                return True
            
            print(f"\n⏳ Status: {status}, waiting... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(5)
    
    print("\n⚠️  Simulation did not complete in time")
    return False


def test_submit_sweep() -> str:
    """Test parameter sweep submission"""
    print_section("Submit Parameter Sweep")
    
    sweep_request = {
        "base_spec": {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "enrichment_pct": 4.5,
            "temperature_K": 900.0,
            "particles": 500,
            "batches": 10
        },
        "parameter": "enrichment_pct",
        "values": [3.0, 3.5, 4.0, 4.5, 5.0]
    }
    
    response = requests.post(f"{API_BASE}/sweeps", json=sweep_request)
    print_response(response)
    
    if response.status_code == 202:
        data = response.json()
        return data["sweep_id"]
    return None


def test_get_sweep(sweep_id: str):
    """Test getting sweep status"""
    print_section(f"Get Sweep: {sweep_id}")
    response = requests.get(f"{API_BASE}/sweeps/{sweep_id}")
    print_response(response)
    return response.status_code == 200


def test_query_runs():
    """Test querying runs"""
    print_section("Query Runs")
    
    # Query with filters
    params = {
        "geometry": "PWR",
        "enrichment_min": 3.0,
        "enrichment_max": 5.0,
        "limit": 10
    }
    
    response = requests.get(f"{API_BASE}/runs", params=params)
    print_response(response)
    return response.status_code == 200


def test_compare_runs(run_ids: list):
    """Test comparing runs"""
    print_section("Compare Runs")
    
    if len(run_ids) < 2:
        print("⚠️  Need at least 2 runs to compare")
        return False
    
    compare_request = {
        "run_ids": run_ids[:5]  # Compare up to 5 runs
    }
    
    response = requests.post(f"{API_BASE}/runs/compare", json=compare_request)
    print_response(response)
    return response.status_code == 200


def test_list_files(run_id: str):
    """Test listing run files"""
    print_section(f"List Files: {run_id}")
    response = requests.get(f"{API_BASE}/simulations/{run_id}/files")
    print_response(response)
    return response.status_code == 200


def test_statistics():
    """Test statistics endpoint"""
    print_section("Statistics")
    response = requests.get(f"{API_BASE}/statistics")
    print_response(response)
    return response.status_code == 200


def main():
    """Run all tests"""
    print("=" * 80)
    print("OPENMC BACKEND API TEST SUITE")
    print("=" * 80)
    print(f"Testing API at: {BASE_URL}")
    
    results = {}
    run_ids = []
    
    # Test 1: Health check
    results["health"] = test_health()
    
    # Test 2: Root endpoint
    results["root"] = test_root()
    
    # Test 3: Submit simulation
    run_id = test_submit_simulation()
    if run_id:
        run_ids.append(run_id)
        results["submit_simulation"] = True
        
        # Test 4: Get simulation status
        results["get_simulation"] = test_get_simulation(run_id)
        
        # Test 5: List files
        results["list_files"] = test_list_files(run_id)
    else:
        results["submit_simulation"] = False
    
    # Test 6: Submit sweep
    sweep_id = test_submit_sweep()
    if sweep_id:
        results["submit_sweep"] = True
        
        # Wait a bit for sweep to start
        time.sleep(5)
        
        # Test 7: Get sweep status
        results["get_sweep"] = test_get_sweep(sweep_id)
    else:
        results["submit_sweep"] = False
    
    # Test 8: Query runs
    results["query_runs"] = test_query_runs()
    
    # Test 9: Compare runs (if we have enough)
    if len(run_ids) >= 1:
        # Submit another quick run for comparison
        run_id2 = test_submit_simulation()
        if run_id2:
            run_ids.append(run_id2)
            time.sleep(10)  # Wait for completion
            results["compare_runs"] = test_compare_runs(run_ids)
    
    # Test 10: Statistics
    results["statistics"] = test_statistics()
    
    # Summary
    print_section("Test Summary")
    passed = sum(results.values())
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {test}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


#!/usr/bin/env python3
"""
Test all API endpoints - run this AFTER starting the server
Usage: python test_endpoints.py
"""

import requests
import json
import time
from typing import Dict, Any

API_URL = "http://localhost:8000"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

passed = 0
failed = 0

def print_header(text):
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{text.center(80)}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")

def test_endpoint(name: str, method: str, endpoint: str, data: Dict = None) -> bool:
    """Test a single endpoint"""
    global passed, failed
    
    url = f"{API_URL}{endpoint}"
    print(f"Testing {name}... ", end="", flush=True)
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            print(f"{RED}✗ FAILED{RESET} - Unknown method")
            failed += 1
            return False
        
        if response.status_code in [200, 202]:
            print(f"{GREEN}✓ PASSED{RESET} (HTTP {response.status_code})")
            passed += 1
            return True
        else:
            print(f"{RED}✗ FAILED{RESET} (HTTP {response.status_code})")
            print(f"  Response: {response.text[:100]}")
            failed += 1
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"{RED}✗ FAILED{RESET} - Cannot connect to server")
        print(f"{YELLOW}  Make sure server is running: python start_server.py{RESET}")
        failed += 1
        return False
    except Exception as e:
        print(f"{RED}✗ FAILED{RESET} - {str(e)}")
        failed += 1
        return False

def main():
    global passed, failed
    
    print_header("AONP API Endpoint Tests")
    print("Testing API at:", API_URL)
    print("Make sure the server is running!")
    print("")
    
    # Test 1: Health & Status
    print_header("Test Suite 1: Health & Status")
    test_endpoint("Health Check", "GET", "/api/v1/health")
    test_endpoint("Statistics", "GET", "/api/v1/statistics")
    
    # Test 2: Router
    print_header("Test Suite 2: Router")
    test_endpoint(
        "Router Test (Keyword Mode)",
        "POST",
        "/api/v1/router",
        {"query": "Simulate PWR at 4.5% enrichment", "use_llm": False}
    )
    
    # Test 3: Natural Language Query
    print_header("Test Suite 3: Natural Language Query")
    
    print("Submitting query... ", end="", flush=True)
    try:
        response = requests.post(
            f"{API_URL}/api/v1/query",
            json={"query": "Simulate PWR at 4.5% enrichment", "use_llm": False},
            timeout=10
        )
        
        if response.status_code == 202:
            data = response.json()
            query_id = data.get("query_id")
            print(f"{GREEN}✓ PASSED{RESET}")
            print(f"  Query ID: {query_id}")
            passed += 1
            
            # Wait for completion
            print("  Waiting for completion... ", end="", flush=True)
            time.sleep(3)
            
            # Check status
            status_response = requests.get(
                f"{API_URL}/api/v1/query/{query_id}",
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get("status")
                print(f"{GREEN}✓ Status: {status}{RESET}")
                passed += 1
                
                if status == "completed":
                    results = status_data.get("results", {})
                    if "keff" in results:
                        print(f"  k-eff: {results['keff']}")
                        print(f"  Run ID: {results.get('run_id')}")
            else:
                print(f"{RED}✗ FAILED{RESET}")
                failed += 1
        else:
            print(f"{RED}✗ FAILED{RESET}")
            failed += 1
            
    except Exception as e:
        print(f"{RED}✗ FAILED{RESET} - {str(e)}")
        failed += 1
    
    # Test 4: Agent Endpoints
    print_header("Test Suite 4: Agent Endpoints")
    test_endpoint(
        "Studies Agent",
        "POST",
        "/api/v1/agents/studies",
        {"query": "Simulate PWR at 4.5% enrichment"}
    )
    test_endpoint(
        "Sweep Agent",
        "POST",
        "/api/v1/agents/sweep",
        {"query": "Compare enrichments 3%, 4%, 5%"}
    )
    test_endpoint(
        "Query Agent",
        "POST",
        "/api/v1/agents/query",
        {"query": "Show me recent simulations"}
    )
    
    # Test 5: Direct Tool Access
    print_header("Test Suite 5: Direct Tool Access")
    
    print("Submit Direct Study... ", end="", flush=True)
    try:
        response = requests.post(
            f"{API_URL}/api/v1/studies",
            json={
                "geometry": "PWR pin cell",
                "materials": ["UO2", "Zircaloy", "Water"],
                "enrichment_pct": 4.5,
                "temperature_K": 600,
                "particles": 10000,
                "batches": 50
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            run_id = data.get("run_id")
            print(f"{GREEN}✓ PASSED{RESET}")
            print(f"  Run ID: {run_id}")
            print(f"  k-eff: {data.get('keff')}")
            passed += 1
            
            # Test get study by ID
            test_endpoint(
                "Get Study by ID",
                "GET",
                f"/api/v1/studies/{run_id}"
            )
        else:
            print(f"{RED}✗ FAILED{RESET}")
            failed += 1
            
    except Exception as e:
        print(f"{RED}✗ FAILED{RESET} - {str(e)}")
        failed += 1
    
    # Test 6: Query Runs
    print_header("Test Suite 6: Query Runs")
    test_endpoint("Query All Runs", "GET", "/api/v1/runs?limit=5")
    test_endpoint("Query PWR Runs", "GET", "/api/v1/runs?geometry=PWR&limit=5")
    
    # Summary
    print_header("Test Summary")
    print(f"Total: {passed + failed}")
    print(f"{GREEN}Passed: {passed}{RESET}")
    print(f"{RED}Failed: {failed}{RESET}")
    print("")
    
    if failed == 0:
        print(f"{GREEN}✓ ALL TESTS PASSED!{RESET}")
        print("=" * 80)
        print("\n🎉 Your API is working perfectly!")
        print("📚 Check out the docs: http://localhost:8000/docs")
        print("🚀 Ready for frontend integration!\n")
        return 0
    else:
        print(f"{RED}✗ SOME TESTS FAILED{RESET}")
        print("=" * 80)
        print("\n⚠️  Check the errors above")
        print("💡 Make sure MongoDB is running and accessible\n")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())


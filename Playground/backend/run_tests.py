#!/usr/bin/env python3
"""
Test runner for AONP Multi-Agent System
Runs all tests with proper configuration
"""

import sys
import os
import subprocess
from pathlib import Path

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_header(text):
    """Print colored header"""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{text.center(80)}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    """Print error message"""
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠ {text}{RESET}")

def check_dependencies():
    """Check if required dependencies are installed"""
    print_header("Checking Dependencies")
    
    required = ["pytest", "pymongo", "fastapi", "langchain", "langchain_fireworks"]
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print_success(f"{package} installed")
        except ImportError:
            missing.append(package)
            print_error(f"{package} missing")
    
    if missing:
        print_error(f"\nMissing packages: {', '.join(missing)}")
        print_warning("Install with: pip install -r requirements.txt")
        return False
    
    return True

def check_environment():
    """Check if environment is properly configured"""
    print_header("Checking Environment")
    
    # Check MongoDB URI
    mongo_uri = os.getenv("MONGO_URI")
    if mongo_uri:
        print_success(f"MONGO_URI set: {mongo_uri[:30]}...")
    else:
        print_error("MONGO_URI not set")
        return False
    
    # Check Fireworks API key
    fireworks_key = os.getenv("FIREWORKS")
    if fireworks_key:
        print_success(f"FIREWORKS key set: {fireworks_key[:10]}...")
    else:
        print_warning("FIREWORKS key not set (some tests may fail)")
    
    # Check OpenMC mode
    use_real_openmc = os.getenv("USE_REAL_OPENMC", "false").lower() == "true"
    if use_real_openmc:
        print_warning("Using REAL OpenMC (tests will be slower)")
    else:
        print_success("Using MOCK OpenMC (fast tests)")
    
    return True

def run_tests(test_path, description, skip_slow=True):
    """Run pytest on specified path"""
    print_header(description)
    
    cmd = ["pytest", test_path, "-v", "--tb=short"]
    
    if skip_slow:
        cmd.extend(["-m", "not slow"])
    
    try:
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0:
            print_success(f"{description} passed")
            return True
        else:
            print_error(f"{description} failed")
            return False
    except Exception as e:
        print_error(f"Error running tests: {e}")
        return False

def main():
    """Main test runner"""
    print_header("AONP Multi-Agent System Test Runner")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        print_error("\nEnvironment not properly configured")
        print_warning("Create .env file with MONGO_URI and FIREWORKS keys")
        sys.exit(1)
    
    # Parse arguments
    skip_slow = "--all" not in sys.argv
    if skip_slow:
        print_warning("\nSkipping slow tests (use --all to run all tests)")
    
    # Run test suites
    results = []
    
    # Test 1: Agent Tools
    results.append(run_tests(
        "tests/test_agent_tools.py",
        "Test Suite 1: Agent Tools",
        skip_slow
    ))
    
    # Test 2: Multi-Agent System
    results.append(run_tests(
        "tests/test_multi_agent_system.py",
        "Test Suite 2: Multi-Agent System",
        skip_slow
    ))
    
    # Test 3: API Endpoints
    results.append(run_tests(
        "api/tests/test_api_v2.py",
        "Test Suite 3: API Endpoints",
        skip_slow
    ))
    
    # Summary
    print_header("Test Summary")
    
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"Total test suites: {total}")
    print_success(f"Passed: {passed}")
    if failed > 0:
        print_error(f"Failed: {failed}")
    
    if all(results):
        print_success("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print_error("\n✗ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()


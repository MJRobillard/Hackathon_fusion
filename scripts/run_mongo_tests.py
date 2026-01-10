#!/usr/bin/env python3
"""
Run MongoDB integration tests.

This script runs all MongoDB tests and provides a summary.

Usage:
    python scripts/run_mongo_tests.py
    python scripts/run_mongo_tests.py --verbose
    python scripts/run_mongo_tests.py --quick  (runs only basic tests)
"""

import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """Run MongoDB tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run MongoDB integration tests")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Run only quick tests"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("AONP MongoDB Integration Tests")
    print("=" * 70)
    print()
    
    # Check prerequisites
    try:
        from aonp.db import get_db
        db = get_db()
        db.command('ping')
        print(f"✅ Connected to MongoDB: {db.name}")
        print()
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print()
        print("Please ensure:")
        print("  1. MongoDB URI is configured in .env")
        print("  2. MongoDB server is accessible")
        print("  3. Run: python scripts/init_db.py")
        sys.exit(1)
    
    # Build pytest command
    cmd = ["pytest", "tests/test_mongodb.py"]
    
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-v")  # Always verbose for better readability
    
    if args.quick:
        cmd.extend(["-k", "TestConnection or TestStudyOperations or TestRunOperations"])
    
    if args.coverage:
        cmd.extend(["--cov=aonp.db", "--cov-report=term-missing"])
    
    cmd.extend([
        "--tb=short",  # Short traceback format
        "--color=yes",  # Colored output
    ])
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    # Run pytest
    result = subprocess.run(cmd)
    
    print()
    if result.returncode == 0:
        print("=" * 70)
        print("✅ All tests passed!")
        print("=" * 70)
    else:
        print("=" * 70)
        print("❌ Some tests failed")
        print("=" * 70)
    
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()


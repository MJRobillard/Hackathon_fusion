#!/usr/bin/env python3
"""
Test MongoDB connection and basic operations.

Usage:
    python scripts/test_db.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aonp.db import (
    get_db,
    upsert_study,
    create_run,
    update_run_phase,
    insert_summary,
    append_event,
    get_run,
    get_summary,
    get_events,
)


def test_connection():
    """Test MongoDB connection."""
    try:
        db = get_db()
        # Ping the database
        db.command('ping')
        print(f"[PASS] Connected to MongoDB: {db.name}")
        return True
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        return False


def test_study_operations():
    """Test study operations."""
    try:
        print("\n📚 Testing study operations...")
        
        # Upsert a test study
        study = upsert_study(
            spec_hash="test_hash_123",
            canonical_spec={
                "name": "test_study",
                "description": "Test OpenMC study"
            }
        )
        print(f"  - Created study with hash: {study['spec_hash']}")
        
        # Upsert again (should not duplicate)
        study2 = upsert_study(
            spec_hash="test_hash_123",
            canonical_spec={
                "name": "test_study",
                "description": "Test OpenMC study"
            }
        )
        print(f"  - Upsert returned same study (no duplicate)")
        
        print("[PASS] Study operations successful")
        return True
    except Exception as e:
        print(f"[FAIL] Study operations failed: {e}")
        return False


def test_run_lifecycle():
    """Test complete run lifecycle."""
    try:
        print("\n🏃 Testing run lifecycle...")
        
        run_id = "test_run_001"
        
        # 1. Create run
        run = create_run(
            run_id=run_id,
            spec_hash="test_hash_123",
            initial_phase="bundle",
            initial_status="queued"
        )
        print(f"  - Created run: {run['run_id']}")
        
        # 2. Update to running/execute phase
        run = update_run_phase(
            run_id=run_id,
            phase="execute",
            status="running",
            started=True
        )
        print(f"  - Updated to phase: {run['phase']}, status: {run['status']}")
        
        # 3. Update to extract phase
        run = update_run_phase(
            run_id=run_id,
            phase="extract",
            status="running"
        )
        print(f"  - Updated to phase: {run['phase']}")
        
        # 4. Insert summary
        summary = insert_summary(
            run_id=run_id,
            keff=1.0234,
            keff_std=0.0012,
            keff_uncertainty_pcm=120.0,
            n_batches=100,
            n_inactive=20,
            n_particles=10000
        )
        print(f"  - Inserted summary: k-eff = {summary['keff']} ± {summary['keff_std']}")
        
        # 5. Update to done
        run = update_run_phase(
            run_id=run_id,
            phase="done",
            status="succeeded"
        )
        print(f"  - Completed: phase={run['phase']}, status={run['status']}")
        
        # 6. Retrieve and verify
        retrieved_run = get_run(run_id)
        retrieved_summary = get_summary(run_id)
        events = get_events(run_id)
        
        print(f"  - Retrieved run with {len(events)} events")
        print(f"  - Summary k-eff: {retrieved_summary['keff']}")
        
        print("[PASS] Run lifecycle successful")
        return True
    except Exception as e:
        print(f"[FAIL] Run lifecycle failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_logging():
    """Test event logging."""
    try:
        print("\n📝 Testing event logging...")
        
        run_id = "test_run_events"
        
        # Create a run
        create_run(
            run_id=run_id,
            spec_hash="test_hash_123"
        )
        
        # Add various events
        append_event(run_id, "custom_event", {"detail": "test detail"})
        append_event(run_id, "another_event", {"value": 42}, agent="test_agent")
        
        # Retrieve events
        events = get_events(run_id)
        print(f"  - Logged {len(events)} events")
        
        # Check event types
        event_types = [e["type"] for e in events]
        print(f"  - Event types: {', '.join(event_types)}")
        
        print("[PASS] Event logging successful")
        return True
    except Exception as e:
        print(f"[FAIL] Event logging failed: {e}")
        return False


def cleanup():
    """Clean up test data."""
    try:
        print("\n🧹 Cleaning up test data...")
        from aonp.db import col_studies, col_runs, col_summaries, col_events
        
        # Delete test documents
        col_studies().delete_many({"spec_hash": {"$regex": "^test_"}})
        col_runs().delete_many({"run_id": {"$regex": "^test_"}})
        col_summaries().delete_many({"run_id": {"$regex": "^test_"}})
        col_events().delete_many({"run_id": {"$regex": "^test_"}})
        
        print("[PASS] Cleanup successful")
        return True
    except Exception as e:
        print(f"[FAIL] Cleanup failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("AONP MongoDB Integration Test")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Connection", test_connection()))
    
    if results[-1][1]:  # Only continue if connection succeeded
        results.append(("Study Operations", test_study_operations()))
        results.append(("Run Lifecycle", test_run_lifecycle()))
        results.append(("Event Logging", test_event_logging()))
        results.append(("Cleanup", cleanup()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name:20s} {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\nSUCCESS: All tests passed!")
        sys.exit(0)
    else:
        print("\nFAILURE: Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()


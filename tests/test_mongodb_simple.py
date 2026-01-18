"""
Simple MongoDB smoke tests that can run without pytest.

These tests verify basic MongoDB functionality and can be run directly:
    python tests/test_mongodb_simple.py

For comprehensive tests, use:
    pytest tests/test_mongodb.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
from aonp.db import (
    get_db,
    init_indexes,
    upsert_study,
    create_run,
    update_run_phase,
    insert_summary,
    append_event,
    get_run,
    get_summary,
    get_events,
    col_studies,
    col_runs,
    col_summaries,
    col_events,
)


def cleanup():
    """Clean up test data."""
    col_studies().delete_many({"spec_hash": {"$regex": "^smoke_test_"}})
    col_runs().delete_many({"run_id": {"$regex": "^smoke_test_"}})
    col_summaries().delete_many({"run_id": {"$regex": "^smoke_test_"}})
    col_events().delete_many({"run_id": {"$regex": "^smoke_test_"}})


def test_connection():
    """Test 1: MongoDB Connection."""
    print("  Testing MongoDB connection...", end=" ")
    try:
        db = get_db()
        result = db.command('ping')
        assert result['ok'] == 1.0
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_indexes():
    """Test 2: Index Initialization."""
    print("  Testing index initialization...", end=" ")
    try:
        init_indexes()
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_study_operations():
    """Test 3: Study CRUD Operations."""
    print("  Testing study operations...", end=" ")
    try:
        spec_hash = f"smoke_test_{uuid.uuid4().hex[:12]}"
        canonical_spec = {"name": "smoke_test_study"}
        
        # Upsert
        study = upsert_study(spec_hash, canonical_spec)
        assert study['spec_hash'] == spec_hash
        
        # Upsert again (should be idempotent)
        study2 = upsert_study(spec_hash, canonical_spec)
        assert study['_id'] == study2['_id']
        
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_run_lifecycle():
    """Test 4: Run Lifecycle."""
    print("  Testing run lifecycle...", end=" ")
    try:
        run_id = f"smoke_test_{uuid.uuid4().hex[:12]}"
        spec_hash = f"smoke_test_{uuid.uuid4().hex[:12]}"
        
        # Create
        run = create_run(run_id, spec_hash)
        assert run['run_id'] == run_id
        assert run['status'] == "queued"
        
        # Update phase
        run = update_run_phase(run_id, phase="execute", status="running", started=True)
        assert run['phase'] == "execute"
        assert run['started_at'] is not None
        
        # Get run
        retrieved = get_run(run_id)
        assert retrieved['run_id'] == run_id
        
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_summary_operations():
    """Test 5: Summary Storage."""
    print("  Testing summary operations...", end=" ")
    try:
        run_id = f"smoke_test_{uuid.uuid4().hex[:12]}"
        
        # Insert
        summary = insert_summary(
            run_id=run_id,
            keff=1.0234,
            keff_std=0.0012,
            keff_uncertainty_pcm=120.0,
            n_batches=100,
            n_inactive=20,
            n_particles=10000
        )
        assert summary['keff'] == 1.0234
        
        # Retrieve
        retrieved = get_summary(run_id)
        assert retrieved['keff'] == 1.0234
        
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_event_logging():
    """Test 6: Event Logging."""
    print("  Testing event logging...", end=" ")
    try:
        run_id = f"smoke_test_{uuid.uuid4().hex[:12]}"
        
        # Append events
        append_event(run_id, "event1", {"data": "test1"})
        append_event(run_id, "event2", {"data": "test2"}, agent="test_agent")
        
        # Retrieve
        events = get_events(run_id)
        assert len(events) == 2
        assert events[0]['run_id'] == run_id
        
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def main():
    """Run all smoke tests."""
    print("=" * 70)
    print("MongoDB Smoke Tests")
    print("=" * 70)
    print()
    
    tests = [
        ("Connection", test_connection),
        ("Indexes", test_indexes),
        ("Study Operations", test_study_operations),
        ("Run Lifecycle", test_run_lifecycle),
        ("Summary Operations", test_summary_operations),
        ("Event Logging", test_event_logging),
    ]
    
    results = []
    
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    print()
    print("  Cleaning up test data...", end=" ")
    try:
        cleanup()
        print("PASS")
    except Exception as e:
        print(f"WARNING: {e}")
    
    print()
    print("=" * 70)
    print("Test Summary:")
    print("=" * 70)
    
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {name:25s} {status}")
    
    all_passed = all(result[1] for result in results)
    
    print()
    if all_passed:
        print("SUCCESS: All smoke tests passed!")
        print()
        print("Next steps:")
        print("  - Run full test suite: pytest tests/test_mongodb.py")
        print("  - Run with coverage: pytest tests/test_mongodb.py --cov=aonp.db")
        sys.exit(0)
    else:
        print("FAILURE: Some tests failed")
        print()
        print("Troubleshooting:")
        print("  - Check MongoDB connection in .env")
        print("  - Run: python scripts/init_db.py")
        print("  - Check MongoDB Atlas network access")
        sys.exit(1)


if __name__ == "__main__":
    main()


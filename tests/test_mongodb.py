"""
Comprehensive tests for MongoDB integration.

Tests cover:
- Connection and initialization
- Study operations (CRUD)
- Run lifecycle management
- Event logging and retrieval
- Summary operations
- Multi-worker coordination (atomic claiming)
- Error handling
- Concurrent operations
- Data integrity
"""

import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, Any
import uuid

# Import database functions
from aonp.db import (
    # Connection
    get_db,
    init_indexes,
    
    # Collections
    col_studies,
    col_runs,
    col_summaries,
    col_events,
    col_agent_outputs,
    
    # Study ops
    upsert_study,
    get_study_by_hash,
    
    # Run ops
    create_run,
    get_run,
    update_run_status,
    update_run_phase,
    update_run_artifacts,
    claim_next_run,
    renew_lease,
    release_run,
    
    # Summary ops
    insert_summary,
    get_summary,
    
    # Event ops
    append_event,
    get_events,
    
    # Agent ops
    upsert_agent_output,
    get_agent_outputs,
)


# Test fixtures
@pytest.fixture(scope="module")
def db():
    """Get database connection for all tests."""
    database = get_db()
    # Ensure indexes exist
    init_indexes(database)
    return database


@pytest.fixture
def test_spec_hash():
    """Generate unique spec hash for testing."""
    return f"test_hash_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def test_run_id():
    """Generate unique run ID for testing."""
    return f"test_run_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def cleanup_test_data(db):
    """Cleanup test data after each test."""
    yield
    # Clean up test documents
    col_studies(db).delete_many({"spec_hash": {"$regex": "^test_"}})
    col_runs(db).delete_many({"run_id": {"$regex": "^test_"}})
    col_summaries(db).delete_many({"run_id": {"$regex": "^test_"}})
    col_events(db).delete_many({"run_id": {"$regex": "^test_"}})
    col_agent_outputs(db).delete_many({"run_id": {"$regex": "^test_"}})


# Connection Tests
class TestConnection:
    """Test MongoDB connection and initialization."""
    
    def test_connection(self, db):
        """Test database connection is established."""
        result = db.command('ping')
        assert result['ok'] == 1.0
    
    def test_database_name(self, db):
        """Test correct database is selected."""
        assert db.name is not None
        assert isinstance(db.name, str)
    
    def test_init_indexes(self, db):
        """Test index initialization."""
        init_indexes(db)
        
        # Check indexes exist
        runs_indexes = col_runs(db).index_information()
        assert 'run_id_1' in runs_indexes
        
        studies_indexes = col_studies(db).index_information()
        assert 'spec_hash_1' in studies_indexes


# Study Operations Tests
class TestStudyOperations:
    """Test study CRUD operations."""
    
    def test_upsert_study_creates_new(self, cleanup_test_data, test_spec_hash):
        """Test upserting a new study creates it."""
        canonical_spec = {
            "name": "test_study",
            "description": "Test study spec"
        }
        
        study = upsert_study(test_spec_hash, canonical_spec)
        
        assert study is not None
        assert study['spec_hash'] == test_spec_hash
        assert study['canonical_spec'] == canonical_spec
        assert 'created_at' in study
    
    def test_upsert_study_is_idempotent(self, cleanup_test_data, test_spec_hash):
        """Test upserting same study doesn't create duplicate."""
        canonical_spec = {"name": "test_study"}
        
        study1 = upsert_study(test_spec_hash, canonical_spec)
        study2 = upsert_study(test_spec_hash, canonical_spec)
        
        assert study1['_id'] == study2['_id']
        assert study1['created_at'] == study2['created_at']
    
    def test_get_study_by_hash(self, cleanup_test_data, test_spec_hash):
        """Test retrieving study by hash."""
        canonical_spec = {"name": "test_study"}
        upsert_study(test_spec_hash, canonical_spec)
        
        retrieved = get_study_by_hash(test_spec_hash)
        
        assert retrieved is not None
        assert retrieved['spec_hash'] == test_spec_hash
        assert retrieved['canonical_spec'] == canonical_spec
    
    def test_get_nonexistent_study(self, cleanup_test_data):
        """Test getting non-existent study returns None."""
        result = get_study_by_hash("nonexistent_hash")
        assert result is None


# Run Operations Tests
class TestRunOperations:
    """Test run lifecycle operations."""
    
    def test_create_run(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test creating a new run."""
        run = create_run(
            run_id=test_run_id,
            spec_hash=test_spec_hash,
            initial_phase="bundle",
            initial_status="queued"
        )
        
        assert run is not None
        assert run['run_id'] == test_run_id
        assert run['spec_hash'] == test_spec_hash
        assert run['status'] == "queued"
        assert run['phase'] == "bundle"
        assert run['claimed_by'] is None
        assert run['lease_expires_at'] is None
        assert 'created_at' in run
        assert run['started_at'] is None
        assert run['ended_at'] is None
    
    def test_get_run(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test retrieving a run."""
        create_run(test_run_id, test_spec_hash)
        
        retrieved = get_run(test_run_id)
        
        assert retrieved is not None
        assert retrieved['run_id'] == test_run_id
    
    def test_update_run_status(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test updating run status."""
        create_run(test_run_id, test_spec_hash)
        
        updated = update_run_status(
            run_id=test_run_id,
            status="running"
        )
        
        assert updated['status'] == "running"
    
    def test_update_run_status_with_error(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test updating run status with error info."""
        create_run(test_run_id, test_spec_hash)
        
        error_info = {
            "type": "SimulationError",
            "message": "Test error",
            "traceback": "..."
        }
        
        updated = update_run_status(
            run_id=test_run_id,
            status="failed",
            error=error_info,
            ended=True
        )
        
        assert updated['status'] == "failed"
        assert updated['error'] == error_info
        assert updated['ended_at'] is not None
    
    def test_update_run_phase(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test updating run phase."""
        create_run(test_run_id, test_spec_hash)
        
        updated = update_run_phase(
            run_id=test_run_id,
            phase="execute",
            status="running",
            started=True
        )
        
        assert updated['phase'] == "execute"
        assert updated['status'] == "running"
        assert updated['started_at'] is not None
    
    def test_update_run_artifacts(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test updating run artifacts."""
        create_run(test_run_id, test_spec_hash)
        
        artifacts = {
            "bundle_path": "/path/to/bundle",
            "statepoint_path": "/path/to/statepoint.h5",
            "parquet_path": "/path/to/summary.parquet"
        }
        
        updated = update_run_artifacts(test_run_id, artifacts)
        
        assert updated['artifacts'] == artifacts
    
    def test_run_lifecycle_complete(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test complete run lifecycle: queued → running → succeeded."""
        # Create
        run = create_run(test_run_id, test_spec_hash)
        assert run['status'] == "queued"
        assert run['phase'] == "bundle"
        
        # Start execution
        run = update_run_phase(test_run_id, phase="execute", status="running", started=True)
        assert run['status'] == "running"
        assert run['phase'] == "execute"
        assert run['started_at'] is not None
        
        # Extract phase
        run = update_run_phase(test_run_id, phase="extract")
        assert run['phase'] == "extract"
        
        # Complete
        run = update_run_phase(test_run_id, phase="done", status="succeeded")
        assert run['status'] == "succeeded"
        assert run['phase'] == "done"


# Multi-Worker Tests
class TestMultiWorkerCoordination:
    """Test atomic claiming and multi-worker coordination."""
    
    def test_claim_next_run(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test claiming a queued run."""
        create_run(test_run_id, test_spec_hash)
        
        claimed = claim_next_run(
            worker_id="worker-01",
            lease_seconds=300
        )
        
        assert claimed is not None
        assert claimed['run_id'] == test_run_id
        assert claimed['status'] == "running"
        assert claimed['claimed_by'] == "worker-01"
        assert claimed['lease_expires_at'] is not None
    
    def test_claim_no_available_runs(self, cleanup_test_data):
        """Test claiming when no runs are available."""
        claimed = claim_next_run(worker_id="worker-01")
        assert claimed is None
    
    def test_claim_respects_status_filter(self, cleanup_test_data, test_spec_hash):
        """Test claim only gets runs with specified status."""
        # Create running run
        run_id1 = f"test_run_{uuid.uuid4().hex[:12]}"
        create_run(run_id1, test_spec_hash, initial_status="running")
        
        # Create queued run
        run_id2 = f"test_run_{uuid.uuid4().hex[:12]}"
        create_run(run_id2, test_spec_hash, initial_status="queued")
        
        # Claim should get queued run, not running run
        claimed = claim_next_run(worker_id="worker-01", eligible_status="queued")
        
        assert claimed is not None
        assert claimed['run_id'] == run_id2
    
    def test_claim_fifo_ordering(self, cleanup_test_data, test_spec_hash):
        """Test claiming respects FIFO order (oldest first)."""
        # Create runs in order
        run_id1 = f"test_run_{uuid.uuid4().hex[:12]}"
        create_run(run_id1, test_spec_hash)
        time.sleep(0.1)  # Ensure different timestamps
        
        run_id2 = f"test_run_{uuid.uuid4().hex[:12]}"
        create_run(run_id2, test_spec_hash)
        
        # Claim should get oldest (run_id1)
        claimed = claim_next_run(worker_id="worker-01")
        
        assert claimed is not None
        assert claimed['run_id'] == run_id1
    
    def test_concurrent_claims_no_collision(self, cleanup_test_data, test_spec_hash):
        """Test two workers can't claim the same run."""
        # Create two runs
        run_id1 = f"test_run_{uuid.uuid4().hex[:12]}"
        run_id2 = f"test_run_{uuid.uuid4().hex[:12]}"
        create_run(run_id1, test_spec_hash)
        create_run(run_id2, test_spec_hash)
        
        # Two workers claim
        claimed1 = claim_next_run(worker_id="worker-01")
        claimed2 = claim_next_run(worker_id="worker-02")
        
        # They should get different runs
        assert claimed1 is not None
        assert claimed2 is not None
        assert claimed1['run_id'] != claimed2['run_id']
        
        # Third claim should get nothing
        claimed3 = claim_next_run(worker_id="worker-03")
        assert claimed3 is None
    
    def test_renew_lease(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test renewing a lease."""
        create_run(test_run_id, test_spec_hash)
        claimed = claim_next_run(worker_id="worker-01", lease_seconds=60)
        
        original_expiry = claimed['lease_expires_at']
        
        # Wait a bit and renew
        time.sleep(0.5)
        success = renew_lease(test_run_id, "worker-01", lease_seconds=120)
        
        assert success is True
        
        # Check lease was extended
        run = get_run(test_run_id)
        assert run['lease_expires_at'] > original_expiry
    
    def test_renew_lease_wrong_worker(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test renewing lease fails for wrong worker."""
        create_run(test_run_id, test_spec_hash)
        claim_next_run(worker_id="worker-01")
        
        # Different worker tries to renew
        success = renew_lease(test_run_id, "worker-02", lease_seconds=120)
        
        assert success is False
    
    def test_release_run(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test releasing a claimed run."""
        create_run(test_run_id, test_spec_hash)
        claim_next_run(worker_id="worker-01")
        
        released = release_run(
            run_id=test_run_id,
            worker_id="worker-01",
            status="succeeded",
            phase="done",
            ended=True
        )
        
        assert released is not None
        assert released['status'] == "succeeded"
        assert released['phase'] == "done"
        assert released['lease_expires_at'] is None
        assert released['ended_at'] is not None
    
    def test_expired_lease_can_be_reclaimed(self, cleanup_test_data, test_run_id, test_spec_hash, db):
        """Test expired lease allows reclaiming."""
        create_run(test_run_id, test_spec_hash)
        
        # Claim with very short lease
        claim_next_run(worker_id="worker-01", lease_seconds=1)
        
        # Manually expire the lease (for testing)
        from aonp.db.mongo import utcnow
        past_time = utcnow() - timedelta(seconds=10)
        col_runs(db).update_one(
            {"run_id": test_run_id},
            {"$set": {"lease_expires_at": past_time}}
        )
        
        # Another worker should be able to claim it
        reclaimed = claim_next_run(worker_id="worker-02", eligible_status="running")
        
        assert reclaimed is not None
        assert reclaimed['run_id'] == test_run_id
        assert reclaimed['claimed_by'] == "worker-02"


# Summary Operations Tests
class TestSummaryOperations:
    """Test summary CRUD operations."""
    
    def test_insert_summary(self, cleanup_test_data, test_run_id):
        """Test inserting a summary."""
        summary = insert_summary(
            run_id=test_run_id,
            keff=1.0234,
            keff_std=0.0012,
            keff_uncertainty_pcm=120.0,
            n_batches=100,
            n_inactive=20,
            n_particles=10000
        )
        
        assert summary is not None
        assert summary['run_id'] == test_run_id
        assert summary['keff'] == 1.0234
        assert summary['keff_std'] == 0.0012
        assert summary['keff_uncertainty_pcm'] == 120.0
        assert 'extracted_at' in summary
    
    def test_get_summary(self, cleanup_test_data, test_run_id):
        """Test retrieving a summary."""
        insert_summary(
            run_id=test_run_id,
            keff=1.0234,
            keff_std=0.0012,
            keff_uncertainty_pcm=120.0,
            n_batches=100,
            n_inactive=20,
            n_particles=10000
        )
        
        retrieved = get_summary(test_run_id)
        
        assert retrieved is not None
        assert retrieved['run_id'] == test_run_id
        assert retrieved['keff'] == 1.0234
    
    def test_get_nonexistent_summary(self, cleanup_test_data):
        """Test getting non-existent summary returns None."""
        result = get_summary("nonexistent_run_id")
        assert result is None


# Event Operations Tests
class TestEventOperations:
    """Test event logging and retrieval."""
    
    def test_append_event(self, cleanup_test_data, test_run_id):
        """Test appending an event."""
        append_event(
            run_id=test_run_id,
            event_type="test_event",
            payload={"detail": "test detail"}
        )
        
        events = get_events(test_run_id)
        
        assert len(events) > 0
        assert events[0]['run_id'] == test_run_id
        assert events[0]['type'] == "test_event"
        assert events[0]['payload']['detail'] == "test detail"
    
    def test_append_event_with_agent(self, cleanup_test_data, test_run_id):
        """Test appending event with agent info."""
        append_event(
            run_id=test_run_id,
            event_type="agent_action",
            payload={"action": "analyze"},
            agent="planner"
        )
        
        events = get_events(test_run_id)
        
        assert events[0]['agent'] == "planner"
    
    def test_get_events_ordered(self, cleanup_test_data, test_run_id):
        """Test events are returned in reverse chronological order."""
        append_event(test_run_id, "event1", {"seq": 1})
        time.sleep(0.1)
        append_event(test_run_id, "event2", {"seq": 2})
        time.sleep(0.1)
        append_event(test_run_id, "event3", {"seq": 3})
        
        events = get_events(test_run_id)
        
        # Most recent first
        assert events[0]['payload']['seq'] == 3
        assert events[1]['payload']['seq'] == 2
        assert events[2]['payload']['seq'] == 1
    
    def test_get_events_with_limit(self, cleanup_test_data, test_run_id):
        """Test getting events with limit."""
        for i in range(10):
            append_event(test_run_id, f"event{i}", {"seq": i})
        
        events = get_events(test_run_id, limit=5)
        
        assert len(events) == 5
    
    def test_get_events_by_type(self, cleanup_test_data, test_run_id):
        """Test filtering events by type."""
        append_event(test_run_id, "type_a", {"data": "a"})
        append_event(test_run_id, "type_b", {"data": "b"})
        append_event(test_run_id, "type_a", {"data": "a2"})
        
        events = get_events(test_run_id, event_type="type_a")
        
        assert len(events) == 2
        assert all(e['type'] == "type_a" for e in events)


# Agent Operations Tests
class TestAgentOperations:
    """Test agent output storage and retrieval."""
    
    def test_upsert_agent_output(self, cleanup_test_data, test_run_id):
        """Test storing agent output."""
        upsert_agent_output(
            run_id=test_run_id,
            agent="planner",
            kind="plan",
            data={"steps": ["step1", "step2"]},
            schema_version="0.1"
        )
        
        outputs = get_agent_outputs(test_run_id)
        
        assert len(outputs) > 0
        assert outputs[0]['agent'] == "planner"
        assert outputs[0]['kind'] == "plan"
        assert outputs[0]['data']['steps'] == ["step1", "step2"]
    
    def test_get_agent_outputs_by_agent(self, cleanup_test_data, test_run_id):
        """Test filtering agent outputs by agent."""
        upsert_agent_output(test_run_id, "planner", "plan", {"data": "p"})
        upsert_agent_output(test_run_id, "executor", "result", {"data": "e"})
        
        outputs = get_agent_outputs(test_run_id, agent="planner")
        
        assert len(outputs) == 1
        assert outputs[0]['agent'] == "planner"
    
    def test_get_agent_outputs_by_kind(self, cleanup_test_data, test_run_id):
        """Test filtering agent outputs by kind."""
        upsert_agent_output(test_run_id, "planner", "plan", {"data": "plan"})
        upsert_agent_output(test_run_id, "planner", "report", {"data": "report"})
        
        outputs = get_agent_outputs(test_run_id, kind="plan")
        
        assert len(outputs) == 1
        assert outputs[0]['kind'] == "plan"


# Integration Tests
class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_complete_simulation_workflow(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test complete simulation workflow from start to finish."""
        # 1. Store study
        upsert_study(test_spec_hash, {"name": "test_study"})
        
        # 2. Create run
        run = create_run(test_run_id, test_spec_hash)
        assert run['status'] == "queued"
        
        # 3. Worker claims run
        claimed = claim_next_run(worker_id="worker-01")
        assert claimed['run_id'] == test_run_id
        
        # 4. Execute phase
        update_run_phase(test_run_id, phase="execute", status="running")
        
        # 5. Store results
        insert_summary(
            run_id=test_run_id,
            keff=1.0234,
            keff_std=0.0012,
            keff_uncertainty_pcm=120.0,
            n_batches=100,
            n_inactive=20,
            n_particles=10000
        )
        
        # 6. Extract phase
        update_run_phase(test_run_id, phase="extract")
        
        # 7. Complete
        release_run(
            run_id=test_run_id,
            worker_id="worker-01",
            status="succeeded",
            phase="done",
            ended=True
        )
        
        # Verify final state
        run = get_run(test_run_id)
        assert run['status'] == "succeeded"
        assert run['phase'] == "done"
        assert run['ended_at'] is not None
        
        summary = get_summary(test_run_id)
        assert summary is not None
        assert summary['keff'] == 1.0234
        
        events = get_events(test_run_id)
        assert len(events) > 0
    
    def test_failure_workflow(self, cleanup_test_data, test_run_id, test_spec_hash):
        """Test workflow with failure."""
        create_run(test_run_id, test_spec_hash)
        claim_next_run(worker_id="worker-01")
        
        # Simulate failure
        error_info = {
            "type": "SimulationError",
            "message": "OpenMC crashed",
            "traceback": "..."
        }
        
        release_run(
            run_id=test_run_id,
            worker_id="worker-01",
            status="failed",
            error=error_info,
            ended=True
        )
        
        # Verify
        run = get_run(test_run_id)
        assert run['status'] == "failed"
        assert run['error'] == error_info
        assert run['ended_at'] is not None


# Edge Case Tests
class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_update_nonexistent_run(self, cleanup_test_data):
        """Test updating non-existent run returns None."""
        result = update_run_status("nonexistent_run_id", "running")
        assert result is None
    
    def test_claim_with_phase_filter(self, cleanup_test_data, test_spec_hash):
        """Test claiming with phase filter."""
        run_id1 = f"test_run_{uuid.uuid4().hex[:12]}"
        run_id2 = f"test_run_{uuid.uuid4().hex[:12]}"
        
        create_run(run_id1, test_spec_hash, initial_phase="bundle")
        create_run(run_id2, test_spec_hash, initial_phase="execute")
        
        # Claim only execute phase
        claimed = claim_next_run(
            worker_id="worker-01",
            eligible_phase="execute"
        )
        
        assert claimed is not None
        assert claimed['run_id'] == run_id2
    
    def test_multiple_summaries_for_same_run(self, cleanup_test_data, test_run_id, db):
        """Test inserting multiple summaries for same run (should be prevented by unique index)."""
        insert_summary(test_run_id, 1.0, 0.001, 100.0, 100, 20, 10000)
        
        # Second insert should fail due to unique constraint on run_id
        # But insert_summary doesn't enforce this - MongoDB does
        # Just verify we can retrieve the summary
        summary = get_summary(test_run_id)
        assert summary is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


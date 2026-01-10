"""
Tests for agent tools
Tests all 8 tools: submit_study, query_results, generate_sweep, compare_runs,
get_study_statistics, get_run_by_id, get_recent_runs, validate_physics
"""

import pytest
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agent_tools import (
    submit_study,
    query_results,
    generate_sweep,
    compare_runs,
    get_study_statistics,
    get_run_by_id,
    get_recent_runs,
    validate_physics,
    USE_REAL_OPENMC
)

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_spec():
    """Sample study specification"""
    return {
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Zircaloy", "Water"],
        "enrichment_pct": 4.5,
        "temperature_K": 600,
        "particles": 10000,
        "batches": 50
    }

@pytest.fixture
def sample_run_id(sample_spec):
    """Create a sample run and return its ID"""
    result = submit_study(sample_spec)
    return result["run_id"]

# ============================================================================
# TEST: submit_study
# ============================================================================

def test_submit_study_success(sample_spec):
    """Test successful study submission"""
    result = submit_study(sample_spec)
    
    assert "run_id" in result
    assert result["run_id"].startswith("run_")
    assert "spec_hash" in result
    assert "keff" in result
    assert "keff_std" in result
    assert result["status"] == "completed"
    assert isinstance(result["keff"], float)
    assert isinstance(result["keff_std"], float)
    assert result["keff"] > 0  # Physical constraint

def test_submit_study_minimal_spec():
    """Test with minimal specification"""
    minimal_spec = {
        "geometry": "Simple sphere",
        "materials": ["UO2"]
    }
    
    result = submit_study(minimal_spec)
    assert result["status"] == "completed"

def test_submit_study_deduplication(sample_spec):
    """Test that identical specs get same spec_hash"""
    result1 = submit_study(sample_spec)
    result2 = submit_study(sample_spec)
    
    assert result1["spec_hash"] == result2["spec_hash"]
    assert result1["run_id"] != result2["run_id"]  # Different runs

def test_submit_study_different_enrichment(sample_spec):
    """Test that different enrichments get different spec_hash"""
    result1 = submit_study(sample_spec)
    
    spec2 = sample_spec.copy()
    spec2["enrichment_pct"] = 3.5
    result2 = submit_study(spec2)
    
    assert result1["spec_hash"] != result2["spec_hash"]

# ============================================================================
# TEST: validate_physics
# ============================================================================

def test_validate_physics_valid_spec(sample_spec):
    """Test validation of valid spec"""
    result = validate_physics(sample_spec)
    
    assert result["valid"] == True
    assert isinstance(result["warnings"], list)
    assert isinstance(result["errors"], list)

def test_validate_physics_invalid_enrichment():
    """Test validation catches invalid enrichment"""
    spec = {
        "geometry": "PWR",
        "materials": ["UO2"],
        "enrichment_pct": 150.0  # Invalid: > 100%
    }
    
    result = validate_physics(spec)
    assert result["valid"] == False
    assert len(result["errors"]) > 0

def test_validate_physics_negative_temperature():
    """Test validation catches negative temperature"""
    spec = {
        "geometry": "PWR",
        "materials": ["UO2"],
        "temperature_K": -100  # Invalid
    }
    
    result = validate_physics(spec)
    assert result["valid"] == False

def test_validate_physics_warnings_low_enrichment():
    """Test validation warns about low enrichment"""
    spec = {
        "geometry": "PWR",
        "materials": ["UO2"],
        "enrichment_pct": 1.0  # Low but valid
    }
    
    result = validate_physics(spec)
    assert result["valid"] == True
    assert len(result["warnings"]) > 0

def test_validate_physics_warnings_few_particles():
    """Test validation warns about few particles"""
    spec = {
        "geometry": "PWR",
        "materials": ["UO2"],
        "particles": 50  # Very few
    }
    
    result = validate_physics(spec)
    assert result["valid"] == True
    assert any("particles" in w.lower() for w in result["warnings"])

# ============================================================================
# TEST: get_run_by_id
# ============================================================================

def test_get_run_by_id_success(sample_run_id):
    """Test fetching run by ID"""
    result = get_run_by_id(sample_run_id)
    
    assert result is not None
    assert result["run_id"] == sample_run_id
    assert "keff" in result
    assert "spec" in result
    assert "created_at" in result

def test_get_run_by_id_not_found():
    """Test fetching non-existent run"""
    result = get_run_by_id("run_notfound")
    assert result is None

# ============================================================================
# TEST: get_recent_runs
# ============================================================================

def test_get_recent_runs_default():
    """Test getting recent runs with default limit"""
    results = get_recent_runs()
    
    assert isinstance(results, list)
    assert len(results) <= 10  # Default limit

def test_get_recent_runs_custom_limit():
    """Test getting recent runs with custom limit"""
    results = get_recent_runs(limit=3)
    
    assert isinstance(results, list)
    assert len(results) <= 3

def test_get_recent_runs_sorted():
    """Test that recent runs are sorted by creation time"""
    # Create two runs
    spec1 = {
        "geometry": "Test 1",
        "materials": ["UO2"],
        "enrichment_pct": 3.0
    }
    submit_study(spec1)
    
    spec2 = {
        "geometry": "Test 2",
        "materials": ["UO2"],
        "enrichment_pct": 4.0
    }
    submit_study(spec2)
    
    results = get_recent_runs(limit=2)
    
    # Most recent should be first
    if len(results) >= 2:
        date1 = datetime.fromisoformat(results[0]["created_at"])
        date2 = datetime.fromisoformat(results[1]["created_at"])
        assert date1 >= date2

# ============================================================================
# TEST: query_results
# ============================================================================

def test_query_results_no_filter():
    """Test querying all results"""
    results = query_results()
    
    assert isinstance(results, list)
    assert len(results) <= 10  # Default limit

def test_query_results_with_filter(sample_run_id):
    """Test querying with filter"""
    results = query_results({"spec.geometry": "PWR pin cell"})
    
    assert isinstance(results, list)
    # Should find at least our sample
    assert len(results) > 0

def test_query_results_custom_limit():
    """Test querying with custom limit"""
    results = query_results(limit=5)
    
    assert len(results) <= 5

def test_query_results_keff_filter():
    """Test querying by keff range"""
    results = query_results({"keff": {"$gt": 1.0}})
    
    assert isinstance(results, list)
    # All results should have keff > 1.0
    for r in results:
        assert r["keff"] > 1.0

# ============================================================================
# TEST: generate_sweep
# ============================================================================

def test_generate_sweep_enrichment():
    """Test enrichment sweep"""
    base_spec = {
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Zircaloy", "Water"],
        "temperature_K": 600,
        "particles": 10000,
        "batches": 50
    }
    
    run_ids = generate_sweep(
        base_spec=base_spec,
        param_name="enrichment_pct",
        param_values=[3.0, 4.0, 5.0]
    )
    
    assert isinstance(run_ids, list)
    assert len(run_ids) == 3
    for run_id in run_ids:
        assert run_id.startswith("run_")

def test_generate_sweep_temperature():
    """Test temperature sweep"""
    base_spec = {
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Zircaloy", "Water"],
        "enrichment_pct": 4.5,
        "particles": 10000,
        "batches": 50
    }
    
    run_ids = generate_sweep(
        base_spec=base_spec,
        param_name="temperature_K",
        param_values=[300, 600, 900]
    )
    
    assert len(run_ids) == 3

def test_generate_sweep_single_value():
    """Test sweep with single value"""
    base_spec = {
        "geometry": "Test",
        "materials": ["UO2"],
        "enrichment_pct": 4.5
    }
    
    run_ids = generate_sweep(
        base_spec=base_spec,
        param_name="enrichment_pct",
        param_values=[4.5]
    )
    
    assert len(run_ids) == 1

# ============================================================================
# TEST: compare_runs
# ============================================================================

def test_compare_runs_success():
    """Test comparing multiple runs"""
    # Create two runs
    spec1 = {
        "geometry": "Compare test 1",
        "materials": ["UO2"],
        "enrichment_pct": 3.0
    }
    result1 = submit_study(spec1)
    
    spec2 = {
        "geometry": "Compare test 2",
        "materials": ["UO2"],
        "enrichment_pct": 5.0
    }
    result2 = submit_study(spec2)
    
    comparison = compare_runs([result1["run_id"], result2["run_id"]])
    
    assert "num_runs" in comparison
    assert comparison["num_runs"] == 2
    assert "keff_values" in comparison
    assert len(comparison["keff_values"]) == 2
    assert "keff_mean" in comparison
    assert "keff_min" in comparison
    assert "keff_max" in comparison
    assert "runs" in comparison

def test_compare_runs_statistics():
    """Test comparison statistics are correct"""
    # Create runs with known order
    specs = [
        {"geometry": "Test", "materials": ["UO2"], "enrichment_pct": 3.0},
        {"geometry": "Test", "materials": ["UO2"], "enrichment_pct": 4.0},
        {"geometry": "Test", "materials": ["UO2"], "enrichment_pct": 5.0}
    ]
    
    run_ids = []
    for spec in specs:
        result = submit_study(spec)
        run_ids.append(result["run_id"])
    
    comparison = compare_runs(run_ids)
    
    # Check statistics
    assert comparison["keff_min"] <= comparison["keff_mean"] <= comparison["keff_max"]
    assert len(comparison["keff_values"]) == 3

def test_compare_runs_not_found():
    """Test comparing non-existent runs"""
    comparison = compare_runs(["run_notfound1", "run_notfound2"])
    
    assert "error" in comparison

def test_compare_runs_single_run():
    """Test comparing single run (edge case)"""
    spec = {
        "geometry": "Single",
        "materials": ["UO2"],
        "enrichment_pct": 4.5
    }
    result = submit_study(spec)
    
    comparison = compare_runs([result["run_id"]])
    
    # Should still work with single run
    assert comparison["num_runs"] == 1
    assert comparison["keff_min"] == comparison["keff_max"]

# ============================================================================
# TEST: get_study_statistics
# ============================================================================

def test_get_study_statistics():
    """Test getting database statistics"""
    stats = get_study_statistics()
    
    assert "total_studies" in stats
    assert "total_runs" in stats
    assert "total_summaries" in stats
    assert "completed_runs" in stats
    assert "recent_runs" in stats
    
    assert isinstance(stats["total_studies"], int)
    assert isinstance(stats["total_runs"], int)
    assert isinstance(stats["recent_runs"], list)
    
    # Should have at least some data from previous tests
    assert stats["total_runs"] > 0

def test_get_study_statistics_recent_runs():
    """Test that recent runs are included"""
    stats = get_study_statistics()
    
    recent = stats["recent_runs"]
    assert isinstance(recent, list)
    assert len(recent) <= 5  # Should return max 5
    
    for run in recent:
        assert "run_id" in run
        assert "keff" in run
        assert "geometry" in run

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_workflow_single_study():
    """Test complete workflow: validate → submit → fetch"""
    spec = {
        "geometry": "Integration test",
        "materials": ["UO2", "Water"],
        "enrichment_pct": 4.5,
        "temperature_K": 600,
        "particles": 10000,
        "batches": 50
    }
    
    # Step 1: Validate
    validation = validate_physics(spec)
    assert validation["valid"]
    
    # Step 2: Submit
    result = submit_study(spec)
    assert result["status"] == "completed"
    run_id = result["run_id"]
    
    # Step 3: Fetch
    fetched = get_run_by_id(run_id)
    assert fetched is not None
    assert fetched["run_id"] == run_id
    assert fetched["keff"] == result["keff"]

def test_full_workflow_sweep():
    """Test complete workflow: sweep → compare → query"""
    base_spec = {
        "geometry": "Sweep integration test",
        "materials": ["UO2", "Water"],
        "temperature_K": 600,
        "particles": 10000,
        "batches": 50
    }
    
    # Step 1: Generate sweep
    run_ids = generate_sweep(
        base_spec=base_spec,
        param_name="enrichment_pct",
        param_values=[3.0, 4.0, 5.0]
    )
    assert len(run_ids) == 3
    
    # Step 2: Compare
    comparison = compare_runs(run_ids)
    assert comparison["num_runs"] == 3
    
    # Step 3: Query
    results = query_results({"spec.geometry": "Sweep integration test"})
    assert len(results) >= 3

# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.slow
def test_performance_multiple_submissions():
    """Test performance with multiple submissions"""
    import time
    
    specs = [
        {
            "geometry": f"Perf test {i}",
            "materials": ["UO2"],
            "enrichment_pct": 3.0 + i * 0.5
        }
        for i in range(5)
    ]
    
    start = time.time()
    for spec in specs:
        submit_study(spec)
    elapsed = time.time() - start
    
    # Should complete reasonably fast
    # With mock: ~0.5s, with real OpenMC: ~20-30s
    if USE_REAL_OPENMC:
        assert elapsed < 60  # 1 minute for 5 runs
    else:
        assert elapsed < 2  # 2 seconds for 5 mock runs

# ============================================================================
# RUN WITH PYTEST
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])


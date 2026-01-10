"""
Tests for API v2 endpoints
Tests all endpoints from plan.md
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main_v2 import app

client = TestClient(app)

# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

class TestHealthCheck:
    """Tests for health check endpoint"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["version"] == "2.0.0"
        assert "services" in data
        assert "mongodb" in data["services"]


# ============================================================================
# NATURAL LANGUAGE QUERY TESTS
# ============================================================================

class TestQueryEndpoint:
    """Tests for /api/v1/query endpoint"""
    
    def test_submit_query_success(self):
        """Test successful query submission"""
        response = client.post("/api/v1/query", json={
            "query": "Simulate PWR pin with 4.5% enriched UO2"
        })
        
        assert response.status_code == 202
        data = response.json()
        
        assert "query_id" in data
        assert data["query_id"].startswith("q_")
        assert data["status"] == "queued"
        assert "assigned_agent" in data
        assert "estimated_duration" in data
    
    def test_submit_query_with_stream_option(self):
        """Test query submission with streaming"""
        response = client.post("/api/v1/query", json={
            "query": "Compare enrichments",
            "options": {"stream": True}
        })
        
        assert response.status_code == 202
        data = response.json()
        assert "stream_url" in data
        assert data["stream_url"].endswith("/stream")
    
    def test_submit_query_empty(self):
        """Test query submission with empty query"""
        response = client.post("/api/v1/query", json={
            "query": ""
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_submit_query_too_long(self):
        """Test query submission with query too long"""
        long_query = "a" * 501
        response = client.post("/api/v1/query", json={
            "query": long_query
        })
        
        assert response.status_code == 422
    
    def test_get_query_status_not_found(self):
        """Test getting status of non-existent query"""
        response = client.get("/api/v1/query/q_notfound")
        assert response.status_code == 404
    
    def test_get_query_status_success(self):
        """Test getting status of existing query"""
        # First create a query
        create_response = client.post("/api/v1/query", json={
            "query": "Test simulation"
        })
        query_id = create_response.json()["query_id"]
        
        # Get its status
        status_response = client.get(f"/api/v1/query/{query_id}")
        assert status_response.status_code == 200
        
        data = status_response.json()
        assert data["query_id"] == query_id
        assert data["query"] == "Test simulation"
        assert data["status"] in ["queued", "processing", "completed", "failed"]


# ============================================================================
# DIRECT TOOL ACCESS TESTS
# ============================================================================

class TestDirectStudySubmission:
    """Tests for /api/v1/studies endpoint"""
    
    def test_submit_study_direct(self):
        """Test direct study submission"""
        response = client.post("/api/v1/studies", json={
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Zircaloy", "Water"],
            "enrichment_pct": 4.5,
            "temperature_K": 600,
            "particles": 10000,
            "batches": 50
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "run_id" in data
        assert "keff" in data
        assert "keff_std" in data
        assert data["status"] == "completed"
    
    def test_submit_study_minimal(self):
        """Test study submission with minimal spec"""
        response = client.post("/api/v1/studies", json={
            "geometry": "Simple",
            "materials": ["UO2"]
        })
        
        assert response.status_code == 200
    
    def test_get_study_by_id_success(self):
        """Test getting study by ID"""
        # First create a study
        create_response = client.post("/api/v1/studies", json={
            "geometry": "Test",
            "materials": ["UO2"],
            "enrichment_pct": 4.5
        })
        run_id = create_response.json()["run_id"]
        
        # Get it
        get_response = client.get(f"/api/v1/studies/{run_id}")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data["run_id"] == run_id
    
    def test_get_study_by_id_not_found(self):
        """Test getting non-existent study"""
        response = client.get("/api/v1/studies/run_notfound")
        assert response.status_code == 404


class TestDirectSweepSubmission:
    """Tests for /api/v1/sweeps endpoint"""
    
    def test_submit_sweep_direct(self):
        """Test direct sweep submission"""
        response = client.post("/api/v1/sweeps", json={
            "base_spec": {
                "geometry": "PWR pin cell",
                "materials": ["UO2", "Water"],
                "temperature_K": 600,
                "particles": 10000,
                "batches": 50
            },
            "param_name": "enrichment_pct",
            "param_values": [3.0, 4.0, 5.0]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "run_ids" in data
        assert len(data["run_ids"]) == 3


class TestRunsQuery:
    """Tests for /api/v1/runs endpoint"""
    
    def test_query_runs_no_filter(self):
        """Test querying runs without filter"""
        response = client.get("/api/v1/runs")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "runs" in data
        assert isinstance(data["runs"], list)
    
    def test_query_runs_with_geometry_filter(self):
        """Test querying runs with geometry filter"""
        response = client.get("/api/v1/runs?geometry=PWR")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned runs should match filter
        for run in data["runs"]:
            assert "PWR" in run["geometry"].upper()
    
    def test_query_runs_with_enrichment_range(self):
        """Test querying runs with enrichment range"""
        response = client.get("/api/v1/runs?enrichment_min=3.0&enrichment_max=5.0")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned runs should be in range
        for run in data["runs"]:
            if run["enrichment_pct"] is not None:
                assert 3.0 <= run["enrichment_pct"] <= 5.0
    
    def test_query_runs_with_keff_range(self):
        """Test querying runs with keff range"""
        response = client.get("/api/v1/runs?keff_min=1.0")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned runs should have keff >= 1.0
        for run in data["runs"]:
            assert run["keff"] >= 1.0
    
    def test_query_runs_pagination(self):
        """Test pagination"""
        response1 = client.get("/api/v1/runs?limit=5&offset=0")
        response2 = client.get("/api/v1/runs?limit=5&offset=5")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        assert len(data1["runs"]) <= 5
        assert len(data2["runs"]) <= 5


class TestCompareRuns:
    """Tests for /api/v1/runs/compare endpoint"""
    
    def test_compare_runs_success(self):
        """Test comparing multiple runs"""
        # First create some runs
        spec1 = {
            "geometry": "Test 1",
            "materials": ["UO2"],
            "enrichment_pct": 3.0
        }
        spec2 = {
            "geometry": "Test 2",
            "materials": ["UO2"],
            "enrichment_pct": 5.0
        }
        
        response1 = client.post("/api/v1/studies", json=spec1)
        response2 = client.post("/api/v1/studies", json=spec2)
        
        run_id1 = response1.json()["run_id"]
        run_id2 = response2.json()["run_id"]
        
        # Compare them
        compare_response = client.post("/api/v1/runs/compare", json={
            "run_ids": [run_id1, run_id2]
        })
        
        assert compare_response.status_code == 200
        data = compare_response.json()
        
        assert data["num_runs"] == 2
        assert "keff_values" in data
        assert "keff_mean" in data
        assert "keff_min" in data
        assert "keff_max" in data
        assert "runs" in data
    
    def test_compare_runs_not_found(self):
        """Test comparing non-existent runs"""
        response = client.post("/api/v1/runs/compare", json={
            "run_ids": ["run_notfound1", "run_notfound2"]
        })
        
        assert response.status_code == 404
    
    def test_compare_runs_single_run(self):
        """Test comparing with single run (should fail validation)"""
        response = client.post("/api/v1/runs/compare", json={
            "run_ids": ["run_abc12345"]
        })
        
        assert response.status_code == 422  # Validation error (min_items=2)


# ============================================================================
# STATISTICS TESTS
# ============================================================================

class TestStatistics:
    """Tests for /api/v1/statistics endpoint"""
    
    def test_get_statistics(self):
        """Test getting statistics"""
        response = client.get("/api/v1/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_studies" in data
        assert "total_runs" in data
        assert "completed_runs" in data
        assert "total_queries" in data
        assert "recent_runs" in data
        
        assert isinstance(data["total_studies"], int)
        assert isinstance(data["total_runs"], int)
        assert isinstance(data["recent_runs"], list)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.mark.asyncio
    async def test_full_query_workflow(self):
        """Test complete query workflow"""
        # Submit query
        create_response = client.post("/api/v1/query", json={
            "query": "Simulate PWR pin with 4.5% enriched UO2"
        })
        assert create_response.status_code == 202
        query_id = create_response.json()["query_id"]
        
        # Poll for completion
        max_wait = 30
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_response = client.get(f"/api/v1/query/{query_id}")
            status = status_response.json()["status"]
            
            if status in ["completed", "failed"]:
                break
            
            time.sleep(1)
        
        # Verify final status
        final_response = client.get(f"/api/v1/query/{query_id}")
        final_data = final_response.json()
        
        assert final_data["status"] in ["completed", "failed"]
        
        if final_data["status"] == "completed":
            assert final_data["results"] is not None
    
    def test_direct_tools_workflow(self):
        """Test workflow using direct tool access"""
        # Step 1: Submit study
        study_response = client.post("/api/v1/studies", json={
            "geometry": "Integration test",
            "materials": ["UO2", "Water"],
            "enrichment_pct": 4.5
        })
        assert study_response.status_code == 200
        run_id = study_response.json()["run_id"]
        
        # Step 2: Get study by ID
        get_response = client.get(f"/api/v1/studies/{run_id}")
        assert get_response.status_code == 200
        
        # Step 3: Query for it
        query_response = client.get("/api/v1/runs?geometry=Integration")
        assert query_response.status_code == 200
        assert len(query_response.json()["runs"]) > 0
    
    def test_sweep_and_compare_workflow(self):
        """Test sweep followed by comparison"""
        # Step 1: Submit sweep
        sweep_response = client.post("/api/v1/sweeps", json={
            "base_spec": {
                "geometry": "Sweep test",
                "materials": ["UO2", "Water"],
                "temperature_K": 600
            },
            "param_name": "enrichment_pct",
            "param_values": [3.0, 4.0, 5.0]
        })
        assert sweep_response.status_code == 200
        run_ids = sweep_response.json()["run_ids"]
        
        # Step 2: Compare runs
        compare_response = client.post("/api/v1/runs/compare", json={
            "run_ids": run_ids
        })
        assert compare_response.status_code == 200
        
        comparison = compare_response.json()
        assert comparison["num_runs"] == 3


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Tests for error handling"""
    
    def test_invalid_json(self):
        """Test request with invalid JSON"""
        response = client.post(
            "/api/v1/query",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_required_field(self):
        """Test request with missing required field"""
        response = client.post("/api/v1/query", json={
            "options": {}  # Missing 'query' field
        })
        assert response.status_code == 422
    
    def test_invalid_field_type(self):
        """Test request with invalid field type"""
        response = client.post("/api/v1/studies", json={
            "geometry": "Test",
            "materials": ["UO2"],
            "enrichment_pct": "not a number"  # Should be float
        })
        assert response.status_code == 422


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestValidation:
    """Tests for request validation"""
    
    def test_query_length_validation(self):
        """Test query length validation"""
        # Max length (500 chars)
        max_query = "a" * 500
        response = client.post("/api/v1/query", json={"query": max_query})
        assert response.status_code == 202
        
        # Too long (501 chars)
        too_long = "a" * 501
        response = client.post("/api/v1/query", json={"query": too_long})
        assert response.status_code == 422
    
    def test_study_validation(self):
        """Test study spec validation"""
        # Valid spec
        valid_spec = {
            "geometry": "Test",
            "materials": ["UO2"],
            "enrichment_pct": 4.5,
            "temperature_K": 600,
            "particles": 10000,
            "batches": 50
        }
        response = client.post("/api/v1/studies", json=valid_spec)
        assert response.status_code == 200
        
        # Invalid: negative particles
        invalid_spec = valid_spec.copy()
        invalid_spec["particles"] = -100
        response = client.post("/api/v1/studies", json=invalid_spec)
        assert response.status_code == 422
    
    def test_compare_runs_validation(self):
        """Test compare runs validation"""
        # Valid: 2+ runs
        response = client.post("/api/v1/runs/compare", json={
            "run_ids": ["run_abc12345", "run_def67890"]
        })
        # Will fail with 404 (runs don't exist), but validation passes
        assert response.status_code == 404
        
        # Invalid: < 2 runs
        response = client.post("/api/v1/runs/compare", json={
            "run_ids": ["run_abc12345"]
        })
        assert response.status_code == 422  # Validation error


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.slow
class TestPerformance:
    """Performance tests"""
    
    def test_health_check_performance(self):
        """Test health check response time"""
        start = time.time()
        response = client.get("/api/v1/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1  # Should be very fast
    
    def test_statistics_performance(self):
        """Test statistics response time"""
        start = time.time()
        response = client.get("/api/v1/statistics")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2  # Should be fast
    
    def test_direct_study_performance(self):
        """Test direct study submission performance"""
        start = time.time()
        response = client.post("/api/v1/studies", json={
            "geometry": "Perf test",
            "materials": ["UO2"],
            "enrichment_pct": 4.5
        })
        elapsed = time.time() - start
        
        assert response.status_code == 200
        
        # With mock: < 2s, with real OpenMC: < 10s
        from agent_tools import USE_REAL_OPENMC
        if USE_REAL_OPENMC:
            assert elapsed < 10
        else:
            assert elapsed < 2


# ============================================================================
# RUN WITH PYTEST
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])


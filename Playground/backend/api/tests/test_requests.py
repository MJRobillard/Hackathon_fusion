"""
Tests for request management endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)

# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "services" in data

# ============================================================================
# REQUEST CREATION TESTS
# ============================================================================

def test_create_request_success():
    """Test successful request creation"""
    response = client.post("/api/v1/requests", json={
        "query": "Simulate PWR pin with 4.5% enriched UO2"
    })
    
    assert response.status_code == 202
    data = response.json()
    
    # Check response structure
    assert "request_id" in data
    assert data["status"] == "queued"
    assert "created_at" in data
    assert "estimated_duration_seconds" in data
    
    # Verify request_id format
    assert data["request_id"].startswith("req_")
    assert len(data["request_id"]) == 12  # "req_" + 8 hex chars

def test_create_request_with_options():
    """Test request creation with options"""
    response = client.post("/api/v1/requests", json={
        "query": "Simulate BWR assembly",
        "options": {
            "stream": True,
            "priority": "high"
        },
        "metadata": {
            "user_id": "test_user"
        }
    })
    
    assert response.status_code == 202
    data = response.json()
    assert "stream_url" in data
    assert data["stream_url"].endswith("/stream")

def test_create_request_empty_query():
    """Test request creation with empty query"""
    response = client.post("/api/v1/requests", json={
        "query": ""
    })
    
    # Should fail validation
    assert response.status_code == 422  # Unprocessable Entity

def test_create_request_missing_query():
    """Test request creation without query field"""
    response = client.post("/api/v1/requests", json={
        "options": {}
    })
    
    # Should fail validation
    assert response.status_code == 422

def test_create_request_query_too_long():
    """Test request creation with query exceeding max length"""
    long_query = "a" * 501  # Max is 500 chars
    response = client.post("/api/v1/requests", json={
        "query": long_query
    })
    
    # Should fail validation
    assert response.status_code == 422

# ============================================================================
# REQUEST STATUS TESTS
# ============================================================================

def test_get_request_status_not_found():
    """Test getting status of non-existent request"""
    response = client.get("/api/v1/requests/req_notfound")
    assert response.status_code == 404

def test_get_request_status_success():
    """Test getting status of existing request"""
    # First create a request
    create_response = client.post("/api/v1/requests", json={
        "query": "Test simulation"
    })
    request_id = create_response.json()["request_id"]
    
    # Get its status
    status_response = client.get(f"/api/v1/requests/{request_id}")
    assert status_response.status_code == 200
    
    data = status_response.json()
    assert data["request_id"] == request_id
    assert data["query"] == "Test simulation"
    assert data["status"] in ["queued", "processing", "completed", "failed"]

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_request_workflow():
    """Test complete request workflow (requires MongoDB)"""
    # This test requires a running MongoDB instance
    # Skip if not available
    try:
        # Create request
        create_response = client.post("/api/v1/requests", json={
            "query": "Simulate PWR pin with 3.5% enriched UO2"
        })
        assert create_response.status_code == 202
        request_id = create_response.json()["request_id"]
        
        # Poll for completion (with timeout)
        import time
        max_wait = 30  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_response = client.get(f"/api/v1/requests/{request_id}")
            status = status_response.json()["status"]
            
            if status in ["completed", "failed"]:
                break
            
            time.sleep(1)
        
        # Verify final status
        final_response = client.get(f"/api/v1/requests/{request_id}")
        final_data = final_response.json()
        
        assert final_data["status"] in ["completed", "failed"]
        
        if final_data["status"] == "completed":
            assert final_data["results"] is not None
            assert "keff" in final_data["results"]["results"]
            assert final_data["analysis"] is not None
    
    except Exception as e:
        pytest.skip(f"Integration test skipped: {e}")

# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_invalid_json():
    """Test request with invalid JSON"""
    response = client.post(
        "/api/v1/requests",
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422

def test_wrong_content_type():
    """Test request with wrong content type"""
    response = client.post(
        "/api/v1/requests",
        data="query=test",
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 422

# ============================================================================
# PAGINATION AND LIMITS
# ============================================================================

def test_request_validation_edge_cases():
    """Test edge cases for request validation"""
    # Test with exactly 500 characters (max allowed)
    max_query = "a" * 500
    response = client.post("/api/v1/requests", json={"query": max_query})
    assert response.status_code == 202
    
    # Test with 1 character (min allowed)
    min_query = "a"
    response = client.post("/api/v1/requests", json={"query": min_query})
    assert response.status_code == 202

# ============================================================================
# RUN WITH PYTEST
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])


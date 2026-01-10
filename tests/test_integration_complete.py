"""
Complete integration test: Agent -> Adapter -> OpenMC -> MongoDB

This test validates the entire pipeline working together.
"""

import os
import sys
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, Mock

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "Playground" / "backend"))


class TestCompleteIntegration:
    """Test complete pipeline from agent spec to database storage."""
    
    @pytest.fixture
    def mock_openmc_execution(self):
        """Mock OpenMC execution for systems without it."""
        with patch('aonp.runner.entrypoint.run_simulation') as mock_run:
            mock_run.return_value = 0  # Success
            
            with patch('aonp.core.extractor.extract_results') as mock_extract:
                mock_extract.return_value = {
                    "keff": 1.18456,
                    "keff_std": 0.00234,
                    "keff_uncertainty_pcm": 234.0,
                    "n_batches": 10,
                    "n_inactive": 2,
                    "n_particles": 1000
                }
                
                yield
    
    def test_agent_to_results_pipeline(self, tmp_path, mock_openmc_execution):
        """Test complete pipeline from agent spec to results."""
        from Playground.backend.openmc_adapter import OpenMCAdapter
        
        # Initialize adapter
        adapter = OpenMCAdapter(runs_dir=tmp_path)
        
        # Agent creates simplified spec
        agent_spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "enrichment_pct": 4.5,
            "temperature_K": 900.0,
            "particles": 1000,
            "batches": 10
        }
        
        # Create mock statepoint and manifest
        def setup_mock_outputs(run_dir, spec_hash):
            outputs_dir = run_dir / "outputs"
            outputs_dir.mkdir(exist_ok=True)
            
            # Mock statepoint
            statepoint = outputs_dir / "statepoint.10.h5"
            statepoint.touch()
            
            # Update manifest
            manifest_path = run_dir / "run_manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = json.load(f)
                manifest["runtime_seconds"] = 5.2
                manifest["status"] = "completed"
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f)
        
        # Patch to create mock outputs after bundle creation
        original_create_bundle = adapter.translate_simple_to_openmc
        
        def translate_and_setup(*args, **kwargs):
            study = original_create_bundle(*args, **kwargs)
            return study
        
        with patch.object(adapter, 'translate_simple_to_openmc', side_effect=translate_and_setup):
            # Patch create_run_bundle to add mock outputs
            from aonp.core.bundler import create_run_bundle as original_bundle
            
            def create_bundle_with_mocks(*args, **kwargs):
                run_dir, spec_hash = original_bundle(*args, **kwargs)
                setup_mock_outputs(run_dir, spec_hash)
                return run_dir, spec_hash
            
            with patch('Playground.backend.openmc_adapter.create_run_bundle', side_effect=create_bundle_with_mocks):
                # Execute pipeline
                result = adapter.execute_real_openmc(agent_spec, run_id="integration_test")
        
        # Verify result structure
        assert result["status"] == "completed"
        assert "keff" in result
        assert "keff_std" in result
        assert "run_id" in result
        assert "spec_hash" in result
        
        # Verify keff is in reasonable range
        assert 0.5 < result["keff"] < 2.0
        assert result["keff_std"] > 0
        
        print(f"\n[OK] Complete integration test passed")
        print(f"  Run ID: {result['run_id']}")
        print(f"  k-eff: {result['keff']:.5f} +/- {result['keff_std']:.5f}")
        print(f"  Spec hash: {result['spec_hash'][:12]}...")
    
    def test_parameter_sweep_pipeline(self, tmp_path, mock_openmc_execution):
        """Test parameter sweep through adapter."""
        from Playground.backend.openmc_adapter import OpenMCAdapter
        
        adapter = OpenMCAdapter(runs_dir=tmp_path)
        
        # Base spec
        base_spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "temperature_K": 900.0,
            "particles": 500,
            "batches": 5
        }
        
        enrichments = [3.0, 3.5, 4.0, 4.5, 5.0]
        results = []
        
        def setup_mock_outputs(run_dir, spec_hash):
            outputs_dir = run_dir / "outputs"
            outputs_dir.mkdir(exist_ok=True)
            statepoint = outputs_dir / f"statepoint.05.h5"
            statepoint.touch()
            manifest_path = run_dir / "run_manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = json.load(f)
                manifest["runtime_seconds"] = 1.5
                manifest["status"] = "completed"
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f)
        
        from aonp.core.bundler import create_run_bundle as original_bundle
        
        def create_bundle_with_mocks(*args, **kwargs):
            run_dir, spec_hash = original_bundle(*args, **kwargs)
            setup_mock_outputs(run_dir, spec_hash)
            return run_dir, spec_hash
        
        with patch('Playground.backend.openmc_adapter.create_run_bundle', side_effect=create_bundle_with_mocks):
            for enrichment in enrichments:
                spec = base_spec.copy()
                spec["enrichment_pct"] = enrichment
                
                result = adapter.execute_real_openmc(spec, run_id=f"sweep_{enrichment}")
                results.append(result)
        
        # Verify all runs completed
        assert len(results) == 5
        assert all(r["status"] == "completed" for r in results)
        
        print(f"\n[OK] Parameter sweep test passed")
        print(f"  Completed {len(results)} runs")
        for i, (enr, res) in enumerate(zip(enrichments, results)):
            print(f"  {enr}%: k-eff = {res['keff']:.5f}")
    
    def test_mongodb_storage_pipeline(self, tmp_path, mock_openmc_execution):
        """Test storing results in MongoDB (if available)."""
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            pytest.skip("MONGO_URI not set - skipping MongoDB test")
        
        from pymongo import MongoClient
        from Playground.backend.openmc_adapter import OpenMCAdapter
        
        # Setup MongoDB
        client = MongoClient(mongo_uri)
        db = client["aonp_test"]
        
        # Clear test data
        db["studies"].delete_many({})
        db["runs"].delete_many({})
        db["summaries"].delete_many({})
        
        try:
            adapter = OpenMCAdapter(runs_dir=tmp_path)
            
            agent_spec = {
                "geometry": "PWR pin cell",
                "materials": ["UO2", "Water"],
                "enrichment_pct": 4.5,
                "temperature_K": 900.0,
                "particles": 500,
                "batches": 5
            }
            
            # Setup mock outputs
            def setup_mock_outputs(run_dir, spec_hash):
                outputs_dir = run_dir / "outputs"
                outputs_dir.mkdir(exist_ok=True)
                statepoint = outputs_dir / "statepoint.05.h5"
                statepoint.touch()
                manifest_path = run_dir / "run_manifest.json"
                if manifest_path.exists():
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                    manifest["runtime_seconds"] = 2.0
                    manifest["status"] = "completed"
                    with open(manifest_path, 'w') as f:
                        json.dump(manifest, f)
            
            from aonp.core.bundler import create_run_bundle as original_bundle
            
            def create_bundle_with_mocks(*args, **kwargs):
                run_dir, spec_hash = original_bundle(*args, **kwargs)
                setup_mock_outputs(run_dir, spec_hash)
                return run_dir, spec_hash
            
            with patch('Playground.backend.openmc_adapter.create_run_bundle', side_effect=create_bundle_with_mocks):
                result = adapter.execute_real_openmc(agent_spec, run_id="mongo_test")
            
            # Store in MongoDB
            run_record = {
                "run_id": result["run_id"],
                "spec_hash": result["spec_hash"],
                "status": result["status"],
                "created_at": datetime.now(timezone.utc)
            }
            db["runs"].insert_one(run_record)
            
            summary_record = {
                "run_id": result["run_id"],
                "spec_hash": result["spec_hash"],
                "keff": result["keff"],
                "keff_std": result["keff_std"],
                "runtime_seconds": result["runtime_seconds"],
                "status": result["status"],
                "created_at": datetime.now(timezone.utc),
                "spec": agent_spec
            }
            db["summaries"].insert_one(summary_record)
            
            # Verify storage
            stored_run = db["runs"].find_one({"run_id": result["run_id"]})
            assert stored_run is not None
            
            stored_summary = db["summaries"].find_one({"run_id": result["run_id"]})
            assert stored_summary is not None
            assert stored_summary["keff"] == result["keff"]
            
            print(f"\n[OK] MongoDB storage test passed")
            print(f"  Stored run: {result['run_id']}")
            print(f"  Collections: runs, summaries")
            
        finally:
            # Cleanup
            db["studies"].delete_many({})
            db["runs"].delete_many({})
            db["summaries"].delete_many({})
    
    def test_error_handling(self, tmp_path):
        """Test error handling in pipeline."""
        from Playground.backend.openmc_adapter import OpenMCAdapter
        
        adapter = OpenMCAdapter(runs_dir=tmp_path)
        
        # Invalid spec (missing materials)
        invalid_spec = {
            "geometry": "PWR pin cell",
            "materials": [],  # Empty!
            "enrichment_pct": 4.5,
            "temperature_K": 900.0,
            "particles": 100,
            "batches": 5
        }
        
        result = adapter.execute_real_openmc(invalid_spec, run_id="error_test")
        
        # Should return error status
        assert result["status"] == "failed"
        assert "error" in result
        
        print(f"\n[OK] Error handling test passed")
        print(f"  Error detected: {result['error'][:50]}...")


def run_integration_tests():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("COMPLETE INTEGRATION TESTS")
    print("="*80 + "\n")
    
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s"
    ])
    
    return exit_code


if __name__ == "__main__":
    exit_code = run_integration_tests()
    sys.exit(exit_code)


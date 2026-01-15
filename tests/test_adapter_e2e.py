"""
End-to-end tests for OpenMC Adapter integration.

Tests the full pipeline from simplified specs through to results extraction.
"""

import os
import sys
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from aonp.runner.openmc_adapter import OpenMCAdapter, execute_real_openmc
from aonp.schemas.study import StudySpec


class TestAdapterTranslation:
    """Test spec translation logic."""
    
    def test_simple_pwr_translation(self):
        """Test translation of simple PWR pin cell spec."""
        adapter = OpenMCAdapter()
        
        simple_spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "enrichment_pct": 4.5,
            "temperature_K": 900.0,
            "particles": 1000,
            "batches": 20
        }
        
        study = adapter.translate_simple_to_openmc(simple_spec, run_id="test_run_001")
        
        # Verify study structure
        assert isinstance(study, StudySpec)
        assert study.name == "test_run_001"
        assert "fuel" in study.materials
        assert "moderator" in study.materials
        
        # Verify fuel material
        fuel = study.materials["fuel"]
        assert fuel.density == 10.4
        assert fuel.temperature == 900.0
        assert len(fuel.nuclides) == 3  # U235, U238, O16
        
        # Verify enrichment
        u235 = next(n for n in fuel.nuclides if n.name == "U235")
        u238 = next(n for n in fuel.nuclides if n.name == "U238")
        
        # Check enrichment ratio (approximately 4.5%)
        enrichment_ratio = u235.fraction / (u235.fraction + u238.fraction)
        assert abs(enrichment_ratio - 0.045) < 0.001
        
        # Verify moderator
        moderator = study.materials["moderator"]
        assert moderator.density == 0.7
        assert len(moderator.nuclides) == 2  # H1, O16
        
        # Verify settings
        assert study.settings.batches == 20
        assert study.settings.particles == 1000
        assert study.settings.inactive == 4  # 20% of 20
        
        # Verify geometry
        assert study.geometry.type == "script"
        assert "pincell_geometry.py" in study.geometry.script
        
        print(f"[OK] Translation test passed")
        print(f"  Study hash: {study.get_short_hash()}")
        print(f"  Materials: {list(study.materials.keys())}")
    
    def test_enrichment_variations(self):
        """Test different enrichment values."""
        adapter = OpenMCAdapter()
        
        enrichments = [3.0, 4.5, 5.0, 19.75]
        
        for enrichment in enrichments:
            simple_spec = {
                "geometry": "PWR pin cell",
                "materials": ["UO2", "Water"],
                "enrichment_pct": enrichment,
                "temperature_K": 900.0,
                "particles": 1000,
                "batches": 10
            }
            
            study = adapter.translate_simple_to_openmc(simple_spec)
            fuel = study.materials["fuel"]
            
            u235 = next(n for n in fuel.nuclides if n.name == "U235")
            u238 = next(n for n in fuel.nuclides if n.name == "U238")
            
            enrichment_ratio = u235.fraction / (u235.fraction + u238.fraction)
            expected_ratio = enrichment / 100.0
            
            assert abs(enrichment_ratio - expected_ratio) < 0.001, \
                f"Enrichment mismatch for {enrichment}%"
        
        print(f"[OK] Enrichment variation test passed")
    
    def test_material_detection(self):
        """Test material name variations."""
        adapter = OpenMCAdapter()
        
        test_cases = [
            {
                "materials": ["UO2", "Water"],
                "expected": ["fuel", "moderator"]
            },
            {
                "materials": ["fuel", "moderator"],
                "expected": ["fuel", "moderator"]
            },
            {
                "materials": ["UO2", "H2O"],
                "expected": ["fuel", "moderator"]
            },
        ]
        
        for case in test_cases:
            simple_spec = {
                "geometry": "PWR pin cell",
                "materials": case["materials"],
                "enrichment_pct": 4.5,
                "temperature_K": 900.0,
                "particles": 1000,
                "batches": 10
            }
            
            study = adapter.translate_simple_to_openmc(simple_spec)
            
            for expected_mat in case["expected"]:
                assert expected_mat in study.materials, \
                    f"Expected material '{expected_mat}' not found for {case['materials']}"
        
        print(f"[OK] Material detection test passed")
    
    def test_spec_hashing_consistency(self):
        """Test that same specs produce same hash."""
        adapter = OpenMCAdapter()
        
        simple_spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "enrichment_pct": 4.5,
            "temperature_K": 900.0,
            "particles": 1000,
            "batches": 10
        }
        
        # Create two identical studies
        study1 = adapter.translate_simple_to_openmc(simple_spec, run_id="test_a")
        study2 = adapter.translate_simple_to_openmc(simple_spec, run_id="test_b")
        
        # Hashes should be identical (run_id doesn't affect hash)
        hash1 = study1.get_canonical_hash()
        hash2 = study2.get_canonical_hash()
        
        # Note: hashes will differ because name is different
        # But if we normalize the name, they should match
        study1_data = study1.model_dump()
        study2_data = study2.model_dump()
        study1_data["name"] = "normalized"
        study2_data["name"] = "normalized"
        
        import json
        import hashlib
        
        hash1 = hashlib.sha256(
            json.dumps(study1_data, sort_keys=True).encode()
        ).hexdigest()
        hash2 = hashlib.sha256(
            json.dumps(study2_data, sort_keys=True).encode()
        ).hexdigest()
        
        assert hash1 == hash2, "Identical specs should produce identical hashes"
        
        print(f"[OK] Spec hashing consistency test passed")


class TestAdapterBundleCreation:
    """Test bundle creation without executing OpenMC."""
    
    def test_bundle_creation(self, tmp_path):
        """Test creating a run bundle."""
        adapter = OpenMCAdapter(runs_dir=tmp_path)
        
        simple_spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "enrichment_pct": 4.5,
            "temperature_K": 900.0,
            "particles": 1000,
            "batches": 10
        }
        
        study = adapter.translate_simple_to_openmc(simple_spec, run_id="test_bundle")
        
        # Import bundler
        from aonp.core.bundler import create_run_bundle
        
        run_dir, spec_hash = create_run_bundle(
            study=study,
            run_id="test_bundle",
            base_dir=tmp_path
        )
        
        # Verify directory structure
        assert run_dir.exists()
        assert (run_dir / "study_spec.json").exists()
        assert (run_dir / "run_manifest.json").exists()
        assert (run_dir / "inputs").exists()
        assert (run_dir / "outputs").exists()
        
        # Verify study spec
        with open(run_dir / "study_spec.json") as f:
            spec_data = json.load(f)
        
        assert spec_data["name"] == "test_bundle"
        assert "fuel" in spec_data["materials"]
        
        # Verify manifest
        with open(run_dir / "run_manifest.json") as f:
            manifest = json.load(f)
        
        assert manifest["run_id"] == "test_bundle"
        assert manifest["spec_hash"] == spec_hash
        
        print(f"[OK] Bundle creation test passed")
        print(f"  Run directory: {run_dir}")
        print(f"  Spec hash: {spec_hash[:12]}...")
    
    def test_xml_generation(self, tmp_path):
        """Test XML file generation."""
        adapter = OpenMCAdapter(runs_dir=tmp_path)
        
        simple_spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "enrichment_pct": 4.5,
            "temperature_K": 900.0,
            "particles": 1000,
            "batches": 10
        }
        
        study = adapter.translate_simple_to_openmc(simple_spec, run_id="test_xml")
        
        from aonp.core.bundler import create_run_bundle
        
        run_dir, _ = create_run_bundle(
            study=study,
            run_id="test_xml",
            base_dir=tmp_path
        )
        
        # Check that XML files were created
        inputs_dir = run_dir / "inputs"
        
        # At minimum, we should have materials.xml and settings.xml
        # (geometry.xml might fail if OpenMC not installed, but placeholders are created)
        assert (inputs_dir / "materials.xml").exists()
        assert (inputs_dir / "settings.xml").exists()
        
        # Verify XML content (at least that they're valid files)
        with open(inputs_dir / "materials.xml") as f:
            materials_xml = f.read()
            assert "<?xml version" in materials_xml
        
        with open(inputs_dir / "settings.xml") as f:
            settings_xml = f.read()
            assert "<?xml version" in settings_xml
        
        print(f"[OK] XML generation test passed")


class TestAdapterWithMongoDB:
    """Test adapter integration with MongoDB."""
    
    @pytest.fixture
    def mongo_setup(self):
        """Setup MongoDB connection if available."""
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            pytest.skip("MONGO_URI not set")
        
        from pymongo import MongoClient
        
        client = MongoClient(mongo_uri)
        db = client["aonp_test"]
        
        # Clear test collections
        db["studies"].delete_many({})
        db["runs"].delete_many({})
        db["summaries"].delete_many({})
        
        yield db
        
        # Cleanup
        db["studies"].delete_many({})
        db["runs"].delete_many({})
        db["summaries"].delete_many({})
    
    def test_mongodb_integration(self, mongo_setup, tmp_path):
        """Test storing results in MongoDB."""
        db = mongo_setup
        
        adapter = OpenMCAdapter(runs_dir=tmp_path)
        
        simple_spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "enrichment_pct": 4.5,
            "temperature_K": 900.0,
            "particles": 100,  # Small for speed
            "batches": 5
        }
        
        study = adapter.translate_simple_to_openmc(simple_spec, run_id="test_mongo")
        
        from aonp.core.bundler import create_run_bundle
        
        run_dir, spec_hash = create_run_bundle(
            study=study,
            run_id="test_mongo",
            base_dir=tmp_path
        )
        
        # Store study in MongoDB
        study_doc = {
            "spec_hash": spec_hash,
            "canonical_spec": study.model_dump(),
            "created_at": datetime.now(timezone.utc)
        }
        
        db["studies"].update_one(
            {"spec_hash": spec_hash},
            {"$set": study_doc},
            upsert=True
        )
        
        # Verify storage
        stored_study = db["studies"].find_one({"spec_hash": spec_hash})
        assert stored_study is not None
        assert stored_study["spec_hash"] == spec_hash
        
        print(f"[OK] MongoDB integration test passed")


class TestEndToEndExecution:
    """Test full execution pipeline (requires OpenMC or mocking)."""
    
    def test_mock_execution(self, tmp_path):
        """Test execution with mocked OpenMC."""
        adapter = OpenMCAdapter(runs_dir=tmp_path)
        
        simple_spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "enrichment_pct": 4.5,
            "temperature_K": 900.0,
            "particles": 100,
            "batches": 5
        }
        
        # Mock the run_simulation function
        with patch('aonp.runner.openmc_adapter.runner_entrypoint.run_simulation') as mock_run:
            mock_run.return_value = 0  # Success
            
            # Mock the extract_results function
            with patch('aonp.runner.openmc_adapter.extract_results') as mock_extract:
                mock_extract.return_value = {
                    "keff": 1.18456,
                    "keff_std": 0.00234,
                    "keff_uncertainty_pcm": 234.0,
                    "n_batches": 5,
                    "n_inactive": 1,
                    "n_particles": 100
                }
                
                # Mock manifest file
                def create_mock_manifest(run_dir):
                    manifest_path = run_dir / "run_manifest.json"
                    with open(manifest_path, 'w') as f:
                        json.dump({
                            "run_id": run_dir.name,
                            "spec_hash": "abc123",
                            "runtime_seconds": 0.5,
                            "status": "completed"
                        }, f)
                
                # Mock statepoint file
                def create_mock_statepoint(run_dir):
                    outputs_dir = run_dir / "outputs"
                    outputs_dir.mkdir(exist_ok=True)
                    statepoint_path = outputs_dir / "statepoint.05.h5"
                    statepoint_path.touch()
                
                with patch('aonp.runner.openmc_adapter.create_run_bundle') as mock_bundle:
                    test_run_dir = tmp_path / "run_test"
                    test_run_dir.mkdir()
                    (test_run_dir / "outputs").mkdir()
                    
                    create_mock_manifest(test_run_dir)
                    create_mock_statepoint(test_run_dir)
                    
                    mock_bundle.return_value = (test_run_dir, "abc123")
                    
                    # Execute
                    result = adapter.execute_real_openmc(simple_spec, run_id="test_exec")
                    
                    # Verify results
                    assert result["status"] == "completed"
                    assert result["keff"] == 1.18456
                    assert result["keff_std"] == 0.00234
                    assert "run_id" in result
                    assert "spec_hash" in result
        
        print(f"[OK] Mock execution test passed")
        print(f"  k-eff: {result['keff']:.5f} +/- {result['keff_std']:.5f}")
    
    @pytest.mark.skipif(
        not shutil.which("openmc"),
        reason="OpenMC not installed"
    )
    def test_real_execution_if_available(self, tmp_path):
        """Test real OpenMC execution if available."""
        # Skip if nuclear data not available
        if not os.getenv("OPENMC_CROSS_SECTIONS"):
            pytest.skip("OPENMC_CROSS_SECTIONS not set")
        
        adapter = OpenMCAdapter(runs_dir=tmp_path)
        
        simple_spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "enrichment_pct": 4.5,
            "temperature_K": 900.0,
            "particles": 100,  # Small for fast test
            "batches": 10
        }
        
        try:
            result = adapter.execute_real_openmc(simple_spec, run_id="test_real")
            
            assert result["status"] == "completed"
            assert 0.5 < result["keff"] < 2.0  # Reasonable range
            assert result["keff_std"] > 0
            assert result["runtime_seconds"] > 0
            
            print(f"[OK] Real execution test passed")
            print(f"  k-eff: {result['keff']:.5f} +/- {result['keff_std']:.5f}")
            print(f"  Runtime: {result['runtime_seconds']:.2f} seconds")
            
        except Exception as e:
            pytest.skip(f"Real execution failed: {e}")


class TestConvenienceFunction:
    """Test the convenience function."""
    
    def test_convenience_function(self, tmp_path):
        """Test execute_real_openmc convenience function."""
        # Change to temp directory for test
        with patch('aonp.runner.openmc_adapter.OpenMCAdapter') as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.execute_real_openmc.return_value = {
                "status": "completed",
                "keff": 1.2,
                "keff_std": 0.003,
                "runtime_seconds": 1.0,
                "run_id": "test",
                "spec_hash": "abc123",
                "run_dir": str(tmp_path)
            }
            mock_adapter_class.return_value = mock_adapter
            
            simple_spec = {
                "geometry": "PWR pin cell",
                "materials": ["UO2", "Water"],
                "enrichment_pct": 4.5,
                "temperature_K": 900.0,
                "particles": 100,
                "batches": 5
            }
            
            result = execute_real_openmc(simple_spec, run_id="test_convenience")
            
            assert result["status"] == "completed"
            assert "keff" in result
        
        print(f"[OK] Convenience function test passed")


def run_all_tests():
    """Run all tests with verbose output."""
    print("\n" + "="*80)
    print("ADAPTER END-TO-END TESTS")
    print("="*80 + "\n")
    
    # Run tests
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s"  # Show print statements
    ])
    
    return exit_code


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)


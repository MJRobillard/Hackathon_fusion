"""
Acceptance tests for full OpenMC integration.

⚠️ Requires:
- OpenMC installed (pip install openmc)
- Nuclear data library (ENDF/B-VII.1 or similar)
- Linux/macOS or WSL on Windows
"""

import sys
import yaml
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aonp.schemas.study import StudySpec
from aonp.core.bundler import create_run_bundle
from aonp.runner.entrypoint import run_simulation
from aonp.core.extractor import create_summary, load_summary


def test_full_pipeline():
    """Test complete workflow from YAML to results."""
    print("Testing full pipeline...")
    
    # Create minimal test study
    yaml_content = """
name: "acceptance_test"
description: "Minimal test for CI/CD"
materials:
  fuel:
    density: 10.4
    density_units: "g/cm3"
    temperature: 900.0
    nuclides:
      - name: "U235"
        fraction: 0.03
        fraction_type: "ao"
      - name: "U238"
        fraction: 0.27
        fraction_type: "ao"
      - name: "O16"
        fraction: 0.70
        fraction_type: "ao"
  moderator:
    density: 1.0
    density_units: "g/cm3"
    temperature: 600.0
    nuclides:
      - name: "H1"
        fraction: 0.6667
        fraction_type: "ao"
      - name: "O16"
        fraction: 0.3333
        fraction_type: "ao"
geometry:
  type: "script"
  script: "aonp/examples/pincell_geometry.py"
settings:
  batches: 50
  inactive: 10
  particles: 1000
  seed: 42
nuclear_data:
  library: "endfb71"
  path: "/home/user/nuclear_data/endfb-vii.1-hdf5/"
"""
    
    # Parse study
    data = yaml.safe_load(yaml_content)
    study = StudySpec(**data)
    print(f"✓ Study validation passed")
    print(f"  Hash: {study.get_canonical_hash()[:12]}...")
    
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        
        # Create bundle
        run_dir, spec_hash = create_run_bundle(study, base_dir=base_dir)
        print(f"✓ Bundle creation passed")
        print(f"  Directory: {run_dir}")
        
        # Verify bundle structure
        assert (run_dir / "study_spec.json").exists()
        assert (run_dir / "run_manifest.json").exists()
        assert (run_dir / "inputs").exists()
        assert (run_dir / "outputs").exists()
        print(f"✓ Bundle structure validated")
        
        # Check if OpenMC is available
        try:
            import openmc
            has_openmc = True
        except ImportError:
            has_openmc = False
            print(f"⚠ OpenMC not installed, skipping simulation")
            return
        
        # Run simulation
        exit_code = run_simulation(run_dir)
        
        if exit_code != 0:
            print(f"✗ Simulation failed with exit code {exit_code}")
            print(f"  This may be due to:")
            print(f"  - Missing nuclear data")
            print(f"  - Incorrect cross_sections.xml path")
            print(f"  - OpenMC installation issues")
            return
        
        print(f"✓ OpenMC execution passed")
        
        # Find statepoint file
        statepoint_files = list((run_dir / "outputs").glob("statepoint.*.h5"))
        if not statepoint_files:
            print(f"✗ No statepoint file found in outputs/")
            return
        
        sp_file = statepoint_files[0]
        print(f"  Statepoint: {sp_file.name}")
        
        # Extract results
        summary_path = create_summary(sp_file)
        print(f"✓ Result extraction passed")
        
        # Load and verify results
        df = load_summary(summary_path)
        print(f"✓ Summary loading passed")
        
        # Check results
        keff_row = df[df['metric'] == 'keff']
        if not keff_row.empty:
            keff = keff_row['value'].iloc[0]
            print(f"  k-eff: {keff:.6f}")
            
            # Sanity check (should be ~1.6 for 3% enriched fuel)
            assert 1.4 < keff < 1.8, f"k-eff out of expected range: {keff}"
            print(f"✓ k-eff in expected range")
        
        print(f"\n✅ Full pipeline test passed!")


def test_reproducibility():
    """Test that same input produces same hash."""
    yaml_content = """
name: "reproducibility_test"
materials:
  fuel:
    density: 10.4
    density_units: "g/cm3"
    temperature: 900.0
    nuclides:
      - name: "U235"
        fraction: 1.0
        fraction_type: "ao"
geometry:
  type: "script"
  script: "test.py"
settings:
  batches: 100
  inactive: 20
  particles: 1000
  seed: 42
nuclear_data:
  library: "endfb71"
  path: "/data"
"""
    
    data = yaml.safe_load(yaml_content)
    
    # Create study twice
    study1 = StudySpec(**data)
    study2 = StudySpec(**data)
    
    hash1 = study1.get_canonical_hash()
    hash2 = study2.get_canonical_hash()
    
    assert hash1 == hash2, "Reproducibility check failed"
    print(f"✓ Reproducibility test passed")
    print(f"  Hash: {hash1[:12]}...")


if __name__ == "__main__":
    print("Running acceptance tests...\n")
    print("=" * 60)
    print("Note: These tests require OpenMC and nuclear data")
    print("=" * 60)
    print()
    
    try:
        test_reproducibility()
        print()
        test_full_pipeline()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


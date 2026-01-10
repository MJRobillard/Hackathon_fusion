#!/usr/bin/env python3
"""
Test script to verify OpenMC installation and functionality.

This script checks:
1. OpenMC module can be imported
2. Version information
3. Nuclear data availability
4. Basic geometry creation
5. Simple simulation execution (if data available)
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def check_openmc_import():
    """Check if OpenMC can be imported."""
    print("=" * 60)
    print("1. Checking OpenMC Import")
    print("=" * 60)
    
    try:
        import openmc
        print(f"[OK] OpenMC successfully imported")
        print(f"     Version: {openmc.__version__}")
        return True, openmc
    except ImportError as e:
        print(f"[ERROR] Cannot import OpenMC: {e}")
        print(f"        Install with: pip install openmc")
        print(f"        Note: Requires Linux/macOS or WSL on Windows")
        return False, None


def check_nuclear_data(openmc):
    """Check nuclear data availability."""
    print("\n" + "=" * 60)
    print("2. Checking Nuclear Data")
    print("=" * 60)
    
    try:
        # Check for cross_sections environment variable
        import os
        cross_sections = os.environ.get('OPENMC_CROSS_SECTIONS')
        
        if cross_sections:
            print(f"[OK] OPENMC_CROSS_SECTIONS set")
            print(f"     Path: {cross_sections}")
            
            if Path(cross_sections).exists():
                print(f"[OK] Cross sections file exists")
                return True
            else:
                print(f"[WARNING] Cross sections file not found at path")
                return False
        else:
            print(f"[WARNING] OPENMC_CROSS_SECTIONS not set")
            print(f"          Set with: export OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error checking nuclear data: {e}")
        return False


def test_basic_geometry(openmc):
    """Test basic geometry creation."""
    print("\n" + "=" * 60)
    print("3. Testing Geometry Creation")
    print("=" * 60)
    
    try:
        # Create simple sphere
        sphere = openmc.Sphere(r=1.0, boundary_type='vacuum')
        print(f"[OK] Created sphere surface")
        
        # Create cell
        cell = openmc.Cell()
        cell.region = -sphere
        print(f"[OK] Created cell")
        
        # Create universe
        universe = openmc.Universe(cells=[cell])
        print(f"[OK] Created universe")
        
        # Create geometry
        geometry = openmc.Geometry(universe)
        print(f"[OK] Created geometry")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Geometry creation failed: {e}")
        return False


def test_material_creation(openmc):
    """Test material creation."""
    print("\n" + "=" * 60)
    print("4. Testing Material Creation")
    print("=" * 60)
    
    try:
        # Create simple material
        mat = openmc.Material(name='water')
        mat.set_density('g/cm3', 1.0)
        mat.add_nuclide('H1', 2.0)
        mat.add_nuclide('O16', 1.0)
        print(f"[OK] Created water material")
        
        # Create materials collection
        materials = openmc.Materials([mat])
        print(f"[OK] Created materials collection")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Material creation failed: {e}")
        return False


def test_aonp_integration():
    """Test AONP integration."""
    print("\n" + "=" * 60)
    print("5. Testing AONP Integration")
    print("=" * 60)
    
    try:
        from aonp.schemas.study import StudySpec
        import yaml
        
        # Try to load example study
        example_file = Path("aonp/examples/simple_pincell.yaml")
        if not example_file.exists():
            print(f"[WARNING] Example file not found: {example_file}")
            return False
        
        with open(example_file) as f:
            data = yaml.safe_load(f)
        
        study = StudySpec(**data)
        print(f"[OK] Loaded example study")
        print(f"     Name: {study.name}")
        print(f"     Hash: {study.get_canonical_hash()[:12]}...")
        
        # Test bundle creation
        from aonp.core.bundler import create_run_bundle
        run_dir, spec_hash = create_run_bundle(study)
        print(f"[OK] Created run bundle")
        print(f"     Directory: {run_dir}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] AONP integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_simulation(openmc):
    """Test a very simple simulation."""
    print("\n" + "=" * 60)
    print("6. Testing Simple Simulation (Optional)")
    print("=" * 60)
    
    # Check if nuclear data is available
    import os
    if not os.environ.get('OPENMC_CROSS_SECTIONS'):
        print(f"[SKIP] No nuclear data available, skipping simulation")
        return True
    
    try:
        import tempfile
        import shutil
        
        # Create temporary directory
        tmpdir = Path(tempfile.mkdtemp())
        print(f"[INFO] Using temporary directory: {tmpdir}")
        
        # Create very simple geometry
        sphere = openmc.Sphere(r=10.0, boundary_type='vacuum')
        cell = openmc.Cell()
        
        # Create material
        mat = openmc.Material()
        mat.set_density('g/cm3', 1.0)
        mat.add_nuclide('U235', 1.0)
        mat.temperature = 900.0
        
        cell.fill = mat
        cell.region = -sphere
        
        universe = openmc.Universe(cells=[cell])
        geometry = openmc.Geometry(universe)
        
        # Create materials
        materials = openmc.Materials([mat])
        
        # Create settings
        settings = openmc.Settings()
        settings.batches = 10
        settings.inactive = 2
        settings.particles = 100
        settings.seed = 1
        
        # Set source
        import openmc.stats
        settings.source = openmc.IndependentSource(
            space=openmc.stats.Point((0, 0, 0))
        )
        
        # Export
        geometry.export_to_xml(tmpdir / 'geometry.xml')
        materials.export_to_xml(tmpdir / 'materials.xml')
        settings.export_to_xml(tmpdir / 'settings.xml')
        
        print(f"[OK] Created XML input files")
        
        # Try to run (this will fail if nuclear data is wrong)
        print(f"[INFO] Attempting to run simulation...")
        print(f"       (This may take 10-30 seconds)")
        
        openmc.run(cwd=str(tmpdir), output=False)
        
        print(f"[OK] Simulation completed!")
        
        # Clean up
        shutil.rmtree(tmpdir)
        
        return True
        
    except Exception as e:
        print(f"[WARNING] Simulation test failed: {e}")
        print(f"          This is expected if nuclear data is not properly configured")
        return False


def main():
    """Main test function."""
    print("OpenMC Installation Test")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: Import
    success, openmc = check_openmc_import()
    results.append(("OpenMC Import", success))
    
    if not success:
        print("\n" + "=" * 60)
        print("RESULT: OpenMC not available")
        print("=" * 60)
        print("\nTo install OpenMC:")
        print("  Linux/WSL: pip install openmc")
        print("  Conda:     conda install -c conda-forge openmc")
        print("\nSee INSTALL.md for detailed instructions")
        return 1
    
    # Test 2: Nuclear data
    has_data = check_nuclear_data(openmc)
    results.append(("Nuclear Data", has_data))
    
    # Test 3: Geometry
    geom_ok = test_basic_geometry(openmc)
    results.append(("Geometry Creation", geom_ok))
    
    # Test 4: Materials
    mat_ok = test_material_creation(openmc)
    results.append(("Material Creation", mat_ok))
    
    # Test 5: AONP
    aonp_ok = test_aonp_integration()
    results.append(("AONP Integration", aonp_ok))
    
    # Test 6: Simulation (optional)
    if has_data:
        sim_ok = test_simple_simulation(openmc)
        results.append(("Simple Simulation", sim_ok))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {name}")
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    print()
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        print("\nOpenMC is ready to use with AONP.")
        return 0
    elif passed >= 5:
        print("\n[PARTIAL] Core functionality works")
        print("\nYou can use AONP for study validation and bundle creation.")
        print("For simulations, ensure nuclear data is properly configured.")
        return 0
    else:
        print("\n[FAIL] Some tests failed")
        print("\nSee error messages above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


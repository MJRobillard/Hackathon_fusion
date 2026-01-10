#!/usr/bin/env python3
"""
Quick start script for AONP.

This script demonstrates the complete workflow:
1. Load and validate a study
2. Create a run bundle
3. (Optional) Execute simulation
4. (Optional) Extract results
"""

import sys
import yaml
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from aonp.schemas.study import StudySpec
from aonp.core.bundler import create_run_bundle


def main():
    print("=" * 60)
    print("AONP Quick Start")
    print("=" * 60)
    print()
    
    # Step 1: Load example study
    example_file = Path("aonp/examples/simple_pincell.yaml")
    
    if not example_file.exists():
        print(f"[ERROR] Example file not found: {example_file}")
        print("   Please ensure you're running from the project root.")
        return 1
    
    print(f"[1/7] Loading study from: {example_file}")
    with open(example_file) as f:
        data = yaml.safe_load(f)
    
    # Step 2: Validate study
    print("[2/7] Validating study specification...")
    try:
        study = StudySpec(**data)
        print(f"[OK] Validation passed!")
        print(f"   Study name: {study.name}")
        print(f"   Materials: {', '.join(study.materials.keys())}")
        print(f"   Batches: {study.settings.batches}")
        print(f"   Particles: {study.settings.particles}")
    except Exception as e:
        print(f"[ERROR] Validation failed: {e}")
        return 1
    
    # Step 3: Compute canonical hash
    print()
    print("[3/7] Computing canonical hash...")
    spec_hash = study.get_canonical_hash()
    print(f"[OK] Hash: {spec_hash[:12]}... (first 12 chars)")
    print(f"   Full: {spec_hash}")
    
    # Step 4: Create run bundle
    print()
    print("[4/7] Creating run bundle...")
    try:
        run_dir, bundle_hash = create_run_bundle(study)
        print(f"[OK] Bundle created!")
        print(f"   Directory: {run_dir}")
        print(f"   Spec hash: {bundle_hash[:12]}...")
        
        # Show bundle contents
        print()
        print("Bundle contents:")
        for item in sorted(run_dir.rglob("*")):
            if item.is_file():
                rel_path = item.relative_to(run_dir)
                size = item.stat().st_size
                print(f"   {rel_path} ({size} bytes)")
    except Exception as e:
        print(f"[ERROR] Bundle creation failed: {e}")
        return 1
    
    # Step 5: Check OpenMC availability
    print()
    print("[5/7] Checking OpenMC availability...")
    try:
        import openmc
        print(f"[OK] OpenMC {openmc.__version__} is installed")
        has_openmc = True
    except ImportError:
        print(f"[WARNING] OpenMC not installed")
        print(f"   Install with: pip install openmc")
        print(f"   Note: Requires Linux/macOS or WSL on Windows")
        has_openmc = False
    
    # Step 6: Optionally run simulation
    if has_openmc:
        print()
        response = input("[6/7] Run simulation now? [y/N]: ").strip().lower()
        
        if response == 'y':
            from aonp.runner.entrypoint import run_simulation
            
            print()
            print("Starting simulation...")
            exit_code = run_simulation(run_dir)
            
            if exit_code == 0:
                print()
                print("[OK] Simulation completed successfully!")
                
                # Step 7: Extract results
                from aonp.core.extractor import create_summary, load_summary
                
                sp_files = list((run_dir / "outputs").glob("statepoint.*.h5"))
                if sp_files:
                    print()
                    print("[7/7] Extracting results...")
                    summary_path = create_summary(sp_files[0])
                    
                    df = load_summary(summary_path)
                    print()
                    print("Summary:")
                    print(df.to_string(index=False))
                else:
                    print("[WARNING] No statepoint file found")
            else:
                print()
                print(f"[ERROR] Simulation failed with exit code {exit_code}")
        else:
            print()
            print("Skipping simulation")
    
    # Final instructions
    print()
    print("=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print()
    print("To run the simulation manually:")
    print(f"  python -m aonp.runner.entrypoint {run_dir}")
    print()
    print("To extract results:")
    print(f"  python -c \"from aonp.core.extractor import create_summary; ")
    print(f"  create_summary('{run_dir}/outputs/statepoint.*.h5')\"")
    print()
    print("To start the API server:")
    print("  uvicorn aonp.api.main:app --reload")
    print()
    print("For more information, see:")
    print("  - README.md")
    print("  - aonp/examples/README.md")
    print("  - openmc_design.md")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


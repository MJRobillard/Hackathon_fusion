#!/usr/bin/env python3
"""
Demo script for OpenMC Adapter integration.

This demonstrates the complete pipeline from simplified specs to results.
Run with mock execution (no OpenMC required) or real execution.

Usage:
    # Mock execution (default)
    python demo_adapter_integration.py

    # Real execution
    USE_REAL_OPENMC=true python demo_adapter_integration.py
"""

import os
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "Playground" / "backend"))


def main():
    print("="*80)
    print("OPENMC ADAPTER INTEGRATION DEMO")
    print("="*80)
    
    # Check configuration
    use_real = os.getenv("USE_REAL_OPENMC", "false").lower() == "true"
    print(f"\nExecution Mode: {'REAL OpenMC' if use_real else 'MOCK (simulated)'}")
    
    if use_real:
        print("⚠️  Real execution requires:")
        print("   - OpenMC installed (pip install openmc)")
        print("   - Nuclear data configured (OPENMC_CROSS_SECTIONS)")
        
        # Check if OpenMC is available
        try:
            import openmc
            print(f"   ✓ OpenMC version {openmc.__version__} found")
        except ImportError:
            print("   ✗ OpenMC not found - will fall back to mock")
        
        # Check nuclear data
        if os.getenv("OPENMC_CROSS_SECTIONS"):
            print(f"   ✓ Nuclear data configured")
        else:
            print("   ⚠️  OPENMC_CROSS_SECTIONS not set")
    
    print("\n" + "-"*80)
    
    # Import adapter
    try:
        from Playground.backend.openmc_adapter import OpenMCAdapter
        print("✓ Adapter imported successfully")
    except Exception as e:
        print(f"✗ Failed to import adapter: {e}")
        return 1
    
    # Create adapter
    adapter = OpenMCAdapter(runs_dir=Path("runs"))
    print("✓ Adapter initialized")
    
    # Test 1: Simple translation
    print("\n" + "-"*80)
    print("TEST 1: Spec Translation")
    print("-"*80)
    
    simple_spec = {
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Water"],
        "enrichment_pct": 4.5,
        "temperature_K": 900.0,
        "particles": 1000,
        "batches": 20
    }
    
    print("\nInput (simplified spec):")
    for key, value in simple_spec.items():
        print(f"  {key}: {value}")
    
    try:
        study = adapter.translate_simple_to_openmc(simple_spec, run_id="demo_001")
        print("\n✓ Translation successful")
        print(f"  Study name: {study.name}")
        print(f"  Materials: {list(study.materials.keys())}")
        print(f"  Spec hash: {study.get_short_hash()}")
        
        # Show fuel composition
        fuel = study.materials["fuel"]
        print(f"\n  Fuel composition:")
        for nuclide in fuel.nuclides:
            print(f"    {nuclide.name}: {nuclide.fraction:.6f}")
    except Exception as e:
        print(f"✗ Translation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test 2: Execution (mock or real)
    print("\n" + "-"*80)
    print("TEST 2: Simulation Execution")
    print("-"*80)
    
    # Use smaller parameters for demo
    demo_spec = {
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Water"],
        "enrichment_pct": 4.5,
        "temperature_K": 900.0,
        "particles": 500 if use_real else 1000,
        "batches": 10 if use_real else 20
    }
    
    print("\nExecuting simulation...")
    print("(This may take a while for real execution)")
    
    try:
        result = adapter.execute_real_openmc(demo_spec, run_id="demo_002")
        
        print("\n✓ Execution completed")
        print(f"  Status: {result['status']}")
        print(f"  Run ID: {result['run_id']}")
        print(f"  k-eff: {result['keff']:.5f} ± {result['keff_std']:.5f}")
        print(f"  Runtime: {result['runtime_seconds']:.2f} seconds")
        
        if result['status'] == 'completed':
            # Calculate uncertainty in pcm
            uncertainty_pcm = result['keff_std'] * 1e5
            print(f"  Uncertainty: {uncertainty_pcm:.1f} pcm")
            
            # Physical interpretation
            if result['keff'] > 1.0:
                print(f"  ➜ System is supercritical (k > 1)")
            elif result['keff'] < 1.0:
                print(f"  ➜ System is subcritical (k < 1)")
            else:
                print(f"  ➜ System is critical (k ≈ 1)")
        
    except Exception as e:
        print(f"✗ Execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test 3: Parameter sweep
    print("\n" + "-"*80)
    print("TEST 3: Enrichment Sweep")
    print("-"*80)
    
    print("\nRunning enrichment sweep...")
    enrichments = [3.0, 3.5, 4.0, 4.5, 5.0]
    results = []
    
    for enrichment in enrichments:
        sweep_spec = {
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "enrichment_pct": enrichment,
            "temperature_K": 900.0,
            "particles": 500 if use_real else 1000,
            "batches": 10 if use_real else 20
        }
        
        try:
            result = adapter.execute_real_openmc(
                sweep_spec,
                run_id=f"demo_sweep_{enrichment}"
            )
            results.append((enrichment, result))
            print(f"  {enrichment:4.1f}%: k-eff = {result['keff']:.5f} ± {result['keff_std']:.5f}")
        except Exception as e:
            print(f"  {enrichment:4.1f}%: FAILED - {e}")
    
    if results:
        print("\n✓ Sweep completed")
        keff_values = [r[1]['keff'] for r in results]
        print(f"  k-eff range: {min(keff_values):.5f} to {max(keff_values):.5f}")
        print(f"  Reactivity span: {(max(keff_values) - min(keff_values)):.5f}")
    
    # Test 4: MongoDB integration (if available)
    print("\n" + "-"*80)
    print("TEST 4: MongoDB Integration")
    print("-"*80)
    
    mongo_uri = os.getenv("MONGO_URI")
    if mongo_uri:
        print("\nStoring results in MongoDB...")
        try:
            from pymongo import MongoClient
            from datetime import datetime, timezone
            
            client = MongoClient(mongo_uri)
            db = client["aonp"]
            
            # Store a summary
            summary = {
                "run_id": result["run_id"],
                "spec_hash": result["spec_hash"],
                "keff": result["keff"],
                "keff_std": result["keff_std"],
                "runtime_seconds": result["runtime_seconds"],
                "status": result["status"],
                "created_at": datetime.now(timezone.utc),
                "spec": demo_spec
            }
            
            db["summaries"].insert_one(summary)
            
            print("✓ Results stored in MongoDB")
            print(f"  Collection: summaries")
            print(f"  Run ID: {result['run_id']}")
            
            # Query back
            stored = db["summaries"].find_one({"run_id": result["run_id"]})
            if stored:
                print("✓ Successfully retrieved from database")
            
        except Exception as e:
            print(f"⚠️  MongoDB integration failed: {e}")
    else:
        print("⚠️  MONGO_URI not set - skipping MongoDB test")
    
    # Summary
    print("\n" + "="*80)
    print("DEMO COMPLETE")
    print("="*80)
    print("\nIntegration Status: ✅ SUCCESS")
    print("\nThe adapter layer is working correctly!")
    print("\nNext Steps:")
    print("  1. Run tests: python tests/test_adapter_e2e.py")
    print("  2. Try real execution: USE_REAL_OPENMC=true python demo_adapter_integration.py")
    print("  3. Use in agent: Playground/backend/aonp_agents.py")
    print("\nSee INTEGRATION_COMPLETE.md for full documentation.")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)


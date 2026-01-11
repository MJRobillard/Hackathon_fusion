#!/usr/bin/env python3
"""
OpenMC simulation runner with provenance tracking.
"""

import os
import sys
import time
import json
from pathlib import Path
import secrets

from aonp.agents.rerun_prompting_agent import generate_rerun_suggestion
from aonp.core.bundler import create_run_bundle
from aonp.schemas.study import StudySpec


def _env_truthy(name: str, default: str = "0") -> bool:
    val = os.getenv(name, default).strip().lower()
    return val in {"1", "true", "yes", "y", "on"}


def run_simulation(run_dir: Path, *, enable_rerun_agent: bool = True) -> int:
    """
    Execute OpenMC simulation in the specified run directory.
    
    Args:
        run_dir: Path to bundle directory containing inputs/
    
    Returns:
        Exit code (0 = success, non-zero = failure)
    """
    # Validate directory structure
    run_dir = Path(run_dir)
    inputs_dir = run_dir / "inputs"
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    
    if not inputs_dir.exists():
        print(f"[ERROR] inputs directory not found: {inputs_dir}")
        return 1
    
    # Load run manifest for provenance
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        print(f"[ERROR] run_manifest.json not found: {manifest_path}")
        return 1
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    print(f"Run ID: {manifest['run_id']}")
    print(f"Spec Hash: {manifest['spec_hash'][:12]}...")
    
    # Set nuclear data path
    nuclear_data_ref = run_dir / "nuclear_data.ref.json"
    if nuclear_data_ref.exists():
        with open(nuclear_data_ref) as f:
            nd_config = json.load(f)
        
        cross_sections_xml = Path(nd_config['cross_sections_path'])
        if not cross_sections_xml.exists():
            print(f"[WARNING] Nuclear data not found: {cross_sections_xml}")
            print(f"[WARNING] Attempting to use OPENMC_CROSS_SECTIONS environment variable")
        else:
            os.environ['OPENMC_CROSS_SECTIONS'] = str(cross_sections_xml)
            print(f"Nuclear data: {nd_config['library']}")
    
    # Configure threading
    if 'OMP_NUM_THREADS' not in os.environ:
        # Default to available cores (leave 2 for system)
        import multiprocessing
        threads = max(1, multiprocessing.cpu_count() - 2)
        os.environ['OMP_NUM_THREADS'] = str(threads)
        print(f"Using {threads} OpenMP threads")
    
    # Check OpenMC installation
    try:
        import openmc
    except ImportError:
        print("[ERROR] OpenMC not installed!")
        print("Install with: pip install openmc")
        print("Note: OpenMC requires Linux/macOS or WSL on Windows")
        return 1
    
    # Execute simulation
    try:
        start_time = time.time()
        
        print("\n" + "="*60)
        print("Starting OpenMC simulation...")
        print("="*60 + "\n")
        
        # Update manifest status
        manifest['status'] = 'running'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Run in inputs directory
        openmc.run(cwd=str(inputs_dir), output=True)
        
        elapsed = time.time() - start_time
        print(f"\n✓ Simulation completed in {elapsed:.2f} seconds")
        
        # Move outputs
        for file in inputs_dir.glob("statepoint.*.h5"):
            file.rename(outputs_dir / file.name)
        for file in inputs_dir.glob("summary.h5"):
            file.rename(outputs_dir / file.name)
        for file in inputs_dir.glob("tallies.out"):
            file.rename(outputs_dir / file.name)
        
        # Update manifest with runtime
        manifest['runtime_seconds'] = elapsed
        manifest['status'] = 'completed'
        manifest['openmc_version'] = openmc.__version__
        
        import sys
        manifest['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"\n[OK] Results written to: {outputs_dir}")

        # Post-run rerun suggestion (best-effort; non-fatal)
        try:
            suggestion = generate_rerun_suggestion(run_dir) if enable_rerun_agent else None
            if suggestion:
                manifest["rerun_suggestion"] = suggestion
                with open(manifest_path, "w") as f:
                    json.dump(manifest, f, indent=2)
                yaml_path = suggestion.get("suggested_study_spec_yaml")
                print("\n" + "-" * 60)
                print("Rerun suggestion (via Fireworks) saved.")
                if yaml_path:
                    print(f"Suggested next input: {yaml_path}")
                if suggestion.get("changes"):
                    print("Suggested changes:")
                    for c in suggestion["changes"]:
                        print(f"  - {c}")

                # Optional: auto-rerun once using the suggested spec
                if _env_truthy("AONP_AUTO_RERUN", "0"):
                    try:
                        suggested_json = suggestion.get("suggested_study_spec_json")
                        if suggested_json and Path(suggested_json).exists():
                            suggested_spec = json.loads(Path(suggested_json).read_text(encoding="utf-8"))
                            suggested_study = StudySpec(**suggested_spec)
                            new_run_id = f"{manifest['run_id']}__rerun_{secrets.token_hex(3)}"
                            new_run_dir, _ = create_run_bundle(
                                suggested_study,
                                run_id=new_run_id,
                                base_dir=run_dir.parent,
                            )
                            # Mark provenance link
                            new_manifest_path = new_run_dir / "run_manifest.json"
                            if new_manifest_path.exists():
                                nm = json.loads(new_manifest_path.read_text(encoding="utf-8"))
                                nm["rerun_of"] = manifest["run_id"]
                                new_manifest_path.write_text(json.dumps(nm, indent=2), encoding="utf-8")

                            print(f"\n[OK] Auto-rerun starting: {new_run_id}")
                            # Prevent infinite chains: do not generate another suggestion on the rerun
                            run_simulation(new_run_dir, enable_rerun_agent=False)
                        else:
                            print("[WARN] Auto-rerun skipped: suggested spec json not found")
                    except Exception as e:
                        print(f"[WARN] Auto-rerun failed: {e}")
                else:
                    print("To auto-run the suggestion next time, set AONP_AUTO_RERUN=1")
                print("-" * 60)
            else:
                # If missing key or call failed, don't spam logs unless user asked for it
                pass
        except Exception as e:
            print(f"[WARN] Rerun suggestion failed: {e}")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Simulation failed: {e}")
        
        # Update manifest with error
        manifest['status'] = 'failed'
        manifest['error'] = str(e)
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        # Even on failure, try to propose a safer next input (best-effort; non-fatal)
        try:
            suggestion = (
                generate_rerun_suggestion(
                    run_dir,
                    objective="Fix the failure and improve the chance of a successful run.",
                )
                if enable_rerun_agent
                else None
            )
            if suggestion:
                manifest["rerun_suggestion"] = suggestion
                with open(manifest_path, "w") as f:
                    json.dump(manifest, f, indent=2)
                yaml_path = suggestion.get("suggested_study_spec_yaml")
                print("\n" + "-" * 60)
                print("Rerun suggestion (via Fireworks) saved (after failure).")
                if yaml_path:
                    print(f"Suggested next input: {yaml_path}")
                print("To auto-run the suggestion next time, set AONP_AUTO_RERUN=1")
                print("-" * 60)
        except Exception:
            pass
        
        return 1


def main():
    """Command-line entry point."""
    if len(sys.argv) != 2:
        print("Usage: python -m aonp.runner.entrypoint <run_directory>")
        sys.exit(1)
    
    run_dir = Path(sys.argv[1])
    if not run_dir.exists():
        print(f"[ERROR] Run directory not found: {run_dir}")
        sys.exit(1)
    
    exit_code = run_simulation(run_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Streaming OpenMC simulation runner that captures stdout for SSE streaming.
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path
from typing import Generator, Optional
import asyncio
from threading import Thread
import queue
import os
import secrets

from aonp.agents.rerun_prompting_agent import generate_rerun_suggestion
from aonp.core.bundler import create_run_bundle
from aonp.schemas.study import StudySpec


class StreamingSimulationRunner:
    """
    Executes OpenMC simulation and captures stdout line-by-line for streaming.
    """
    
    def __init__(self, run_dir: Path, *, enable_rerun_agent: bool = True):
        self.run_dir = Path(run_dir)
        self.inputs_dir = self.run_dir / "inputs"
        self.outputs_dir = self.run_dir / "outputs"
        self.manifest_path = self.run_dir / "run_manifest.json"
        self.enable_rerun_agent = enable_rerun_agent

    def _env_truthy(self, name: str, default: str = "0") -> bool:
        val = os.getenv(name, default).strip().lower()
        return val in {"1", "true", "yes", "y", "on"}
        
    def validate_setup(self) -> tuple[bool, Optional[str]]:
        """Validate directory structure and manifest."""
        if not self.inputs_dir.exists():
            return False, f"inputs directory not found: {self.inputs_dir}"
        
        if not self.manifest_path.exists():
            return False, f"run_manifest.json not found: {self.manifest_path}"
        
        return True, None
    
    def load_manifest(self) -> dict:
        """Load run manifest."""
        with open(self.manifest_path) as f:
            return json.load(f)
    
    def save_manifest(self, manifest: dict):
        """Save run manifest."""
        with open(self.manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def setup_environment(self, manifest: dict):
        """Configure environment variables for OpenMC."""
        # Set nuclear data path
        nuclear_data_ref = self.run_dir / "nuclear_data.ref.json"
        cross_sections_set = False
        
        if nuclear_data_ref.exists():
            with open(nuclear_data_ref) as f:
                nd_config = json.load(f)
            
            cross_sections_xml = Path(nd_config['cross_sections_path'])
            if cross_sections_xml.exists():
                os.environ['OPENMC_CROSS_SECTIONS'] = str(cross_sections_xml)
                cross_sections_set = True
            else:
                # Try to use existing environment variable as fallback
                if 'OPENMC_CROSS_SECTIONS' in os.environ:
                    env_path = Path(os.environ['OPENMC_CROSS_SECTIONS'])
                    if env_path.exists():
                        cross_sections_set = True
        
        # Fallback: use existing environment variable if not set from ref file
        if not cross_sections_set and 'OPENMC_CROSS_SECTIONS' in os.environ:
            env_path = Path(os.environ['OPENMC_CROSS_SECTIONS'])
            if env_path.exists():
                cross_sections_set = True
        
        # Configure threading
        if 'OMP_NUM_THREADS' not in os.environ:
            import multiprocessing
            threads = max(1, multiprocessing.cpu_count() - 2)
            os.environ['OMP_NUM_THREADS'] = str(threads)
        
        return cross_sections_set
    
    def stream_simulation(self) -> Generator[str, None, None]:
        """
        Execute OpenMC simulation and yield stdout lines in real-time.
        
        Yields:
            Lines of stdout from OpenMC simulation
        """
        # Validate setup
        valid, error = self.validate_setup()
        if not valid:
            yield f"[ERROR] {error}\n"
            return
        
        # Load and update manifest
        manifest = self.load_manifest()
        
        # Setup environment
        cross_sections_set = self.setup_environment(manifest)
        
        # Check if nuclear data is configured
        if not cross_sections_set:
            yield "\n[ERROR] Nuclear data (cross_sections.xml) not found!\n"
            yield "Please ensure one of the following:\n"
            yield "  1. nuclear_data.ref.json exists with valid cross_sections_path\n"
            yield "  2. OPENMC_CROSS_SECTIONS environment variable is set\n"
            nuclear_data_ref = self.run_dir / "nuclear_data.ref.json"
            if nuclear_data_ref.exists():
                with open(nuclear_data_ref) as f:
                    nd_config = json.load(f)
                yield f"  Expected path: {nd_config.get('cross_sections_path', 'N/A')}\n"
            if 'OPENMC_CROSS_SECTIONS' in os.environ:
                yield f"  Environment variable set to: {os.environ['OPENMC_CROSS_SECTIONS']}\n"
            yield "\n"
            manifest['status'] = 'failed'
            manifest['error'] = 'Nuclear data (cross_sections.xml) not found'
            self.save_manifest(manifest)
            return
        
        # Create outputs directory
        self.outputs_dir.mkdir(exist_ok=True)
        
        # Yield initial information
        yield f"Run ID: {manifest['run_id']}\n"
        yield f"Spec Hash: {manifest['spec_hash'][:12]}...\n"
        yield f"\n{'='*60}\n"
        yield "Starting OpenMC simulation...\n"
        yield f"{'='*60}\n\n"
        
        # Update manifest status
        manifest['status'] = 'running'
        self.save_manifest(manifest)
        
        start_time = time.time()
        
        # Check OpenMC installation
        try:
            result = subprocess.run(
                ['python', '-c', 'import openmc; print(openmc.__version__)'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                yield "[ERROR] OpenMC not installed!\n"
                yield "Install with: pip install openmc\n"
                manifest['status'] = 'failed'
                manifest['error'] = 'OpenMC not installed'
                self.save_manifest(manifest)
                return
            
            openmc_version = result.stdout.strip()
            yield f"OpenMC version: {openmc_version}\n\n"
        except Exception as e:
            yield f"[ERROR] Failed to check OpenMC: {e}\n"
            manifest['status'] = 'failed'
            manifest['error'] = str(e)
            self.save_manifest(manifest)
            return
        
        # Execute simulation with real-time output
        try:
            # Prepare environment for subprocess (inherit current env with OPENMC_CROSS_SECTIONS)
            env = os.environ.copy()
            
            # Run OpenMC as subprocess to capture stdout
            process = subprocess.Popen(
                [
                    sys.executable, '-c',
                    f'''
import openmc
import sys
import os
sys.stdout.flush()
openmc.run(cwd="{self.inputs_dir}", output=True)
'''
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            # Stream output line by line
            for line in iter(process.stdout.readline, ''):
                if line:
                    yield line
            
            process.wait()
            
            if process.returncode != 0:
                yield f"\n[ERROR] Simulation failed with exit code {process.returncode}\n"
                manifest['status'] = 'failed'
                manifest['error'] = f'Exit code {process.returncode}'
                self.save_manifest(manifest)
                return
            
            elapsed = time.time() - start_time
            yield f"\n✓ Simulation completed in {elapsed:.2f} seconds\n"
            
            # Move outputs
            moved_files = []
            for pattern in ["statepoint.*.h5", "summary.h5", "tallies.out"]:
                for file in self.inputs_dir.glob(pattern):
                    dest = self.outputs_dir / file.name
                    file.rename(dest)
                    moved_files.append(file.name)
            
            if moved_files:
                yield f"\nMoved output files: {', '.join(moved_files)}\n"
            
            # Update manifest with success
            manifest['runtime_seconds'] = elapsed
            manifest['status'] = 'completed'
            manifest['openmc_version'] = openmc_version
            manifest['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            self.save_manifest(manifest)
            
            yield f"\n[OK] Results written to: {self.outputs_dir}\n"

            # Post-run rerun suggestion (best-effort, non-fatal)
            try:
                suggestion = generate_rerun_suggestion(self.run_dir) if self.enable_rerun_agent else None
                if suggestion:
                    manifest["rerun_suggestion"] = suggestion
                    self.save_manifest(manifest)
                    yaml_path = suggestion.get("suggested_study_spec_yaml")
                    yield "\n" + "-" * 60 + "\n"
                    yield "Rerun suggestion (via Fireworks) saved.\n"
                    if yaml_path:
                        yield f"Suggested next input: {yaml_path}\n"
                    if suggestion.get("changes"):
                        yield "Suggested changes:\n"
                        for c in suggestion["changes"]:
                            yield f"  - {c}\n"

                    # Optional: auto-rerun once using the suggested spec (streamed)
                    if self._env_truthy("AONP_AUTO_RERUN", "0"):
                        try:
                            suggested_json = suggestion.get("suggested_study_spec_json")
                            if suggested_json and Path(suggested_json).exists():
                                suggested_spec = json.loads(Path(suggested_json).read_text(encoding="utf-8"))
                                suggested_study = StudySpec(**suggested_spec)
                                new_run_id = f"{manifest['run_id']}__rerun_{secrets.token_hex(3)}"
                                new_run_dir, _ = create_run_bundle(
                                    suggested_study,
                                    run_id=new_run_id,
                                    base_dir=self.run_dir.parent,
                                )
                                # Mark provenance link
                                new_manifest_path = new_run_dir / "run_manifest.json"
                                if new_manifest_path.exists():
                                    nm = json.loads(new_manifest_path.read_text(encoding="utf-8"))
                                    nm["rerun_of"] = manifest["run_id"]
                                    new_manifest_path.write_text(json.dumps(nm, indent=2), encoding="utf-8")

                                yield f"\n[OK] Auto-rerun starting: {new_run_id}\n"
                                yield "\n" + "=" * 60 + "\n"
                                yield "AUTO-RERUN STREAM\n"
                                yield "=" * 60 + "\n\n"

                                # Prevent infinite chains: do not generate another suggestion on the rerun
                                rerun_runner = StreamingSimulationRunner(new_run_dir, enable_rerun_agent=False)
                                for line in rerun_runner.stream_simulation():
                                    yield line
                            else:
                                yield "[WARN] Auto-rerun skipped: suggested spec json not found\n"
                        except Exception as e:
                            yield f"[WARN] Auto-rerun failed: {e}\n"
                    else:
                        yield "To auto-run the suggestion next time, set AONP_AUTO_RERUN=1\n"
                    yield "-" * 60 + "\n"
            except Exception as e:
                yield f"[WARN] Rerun suggestion failed/skipped: {e}\n"
            
        except subprocess.TimeoutExpired:
            yield "\n[ERROR] Simulation timed out\n"
            manifest['status'] = 'failed'
            manifest['error'] = 'Timeout'
            self.save_manifest(manifest)
        except Exception as e:
            yield f"\n[ERROR] Simulation failed: {e}\n"
            manifest['status'] = 'failed'
            manifest['error'] = str(e)
            self.save_manifest(manifest)

            # Even on failure, try to propose a safer next input (best-effort)
            try:
                suggestion = (
                    generate_rerun_suggestion(
                        self.run_dir,
                        objective="Fix the failure and improve the chance of a successful run.",
                    )
                    if self.enable_rerun_agent
                    else None
                )
                if suggestion:
                    manifest["rerun_suggestion"] = suggestion
                    self.save_manifest(manifest)
                    yaml_path = suggestion.get("suggested_study_spec_yaml")
                    yield "\n" + "-" * 60 + "\n"
                    yield "Rerun suggestion (via Fireworks) saved (after failure).\n"
                    if yaml_path:
                        yield f"Suggested next input: {yaml_path}\n"
                    yield "To auto-run the suggestion next time, set AONP_AUTO_RERUN=1\n"
                    yield "-" * 60 + "\n"
            except Exception:
                pass


async def async_stream_simulation(run_dir: Path) -> Generator[str, None, None]:
    """
    Async wrapper for streaming simulation output.
    
    Args:
        run_dir: Path to run directory
        
    Yields:
        Lines of simulation output
    """
    runner = StreamingSimulationRunner(run_dir)
    
    # Use thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    q = queue.Queue()
    
    def run_in_thread():
        try:
            for line in runner.stream_simulation():
                q.put(line)
        finally:
            q.put(None)  # Sentinel
    
    thread = Thread(target=run_in_thread, daemon=True)
    thread.start()
    
    # Yield from queue
    while True:
        # Non-blocking check with timeout
        try:
            line = await loop.run_in_executor(None, q.get, True, 0.1)
            if line is None:
                break
            yield line
        except queue.Empty:
            await asyncio.sleep(0.01)
            continue


if __name__ == "__main__":
    """Command-line interface for testing."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python streaming_runner.py <run_dir>")
        sys.exit(1)
    
    run_dir = Path(sys.argv[1])
    runner = StreamingSimulationRunner(run_dir)
    
    for line in runner.stream_simulation():
        print(line, end='', flush=True)


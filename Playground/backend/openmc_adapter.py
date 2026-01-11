"""
OpenMC Adapter Layer - Bridge between simplified agent specs and full OpenMC specs

This module translates simplified agent specifications into complete OpenMC StudySpec
objects and manages the execution pipeline.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

# Import AONP components
from aonp.schemas.study import (
    StudySpec, MaterialSpec, NuclideSpec, GeometrySpec, 
    SettingsSpec, NuclearDataSpec, SourceSpec
)
from aonp.core.bundler import create_run_bundle
import aonp.runner.entrypoint as runner_entrypoint
from aonp.core.extractor import extract_results


class OpenMCAdapter:
    """Adapter for translating simplified specs to OpenMC format and executing simulations."""
    
    def __init__(
        self,
        runs_dir: Path = Path("runs"),
        nuclear_data_path: Optional[str] = None,
        nuclear_data_library: str = "endfb71"
    ):
        """
        Initialize adapter.
        
        Args:
            runs_dir: Base directory for simulation runs
            nuclear_data_path: Path to nuclear data (uses env var if not provided)
            nuclear_data_library: Library identifier
        """
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(exist_ok=True)
        
        # Nuclear data configuration
        if nuclear_data_path is None:
            # Try to get from environment
            nuclear_data_path = os.getenv("OPENMC_CROSS_SECTIONS")
            if nuclear_data_path:
                # Extract directory from cross_sections.xml path
                nuclear_data_path = str(Path(nuclear_data_path).parent)
            else:
                # Default fallback
                nuclear_data_path = "/opt/openmc/data"
        
        self.nuclear_data_path = nuclear_data_path
        self.nuclear_data_library = nuclear_data_library
    
    def translate_simple_to_openmc(
        self,
        simple_spec: Dict[str, Any],
        run_id: Optional[str] = None
    ) -> StudySpec:
        """
        Translate simplified agent spec to full OpenMC StudySpec.
        
        Args:
            simple_spec: Simplified spec from agent with keys:
                - geometry: str (e.g., "PWR pin cell")
                - materials: List[str] (e.g., ["UO2", "Water"])
                - enrichment_pct: Optional[float]
                - temperature_K: Optional[float]
                - particles: int
                - batches: int
            run_id: Optional run identifier
        
        Returns:
            Complete StudySpec object ready for execution
        """
        # Extract parameters
        geometry_type = simple_spec.get("geometry", "PWR pin cell")
        material_names = simple_spec.get("materials", ["UO2", "Water"])
        enrichment = simple_spec.get("enrichment_pct", 4.5)
        temperature = simple_spec.get("temperature_K", 900.0)
        particles = simple_spec.get("particles", 10000)
        batches = simple_spec.get("batches", 50)
        
        # Create materials based on simplified spec
        materials = self._create_materials(
            material_names=material_names,
            enrichment_pct=enrichment,
            temperature_K=temperature
        )
        
        # Create geometry spec
        geometry = self._create_geometry(geometry_type)
        
        # Create settings
        settings = SettingsSpec(
            batches=batches,
            inactive=min(10, batches // 5),  # 20% inactive batches
            particles=particles,
            seed=42,
            source=SourceSpec(
                type="point",
                position=[0.0, 0.0, 0.0],
                energy=1.0e6  # 1 MeV
            )
        )
        
        # Create nuclear data spec
        nuclear_data = NuclearDataSpec(
            library=self.nuclear_data_library,
            path=self.nuclear_data_path,
            temperature_method="interpolation",
            temperature_tolerance=200.0
        )
        
        # Create full StudySpec
        study = StudySpec(
            name=run_id or f"study_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            description=f"Translated from simplified spec: {geometry_type}",
            materials=materials,
            geometry=geometry,
            settings=settings,
            nuclear_data=nuclear_data
        )
        
        return study
    
    def _create_materials(
        self,
        material_names: list[str],
        enrichment_pct: float,
        temperature_K: float
    ) -> Dict[str, MaterialSpec]:
        """
        Create material specifications from simplified names.
        
        Args:
            material_names: List of material names (e.g., ["UO2", "Water"])
            enrichment_pct: U-235 enrichment percentage
            temperature_K: Temperature in Kelvin
        
        Returns:
            Dictionary of MaterialSpec objects keyed by name
        """
        materials = {}
        
        for mat_name in material_names:
            mat_lower = mat_name.lower()
            
            # UO2 fuel
            if "uo2" in mat_lower or "fuel" in mat_lower:
                u235_fraction = enrichment_pct / 100.0
                u238_fraction = 1.0 - u235_fraction
                
                # Pre-normalize fractions (UO2 has U:O ratio of 1:2)
                total_fraction = u235_fraction + u238_fraction + 2.0
                u235_norm = u235_fraction / total_fraction
                u238_norm = u238_fraction / total_fraction
                o16_norm = 2.0 / total_fraction
                
                materials["fuel"] = MaterialSpec(
                    density=10.4,  # g/cm³
                    density_units="g/cm3",
                    temperature=temperature_K,
                    nuclides=[
                        NuclideSpec(name="U235", fraction=u235_norm, fraction_type="ao"),
                        NuclideSpec(name="U238", fraction=u238_norm, fraction_type="ao"),
                        NuclideSpec(name="O16", fraction=o16_norm, fraction_type="ao"),
                    ]
                )
            
            # Water moderator
            elif "water" in mat_lower or "moderator" in mat_lower or "h2o" in mat_lower:
                # H2O has H:O ratio of 2:1
                total_fraction = 3.0
                h1_norm = 2.0 / total_fraction
                o16_norm = 1.0 / total_fraction
                
                materials["moderator"] = MaterialSpec(
                    density=0.7,  # g/cm³ (typical for PWR)
                    density_units="g/cm3",
                    temperature=600.0,  # Typical moderator temperature
                    nuclides=[
                        NuclideSpec(name="H1", fraction=h1_norm, fraction_type="ao"),
                        NuclideSpec(name="O16", fraction=o16_norm, fraction_type="ao"),
                    ]
                )
            
            # Zircaloy cladding
            elif "zircaloy" in mat_lower or "zirconium" in mat_lower or "clad" in mat_lower:
                materials["cladding"] = MaterialSpec(
                    density=6.5,  # g/cm³
                    density_units="g/cm3",
                    temperature=600.0,
                    nuclides=[
                        NuclideSpec(name="Zr90", fraction=0.5145, fraction_type="ao"),
                        NuclideSpec(name="Zr91", fraction=0.1122, fraction_type="ao"),
                        NuclideSpec(name="Zr92", fraction=0.1715, fraction_type="ao"),
                        NuclideSpec(name="Zr94", fraction=0.1738, fraction_type="ao"),
                        NuclideSpec(name="Zr96", fraction=0.0280, fraction_type="ao"),
                    ]
                )
        
        # Ensure we have at least fuel and moderator
        if "fuel" not in materials:
            raise ValueError("Could not identify fuel material in spec")
        if "moderator" not in materials:
            raise ValueError("Could not identify moderator material in spec")
        
        return materials
    
    def _create_geometry(self, geometry_type: str) -> GeometrySpec:
        """
        Create geometry specification from simplified type.
        
        Args:
            geometry_type: Simple description (e.g., "PWR pin cell")
        
        Returns:
            GeometrySpec object
        """
        # For MVP, use the example pincell geometry
        geometry_script = Path(__file__).parent.parent.parent / "aonp" / "examples" / "pincell_geometry.py"
        
        if not geometry_script.exists():
            raise FileNotFoundError(f"Geometry script not found: {geometry_script}")
        
        return GeometrySpec(
            type="script",
            script=str(geometry_script)
        )
    
    def execute_real_openmc(
        self,
        simple_spec: Dict[str, Any],
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute real OpenMC simulation from simplified spec.
        
        This replaces the mock execution in agent_tools.py.
        
        Args:
            simple_spec: Simplified spec from agent
            run_id: Optional run identifier
        
        Returns:
            Dictionary with execution results:
                - keff: float
                - keff_std: float
                - runtime_seconds: float
                - status: str
                - run_id: str
                - spec_hash: str
                - run_dir: str (path to run directory)
        """
        try:
            # Step 1: Translate to full OpenMC spec
            study = self.translate_simple_to_openmc(simple_spec, run_id)
            
            # Step 2: Create run bundle
            run_dir, spec_hash = create_run_bundle(
                study=study,
                run_id=run_id,
                base_dir=self.runs_dir
            )
            
            # Step 3: Execute simulation
            exit_code = runner_entrypoint.run_simulation(run_dir)
            
            if exit_code != 0:
                return {
                    "status": "failed",
                    "error": "OpenMC execution failed",
                    "run_id": run_dir.name,
                    "spec_hash": spec_hash,
                    "run_dir": str(run_dir),
                    "keff": 0.0,
                    "keff_std": 0.0,
                    "runtime_seconds": 0.0
                }
            
            # Step 4: Extract results
            statepoint_files = list((run_dir / "outputs").glob("statepoint.*.h5"))
            
            if not statepoint_files:
                return {
                    "status": "failed",
                    "error": "No statepoint file found",
                    "run_id": run_dir.name,
                    "spec_hash": spec_hash,
                    "run_dir": str(run_dir),
                    "keff": 0.0,
                    "keff_std": 0.0,
                    "runtime_seconds": 0.0
                }
            
            results = extract_results(statepoint_files[0])
            
            # Step 5: Load runtime from manifest
            import json
            manifest_path = run_dir / "run_manifest.json"
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            return {
                "keff": results["keff"],
                "keff_std": results["keff_std"],
                "runtime_seconds": manifest.get("runtime_seconds", 0.0),
                "status": "completed",
                "run_id": run_dir.name,
                "spec_hash": spec_hash,
                "run_dir": str(run_dir)
            }
            
        except Exception as e:
            print(f"[ERROR] OpenMC execution failed: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "status": "failed",
                "error": str(e),
                "run_id": run_id or "unknown",
                "spec_hash": "",
                "run_dir": "",
                "keff": 0.0,
                "keff_std": 0.0,
                "runtime_seconds": 0.0
            }


# Convenience function for direct import
def execute_real_openmc(simple_spec: Dict[str, Any], run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to execute OpenMC with default adapter settings.
    
    Args:
        simple_spec: Simplified spec from agent
        run_id: Optional run identifier
    
    Returns:
        Execution results dictionary
    """
    adapter = OpenMCAdapter()
    return adapter.execute_real_openmc(simple_spec, run_id)


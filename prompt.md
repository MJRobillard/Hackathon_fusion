# OpenMC Integration Design Document
## AONP - Agent-Orchestrated Neutronics Platform

**Version**: 0.1.0  
**Last Updated**: January 10, 2026  
**Purpose**: Complete reproducible design for OpenMC simulation engine integration

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [OpenMC Data Flow](#openmc-data-flow)
4. [Component Design](#component-design)
5. [File Structure](#file-structure)
6. [Setup and Installation](#setup-and-installation)
7. [Configuration Schema](#configuration-schema)
8. [Execution Pipeline](#execution-pipeline)
9. [Nuclear Data Management](#nuclear-data-management)
10. [Result Extraction](#result-extraction)
11. [Provenance and Reproducibility](#provenance-and-reproducibility)
12. [Error Handling](#error-handling)
13. [Performance Considerations](#performance-considerations)
14. [Testing Strategy](#testing-strategy)
15. [Future Enhancements](#future-enhancements)

---

## Executive Summary

The OpenMC integration layer serves as the **physics engine** within AONP's high-integrity neutronics platform. This design ensures:

- **Deterministic execution**: Same inputs always produce identical results (given fixed random seed)
- **Complete provenance**: Every simulation result traceable to exact input configuration
- **Reproducible setup**: Full installation and configuration documentation
- **Validation pipeline**: Comprehensive testing from input validation to result extraction

### Key Capabilities

✅ Monte Carlo neutron transport simulation  
✅ XML-based input generation from YAML specifications  
✅ HDF5 output processing to Parquet format  
✅ Multi-threading support (OpenMP)  
✅ Nuclear data library management (ENDF/B-VII.1)  
✅ Cryptographic input hashing for reproducibility  

---

## Architecture Overview

### Position in AONP System

```
┌─────────────────────────────────────────────────────────────────┐
│                    AONP SYSTEM ARCHITECTURE                      │
│                  (OpenMC as Physics Engine)                      │
└─────────────────────────────────────────────────────────────────┘

USER INPUT                          AONP LAYER                  OPENMC LAYER
──────────                          ──────────                  ────────────

study.yaml ──┐
             │
             ▼
      ┌──────────────┐
      │   Pydantic   │         StudySpec Model
      │  Validation  │         ├── materials
      │              │         ├── geometry
      └──────┬───────┘         ├── settings
             │                 └── nuclear_data
             │
             ▼
      ┌──────────────┐
      │  Canonical   │         SHA256(sorted_json)
      │    Hash      │         → spec_hash
      └──────┬───────┘
             │
             ▼
      ┌──────────────┐         bundles/{spec_hash}/{run_id}/
      │   Bundler    │         ├── study_spec.json
      │              │         ├── run_manifest.json
      └──────┬───────┘         ├── nuclear_data.ref.json
             │                 └── inputs/
             │
             ▼
      ┌──────────────┐         Generate OpenMC XML files:
      │  XML Writer  │─────┐   ├── materials.xml
      │              │     │   ├── geometry.xml (from .py)
      └──────────────┘     │   ├── settings.xml
                           │   └── tallies.xml (future)
                           │
                           ▼
                    ┌──────────────┐
                    │   OpenMC     │   openmc.run()
                    │   Solver     │   ├── Initialize
                    │              │   ├── Transport
                    └──────┬───────┘   └── Write HDF5
                           │
                           │   outputs/
                           │   ├── statepoint.*.h5
                           │   ├── summary.h5
                           │   └── tallies.out
                           │
                           ▼
                    ┌──────────────┐
                    │  Extractor   │   Parse HDF5 → DataFrame
                    │              │   ├── k-effective
                    └──────┬───────┘   ├── uncertainties
                           │           └── batch stats
                           ▼
                    summary.parquet ──▶ MongoDB / Analysis

```

### Component Responsibilities

| Component | Input | Output | Purpose |
|-----------|-------|--------|---------|
| **Validator** | `study.yaml` | `StudySpec` | Type-safe parsing & validation |
| **Hasher** | `StudySpec` | `spec_hash` | Deterministic input fingerprint |
| **Bundler** | `StudySpec` + `run_id` | Bundle directory | Self-contained execution unit |
| **XML Writer** | Bundle metadata | `*.xml` files | OpenMC input generation |
| **Runner** | Bundle directory | Exit code + HDF5 | Execute OpenMC simulation |
| **Extractor** | `statepoint.h5` | `summary.parquet` | Result post-processing |

---

## OpenMC Data Flow

### Detailed Execution Sequence

```
┌───────────────────────────────────────────────────────────────────────────┐
│                     OPENMC INTEGRATION DATA FLOW                          │
│                     (Single Run Execution Path)                           │
└───────────────────────────────────────────────────────────────────────────┘

PHASE 1: INPUT PREPARATION
═══════════════════════════

study.yaml
    │
    ├─ name: "simple_pincell_v1"
    ├─ materials:
    │   ├─ fuel: {density: 10.4, temp: 900, nuclides: [...]}
    │   └─ moderator: {density: 1.0, temp: 600, nuclides: [...]}
    ├─ geometry:
    │   ├─ type: "script"
    │   └─ script: "pincell_geometry.py"
    ├─ settings:
    │   ├─ batches: 120
    │   ├─ particles: 10000
    │   └─ seed: 42
    └─ nuclear_data:
        └─ library: "endfb71"
    │
    ▼
StudySpec.model_validate()  ◄─── Pydantic validation
    │
    ├─ Type checking (int, float, str)
    ├─ Range validation (positive values)
    ├─ Enum validation (library names)
    └─ Structural integrity
    │
    ▼
spec_hash = sha256(canonical_json)  ◄─── Deterministic hash
    │
    ▼
bundles/spec_a1b2c3d4/run_e5f6g7h8/
    │
    ├─── study_spec.json           ← Canonical input (sorted keys)
    ├─── run_manifest.json         ← Provenance metadata
    ├─── nuclear_data.ref.json     ← Library references
    └─── inputs/                   ← OpenMC XML files (generated next)


PHASE 2: OPENMC INPUT GENERATION
═════════════════════════════════

Bundle Directory
    │
    ▼
generate_materials_xml()
    │
    ├─ Parse materials section from study_spec.json
    ├─ For each material:
    │   ├─ Create <material id="X" name="Y">
    │   ├─ Set density (g/cm³ or atom/b-cm)
    │   ├─ Set temperature (K)
    │   └─ Add nuclides with atomic fractions
    │
    ▼
inputs/materials.xml
    │
    ├─ <material id="1" name="fuel">
    │   ├─ <density value="10.4" units="g/cm3"/>
    │   ├─ <temperature>900.0</temperature>
    │   ├─ <nuclide name="U235" ao="0.03"/>
    │   ├─ <nuclide name="U238" ao="0.27"/>
    │   └─ <nuclide name="O16" ao="0.70"/>
    └─ <material id="2" name="moderator">
        ├─ ...


generate_geometry_xml()
    │
    ├─ Execute geometry.script (Python script)
    │   └─ pincell_geometry.py creates OpenMC Universe
    │
    ├─ Export to XML format
    │   ├─ Surfaces (cylinders, planes)
    │   ├─ Cells (regions filled with materials)
    │   └─ Boundary conditions (reflective/vacuum)
    │
    ▼
inputs/geometry.xml
    │
    ├─ <surface id="1" type="z-cylinder" r="0.39"/>
    ├─ <surface id="2" type="z-cylinder" r="0.40"/>
    ├─ <cell id="1" material="1" region="-1"/>
    ├─ <cell id="2" material="2" region="1 -2"/>
    └─ <cell id="3" material="void" region="2" boundary="reflective"/>


generate_settings_xml()
    │
    ├─ Parse settings section
    │   ├─ batches = 120
    │   ├─ inactive = 20
    │   ├─ particles = 10000
    │   └─ seed = 42
    │
    ▼
inputs/settings.xml
    │
    ├─ <batches>120</batches>
    ├─ <inactive>20</inactive>
    ├─ <particles>10000</particles>
    ├─ <seed>42</seed>
    └─ <entropy_mesh>...</entropy_mesh>


PHASE 3: OPENMC EXECUTION
══════════════════════════

Run Directory: bundles/spec_a1b2c3d4/run_e5f6g7h8/
    │
    ▼
python -m aonp.runner.entrypoint $RUN_DIR
    │
    ├─ Set OPENMC_CROSS_SECTIONS env var
    ├─ Set OMP_NUM_THREADS for parallelism
    │
    ▼
openmc.run(cwd="inputs/")
    │
    ├─ [Initialize Phase]
    │   ├─ Load cross section data (ENDF/B-VII.1)
    │   ├─ Build geometry tree
    │   ├─ Initialize particle source
    │   └─ Time: ~0.4s
    │
    ├─ [Inactive Batches: 1-20]
    │   ├─ Purpose: Converge fission source
    │   ├─ Track Shannon entropy
    │   ├─ Discard these batches from statistics
    │   └─ Time: ~1.4s
    │
    ├─ [Active Batches: 21-120]
    │   ├─ Purpose: Accumulate statistics
    │   ├─ Calculate k-effective estimators:
    │   │   ├─ Collision estimator
    │   │   ├─ Track-length estimator
    │   │   └─ Absorption estimator
    │   ├─ Accumulate tally scores
    │   └─ Time: ~5.8s
    │
    ▼
outputs/
    │
    ├─ statepoint.120.h5           ← Final state (particles, k-eff, tallies)
    ├─ summary.h5                  ← Simulation metadata
    └─ tallies.out                 ← Human-readable tally output


PHASE 4: RESULT EXTRACTION
═══════════════════════════

outputs/statepoint.120.h5
    │
    ▼
python -m aonp.core.extractor
    │
    ├─ sp = openmc.StatePoint("statepoint.120.h5")
    │
    ├─ Extract k-effective:
    │   ├─ keff = sp.keff.nominal_value      → 1.60991
    │   └─ keff_std = sp.keff.std_dev        → 0.00087
    │
    ├─ Extract batch statistics:
    │   ├─ n_batches = sp.n_batches          → 120
    │   ├─ n_inactive = sp.n_inactive        → 20
    │   └─ n_particles = sp.n_particles      → 10000
    │
    ├─ Extract tallies (future):
    │   └─ flux_mesh = sp.tallies[...]
    │
    ▼
summary.parquet
    │
    ├─ run_id: "run_e5f6g7h8"
    ├─ spec_hash: "spec_a1b2c3d4"
    ├─ keff: 1.60991
    ├─ keff_std: 0.00087
    ├─ runtime_s: 7.225
    └─ timestamp: "2026-01-08T18:09:44Z"
    │
    ▼
MongoDB: summaries.insert_one(...)  ◄─── Queryable results
```

---

## Component Design

### 1. Bundler (`aonp/core/bundler.py`)

**Purpose**: Create self-contained execution directories with complete provenance.

**Key Functions**:

```python
def create_run_bundle(
    study: StudySpec,
    run_id: Optional[str] = None,
    base_dir: Path = Path("runs")
) -> Tuple[Path, str]:
    """
    Creates a run bundle with:
    - Canonical study specification
    - Run manifest (provenance)
    - Nuclear data references
    - Generated OpenMC XML inputs
    
    Returns:
        (run_directory, spec_hash)
    """
```

**Directory Structure Created**:

```
runs/run_{random_id}/
├── study_spec.json          # Canonical input (sorted keys, no whitespace)
├── run_manifest.json        # Provenance metadata
├── nuclear_data.ref.json    # Nuclear data library references
├── inputs/
│   ├── materials.xml        # Generated from study_spec
│   ├── geometry.xml         # Generated from geometry script
│   ├── settings.xml         # Generated from study_spec
│   └── geometry_script.py   # Copy of user-provided script
└── outputs/                 # Created during execution
    ├── statepoint.*.h5
    ├── summary.h5
    └── logs.txt
```

**Hashing Algorithm**:

```python
def get_canonical_hash(self) -> str:
    """Generate deterministic SHA256 hash of study specification."""
    # 1. Convert Pydantic model to dict
    data = self.model_dump()
    
    # 2. Serialize to JSON with sorted keys, no whitespace
    canonical_json = json.dumps(
        data,
        sort_keys=True,      # Order-independent
        separators=(',', ':'),  # No spaces
        ensure_ascii=True    # Portable encoding
    )
    
    # 3. Hash the bytes
    hash_obj = hashlib.sha256(canonical_json.encode('utf-8'))
    return hash_obj.hexdigest()
```

**Validation**:
- ✅ Same study → Same hash (format-independent)
- ✅ Different study → Different hash (parameter-sensitive)
- ✅ Comments in YAML → No effect on hash
- ✅ Reordered keys → No effect on hash

---

### 2. XML Generator (integrated in `bundler.py`)

**Purpose**: Convert StudySpec to OpenMC-compatible XML format.

#### Materials XML Generation

```python
def write_materials_xml(study: StudySpec, output_path: Path):
    """Generate materials.xml from study specification."""
    materials = openmc.Materials()
    
    for mat_name, mat_spec in study.materials.items():
        mat = openmc.Material(name=mat_name)
        
        # Set density
        mat.set_density(
            mat_spec.density_units,  # 'g/cm3' or 'atom/b-cm'
            mat_spec.density
        )
        
        # Set temperature
        mat.temperature = mat_spec.temperature  # Kelvin
        
        # Add nuclides
        for nuclide in mat_spec.nuclides:
            mat.add_nuclide(
                nuclide.name,         # e.g., 'U235'
                nuclide.fraction,     # atomic or weight fraction
                nuclide.fraction_type # 'ao' or 'wo'
            )
        
        materials.append(mat)
    
    materials.export_to_xml(output_path)
```

**Example Output** (`materials.xml`):

```xml
<?xml version="1.0"?>
<materials>
  <material id="1" name="fuel">
    <density value="10.4" units="g/cm3"/>
    <temperature>900.0</temperature>
    <nuclide name="U235" ao="0.03"/>
    <nuclide name="U238" ao="0.27"/>
    <nuclide name="O16" ao="0.70"/>
  </material>
  <material id="2" name="moderator">
    <density value="1.0" units="g/cm3"/>
    <temperature>600.0</temperature>
    <nuclide name="H1" ao="0.6667"/>
    <nuclide name="O16" ao="0.3333"/>
  </material>
</materials>
```

#### Geometry XML Generation

```python
def write_geometry_xml(study: StudySpec, output_path: Path):
    """Generate geometry.xml by executing user-provided script."""
    if study.geometry.type == "script":
        # Execute geometry script
        script_path = Path(study.geometry.script)
        
        # Import script and get geometry
        spec = importlib.util.spec_from_file_location("geom", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Script must define create_geometry() function
        geometry = module.create_geometry(study.materials)
        geometry.export_to_xml(output_path)
```

**Example Geometry Script** (`pincell_geometry.py`):

```python
import openmc

def create_geometry(materials_spec):
    """Create a simple pin cell geometry."""
    
    # Define surfaces
    fuel_or = openmc.ZCylinder(r=0.39)
    clad_or = openmc.ZCylinder(r=0.40)
    clad_or.boundary_type = 'reflective'  # Infinite lattice
    
    # Define cells
    fuel_cell = openmc.Cell(name='fuel')
    fuel_cell.fill = materials_spec['fuel']
    fuel_cell.region = -fuel_or
    
    clad_cell = openmc.Cell(name='clad')
    clad_cell.fill = materials_spec['moderator']
    clad_cell.region = +fuel_or & -clad_or
    
    # Create universe and geometry
    root = openmc.Universe(cells=[fuel_cell, clad_cell])
    geometry = openmc.Geometry(root)
    
    return geometry
```

#### Settings XML Generation

```python
def write_settings_xml(study: StudySpec, output_path: Path):
    """Generate settings.xml from study specification."""
    settings = openmc.Settings()
    
    # Batch configuration
    settings.batches = study.settings.batches
    settings.inactive = study.settings.inactive
    settings.particles = study.settings.particles
    
    # Random seed (for reproducibility)
    settings.seed = study.settings.seed
    
    # Source definition
    if study.settings.source:
        # Custom source
        source = openmc.Source()
        source.space = openmc.stats.Point(study.settings.source.position)
        source.energy = openmc.stats.Discrete([study.settings.source.energy], [1.0])
        settings.source = source
    else:
        # Default: uniform fission source
        bounds = [-0.62, -0.62, -1, 0.62, 0.62, 1]
        uniform_dist = openmc.stats.Box(bounds[:3], bounds[3:])
        settings.source = openmc.Source(space=uniform_dist)
    
    # Shannon entropy mesh (for convergence monitoring)
    entropy_mesh = openmc.RegularMesh()
    entropy_mesh.lower_left = [-0.62, -0.62, -1]
    entropy_mesh.upper_right = [0.62, 0.62, 1]
    entropy_mesh.dimension = [10, 10, 1]
    settings.entropy_mesh = entropy_mesh
    
    settings.export_to_xml(output_path)
```

---

### 3. Runner (`aonp/runner/entrypoint.py`)

**Purpose**: Execute OpenMC simulation with proper environment configuration.

```python
#!/usr/bin/env python3
"""OpenMC simulation runner with provenance tracking."""

import os
import sys
import time
import json
from pathlib import Path
import openmc

def run_simulation(run_dir: Path) -> int:
    """
    Execute OpenMC simulation in the specified run directory.
    
    Args:
        run_dir: Path to bundle directory containing inputs/
    
    Returns:
        Exit code (0 = success, non-zero = failure)
    """
    
    # Validate directory structure
    inputs_dir = run_dir / "inputs"
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    
    if not inputs_dir.exists():
        print(f"Error: inputs directory not found: {inputs_dir}")
        return 1
    
    # Load run manifest for provenance
    manifest_path = run_dir / "run_manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    print(f"Run ID: {manifest['run_id']}")
    print(f"Spec Hash: {manifest['input_hash']}")
    
    # Set nuclear data path
    nuclear_data_ref = run_dir / "nuclear_data.ref.json"
    with open(nuclear_data_ref) as f:
        nd_config = json.load(f)
    
    cross_sections_xml = Path(nd_config['cross_sections_path'])
    if not cross_sections_xml.exists():
        print(f"Error: Nuclear data not found: {cross_sections_xml}")
        return 1
    
    os.environ['OPENMC_CROSS_SECTIONS'] = str(cross_sections_xml)
    
    # Configure threading
    if 'OMP_NUM_THREADS' not in os.environ:
        # Default to available cores (leave 2 for system)
        import multiprocessing
        threads = max(1, multiprocessing.cpu_count() - 2)
        os.environ['OMP_NUM_THREADS'] = str(threads)
        print(f"Using {threads} OpenMP threads")
    
    # Execute simulation
    try:
        start_time = time.time()
        
        print("\n" + "="*60)
        print("Starting OpenMC simulation...")
        print("="*60 + "\n")
        
        # Run in inputs directory
        openmc.run(cwd=str(inputs_dir), output=True)
        
        elapsed = time.time() - start_time
        print(f"\n✓ Simulation completed in {elapsed:.2f} seconds")
        
        # Move outputs
        for file in inputs_dir.glob("statepoint.*.h5"):
            file.rename(outputs_dir / file.name)
        for file in inputs_dir.glob("summary.h5"):
            file.rename(outputs_dir / file.name)
        
        # Update manifest with runtime
        manifest['runtime_seconds'] = elapsed
        manifest['status'] = 'completed'
        manifest['openmc_version'] = openmc.__version__
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Simulation failed: {e}")
        
        # Update manifest with error
        manifest['status'] = 'failed'
        manifest['error'] = str(e)
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m aonp.runner.entrypoint <run_directory>")
        sys.exit(1)
    
    run_dir = Path(sys.argv[1])
    exit_code = run_simulation(run_dir)
    sys.exit(exit_code)
```

---

### 4. Extractor (`aonp/core/extractor.py`)

**Purpose**: Parse OpenMC HDF5 outputs into structured data formats.

```python
import openmc
import pandas as pd
from pathlib import Path
from typing import Dict, Any

def extract_results(statepoint_path: Path) -> Dict[str, Any]:
    """
    Extract key results from OpenMC statepoint file.
    
    Args:
        statepoint_path: Path to statepoint.*.h5 file
    
    Returns:
        Dictionary with k-effective, uncertainties, and batch stats
    """
    sp = openmc.StatePoint(str(statepoint_path))
    
    # Extract k-effective
    keff = sp.keff.nominal_value
    keff_std = sp.keff.std_dev
    
    # Extract batch statistics
    results = {
        'keff': keff,
        'keff_std': keff_std,
        'keff_uncertainty_pcm': keff_std * 1e5,  # Convert to pcm
        'n_batches': sp.n_batches,
        'n_inactive': sp.n_inactive,
        'n_particles': sp.n_particles,
        'n_realizations': sp.n_realizations,
    }
    
    # Extract batch k-effective values
    results['batch_keff'] = sp.k_generation.tolist()
    
    # Extract entropy (if available)
    if hasattr(sp, 'entropy'):
        results['entropy'] = sp.entropy.tolist()
    
    return results


def create_summary(statepoint_path: Path, output_path: Path = None) -> Path:
    """
    Create summary Parquet file from statepoint.
    
    Args:
        statepoint_path: Path to statepoint file
        output_path: Optional output path (default: same dir as statepoint)
    
    Returns:
        Path to created summary.parquet file
    """
    results = extract_results(statepoint_path)
    
    # Create DataFrame
    summary_data = {
        'metric': ['keff', 'keff_std', 'keff_uncertainty_pcm', 
                   'n_batches', 'n_inactive', 'n_particles'],
        'value': [results['keff'], results['keff_std'], 
                  results['keff_uncertainty_pcm'],
                  results['n_batches'], results['n_inactive'], 
                  results['n_particles']]
    }
    
    df = pd.DataFrame(summary_data)
    
    # Determine output path
    if output_path is None:
        output_path = statepoint_path.parent / "summary.parquet"
    
    # Write Parquet (efficient for queries)
    df.to_parquet(output_path, index=False)
    
    print(f"[OK] Extracted results to: {output_path}")
    print(f"  k-eff: {results['keff']:.6f} +/- {results['keff_std']:.6f}")
    print(f"  Batches: {results['n_batches']}")
    
    return output_path


def load_summary(parquet_path: Path) -> pd.DataFrame:
    """Load summary DataFrame from Parquet file."""
    return pd.read_parquet(parquet_path)
```

---

## File Structure

### Complete Bundle Anatomy

```
bundles/spec_a1b2c3d4e5f6/run_e7f8g9h0i1j2/
│
├── study_spec.json              # Canonical input specification
│   ├── name: "simple_pincell_v1"
│   ├── materials: {...}
│   ├── geometry: {...}
│   ├── settings: {...}
│   └── nuclear_data: {...}
│
├── run_manifest.json            # Provenance metadata
│   ├── run_id: "run_e7f8g9h0i1j2"
│   ├── spec_hash: "spec_a1b2c3d4e5f6"
│   ├── timestamp: "2026-01-08T18:09:44Z"
│   ├── openmc_version: "0.15.3"
│   ├── runtime_seconds: 7.225
│   └── status: "completed"
│
├── nuclear_data.ref.json        # Nuclear data references
│   ├── library: "endfb71"
│   ├── version: "VII.1"
│   ├── cross_sections_path: "/path/to/cross_sections.xml"
│   └── nuclides: ["U235", "U238", "O16", "H1"]
│
├── inputs/                      # OpenMC input files
│   ├── materials.xml            # Material definitions
│   ├── geometry.xml             # Geometry definitions
│   ├── settings.xml             # Monte Carlo settings
│   ├── geometry_script.py       # Original geometry script (copy)
│   └── tallies.xml              # (future) Tally specifications
│
└── outputs/                     # Simulation results
    ├── statepoint.120.h5        # Final state (HDF5)
    │   ├── k-effective values
    │   ├── batch statistics
    │   ├── tally results
    │   └── particle data
    │
    ├── summary.h5               # Simulation metadata (HDF5)
    │   ├── input file hashes
    │   ├── nuclide metadata
    │   └── performance metrics
    │
    ├── summary.parquet          # Extracted results (for queries)
    │   ├── keff: 1.60991
    │   ├── keff_std: 0.00087
    │   └── batch_stats: [...]
    │
    └── logs.txt                 # Simulation log output
```

---

## Setup and Installation

### System Requirements

**Operating System**:
- Linux (native, recommended)
- macOS (native, recommended)
- Windows via WSL2 (tested, fully functional)

**Software Dependencies**:
- Python 3.8+
- OpenMC 0.14.0+ (requires HDF5, BLAS/LAPACK)
- Nuclear data library (ENDF/B-VII.1 or newer)

### Installation Methods

#### Method 1: Conda (Cross-Platform, Recommended)

```bash
# Create conda environment
conda create -n openmc-env python=3.11
conda activate openmc-env

# Install OpenMC from conda-forge
conda install -c conda-forge openmc

# Install AONP dependencies
pip install -r requirements.txt

# Verify installation
python -c "import openmc; print(openmc.__version__)"
```

#### Method 2: From Source (Linux/WSL)

```bash
# Install build dependencies
sudo apt-get update
sudo apt-get install -y \
    git cmake build-essential \
    libhdf5-dev libpng-dev \
    libblas-dev liblapack-dev

# Clone and build OpenMC
git clone https://github.com/openmc-dev/openmc.git
cd openmc
mkdir build && cd build
cmake ..
make
sudo make install

# Install Python API
cd ../
pip install .

# Install AONP dependencies
pip install -r requirements.txt
```

#### Method 3: Docker (Fully Isolated)

```bash
# Build Docker image with OpenMC pre-installed
docker build -t aonp:v0.1 -f aonp/runner/Dockerfile .

# Run simulation
docker run -v $(pwd)/runs:/app/runs aonp:v0.1 \
    python -m aonp.runner.entrypoint /app/runs/run_<hash>
```

### Nuclear Data Setup

OpenMC requires nuclear cross-section data. Use the provided script:

```bash
# Download ENDF/B-VII.1 (recommended, ~1 GB)
bash install_openmc_conda.sh

# Or download manually
mkdir -p ~/nuclear_data
cd ~/nuclear_data
wget https://anl.box.com/shared/static/9igk353zpy8fn9ttvtrqgzvw1vtejoz6.xz \
    -O endfb-vii.1-hdf5.tar.xz
tar -xJf endfb-vii.1-hdf5.tar.xz

# Set environment variable
export OPENMC_CROSS_SECTIONS=~/nuclear_data/endfb-vii.1-hdf5/cross_sections.xml

# Verify
python -c "import openmc; openmc.Materials()"
```

**Alternative Libraries**:
- **ENDF/B-VIII.0**: Latest evaluation (~2 GB)
- **JEFF-3.3**: European library
- **JENDL-5.0**: Japanese library

### WSL2 Setup (Windows Users)

```powershell
# Install WSL2 (from PowerShell as Administrator)
wsl --install

# Or use provided batch script
.\install_wsl.bat

# Launch WSL and run setup
wsl
cd /mnt/c/Users/YOUR_USERNAME/Downloads/fusion/fusion
bash setup_linux.sh
```

### Verification Tests

Run acceptance tests to validate installation:

```bash
# Test core functionality (no OpenMC required)
python test_core_only.py

# Test full pipeline (requires OpenMC + nuclear data)
python test_acceptance.py
```

**Expected Output**:
```
✓ Study validation passed
✓ Hash computation passed
✓ Hash stability passed
✓ Hash sensitivity passed
✓ Bundle creation passed
✓ OpenMC execution passed
✓ Result extraction passed

All tests passed! System is operational.
```

---

## Configuration Schema

### StudySpec (Pydantic Model)

Complete YAML specification structure:

```yaml
# Study identification
name: "simple_pincell_v1"
description: "Single UO2 fuel pin cell for validation"

# Material definitions
materials:
  fuel:
    density: 10.4
    density_units: "g/cm3"
    temperature: 900.0  # Kelvin
    nuclides:
      - name: "U235"
        fraction: 0.03
        fraction_type: "ao"  # atomic fraction
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

# Geometry definition
geometry:
  type: "script"  # or "inline" (future)
  script: "aonp/examples/pincell_geometry.py"

# Monte Carlo settings
settings:
  batches: 120
  inactive: 20
  particles: 10000
  seed: 42
  
  # Optional: custom source
  source:
    type: "point"
    position: [0.0, 0.0, 0.0]
    energy: 1.0e6  # eV

# Nuclear data library
nuclear_data:
  library: "endfb71"
  path: "/home/ratth/projects/fusion/nuclear_data/endfb-vii.1-hdf5/"
```

### Validation Rules

Implemented in `aonp/schemas/study.py`:

```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Literal

class NuclideSpec(BaseModel):
    name: str = Field(..., pattern=r'^[A-Z][a-z]?\d+$')
    fraction: float = Field(..., gt=0.0, le=1.0)
    fraction_type: Literal["ao", "wo"] = "ao"

class MaterialSpec(BaseModel):
    density: float = Field(..., gt=0.0)
    density_units: Literal["g/cm3", "atom/b-cm"] = "g/cm3"
    temperature: float = Field(..., gt=0.0)
    nuclides: List[NuclideSpec]
    
    @field_validator('nuclides')
    def validate_fractions(cls, v):
        """Ensure fractions sum to approximately 1.0."""
        total = sum(n.fraction for n in v)
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Nuclide fractions must sum to 1.0 (got {total})")
        return v

class SettingsSpec(BaseModel):
    batches: int = Field(..., gt=0)
    inactive: int = Field(..., ge=0)
    particles: int = Field(..., gt=0)
    seed: int = Field(default=42)
    
    @field_validator('inactive')
    def validate_inactive(cls, v, info):
        """Ensure inactive < batches."""
        if 'batches' in info.data and v >= info.data['batches']:
            raise ValueError("inactive must be less than batches")
        return v

class StudySpec(BaseModel):
    name: str
    description: str = ""
    materials: Dict[str, MaterialSpec]
    geometry: GeometrySpec
    settings: SettingsSpec
    nuclear_data: NuclearDataSpec
    
    def get_canonical_hash(self) -> str:
        """Generate deterministic SHA256 hash."""
        import json, hashlib
        data = self.model_dump()
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

---

## Execution Pipeline

### Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OPENMC EXECUTION PIPELINE                         │
│                    (Single Run Lifecycle)                           │
└─────────────────────────────────────────────────────────────────────┘

STEP 1: VALIDATION
──────────────────
Input: study.yaml
   │
   ├─▶ YAML parsing
   ├─▶ Pydantic validation
   ├─▶ Type checking
   └─▶ Physical constraint validation
   │
   ✓ StudySpec object created


STEP 2: HASHING
───────────────
Input: StudySpec
   │
   ├─▶ Convert to dict
   ├─▶ JSON serialization (sorted keys)
   └─▶ SHA256 hashing
   │
   ✓ spec_hash = "a1b2c3d4e5f6g7h8..."


STEP 3: BUNDLING
────────────────
Input: StudySpec + spec_hash
   │
   ├─▶ Create directory: runs/run_{random_id}/
   ├─▶ Write study_spec.json (canonical)
   ├─▶ Write run_manifest.json (provenance)
   ├─▶ Write nuclear_data.ref.json (data references)
   └─▶ Create inputs/ and outputs/ directories
   │
   ✓ Bundle directory created


STEP 4: XML GENERATION
──────────────────────
Input: Bundle directory
   │
   ├─▶ Generate inputs/materials.xml
   ├─▶ Execute geometry script → inputs/geometry.xml
   └─▶ Generate inputs/settings.xml
   │
   ✓ OpenMC XML inputs ready


STEP 5: EXECUTION
─────────────────
Input: Bundle directory with XMLs
   │
   ├─▶ Set OPENMC_CROSS_SECTIONS env var
   ├─▶ Set OMP_NUM_THREADS
   ├─▶ Run: openmc.run(cwd="inputs/")
   │   │
   │   ├─▶ [Initialize: Load nuclear data]
   │   ├─▶ [Inactive batches: Converge source]
   │   └─▶ [Active batches: Accumulate statistics]
   │
   └─▶ Write outputs/statepoint.120.h5
   │
   ✓ Simulation completed


STEP 6: EXTRACTION
──────────────────
Input: outputs/statepoint.120.h5
   │
   ├─▶ Load with openmc.StatePoint()
   ├─▶ Extract k-effective
   ├─▶ Extract uncertainties
   ├─▶ Extract batch statistics
   └─▶ Convert to DataFrame
   │
   └─▶ Write outputs/summary.parquet
   │
   ✓ Results extracted


STEP 7: PERSISTENCE (Future)
────────────────────────────
Input: summary.parquet + run_manifest.json
   │
   ├─▶ MongoDB: summaries.insert_one()
   ├─▶ MongoDB: runs.update_one({status: "completed"})
   └─▶ MongoDB: events.insert_one({type: "run_completed"})
   │
   ✓ Results queryable in database


ERROR HANDLING AT EACH STEP:
────────────────────────────
• Validation error → Return 400 with error details
• Hashing error → Impossible (deterministic)
• Bundle creation error → Check disk space, permissions
• XML generation error → Check geometry script syntax
• Execution error → Log to manifest, mark run as failed
• Extraction error → Check statepoint file integrity
• Persistence error → Retry with exponential backoff
```

### Command-Line Execution

```bash
# Full pipeline (recommended)
python -m aonp.api.main submit examples/simple_pincell.yaml

# Manual step-by-step execution
# Step 1: Create bundle
python -c "
from pathlib import Path
import yaml
from aonp.schemas.study import StudySpec
from aonp.core.bundler import create_run_bundle

with open('examples/simple_pincell.yaml') as f:
    study = StudySpec(**yaml.safe_load(f))

run_dir, spec_hash = create_run_bundle(study)
print(f'Bundle created: {run_dir}')
"

# Step 2: Run simulation
python -m aonp.runner.entrypoint ./runs/run_<hash>

# Step 3: Extract results
python -c "
from aonp.core.extractor import create_summary
from pathlib import Path

sp_file = Path('./runs/run_<hash>/outputs/statepoint.120.h5')
summary = create_summary(sp_file)
print(f'Results: {summary}')
"
```

---

## Nuclear Data Management

### Cross-Section Libraries

OpenMC uses continuous-energy cross-section data in HDF5 format.

**Supported Libraries**:

| Library | Version | Size | Download URL |
|---------|---------|------|--------------|
| ENDF/B-VII.1 | 2011 | ~1 GB | [ANL Box](https://anl.box.com/shared/static/9igk353zpy8fn9ttvtrqgzvw1vtejoz6.xz) |
| ENDF/B-VIII.0 | 2018 | ~2 GB | [OpenMC Data](https://openmc.org/official-data-libraries/) |
| JEFF-3.3 | 2017 | ~2 GB | [NEA](https://www.oecd-nea.org/dbdata/jeff/) |

### Data Directory Structure

```
~/nuclear_data/
├── endfb-vii.1-hdf5/
│   ├── cross_sections.xml         # Index file (OpenMC reads this)
│   ├── H1.h5                       # Hydrogen-1 cross sections
│   ├── O16.h5                      # Oxygen-16 cross sections
│   ├── U235.h5                     # Uranium-235 cross sections
│   ├── U238.h5                     # Uranium-238 cross sections
│   └── ... (400+ nuclides)
│
└── endfb-viii.0-hdf5/
    ├── cross_sections.xml
    └── ...
```

### Cross Sections XML Format

```xml
<?xml version="1.0"?>
<cross_sections>
  <library materials="H1" path="H1.h5" type="neutron"/>
  <library materials="O16" path="O16.h5" type="neutron"/>
  <library materials="U235" path="U235.h5" type="neutron"/>
  <library materials="U238" path="U238.h5" type="neutron"/>
  <!-- ... -->
</cross_sections>
```

### Environment Configuration

```bash
# Set globally (add to ~/.bashrc)
export OPENMC_CROSS_SECTIONS=~/nuclear_data/endfb-vii.1-hdf5/cross_sections.xml

# Or set per-run (in entrypoint.py)
os.environ['OPENMC_CROSS_SECTIONS'] = '/path/to/cross_sections.xml'

# Verify
python -c "import openmc; print(openmc.config.get('cross_sections'))"
```

### Nuclear Data in Study Spec

```yaml
nuclear_data:
  library: "endfb71"  # Library identifier
  path: "/home/user/nuclear_data/endfb-vii.1-hdf5/"
  
  # Optional: temperature interpolation
  temperature_method: "interpolation"  # or "nearest"
  temperature_tolerance: 200  # Kelvin
```

### Data Provenance

The `nuclear_data.ref.json` file tracks exact data used:

```json
{
  "library": "endfb71",
  "version": "VII.1",
  "cross_sections_path": "/home/ratth/nuclear_data/endfb-vii.1-hdf5/cross_sections.xml",
  "nuclides": [
    {
      "name": "U235",
      "file": "U235.h5",
      "sha256": "a1b2c3d4e5f6...",
      "temperature_range": [293.6, 2500.0],
      "energy_max": 20000000.0
    },
    {
      "name": "U238",
      "file": "U238.h5",
      "sha256": "f6e5d4c3b2a1...",
      "temperature_range": [293.6, 2500.0],
      "energy_max": 20000000.0
    }
  ],
  "timestamp": "2026-01-08T18:09:44Z"
}
```

---

## Result Extraction

### Statepoint File Structure

OpenMC writes binary HDF5 files with the following structure:

```
statepoint.120.h5
├── /k_combined         [Dataset] Combined k-effective estimator
│   ├── mean = 1.60991
│   ├── std_dev = 0.00087
│   └── confidence_intervals = [...]
│
├── /k_collision        [Dataset] Collision estimator
├── /k_absorption       [Dataset] Absorption estimator
├── /k_tracklength      [Dataset] Track-length estimator
│
├── /generations        [Dataset] Per-batch k-effective values
│   └── shape = (120,)
│
├── /entropy            [Dataset] Shannon entropy per batch
│   └── shape = (120,)
│
├── /tallies/
│   ├── tally_1/
│   │   ├── results     [Dataset] Tally scores
│   │   ├── sum         [Dataset] Sum of scores
│   │   └── ...
│   └── ...
│
└── /source_bank        [Dataset] Fission source distribution
```

### Extraction API

```python
import openmc
import pandas as pd

# Load statepoint
sp = openmc.StatePoint("outputs/statepoint.120.h5")

# K-effective with uncertainty
keff = sp.keff.nominal_value  # 1.60991
keff_std = sp.keff.std_dev    # 0.00087

# Batch k-effective evolution
batch_keff = sp.k_generation  # NumPy array

# Entropy evolution (convergence diagnostic)
entropy = sp.entropy  # NumPy array

# Tallies (if defined)
for tally in sp.tallies.values():
    df = tally.get_pandas_dataframe()
    print(df)
```

### Summary Parquet Schema

```python
# Simple summary format
{
    'run_id': 'run_e7f8g9h0',
    'spec_hash': 'spec_a1b2c3d4',
    'keff': 1.60991,
    'keff_std': 0.00087,
    'keff_uncertainty_pcm': 87.0,
    'n_batches': 120,
    'n_inactive': 20,
    'n_particles': 10000,
    'runtime_s': 7.225,
    'timestamp': '2026-01-08T18:09:44'
}
```

### Batch Statistics Export

For detailed analysis, export batch-by-batch data:

```python
def export_batch_statistics(sp: openmc.StatePoint) -> pd.DataFrame:
    """Export per-batch statistics."""
    df = pd.DataFrame({
        'batch': range(1, sp.n_batches + 1),
        'keff': sp.k_generation,
        'entropy': sp.entropy,
        'active': [i >= sp.n_inactive for i in range(sp.n_batches)]
    })
    return df

# Usage
df_batches = export_batch_statistics(sp)
df_batches.to_parquet("batch_statistics.parquet")
```

---

## Provenance and Reproducibility

### Deterministic Execution

**Guaranteed Reproducibility**:

Given the same:
1. `spec_hash` (input configuration)
2. `seed` (random number generator seed)
3. `openmc_version` (OpenMC version)
4. `nuclear_data` (cross-section library + version)

You will get **identical results** (bit-for-bit k-effective values).

### Provenance Chain

```
study.yaml (user input)
    │
    ▼
spec_hash = sha256(canonical_study_spec)
    │
    ▼
run_id = f"run_{random_suffix}"
    │
    ▼
run_manifest.json
    ├── input_hash: spec_hash
    ├── run_id: run_id
    ├── timestamp: ISO8601
    ├── openmc_version: "0.15.3"
    ├── nuclear_data: {...}
    └── runtime_seconds: 7.225
    │
    ▼
summary.parquet
    ├── run_id: run_id
    ├── spec_hash: spec_hash
    ├── keff: 1.60991
    └── ...
    │
    ▼
MongoDB: summaries collection
    ├── _id: ObjectId(...)
    ├── run_id: "run_e7f8g9h0"
    ├── spec_hash: "spec_a1b2c3d4"
    ├── keff: 1.60991
    └── created_at: ISODate(...)
```

### Reproducibility Test

```python
def test_reproducibility():
    """Verify two runs with same inputs produce identical results."""
    
    # Run 1
    study = StudySpec(**yaml.safe_load(open("study.yaml")))
    run_dir_1, hash_1 = create_run_bundle(study)
    run_simulation(run_dir_1)
    results_1 = extract_results(run_dir_1 / "outputs/statepoint.120.h5")
    
    # Run 2 (same study, different run_id)
    run_dir_2, hash_2 = create_run_bundle(study)
    run_simulation(run_dir_2)
    results_2 = extract_results(run_dir_2 / "outputs/statepoint.120.h5")
    
    # Verify
    assert hash_1 == hash_2, "Input hashes must match"
    assert results_1['keff'] == results_2['keff'], "k-eff must match exactly"
    assert results_1['keff_std'] == results_2['keff_std'], "Uncertainties must match"
    
    print("✓ Reproducibility verified")
```

---

## Error Handling

### Common Errors and Solutions

#### 1. Missing Boundary Conditions

**Error**:
```
RuntimeError: No boundary conditions were applied to any surfaces!
```

**Cause**: Geometry script didn't specify boundary conditions.

**Solution**:
```python
# In geometry script, mark outer surface:
outer_surface.boundary_type = 'reflective'  # or 'vacuum'
```

#### 2. Lost Particles

**Error**:
```
RuntimeError: Maximum number of lost particles has been reached
```

**Cause**: Geometry gaps or overlaps, particles escaping defined space.

**Solution**:
- Check cell definitions for complete space filling
- Verify surface equations
- Add `geometry.check()` before simulation

```python
geometry = module.create_geometry(materials)
geometry.check()  # Validates geometry integrity
```

#### 3. Nuclear Data Not Found

**Error**:
```
FileNotFoundError: Cross sections XML file not found
```

**Cause**: `OPENMC_CROSS_SECTIONS` environment variable not set.

**Solution**:
```bash
export OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml
```

#### 4. Memory Errors (Large Simulations)

**Error**:
```
MemoryError: Unable to allocate array
```

**Cause**: Too many particles or tallies.

**Solution**:
- Reduce `particles` per batch
- Increase `batches` to maintain statistics
- Use tally filters to reduce memory footprint

### Error Recovery

```python
def run_with_retry(run_dir: Path, max_attempts: int = 3) -> int:
    """Execute simulation with retry logic."""
    
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Attempt {attempt}/{max_attempts}")
            exit_code = run_simulation(run_dir)
            
            if exit_code == 0:
                return 0
            
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            
            if attempt < max_attempts:
                # Exponential backoff
                wait_time = 2 ** attempt
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
    
    print("All attempts failed")
    return 1
```

---

## Performance Considerations

### Threading Configuration

OpenMC uses OpenMP for shared-memory parallelism:

```bash
# Set thread count (recommended: leave 2 cores for system)
export OMP_NUM_THREADS=22  # for 24-core system

# Thread affinity (can improve cache locality)
export OMP_PROC_BIND=true
export OMP_PLACES=cores
```

**Performance Scaling**:
- **Ideal**: Linear speedup up to ~16 threads
- **Typical**: 80-90% efficiency up to 32 threads
- **Diminishing returns**: Beyond 64 threads

### Memory Requirements

**Per-particle memory** (approximate):
- Base: ~100 KB
- With tallies: +50-200 KB per tally
- With depletion: +500 KB

**Example**:
- 10,000 particles/batch × 100 KB = ~1 GB RAM
- With 5 tallies: ~2 GB RAM

### Batch Size Optimization

```yaml
# Option A: Many small batches (better convergence monitoring)
batches: 500
inactive: 50
particles: 5000

# Option B: Fewer large batches (less overhead)
batches: 100
inactive: 10
particles: 25000

# Same total active particles: 450,000
# Option B is ~10% faster due to reduced synchronization
```

### Disk I/O Optimization

```python
# In settings.xml, control output frequency
settings = openmc.Settings()

# Write statepoint every N batches (default: only last batch)
settings.statepoint = {'batches': [100, 120]}  # Write at batch 100 and 120

# Reduce output verbosity
settings.verbosity = 6  # 1-10 scale (lower = less output)

# Disable summary output (if not needed)
settings.output = {'summary': False}
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_bundler.py
def test_bundle_creation():
    """Test bundle directory structure."""
    study = StudySpec(**yaml.safe_load(open("examples/simple_pincell.yaml")))
    run_dir, spec_hash = create_run_bundle(study)
    
    assert run_dir.exists()
    assert (run_dir / "study_spec.json").exists()
    assert (run_dir / "run_manifest.json").exists()
    assert (run_dir / "inputs").exists()
    assert (run_dir / "outputs").exists()

def test_hash_stability():
    """Test that hash is format-independent."""
    yaml1 = "name: test\nmaterials: {}"
    yaml2 = "name:  test  \nmaterials:   {}\n"  # Extra whitespace
    
    study1 = StudySpec(**yaml.safe_load(yaml1))
    study2 = StudySpec(**yaml.safe_load(yaml2))
    
    assert study1.get_canonical_hash() == study2.get_canonical_hash()
```

### Integration Tests

```python
# tests/test_integration.py
def test_full_pipeline():
    """Test complete workflow from YAML to results."""
    # Load study
    with open("examples/simple_pincell.yaml") as f:
        study = StudySpec(**yaml.safe_load(f))
    
    # Create bundle
    run_dir, spec_hash = create_run_bundle(study)
    
    # Run simulation (requires OpenMC + nuclear data)
    exit_code = run_simulation(run_dir)
    assert exit_code == 0, "Simulation failed"
    
    # Extract results
    sp_file = run_dir / "outputs" / "statepoint.120.h5"
    assert sp_file.exists(), "Statepoint file not created"
    
    results = extract_results(sp_file)
    assert 1.5 < results['keff'] < 1.7, "k-eff out of expected range"
    assert results['keff_std'] < 0.01, "Uncertainty too large"
```

### Regression Tests

```python
# tests/test_regression.py
def test_keff_regression():
    """Verify k-eff hasn't changed for reference case."""
    study = StudySpec(**yaml.safe_load(open("examples/simple_pincell.yaml")))
    run_dir, _ = create_run_bundle(study)
    run_simulation(run_dir)
    
    results = extract_results(run_dir / "outputs/statepoint.120.h5")
    
    # Reference value from validation run
    expected_keff = 1.60991
    tolerance = 0.00300  # ~3 sigma
    
    assert abs(results['keff'] - expected_keff) < tolerance, \
        f"k-eff regression: {results['keff']} vs {expected_keff}"
```

---

## Future Enhancements

### Phase 1: Tally Support

```yaml
# In study.yaml, add tallies section
tallies:
  - name: "flux_distribution"
    type: "mesh"
    filters:
      - type: "energy"
        bins: [0.0, 0.625, 1e7]
    scores: ["flux"]
    mesh:
      type: "regular"
      lower_left: [-0.62, -0.62, -1.0]
      upper_right: [0.62, 0.62, 1.0]
      dimension: [50, 50, 1]
```

### Phase 2: Depletion Calculations

```yaml
# Burnup/depletion support
depletion:
  timesteps: [30, 30, 30, 30]  # days
  power: 174.0  # W/gHM
  integrator: "predictor"
  chain_file: "chain_endfb71.xml"
```

### Phase 3: Distributed Execution

- **Celery** integration for task queuing
- **Ray** for distributed computing
- **Slurm** connector for HPC clusters
- **Temporal** workflows for orchestration

### Phase 4: Advanced Analysis

- Sensitivity and uncertainty analysis (S/U)
- Adjoint-weighted perturbation theory
- Multi-group cross-section generation
- Reactor kinetics parameters (β_eff, Λ)

---

## Appendix: Reference Configuration

### Complete Working Example

**File**: `examples/simple_pincell.yaml`

```yaml
name: "simple_pincell_v1"
description: "Single UO2 fuel pin cell for validation"

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
  batches: 120
  inactive: 20
  particles: 10000
  seed: 42

nuclear_data:
  library: "endfb71"
  path: "/home/ratth/projects/fusion/nuclear_data/endfb-vii.1-hdf5/"
```

**Execution**:

```bash
# Validate and run
python -c "
import yaml
from pathlib import Path
from aonp.schemas.study import StudySpec
from aonp.core.bundler import create_run_bundle
from aonp.runner.entrypoint import run_simulation
from aonp.core.extractor import create_summary

# Load and validate
with open('examples/simple_pincell.yaml') as f:
    study = StudySpec(**yaml.safe_load(f))

print(f'Study: {study.name}')
print(f'Hash: {study.get_canonical_hash()}')

# Create bundle
run_dir, spec_hash = create_run_bundle(study)
print(f'Bundle: {run_dir}')

# Execute
exit_code = run_simulation(run_dir)
print(f'Exit code: {exit_code}')

# Extract
if exit_code == 0:
    sp_file = run_dir / 'outputs' / 'statepoint.120.h5'
    summary = create_summary(sp_file)
    print(f'Results: {summary}')
"
```

**Expected Output**:

```
Study: simple_pincell_v1
Hash: a1b2c3d4e5f6g7h8i9j0...
Bundle: runs/run_k1l2m3n4o5p6/
Run ID: run_k1l2m3n4o5p6
Spec Hash: spec_a1b2c3d4e5f6

========================================
Starting OpenMC simulation...
========================================

 ===================================================================
 |                  OpenMC 0.15.3 (commit 27e38e8)                |
 ===================================================================

 Reading settings XML file...
 Reading cross sections XML file...
 Reading materials XML file...
 Reading geometry XML file...
 Building neighboring cells lists for each surface...
 Initializing source particles...

 ====================>     K EIGENVALUE SIMULATION     <====================

  Bat./Gen.      k            Average k
  =========   ========   ====================
        1       1.58234
        2       1.62157
        ...
      120       1.61193
 Creating state point statepoint.120.h5...

 ===================================================================
 |                      TIMING STATISTICS                         |
 ===================================================================
 Total time for simulation     = 7.225e+00 sec
   Inactive batches            = 1.418e+00 sec
   Active batches              = 5.808e+00 sec
 ===================================================================

✓ Simulation completed in 7.23 seconds
Exit code: 0

[OK] Extracted results to: runs/run_k1l2m3n4o5p6/outputs/summary.parquet
  k-eff: 1.609905 +/- 0.000871
  Batches: 120
```

---

## Conclusion

This OpenMC integration design provides:

✅ **Complete reproducibility** through deterministic hashing  
✅ **Full provenance tracking** from input to output  
✅ **Robust error handling** with retry mechanisms  
✅ **Performance optimization** guidance for large-scale simulations  
✅ **Comprehensive testing** strategy for validation  

**Status**: Production-ready for single-node execution  
**Next Steps**: Distributed execution (Temporal workflows) + parameter sweeps  

---

**Document Version**: 1.0  
**Last Updated**: January 10, 2026  
**Maintained by**: AONP Development Team


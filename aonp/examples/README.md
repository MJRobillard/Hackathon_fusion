# AONP Examples

This directory contains example studies for testing and validation.

## Simple Pin Cell

**File**: `simple_pincell.yaml`

A basic PWR-style fuel pin cell with:
- 3.1% enriched UO2 fuel
- Light water moderator
- Reflective boundary conditions (infinite lattice approximation)

Expected k-effective: ~1.61 (typical for fresh 3% enriched fuel)

### Usage

1. **Update nuclear data path** in `simple_pincell.yaml`:
   ```yaml
   nuclear_data:
     path: "/path/to/your/endfb-vii.1-hdf5/"
   ```

2. **Validate the study**:
   ```python
   import yaml
   from aonp.schemas.study import StudySpec
   
   with open("aonp/examples/simple_pincell.yaml") as f:
       study = StudySpec(**yaml.safe_load(f))
   
   print(f"Hash: {study.get_canonical_hash()}")
   ```

3. **Create run bundle**:
   ```python
   from aonp.core.bundler import create_run_bundle
   
   run_dir, spec_hash = create_run_bundle(study)
   print(f"Bundle: {run_dir}")
   ```

4. **Execute simulation** (requires OpenMC):
   ```bash
   python -m aonp.runner.entrypoint ./runs/run_<hash>
   ```

5. **Extract results**:
   ```python
   from aonp.core.extractor import create_summary
   from pathlib import Path
   
   sp_file = Path("./runs/run_<hash>/outputs/statepoint.120.h5")
   summary = create_summary(sp_file)
   ```

## Geometry Script

**File**: `pincell_geometry.py`

Demonstrates how to create OpenMC geometry for AONP studies.

### Requirements

The geometry script must:
1. Define a `create_geometry(materials_dict)` function
2. Accept a dictionary of OpenMC materials
3. Return an `openmc.Geometry` object

### Example Structure

```python
import openmc

def create_geometry(materials_dict):
    # Extract materials
    fuel = materials_dict['fuel']
    moderator = materials_dict['moderator']
    
    # Define surfaces
    fuel_or = openmc.ZCylinder(r=0.39)
    pin_or = openmc.ZCylinder(r=0.63, boundary_type='reflective')
    
    # Define cells
    fuel_cell = openmc.Cell(fill=fuel, region=-fuel_or)
    mod_cell = openmc.Cell(fill=moderator, region=+fuel_or & -pin_or)
    
    # Create geometry
    geometry = openmc.Geometry([fuel_cell, mod_cell])
    return geometry
```

## Nuclear Data Setup

Before running simulations, you need nuclear cross-section data:

### Quick Setup (Conda)

```bash
conda install -c conda-forge openmc
# Nuclear data is automatically downloaded
```

### Manual Setup

```bash
# Download ENDF/B-VII.1 (recommended, ~1 GB)
mkdir -p ~/nuclear_data
cd ~/nuclear_data
wget https://anl.box.com/shared/static/9igk353zpy8fn9ttvtrqgzvw1vtejoz6.xz \
    -O endfb-vii.1-hdf5.tar.xz
tar -xJf endfb-vii.1-hdf5.tar.xz

# Set environment variable
export OPENMC_CROSS_SECTIONS=~/nuclear_data/endfb-vii.1-hdf5/cross_sections.xml

# Verify
python -c "import openmc; print('OK')"
```

## Testing Your Setup

Run the acceptance test:

```python
# test_acceptance.py
import yaml
from pathlib import Path
from aonp.schemas.study import StudySpec
from aonp.core.bundler import create_run_bundle
from aonp.runner.entrypoint import run_simulation
from aonp.core.extractor import create_summary

# Load study
with open("aonp/examples/simple_pincell.yaml") as f:
    study = StudySpec(**yaml.safe_load(f))

print(f"✓ Study validation passed")
print(f"  Hash: {study.get_canonical_hash()[:12]}...")

# Create bundle
run_dir, spec_hash = create_run_bundle(study)
print(f"✓ Bundle creation passed")
print(f"  Directory: {run_dir}")

# Run simulation
exit_code = run_simulation(run_dir)
assert exit_code == 0, "Simulation failed"
print(f"✓ OpenMC execution passed")

# Extract results
sp_file = run_dir / "outputs" / "statepoint.120.h5"
summary = create_summary(sp_file)
print(f"✓ Result extraction passed")

print("\n✅ All tests passed! System is operational.")
```

## Expected Results

For the simple pin cell:

| Metric | Expected Value | Tolerance |
|--------|---------------|-----------|
| k-effective | 1.609 - 1.611 | ±0.003 |
| Uncertainty | < 100 pcm | - |
| Runtime (10k particles) | 5-10 seconds | - |

Results may vary slightly based on:
- Nuclear data library version
- Number of particles/batches
- Random seed
- OpenMC version


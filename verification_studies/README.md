# OpenMC Verification Studies

A comprehensive suite of test cases to verify your OpenMC installation and demonstrate fusion neutronics modeling capabilities with **moderate runtimes**.

## 📋 Overview

These verification studies are designed like **tuning a musical instrument**:
1. Start with a **single clear note** (toy geometry)
2. Play a **simple scale** (single torus)
3. Attempt a **short piece** (multi-layer reactor)
4. Perform a **complete song** (full reactor model)
5. Master **efficient techniques** (sector slicing)

Each study progressively increases in complexity while maintaining reasonable runtimes for verification purposes.

---

## 🎯 Study Progression

| Study | Model | Runtime | Purpose |
|-------|-------|---------|---------|
| **01** | Two-Volume Toy Geometry | 1-2 min | Basic OpenMC functionality |
| **02** | Single Layered Torus | 5-10 min | Toroidal geometry & ring sources |
| **03** | Multi-Layered Torus | 10-15 min | Tritium breeding & multi-materials |
| **04** | DEMO Reactor Model | 15-30 min | Integral parameters (TBR, heating) |
| **05** | Sector Slicing Model | 5-10 min | Computational efficiency (18-36x speedup) |

**Total verification time: ~40-70 minutes**

---

## 📖 Study Details

### Study 1: Two-Volume Toy Geometry
**File:** `01_toy_geometry.py`

**What it tests:**
- Basic OpenMC installation and nuclear data
- Material definitions
- Simple geometry (concentric spheres)
- Point source with tallies
- Particle transport mechanics

**Model:**
- Inner sphere: Water (10 cm radius)
- Outer shell: Steel (20 cm radius)
- Source: 14 MeV point source at origin
- Particles: 10 batches × 10⁵ particles

**Expected output:**
- Flux, heating, and absorption in both regions
- Quick verification of basic functionality

**Run:**
```bash
python 01_toy_geometry.py
```

---

### Study 2: Single Layered Torus
**File:** `02_single_torus.py`

**What it tests:**
- Toroidal (torus) geometry construction
- Ring source (characteristic of fusion reactors)
- Cylindrical mesh tallies
- Tokamak topology fundamentals

**Model:**
- Major radius: 4.0 m
- Minor radius: 1.5 - 1.7 m (20 cm wall)
- Material: Stainless steel 316
- Source: Ring source at major radius, 14 MeV neutrons

**Expected output:**
- Toroidal flux distribution
- Heating in steel wall
- Mesh tally for visualization

**Run:**
```bash
python 02_single_torus.py
```

---

### Study 3: Multi-Layered Torus
**File:** `03_multi_torus.py`

**What it tests:**
- Multi-material interfaces
- Tritium breeding calculations (TBR)
- Neutron multiplication (Be reactions)
- Realistic fusion blanket design

**Model:**
- Major radius: 4.0 m
- Layers:
  - Plasma region (r < 1.4 m)
  - Tungsten first wall (5 cm)
  - Li₄SiO₄ + Be blanket (50 cm, 30% Li-6 enrichment)
  - Steel vacuum vessel (15 cm)
- Source: Ring source at plasma edge

**Key metrics:**
- **Tritium Breeding Ratio (TBR)**: Must be > 1.0 for self-sustaining reactor
- Neutron multiplication from Be(n,2n) reactions
- Heating distribution across components

**Expected output:**
- TBR calculation
- Component-wise heating
- Neutron multiplication rates
- Spatial mesh tallies

**Run:**
```bash
python 03_multi_torus.py
```

---

### Study 4: Low-Fidelity DEMO Reactor Model
**File:** `04_reactor_model.py`

**What it tests:**
- Full-scale DEMO-class tokamak
- Integral parameter calculations
- Inboard vs. outboard blanket differences
- Realistic blanket configurations

**Model:**
- Major radius: 9.0 m (DEMO scale)
- Components:
  - Deuterium-tritium plasma
  - Tungsten first wall
  - Dual breeding blankets (inboard/outboard with different enrichments)
  - EUROFER steel structure
  - Neutron shield
  - Vacuum vessel
- Source: Volumetric plasma source
- Particles: 100,000 neutrons over 30 batches

**Key metrics:**
- Total TBR (inboard + outboard contributions)
- Energy multiplication factor
- Heating by component
- Neutron flux distributions

**Expected output:**
- Comprehensive integral parameters
- TBR > 1.0 verification
- Total heating deposition (~14 MeV per neutron)
- Performance metrics (particles/second)

**Run:**
```bash
python 04_reactor_model.py
```

**Notes:**
- Runtime scales with particle count
- Can reduce to 50,000 particles for faster verification
- Results converge with increased statistics

---

### Study 5: Sector Slicing Model
**File:** `05_sector_model.py`

**What it tests:**
- Computational efficiency through symmetry
- Reflective boundary conditions
- Memory reduction strategies
- Equivalent accuracy with reduced domain

**Model:**
- Sector angle: 10° or 20° (user configurable)
- Major radius: 6.0 m
- Layers: First wall, blanket, vessel
- Boundaries: **Reflective at azimuthal edges**
- Particles: 100,000 over 25 batches

**Efficiency gains:**
- **10° sector**: 36× faster than full 360° geometry
- **20° sector**: 18× faster than full geometry
- Memory reduction: Proportional to angular fraction
- **Precision**: Identical for toroidally-symmetric systems

**Key insight:**
For axisymmetric tokamak designs, modeling only a small wedge with reflective boundaries gives identical results to the full geometry, with massive computational savings.

**Results scaling:**
- **Volumetric quantities** (heating): Multiply by (360°/sector angle)
- **Intensive properties** (TBR, flux ratios): No scaling needed
- **Mesh tallies**: Only need to cover sector, not full torus

**Expected output:**
- TBR (same as full geometry)
- Scaled heating distributions
- Computational efficiency metrics
- Time savings analysis

**Run:**
```bash
python 05_sector_model.py
```

**Customization:**
Change sector angle in the script:
```python
SECTOR_ANGLE = 20.0  # Try 10.0 or 36.0
```

---

## 🚀 Quick Start

### Prerequisites

1. **OpenMC installed** (version ≥ 0.13.0 recommended)
   ```bash
   conda install -c conda-forge openmc
   ```
   or
   ```bash
   pip install openmc
   ```

2. **Nuclear data library** configured
   - Download ENDF/B-VII.1 or newer
   - Set environment variable:
     ```bash
     export OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml
     ```

3. **Python packages**
   ```bash
   pip install numpy pandas h5py
   ```

### Running All Studies

**Sequential execution:**
```bash
python 01_toy_geometry.py
python 02_single_torus.py
python 03_multi_torus.py
python 04_reactor_model.py
python 05_sector_model.py
```

**Batch script (Unix/Linux):**
```bash
#!/bin/bash
for study in 01_toy_geometry.py 02_single_torus.py 03_multi_torus.py \
             04_reactor_model.py 05_sector_model.py; do
    echo "Running $study..."
    python $study
    if [ $? -ne 0 ]; then
        echo "Study $study failed!"
        exit 1
    fi
done
echo "All verification studies passed!"
```

**PowerShell (Windows):**
```powershell
$studies = @(
    "01_toy_geometry.py",
    "02_single_torus.py",
    "03_multi_torus.py",
    "04_reactor_model.py",
    "05_sector_model.py"
)

foreach ($study in $studies) {
    Write-Host "Running $study..." -ForegroundColor Cyan
    python $study
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Study $study failed!" -ForegroundColor Red
        exit 1
    }
}
Write-Host "All verification studies passed!" -ForegroundColor Green
```

---

## 📊 Output Files

Each study creates an output directory with:

```
{study_name}_output/
├── materials.xml      # Material definitions
├── geometry.xml       # Geometry specification
├── settings.xml       # Simulation settings
├── tallies.xml        # Tally definitions
├── statepoint.*.h5    # Results (HDF5 format)
├── summary.h5         # Geometry/material summary
└── tallies.out        # Text output (if verbose)
```

### Reading Results

**Python:**
```python
import openmc

# Load statepoint
sp = openmc.StatePoint('statepoint.30.h5')

# Get tally by name
tally = sp.get_tally(name='TBR')
df = tally.get_pandas_dataframe()
print(df)

# Access mesh tallies
mesh_tally = sp.get_tally(name='mesh_heating')
mean_values = mesh_tally.mean
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. "Nuclear data library not found"
```
Error: could not find cross_sections.xml
```
**Solution:**
```bash
export OPENMC_CROSS_SECTIONS=/path/to/your/cross_sections.xml
```

#### 2. "Lost particles" or geometry errors
```
Error: Particle ... was lost
```
**Solutions:**
- Check geometry boundaries are properly closed
- Verify material assignments
- Inspect geometry visually (use `openmc-plotter` or plots.xml)

#### 3. "Material XYZ not found in nuclear data"
```
Error: Nuclide Li6 not found in nuclear data library
```
**Solution:**
- Ensure your nuclear data library includes all required isotopes
- Use ENDF/B-VII.1 or ENDF/B-VIII.0 (comprehensive libraries)

#### 4. Slow performance
**Solutions:**
- Reduce particle count for initial verification
- Enable multiprocessing: `openmc.run(threads=4)`
- Use sector slicing (Study 5) for large geometries
- Check system resources (memory, CPU)

#### 5. TBR results seem wrong
**Common issues:**
- Forgot to normalize by source rate
- Missing lithium isotopes in nuclear data
- Blanket too thin or enrichment too low

---

## 📈 Performance Tips

### Multiprocessing
Enable parallel execution:
```python
import openmc
openmc.run(threads=8)  # Use 8 CPU cores
```

Or set in settings:
```python
settings.threads = 8
```

### Memory Management
For large mesh tallies:
- Start with coarse meshes (10³-10⁴ elements)
- Gradually increase resolution
- Use sector models to reduce domain size

### Adaptive Sampling
For better statistics in specific regions:
```python
# Use energy filters for thermal vs. fast neutrons
energy_filter = openmc.EnergyFilter([0, 0.625, 20e6])
```

---

## 📚 Key Concepts Tested

### 1. Tritium Breeding Ratio (TBR)
```
TBR = (Tritium atoms produced) / (Neutrons from fusion)
```
- **TBR > 1.0**: Self-sustaining (required for fusion power plants)
- **TBR < 1.0**: Need external tritium supply

**Main reactions:**
- ⁶Li(n,t)α: ~4.8 MeV (exothermic)
- ⁷Li(n,n't)α: -2.5 MeV (requires E_n > 2.5 MeV)

### 2. Neutron Multiplication
Beryllium reactions:
- ⁹Be(n,2n): Doubles neutron population
- Critical for achieving TBR > 1.0

### 3. Energy Deposition
Total energy per D-T fusion:
- Fusion products: 17.6 MeV
  - Neutron: 14.08 MeV
  - Alpha particle: 3.52 MeV (stays in plasma)
- Blanket captures ~14 MeV + breeding energy

### 4. Computational Efficiency
Sector slicing exploits toroidal symmetry:
- No loss of accuracy for symmetric configurations
- Speedup = 360° / sector_angle
- Essential for parametric studies

---

## 🎓 Next Steps After Verification

Once all studies pass:

### 1. **Production Runs**
- Increase particle counts (10⁶ - 10⁷ particles)
- Add high-resolution mesh tallies
- Enable variance reduction techniques

### 2. **Parameter Studies**
- Blanket thickness optimization
- Li-6 enrichment sweeps
- Material comparisons (Li₄SiO₄ vs. Pb-Li)

### 3. **Advanced Physics**
- Photon transport (add `settings.photon_transport = True`)
- Activation and decay (using `openmc.deplete`)
- Coupled neutron-photon heating

### 4. **Visualization**
Create plots for publication:
```python
# Create geometry plot
plot = openmc.Plot()
plot.filename = 'reactor_cross_section'
plot.basis = 'xz'
plot.origin = [0, 0, 0]
plot.width = [20, 20]
plot.pixels = [1000, 1000]
plot.color_by = 'material'

plots = openmc.Plots([plot])
plots.export_to_xml()
openmc.plot_geometry()
```

### 5. **Integration with AONP Framework**
These verification studies validate OpenMC for use with the AONP system:
```bash
# Submit verified models through AONP API
python -m aonp.api.main
```

---

## 📖 References

### OpenMC Documentation
- Official docs: https://docs.openmc.org
- GitHub: https://github.com/openmc-dev/openmc
- User's guide: https://docs.openmc.org/en/stable/usersguide/

### Fusion Neutronics
- ITER Physics Basis: https://www.iter.org
- Fusion Energy Neutronics Workshop materials
- DEMO reactor design studies

### Nuclear Data
- ENDF/B-VIII.0: https://www.nndc.bnl.gov/endf-b8.0/
- JEFF libraries: https://www.oecd-nea.org/janisweb/

---

## ✅ Verification Checklist

After running all studies, verify:

- [ ] Study 1 completes in < 5 minutes
- [ ] Study 2 shows toroidal flux distribution
- [ ] Study 3 calculates TBR (value between 0.5-1.5 expected)
- [ ] Study 4 completes DEMO model in < 30 minutes
- [ ] Study 5 demonstrates computational speedup
- [ ] All statepoint files generated successfully
- [ ] No "lost particle" errors
- [ ] Tally uncertainties < 5% (increase particles if needed)
- [ ] TBR trends match physical expectations
- [ ] Heating totals ~14 MeV per fusion neutron

---

## 🤝 Contributing

Found an issue or have improvements?
1. Check existing issues
2. Submit detailed bug reports
3. Propose enhancements with use cases

---

## 📜 License

These verification studies are provided as educational examples for OpenMC users.
OpenMC is distributed under the MIT license.

---

## 🎉 Congratulations!

If all verification studies pass, your OpenMC installation is **fully functional** and ready for:
- Production fusion neutronics calculations
- Reactor design optimization
- Research-grade simulations
- Integration with the AONP automated workflow

**Happy neutron transport modeling! 🚀**

---

## Analogy Recap

> Verifying your OpenMC setup is like **tuning a musical instrument**:
> 
> 1. **Toy Geometry** = Single note (pitch check)
> 2. **Single Torus** = Simple scale (mechanics smooth)
> 3. **Multi-Layer Torus** = Short simplified piece (system integration)
> 4. **DEMO Reactor** = Complete song (full performance)
> 5. **Sector Model** = Efficient practice technique (smart rehearsal)

Now you're ready to compose your own fusion reactor symphony! 🎼🎵


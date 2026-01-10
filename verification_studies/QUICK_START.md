# Quick Start Guide - OpenMC Verification Studies

**Goal:** Verify your OpenMC installation in ~40-70 minutes with 5 progressive test cases.

---

## ⚡ Fastest Path to Verification

### 1️⃣ Prerequisites Check (2 minutes)

```bash
# Check OpenMC installation
python -c "import openmc; print(f'OpenMC version: {openmc.__version__}')"

# Check nuclear data
echo $OPENMC_CROSS_SECTIONS

# If not set:
# export OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml
```

**Requirements:**
- OpenMC ≥ 0.13.0
- Nuclear data library (ENDF/B-VII.1 or newer)
- Python packages: `numpy`, `pandas`, `h5py`

---

### 2️⃣ Run All Studies (40-70 minutes)

**Option A: Automated (recommended)**
```bash
cd verification_studies
python run_all_studies.py
```

**Option B: Manual (one by one)**
```bash
python 01_toy_geometry.py      # ~2 min
python 02_single_torus.py       # ~8 min
python 03_multi_torus.py        # ~12 min
python 04_reactor_model.py      # ~25 min
python 05_sector_model.py       # ~8 min
```

---

### 3️⃣ Check Results

Look for these success indicators:

✅ **Study 1:** 
```
✓ VERIFICATION PASSED
Your OpenMC installation is working correctly!
```

✅ **Study 2:**
```
✓ VERIFICATION PASSED
Toroidal geometry working correctly!
```

✅ **Study 3:**
```
✓ VERIFICATION PASSED
Multi-layer fusion reactor simulation working!
```

✅ **Study 4:**
```
✓✓✓ VERIFICATION PASSED ✓✓✓
Full-scale DEMO reactor simulation successful!
```

✅ **Study 5:**
```
✓✓✓ VERIFICATION PASSED ✓✓✓
Sector slicing strategy validated!
```

---

## 📊 What Each Study Tests

| Study | What It Verifies | Key Output |
|-------|------------------|------------|
| **01** | Basic installation | Flux & heating in 2 volumes |
| **02** | Toroidal geometry | Ring source, cylindrical mesh |
| **03** | Breeding blanket | TBR calculation |
| **04** | Full reactor | Integral parameters (TBR, heating) |
| **05** | Efficiency tricks | 18-36× speedup with sectors |

---

## 🆘 Common Issues

### ❌ "Nuclear data not found"
```bash
# Download ENDF/B-VII.1
wget https://anl.box.com/shared/static/9igk353zpy8fn9ttvtrqgzvw1vtejoz6.xz -O endfb71_hdf5.tar.xz
tar -xvf endfb71_hdf5.tar.xz

# Set environment variable
export OPENMC_CROSS_SECTIONS=$PWD/endfb-vii.1-hdf5/cross_sections.xml
```

### ❌ "ImportError: No module named openmc"
```bash
# Install OpenMC
conda install -c conda-forge openmc
# or
pip install openmc
```

### ❌ "Lost particles" error
- Geometry issue (boundaries not closed)
- Run with fewer particles first to debug
- Check `geometry.xml` for surface overlaps

### ❌ Slow performance
```python
# Enable multiprocessing in any study:
openmc.run(threads=8)  # Use 8 cores
```

---

## 🎯 Success Criteria

Your installation is verified if:

- ✅ All 5 studies complete without errors
- ✅ TBR values are reasonable (0.5 - 1.5)
- ✅ Total heating ≈ 14 MeV per fusion neutron
- ✅ No "lost particle" messages
- ✅ Tally uncertainties < 10%

---

## 🚀 After Verification

**Increase fidelity:**
```python
# In any study, increase particles:
settings = create_settings(n_particles=1e6, n_batches=50)
```

**Visualize geometry:**
```bash
# Add before openmc.run():
plot = openmc.Plot()
plot.filename = 'geometry'
plot.basis = 'xz'
plot.width = [1000, 1000]
plot.pixels = [1000, 1000]
plot.color_by = 'material'

plots = openmc.Plots([plot])
plots.export_to_xml()
openmc.plot_geometry()
```

**Extract detailed results:**
```python
import openmc
sp = openmc.StatePoint('statepoint.30.h5')

# Get TBR
tbr_tally = sp.get_tally(name='TBR')
df = tbr_tally.get_pandas_dataframe()
print(f"TBR = {df['mean'].sum():.4f}")

# Get heating
heating_tally = sp.get_tally(name='cell_heating')
print(heating_tally.get_pandas_dataframe())
```

---

## 📚 Next Steps

1. **Read full README.md** for detailed explanations
2. **Modify studies** to test different parameters
3. **Integrate with AONP** for automated workflows
4. **Scale up** for production calculations

---

## 🆘 Still Having Issues?

1. Check `README.md` Troubleshooting section
2. Review OpenMC docs: https://docs.openmc.org
3. Verify nuclear data library has all isotopes (Li6, Li7, Be9, etc.)
4. Try reducing particle counts for initial testing

---

**Time estimate:** Setup (5 min) + Running (40-70 min) + Analysis (10 min) = **~1-2 hours total**

**You got this! 🚀**


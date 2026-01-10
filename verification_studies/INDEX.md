# OpenMC Verification Studies - File Index

## 📁 Directory Structure

```
verification_studies/
├── README.md                    ← Start here! Complete guide
├── QUICK_START.md              ← Fast-track verification (1-2 hours)
├── STUDY_COMPARISON.md         ← Detailed comparison matrix
├── INDEX.md                    ← This file
│
├── 01_toy_geometry.py          ← Study 1: Basic functionality
├── 02_single_torus.py          ← Study 2: Toroidal geometry
├── 03_multi_torus.py           ← Study 3: Breeding blanket
├── 04_reactor_model.py         ← Study 4: DEMO reactor
├── 05_sector_model.py          ← Study 5: Efficiency tricks
│
├── run_all_studies.py          ← Automated test runner
│
└── *_output/                   ← Output directories (created at runtime)
    ├── materials.xml
    ├── geometry.xml
    ├── settings.xml
    ├── tallies.xml
    └── statepoint.*.h5
```

---

## 📖 Documentation Files

### **README.md** - Complete Guide
- **Purpose:** Comprehensive documentation for all studies
- **Length:** ~600 lines
- **Content:**
  - Overview of all 5 studies
  - Detailed study descriptions
  - Installation instructions
  - Troubleshooting guide
  - Key concepts (TBR, multiplication, etc.)
  - Performance tips
  - Next steps after verification

**📌 Read this first for complete understanding**

---

### **QUICK_START.md** - Fast Track
- **Purpose:** Get up and running in under 2 hours
- **Length:** ~200 lines
- **Content:**
  - Prerequisites checklist
  - One-command execution
  - Success criteria
  - Common issues and fixes
  - Minimal explanations

**⚡ Use this if you just want to verify ASAP**

---

### **STUDY_COMPARISON.md** - Detailed Analysis
- **Purpose:** Compare all studies side-by-side
- **Length:** ~400 lines
- **Content:**
  - Feature comparison matrix
  - Physics coverage by study
  - Geometry complexity diagrams
  - Scaling analysis
  - Expected results
  - Optimization tips

**🔬 Use this to understand differences and choose studies**

---

### **INDEX.md** - This File
- **Purpose:** Navigate the verification suite
- **Content:** File descriptions and quick reference

---

## 🐍 Python Study Files

### **01_toy_geometry.py**
- **Runtime:** 1-2 minutes
- **Purpose:** Verify basic OpenMC installation
- **Geometry:** Concentric spheres (water + steel)
- **Source:** Point source, 14 MeV
- **Tallies:** Flux, heating, absorption
- **Output:** `toy_geometry_output/`

**What it verifies:**
✅ OpenMC installation  
✅ Nuclear data library  
✅ Basic transport  
✅ Simple geometry  
✅ Tally system  

**Run:** `python 01_toy_geometry.py`

---

### **02_single_torus.py**
- **Runtime:** 5-10 minutes
- **Purpose:** Test toroidal geometry
- **Geometry:** Hollow steel torus (R₀=4m, r=1.5-1.7m)
- **Source:** Ring source, 14 MeV
- **Tallies:** Cell + cylindrical mesh (flux, heating)
- **Output:** `single_torus_output/`

**What it verifies:**
✅ Toroidal surfaces  
✅ Ring sources  
✅ Mesh tallies  
✅ Tokamak topology  

**Run:** `python 02_single_torus.py`

---

### **03_multi_torus.py**
- **Runtime:** 10-15 minutes
- **Purpose:** Test breeding calculations
- **Geometry:** Multi-layer torus
  - Tungsten first wall (5 cm)
  - Li₄SiO₄ + Be blanket (50 cm)
  - Steel vessel (15 cm)
- **Source:** Ring source at plasma edge
- **Tallies:** TBR, heating, flux, multiplication
- **Output:** `multi_torus_output/`

**What it verifies:**
✅ Multi-material interfaces  
✅ TBR calculation  
✅ Neutron multiplication  
✅ Breeding physics  

**Key result:** TBR value (expect 0.6-0.9)

**Run:** `python 03_multi_torus.py`

---

### **04_reactor_model.py**
- **Runtime:** 15-30 minutes
- **Purpose:** Full-scale DEMO reactor
- **Geometry:** DEMO-class tokamak (R₀=9m)
  - Plasma region
  - Tungsten first wall
  - Inboard blanket (low enrichment)
  - Outboard blanket (high enrichment)
  - Steel vessel
- **Source:** Volumetric plasma source
- **Tallies:** Comprehensive integral parameters
- **Output:** `reactor_model_output/`

**What it verifies:**
✅ Large-scale geometry  
✅ Dual-zone blanket  
✅ Integral TBR  
✅ Energy balance  

**Key results:**
- Total TBR (expect 1.0-1.3)
- Heating by component
- Inboard vs outboard contribution

**Run:** `python 04_reactor_model.py`

---

### **05_sector_model.py**
- **Runtime:** 5-10 minutes
- **Purpose:** Demonstrate computational efficiency
- **Geometry:** 20° sector of torus (R₀=6m)
  - Reflective boundaries at sector edges
  - Same layers as full reactor
- **Source:** Ring source (limited to sector)
- **Tallies:** TBR, heating (with scaling instructions)
- **Output:** `sector_model_output/`

**What it verifies:**
✅ Reflective boundaries  
✅ Symmetry exploitation  
✅ Result scaling  
✅ Memory efficiency  

**Key insight:** 18× faster than full 360° model with identical physics!

**Customization:**
Edit `SECTOR_ANGLE` in script (try 10°, 20°, or 36°)

**Run:** `python 05_sector_model.py`

---

## 🤖 Automation Scripts

### **run_all_studies.py**
- **Purpose:** Run all 5 studies sequentially
- **Features:**
  - Automated execution
  - Progress tracking
  - Error handling
  - Summary report generation
  - Selective execution (`--skip`, `--only`)

**Basic usage:**
```bash
python run_all_studies.py
```

**Advanced usage:**
```bash
# Skip study 4 (long runtime)
python run_all_studies.py --skip 4

# Run only study 3
python run_all_studies.py --only 3

# Skip multiple studies
python run_all_studies.py --skip 3 --skip 4

# Custom report filename
python run_all_studies.py --report my_report.txt
```

**Output:**
- Console: Real-time progress and summary
- File: `verification_report.txt` (detailed results)

---

## 📊 Output Directories

After running studies, you'll see:

```
verification_studies/
├── toy_geometry_output/
│   ├── materials.xml
│   ├── geometry.xml
│   ├── settings.xml
│   ├── tallies.xml
│   ├── statepoint.10.h5
│   └── summary.h5
│
├── single_torus_output/
│   └── [same structure]
│
├── multi_torus_output/
│   └── [same structure]
│
├── reactor_model_output/
│   └── [same structure]
│
├── sector_model_output/
│   └── [same structure]
│
└── verification_report.txt  ← Summary from run_all_studies.py
```

---

## 🎯 Quick Reference: What to Run?

| Goal | Files to Run | Time |
|------|-------------|------|
| **Quick check** | `01_toy_geometry.py` | 2 min |
| **Fusion basics** | `01`, `02`, `03` | 20 min |
| **Full verification** | `run_all_studies.py` | 60 min |
| **TBR calculation** | `03` or `04` | 10-30 min |
| **Learn efficiency** | `05` | 10 min |

---

## 📈 Suggested Learning Path

### Path 1: Linear Progression (Recommended)
```
01 → 02 → 03 → 04 → 05
```
- Best for learning
- Each builds on previous
- ~60-70 minutes total

### Path 2: Quick Verification
```
01 → 04
```
- Fastest validation
- Basic + full reactor
- ~30 minutes total

### Path 3: Focus on Breeding
```
01 → 03 → 04
```
- TBR-focused
- Skip toroidal intro
- ~40 minutes total

### Path 4: Efficiency Expert
```
01 → 04 → 05
```
- Basic + production + optimization
- Learn smart modeling
- ~40 minutes total

---

## 🆘 Help & Resources

### Getting Help

1. **Quick issues:** Check `QUICK_START.md` common issues section
2. **Detailed help:** See `README.md` troubleshooting section
3. **Study-specific:** Read docstring at top of each `.py` file
4. **Comparison:** Consult `STUDY_COMPARISON.md`

### External Resources

- **OpenMC Documentation:** https://docs.openmc.org
- **OpenMC GitHub:** https://github.com/openmc-dev/openmc
- **Nuclear Data:** https://www.nndc.bnl.gov/endf-b8.0/
- **ITER:** https://www.iter.org

---

## ✅ Verification Checklist

Use this to track your progress:

```
Installation:
[ ] OpenMC installed (version ≥ 0.13.0)
[ ] Nuclear data library configured
[ ] Python packages installed (numpy, pandas, h5py)

Studies:
[ ] Study 1: Toy Geometry (PASSED / FAILED)
[ ] Study 2: Single Torus (PASSED / FAILED)
[ ] Study 3: Multi-Layer Torus (PASSED / FAILED)
[ ] Study 4: DEMO Reactor (PASSED / FAILED)
[ ] Study 5: Sector Model (PASSED / FAILED)

Results Review:
[ ] All studies completed without errors
[ ] TBR values are reasonable (0.5-1.5)
[ ] Heating ~14 MeV per neutron
[ ] No lost particles
[ ] Output files generated

Next Steps:
[ ] Read README.md fully
[ ] Increase particle counts for production
[ ] Try parameter variations
[ ] Integrate with AONP framework
```

---

## 📝 File Sizes

| File | Lines | Size |
|------|------:|-----:|
| `README.md` | 600 | ~45 KB |
| `QUICK_START.md` | 200 | ~12 KB |
| `STUDY_COMPARISON.md` | 400 | ~25 KB |
| `INDEX.md` | 350 | ~18 KB |
| `01_toy_geometry.py` | 214 | ~7 KB |
| `02_single_torus.py` | 307 | ~11 KB |
| `03_multi_torus.py` | 424 | ~15 KB |
| `04_reactor_model.py` | 650 | ~28 KB |
| `05_sector_model.py` | 600 | ~26 KB |
| `run_all_studies.py` | 400 | ~15 KB |

**Total:** ~4,000 lines of code and documentation

---

## 🎓 Skill Level Requirements

| Study | Python | OpenMC | Fusion Physics | Neutronics |
|-------|:------:|:------:|:--------------:|:----------:|
| **01** | Basic | None | None | Basic |
| **02** | Basic | Basic | Basic | Basic |
| **03** | Basic | Basic | Intermediate | Intermediate |
| **04** | Intermediate | Intermediate | Intermediate | Intermediate |
| **05** | Intermediate | Intermediate | Basic | Intermediate |

**Legend:**
- **None:** No prior knowledge needed
- **Basic:** Understand fundamental concepts
- **Intermediate:** Can modify and adapt code

---

## 🚀 Ready to Start?

### Option 1: Fast Track (90 minutes)
```bash
cd verification_studies
python run_all_studies.py
```

### Option 2: Step-by-Step (2 hours)
```bash
# Read overview
cat README.md

# Run each study
python 01_toy_geometry.py
python 02_single_torus.py
python 03_multi_torus.py
python 04_reactor_model.py
python 05_sector_model.py
```

### Option 3: Explore First (15 minutes)
```bash
# Read quick start
cat QUICK_START.md

# Read comparison
cat STUDY_COMPARISON.md

# Then decide which studies to run
```

---

**🎉 Good luck with your verification!**

**Questions?** Consult the appropriate documentation file above.

**Issues?** Check troubleshooting sections in README.md or QUICK_START.md.

**Success?** Congratulations! Your OpenMC installation is production-ready! 🚀


# OpenMC Verification Studies - Detailed Comparison

## 📊 Study Comparison Matrix

| Feature | Study 1<br>Toy Geo | Study 2<br>Single Torus | Study 3<br>Multi Torus | Study 4<br>DEMO Reactor | Study 5<br>Sector Model |
|---------|:------------------:|:-----------------------:|:----------------------:|:----------------------:|:----------------------:|
| **Runtime** | 1-2 min | 5-10 min | 10-15 min | 15-30 min | 5-10 min |
| **Complexity** | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Particles** | 10⁵ | 10⁵ | 2×10⁵ | 10⁵ | 10⁵ |
| **Batches** | 10 | 20 | 25 | 30 | 25 |
| **Major Radius** | N/A | 4 m | 4 m | 9 m | 6 m |
| **Geometry Type** | Spherical | Toroidal | Toroidal | Toroidal | Toroidal Sector |

---

## 🎯 Capability Matrix

| Capability | Study 1 | Study 2 | Study 3 | Study 4 | Study 5 |
|------------|:-------:|:-------:|:-------:|:-------:|:-------:|
| **Basic Geometry** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Material Definitions** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Point Source** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Ring Source** | ❌ | ✅ | ✅ | ❌ | ✅ |
| **Volumetric Source** | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Toroidal Geometry** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Multi-Layer Design** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **TBR Calculation** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Neutron Multiplication** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Mesh Tallies** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Reflective Boundaries** | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Sector Optimization** | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 🔬 Physics Coverage

### Study 1: Two-Volume Toy Geometry
**Physics tested:**
- ✅ Basic neutron transport
- ✅ Material interactions (water, steel)
- ✅ Flux tallies
- ✅ Heating deposition
- ✅ Absorption reactions

**Key learning:** Verify OpenMC installation works at all

---

### Study 2: Single Layered Torus
**Physics tested:**
- ✅ Toroidal particle tracking
- ✅ Ring source geometry
- ✅ Cylindrical coordinate systems
- ✅ Steel wall interactions
- ✅ Spatial mesh tallies

**Key learning:** Can handle tokamak-like geometries

---

### Study 3: Multi-Layered Torus
**Physics tested:**
- ✅ Multi-material interfaces
- ✅ Tungsten plasma-facing material
- ✅ Lithium breeding reactions:
  - ⁶Li(n,t)α → TBR contribution
  - ⁷Li(n,n't)α → Threshold breeding
- ✅ Beryllium multiplication:
  - ⁹Be(n,2n) → Neutron doubling
- ✅ Heating distribution across layers

**Key learning:** Tritium breeding physics fundamentals

---

### Study 4: DEMO Reactor Model
**Physics tested:**
- ✅ Full-scale reactor modeling (9m major radius)
- ✅ Volumetric plasma source
- ✅ Inboard vs. outboard blanket asymmetry
- ✅ Multiple blanket enrichments
- ✅ Energy multiplication factor
- ✅ Integral parameters:
  - Total TBR
  - Component-wise heating
  - Neutron flux distributions
  - Neutron multiplication rates

**Key learning:** Production-level integral calculations

---

### Study 5: Sector Slicing Model
**Physics tested:**
- ✅ Reflective boundary conditions
- ✅ Toroidal symmetry exploitation
- ✅ Equivalent physics with reduced domain
- ✅ Computational efficiency strategies
- ✅ Result scaling (volumetric vs. intensive properties)

**Key learning:** Smart modeling for parameter studies

---

## 🏗️ Geometry Complexity

```
Study 1: Sphere-in-sphere
┌─────────────────┐
│                 │
│    ┌─────┐     │  ← Steel shell
│    │     │     │
│    │  H₂O │    │  ← Water core
│    │     │     │
│    └─────┘     │
│                 │
└─────────────────┘

Study 2: Single-layer torus
        ┌────┐
    ┌───┘    └───┐
    │   Plasma   │  ← Vacuum
    │            │
┌───┤   Steel    ├───┐  ← Steel wall
│   │            │   │
└───┐    ┌──────┘   │
    └────┘

Study 3: Multi-layer torus
        ┌────┐
    ┌───┘    └───┐
    │  Plasma    │
┌───┤ Tungsten   ├───┐  ← First wall
│   │ Li₄SiO₄+Be │   │  ← Breeding blanket
│   │   Steel    │   │  ← Vacuum vessel
└───┐            ┌───┘
    └────────────┘

Study 4: DEMO reactor (2× larger)
        ┌────────┐
    ┌───┘        └───┐
    │    Plasma      │
┌───┤  First Wall    ├───┐
│   │  Blanket (IB)  │   │  ← Inboard: lower enrichment
│   │  Blanket (OB)  │   │  ← Outboard: higher enrichment
│   │     Vessel     │   │
└───┐                ┌───┘
    └────────────────┘

Study 5: Sector model (20° wedge)
       ┌────┐
   ┌───┘    └───┐
   │  Plasma    │
   │ Blanket    │
   └────────────┘
      ↑      ↑
   Reflective boundaries
   (Only model 1/18 of full torus!)
```

---

## 📈 Scaling Analysis

### Particle Count Scaling
| Study | Current | Quick Mode | Production | High-Fidelity |
|-------|:-------:|:----------:|:----------:|:-------------:|
| **1** | 10⁵ × 10 | 10⁴ × 5 | 10⁶ × 20 | 10⁷ × 50 |
| **2** | 10⁵ × 20 | 10⁴ × 10 | 10⁶ × 30 | 10⁷ × 100 |
| **3** | 2×10⁵ × 25 | 5×10⁴ × 10 | 10⁶ × 50 | 10⁷ × 100 |
| **4** | 10⁵ × 30 | 5×10⁴ × 15 | 10⁶ × 50 | 10⁷ × 100 |
| **5** | 10⁵ × 25 | 10⁴ × 10 | 10⁶ × 40 | 10⁷ × 80 |

### Expected Runtime Scaling (single core)
| Mode | Total Time | Study 1 | Study 2 | Study 3 | Study 4 | Study 5 |
|------|:----------:|:-------:|:-------:|:-------:|:-------:|:-------:|
| **Quick** | 10-15 min | 30 sec | 2 min | 3 min | 5 min | 2 min |
| **Current** | 40-70 min | 2 min | 8 min | 12 min | 25 min | 8 min |
| **Production** | 5-8 hours | 20 min | 1 hr | 2 hr | 4 hr | 1 hr |
| **High-Fidelity** | 50-80 hours | 3 hr | 10 hr | 20 hr | 40 hr | 10 hr |

---

## 🎓 Learning Progression

### Level 1: Basic Transport (Study 1)
**Concepts:**
- Neutron transport equation
- Cross sections
- Flux definitions
- Energy deposition

**Prerequisites:** None

---

### Level 2: Fusion Geometry (Study 2)
**Concepts:**
- Toroidal coordinates
- Ring sources
- Mesh tallies
- Cylindrical meshes

**Prerequisites:** Study 1

---

### Level 3: Breeding Physics (Study 3)
**Concepts:**
- Tritium breeding ratio (TBR)
- Li-6 and Li-7 reactions
- Neutron multiplication
- Material optimization

**Prerequisites:** Studies 1-2

---

### Level 4: Reactor Design (Study 4)
**Concepts:**
- Integral parameters
- Inboard/outboard asymmetry
- Blanket segmentation
- Energy balance
- Reactor self-sufficiency (TBR > 1)

**Prerequisites:** Studies 1-3

---

### Level 5: Optimization (Study 5)
**Concepts:**
- Computational efficiency
- Symmetry exploitation
- Reflective boundaries
- Result scaling
- Parameter studies

**Prerequisites:** Studies 1-4

---

## 🔍 Tally Comparison

| Tally Type | Study 1 | Study 2 | Study 3 | Study 4 | Study 5 |
|------------|:-------:|:-------:|:-------:|:-------:|:-------:|
| **Cell Flux** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Cell Heating** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Absorption** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Mesh Flux** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Mesh Heating** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **(n,Xt) - TBR** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **(n,2n)** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Energy Filters** | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 💾 Output File Sizes (Approximate)

| Study | XML Files | statepoint.h5 | Total |
|-------|:---------:|:-------------:|:-----:|
| **1** | 10 KB | 500 KB | ~500 KB |
| **2** | 15 KB | 5 MB | ~5 MB |
| **3** | 20 KB | 10 MB | ~10 MB |
| **4** | 25 KB | 15 MB | ~15 MB |
| **5** | 20 KB | 8 MB | ~8 MB |

**Note:** Mesh tallies significantly increase statepoint size. High-fidelity runs can produce 100+ MB files.

---

## 🧮 Expected Physical Results

### Study 1: Toy Geometry
- Flux in water > Flux in steel (neutrons slow down)
- Heating mostly in water (hydrogen scattering)
- Absorption mostly in steel

### Study 2: Single Torus
- Symmetric flux distribution (no breeding materials)
- Heating concentrated near source ring
- Steel activation patterns

### Study 3: Multi-Layer Torus
- **TBR: 0.6 - 0.9** (below self-sustaining without optimization)
- Heating: First wall > Blanket > Vessel
- Be multiplies neutrons by ~1.1-1.2×

### Study 4: DEMO Reactor
- **TBR: 1.0 - 1.3** (self-sustaining with dual blankets)
- Outboard TBR > Inboard TBR (more space)
- Total heating ≈ 14 MeV per fusion neutron
- Energy multiplication: ~1.15-1.20

### Study 5: Sector Model
- **Identical TBR to full geometry**
- Heating scales by (360° / sector angle)
- 18-36× faster runtime
- Same statistical precision

---

## 🎯 Which Study Should I Run?

### Quick Installation Check (< 5 minutes)
→ **Study 1 only**

### Verify Fusion Capabilities (< 30 minutes)
→ **Studies 1, 2, 3**

### Full Verification (1-2 hours)
→ **All studies (1-5)**

### Test Specific Feature
| Feature | Study |
|---------|-------|
| Basic transport | 1 |
| Toroidal geometry | 2 |
| TBR calculation | 3 or 4 |
| Full reactor | 4 |
| Efficiency tricks | 5 |

---

## 🚀 Optimization Tips by Study

### Study 1
- Increase batches for better statistics
- Add energy bins to flux tally

### Study 2
- Refine mesh resolution for plots
- Add angular flux tallies

### Study 3
- Vary Li-6 enrichment (10% - 90%)
- Test blanket thickness
- Try different multipliers (Pb vs Be)

### Study 4
- Optimize inboard/outboard enrichment ratio
- Test different blanket materials
- Add shield region

### Study 5
- Try different sector angles (10°, 20°, 36°)
- Compare results with full geometry
- Measure actual speedup on your system

---

## 📚 Further Reading

- **OpenMC Docs:** https://docs.openmc.org
- **Fusion Breeding:** ITER Physics Basis, Chapter 4
- **TBR Requirements:** Fusion Engineering Design, M. Abdou
- **Neutron Multipliers:** "Neutron Multiplication in Beryllium"
- **Computational Efficiency:** "Variance Reduction in Monte Carlo"

---

**💡 Pro Tip:** Run Study 5 (sector model) after Study 4 to see how you can get similar results 18× faster for parameter studies!


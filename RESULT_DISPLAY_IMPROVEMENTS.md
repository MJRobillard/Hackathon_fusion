# Result Display Improvements

## Overview
Enhanced the visual presentation of simulation results in the AONP agent tools to provide clearer, more informative output.

## Changes Made

### 1. Enhanced Single Run Results (`submit_study`)

**Before:**
```
  [OK] keff = 1.41812 +/- 0.001579
  [OK] Generated 1 runs
```

**After:**
```
  ======================================================================
  ✅ SIMULATION COMPLETE
  ======================================================================
  Run ID:         run_abc12345
  Status:         completed
  Runtime:        7.46 seconds

  RESULTS:
  ┌─────────────────────────────────────────────────────────────┐
  │  k-effective = 1.41812 ± 0.001579                           │
  │  Uncertainty = 158 pcm (0.111%)                             │
  └─────────────────────────────────────────────────────────────┘

  PHYSICS INTERPRETATION:
  🔥 System is SUPERCRITICAL (k > 1)
     Excess reactivity: 4181 pcm
     → Neutron population is increasing

  CONFIGURATION:
  • Geometry:     PWR pin cell
  • Materials:    UO2, Zircaloy, Water
  • Enrichment:   4.5%
  • Temperature:  900 K
  • Particles:    10,000
  • Batches:      50
  ======================================================================
```

### 2. Enhanced Run Comparison (`compare_runs`)

**Before:**
```
[TOOL: compare_runs]
  Comparing 1 runs
  keff range: [1.41812, 1.41812]
```

**After:**
```
[TOOL: compare_runs]
  ======================================================================
  📊 COMPARING 5 SIMULATION RUNS
  ======================================================================

  SUMMARY STATISTICS:
  ┌─────────────────────────────────────────────────────────────┐
  │  Number of runs:      5                                     │
  │  k-eff mean:        1.32456                                 │
  │  k-eff range:       [1.28934, 1.36789]                      │
  │  k-eff spread:      0.07855 (7855 pcm)                      │
  └─────────────────────────────────────────────────────────────┘

  INDIVIDUAL RESULTS:
   1. ❄️  SUB       k=1.28934 ± 0.001234  enrichment=3.0%
   2. ⚖️  CRITICAL  k=1.30123 ± 0.001156  enrichment=3.5%
   3. ⚖️  CRITICAL  k=1.32456 ± 0.001089  enrichment=4.0%
   4. 🔥 SUPER      k=1.34789 ± 0.001234  enrichment=4.5%
   5. 🔥 SUPER      k=1.36789 ± 0.001345  enrichment=5.0%

  TREND ANALYSIS:
  📈 Monotonically INCREASING trend
  📊 Reactivity coefficient: 0.0393 Δk/Δenrichment
  ======================================================================
```

### 3. Enhanced Parameter Sweep (`generate_sweep`)

**Before:**
```
[TOOL: generate_sweep]
  Sweeping enrichment_pct over 5 values
  [OK] Generated 5 runs
```

**After:**
```
[TOOL: generate_sweep]
  ======================================================================
  🔄 PARAMETER SWEEP: enrichment_pct
  ======================================================================
  Sweep values: [3.0, 3.5, 4.0, 4.5, 5.0]
  Number of runs: 5
  ──────────────────────────────────────────────────────────────────────

  [1/5] Running with enrichment_pct = 3.0...
  [Individual run output...]

  [2/5] Running with enrichment_pct = 3.5...
  [Individual run output...]

  ... (continues for each value) ...

  ======================================================================
  ✅ SWEEP COMPLETE
  ======================================================================
  Generated 5 runs
  Run IDs: ['run_abc123', 'run_def456', ...]
  ======================================================================
```

## Key Improvements

### 1. **Visual Hierarchy**
- Clear section headers with decorative borders
- Box drawings for key results
- Consistent spacing and alignment

### 2. **Physical Interpretation**
- Automatic criticality assessment (supercritical/critical/subcritical)
- Reactivity values in pcm (percent mille)
- Visual indicators: 🔥 (super), ⚖️ (critical), ❄️ (sub)

### 3. **Statistical Context**
- Uncertainty displayed in both absolute and percentage terms
- Mean, range, and spread for multi-run comparisons
- Trend analysis for parameter sweeps

### 4. **Configuration Summary**
- Full specification details shown with results
- Formatted numbers (thousands separator)
- Clear parameter labeling

### 5. **Trend Analysis** (for sweeps)
- Monotonicity detection
- Reactivity coefficient calculation
- Visual trend indicators (📈📉〰️)

## Usage

The improvements are automatically applied when using the agent tools:

```python
from Playground.backend.agent_tools import submit_study, generate_sweep, compare_runs

# Single run - now shows enhanced output
result = submit_study({
    "geometry": "PWR pin cell",
    "materials": ["UO2", "Water"],
    "enrichment_pct": 4.5,
    "temperature_K": 900.0,
    "particles": 10000,
    "batches": 50
})

# Parameter sweep - now shows progress and summary
run_ids = generate_sweep(
    base_spec={"geometry": "PWR pin", "materials": ["UO2", "Water"]},
    param_name="enrichment_pct",
    param_values=[3.0, 3.5, 4.0, 4.5, 5.0]
)

# Comparison - now shows detailed statistics
comparison = compare_runs(run_ids)
```

## Benefits

1. **Better User Experience**: Results are easier to read and understand
2. **More Context**: Physical interpretation helps users understand what the numbers mean
3. **Professional Appearance**: Clean formatting suitable for presentations or reports
4. **Actionable Insights**: Trend analysis helps identify patterns in parameter sweeps
5. **Reduced Cognitive Load**: Visual indicators (emojis, symbols) provide quick status assessment

## Technical Details

- **File Modified**: `Playground/backend/agent_tools.py`
- **Functions Enhanced**: 
  - `submit_study()` - lines 320-360
  - `compare_runs()` - lines 393-480
  - `generate_sweep()` - lines 360-415
- **Dependencies**: No new dependencies required
- **Backward Compatibility**: Return values unchanged, only console output improved


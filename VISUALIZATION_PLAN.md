# Data Visualization Plan for MongoDB & Experiment Data

## Overview
Plan for visualizing MongoDB simulation data and real-time experiment results in the AI OpenMC interface.

---

## Available Data Sources

### MongoDB Collections
1. **`summaries`** - Completed simulation results
   - `run_id`, `spec_hash`, `keff`, `keff_std`
   - `runtime_seconds`, `status`, `created_at`
   - `spec`: Full study spec (geometry, materials, enrichment_pct, temperature_K, particles, batches)

2. **`openmc_runs`** - Detailed run records
   - Similar to summaries + execution metadata

3. **Batch-level data** (from extractor)
   - `batch_keff`: Per-batch k-effective values
   - `entropy`: Convergence diagnostic per batch
   - `n_batches`, `n_inactive`, `n_particles`

### Real-time Experiment Data
- Current run: `keff`, `keff_std`, convergence progress
- Parameter sweeps: Multiple runs with varying parameters

---

## Key Questions Users Will Ask

### 1. **Single Run Analysis**
- "How did k-effective converge over batches?"
- "Is the simulation converged?"
- "What's the uncertainty in my result?"
- "How long did this simulation take?"

### 2. **Parameter Sweep Analysis**
- "How does enrichment affect criticality?"
- "What's the optimal enrichment for criticality?"
- "What's the reactivity coefficient (dk/dp)?"
- "Are there any anomalies in the sweep?"

### 3. **Historical Comparison**
- "How does this run compare to previous runs?"
- "What runs have similar configurations?"
- "Has this configuration been run before?"
- "What's the spread of results for similar specs?"

### 4. **Trend Analysis**
- "What are recent simulation results?"
- "Is there a pattern in my results over time?"
- "What configurations give the best/worst results?"

### 5. **Database Exploration**
- "How many simulations have been run?"
- "What's the distribution of k-effective values?"
- "What enrichment ranges have been explored?"

---

## Visualization Types & What They Tell Users

### 1. **Batch Convergence Plot** (Single Run)
**Chart Type**: Line chart with shaded uncertainty bands
**Data**: `batch_keff` array, `entropy` array
**X-axis**: Batch number (1 to n_batches)
**Y-axis**: k-effective (left), Entropy (right, secondary axis)
**Features**:
- Show inactive vs active batches (different color/shading)
- Mark convergence point (when k-effective stabilizes)
- Shade uncertainty region (±keff_std around mean)
- Show final k-effective as horizontal line
**Answers**: 
- "Is this converged?" (flat line after inactive batches)
- "How many batches until convergence?" (inflection point)
- "What's the statistical quality?" (tightness of uncertainty)

### 2. **Parameter Sweep Plot** (Multi-run)
**Chart Type**: Scatter plot with error bars + trend line
**Data**: Multiple runs with varying parameter (e.g., enrichment)
**X-axis**: Parameter value (enrichment %, temperature K, etc.)
**Y-axis**: k-effective
**Features**:
- Error bars showing keff_std
- Linear/non-linear trend line
- Color by criticality (super/sub/critical)
- Interactive hover: show run_id, full spec
**Answers**:
- "How does parameter X affect criticality?" (slope)
- "What's the reactivity coefficient?" (gradient)
- "Where is criticality?" (where k=1.0 crosses)

### 3. **Comparison Chart** (Multi-run)
**Chart Type**: Grouped bar chart or violin plot
**Data**: Selected runs to compare
**X-axis**: Run ID or parameter value
**Y-axis**: k-effective with error bars
**Features**:
- Side-by-side comparison
- Highlight min/max/mean
- Show statistical spread
**Answers**:
- "How do these runs compare?" (visual ranking)
- "What's the spread?" (range visualization)
- "Which run is most/least critical?"

### 4. **Historical Timeline** (All Runs)
**Chart Type**: Scatter plot over time
**Data**: All summaries, sorted by `created_at`
**X-axis**: Time (created_at)
**Y-axis**: k-effective
**Features**:
- Color by geometry or material
- Size by uncertainty (large = uncertain)
- Filter by parameter ranges
**Answers**:
- "What's the trend over time?" (learning curve)
- "When did I explore different configurations?" (clusters)
- "What's the distribution of results?" (vertical spread)

### 5. **k-effective Distribution** (Statistical)
**Chart Type**: Histogram + box plot
**Data**: All completed runs
**Features**:
- Bin k-effective values
- Show mean, median, quartiles
- Overlay target (k=1.0) line
- Filter by parameter ranges
**Answers**:
- "What's the typical k-effective?" (central tendency)
- "How spread out are my results?" (variance)
- "How many super/sub/critical runs?" (counts by range)

### 6. **Uncertainty vs Runtime** (Performance)
**Chart Type**: Scatter plot
**Data**: All runs
**X-axis**: Runtime (seconds)
**Y-axis**: Uncertainty (keff_std)
**Features**:
- Color by particles/batches (simulation quality)
- Trend line (more time = better statistics?)
**Answers**:
- "Is longer runtime worth it?" (uncertainty reduction)
- "What's the efficiency tradeoff?" (time vs quality)

### 7. **Parameter Space Heatmap** (2D Sweep)
**Chart Type**: Heatmap / contour plot
**Data**: Runs with 2 varying parameters (future)
**X-axis**: Parameter 1 (e.g., enrichment)
**Y-axis**: Parameter 2 (e.g., temperature)
**Color**: k-effective value
**Answers**:
- "What's the optimal 2D parameter space?" (color gradients)
- "Where are criticality boundaries?" (contour lines at k=1.0)

### 8. **Database Statistics Dashboard**
**Chart Type**: Summary cards + mini charts
**Metrics**:
- Total runs, completed, failed
- Average runtime
- k-effective statistics (mean, std, range)
- Most common geometries/materials
- Recent runs list
**Answers**:
- "How much data do I have?" (volume metrics)
- "What's the overall picture?" (aggregates)

---

## Where Visualizations Should Go

### Primary Locations

#### 1. **Right Sidebar (Telemetry Panel) - Current Run Focus**
**Current State**: Shows live metrics (keff, convergence, interlocks)
**Add**:
- **Batch Convergence Plot** (below current metrics)
  - Collapsible section "Batch History"
  - Updates in real-time as simulation progresses
  - Shows only for active runs
  - Auto-scales to show convergence

#### 2. **New Panel: "Analytics" Tab in Right Sidebar**
**Location**: Add tab next to "Telemetry" and "RAG Copilot" tabs
**Content**:
- **Dashboard View** (default)
  - Database statistics cards
  - Recent runs list (clickable to drill down)
  - Quick filters (geometry, enrichment range)
  
- **Single Run View** (when run selected)
  - Full batch convergence plot
  - Run details sidebar
  - Comparison to similar runs
  
- **Sweep View** (when sweep detected)
  - Parameter sweep plot
  - Trend analysis
  - Reactivity coefficient calculation

- **Comparison View** (when multiple runs selected)
  - Comparison chart
  - Statistical summary

#### 3. **Database Panel Enhancement**
**Current State**: Shows raw JSON documents
**Add**:
- **Visualization Mode** toggle (JSON view vs Chart view)
- When viewing `summaries` collection:
  - Auto-generate appropriate chart based on selection
  - Parameter sweep detection (runs with same spec except one parameter)
  - Quick comparison button for selected runs

#### 4. **After Run Completion - Auto-Popup**
**Location**: Modal or expandable panel in center area
**Trigger**: Simulation completes
**Content**:
- Batch convergence plot (final view)
- Comparison to recent similar runs (if any)
- Quick stats: runtime, uncertainty, criticality status
- "View Full Analysis" button → Opens Analytics tab

---

## Implementation Approach

### Phase 1: Tool Integration (Backend)
1. **Visualization Tool Call** (`visualize_run`, `visualize_sweep`)
   - Agent can call these tools after run completion
   - Returns chart data (JSON) ready for frontend rendering
   - Handles MongoDB queries for historical context

2. **Passive Visualization Hook**
   - After every run completion, automatically:
     - Generate batch convergence data
     - Find similar runs for comparison
     - Store visualization-ready data in MongoDB or return to frontend

### Phase 2: Frontend Components
1. **Chart Library**: Use Recharts or Chart.js (React-friendly)
2. **Components**:
   - `BatchConvergenceChart`
   - `ParameterSweepChart`
   - `ComparisonChart`
   - `TimelineChart`
   - `DistributionChart`
   - `AnalyticsDashboard`

### Phase 3: Integration Points
1. **Real-time Updates**: SSE stream includes chart data
2. **API Endpoints**: 
   - `/api/v1/visualizations/run/{run_id}` - Get visualization data for run
   - `/api/v1/visualizations/sweep/{sweep_id}` - Get sweep visualization
   - `/api/v1/visualizations/comparison` - Compare multiple runs

---

## Recommended Priority

### High Priority (Immediate Value)
1. **Batch Convergence Plot** - Essential for understanding single runs
2. **Parameter Sweep Plot** - Most common multi-run analysis
3. **Database Statistics Dashboard** - Quick overview

### Medium Priority (Enhanced Analysis)
4. **Comparison Chart** - Useful for comparing selected runs
5. **Historical Timeline** - Understanding trends
6. **Auto-popup after completion** - Better UX

### Low Priority (Nice to Have)
7. **Distribution charts** - Statistical deep-dive
8. **Uncertainty vs Runtime** - Performance analysis
9. **2D Parameter space** - Advanced analysis

---

## Technical Considerations

### Data Aggregation
- MongoDB aggregation pipelines for efficient queries
- Cache frequently accessed visualizations
- Pagination for large datasets

### Performance
- Lazy load charts (only render when visible)
- Virtual scrolling for large run lists
- Debounce real-time updates (don't re-render every batch)

### Responsive Design
- Charts adapt to sidebar width
- Mobile-friendly (if needed)
- Export as PNG/SVG for reports

### Accessibility
- Colorblind-friendly palettes
- Alt text for charts
- Keyboard navigation

---

## Example User Flows

### Flow 1: Single Run Analysis
1. User submits simulation
2. During run: Real-time batch convergence plot in Telemetry panel
3. After completion: Auto-popup with final convergence plot + quick stats
4. Click "View Full Analysis" → Opens Analytics tab with:
   - Full convergence history
   - Similar runs comparison
   - Run details

### Flow 2: Parameter Sweep Analysis
1. User submits sweep (e.g., enrichment 3.0-5.0%)
2. Agent executes multiple runs
3. After completion: Analytics tab auto-switches to "Sweep View"
4. Shows parameter sweep plot with trend line
5. Displays reactivity coefficient: "dk/d(enrichment) = X pcm/%"

### Flow 3: Historical Exploration
1. User clicks "Analytics" tab
2. Sees dashboard with recent runs
3. Clicks on a run → Drill down to single run view
4. Selects multiple runs → Switches to comparison view
5. Can filter by parameter ranges to explore patterns

---

## Next Steps

1. **Confirm priorities** with user
2. **Choose chart library** (Recharts recommended for React)
3. **Design API endpoints** for visualization data
4. **Implement backend visualization tools** (MongoDB queries + data formatting)
5. **Build frontend components** incrementally
6. **Integrate with existing UI** (Telemetry panel, Database panel)
7. **Add real-time updates** via SSE streams
8. **Test with real data** from MongoDB


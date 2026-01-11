# Frontend Redesign Plan: OpenMC Mission Control

## Overview
Redesign the current frontend to match the "Mission Control" aesthetic - a dark, sophisticated, data-dense dashboard interface inspired by control room and aerospace mission control systems.

## Design Philosophy
- **Dark Theme**: Deep blacks (#0A0B0D, #0F1115, #050607) with subtle borders
- **Information Density**: Maximum useful data visible without overwhelming
- **Status Awareness**: Clear visual indicators for system states (running, success, warning, failed)
- **Professional Aesthetic**: Monospace fonts, uppercase labels, technical terminology
- **Real-time Focus**: Emphasis on live telemetry and streaming logs

---

## Layout Structure

### 1. **Top Header** (h-14)
**Current:** `TopBar.tsx`
**Target Design:**
- Left section:
  - Logo (MC in blue box) + "OPENMC MISSION CONTROL" title
  - Project badge: `fusion-core-alpha-09` in monospace
- Right section:
  - Control buttons (Play, Stop, Reset) in button group
  - Command Palette button (blue primary CTA)

**Changes Needed:**
- Redesign header to be more compact (56px height)
- Add control button group with icons
- Style project name as a pill/badge
- Update color scheme to darker backgrounds

---

### 2. **Left Sidebar: Simulation Runs** (w-80)
**Current:** Split across `RequestHistory.tsx`
**Target Design:**
- Header: "SIMULATION RUNS" with filter icon
- Scrollable list of runs showing:
  - Run ID (monospace, e.g., "OM-945")
  - Status pill (colored badge with dot indicator)
  - Type and timestamp
  - Active run highlighted with blue accent
- Color-coded status:
  - Running: Blue
  - Success: Emerald/Green
  - Warning: Amber
  - Failed: Red

**Changes Needed:**
- Convert RequestHistory to sidebar format
- Add status pill component with proper colors
- Implement active run selection state
- Add collapsible functionality
- Style with darker backgrounds and border-left accent for active items

---

### 3. **Main Workspace**

#### 3a. **Top Panel: Agent Orchestration** (flex-1)
**Current:** `AgentWorkflow.tsx`, `AgentFlowDiagram.tsx`
**Target Design:**
- Header bar: "Agent Orchestration" + current task description
- 3-column card layout showing agent states:
  - **Parser Agent**: File validation status
  - **Simulation Core**: Active execution (pulsing indicator)
  - **Validation Gate**: Waiting/pending state
- Flow visualization canvas below (schematic workflow graph)

**Changes Needed:**
- Redesign agent cards as compact status boxes
- Add state indicators (colored dots: green=complete, blue=active, gray=pending)
- Create flow diagram showing: Geometry → Monte Carlo → Tallies
- Add pulsing animation for active states
- Implement opacity for inactive/pending agents

#### 3b. **Bottom Panel: Execution Logs** (h-64)
**Current:** `ExecutionLogs.tsx`
**Target Design:**
- Header: "EXECUTION LOGS" with error/warning counts
- Terminal-style log output:
  - Timestamp column (gray)
  - Log message (color-coded by type)
  - Blinking cursor for active state
- Log types:
  - INFO: Default gray
  - WARNING: Amber
  - PROCESS: Blue
  - ERROR: Red

**Changes Needed:**
- Redesign as terminal/console output
- Add timestamp formatting
- Implement color coding by log type
- Add animated cursor
- Update header with error/warning counters
- Use monospace font throughout

---

### 4. **Right Sidebar: Live Telemetry** (w-72)
**Current:** `ResultsPanel.tsx`
**Target Design:**

#### Section 1: Live Telemetry
- **k-eff Value Card**:
  - Large number display (1.00245)
  - Uncertainty range (± 0.00012)
  - Status badge [NOMINAL]
- **Convergence Rate Card**:
  - Progress bar (visual)
  - Iteration count
  - Percentage complete

#### Section 2: Interlocks
- List of validation checks:
  - Geometry Check (passed)
  - Cross Section (passed)
  - Convergence Variance (alert)
- Status indicators (colored dots)

#### Section 3: Resource Allocation
- CPU utilization (128 cores, 82%)
- Agent cost tracking ($4.22)
- Export artifacts button

**Changes Needed:**
- Split ResultsPanel into three distinct sections
- Create telemetry card components with large number displays
- Add progress bar component
- Create interlock checklist component
- Add resource allocation metrics
- Style all with dark cards and borders

---

### 5. **Footer: Status Bar** (h-8)
**Target Design:**
- Left: System status (green dot + "SYSTEM READY") + OpenMC version
- Right: Latency, token consumption, estimated completion time
- Monospace font for all metrics

**Changes Needed:**
- Create new footer component
- Add pulsing green status indicator
- Display technical metrics in monospace
- Use very small text (10px)

---

## Component Architecture

### New/Modified Components

1. **`layouts/MissionControlLayout.tsx`**
   - Main layout wrapper with 4-zone grid
   - Manages sidebar collapse states

2. **`components/TopBar.tsx`** (redesign)
   - Logo and title
   - Project badge
   - Control buttons
   - Command palette

3. **`components/SimulationRunsSidebar.tsx`** (new)
   - Run list with filtering
   - Status pills
   - Active selection state

4. **`components/AgentOrchestrationPanel.tsx`** (replaces AgentWorkflow)
   - Agent status cards
   - Flow diagram
   - Current task display

5. **`components/ExecutionLogs.tsx`** (redesign)
   - Terminal-style output
   - Color-coded messages
   - Error/warning counters

6. **`components/TelemetrySidebar.tsx`** (new)
   - Live metrics cards
   - Interlocks checklist
   - Resource allocation
   - Export button

7. **`components/StatusFooter.tsx`** (new)
   - System status
   - Performance metrics

8. **`components/ui/StatusPill.tsx`** (new)
   - Reusable status badge component

9. **`components/ui/MetricCard.tsx`** (new)
   - Telemetry display card

10. **`components/ui/ProgressBar.tsx`** (new)
    - Convergence progress indicator

---

## Color Palette

### Backgrounds
- `bg-primary`: #0A0B0D (main background)
- `bg-secondary`: #0F1115 (panels, header)
- `bg-tertiary`: #050607 (main workspace)
- `bg-card`: #14161B (cards, elevated elements)

### Borders
- `border-default`: #1F2937 (gray-800)
- `border-subtle`: #111827 (gray-900)

### Status Colors
- **Running/Active**: Blue (#3B82F6, #1E3A8A)
- **Success**: Emerald (#10B981, #064E3B)
- **Warning**: Amber (#F59E0B, #78350F)
- **Failed**: Red (#EF4444, #7F1D1D)
- **Info**: Gray (#9CA3AF)

### Text
- `text-primary`: #D1D5DB (gray-300)
- `text-secondary`: #9CA3AF (gray-400)
- `text-tertiary`: #6B7280 (gray-500)
- `text-emphasis`: #FFFFFF (white)

---

## Typography

### Font Families
- **Headings/Labels**: `font-sans` (system font, bold)
- **Data/Code**: `font-mono` (monospace)

### Font Sizes
- `text-[10px]`: Labels, footer, badges (tracking-widest, uppercase)
- `text-[11px]`: Logs, small data
- `text-xs`: Standard text
- `text-sm`: Larger labels
- `text-2xl`: Large metric values

---

## Animations & Interactions

1. **Pulsing Indicators**
   - Active status dots: `animate-pulse`
   - System ready indicator: `animate-pulse`

2. **Hover States**
   - Sidebar items: `hover:bg-gray-900`
   - Buttons: `hover:bg-gray-700`

3. **Active States**
   - Selected run: Blue left border + background tint
   - Active agent: Blue outline

4. **Transitions**
   - Sidebar collapse: `transition-all`
   - Hover states: `transition-colors`

---

## Data Flow & State Management

### State to Track
1. **Active Run ID**: Currently selected simulation
2. **Runs List**: All simulations with status
3. **Current Task**: Active agent task description
4. **Agent States**: Parser, Core, Validation statuses
5. **Logs Stream**: Real-time log messages
6. **Telemetry**: k-eff, convergence, iterations
7. **Interlocks**: Validation check statuses
8. **Resources**: CPU %, agent cost

### API Integration Points
- Keep existing hooks: `useEventStream`, `useQueryHistory`
- Adapt data to new component structure
- Map backend status to UI status colors
- Format telemetry data for display

---

## Implementation Phases

### Phase 1: Core Layout (2-3 hours)
- [ ] Create new color scheme in Tailwind config
- [ ] Build MissionControlLayout with 4-zone structure
- [ ] Implement StatusFooter
- [ ] Update globals.css with new theme

### Phase 2: Left Sidebar (2 hours)
- [ ] Build SimulationRunsSidebar component
- [ ] Create StatusPill component
- [ ] Implement run selection logic
- [ ] Add collapse functionality

### Phase 3: Top Bar (1 hour)
- [ ] Redesign TopBar with new layout
- [ ] Add control buttons
- [ ] Style project badge

### Phase 4: Main Workspace - Top (3 hours)
- [ ] Build AgentOrchestrationPanel
- [ ] Create agent status cards
- [ ] Implement flow diagram
- [ ] Add state indicators and animations

### Phase 5: Main Workspace - Bottom (2 hours)
- [ ] Redesign ExecutionLogs as terminal
- [ ] Add color coding logic
- [ ] Implement error/warning counters
- [ ] Add animated cursor

### Phase 6: Right Sidebar (3 hours)
- [ ] Build TelemetrySidebar structure
- [ ] Create MetricCard for k-eff display
- [ ] Add ProgressBar for convergence
- [ ] Implement interlocks checklist
- [ ] Add resource allocation section

### Phase 7: Polish & Integration (2 hours)
- [ ] Connect to existing API hooks
- [ ] Test data flow
- [ ] Add responsive breakpoints
- [ ] Fine-tune spacing and typography
- [ ] Add loading states

---

## Technical Considerations

### Tailwind Configuration
Add custom colors to `tailwind.config.js`:
```js
colors: {
  background: {
    primary: '#0A0B0D',
    secondary: '#0F1115',
    tertiary: '#050607',
    card: '#14161B',
  },
  border: {
    default: '#1F2937',
    subtle: '#111827',
  }
}
```

### Font Setup
Ensure monospace font is properly loaded in `layout.tsx`

### Icon Library
Using `lucide-react` (already in reference design):
- Play, Square, RotateCcw (controls)
- Terminal, Activity, FileCode, ShieldCheck (agents)
- Cpu, Filter, Download, AlertTriangle (status)

### Performance
- Virtualize logs if list grows large
- Debounce log updates
- Memoize expensive calculations
- Use React.memo for static components

---

## Testing Checklist

- [ ] All status colors render correctly
- [ ] Active run selection works
- [ ] Logs stream in real-time
- [ ] Telemetry updates properly
- [ ] Interlock states reflect backend
- [ ] Sidebar collapse/expand smooth
- [ ] Responsive on different screen sizes
- [ ] Dark theme consistent across all components
- [ ] Monospace fonts applied to technical data
- [ ] Animations perform smoothly

---

## Files to Modify

### Update Existing
- `frontend/app/page.tsx` - Use new layout
- `frontend/app/globals.css` - Add new theme variables
- `frontend/components/TopBar.tsx` - Redesign
- `frontend/components/ExecutionLogs.tsx` - Redesign
- `frontend/lib/types.ts` - Add status type definitions

### Create New
- `frontend/layouts/MissionControlLayout.tsx`
- `frontend/components/SimulationRunsSidebar.tsx`
- `frontend/components/AgentOrchestrationPanel.tsx`
- `frontend/components/TelemetrySidebar.tsx`
- `frontend/components/StatusFooter.tsx`
- `frontend/components/ui/StatusPill.tsx`
- `frontend/components/ui/MetricCard.tsx`
- `frontend/components/ui/ProgressBar.tsx`

### Possibly Remove/Archive
- `frontend/components/AgentWorkflow.tsx` (replace)
- `frontend/components/ResultsPanel.tsx` (replace)
- `frontend/components/RequestHistory.tsx` (replace)

---

## Success Criteria

✅ Design matches reference aesthetic (dark, technical, mission control vibe)
✅ All data from current implementation still displays
✅ Real-time updates work smoothly
✅ Interface feels responsive and professional
✅ Status indicators are clear and intuitive
✅ Information density improved without cluttering
✅ Color coding enhances readability
✅ Monospace fonts used appropriately for technical data

---

## Notes & Considerations

- **Preserve functionality**: Don't break existing API integrations
- **Mobile**: Consider if mobile view is needed (seems desktop-focused)
- **Accessibility**: Ensure color contrast meets WCAG standards
- **Loading states**: Add skeleton loaders for data fetching
- **Error handling**: Design error states for each panel
- **Empty states**: What shows when no runs exist?

---

## Estimated Total Time: 15-18 hours

This is a complete visual overhaul while maintaining backend compatibility.


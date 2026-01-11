# Mission Control MVP - Frontend Redesign & Agent Loop

## Overview
Build a dark, mission-control-style dashboard that displays live agent orchestration and enables autonomous agent experimentation loops.

---

## Core Design Principles
- **Dark theme** with high contrast (#0A0B0D backgrounds, bright status colors)
- **Standard patterns** - use Next.js conventions, no custom frameworks
- **Real-time updates** via Server-Sent Events
- **Agent-first** - UI reflects agent state and decision-making
- **Autonomous loops** - agents suggest and queue new experiments automatically

---

## Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│ Top Bar (h-14)                                               │
│ [OPENMC MISSION CONTROL] | fusion-core | [▶ ⏹ ⟲] [Command]  │
├─────────────┬───────────────────────────────┬────────────────┤
│             │                               │                │
│  RUNS       │   AGENT ORCHESTRATION         │  TELEMETRY     │
│  (w-80)     │   (flex-1)                    │  (w-72)        │
│             │                               │                │
│  • OM-945   │   ┌───────────────────────┐   │  k-eff         │
│    Running  │   │ Intent Classifier     │   │  1.00245       │
│  • OM-944   │   │ Study Planner    [●]  │   │  ± 0.00012     │
│    Complete │   │ Executor              │   │                │
│             │   └───────────────────────┘   │  Convergence   │
│             │                               │  █████░ 82%    │
│             ├───────────────────────────────┤                │
│             │   EXECUTION LOGS (h-64)       │  Interlocks    │
│             │   > Starting simulation...    │  ✓ Geometry    │
│             │   > Batch 45/100 complete     │  ✓ Cross Sec   │
│             │   ▊                           │  ⚠ Variance    │
└─────────────┴───────────────────────────────┴────────────────┘
│ Footer: ● SYSTEM READY | OpenMC 0.14.0 | 128 cores @ 82%   │
└──────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Top Bar (`components/TopBar.tsx`)
- Logo + "OPENMC MISSION CONTROL"
- Project badge (monospace): `fusion-core-alpha-09`
- Control buttons: Play ▶ Stop ⏹ Reset ⟲
- **New**: Command Palette button (triggers agent query input)

**Changes**:
- Redesign with `bg-[#0F1115]` and `h-14`
- Add button group with hover states
- Monospace font for project name

---

### 2. Left Sidebar: Runs (`components/RunsSidebar.tsx`)
**Purpose**: List of all simulation runs

**Display**:
- Run ID (monospace, e.g., "OM-945")
- Status pill with colored dot
- Timestamp
- Active run has blue left border

**Status colors**:
- 🔵 Running (blue)
- 🟢 Success (emerald)
- 🟡 Warning (amber)
- 🔴 Failed (red)

**Implementation**:
```tsx
// components/RunsSidebar.tsx
- Map over runs from API
- Use StatusPill component for status
- onClick sets active run
- Scroll container with custom scrollbar
```

---

### 3. Main Panel: Agent Orchestration (`components/AgentPanel.tsx`)

#### Top Section: Agent Flow (h-auto)
**Purpose**: Show which agents are active

**Display**: 3-column card layout
- **Intent Classifier**: "Analyzing request..."
- **Study Planner**: "Generating spec..." [●] ← pulsing dot if active
- **Executor**: "Waiting..."

**Agent states**:
- Active: Blue pulsing dot, higher opacity
- Complete: Green checkmark
- Pending: Gray, lower opacity

#### Bottom Section: Execution Logs (h-64)
**Purpose**: Terminal-style log output

**Display**:
- Fixed-height scrollable container
- Monospace font
- Color-coded by type:
  - INFO: gray
  - WARNING: amber
  - PROCESS: blue
  - ERROR: red
- Timestamps on left
- Animated cursor `▊` when streaming

**Implementation**:
```tsx
// components/ExecutionLogs.tsx
- useEventStream hook for SSE
- Auto-scroll to bottom on new log
- Filter buttons for log types
```

---

### 4. Right Sidebar: Telemetry (`components/TelemetrySidebar.tsx`)

#### Section 1: Live Metrics
**k-eff Card**:
- Large number: `1.00245`
- Uncertainty: `± 0.00012`
- Status badge: `[NOMINAL]`

**Convergence Card**:
- Progress bar (visual)
- Text: "Batch 82/100"
- Percentage: "82%"

#### Section 2: Interlocks
**Purpose**: Validation checks

**Display**:
- Geometry Check ✓ (green)
- Cross Section ✓ (green)
- Convergence Variance ⚠ (amber)

#### Section 3: Resources
- CPU: "128 cores @ 82%"
- Agent cost: "$4.22"
- Export button

**Implementation**:
```tsx
// components/TelemetrySidebar.tsx
- MetricCard sub-component
- ProgressBar sub-component
- Poll results API every 2s
```

---

### 5. Footer: Status Bar (`components/StatusFooter.tsx`)
- Left: `● SYSTEM READY` (pulsing green dot) + OpenMC version
- Right: Latency | Token count | ETA
- Background: `bg-[#050607]`
- Height: `h-8`
- Text: `text-[10px]` monospace

---

## Agent Integration: Autonomous Loop

### Current Agent Capabilities (from tests)
1. **Intent Classifier** - Routes query to correct agent
2. **Study Planner** - Extracts specs from natural language
3. **Sweep Planner** - Generates parameter sweeps
4. **Executor** - Runs simulations
5. **Query Agent** - Searches past results
6. **Analyzer** - Interprets results
7. **Suggester** - Recommends next experiments

### New Feature: Autonomous Experimentation Loop

**Goal**: Agents continuously propose and run new experiments

**Implementation**:
```
1. User starts with initial query
   └─> "Simulate PWR pin at various enrichments"

2. Agent executes sweep (3%, 4%, 5%)
   └─> Gets results

3. Analyzer identifies trend
   └─> "k-eff increases linearly with enrichment"

4. Suggester proposes next experiments
   └─> "Try 5.5% to test linearity limit"
   └─> "Vary temperature at 5% enrichment"
   └─> "Test geometry sensitivity"

5. **Auto-queue suggestions** (NEW)
   └─> Add to experiment queue
   └─> Execute automatically if "autonomous mode" enabled

6. Loop continues...
   └─> Each result triggers new suggestions
   └─> Build experiment tree
```

### Frontend Components for Agent Loop

#### New: Experiment Queue Panel (`components/ExperimentQueue.tsx`)
**Purpose**: Show upcoming agent-proposed experiments

**Display**:
- List of queued experiments
- Status: Queued | Running | Complete
- "Pause Queue" button
- "Clear Queue" button

**Location**: Replace or augment left sidebar

#### New: Agent Suggestion Cards (`components/SuggestionCards.tsx`)
**Purpose**: Show agent reasoning and proposals

**Display**:
- Card per suggestion
- Reasoning: "Based on trend analysis..."
- Proposed spec preview
- Actions: "Queue" | "Run Now" | "Dismiss"

**Location**: Overlay or right panel section

#### New: Experiment Tree View (`components/ExperimentTree.tsx`)
**Purpose**: Visualize how experiments relate

**Display**:
- Tree graph (React Flow or similar)
- Nodes = experiments
- Edges = "suggested by" relationships
- Color by status

**Location**: Optional full-screen view (accessible via command palette)

---

## API Endpoints

### Existing (from backend)
- `POST /validate` - Validate study spec
- `POST /run` - Submit simulation
- `GET /runs/{run_id}` - Get run status
- `GET /health` - System health

### New (required for MVP)
- `POST /agent/query` - Submit natural language query to agents
  - Request: `{ query: "Simulate PWR at 4.5% enrichment" }`
  - Response: `{ intent, agent_path, run_ids, results, suggestions }`

- `GET /agent/suggestions` - Get pending suggestions
  - Response: `[{ id, reasoning, spec, priority }]`

- `POST /agent/suggestions/{id}/queue` - Queue a suggestion
- `POST /agent/suggestions/{id}/dismiss` - Dismiss a suggestion

- `GET /experiments/tree` - Get experiment relationship graph
  - Response: `{ nodes: [...], edges: [...] }`

- `POST /autonomous/toggle` - Enable/disable autonomous mode
  - Request: `{ enabled: true }`

- `GET /stream/logs` - SSE endpoint for real-time logs

---

## Color Palette (Tailwind Config)

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        mc: {
          bg: {
            primary: '#0A0B0D',
            secondary: '#0F1115',
            tertiary: '#050607',
            card: '#14161B',
          },
          border: {
            default: '#1F2937',
            subtle: '#111827',
          },
          status: {
            running: '#3B82F6',
            success: '#10B981',
            warning: '#F59E0B',
            failed: '#EF4444',
            info: '#9CA3AF',
          },
          text: {
            primary: '#D1D5DB',
            secondary: '#9CA3AF',
            tertiary: '#6B7280',
          }
        }
      }
    }
  }
}
```

---

## Implementation Plan

### Phase 1: Core Layout (2-3 hours)
- [ ] Update `globals.css` with dark theme
- [ ] Create `MissionControlLayout.tsx` with 4-zone grid
- [ ] Build `StatusFooter.tsx`
- [ ] Update Tailwind config with color palette

### Phase 2: Top Bar & Sidebar (2 hours)
- [ ] Redesign `TopBar.tsx`
- [ ] Create `RunsSidebar.tsx`
- [ ] Create `StatusPill.tsx` component
- [ ] Wire up to existing `/runs` API

### Phase 3: Agent Panel (3 hours)
- [ ] Create `AgentPanel.tsx` with agent cards
- [ ] Add pulsing animations for active agents
- [ ] Redesign `ExecutionLogs.tsx` as terminal
- [ ] Implement log color coding

### Phase 4: Telemetry Sidebar (2 hours)
- [ ] Create `TelemetrySidebar.tsx`
- [ ] Build `MetricCard` for k-eff display
- [ ] Build `ProgressBar` for convergence
- [ ] Add interlocks checklist
- [ ] Wire up to `/runs/{id}` API

### Phase 5: Agent Integration (4 hours)
- [ ] Create backend route `POST /agent/query`
- [ ] Integrate with existing `aonp_agents.py`
- [ ] Create `CommandPalette.tsx` for query input
- [ ] Display agent flow in real-time

### Phase 6: Autonomous Loop (4 hours)
- [ ] Create `POST /agent/suggestions/queue` endpoint
- [ ] Create `ExperimentQueue.tsx` component
- [ ] Create `SuggestionCards.tsx` component
- [ ] Add "Autonomous Mode" toggle
- [ ] Implement auto-queue logic in backend

### Phase 7: Polish (2 hours)
- [ ] Add loading states
- [ ] Add error boundaries
- [ ] Test responsive layout
- [ ] Add keyboard shortcuts
- [ ] Performance optimization

---

## Technical Stack

**Frontend**:
- Next.js 14 (App Router)
- Tailwind CSS 4
- React Query for data fetching
- Lucide React for icons
- EventSource for SSE

**Backend** (existing):
- FastAPI
- MongoDB
- LangGraph + LangChain
- OpenMC

---

## Agent Loop Configuration

### Autonomous Mode Settings
```json
{
  "autonomous_mode": {
    "enabled": true,
    "max_queue_size": 10,
    "auto_execute_suggestions": true,
    "suggestion_threshold": 0.7,  // Only queue high-confidence suggestions
    "cooldown_seconds": 30,  // Wait between auto-executions
    "max_iterations": 50  // Stop after N experiments
  }
}
```

### Safety Limits
- Max queue size: 10 experiments
- Cooldown between runs: 30s
- Cost limit: $50/day
- Manual approval required for:
  - Experiments >10K particles
  - Novel geometry types
  - Sweeps >10 runs

---

## Key Workflows

### Workflow 1: Manual Single Study
1. User clicks "Command Palette"
2. Types: "Simulate PWR at 4.5% enrichment"
3. Intent Classifier activates (UI shows pulsing dot)
4. Study Planner generates spec (UI shows spec preview)
5. User clicks "Execute"
6. Executor runs simulation (logs stream in terminal)
7. Results appear in telemetry sidebar
8. Analyzer generates interpretation
9. Suggester shows 3 follow-up cards
10. User can queue or dismiss

### Workflow 2: Autonomous Sweep
1. User enables "Autonomous Mode"
2. User submits: "Explore enrichment space for PWR"
3. Sweep Planner generates 3-5% sweep
4. Executor runs all variants
5. Analyzer detects trend
6. Suggester proposes: "Test 5.5% and 6%"
7. **Auto-queued** (no user action)
8. Executor runs new sweep
9. Loop continues until:
   - Cost limit hit
   - Iteration limit hit
   - User pauses queue
   - Physical constraint found (e.g., geometry invalid)

### Workflow 3: Query & Compare
1. User asks: "Show me all critical PWR configs"
2. Query Agent searches MongoDB
3. Results appear in runs sidebar (filtered)
4. User selects 2 runs
5. Clicks "Compare"
6. Analysis Agent generates diff and interpretation
7. Suggester: "Try intermediate enrichment between these"

---

## Testing Strategy

### Frontend
- [ ] Storybook for isolated component testing
- [ ] Playwright for E2E flows
- [ ] Test autonomous loop with mock backend

### Backend
- [ ] Test agent routing (use existing `test_aonp_agents.py`)
- [ ] Test suggestion generation
- [ ] Test queue management
- [ ] Test safety limits

### Integration
- [ ] Test full autonomous loop (10 iterations)
- [ ] Test SSE log streaming
- [ ] Test error recovery (failed simulation)

---

## Success Criteria

✅ Dark mission control aesthetic matches reference  
✅ All agent types working (classifier, planner, executor, analyzer, suggester)  
✅ Real-time logs streaming via SSE  
✅ Autonomous mode successfully runs 10+ experiments without intervention  
✅ Suggestions generated after each run  
✅ Experiment queue functional  
✅ Status indicators clear and accurate  
✅ No breaking changes to existing API contracts  

---

## Estimated Time: 19-22 hours

**Breakdown**:
- Frontend: 11-13 hours
- Backend agent integration: 4-5 hours
- Testing & polish: 4 hours

---

## Next Steps

1. **Start**: Update `globals.css` and Tailwind config
2. **Build**: Core layout and components
3. **Integrate**: Connect to agent backend
4. **Test**: Run autonomous loop with mock data
5. **Deploy**: Test with real OpenMC

---

## Notes

- **Mobile**: Not required for MVP (desktop-first)
- **Accessibility**: Basic keyboard nav only (no full WCAG audit)
- **Experiment tree**: Optional (nice-to-have, not blocking)
- **Cost tracking**: Hardcoded placeholder for MVP (real tracking in v2)
- **Command palette**: Simple modal for MVP (advanced fuzzy search in v2)


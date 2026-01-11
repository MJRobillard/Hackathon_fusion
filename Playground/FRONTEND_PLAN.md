# AONP Multi-Agent Frontend - Implementation Plan

**Version:** 2.0  
**Backend API:** FastAPI v2.0.0  
**Architecture:** Router + 4 Specialist Agents  
**Status:** Ready for Implementation

---

## Executive Summary

This document provides a **complete frontend implementation plan** for the AONP Multi-Agent Nuclear Simulation System. The frontend connects to the FastAPI backend (already built and tested) and visualizes the Router + 4 Specialist Agents workflow.

**Key Features:**
- Natural language query interface
- Real-time agent workflow visualization
- Request history with instant recall
- Live execution logs via Server-Sent Events
- Results display with AI analysis
- Fast keyword routing (default) or LLM routing (optional)

---

## Technology Stack Recommendation

### Option 1: React + Vite (Recommended)
**Best for:** Fast development, modern tooling, large ecosystem

```bash
npm create vite@latest aonp-frontend -- --template react-ts
cd aonp-frontend
npm install
npm install @tanstack/react-query axios lucide-react tailwindcss
```

**Pros:**
- ⚡ Extremely fast dev server (Vite)
- 📦 Large component library ecosystem
- 🔥 Hot module replacement
- 💪 TypeScript support out of the box

### Option 2: Next.js (Alternative)
**Best for:** SEO requirements, server-side rendering needs

```bash
npx create-next-app@latest aonp-frontend --typescript --tailwind
```

**Pros:**
- 🚀 Built-in routing
- 📱 Better mobile performance
- 🔍 SEO optimized

### Option 3: Vue 3 + Vite (Alternative)
**Best for:** Simpler learning curve, cleaner syntax

```bash
npm create vite@latest aonp-frontend -- --template vue-ts
```

---

## Architecture Overview

### Our 4-Agent System

```
User Query → Router Agent → Specialist Agent → Tools → Results
                  ↓
            ┌─────┴────────┬──────────┬──────────┐
            ↓              ↓          ↓          ↓
        Studies        Sweep      Query     Analysis
        Agent         Agent      Agent      Agent
```

**Key Differences from 8-Agent Design:**
- **Simpler workflow:** Router → Specialist → Results
- **Fast routing:** Keyword-based (10ms) by default, LLM optional
- **Direct agent access:** Can bypass router for specific agents
- **Tool transparency:** See exactly which tools are called

---

## UI Layout Design

### Overall Structure (1400px minimum)

```
┌─────────────────────────────────────────────────────────────────┐
│ Top Bar: Input + Submit + Mode Toggle                     56px  │
├──────────┬──────────────────────────────────┬────────────────────┤
│          │                                  │                    │
│ Left     │       Center Panel               │   Right Sidebar    │
│ Sidebar  │                                  │                    │
│          │  ┌──────────────────────────┐    │   Results          │
│ Recent   │  │  Agent Workflow          │    │   ┌──────────────┐ │
│ Requests │  │  [Router] → [Specialist] │    │   │ keff Results │ │
│          │  │     ↓           ↓        │    │   │ 1.045±0.002  │ │
│ q_8e74   │  │  [Fast]    [Execute]     │    │   ├──────────────┤ │
│ ✓ 2m ago │  └──────────────────────────┘    │   │ Analysis     │ │
│          │                                  │   │ Critical...  │ │
│ q_7a3c   │  ┌──────────────────────────┐    │   ├──────────────┤ │
│ 🔄 30s   │  │ Execution Logs:          │    │   │ Suggestions  │ │
│          │  │ [ROUTER] → studies       │    │   │ 1. Try 5%... │ │
│ q_5f91   │  │ [STUDIES] Extracting...  │    │   │ 2. Vary T... │ │
│ ✓ 15m    │  │ [TOOL] submit_study      │    │   └──────────────┘ │
│          │  │ [RESULT] keff=1.045      │    │                    │
│          │  └──────────────────────────┘    │                    │
│ 280px    │           flex-1                 │      360px         │
└──────────┴──────────────────────────────────┴────────────────────┘
│ Footer: Studies: 42 | Runs: 157 | MongoDB: ✓             32px │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Top Bar (`TopBar.tsx`)

**Purpose:** Primary input interface with routing mode selector

```typescript
interface TopBarProps {
  onSubmit: (query: string, useLLM: boolean) => void;
  isProcessing: boolean;
  activeQueryId?: string;
}

// Features:
// - Large text input (full width)
// - Submit button (disabled while processing)
// - Mode toggle: ⚡ Fast (keyword) | 🧠 Smart (LLM)
// - Active query indicator with status badge
```

**Visual:**
```
┌──────────────────────────────────────────────────────────────┐
│ [Input: "Simulate PWR at 4.5%..."]  [⚡Fast] [🧠Smart] [Submit] │
│                                           q_8e74 | ✓ completed │
└──────────────────────────────────────────────────────────────┘
```

**API Integration:**
```typescript
const submitQuery = async () => {
  const response = await fetch('http://localhost:8000/api/v1/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      query: inputValue,
      use_llm: useLLMMode  // false = fast keyword, true = LLM
    })
  });
  const { query_id } = await response.json();
  return query_id;
};
```

---

### 2. Left Sidebar (`RequestHistory.tsx`)

**Purpose:** Recent queries with instant recall

```typescript
interface Request {
  query_id: string;
  query: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  created_at: string;
  routing?: {
    agent: string;
    intent: string;
    method: 'keyword' | 'llm';
  };
}

interface RequestHistoryProps {
  requests: Request[];
  activeQueryId?: string;
  onSelect: (queryId: string) => void;
}
```

**Display Format:**
```
📋 Recent Requests
┌────────────────────┐
│ q_8e74             │ ← Click to load
│ "PWR sweep 3-5%"   │
│ ✓ completed        │
│ 🔀 studies (⚡)    │ ← Shows agent + routing method
│ 2m ago             │
├────────────────────┤
│ q_7a3c             │
│ "BWR single run"   │
│ 🔄 processing      │
│ 🔀 sweep (⚡)      │
│ 30s ago            │
└────────────────────┘
```

**API Integration:**
```typescript
// Poll for updates (or use SSE)
const pollRequests = async () => {
  const response = await fetch('http://localhost:8000/api/v1/statistics');
  const data = await response.json();
  // Get recent queries from statistics or separate endpoint
};
```

---

### 3. Agent Workflow Cards (`AgentWorkflow.tsx`)

**Purpose:** Visualize routing + execution flow

**Our 4-Agent Flow:**

```
┌──────────┐   ┌───────────┐   ┌──────────┐
│  Router  │ → │ Specialist│ → │  Tools   │
│          │   │  Agent    │   │          │
│ ✓ Fast   │   │ 🔄 Running│   │ ⏳ Waiting│
│ 10ms     │   │ studies   │   │ submit   │
└──────────┘   └───────────┘   └──────────┘
```

**Status Colors:**
- ⏳ Waiting: `text-gray-500`
- 🔄 Running: `text-blue-400` with pulse animation
- ✓ Complete: `text-emerald-400`
- ✗ Failed: `text-red-400`

**Agent-Specific Icons:**
```typescript
const AGENT_ICONS = {
  'studies': '🔬', // Single simulation
  'sweep': '🔄',   // Parameter sweep
  'query': '🔍',   // Database search
  'analysis': '📊' // Comparison
};

const ROUTING_BADGES = {
  'keyword': '⚡ Fast',  // 10ms routing
  'llm': '🧠 Smart'      // 2-5s routing
};
```

---

### 4. Execution Logs (`ExecutionLogs.tsx`)

**Purpose:** Real-time agent transition and tool call logs

**Log Format:**
```typescript
interface LogEntry {
  timestamp: string;
  level: 'info' | 'success' | 'warning' | 'error';
  source: 'ROUTER' | 'STUDIES' | 'SWEEP' | 'QUERY' | 'ANALYSIS' | 'TOOL';
  message: string;
}
```

**Example Output:**
```
14:30:05  [ROUTER] Analyzing query with keyword routing...
14:30:05  [ROUTER] ✓ Routed to: studies (confidence: 0.8)
14:30:06  [STUDIES] Extracting spec from query...
14:30:06  [STUDIES] ✓ Enrichment: 4.5%, Temperature: 600K
14:30:07  [TOOL] submit_study - Starting simulation...
14:30:22  [TOOL] submit_study - ✓ keff = 1.045 ± 0.002
14:30:22  [STUDIES] ✓ Study completed: run_8e742c47
```

**API Integration (Server-Sent Events):**
```typescript
const connectToEventStream = (queryId: string) => {
  const eventSource = new EventSource(
    `http://localhost:8000/api/v1/query/${queryId}/stream`
  );

  eventSource.addEventListener('routing', (e) => {
    const data = JSON.parse(e.data);
    addLog({ source: 'ROUTER', message: data.message });
  });

  eventSource.addEventListener('query_complete', (e) => {
    addLog({ source: 'SYSTEM', message: '✓ Query completed' });
    eventSource.close();
  });

  return eventSource;
};
```

---

### 5. Results Panel (`ResultsPanel.tsx`)

**Purpose:** Display simulation results with AI analysis

**Layout (3 sections):**

#### Section 1: Results Summary
```typescript
interface Results {
  type: 'single_study' | 'sweep' | 'query' | 'analysis';
  
  // Single study
  run_id?: string;
  keff?: number;
  keff_std?: number;
  
  // Sweep
  run_ids?: string[];
  keff_values?: number[];
  keff_mean?: number;
  keff_min?: number;
  keff_max?: number;
  
  // Query
  count?: number;
  results?: any[];
  
  // Analysis
  comparison?: any;
}
```

**Display Example:**
```
📊 Results
─────────────────────

Single Study:
  Run ID: run_8e742c47
  k-eff: 1.045 ± 0.002
  Status: ⚠️ SUPERCRITICAL

  Geometry: PWR pin cell
  Enrichment: 4.5%
  Temperature: 600K
  Particles: 10,000
  Batches: 50

─────────────────────

Parameter Sweep:
  Runs: 5
  k-eff range: [0.980, 1.084]
  k-eff mean: 1.022
  Status: Critical at ~3.8%
```

**Criticality Indicators:**
```typescript
const getCriticalityStatus = (keff: number) => {
  if (keff < 0.98) return { 
    label: '⚡ SUBCRITICAL', 
    color: 'text-amber-400' 
  };
  if (keff <= 1.02) return { 
    label: '✓ CRITICAL', 
    color: 'text-emerald-400' 
  };
  return { 
    label: '⚠️ SUPERCRITICAL', 
    color: 'text-red-400' 
  };
};
```

#### Section 2: AI Analysis (if available)
```
🔬 Analysis
─────────────────────

k-eff = 1.045 ± 0.002 indicates supercritical 
configuration. Low uncertainty (0.2%) suggests 
consistent neutron multiplication. System would 
experience net neutron gain, requiring control 
measures to prevent uncontrolled power increase.
```

#### Section 3: Suggestions (if available)
```
💡 Next Experiments
─────────────────────

1. Validate with different enrichment (4.0%, 5.0%)
   to confirm k-eff trend

2. Test temperature dependence (500K-700K) to
   assess thermal feedback effects

3. Evaluate coolant variations (H2O vs borated)
```

---

### 6. Footer (`Footer.tsx`)

**Purpose:** System statistics and health status

```typescript
interface SystemStats {
  total_studies: number;
  total_runs: number;
  completed_runs: number;
  total_queries: number;
  mongodb_status: 'connected' | 'disconnected';
}
```

**Display:**
```
┌────────────────────────────────────────────────────────────┐
│ Studies: 42 | Runs: 157 | Queries: 23 | MongoDB: ✓       │
└────────────────────────────────────────────────────────────┘
```

**API Integration:**
```typescript
const fetchStats = async () => {
  const response = await fetch('http://localhost:8000/api/v1/statistics');
  return await response.json();
};

// Poll every 30 seconds
useEffect(() => {
  const interval = setInterval(fetchStats, 30000);
  return () => clearInterval(interval);
}, []);
```

---

## State Management

### Recommended: React Query (TanStack Query)

**Why:** Built-in caching, automatic refetching, SSE support

```typescript
import { useQuery, useMutation } from '@tanstack/react-query';

// Query hook
const useQueryStatus = (queryId: string) => {
  return useQuery({
    queryKey: ['query', queryId],
    queryFn: async () => {
      const response = await fetch(
        `http://localhost:8000/api/v1/query/${queryId}`
      );
      return response.json();
    },
    refetchInterval: (data) => {
      // Poll every 2s while processing, stop when complete
      return data?.status === 'processing' ? 2000 : false;
    }
  });
};

// Mutation hook
const useSubmitQuery = () => {
  return useMutation({
    mutationFn: async ({ query, use_llm }) => {
      const response = await fetch(
        'http://localhost:8000/api/v1/query',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, use_llm })
        }
      );
      return response.json();
    }
  });
};
```

### Alternative: Zustand (Simple State)

```typescript
import create from 'zustand';

interface AppState {
  activeQueryId: string | null;
  queries: Map<string, Query>;
  useLLMMode: boolean;
  
  setActiveQuery: (id: string) => void;
  addQuery: (query: Query) => void;
  toggleLLMMode: () => void;
}

const useStore = create<AppState>((set) => ({
  activeQueryId: null,
  queries: new Map(),
  useLLMMode: false,
  
  setActiveQuery: (id) => set({ activeQueryId: id }),
  addQuery: (query) => set((state) => ({
    queries: new Map(state.queries).set(query.query_id, query)
  })),
  toggleLLMMode: () => set((state) => ({
    useLLMMode: !state.useLLMMode
  }))
}));
```

---

## API Integration Guide

### Complete Endpoint Reference

```typescript
const API_BASE = 'http://localhost:8000';

// 1. Submit Query (Main Interface)
POST /api/v1/query
Body: { query: string, use_llm: boolean }
→ { query_id: string, status: string, stream_url?: string }

// 2. Get Query Status
GET /api/v1/query/{query_id}
→ { 
    status: string, 
    query: string,
    routing: { agent: string, intent: string },
    results: { keff, run_id, ... }
  }

// 3. Stream Progress (SSE)
GET /api/v1/query/{query_id}/stream
→ Server-Sent Events with routing, progress, completion

// 4. Test Routing
POST /api/v1/router
Body: { query: string, use_llm: boolean }
→ { agent: string, intent: string, confidence: number }

// 5. Direct Agent Access
POST /api/v1/agents/studies
POST /api/v1/agents/sweep
POST /api/v1/agents/query
POST /api/v1/agents/analysis
Body: { query: string }
→ { status: string, results: {...} }

// 6. Direct Tool Access (Fastest)
POST /api/v1/studies
Body: { 
  geometry: string,
  materials: string[],
  enrichment_pct: number,
  temperature_K: number
}
→ { run_id: string, keff: number, keff_std: number }

// 7. Query Runs
GET /api/v1/runs?geometry=PWR&keff_min=1.0&limit=10
→ { total: number, runs: [...] }

// 8. System Status
GET /api/v1/health
→ { status: string, services: {...} }

GET /api/v1/statistics
→ { total_studies, total_runs, ... }
```

### Example API Service (`api/queryService.ts`)

```typescript
export class QueryService {
  private baseUrl = 'http://localhost:8000';

  async submitQuery(query: string, useLLM: boolean = false) {
    const response = await fetch(`${this.baseUrl}/api/v1/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, use_llm: useLLM })
    });
    return response.json();
  }

  async getQueryStatus(queryId: string) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/query/${queryId}`
    );
    return response.json();
  }

  createEventStream(queryId: string): EventSource {
    return new EventSource(
      `${this.baseUrl}/api/v1/query/${queryId}/stream`
    );
  }

  async testRouting(query: string, useLLM: boolean) {
    const response = await fetch(`${this.baseUrl}/api/v1/router`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, use_llm: useLLM })
    });
    return response.json();
  }

  async getStatistics() {
    const response = await fetch(`${this.baseUrl}/api/v1/statistics`);
    return response.json();
  }
}

export const queryService = new QueryService();
```

---

## Styling Guide (Tailwind CSS)

### Color Palette

```css
/* Base colors */
--bg-primary: #0A0B0D;      /* Main background */
--bg-panel: #0F1115;         /* Panel background */
--bg-card: #111827;          /* Card background */
--border-subtle: #1F2937;    /* Borders */

/* Status colors */
--status-waiting: #6B7280;   /* Gray */
--status-running: #3B82F6;   /* Blue */
--status-complete: #10B981;  /* Green */
--status-failed: #EF4444;    /* Red */
--status-warning: #F59E0B;   /* Amber */

/* Agent colors */
--agent-studies: #3B82F6;    /* Blue */
--agent-sweep: #8B5CF6;      /* Purple */
--agent-query: #10B981;      /* Green */
--agent-analysis: #F97316;   /* Orange */
```

### Component Classes

```css
/* Cards */
.card {
  @apply bg-gray-900 border border-gray-800 rounded-lg p-4;
}

.card-hover {
  @apply hover:bg-gray-800/50 transition-colors cursor-pointer;
}

.card-active {
  @apply bg-blue-600/10 border-l-2 border-l-blue-500;
}

/* Status badges */
.badge {
  @apply inline-flex items-center gap-1 px-2 py-0.5 rounded-full 
         text-[10px] font-mono uppercase border;
}

.badge-running {
  @apply text-blue-400 border-blue-400/30 bg-blue-400/10;
}

.badge-complete {
  @apply text-emerald-400 border-emerald-400/30 bg-emerald-400/10;
}

/* Logs */
.log-entry {
  @apply flex gap-4 font-mono text-[11px] text-gray-300;
}

.log-timestamp {
  @apply text-gray-600 shrink-0 w-20;
}

.log-source {
  @apply font-bold text-blue-400;
}
```

---

## Implementation Roadmap

### Phase 1: Core UI (Week 1)
- [ ] Project setup (Vite + React + TypeScript + Tailwind)
- [ ] Top bar with input and submit
- [ ] Basic layout (sidebar + center + results)
- [ ] Request history sidebar
- [ ] API integration for query submission

### Phase 2: Agent Visualization (Week 2)
- [ ] Agent workflow cards
- [ ] Status indicators and animations
- [ ] Execution logs component
- [ ] SSE integration for real-time updates
- [ ] Mode toggle (Fast vs Smart routing)

### Phase 3: Results Display (Week 3)
- [ ] Results panel with adaptive display
- [ ] Criticality status indicators
- [ ] Analysis section
- [ ] Suggestions section
- [ ] Footer statistics

### Phase 4: Polish & Testing (Week 4)
- [ ] Error handling and loading states
- [ ] Keyboard shortcuts
- [ ] Accessibility improvements
- [ ] Performance optimization
- [ ] End-to-end testing

---

## Development Setup

### 1. Create React App

```bash
# Navigate to Playground directory
cd Playground

# Create React app with Vite
npm create vite@latest frontend -- --template react-ts

cd frontend
npm install
```

### 2. Install Dependencies

```bash
npm install @tanstack/react-query axios lucide-react

# Install Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 3. Configure Tailwind

```javascript
// tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0A0B0D',
        'bg-panel': '#0F1115',
        'bg-card': '#111827',
      }
    },
  },
  plugins: [],
}
```

### 4. Configure API Proxy (dev mode)

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

### 5. Start Development

```bash
# Terminal 1: Backend
cd Playground/backend
python start_server.py

# Terminal 2: Frontend
cd Playground/frontend
npm run dev
```

---

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── TopBar.tsx           # Query input + mode toggle
│   │   ├── RequestHistory.tsx   # Left sidebar
│   │   ├── AgentWorkflow.tsx    # Agent cards
│   │   ├── ExecutionLogs.tsx    # Real-time logs
│   │   ├── ResultsPanel.tsx     # Results display
│   │   └── Footer.tsx           # Statistics
│   │
│   ├── hooks/
│   │   ├── useQuery.ts          # Query submission logic
│   │   ├── useEventStream.ts    # SSE connection
│   │   └── useStatistics.ts     # Stats polling
│   │
│   ├── services/
│   │   ├── api.ts               # API client
│   │   └── queryService.ts      # Query operations
│   │
│   ├── types/
│   │   └── index.ts             # TypeScript interfaces
│   │
│   ├── utils/
│   │   ├── formatters.ts        # Data formatting
│   │   └── constants.ts         # Constants
│   │
│   ├── App.tsx                  # Main app
│   └── main.tsx                 # Entry point
│
├── public/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

---

## Key Features Implementation

### 1. Real-Time Updates with SSE

```typescript
const useEventStream = (queryId: string) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<string>('queued');

  useEffect(() => {
    const eventSource = new EventSource(
      `http://localhost:8000/api/v1/query/${queryId}/stream`
    );

    eventSource.addEventListener('routing', (e) => {
      const data = JSON.parse(e.data);
      setLogs(prev => [...prev, {
        timestamp: new Date().toISOString(),
        source: 'ROUTER',
        message: data.message,
        level: 'info'
      }]);
    });

    eventSource.addEventListener('query_complete', (e) => {
      setStatus('completed');
      eventSource.close();
    });

    return () => eventSource.close();
  }, [queryId]);

  return { logs, status };
};
```

### 2. Polling Fallback (if SSE unavailable)

```typescript
const usePollQueryStatus = (queryId: string) => {
  return useQuery({
    queryKey: ['query', queryId],
    queryFn: async () => {
      const res = await fetch(
        `http://localhost:8000/api/v1/query/${queryId}`
      );
      return res.json();
    },
    refetchInterval: (data) => {
      // Stop polling when complete or failed
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
    enabled: !!queryId
  });
};
```

### 3. Mode Toggle (Fast vs Smart)

```typescript
const ModeToggle = ({ value, onChange }) => {
  return (
    <div className="flex gap-1 p-1 bg-gray-800 rounded-lg">
      <button
        onClick={() => onChange(false)}
        className={`px-3 py-1 rounded text-xs font-medium transition ${
          !value 
            ? 'bg-blue-600 text-white' 
            : 'text-gray-400 hover:text-gray-200'
        }`}
      >
        ⚡ Fast
        <span className="text-[10px] ml-1 opacity-60">(10ms)</span>
      </button>
      <button
        onClick={() => onChange(true)}
        className={`px-3 py-1 rounded text-xs font-medium transition ${
          value 
            ? 'bg-purple-600 text-white' 
            : 'text-gray-400 hover:text-gray-200'
        }`}
      >
        🧠 Smart
        <span className="text-[10px] ml-1 opacity-60">(2-5s)</span>
      </button>
    </div>
  );
};
```

---

## Testing Strategy

### 1. Component Tests (Jest + React Testing Library)

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { TopBar } from './TopBar';

test('submits query when button clicked', async () => {
  const mockSubmit = jest.fn();
  render(<TopBar onSubmit={mockSubmit} />);
  
  const input = screen.getByPlaceholderText(/simulate/i);
  const button = screen.getByRole('button', { name: /submit/i });
  
  fireEvent.change(input, { target: { value: 'PWR at 4.5%' } });
  fireEvent.click(button);
  
  expect(mockSubmit).toHaveBeenCalledWith('PWR at 4.5%', false);
});
```

### 2. API Integration Tests

```typescript
import { queryService } from './services/queryService';

test('submits query and returns query_id', async () => {
  const result = await queryService.submitQuery('Test query');
  
  expect(result).toHaveProperty('query_id');
  expect(result.query_id).toMatch(/^q_[a-f0-9]{8}$/);
  expect(result.status).toBe('queued');
});
```

### 3. E2E Tests (Playwright/Cypress)

```typescript
test('complete workflow: submit → process → results', async () => {
  // Submit query
  await page.fill('input[placeholder*="Simulate"]', 'PWR at 4.5%');
  await page.click('button:has-text("Submit")');
  
  // Wait for processing
  await page.waitForSelector('text=/✓ completed/', { timeout: 30000 });
  
  // Check results
  await expect(page.locator('text=/k-eff/')).toBeVisible();
  await expect(page.locator('text=/run_/')).toBeVisible();
});
```

---

## Performance Optimization

### 1. Code Splitting

```typescript
// Lazy load heavy components
const ResultsPanel = lazy(() => import('./components/ResultsPanel'));
const ExecutionLogs = lazy(() => import('./components/ExecutionLogs'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <ResultsPanel />
      <ExecutionLogs />
    </Suspense>
  );
}
```

### 2. Memoization

```typescript
const AgentCard = memo(({ agent, status }) => {
  return (
    <div className="card">
      <div>{agent}</div>
      <StatusBadge status={status} />
    </div>
  );
});

const ResultsPanel = ({ results }) => {
  const formattedResults = useMemo(() => {
    return formatResults(results);
  }, [results]);
  
  return <div>{formattedResults}</div>;
};
```

### 3. Virtual Scrolling (for long log lists)

```typescript
import { FixedSizeList } from 'react-window';

const LogsList = ({ logs }) => {
  return (
    <FixedSizeList
      height={400}
      itemCount={logs.length}
      itemSize={24}
    >
      {({ index, style }) => (
        <div style={style}>
          <LogEntry log={logs[index]} />
        </div>
      )}
    </FixedSizeList>
  );
};
```

---

## Deployment

### Build for Production

```bash
npm run build
```

### Serve Static Files

```bash
# Option 1: Serve with nginx
location / {
    root /var/www/aonp-frontend/dist;
    try_files $uri $uri/ /index.html;
}

location /api {
    proxy_pass http://localhost:8000;
}

# Option 2: Serve with node
npm install -g serve
serve -s dist -l 3000
```

---

## Next Steps

1. **Start Backend:** `cd Playground/backend && python start_server.py`
2. **Create Frontend:** `cd Playground && npm create vite@latest frontend -- --template react-ts`
3. **Install Dependencies:** See "Development Setup" section
4. **Build Components:** Follow "Implementation Roadmap"
5. **Test Integration:** Use provided API examples
6. **Deploy:** Build and serve

---

## Additional Resources

- **Backend API Docs:** http://localhost:8000/docs
- **Backend Code:** `Playground/backend/api/main_v2.py`
- **API Documentation:** `Playground/backend/API_DOCUMENTATION.md`
- **Frontend Quick Start:** `Playground/backend/FRONTEND_QUICKSTART.md`

---

**You now have everything needed to build the frontend!** 🚀

The backend is ready, tested, and documented. Just follow this plan to create a beautiful UI that connects to it.


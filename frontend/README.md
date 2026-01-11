# AONP Multi-Agent Frontend

Advanced OpenMC Nuclear Physics Multi-Agent Simulation System - Frontend Interface

## Features

- 🔬 **Natural Language Interface** - Submit simulation queries in plain English
- ⚡ **Real-Time Updates** - Live execution logs via Server-Sent Events
- 🔀 **Agent Workflow Visualization** - See routing and execution flow
- 📊 **Results Display** - Criticality analysis with AI-generated insights
- 📝 **Request History** - Instant recall of previous queries
- 🚀 **Fast & Smart Routing** - Choose keyword (10ms) or LLM (2-5s) routing

## Tech Stack

- **Next.js 16** - React framework with server-side rendering
- **TypeScript** - Type-safe development
- **Tailwind CSS 4** - Modern utility-first styling
- **TanStack Query** - Powerful data fetching and caching
- **Lucide React** - Beautiful icon system
- **Server-Sent Events** - Real-time backend communication

## Project Structure

```
frontend/
├── app/
│   ├── page.tsx           # Main application page
│   ├── layout.tsx         # Root layout with providers
│   ├── providers.tsx      # React Query provider
│   └── globals.css        # Global styles
├── components/
│   ├── TopBar.tsx         # Query input and mode toggle
│   ├── RequestHistory.tsx # Left sidebar with query history
│   ├── AgentWorkflow.tsx  # Agent routing visualization
│   ├── ExecutionLogs.tsx  # Real-time execution logs
│   ├── ResultsPanel.tsx   # Results display with analysis
│   └── Footer.tsx         # System statistics
├── hooks/
│   ├── useEventStream.ts  # SSE connection management
│   └── useQueryHistory.ts # Query history state
├── lib/
│   ├── types.ts           # TypeScript type definitions
│   ├── constants.ts       # Application constants
│   ├── api.ts             # API service layer
│   └── formatters.ts      # Data formatting utilities
└── package.json
```

## Getting Started

### Prerequisites

- Node.js 20.9.0 or later
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Usage

### Submit a Query

1. Type your simulation request in the top input bar
2. Choose routing mode:
   - **⚡ Fast** - Keyword-based routing (~10ms)
   - **🧠 Smart** - LLM-powered routing (2-5s)
3. Click **Submit**

### Example Queries

```
Simulate a PWR pin cell at 4.5% enrichment
Run a parameter sweep for BWR from 3% to 5% enrichment
Find all runs with keff > 1.0 and PWR geometry
Compare runs run_abc123 and run_def456
```

### View Results

- **Left Sidebar** - Click any previous query to view its results
- **Center Panel** - Watch agent workflow and execution logs in real-time
- **Right Panel** - See simulation results, analysis, and suggestions

## API Integration

The frontend connects to the backend API at `http://localhost:8000`:

### Main Endpoints

- `POST /api/v1/query` - Submit new query
- `GET /api/v1/query/{id}` - Get query status and results
- `GET /api/v1/query/{id}/stream` - SSE connection for real-time updates
- `GET /api/v1/statistics` - System statistics
- `GET /api/v1/health` - Health check

### Real-Time Updates

The application uses Server-Sent Events (SSE) for real-time updates:

- Routing decisions
- Agent transitions
- Tool executions
- Progress messages
- Completion status

## Development

### Build for Production

```bash
npm run build
npm start
```

### Linting

```bash
npm run lint
```

## Architecture

### 4-Agent System

```
User Query → Router Agent → Specialist Agent → Tools → Results
                  ↓
            ┌─────┴────────┬──────────┬──────────┐
            ↓              ↓          ↓          ↓
        Studies        Sweep      Query     Analysis
        Agent         Agent      Agent      Agent
```

### State Management

- **React Query** - Server state, caching, and refetching
- **React Hooks** - Local component state
- **Custom Hooks** - Event stream and query history management

### Styling

- **Tailwind CSS** - Utility-first styling
- **Dark Theme** - Nuclear physics aesthetic
- **Responsive** - Mobile-friendly layout
- **Custom Colors** - Agent-specific color coding

## Components

### TopBar
Query input with mode toggle and submit button. Shows active query status.

### RequestHistory
Sidebar showing recent queries with status, routing info, and time.

### AgentWorkflow
Visual representation of routing and agent execution flow.

### ExecutionLogs
Real-time logs from router, agents, and tools with color coding.

### ResultsPanel
Displays simulation results with criticality status, AI analysis, and suggestions.

### Footer
System statistics and MongoDB connection status.

## Troubleshooting

### Backend Connection Issues

If you see "Event stream connection lost":
1. Ensure backend is running on `http://localhost:8000`
2. Check CORS settings in backend
3. Verify MongoDB is connected

### No Real-Time Updates

If logs don't update in real-time:
1. Check browser console for SSE errors
2. Verify backend `/stream` endpoint is working
3. Try refreshing the page

## License

Part of the AONP Multi-Agent System project.

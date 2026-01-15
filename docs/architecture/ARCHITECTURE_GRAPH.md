# AONP Architecture Graph

## Core Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                    (frontend/ directory)                         │
│                                                                   │
│  Entry Point: frontend/app/page.tsx                              │
│  └─> Components: frontend/components/*.tsx                       │
│  └─> Hooks: frontend/hooks/*.ts                                  │
│  └─> API Client: frontend/lib/api.ts                             │
│  └─> Config: frontend/next.config.ts (proxies to :8001)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP (localhost:8001)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
│                 (aonp/api/main_v2.py)                            │
│                                                                   │
│  Main API Server: main_v2.py                                      │
│  ├─> geometry_router.py      (Run XML access)                     │
│  ├─> terminal_streamer.py    (SSE terminal streaming)             │
│  └─> aonp/runner/openmc_adapter.py (OpenMC adapter)               │
└─────────────────────────────────────────────────────────────────┘
```

## File Dependency Tree

### Frontend Core Files
```
frontend/
├── app/
│   ├── page.tsx              # Main page
│   ├── layout.tsx            # Root layout
│   ├── providers.tsx         # React Query provider
│   └── globals.css           # Styles
├── components/               # All UI components
├── hooks/
│   ├── useEventStream.ts     # SSE connection
│   └── useQueryHistory.ts    # Query state
├── lib/
│   ├── api.ts                # API client
│   ├── types.ts              # TypeScript types
│   └── constants.ts          # Constants
└── package.json
```

### Backend Core Files
```
aonp/
├── api/
│   ├── main_v2.py            # Main API server
│   ├── geometry_router.py    # Geometry input access
│   └── terminal_streamer.py  # Terminal SSE streaming
├── core/
│   ├── bundler.py            # Creates OpenMC XML bundles
│   └── extractor.py          # Extracts results from statepoints
├── runner/
│   ├── entrypoint.py         # OpenMC simulation runner
│   ├── streaming_runner.py   # Streams OpenMC stdout
│   └── openmc_adapter.py     # Adapter for simplified specs
└── schemas/
    ├── study.py              # Study specification schemas
    └── manifest.py           # Run metadata schemas
```

## Data Flow

```
User Request (Frontend)
    │
    ▼
POST / (aonp/api/main_v2.py)
    │
    ▼
OpenMCAdapter.translate_simple_to_openmc()
    │
    ▼
aonp/core/bundler.py (create_run_bundle)
    │
    ▼
aonp/runner/entrypoint.py (run_simulation)
    │
    ▼
aonp/core/extractor.py (extract results)
```

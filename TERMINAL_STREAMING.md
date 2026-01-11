# Terminal Streaming Implementation

## Overview
Stream ALL backend terminal output (stdout/stderr) to the frontend in real-time via Server-Sent Events (SSE).

## Architecture

```
Backend (Port 8000) → Terminal Interceptor → SSE Stream → Frontend
    ↓                        ↓
All print()          Captures output      Real-time display
statements           & broadcasts         in terminal panel
```

## Key Files

### Backend
- `Playground/backend/terminal_streamer.py` - Core streaming implementation
  - `TerminalBroadcaster` - Manages subscribers and broadcasts output
  - `StreamInterceptor` - Intercepts stdout/stderr
  - `install_terminal_interceptor()` - Hooks into sys.stdout/stderr

- `Playground/backend/api/main.py` - API endpoint
  - Import: `from terminal_streamer import terminal_broadcaster, install_terminal_interceptor`
  - Startup: Initialize broadcaster in `@app.on_event("startup")`
  - Endpoint: `/api/v1/terminal/stream` - SSE stream

### Frontend
- `frontend/hooks/useGlobalTerminalStream.ts` - React hook
  - Connects to `http://localhost:8000/api/v1/terminal/stream`
  - Manages EventSource connection
  - Returns: `{ lines, events, isConnected, error, reconnect, clear }`

- `frontend/components/GlobalTerminal.tsx` - UI component
  - Terminal display with syntax highlighting
  - Features: auto-scroll, copy, download, filter (all/errors/openmc)
  - Color codes: errors (red), warnings (yellow), success (green)

- `frontend/app/page.tsx` - Integration
  - Replaced AgentThinkingPanel with GlobalTerminal
  - Import: `import GlobalTerminal from '@/components/GlobalTerminal'`
  - Usage: `<GlobalTerminal autoScroll={true} maxLines={5000} />`

## Setup

1. **Install terminal streamer** (one-time):
```bash
cp aonp/api/terminal_streamer.py Playground/backend/terminal_streamer.py
```

2. **Start backend**:
```bash
cd Playground/backend/api
uvicorn main:app --reload
```

3. **Start frontend**:
```bash
cd frontend
npm run dev
```

## How It Works

1. **Startup**: `install_terminal_interceptor()` replaces `sys.stdout` and `sys.stderr`
2. **Runtime**: All print statements → `StreamInterceptor.write()` → broadcast to subscribers
3. **Frontend**: EventSource subscribes via SSE, receives JSON events:
```json
{
  "timestamp": "2026-01-11T...",
  "stream": "stdout",
  "content": "Processing query...\n"
}
```

## Common Issues

### ModuleNotFoundError: No module named 'aonp'
**Fix**: Copy `terminal_streamer.py` to `Playground/backend/` and import as:
```python
from terminal_streamer import terminal_broadcaster, install_terminal_interceptor
```

### UnboundLocalError: cannot access local variable 'json'
**Fix**: Add imports at top of file:
```python
import json
from datetime import datetime
```

### Address already in use (port 8000)
**Fix**: Kill existing process:
```bash
lsof -ti:8000 | xargs kill -9
# or
fuser -k 8000/tcp
```

### Connected but no output
**Fix**: Ensure `install_terminal_interceptor()` is called in `@app.on_event("startup")`

## Testing

Test backend streaming:
```bash
python test_global_stream.py
```

Make requests to see output:
```bash
curl http://localhost:8000/api/v1/health
```

## What Gets Streamed
- ✅ All `print()` statements
- ✅ OpenMC simulation output
- ✅ Agent execution logs
- ✅ API request logs (uvicorn)
- ✅ Error tracebacks
- ✅ Database queries
- ✅ LLM API calls


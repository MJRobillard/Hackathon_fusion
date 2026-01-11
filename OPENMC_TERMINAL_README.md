# OpenMC Terminal Streaming

Real-time streaming of OpenMC simulation output to the frontend using Server-Sent Events (SSE).

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend  │  SSE    │   Backend    │  Popen  │    OpenMC    │
│  Terminal   │◄────────│   FastAPI    │◄────────│  Simulation  │
│  Component  │         │   /stream    │         │   (stdout)   │
└─────────────┘         └──────────────┘         └──────────────┘
```

## Backend Implementation

### 1. Streaming Runner (`aonp/runner/streaming_runner.py`)

Captures OpenMC stdout line-by-line using `subprocess.Popen`:

```python
from aonp.runner.streaming_runner import StreamingSimulationRunner

runner = StreamingSimulationRunner(run_dir)
for line in runner.stream_simulation():
    print(line, end='')
```

### 2. SSE Endpoint (`aonp/api/main.py`)

```python
@app.get("/runs/{run_id}/stream")
async def stream_run_execution(run_id: str):
    """Stream OpenMC simulation output using SSE"""
    runner = StreamingSimulationRunner(run_dir)
    
    async def event_generator():
        for line in runner.stream_simulation():
            yield f"data: {line}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

## Frontend Implementation

### 1. Hook (`frontend/hooks/useOpenMCStream.ts`)

Consumes SSE stream and manages connection:

```typescript
const { lines, isConnected, error, isComplete } = useOpenMCStream(runId);
```

Features:
- Auto-reconnect on connection loss
- Line-by-line buffering
- Completion detection
- Error handling

### 2. Terminal Component (`frontend/components/OpenMCTerminal.tsx`)

Beautiful terminal UI with:
- **Syntax highlighting** (errors in red, success in green, etc.)
- **Auto-scroll** with pause when user scrolls up
- **Copy to clipboard**
- **Download log file**
- **Connection status indicator**
- **Real-time streaming**

### 3. Integration in Main UI (`frontend/app/page.tsx`)

The terminal replaces the execution logs component when a simulation is running:

```tsx
{terminalRunId ? (
  <OpenMCTerminal 
    runId={terminalRunId}
    onComplete={() => setIsProcessing(false)}
  />
) : (
  <MissionControlLogs logs={logs} />
)}
```

## Usage

### Start a Simulation with Streaming

```typescript
// In your frontend code, when starting a run:
const response = await apiService.submitRun(studyYaml);
const runId = response.run_id;

// Set the terminal to stream this run
setTerminalRunId(runId);

// The terminal will automatically connect to:
// GET /runs/{run_id}/stream
```

### Backend - Manual Test

```bash
# Test the streaming endpoint directly
curl -N http://localhost:8000/runs/run_abc123/stream

# You should see:
# data: Run ID: run_abc123
# data: Spec Hash: a1b2c3d4...
# data: ==================== ... ====================
# data: Starting OpenMC simulation...
# data: 
# data:        1/1    1.38979
# data:        2/1    1.43209
# ...
```

### Frontend - Manual Test

```bash
cd frontend
npm run dev

# In browser console:
const eventSource = new EventSource('http://localhost:8000/runs/run_abc123/stream');
eventSource.onmessage = (e) => console.log(e.data);
```

## Features

### Terminal UI Features

1. **Colorized Output**
   - Red: Errors (`[ERROR]`, `failed`, `✗`)
   - Yellow: Warnings (`[WARNING]`, `⚠️`)
   - Green: Success (`[OK]`, `✓`, `completed`)
   - Blue: Separators (`===`, `---`)
   - Cyan: Run info (`Run ID:`, `Spec Hash:`)
   - Purple: Batch numbers (`1/1`, `2/1`, etc.)
   - Gray: Info logs (`INFO:`, HTTP requests)

2. **Auto-scroll with Pause**
   - Automatically scrolls to bottom as new lines arrive
   - Pauses when user scrolls up to read
   - "Resume" button appears when paused

3. **Actions**
   - **Copy**: Copy all terminal output to clipboard
   - **Download**: Save log file as `openmc-{runId}-{timestamp}.log`

4. **Status Indicator**
   - Green pulsing: Streaming...
   - Blue: Complete
   - Red: Error
   - Gray: Disconnected

### Backend Features

1. **Real-time Streaming**
   - Line-by-line output capture
   - No buffering delays
   - Immediate delivery to frontend

2. **Error Handling**
   - Validates run directory exists
   - Checks OpenMC installation
   - Updates manifest on success/failure
   - Streams error messages to frontend

3. **Provenance Tracking**
   - Updates run_manifest.json with status
   - Records runtime, OpenMC version, Python version
   - Maintains audit trail

## API Reference

### Backend Endpoint

**GET** `/runs/{run_id}/stream`

Streams OpenMC simulation output using Server-Sent Events.

**Parameters:**
- `run_id` (path): Run identifier

**Returns:**
- Content-Type: `text/event-stream`
- Format: SSE (Server-Sent Events)

**Example Response:**
```
data: Run ID: run_abc123

data: Starting OpenMC simulation...

data:        1/1    1.38979

data:        2/1    1.43209

data: ✓ Simulation completed in 7.23 seconds

```

### Frontend Hook

**useOpenMCStream(runId: string)**

Hook to consume OpenMC SSE stream.

**Returns:**
```typescript
{
  lines: string[];           // Array of output lines
  isConnected: boolean;      // Connection status
  error: string | null;      // Error message if failed
  isComplete: boolean;       // True when simulation completes
  reconnect: () => void;     // Manual reconnect function
}
```

### Frontend Component

**<OpenMCTerminal />**

Terminal component to display OpenMC output.

**Props:**
```typescript
{
  runId: string;                    // Required: Run ID to stream
  autoScroll?: boolean;             // Auto-scroll to bottom (default: true)
  onComplete?: () => void;          // Callback when simulation completes
  onError?: (error: string) => void; // Callback on error
}
```

## Example: Full Integration

```typescript
// In your main page component
const [terminalRunId, setTerminalRunId] = useState<string | null>(null);

// When submitting a new run
const handleRunSimulation = async () => {
  const response = await fetch('/api/run', {
    method: 'POST',
    body: formData
  });
  
  const data = await response.json();
  
  // Show terminal for this run
  setTerminalRunId(data.run_id);
  
  // Optional: Start execution
  await fetch(`/runs/${data.run_id}/execute`, { method: 'POST' });
};

// In your render
return (
  <div className="execution-logs">
    {terminalRunId ? (
      <OpenMCTerminal 
        runId={terminalRunId}
        onComplete={() => {
          console.log('Simulation complete!');
          setTerminalRunId(null); // Clear terminal
        }}
      />
    ) : (
      <MissionControlLogs logs={systemLogs} />
    )}
  </div>
);
```

## Testing

### 1. Backend Test (Direct)

```bash
# Test the streaming runner directly
cd /path/to/project
python aonp/runner/streaming_runner.py runs/run_abc123
```

### 2. Backend Test (API)

```bash
# Start the API server
cd aonp
uvicorn api.main:app --reload

# In another terminal, test the stream
curl -N http://localhost:8000/runs/run_abc123/stream
```

### 3. Frontend Test

```bash
# Start frontend dev server
cd frontend
npm run dev

# Navigate to http://localhost:3000
# Trigger a simulation and watch the terminal!
```

## Configuration

### Environment Variables

```bash
# Backend API URL (frontend)
NEXT_PUBLIC_API_URL=http://localhost:8000

# CORS Origins (backend)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Adjusting Stream Buffer

If you experience buffering issues, ensure nginx/proxy settings don't buffer SSE:

```nginx
location /runs/ {
    proxy_pass http://backend;
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection '';
    chunked_transfer_encoding off;
}
```

## Troubleshooting

### Stream Not Connecting

1. Check CORS settings
2. Verify run_id exists in `runs/` directory
3. Check browser console for errors
4. Test with curl first

### No Output Appearing

1. Check OpenMC is installed: `python -c "import openmc; print(openmc.__version__)"`
2. Verify run directory has `inputs/` folder with XML files
3. Check backend logs for errors

### Buffering/Delayed Output

1. Disable any proxy buffering
2. Use `subprocess.Popen` with `bufsize=1`
3. Ensure SSE headers are set correctly

## Performance

- **Latency**: < 100ms per line
- **Memory**: Lines stored in React state (consider pagination for very long runs)
- **Connection**: Auto-reconnects on disconnect
- **Concurrent**: Multiple terminals can stream different runs simultaneously

## Future Enhancements

- [ ] Search/filter terminal output
- [ ] Export to different formats (JSON, CSV)
- [ ] Pause/resume simulation
- [ ] Multiple terminal tabs for parallel runs
- [ ] Terminal history persistence
- [ ] Replay completed runs


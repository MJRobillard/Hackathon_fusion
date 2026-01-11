# OpenMC Terminal Demo

Quick guide to see the OpenMC streaming terminal in action.

## Setup

1. **Start the backend:**
```bash
cd /path/to/Hackathon_fusion
python Playground/backend/start_server.py
```

2. **Start the frontend:**
```bash
cd frontend
npm run dev
```

3. **Navigate to:** http://localhost:3000

## Triggering a Simulation Stream

### Method 1: Using Existing Run

If you have a completed run in the `runs/` directory:

```typescript
// In the browser console or add a button in the UI:
setTerminalRunId('run_abc123'); // Replace with actual run ID
```

### Method 2: Submit New Run via API

```bash
# Submit a new run
curl -X POST http://localhost:8000/run \
  -F "file=@aonp/examples/simple_pincell.yaml"

# Response will include run_id
# {
#   "run_id": "run_e3753341e8d6",
#   "spec_hash": "...",
#   "status": "created",
#   "run_directory": "..."
# }

# Then in your frontend, set:
# setTerminalRunId('run_e3753341e8d6')
```

### Method 3: Add Button to UI

Add this to your `page.tsx`:

```typescript
const handleTestTerminal = () => {
  // Use an existing run ID from your runs/ directory
  setTerminalRunId('run_7b5506d0364f'); // Example
};

// In your render:
<button 
  onClick={handleTestTerminal}
  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded"
>
  Test Terminal Stream
</button>
```

## What to Expect

When the terminal connects, you'll see:

```
Run ID: run_abc123
Spec Hash: a1b2c3d4...

============================================================
Starting OpenMC simulation...
============================================================

OpenMC version: 0.14.0

                 ###############################################
                 #                   OpenMC                    #
                 ###############################################

 ====================>     K EIGENVALUE SIMULATION     <====================

 Bat./Gen.      k            Average k
 =========   ========   ====================
       1/1    1.38979
INFO:     127.0.0.1:48528 - "GET /api/v1/query/q_de30daba HTTP/1.1" 200 OK
       2/1    1.43209
       3/1    1.38782
       ...
      37/1    1.41159    1.41718 +/- 0.00319

✓ Simulation completed in 7.23 seconds

Moved output files: statepoint.100.h5, summary.h5, tallies.out

[OK] Results written to: runs/run_abc123/outputs
```

## Terminal Features to Try

1. **Auto-scroll**: Watch it scroll automatically as new lines come in

2. **Pause scrolling**: Scroll up manually - notice the "Resume" button appears

3. **Copy output**: Click "Copy" to copy all terminal output to clipboard

4. **Download log**: Click "Download" to save the log as a file

5. **Connection status**: Watch the status indicator (green = streaming, blue = complete)

6. **Color coding**: Notice different colors for errors (red), warnings (yellow), success (green)

## Direct API Test

Test the streaming endpoint directly:

```bash
# Stream in terminal with curl
curl -N http://localhost:8000/runs/run_7b5506d0364f/stream

# Or with HTTPie
http --stream GET http://localhost:8000/runs/run_7b5506d0364f/stream
```

## JavaScript Console Test

Open browser console and try:

```javascript
// Create EventSource connection
const es = new EventSource('http://localhost:8000/runs/run_7b5506d0364f/stream');

// Listen for messages
es.onmessage = (event) => {
  console.log('Received:', event.data);
};

// Handle errors
es.onerror = (error) => {
  console.error('Stream error:', error);
};

// Close when done
// es.close();
```

## Example: Full Workflow

```bash
# 1. Submit a new study
curl -X POST http://localhost:8000/run \
  -F "file=@aonp/examples/simple_pincell.yaml" \
  > response.json

# 2. Extract run_id
RUN_ID=$(jq -r '.run_id' response.json)
echo "Run ID: $RUN_ID"

# 3. Stream the execution (opens SSE connection)
curl -N "http://localhost:8000/runs/$RUN_ID/stream"

# This will stream the OpenMC output in real-time!
```

## Troubleshooting

### "Run not found" error
- Check that the run ID exists in the `runs/` directory
- Use `ls runs/` to see available runs

### No output appearing
- Verify OpenMC is installed: `python -c "import openmc"`
- Check that the run has `inputs/` directory with XML files
- Look at backend logs for errors

### Connection closes immediately
- Check CORS settings in backend
- Verify API URL in frontend: `NEXT_PUBLIC_API_URL`
- Check browser Network tab for errors

## Screenshots

The terminal will appear in the **Execution Logs** section (center-right panel) when `terminalRunId` is set.

**Normal Logs View:**
```
┌─────────────────┬────────────────────┐
│  Agent Thinking │  Execution Logs    │
│                 │  [System logs]     │
└─────────────────┴────────────────────┘
```

**Terminal View:**
```
┌─────────────────┬────────────────────┐
│  Agent Thinking │  OpenMC Terminal   │
│                 │  [Streaming...]    │
│                 │  1/1    1.38979    │
│                 │  2/1    1.43209    │
└─────────────────┴────────────────────┘
```


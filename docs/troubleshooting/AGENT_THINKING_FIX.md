# Agent Thinking Display Fix

## Issue
Agent reasoning/thinking events not appearing in the frontend.

## Changes Made

### 1. Fixed Async Event Publishing ✅
**File**: `Playground/backend/api/main_v2.py`

**Problem**: `_fire_and_forget` was using `call_soon_threadsafe` incorrectly, which could fail silently when agents run in thread executors.

**Fix**: Changed to use `asyncio.run_coroutine_threadsafe()` which properly schedules async coroutines from threads.

```python
# Before (broken):
MAIN_LOOP.call_soon_threadsafe(asyncio.create_task, self._publish(payload))

# After (fixed):
asyncio.run_coroutine_threadsafe(self._publish(payload), MAIN_LOOP)
```

### 2. Added Error Handling ✅
**File**: `Playground/backend/multi_agent_system.py`

Added try/except blocks around callback invocations to catch and log errors instead of failing silently.

### 3. Enhanced Debugging ✅
Added warning logs when `MAIN_LOOP` is not set, and error logging when event publishing fails.

## How to Verify It's Working

### Backend Check
1. **Check logs** when running a query - you should see:
   ```
   [ROUTER] Analyzing query: ...
   ```
   If you see `[WARN]` or `[ERROR]` messages about callbacks, that indicates the issue.

2. **Test the SSE endpoint directly**:
   ```bash
   curl -N http://localhost:8000/api/v1/query/{query_id}/stream
   ```
   You should see events like:
   ```
   event: agent_thinking
   data: {"type":"agent_thinking","agent":"Router","content":"Analyzing query: ..."}
   ```

### Frontend Check
1. **Open browser DevTools** → Network tab
2. **Filter by "stream"** or "EventSource"
3. **Submit a query**
4. **Check the stream connection** - should see:
   - Status 200
   - Type: eventsource
   - Response should show SSE events coming through

5. **Check Console** for any errors related to EventSource

## Common Issues

### Issue 1: Events Not Appearing
**Symptoms**: Backend logs show callback being called, but frontend shows nothing.

**Possible Causes**:
- SSE connection not established
- Wrong query_id in frontend
- CORS issues
- Event format mismatch

**Debug Steps**:
1. Check browser Network tab - is the stream endpoint connected?
2. Check browser Console - any errors?
3. Check backend logs - are events being published?
4. Test SSE endpoint directly with curl

### Issue 2: MAIN_LOOP Not Set
**Symptoms**: Backend logs show `[WARN] MAIN_LOOP not set, dropping event`

**Fix**: Ensure FastAPI startup event runs:
```python
@app.on_event("startup")
async def _startup():
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_running_loop()
```

### Issue 3: Callback Not Passed
**Symptoms**: No callback errors, but no events either.

**Check**: Verify callback is passed in `query_graph.py`:
```python
router = RouterAgent(use_llm=ctx.use_llm, thinking_callback=ctx.thinking_callback)
```

### Issue 4: Frontend Not Listening
**Symptoms**: Backend emits events, but frontend doesn't display them.

**Check**: Verify frontend is listening for the right event types:
- `agent_thinking`
- `agent_planning`
- `agent_observation`
- `agent_decision`

## Testing

Run a simple query and check:

1. **Backend logs** should show:
   ```
   [ROUTER] Analyzing query: ...
   ```

2. **SSE stream** (curl or browser) should show:
   ```
   event: agent_thinking
   data: {"type":"agent_thinking","agent":"Router","content":"Analyzing query: ...","metadata":{...},"timestamp":"..."}
   
   event: agent_planning
   data: {"type":"agent_planning","agent":"Router","content":"Using LLM-based routing",...}
   ```

3. **Frontend** should display:
   - Agent Reasoning panel shows thoughts
   - Different thought types (thinking, planning, decision, observation)
   - Metadata expandable details

## Next Steps if Still Not Working

1. **Enable verbose logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Add temporary print statements** in `AgentThinkingCallback` methods:
   ```python
   def thinking(self, agent: str, content: str, metadata=None):
       print(f"[DEBUG] AgentThinkingCallback.thinking called: agent={agent}")
       self._fire_and_forget({...})
   ```

3. **Check event bus**:
   ```python
   # In main_v2.py, add logging:
   async def publish(self, query_id: str, event: Dict[str, Any]):
       print(f"[DEBUG] EventBus.publish: query_id={query_id}, type={event.get('type')}")
       # ... rest of code
   ```

4. **Verify SSE endpoint** is being called with correct query_id

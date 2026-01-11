# Agent Thinking Display - Implementation Guide

## ✅ What's Been Implemented (Frontend)

### 1. **Agent Thinking Panel** (`components/AgentThinkingPanel.tsx`)
A beautiful panel that displays the agent's thought process in real-time with different types of thoughts:

- 🤔 **THINKING** - Agent reasoning and analysis (blue)
- ⚡ **DECISION** - Agent decisions and choices (purple)
- 🔧 **TOOL CALL** - Tool/function calls (green)
- 👁️ **OBSERVATION** - Results and observations (amber)
- 📋 **PLANNING** - Planning next steps (cyan)

### 2. **Enhanced Event Stream Hook** (`hooks/useEventStream.ts`)
- Added `agentThoughts` state to capture thinking events
- New event listeners for:
  - `agent_thinking`
  - `agent_decision`
  - `agent_planning`
  - Enhanced `tool_call` and `tool_result`

### 3. **Mission Control UI Updates** (`app/page.tsx`)
- Split center panel into two columns:
  - **Left**: Agent Reasoning Panel (shows thought process)
  - **Right**: Execution Logs (shows system logs)
- Added Database Panel (MongoDB viewer)
- Added Health Panel (System health checks)
- Top bar buttons to open Database and Health panels

### 4. **Database Panel** (`components/DatabasePanel.tsx`)
- Browse MongoDB collections
- View documents with pagination
- Inspect individual document details
- Full JSON view

### 5. **Health Panel** (`components/HealthPanel.tsx`)
- Real-time system health monitoring
- MongoDB and OpenMC status
- API endpoint testing
- Run health checks on demand

### 6. **Enhanced API Client** (`lib/api.ts`)
Added MongoDB database operations:
- `getCollections()` - List all collections
- `getDocuments(collection, limit, skip)` - Get documents
- `getDocument(collection, id)` - Get single document
- `getCollectionCount(collection)` - Get count

---

## ⚠️ What's Needed (Backend)

### Backend Changes Required

The frontend is **ready to display agent thoughts**, but the backend needs to emit the new events.

See: `Playground/backend/api/agent_thinking_events.py` for complete implementation guide.

### Quick Start:

#### 1. Add Callback System to Agents

```python
from agent_thinking_events import AgentThinkingCallback

# In RouterAgent
class RouterAgent:
    def __init__(self, use_llm=False, thinking_callback=None):
        self.thinking_callback = thinking_callback
    
    def route(self, query: str):
        if self.thinking_callback:
            self.thinking_callback.thinking(
                "Router",
                f"Analyzing query: '{query}'"
            )
        
        # ... routing logic ...
        
        if self.thinking_callback:
            self.thinking_callback.decision(
                "Router",
                f"Decided to route to {agent} agent",
                {"intent": intent, "confidence": 0.95}
            )
```

#### 2. Update execute_multi_agent_query in main_v2.py

```python
async def execute_multi_agent_query(query_id: str, query: str, mongodb, use_llm: bool = True):
    try:
        # Create thinking callback
        from agent_thinking_events import AgentThinkingCallback
        thinking_callback = AgentThinkingCallback(event_bus, query_id)
        
        # Pass to orchestrator and all agents
        orchestrator = MultiAgentOrchestrator(thinking_callback=thinking_callback)
        orchestrator.router = RouterAgent(use_llm=use_llm, thinking_callback=thinking_callback)
        
        # ... rest of code ...
```

#### 3. Add MongoDB API Endpoints (Optional)

For the Database Panel to work, add these endpoints to `main_v2.py`:

```python
@app.get("/api/v1/db/collections")
async def get_collections(mongodb=Depends(get_database)):
    collections = await mongodb.list_collection_names()
    return collections

@app.get("/api/v1/db/{collection}")
async def get_documents(collection: str, limit: int = 50, skip: int = 0, mongodb=Depends(get_database)):
    cursor = mongodb[collection].find().skip(skip).limit(limit)
    documents = await cursor.to_list(length=limit)
    # Convert ObjectId to string
    for doc in documents:
        doc['_id'] = str(doc['_id'])
    return documents

@app.get("/api/v1/db/{collection}/count")
async def get_collection_count(collection: str, mongodb=Depends(get_database)):
    count = await mongodb[collection].count_documents({})
    return {"count": count}

@app.get("/api/v1/db/{collection}/{doc_id}")
async def get_document(collection: str, doc_id: str, mongodb=Depends(get_database)):
    from bson import ObjectId
    doc = await mongodb[collection].find_one({"_id": ObjectId(doc_id)})
    if doc:
        doc['_id'] = str(doc['_id'])
        return doc
    raise HTTPException(status_code=404, detail="Document not found")
```

---

## 🎯 Example Agent Thought Flow

When a user submits: **"Simulate PWR at 4.5% enrichment"**

The frontend will display:

```
🤔 THINKING - Router                        14:30:05
   Analyzing query: 'Simulate PWR at 4.5% enrichment'

📋 PLANNING - Router                        14:30:06
   Using LLM for intelligent routing

⚡ DECISION - Router                        14:30:07
   Decided to route to Studies Agent
   [View Details: intent, confidence, reasoning]

🤔 THINKING - Studies Agent                 14:30:08
   Extracting simulation parameters from query

👁️ OBSERVATION - Studies Agent             14:30:09
   Extracted parameters: enrichment=4.5%, geometry=PWR

📋 PLANNING - Studies Agent                 14:30:10
   Validating simulation parameters

⚡ DECISION - Studies Agent                 14:30:11
   Parameters validated. Proceeding with simulation

🔧 TOOL CALL - Studies Agent                14:30:12
   Calling run_openmc_simulation
   [View Details: parameters]

👁️ OBSERVATION - Studies Agent             14:35:44
   Simulation complete. k-eff: 1.00245 ± 0.00012
```

---

## 🚀 Testing Without Backend Changes

The UI components work with dummy data. To test:

1. Start the frontend: `cd frontend && npm run dev`
2. Open http://localhost:3000
3. The Agent Reasoning panel will show "Waiting for agent thoughts..."
4. Once backend emits the new events, they'll appear automatically

---

## 📊 Features Summary

| Feature | Status | Description |
|---------|--------|-------------|
| Command Palette | ✅ Working | Submit natural language queries |
| Agent Orchestration | ✅ Working | Shows agent status and workflow |
| Execution Logs | ✅ Working | Terminal-style system logs |
| **Agent Reasoning** | ✅ **Frontend Ready** | Shows agent thought process (needs backend events) |
| Telemetry Sidebar | ✅ Working | Live metrics and interlocks |
| Runs Sidebar | ✅ Working | List of simulation runs |
| Database Panel | ✅ **Frontend Ready** | MongoDB browser (needs backend API) |
| Health Panel | ✅ Working | System health monitoring |
| Status Footer | ✅ Working | System status bar |

---

## 🎨 UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Top Bar: [MC Logo] | Project | [Health] [DB] [▶ ⏹ ⟲] [CMD] │
├─────────────┬──────────────────────────────┬────────────────┤
│             │ Agent Orchestration          │                │
│   RUNS      ├──────────────┬───────────────┤   TELEMETRY    │
│  • OM-945   │ Agent        │ Execution     │                │
│    Running  │ Reasoning    │ Logs          │   k-eff        │
│  • OM-944   │ (NEW!)       │               │   1.00245      │
│    Success  │              │               │                │
│             │ 🤔 Thinking  │ [INFO] ...    │   Progress     │
│             │ ⚡ Decision  │ [PROCESS] ... │   ████░ 82%    │
│             │ 🔧 Tool Call │               │                │
│             │              │               │   Interlocks   │
└─────────────┴──────────────┴───────────────┴────────────────┘
│ Footer: ● SYSTEM READY | OpenMC 0.14.0 | Stats             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Next Steps

1. ✅ Frontend is complete and ready
2. ⚠️ Add agent thinking callbacks to backend (see `agent_thinking_events.py`)
3. ⚠️ Add MongoDB API endpoints for Database Panel
4. 🎉 Test full integration!

---

## 🔗 Key Files

- `components/AgentThinkingPanel.tsx` - Displays agent thoughts
- `components/DatabasePanel.tsx` - MongoDB browser
- `components/HealthPanel.tsx` - System health
- `hooks/useEventStream.ts` - Captures events
- `app/page.tsx` - Main mission control layout
- `Playground/backend/api/agent_thinking_events.py` - Backend integration guide


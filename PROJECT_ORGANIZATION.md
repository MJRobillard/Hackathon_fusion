# AONP Project Organization

**Two codebases that need to work together**

---

## 📁 Folder Structure

```
hackathon/
├── Playground/                    ← Team 2: Agent & Frontend
│   ├── backend/                   # Python agents & API
│   │   ├── agent_tools.py        # MongoDB tools (simplified specs)
│   │   ├── aonp_agents.py        # LangGraph multi-agent system
│   │   ├── openmc_adapter.py     # 🔧 NEW: Translator layer
│   │   └── api/
│   │       └── main.py           # FastAPI server (port 8000)
│   ├── frontend/                  # Next.js UI
│   │   └── app/                  # React components
│   └── docs/                      # Team 2 documentation
│
├── aonp/                          ← Team 1: OpenMC Integration
│   ├── schemas/                   # Structured Pydantic models
│   │   ├── study.py              # Full OpenMC StudySpec
│   │   ├── manifest.py           # Run provenance
│   │   └── manifest.py
│   ├── core/                      # Core OpenMC logic
│   │   ├── bundler.py            # Create run bundles
│   │   ├── extractor.py          # Parse statepoint.h5
│   │   └── hasher.py
│   ├── runner/                    # Execution engine
│   │   └── entrypoint.py         # OpenMC subprocess runner
│   ├── db/                        # Database integration
│   │   └── mongo.py              # MongoDB with worker queues
│   └── api/                       # Optional: HTTP API
│       ├── main.py               # FastAPI (if exposing as service)
│       └── main_with_mongo.py
│
├── runs/                          # Shared: Simulation outputs
│   ├── run_abc123/
│   │   ├── study_spec.json
│   │   ├── run_manifest.json
│   │   ├── inputs/
│   │   └── outputs/
│   │       └── statepoint.h5
│   └── ...
│
├── tests/                         # Team 1 tests
├── scripts/                       # Utility scripts
├── verification_studies/          # Sample studies
│
├── INTEGRATION_BRIDGE.md          # 🔧 Integration guide
├── OPENMC_API_SPEC.md            # (deprecated)
└── PROJECT_ORGANIZATION.md        # This file
```

---

## 🔗 Integration Points

### 1. **Spec Translation** (Primary Integration Point)

**Location**: `Playground/backend/openmc_adapter.py`

**Purpose**: Translate between formats

```python
# Input: Simplified spec from agents
{
  "geometry": "PWR pin cell",
  "materials": ["UO2", "Zircaloy", "Water"],
  "enrichment_pct": 4.5
}

# Output: Structured OpenMC spec
{
  "materials": {
    "fuel": {
      "density": 10.4,
      "nuclides": [{"name": "U235", "fraction": 0.045}]
    }
  },
  "geometry": {"type": "script", "script": "examples/pincell_geometry.py"}
}
```

### 2. **Execution Flow**

```
User Request
    ↓
Playground/backend/api/main.py (FastAPI)
    ↓
Playground/backend/aonp_agents.py (LangGraph)
    ↓
Playground/backend/agent_tools.py (submit_study)
    ↓
🔧 Playground/backend/openmc_adapter.py (NEW)
    ↓ translate_simple_to_openmc()
    ↓
aonp/core/bundler.py (create_run_bundle)
    ↓
aonp/runner/entrypoint.py (run_simulation)
    ↓
aonp/core/extractor.py (extract results)
    ↓
MongoDB (shared database)
```

### 3. **Shared MongoDB Collections**

| Collection | Writer | Reader | Schema Owner |
|------------|--------|--------|--------------|
| `studies` | Both | Both | Team 1 (use Team 1's schema) |
| `runs` | Both | Both | Team 1 (use Team 1's schema) |
| `summaries` | Both | Both | Shared (compatible) |
| `requests` | Team 2 | Team 2 | Team 2 only |
| `agent_traces` | Team 2 | Team 2 | Team 2 only |

**Decision**: Team 2 should adapt to Team 1's schema for `studies`/`runs`

---

## 🚀 Setup Instructions

### For Team 2 (Playground)

```bash
cd Playground

# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Create .env in Playground/ root
cat > .env <<EOF
MONGO_URI=mongodb+srv://...
FIREWORKS=your_fireworks_key
VOYAGE=your_voyage_key
EOF

# 3. Create adapter (NEW STEP)
# See INTEGRATION_BRIDGE.md for openmc_adapter.py implementation

# 4. Update agent_tools.py to use adapter
# Replace: mock_openmc_execution()
# With: execute_real_openmc() from adapter

# 5. Start API
cd api
python main.py
# Running on http://localhost:8000
```

### For Team 1 (OpenMC)

```bash
# No changes needed!
# Playground will import your modules directly

# Optional: Expose as HTTP service
cd aonp/api
python main.py --port 8001
```

### Testing Integration

```bash
# Terminal 1: Start Playground backend
cd Playground/backend/api
python main.py

# Terminal 2: Submit test request
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Simulate PWR pin cell with 4.5% enriched UO2 at 600K"
  }'

# Should now execute real OpenMC instead of mock!
```

---

## 📊 Data Flow Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                    INTEGRATED SYSTEM                           │
└────────────────────────────────────────────────────────────────┘

USER INPUT (Natural Language)
    │
    │ "Simulate PWR pin with 4.5% enriched fuel"
    │
    ▼
┌───────────────────────────────┐
│   Playground/frontend/        │
│   (Next.js)                   │
└──────────────┬────────────────┘
               │ HTTP POST
               │
               ▼
┌───────────────────────────────┐
│   Playground/backend/api/     │
│   FastAPI (port 8000)         │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│   Playground/backend/         │
│   aonp_agents.py              │
│   (LangGraph)                 │
│   - Intent: single_study      │
│   - Plan: PWR pin cell        │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│   Playground/backend/         │
│   agent_tools.py              │
│   submit_study({...})         │
└──────────────┬────────────────┘
               │
               │ 🔧 INTEGRATION POINT
               ▼
┌───────────────────────────────┐
│   Playground/backend/         │
│   openmc_adapter.py (NEW!)    │
│   translate_simple_to_openmc()│
│                               │
│   Input: Simplified spec      │
│   Output: Full OpenMC spec    │
└──────────────┬────────────────┘
               │
               │ Import: from aonp.core.bundler import ...
               │
               ▼
┌───────────────────────────────┐
│   aonp/core/bundler.py        │
│   create_run_bundle()         │
│   - Validates StudySpec       │
│   - Creates runs/run_xyz/     │
│   - Generates OpenMC XMLs     │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│   aonp/runner/entrypoint.py   │
│   run_simulation()            │
│   - Executes OpenMC           │
│   - Writes statepoint.h5      │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│   aonp/core/extractor.py      │
│   extract()                   │
│   - Parses statepoint.h5      │
│   - Extracts keff, std        │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│   MongoDB Atlas               │
│   - studies                   │
│   - runs                      │
│   - summaries                 │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│   Playground/backend/         │
│   aonp_agents.py              │
│   (Results analyzer)          │
│   - Interpret keff            │
│   - Generate suggestions      │
└──────────────┬────────────────┘
               │
               ▼
         FRONTEND DISPLAY
```

---

## 🎯 Action Items

### Immediate (To integrate systems):

- [ ] **Create `Playground/backend/openmc_adapter.py`** (see `INTEGRATION_BRIDGE.md`)
- [ ] **Update `Playground/backend/agent_tools.py`** to import adapter
- [ ] **Test translation** with sample specs
- [ ] **Run end-to-end test** with real OpenMC

### Short-term (To improve):

- [ ] Create geometry template library
- [ ] Create material definition library
- [ ] Add error handling in adapter
- [ ] Update MongoDB schemas to be compatible
- [ ] Add extractor integration

### Long-term (Nice to have):

- [ ] Expose OpenMC as HTTP service (optional)
- [ ] Add Redis queue for async execution
- [ ] Deploy both services
- [ ] Add authentication/authorization

---

## 📝 Notes

**Why two separate projects?**
- Team 2 built agents/frontend independently
- Team 1 built OpenMC integration independently
- Now we need to connect them

**Why adapter layer?**
- Simplifies agent LLM prompts (natural language works better)
- Keeps OpenMC team's strict validation
- Allows independent development

**Alternative: Unified schema?**
- Could force agents to use full OpenMC schema
- But: LLMs struggle with deeply nested structures
- Current approach is more practical

---

**Last Updated**: 2026-01-10  
**Status**: Active integration phase


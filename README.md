# AONP - Agent-Orchestrated Neutronics Platform

**Version 0.1.0**

An intelligent agentic orchestration system that automates nuclear simulation workflows, enabling researchers to focus on high-level physics rather than repetitive computational tasks.

---

## 🎯 Problem Statement

Nuclear researchers with high skill levels spend significant time on monotonous, repetitive simulation tasks that don't leverage their expertise. These researchers must:

- Manually create and validate simulation configurations
- Write and debug XML input files for Monte Carlo simulations
- Monitor long-running simulations and manage execution
- Extract and process results from complex HDF5 outputs
- Track provenance and ensure reproducibility across studies
- Coordinate parameter sweeps and comparative analyses

These routine tasks consume valuable time that could be better spent on:
- Designing novel reactor concepts
- Analyzing physics phenomena
- Interpreting results and advancing scientific understanding
- Publishing research findings

**The Problem**: High-skilled researchers are trapped in low-value computational workflows instead of advancing nuclear science.

---

## 💡 Solution: Agentic Orchestration

AONP (Agent-Orchestrated Neutronics Platform) provides an intelligent multi-agent system that automates the entire simulation workflow. Instead of manually creating configurations, managing runs, and processing results, researchers interact with the system through natural language queries or structured APIs.

### How It Works

The system uses a **LangGraph-based multi-agent orchestration** architecture:

1. **Router Agent**: Classifies user intent (simulation, parameter sweep, query, analysis)
2. **Specialist Agents**: Handle specific tasks with domain expertise
   - **Studies Agent**: Single simulation execution
   - **Sweep Agent**: Parameter sweep generation and management
   - **Query Agent**: Historical data search and retrieval
   - **Analysis Agent**: Result comparison and insights
3. **Tool Layer**: Interfaces with OpenMC simulation engine and MongoDB database
4. **Frontend**: Real-time visualization and interaction via Next.js web interface

### Key Capabilities

✅ **Natural Language Interface**: Submit queries like "Simulate a PWR pin cell with 4.5% enriched UO2 at 600K"  
✅ **Automated Configuration**: Agents generate validated OpenMC XML inputs from high-level specifications  
✅ **Provenance Tracking**: Cryptographic hashing ensures complete reproducibility  
✅ **Real-Time Monitoring**: Server-Sent Events (SSE) provide live simulation progress  
✅ **Intelligent Result Extraction**: Automatic processing of HDF5 outputs to structured formats  
✅ **Parameter Sweep Orchestration**: Automated generation and execution of multi-run studies  
✅ **Historical Query System**: Search and compare past simulation results  
✅ **RAG-Enhanced Assistance**: Context-aware help with nuclear engineering knowledge  

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    AONP SYSTEM ARCHITECTURE                  │
└─────────────────────────────────────────────────────────────┘

USER INTERFACE                    ORCHESTRATION LAYER          PHYSICS ENGINE
───────────────                   ───────────────────          ─────────────

Natural Language Query
        │
        ▼
┌───────────────┐
│  Next.js      │◄──── Server-Sent Events (SSE)
│  Frontend     │
└───────┬───────┘
        │ HTTP/REST
        ▼
┌───────────────┐
│   FastAPI     │
│   Backend     │
└───────┬───────┘
        │
        ▼
┌──────────────────────────────────┐
│   LangGraph Multi-Agent System   │
│                                  │
│  Router → Specialist Agents      │
│  (Studies | Sweep | Query |      │
│   Analysis)                      │
└───────┬──────────────────────────┘
        │ Tool Calls
        ▼
┌──────────────────────────────────┐      ┌─────────────────┐
│   Agent Tools Layer              │      │   MongoDB       │
│   - submit_study                 │─────▶│   Database      │
│   - query_results                │      │   - studies     │
│   - generate_sweep               │      │   - runs        │
│   - compare_runs                 │      │   - summaries   │
│   - validate_physics             │      │   - events      │
└───────┬──────────────────────────┘      └─────────────────┘
        │
        ▼
┌──────────────────────────────────┐
│   OpenMC Integration Layer       │
│                                  │
│  1. YAML → StudySpec (Pydantic)  │
│  2. StudySpec → Canonical Hash   │
│  3. Hash → Run Bundle            │
│  4. Bundle → XML Generation      │
│  5. XML → OpenMC Execution       │
│  6. HDF5 → Result Extraction     │
│  7. Results → MongoDB Storage    │
└───────┬──────────────────────────┘
        │
        ▼
┌───────────────┐
│    OpenMC     │
│  (Monte Carlo │
│   Neutron     │
│  Transport)   │
└───────────────┘
```

---

## 🔄 Complete Workflow Process

### OpenMC Integration Process

AONP integrates with OpenMC (MIT's Monte Carlo neutron transport code) through a comprehensive pipeline:

#### Step 1: User Input
- **Natural Language Query**: "Run a simulation of a PWR pin cell with 4.5% U-235 enrichment"
- **Structured YAML**: Submit a validated study specification
- **API Call**: Direct REST API submission

#### Step 2: Agent Orchestration
1. **Router Agent** classifies the query intent
2. **Specialist Agent** (e.g., Studies Agent) processes the request
3. Agent calls tools to:
   - Validate the physics specification
   - Check for duplicate studies (via hash lookup)
   - Generate or retrieve study configuration

#### Step 3: Study Specification
The system uses Pydantic schemas to create a validated `StudySpec` object:

```yaml
name: "pwr_pincell_4.5pct"
materials:
  fuel:
    density: 10.4  # g/cm³
    nuclides:
      - {nuclide: "U235", fraction: 0.045}
      - {nuclide: "U238", fraction: 0.955}
  cladding:
    density: 6.56
    nuclides:
      - {nuclide: "Zr", fraction: 1.0}
geometry:
  script: "pincell_geometry.py"
  parameters:
    pitch: 1.26  # cm
    fuel_radius: 0.4096  # cm
settings:
  particles: 10000
  batches: 50
  inactive: 10
nuclear_data:
  library: "endfb-vii.1"
```

#### Step 4: Canonical Hashing
- StudySpec is converted to canonical JSON (sorted keys)
- SHA256 hash is computed for reproducibility
- Hash enables duplicate detection and result lookup

#### Step 5: Run Bundle Creation
Self-contained execution directory structure:

```
runs/run_{hash}/
├── study_spec.json          # Canonical specification
├── run_manifest.json        # Provenance metadata
├── nuclear_data.ref.json    # Data library references
├── inputs/
│   ├── materials.xml        # Generated OpenMC XML
│   ├── geometry.xml         # Generated from Python script
│   ├── settings.xml         # Monte Carlo settings
│   └── geometry_script.py   # Copied for reproducibility
└── outputs/
    ├── statepoint.50.h5     # OpenMC results
    ├── summary.h5           # Summary data
    └── openmc_stdout.log    # Execution log
```

#### Step 6: XML Generation
- **Materials XML**: Generated from material specifications
- **Geometry XML**: Executed from Python geometry scripts
- **Settings XML**: Monte Carlo parameters (particles, batches, etc.)

#### Step 7: OpenMC Execution
- Environment configured (cross-section paths, threading)
- OpenMC solver runs Monte Carlo neutron transport
- Results written to HDF5 format (statepoint files)

#### Step 8: Result Extraction
- HDF5 files processed to extract:
  - k-effective (multiplication factor)
  - Uncertainties and confidence intervals
  - Batch statistics
  - Tally results (if configured)
- Results stored in Parquet format for efficient querying

#### Step 9: Database Storage
Results stored in MongoDB:
- **studies**: Deduplicated study specifications
- **runs**: Execution state and metadata
- **summaries**: Lightweight result summaries
- **events**: Audit log of all operations

#### Step 10: User Notification
- Real-time updates via SSE streams
- Results available through REST API
- Frontend visualization of results

---

## 📦 Project Structure

```
Hackathon_fusion/
├── aonp/                          # Core AONP package
│   ├── schemas/                   # Pydantic data models
│   │   ├── study.py               # StudySpec with deterministic hashing
│   │   └── manifest.py            # RunManifest (provenance record)
│   ├── core/                      # Core utilities
│   │   ├── bundler.py             # Creates canonical run bundles
│   │   └── extractor.py           # Post-processing (H5 → Parquet)
│   ├── db/                        # MongoDB persistence layer
│   │   ├── mongo.py               # Database operations
│   │   └── README.md              # Database documentation
│   ├── runner/                    # Execution logic
│   │   ├── entrypoint.py          # OpenMC simulation runner
│   │   └── Dockerfile             # Container environment
│   ├── api/                       # REST API
│   │   └── main.py                # FastAPI application
│   └── examples/                  # Example studies
│       ├── simple_pincell.yaml
│       └── pincell_geometry.py
│
├── Playground/                    # Agent orchestration system
│   └── backend/
│       ├── graphs/                # LangGraph state machines
│       │   └── query_graph.py     # Main query orchestration
│       ├── multi_agent_system.py  # Router + specialist agents
│       ├── agent_tools.py         # MongoDB simulation tools
│       ├── openmc_adapter.py      # OpenMC integration adapter
│       └── api/
│           ├── main.py            # FastAPI server
│           ├── main_v2.py         # Enhanced API with agents
│           └── rag_endpoints.py   # RAG-enhanced endpoints
│
├── frontend/                      # Next.js web interface
│   ├── app/                       # Next.js App Router
│   │   ├── page.tsx               # Main application page
│   │   └── layout.tsx             # App layout
│   ├── components/                # React components
│   │   ├── RAGCopilotPanel.tsx    # Main chat interface
│   │   └── RAGAgentCard.tsx       # Agent status cards
│   ├── hooks/                     # React hooks
│   │   ├── useEventStream.ts      # SSE event streaming
│   │   └── useQueryHistory.ts     # Query history management
│   └── lib/                       # Utilities
│       ├── api.ts                 # API client
│       └── types.ts               # TypeScript types
│
├── verification_studies/          # Validation test cases
│   ├── 01_toy_geometry.py
│   ├── 02_single_torus.py
│   └── ...
│
├── openmc_design.md               # OpenMC integration design doc
├── OPENMC_API_SPEC.md             # API specification
├── requirements.txt               # Python dependencies
├── pyproject.toml                 # Project metadata
└── README.md                      # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** (3.10+ recommended)
- **Node.js 18+** (for frontend)
- **MongoDB** (Atlas cloud or local instance)
- **Linux/macOS** (OpenMC requires Linux/macOS; Windows users should use WSL2)

### Installation

#### 1. Backend Setup

```bash
# Clone repository
git clone <repository-url>
cd Hackathon_fusion

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install OpenMC (Linux/macOS only)
# Option 1: Conda (recommended)
conda install -c conda-forge openmc

# Option 2: pip (may require system dependencies)
pip install openmc

# Configure environment
cp Playground/backend/env_example.txt .env
# Edit .env with your MongoDB URI and API keys
```

#### 2. MongoDB Setup

```bash
# Option 1: MongoDB Atlas (Cloud - Free tier available)
# 1. Sign up at https://www.mongodb.com/cloud/atlas/register
# 2. Create a cluster
# 3. Get connection string
# 4. Add to .env: MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/

# Option 2: Local MongoDB
# Install MongoDB locally and use: MONGODB_URI=mongodb://localhost:27017/

# Initialize database
python scripts/init_db.py

# Test connection
python scripts/test_db.py
```

#### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (create .env.local)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
# Frontend available at http://localhost:3000
```

#### 4. Start Backend API

```bash
cd Playground/backend

# Start FastAPI server
python api/main_v2.py
# Or with uvicorn directly:
uvicorn api.main_v2:app --reload --host 0.0.0.0 --port 8000

# API available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Usage Examples

#### Natural Language Query (via API)

```bash
curl -X POST "http://localhost:8000/api/v1/requests" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Simulate a PWR pin cell with 4.5% enriched UO2 fuel at 600K"
  }'
```

#### Direct Study Submission (YAML)

```bash
curl -X POST "http://localhost:8000/api/v1/studies" \
  -F "file=@aonp/examples/simple_pincell.yaml"
```

#### Query Simulation Results

```bash
# Get run by ID
curl "http://localhost:8000/api/v1/runs/{run_id}"

# Search runs
curl "http://localhost:8000/api/v1/runs?geometry=pincell&enrichment_min=4.0"
```

---

## 📋 Current Project Specifications

### Technology Stack

**Backend**:
- Python 3.10+
- FastAPI (async REST API framework)
- LangGraph (multi-agent orchestration)
- Pydantic v2 (data validation)
- Motor (async MongoDB driver)
- Fireworks AI (LLM provider)

**Frontend**:
- Next.js 15 (React framework)
- TypeScript
- Tailwind CSS
- Server-Sent Events (SSE) for real-time updates

**Simulation Engine**:
- OpenMC 0.14+ (Monte Carlo neutron transport)
- ENDF/B-VII.1 nuclear data library

**Database**:
- MongoDB (state, results, provenance)
- ChromaDB (optional, for RAG vector storage)

### Key Features Implemented

✅ **Multi-Agent Orchestration**
- Router agent for intent classification
- Specialist agents (Studies, Sweep, Query, Analysis)
- LangGraph state machine for workflow management

✅ **OpenMC Integration**
- YAML → StudySpec validation
- Canonical hashing for reproducibility
- XML generation from specifications
- HDF5 result extraction
- MongoDB persistence

✅ **REST API**
- Natural language query endpoints
- Direct study submission
- Run status and results retrieval
- Real-time SSE streaming

✅ **Frontend Interface**
- Next.js web application
- Real-time agent progress visualization
- Query history and result display
- RAG-enhanced chat interface

✅ **Provenance Tracking**
- Cryptographic input hashing
- Complete run manifests
- Audit logging
- Reproducible execution

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/requests` | POST | Submit natural language query |
| `/api/v1/requests/{id}` | GET | Get query status |
| `/api/v1/requests/{id}/stream` | GET | Stream agent progress (SSE) |
| `/api/v1/studies` | POST | Submit study directly (YAML) |
| `/api/v1/runs` | GET | Query simulation runs |
| `/api/v1/runs/{id}` | GET | Get specific run details |
| `/api/v1/runs/compare` | POST | Compare multiple runs |
| `/api/v1/statistics` | GET | Database statistics |
| `/api/v1/health` | GET | Health check |

Full API documentation available at `/docs` when server is running.

---

## 📚 Documentation

### Core Documentation

- **[openmc_design.md](openmc_design.md)** - Complete OpenMC integration design document
- **[OPENMC_API_SPEC.md](OPENMC_API_SPEC.md)** - API specification (superseded, see design doc)
- **[Playground/backend/README_MULTI_AGENT.md](Playground/backend/README_MULTI_AGENT.md)** - Multi-agent system guide
- **[Playground/backend/README_API.md](Playground/backend/README_API.md)** - Backend API documentation
- **[aonp/db/README.md](aonp/db/README.md)** - MongoDB schema and usage

### Frontend Documentation

- **[frontend/RAG_FRONTEND_SHOWCASE.md](frontend/RAG_FRONTEND_SHOWCASE.md)** - RAG frontend features
- **[frontend/MISSION_CONTROL_MVP_PLAN.md](frontend/MISSION_CONTROL_MVP_PLAN.md)** - Mission control interface plan

### Implementation Summaries

- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - OpenMC integration implementation
- **[INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md)** - System integration summary

---

## 🧪 Testing

### Backend Tests

```bash
cd Playground/backend
pytest tests/
```

### Integration Tests

```bash
# Run end-to-end tests
pytest tests/test_integration_complete.py

# Test MongoDB integration
python scripts/test_db.py

# Test OpenMC adapter
python -m pytest tests/test_adapter_e2e.py
```

### Verification Studies

```bash
cd verification_studies
python run_all_studies.py
```

---

## 🔐 Environment Variables

### Backend `.env` (in project root)

```bash
# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DB=aonp_db

# LLM Provider (Fireworks AI)
FIREWORKS_API_KEY=your_fireworks_api_key

# Optional: RAG
VOYAGE_API_KEY=your_voyage_api_key  # For embeddings

# Optional: LangSmith Tracing
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=aonp

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
```

### Frontend `.env.local` (in frontend/)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🐳 Docker Usage

### Build Backend Image

```bash
docker build -t aonp-backend -f aonp/runner/Dockerfile .
```

### Run Backend Container

```bash
docker run -p 8000:8000 \
  -e MONGODB_URI=mongodb+srv://... \
  -e FIREWORKS_API_KEY=... \
  --env-file .env \
  aonp-backend
```

---

## 🚧 Roadmap

### Completed ✅

- [x] Core AONP package with Pydantic schemas
- [x] OpenMC integration (bundling, XML generation, execution)
- [x] MongoDB persistence layer
- [x] Multi-agent orchestration system (LangGraph)
- [x] FastAPI REST API
- [x] Next.js frontend with real-time updates
- [x] RAG-enhanced assistance system
- [x] Provenance tracking with cryptographic hashing

### In Progress 🚧

- [ ] Advanced parameter sweep UI
- [ ] Enhanced result visualization
- [ ] Multi-user authentication
- [ ] Production deployment guides

### Planned 📋

- [ ] Distributed execution (Celery/Ray)
- [ ] Advanced geometry DSL
- [ ] Tally specification in YAML
- [ ] Integration with other neutronics codes
- [ ] Performance optimization for large-scale studies

---

## 🤝 Contributing

This project follows high-integrity scientific computing principles:

1. **Deterministic behavior**: No hidden randomness
2. **Schema-first design**: Pydantic validation for all data
3. **Provenance tracking**: Every result traceable to inputs
4. **Type safety**: Type hints and validation throughout
5. **Comprehensive testing**: Unit, integration, and verification tests

---

## 📄 License

MIT License

---

## 🙏 Acknowledgments

- **OpenMC Team**: Built on [OpenMC](https://openmc.org) - MIT's Monte Carlo particle transport code
- **LangChain/LangGraph**: Multi-agent orchestration framework
- **Fireworks AI**: LLM inference infrastructure
- **MongoDB**: Database and persistence layer

---

## 📧 Contact

For questions, contributions, or collaboration inquiries, please contact:

**Matthew Robillard**  
Email: **robillard.matthew22@berkeley.edu**

---

**Last Updated**: January 2026  
**Version**: 0.1.0

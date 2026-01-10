# AONP Multi-Agent Nuclear Simulation System

AI-powered nuclear simulation system with natural language interface, multi-agent orchestration, and real-time results visualization.

---

## 🏗️ Project Structure

```
.
├── backend/              # Python FastAPI + LangGraph agents
│   ├── api/             # FastAPI REST API
│   ├── agent_tools.py   # MongoDB simulation tools
│   ├── aonp_agents.py   # LangGraph multi-agent orchestrator
│   └── requirements.txt
│
├── frontend/            # Next.js + TypeScript + React
│   ├── app/            # Next.js App Router
│   ├── components/     # React components
│   └── package.json
│
├── docs/               # Documentation
│   ├── OPENMC_API_SPEC.md       # API contract for OpenMC team
│   ├── API_DESIGN_DOCUMENT.md   # Full API documentation
│   └── *.md                      # Other guides
│
└── README.md          # This file
```

---

## 🚀 Quick Start

### 1. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment (.env in project root)
MONGO_URI=mongodb+srv://...
FIREWORKS=your_api_key
VOYAGE=your_api_key
REDIS_URL=redis://localhost:6379  # Optional: for OpenMC queue

# Start FastAPI server
cd api
python main.py
# API running at: http://localhost:8000
# Docs at: http://localhost:8000/docs
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure API endpoint (create .env.local)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
# Frontend running at: http://localhost:3000
```

### 3. Redis Setup (Optional - for OpenMC integration)

```bash
# Docker
docker run -d -p 6379:6379 redis:alpine

# Or use Redis Cloud free tier
# https://redis.com/try-free/
```

---

## 📡 Architecture

### Message Queue Pattern (Recommended)

```
┌──────────┐
│ Frontend │
└────┬─────┘
     │ HTTP
┌────▼──────────────────────┐
│  FastAPI + AONP Agents    │
└────┬──────────────────────┘
     │ Push jobs
┌────▼──────────────────────┐
│     Redis Queue           │
└────┬──────────────────────┘
     │ Pull jobs
┌────▼──────────────────────┐      ┌──────────┐
│  OpenMC Workers           │─────▶│ MongoDB  │
│  (Separate service)       │      │ (shared) │
└───────────────────────────┘      └──────────┘
```

**Data Flow**:
1. User submits natural language query via frontend
2. FastAPI routes to LangGraph agents
3. Agents classify intent, create simulation specs
4. Specs pushed to Redis queue
5. OpenMC workers pull jobs, run simulations
6. Results written to MongoDB
7. Agents analyze results, provide suggestions
8. Frontend displays results in real-time (SSE)

---

## 🔌 API Endpoints

### Backend API (FastAPI)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/requests` | POST | Submit simulation request |
| `/api/v1/requests/{id}` | GET | Get request status |
| `/api/v1/requests/{id}/stream` | GET | Stream agent progress (SSE) |
| `/api/v1/runs` | GET | Query simulation runs |
| `/api/v1/runs/compare` | POST | Compare multiple runs |
| `/api/v1/statistics` | GET | Database statistics |
| `/api/v1/health` | GET | Health check |

**Full API docs**: http://localhost:8000/docs

### OpenMC Backend API (To be implemented by OpenMC team)

See: [`docs/OPENMC_API_SPEC.md`](docs/OPENMC_API_SPEC.md)

---

## 📚 Documentation

- **[OPENMC_API_SPEC.md](docs/OPENMC_API_SPEC.md)** - API contract for OpenMC team (⭐ START HERE)
- **[API_DESIGN_DOCUMENT.md](docs/API_DESIGN_DOCUMENT.md)** - Full backend API documentation
- **[AONP_AGENTS_GUIDE.md](docs/AONP_AGENTS_GUIDE.md)** - Multi-agent system guide
- **[QUICKSTART.md](docs/QUICKSTART.md)** - Detailed setup instructions

---

## 🧪 Testing

### Backend
```bash
cd backend
pytest tests/
```

### Frontend
```bash
cd frontend
npm test
```

### Integration Test
```bash
# Terminal 1: Start backend
cd backend/api && python main.py

# Terminal 2: Start frontend
cd frontend && npm run dev

# Terminal 3: Submit test request
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Content-Type: application/json" \
  -d '{"query": "Simulate PWR pin with 4.5% enriched UO2"}'
```

---

## 🛠️ Development

### Backend Hot Reload
```bash
cd backend/api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Hot Reload
```bash
cd frontend
npm run dev
```

### Database Inspection
```bash
cd backend
python inspect_mongodb.py
```

---

## 🚢 Deployment

### Backend (Azure App Service / Docker)
```bash
cd backend
docker build -t aonp-backend .
docker run -p 8000:8000 --env-file .env aonp-backend
```

### Frontend (Vercel / Netlify)
```bash
cd frontend
npm run build
# Deploy to Vercel: vercel deploy
```

---

## 🔐 Environment Variables

### Backend `.env` (in project root)
```bash
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/aonp
FIREWORKS=your_fireworks_api_key
VOYAGE=your_voyage_api_key
REDIS_URL=redis://localhost:6379
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
```

### Frontend `.env.local` (in frontend/)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🤝 For OpenMC Team

**Integration Guide**: See [`docs/OPENMC_API_SPEC.md`](docs/OPENMC_API_SPEC.md)

**Quick Integration Options**:

1. **Redis Queue** (Recommended):
   - Pull jobs from `openmc:simulation_queue`
   - Write results to MongoDB `runs` collection
   - Zero HTTP API needed

2. **HTTP API**:
   - Implement `POST /api/v1/simulations`
   - Implement `GET /api/v1/simulations/{run_id}`
   - See spec for details

3. **Direct MongoDB**:
   - Poll `runs` collection for `status: "queued"`
   - Update with results when done
   - Simplest but least efficient

**MongoDB Collections You'll Write To**:
- `runs` - Full simulation data
- `summaries` - Lightweight keff summaries

---

## 📊 Tech Stack

**Backend**:
- Python 3.13
- FastAPI (async REST API)
- LangGraph (multi-agent orchestration)
- Motor (async MongoDB driver)
- Fireworks AI (LLM provider)

**Frontend**:
- Next.js 15 (React framework)
- TypeScript
- Tailwind CSS
- Server-Sent Events (SSE) for real-time updates

**Infrastructure**:
- MongoDB Atlas (database)
- Redis (message queue)
- OpenMC (nuclear simulations)

---

## 📈 Roadmap

- [x] Multi-agent orchestration system
- [x] FastAPI REST API
- [x] MongoDB integration
- [ ] Next.js frontend UI
- [ ] OpenMC integration (via Redis queue)
- [ ] Real-time SSE updates
- [ ] Results visualization
- [ ] Parameter sweep UI
- [ ] Authentication
- [ ] Production deployment

---

## 🐛 Troubleshooting

**Backend won't start**:
- Check `.env` file exists in project root
- Verify `MONGO_URI` is correct
- Test: `python -c "from pymongo import MongoClient; print(MongoClient(os.getenv('MONGO_URI')).server_info())"`

**Frontend can't connect to API**:
- Ensure backend is running on port 8000
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Verify CORS is configured: `CORS_ORIGINS=http://localhost:3000`

**OpenMC integration issues**:
- See [`docs/OPENMC_API_SPEC.md`](docs/OPENMC_API_SPEC.md)
- Test MongoDB connection from OpenMC side
- Verify Redis queue is running (if using queue pattern)

---

## 📝 License

MIT

---

## 👥 Team

- **AONP Agents Team**: Backend + Multi-agent system
- **OpenMC Team**: Nuclear simulation backend
- **Frontend Team**: Web UI

---

**Last Updated**: 2026-01-10  
**Version**: 1.0.0


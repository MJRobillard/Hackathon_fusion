# Docker Backend Setup Guide

This guide walks you through setting up and running the backend using Docker.

## Overview

The Docker setup includes:
- **MongoDB**: Database service (port 27017)
- **Backend**: FastAPI server (port 8000)
- **Frontend**: Next.js app (port 3000) - optional

## Prerequisites

1. **Docker** and **Docker Compose** installed
   ```bash
   # Verify installation
   docker --version
   docker compose version
   ```

2. **Environment Variables** (optional but recommended)
   - `FIREWORKS`: API key for Fireworks AI (optional)
   - `VOYAGE_API_KEY`: API key for Voyage AI embeddings (optional)

## Step-by-Step Setup

### Step 1: Create Environment File (Optional)

Create a `.env` file in the project root for API keys:

```bash
# .env file (in project root)
FIREWORKS=your_fireworks_api_key_here
VOYAGE_API_KEY=your_voyage_api_key_here
```

**Note**: These are optional. The backend will work without them, but some features (LLM routing, RAG) may be limited.

### Step 2: Build and Start Services

From the project root directory:

```bash
# Build and start all services (MongoDB + Backend + Frontend)
docker compose up --build

# Or run in detached mode (background)
docker compose up --build -d

# Or start only backend and MongoDB (skip frontend)
docker compose up --build mongo backend
```

### Step 3: Verify Services are Running

```bash
# Check running containers
docker compose ps

# View logs
docker compose logs backend
docker compose logs mongo

# Follow logs in real-time
docker compose logs -f backend
```

### Step 4: Test the Backend

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Or open in browser
# http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {"mongodb": true},
  "version": "2.0.0"
}
```

### Step 5: Access API Documentation

- **Interactive Docs (Swagger)**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Common Operations

### Start Services
```bash
docker compose up
```

### Stop Services
```bash
docker compose down
```

### Stop and Remove Volumes (clean slate)
```bash
docker compose down -v
```

### Rebuild After Code Changes
```bash
docker compose up --build
```

### View Backend Logs
```bash
docker compose logs -f backend
```

### Execute Commands in Backend Container
```bash
docker compose exec backend bash
```

### Restart Only Backend
```bash
docker compose restart backend
```

## Docker Configuration Details

### Backend Service

**Dockerfile**: `Playground/backend/Dockerfile`
- Base image: `python:3.11-slim`
- Installs dependencies from `Playground/backend/api/requirements.txt`
- Exposes port 8000
- Runs `Playground/backend/start_server.py`

**Environment Variables** (set in docker-compose.yml):
- `MONGO_URI`: `mongodb://mongo:27017` (connects to MongoDB service)
- `API_HOST`: `0.0.0.0`
- `API_PORT`: `8000`
- `CORS_ORIGINS`: `http://localhost:3000`
- `FIREWORKS`: From `.env` file or empty
- `VOYAGE_API_KEY`: From `.env` file or empty

### MongoDB Service

- Image: `mongo:7`
- Port: `27017:27017`
- Data persistence: `mongo_data` volume

## Troubleshooting

### Backend Won't Start

1. **Check MongoDB is running**:
   ```bash
   docker compose ps mongo
   docker compose logs mongo
   ```

2. **Check backend logs**:
   ```bash
   docker compose logs backend
   ```

3. **Verify environment variables**:
   ```bash
   docker compose exec backend env | grep MONGO_URI
   ```

### Port Already in Use

If port 8000 is already in use:

```bash
# Find what's using the port
# On Linux/WSL:
sudo lsof -i :8000

# On Windows:
netstat -ano | findstr :8000

# Stop the conflicting service or change the port in docker-compose.yml
```

### MongoDB Connection Issues

The backend connects to MongoDB using the service name `mongo` (not `localhost`). This is automatically configured in `docker-compose.yml`:

```yaml
MONGO_URI: mongodb://mongo:27017
```

If you need to connect from outside Docker, use `localhost:27017`.

### Rebuild After Dependency Changes

If you modify `Playground/backend/api/requirements.txt`:

```bash
docker compose build --no-cache backend
docker compose up backend
```

### View Real-time Logs

```bash
# All services
docker compose logs -f

# Just backend
docker compose logs -f backend

# Last 100 lines
docker compose logs --tail=100 backend
```

### Clean Up

```bash
# Stop and remove containers
docker compose down

# Remove containers, networks, and volumes
docker compose down -v

# Remove images
docker compose down --rmi all
```

## Development Workflow

### Option 1: Docker for Everything
- Use `docker compose up` for all services
- Code changes require rebuild: `docker compose up --build`

### Option 2: Hybrid Approach
- Run MongoDB in Docker: `docker compose up mongo`
- Run backend locally (for faster iteration):
  ```bash
  export MONGO_URI="mongodb://localhost:27017"
  cd Playground/backend
  python start_server.py
  ```

## Next Steps

Once the backend is running:
1. Test the health endpoint: `curl http://localhost:8000/api/v1/health`
2. Explore API docs: http://localhost:8000/docs
3. Connect your frontend to `http://localhost:8000`

## Additional Resources

- Backend Quick Start: `BACKEND_START_GUIDE.md`
- API Documentation: `Playground/backend/README_API.md`
- Docker Compose file: `docker-compose.yml`
- Backend Dockerfile: `Playground/backend/Dockerfile`

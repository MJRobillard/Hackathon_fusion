# 🚀 Start the AONP API Server

## Step 1: Start MongoDB (if not running)

```bash
# Check if MongoDB is running
mongosh --eval "db.version()"

# If not running, start it
sudo systemctl start mongod
```

## Step 2: Set Environment Variables

```bash
cd ~/projects/Hackathon_fusion/Hackathon_fusion/Playground/backend

# Set MongoDB URI (required)
export MONGO_URI="mongodb://localhost:27017"

# Optional: Set Fireworks API key (for LLM routing)
# export FIREWORKS="your_key_here"
```

## Step 3: Start the Server

**Terminal 1 - Start Server:**

```bash
cd ~/projects/Hackathon_fusion/Hackathon_fusion/Playground/backend
python start_server.py
```

You should see:
```
✓ MONGO_URI set
⚠️  WARNING: FIREWORKS key not set (using fast keyword routing)

================================================================================
  AONP Multi-Agent API Server
================================================================================
  
  📡 Server: http://0.0.0.0:8000
  📚 API Docs: http://0.0.0.0:8000/docs
  
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ Connected to MongoDB
```

## Step 4: Test the Server

**Terminal 2 - Run Tests:**

```bash
cd ~/projects/Hackathon_fusion/Hackathon_fusion/Playground/backend
python test_endpoints.py
```

Or test manually:

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Should return: {"status":"healthy","version":"2.0.0",...}
```

## Alternative: Direct uvicorn

If `start_server.py` doesn't work:

```bash
cd ~/projects/Hackathon_fusion/Hackathon_fusion/Playground/backend/api
export MONGO_URI="mongodb://localhost:27017"
python -m uvicorn main_v2:app --host 0.0.0.0 --port 8000 --reload
```

---

## Quick Commands Summary

```bash
# Terminal 1 (Server)
cd ~/projects/Hackathon_fusion/Hackathon_fusion/Playground/backend
export MONGO_URI="mongodb://localhost:27017"
python start_server.py

# Terminal 2 (Tests)  
cd ~/projects/Hackathon_fusion/Hackathon_fusion/Playground/backend
python test_endpoints.py
```

---

## Troubleshooting

### "MONGO_URI not found in environment"
```bash
export MONGO_URI="mongodb://localhost:27017"
```

### "Cannot connect to MongoDB"
```bash
# Start MongoDB
sudo systemctl start mongod

# Check status
sudo systemctl status mongod
```

### "Port 8000 already in use"
```bash
# Kill existing process
sudo lsof -ti:8000 | xargs kill -9
```

---

**Once the server is running, open http://localhost:8000/docs to see the API!**


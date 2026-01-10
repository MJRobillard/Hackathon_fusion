# Quick Start - Run the API Server

## 🚀 Three Ways to Start the Server

### Option 1: Python Script (Easiest - No permissions needed!)

```bash
cd Playground/backend
python start_server.py
```

### Option 2: Direct uvicorn

```bash
cd Playground/backend/api
python -m uvicorn main_v2:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Python main file

```bash
cd Playground/backend/api
python main_v2.py
```

---

## ✅ What You'll See

```
✓ MONGO_URI set
⚠️  WARNING: FIREWORKS key not set (using fast keyword routing)

================================================================================
  AONP Multi-Agent API Server
================================================================================
  Host: 0.0.0.0
  Port: 8000
  CORS: http://localhost:3000,http://localhost:5173

  📡 Server: http://0.0.0.0:8000
  📚 API Docs: http://0.0.0.0:8000/docs
  📖 ReDoc: http://0.0.0.0:8000/redoc
================================================================================

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
✅ Connected to MongoDB
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 🧪 Test It's Working

### In another terminal:

```bash
# Test health endpoint
curl http://localhost:8000/api/v1/health

# Should return:
# {"status":"healthy","version":"2.0.0",...}
```

### Or open in browser:

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

---

## 🔧 If You Get Errors

### "MONGO_URI not set"

Set your MongoDB connection:

```bash
export MONGO_URI="mongodb://localhost:27017"
```

Or create a `.env` file:

```bash
cd Playground/backend
echo 'MONGO_URI=mongodb://localhost:27017' > .env
```

### "uvicorn not installed"

```bash
pip install uvicorn fastapi motor pymongo python-dotenv
```

Or install all requirements:

```bash
cd Playground/backend
pip install -r requirements.txt
```

### "Cannot connect to MongoDB"

Make sure MongoDB is running:

```bash
# Check if MongoDB is running
mongosh --eval "db.version()"

# Or start MongoDB
sudo systemctl start mongod
```

---

## 📡 API Endpoints

Once running, you can test these endpoints:

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### Submit a Query
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Simulate PWR at 4.5% enrichment", "use_llm": false}'
```

### Get Statistics
```bash
curl http://localhost:8000/api/v1/statistics
```

### Query Runs
```bash
curl "http://localhost:8000/api/v1/runs?limit=5"
```

---

## 🎨 Frontend Integration

Once the server is running, your frontend can connect to:

```javascript
const API_URL = "http://localhost:8000";

// Example: Submit query
fetch(`${API_URL}/api/v1/query`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "Simulate PWR at 4.5% enrichment",
    use_llm: false
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## 📚 Full Documentation

- **API Reference**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **Frontend Guide**: [FRONTEND_QUICKSTART.md](./FRONTEND_QUICKSTART.md)
- **Architecture**: [README_API.md](./README_API.md)

---

## 🛑 Stop the Server

Press `Ctrl+C` in the terminal where the server is running.

---

**That's it! Your API is running!** 🚀


# RAG Chat Troubleshooting Guide

## Error: "Failed to execute RAG query: Internal Server Error"

This error means the backend is returning a 500 error. Here's how to fix it:

## Step 1: Check Backend is Running

1. Navigate to the backend directory:
   ```bash
   cd Playground/backend/api
   ```

2. Check if the server is running. You should see output like:
   ```
   ✅ RAG Copilot endpoints registered
   Uvicorn running on http://0.0.0.0:8000
   ```

3. If not running, start it:
   ```bash
   # Windows PowerShell
   python main_v2.py
   
   # Or using uvicorn directly
   uvicorn main_v2:app --reload --host 0.0.0.0 --port 8000
   ```

## Step 2: Check Environment Variables

The backend needs these environment variables. Check your `.env` file in `Playground/backend`:

```bash
# Required
MONGO_URI=mongodb://localhost:27017
FIREWORKS=your_fireworks_api_key_here

# Optional
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Get Fireworks API Key:
1. Go to https://fireworks.ai
2. Sign up/login
3. Get your API key from the dashboard
4. Add it to `.env` file

## Step 3: Check MongoDB is Running

The RAG system needs MongoDB to query simulation data:

```bash
# Check if MongoDB is running
mongosh --eval "db.version()"

# Or check connection
mongosh mongodb://localhost:27017
```

If MongoDB isn't running:
- **Windows**: Start MongoDB service from Services
- **WSL/Linux**: `sudo systemctl start mongod`
- **Docker**: `docker run -d -p 27017:27017 mongo`

## Step 4: Check Backend Console Logs

Look at your backend terminal for error messages:

### Common Errors:

1. **"RAG system not available"**
   - Missing dependencies: `pip install langchain-fireworks pymongo`

2. **"FIREWORKS API key not set"**
   - Add `FIREWORKS=your_key` to `.env`

3. **"MongoDB connection failed"**
   - Check MongoDB is running
   - Check `MONGO_URI` in `.env`

4. **"SimpleRAGAgent initialization failed"**
   - Check both FIREWORKS and MONGO_URI are set

## Step 5: Test the Endpoint Directly

Test if the RAG endpoint works:

```bash
# Test with curl
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is nuclear fusion?"}'

# Expected response:
{
  "status": "success",
  "query": "What is nuclear fusion?",
  "intent": "literature_search",
  "result": "Nuclear fusion is..."
}
```

If this fails, the problem is in the backend, not the frontend.

## Step 6: Check Frontend API URL

Make sure your frontend is pointing to the right backend URL.

Check `frontend/.env.local` or `frontend/lib/constants.ts`:

```typescript
// Should be:
export const API_BASE_URL = 'http://localhost:8000';
```

## Step 7: Check Browser Console

Open browser DevTools (F12) and look at:

1. **Console Tab**: For JavaScript errors
2. **Network Tab**: Check the request to `/api/v1/rag/query`
   - Status should be 200 (not 500 or 404)
   - Response should have JSON data

## Quick Fix Checklist

✅ Backend server is running on port 8000
✅ `FIREWORKS` API key is set in `Playground/backend/.env`
✅ `MONGO_URI` is set in `Playground/backend/.env`
✅ MongoDB is running (mongod service)
✅ RAG endpoints registered (check backend console)
✅ No errors in backend console logs
✅ Frontend `API_BASE_URL` points to `http://localhost:8000`
✅ Browser can reach backend (check Network tab)

## Still Not Working?

Run the backend with verbose logging:

```bash
cd Playground/backend/api
python main_v2.py

# Watch for these messages:
# ✅ RAG Copilot endpoints registered
# ✅ Simple RAG system initialized
#    Papers read: 6
#    Studies learned: 53
```

If you see errors, share them and I can help debug further!

## Alternative: Test RAG Without Frontend

Test the RAG agent directly:

```bash
cd Playground/backend
python simple_rag_agent.py

# Should show:
# ✅ Agent initialized
#    Papers read: 6
#    Studies learned: 53
```

This will tell you if the issue is with the RAG agent itself or the API integration.


# Backend Server Quick Start Guide

## Problem
"Failed to fetch" error occurs because the backend API server is not running.

## Solution: Start the Backend Server

### Prerequisites

1. **MongoDB** must be running
2. **Nuclear data** should be in `nuclear_data/endfb-vii.1-hdf5/cross_sections.xml` (auto-detected by startup scripts)

### Option 1: Using Python Script (Recommended)

**In WSL/Ubuntu terminal:**

```bash
cd ~/projects/Hackathon_fusion/Hackathon_fusion/Playground/backend

# Set MongoDB URI (required)
export MONGO_URI="mongodb://localhost:27017"

# Start the server (automatically sets OPENMC_CROSS_SECTIONS if nuclear_data exists)
python start_server.py
```

### Option 2: Direct uvicorn

```bash
cd ~/projects/Hackathon_fusion/Hackathon_fusion/Playground/backend/api

export MONGO_URI="mongodb://localhost:27017"

# Optional: Set nuclear data path if not auto-detected
export OPENMC_CROSS_SECTIONS="$(cd ../.. && pwd)/nuclear_data/endfb-vii.1-hdf5/cross_sections.xml"

python -m uvicorn main_v2:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Using Shell Script

```bash
cd ~/projects/Hackathon_fusion/Hackathon_fusion/Playground/backend

export MONGO_URI="mongodb://localhost:27017"
chmod +x start_api.sh
./start_api.sh  # Automatically sets OPENMC_CROSS_SECTIONS if nuclear_data exists
```

## Verify Server is Running

After starting, you should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ Connected to MongoDB
```

Test the health endpoint:
```bash
curl http://localhost:8000/api/v1/health
```

Should return:
```json
{"status":"healthy","services":{"mongodb":true},"version":"2.0.0",...}
```

## Environment Variables

### Required
- `MONGO_URI`: MongoDB connection string (e.g., `mongodb://localhost:27017`)

### Optional (Auto-detected if nuclear_data directory exists)
- `OPENMC_CROSS_SECTIONS`: Path to cross_sections.xml file
  - Default: `{project_root}/nuclear_data/endfb-vii.1-hdf5/cross_sections.xml`
  - The startup scripts automatically set this if the file exists

### Manual Setup

If nuclear data is in a different location:

```bash
export OPENMC_CROSS_SECTIONS="/path/to/your/cross_sections.xml"
```

## Troubleshooting

### MongoDB Not Running
```bash
# Check if MongoDB is running
sudo systemctl status mongod

# Start MongoDB if needed
sudo systemctl start mongod
```

### Port Already in Use
If port 8000 is already in use:
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process or use a different port
export API_PORT=8001
```

### Missing Dependencies
```bash
pip install fastapi uvicorn motor pymongo python-dotenv
```

### Nuclear Data Not Found

If you see errors about `cross_sections.xml`:

1. **Check if nuclear data exists:**
   ```bash
   ls -la nuclear_data/endfb-vii.1-hdf5/cross_sections.xml
   ```

2. **Set manually if in different location:**
   ```bash
   export OPENMC_CROSS_SECTIONS="/full/path/to/cross_sections.xml"
   ```

3. **Verify it's set:**
   ```bash
   echo $OPENMC_CROSS_SECTIONS
   ```

## Frontend Configuration

The frontend is configured to connect to `http://localhost:8000` via:
- Next.js rewrites in `next.config.ts`
- API service in `frontend/lib/api.ts`

No changes needed if backend runs on port 8000.

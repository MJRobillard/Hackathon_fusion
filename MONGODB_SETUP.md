# MongoDB Setup Guide for AONP

## Quick Start

### 1. Get MongoDB Atlas (Free Tier)

1. Go to https://www.mongodb.com/cloud/atlas/register
2. Create a free account
3. Create a new cluster (M0 Free Tier is sufficient)
4. Wait for cluster provisioning (~5 minutes)

### 2. Configure Database Access

1. In Atlas dashboard, go to **Database Access**
2. Click **Add New Database User**
3. Choose **Password** authentication
4. Create username and password (save these!)
5. Set user privileges to **Read and write to any database**

### 3. Configure Network Access

1. Go to **Network Access**
2. Click **Add IP Address**
3. Choose **Allow Access from Anywhere** (for development)
   - Or add your specific IP for better security
4. Click **Confirm**

### 4. Get Connection String

1. Go to **Database** → **Connect**
2. Choose **Connect your application**
3. Select **Python** driver version **3.12 or later**
4. Copy the connection string (looks like):
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
5. Replace `<username>` and `<password>` with your credentials

### 5. Create .env File

In your project root, create a `.env` file:

```bash
# MongoDB Configuration
MONGODB_URI=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=aonp_db

# Optional: OpenAI/Agent keys (if using agents)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

**Important**: Add `.env` to your `.gitignore` to keep credentials secure!

### 6. Initialize Database

Run the initialization script to create indexes:

```bash
python scripts/init_db.py
```

Expected output:
```
Connected to MongoDB database: aonp_db
Creating indexes...
✅ MongoDB initialized successfully!

Indexes created for collections:
  - studies (spec_hash unique, created_at)
  - runs (run_id unique, status+created_at, spec_hash+created_at, lease_expires_at, phase+status)
  - summaries (run_id unique, extracted_at)
  - events (run_id+ts, type+ts)
  - agent_outputs (run_id+agent+kind+ts)
```

### 7. Test Connection

Run the test script:

```bash
python scripts/test_db.py
```

Expected output:
```
============================================================
AONP MongoDB Integration Test
============================================================

✅ Connected to MongoDB: aonp_db

📚 Testing study operations...
  - Created study with hash: test_hash_123
  - Upsert returned same study (no duplicate)
✅ Study operations successful

🏃 Testing run lifecycle...
  - Created run: test_run_001
  - Updated to phase: execute, status: running
  - Updated to phase: extract
  - Inserted summary: k-eff = 1.0234 ± 0.0012
  - Completed: phase=done, status=succeeded
  - Retrieved run with 8 events
  - Summary k-eff: 1.0234
✅ Run lifecycle successful

📝 Testing event logging...
  - Logged 4 events
  - Event types: custom_event, another_event, run_created
✅ Event logging successful

🧹 Cleaning up test data...
✅ Cleanup successful

============================================================
Test Summary:
============================================================
Connection           ✅ PASSED
Study Operations     ✅ PASSED
Run Lifecycle        ✅ PASSED
Event Logging        ✅ PASSED
Cleanup              ✅ PASSED

🎉 All tests passed!
```

## Schema Overview

### Collections

#### 1. **studies** - OpenMC Study Specifications
Deduplicated storage of study specs by hash.

```javascript
{
  _id: ObjectId,
  spec_hash: "abc123...",        // unique SHA256 hash
  canonical_spec: {...},          // full StudySpec JSON
  created_at: ISODate
}
```

**Indexes:**
- `spec_hash` (unique)
- `created_at`

#### 2. **runs** - Execution State
Hybrid OpenMC execution + agent coordination.

```javascript
{
  _id: ObjectId,
  run_id: "run_xyz789",          // unique identifier
  spec_hash: "abc123...",         // → studies
  status: "queued|running|succeeded|failed",
  phase: "bundle|execute|extract|done",
  claimed_by: "worker-01",        // for atomic claiming
  lease_expires_at: ISODate,      // lease expiration
  artifacts: {
    bundle_path: "/path/to/bundle",
    statepoint_path: "/path/to/statepoint.h5",
    parquet_path: "/path/to/summary.parquet"
  },
  created_at: ISODate,
  started_at: ISODate,
  ended_at: ISODate
}
```

**Indexes:**
- `run_id` (unique)
- `status + created_at` (compound)
- `spec_hash + created_at` (compound)
- `lease_expires_at`
- `phase + status` (compound)

#### 3. **summaries** - OpenMC Results
k-eff results extracted from statepoint files.

```javascript
{
  _id: ObjectId,
  run_id: "run_xyz789",          // → runs (unique)
  keff: 1.0234,
  keff_std: 0.0012,
  keff_uncertainty_pcm: 120.0,
  n_batches: 100,
  n_inactive: 20,
  n_particles: 10000,
  extracted_at: ISODate
}
```

**Indexes:**
- `run_id` (unique)
- `extracted_at`

#### 4. **events** - Audit Log
Append-only timeline of all run events.

```javascript
{
  _id: ObjectId,
  run_id: "run_xyz789",
  ts: ISODate,
  type: "phase_started|error|summary_extracted",
  agent: "worker-01",             // optional
  payload: {                      // event-specific data
    detail: "..."
  }
}
```

**Indexes:**
- `run_id + ts` (compound)
- `type + ts` (compound)

#### 5. **agent_outputs** - Structured Agent Data (Optional)
Versioned outputs from AI agents.

```javascript
{
  _id: ObjectId,
  run_id: "run_xyz789",
  agent: "planner",
  kind: "plan|report|analysis",
  data: {...},                    // structured data
  schema_version: "0.1",
  ts: ISODate
}
```

**Indexes:**
- `run_id + agent + kind + ts` (compound)

## API Integration

### Option 1: Use the Example Integration

The example file `aonp/api/main_with_mongo.py` shows complete MongoDB integration:

```bash
# Run with MongoDB-enabled API
uvicorn aonp.api.main_with_mongo:app --reload
```

### Option 2: Merge into Existing API

Copy the MongoDB operations from `main_with_mongo.py` into your existing `aonp/api/main.py`.

Key changes:
1. Add imports from `aonp.db`
2. Store studies with `upsert_study()`
3. Track runs with `create_run()`, `update_run_phase()`, etc.
4. Use `append_event()` for audit logging

## Common Operations

### Submit a Run
```bash
curl -X POST "http://localhost:8000/run" \
  -F "file=@aonp/examples/simple_pincell.yaml"
```

Response:
```json
{
  "run_id": "run_abc123",
  "spec_hash": "9bc8221...",
  "status": "queued",
  "phase": "bundle",
  "run_directory": "runs/run_abc123"
}
```

### Check Run Status
```bash
curl "http://localhost:8000/runs/run_abc123"
```

Response:
```json
{
  "run_id": "run_abc123",
  "spec_hash": "9bc8221...",
  "status": "running",
  "phase": "execute",
  "created_at": "2026-01-10T12:00:00Z",
  "started_at": "2026-01-10T12:01:00Z",
  "ended_at": null,
  "artifacts": {
    "bundle_path": "runs/run_abc123",
    "statepoint_path": null,
    "parquet_path": null
  },
  "summary": null,
  "recent_events": [
    {
      "type": "execution_started",
      "timestamp": "2026-01-10T12:01:00Z",
      "agent": null,
      "payload": {"run_dir": "runs/run_abc123"}
    }
  ]
}
```

### List All Runs
```bash
curl "http://localhost:8000/runs?status=queued&limit=10"
```

### Health Check
```bash
curl "http://localhost:8000/health"
```

Response includes MongoDB status:
```json
{
  "status": "healthy",
  "python_version": "3.12.0",
  "openmc_available": true,
  "openmc_version": "0.14.0",
  "mongodb_available": true,
  "mongodb_db": "aonp_db"
}
```

## Multi-Worker Pattern

For distributed execution with multiple workers:

```python
from aonp.db import claim_next_run, release_run, renew_lease

# Worker loop
worker_id = "worker-01"

while True:
    # Atomically claim next queued run
    run = claim_next_run(
        worker_id=worker_id,
        lease_seconds=300,  # 5-minute lease
        eligible_status="queued"
    )
    
    if not run:
        time.sleep(5)  # No work available
        continue
    
    try:
        # Process the run
        run_id = run["run_id"]
        
        # Renew lease periodically if work takes longer
        renew_lease(run_id, worker_id, lease_seconds=300)
        
        # Do work...
        process_run(run)
        
        # Release with success
        release_run(
            run_id=run_id,
            worker_id=worker_id,
            status="succeeded",
            phase="done",
            ended=True
        )
        
    except Exception as e:
        # Release with failure
        release_run(
            run_id=run_id,
            worker_id=worker_id,
            status="failed",
            error={"type": type(e).__name__, "message": str(e)},
            ended=True
        )
```

## Monitoring

### MongoDB Atlas Dashboard

View your data in the Atlas UI:
1. Go to **Database** → **Browse Collections**
2. Select `aonp_db` database
3. Browse each collection

### Query Examples

Connect with Python shell:

```python
from aonp.db import get_db, col_runs

db = get_db()

# Count runs by status
pipeline = [
    {"$group": {"_id": "$status", "count": {"$sum": 1}}}
]
list(col_runs().aggregate(pipeline))

# Find slow runs (>1 hour)
from datetime import datetime, timedelta
cutoff = datetime.utcnow() - timedelta(hours=1)
slow_runs = list(col_runs().find({
    "status": "running",
    "started_at": {"$lt": cutoff}
}))

# Find all runs for a study
runs_for_study = list(col_runs().find({
    "spec_hash": "abc123..."
}).sort("created_at", -1))
```

## Troubleshooting

### Connection Issues

**Error: "Missing MONGODB_URI in environment/.env"**
- Ensure `.env` file exists in project root
- Check `MONGODB_URI` is set correctly

**Error: "ServerSelectionTimeoutError"**
- Verify network access in Atlas (IP whitelist)
- Check MongoDB connection string is correct
- Test internet connectivity

### Authentication Issues

**Error: "Authentication failed"**
- Verify username/password in connection string
- Check user has correct permissions in Atlas
- Ensure password is URL-encoded (escape special characters)

### Index Creation Issues

If `init_db.py` fails:
- Check you have write permissions on the database
- Verify database name is correct
- Try dropping and recreating the database

## Security Best Practices

1. **Never commit .env files** - Add to `.gitignore`
2. **Use IP whitelisting** - Don't allow access from anywhere in production
3. **Rotate credentials** - Change passwords periodically
4. **Use separate databases** - Development vs Production
5. **Enable audit logging** - Track all database access (Atlas feature)

## Next Steps

1. ✅ MongoDB configured and tested
2. Run your first simulation: `python scripts/test_db.py`
3. Start API server: `uvicorn aonp.api.main_with_mongo:app --reload`
4. Submit a run via API
5. Monitor execution in MongoDB Atlas dashboard

For more details, see `aonp/db/README.md`.


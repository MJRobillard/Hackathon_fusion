# MongoDB Quick Reference

## Setup (One-Time)

```bash
# 1. Create .env file
echo "MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/" > .env
echo "MONGODB_DB=aonp_db" >> .env

# 2. Initialize indexes
python scripts/init_db.py

# 3. Test connection
python scripts/test_db.py
```

## Common Imports

```python
from aonp.db import (
    # Study ops
    upsert_study,
    get_study_by_hash,
    
    # Run ops
    create_run,
    get_run,
    update_run_phase,
    update_run_status,
    update_run_artifacts,
    
    # Results
    insert_summary,
    get_summary,
    
    # Audit log
    append_event,
    get_events,
    
    # Multi-worker
    claim_next_run,
    renew_lease,
    release_run,
)
```

## Typical Run Lifecycle

```python
# 1. Store study (deduplicated)
upsert_study(spec_hash="abc123", canonical_spec={...})

# 2. Create run (queued)
create_run(
    run_id="run_xyz",
    spec_hash="abc123",
    initial_phase="bundle",
    initial_status="queued"
)

# 3. Start execution
update_run_phase(
    run_id="run_xyz",
    phase="execute",
    status="running",
    started=True
)

# 4. Store artifacts
update_run_artifacts(
    run_id="run_xyz",
    artifacts={
        "bundle_path": "/path/to/bundle",
        "statepoint_path": "/path/to/statepoint.h5",
        "parquet_path": "/path/to/summary.parquet"
    }
)

# 5. Extract results
update_run_phase(run_id="run_xyz", phase="extract")

insert_summary(
    run_id="run_xyz",
    keff=1.0234,
    keff_std=0.0012,
    keff_uncertainty_pcm=120.0,
    n_batches=100,
    n_inactive=20,
    n_particles=10000
)

# 6. Complete
update_run_phase(
    run_id="run_xyz",
    phase="done",
    status="succeeded"
)
```

## Event Logging

```python
# Log custom events
append_event(
    run_id="run_xyz",
    event_type="simulation_started",
    payload={"worker": "worker-01", "cores": 4}
)

# Retrieve events
events = get_events(run_id="run_xyz", limit=50)
```

## Multi-Worker Pattern

```python
# Worker loop
worker_id = "worker-01"

while True:
    # Claim next run (atomic)
    run = claim_next_run(
        worker_id=worker_id,
        lease_seconds=300,
        eligible_status="queued"
    )
    
    if not run:
        time.sleep(5)
        continue
    
    try:
        # Process run
        run_id = run["run_id"]
        
        # Renew lease if needed
        renew_lease(run_id, worker_id, 300)
        
        # Do work...
        
        # Success
        release_run(
            run_id=run_id,
            worker_id=worker_id,
            status="succeeded",
            phase="done",
            ended=True
        )
    except Exception as e:
        # Failure
        release_run(
            run_id=run_id,
            worker_id=worker_id,
            status="failed",
            error={"type": type(e).__name__, "message": str(e)},
            ended=True
        )
```

## Error Handling

```python
try:
    # Run simulation
    run_simulation(run_dir)
    
    update_run_status(
        run_id=run_id,
        status="succeeded",
        ended=True
    )
except Exception as e:
    update_run_status(
        run_id=run_id,
        status="failed",
        error={
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        },
        ended=True
    )
```

## Common Queries

```python
from aonp.db import col_runs, col_summaries

# Find queued runs
queued = list(col_runs().find({"status": "queued"}))

# Find runs for a study
study_runs = list(col_runs().find({
    "spec_hash": "abc123"
}).sort("created_at", -1))

# Count by status
pipeline = [
    {"$group": {"_id": "$status", "count": {"$sum": 1}}}
]
counts = list(col_runs().aggregate(pipeline))

# Find failed runs
failed = list(col_runs().find({
    "status": "failed"
}).sort("ended_at", -1).limit(10))

# Find runs with k-eff > 1.0
from aonp.db import get_db
db = get_db()
high_keff = list(db.summaries.find({"keff": {"$gt": 1.0}}))
```

## Status & Phase Values

```python
# Status (Literal type)
"queued"      # Waiting to be processed
"running"     # Currently executing
"succeeded"   # Completed successfully
"failed"      # Failed with error

# Phase (Literal type)
"bundle"      # Creating input files
"execute"     # Running OpenMC
"extract"     # Post-processing results
"done"        # Fully complete
```

## Collection Access

```python
from aonp.db import (
    col_studies,
    col_runs,
    col_summaries,
    col_events,
    col_agent_outputs
)

# Direct collection access
runs = col_runs()
runs.find_one({"run_id": "run_xyz"})
runs.count_documents({"status": "queued"})
```

## Monitoring

```python
from aonp.db import get_db

db = get_db()

# Check connection
db.command('ping')

# List collections
db.list_collection_names()

# Collection stats
db.command('collStats', 'runs')

# Index info
col_runs().index_information()
```

## Timestamps

All timestamps are UTC-aware:

```python
from aonp.db.mongo import utcnow

now = utcnow()  # datetime with timezone=UTC
```

## Environment Variables

```bash
# Required
MONGODB_URI=mongodb+srv://...
MONGODB_DB=aonp_db

# Optional (for agents)
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

## Troubleshooting

```python
# Test connection
from aonp.db import get_db
db = get_db()
print(db.command('ping'))  # Should return {'ok': 1.0}

# Check indexes
from aonp.db import init_indexes
init_indexes()  # Safe to run multiple times

# View run details
from aonp.db import get_run, get_events
run = get_run("run_xyz")
events = get_events("run_xyz", limit=100)
print(f"Status: {run['status']}, Phase: {run['phase']}")
for e in events:
    print(f"{e['ts']}: {e['type']} - {e['payload']}")
```

## API Integration

```python
from fastapi import FastAPI
from aonp.db import create_run, get_run

app = FastAPI()

@app.post("/run")
async def submit_run(study: StudySpec):
    spec_hash = study.get_canonical_hash()
    
    # Store study
    upsert_study(spec_hash, study.model_dump())
    
    # Create run
    run = create_run(
        run_id=f"run_{uuid.uuid4().hex[:12]}",
        spec_hash=spec_hash
    )
    
    return {"run_id": run["run_id"]}

@app.get("/runs/{run_id}")
async def get_status(run_id: str):
    run = get_run(run_id)
    if not run:
        raise HTTPException(404)
    return run
```

## See Also

- **Full Documentation**: `aonp/db/README.md`
- **Setup Guide**: `MONGODB_SETUP.md`
- **Implementation Details**: `MONGODB_IMPLEMENTATION.md`
- **API Example**: `aonp/api/main_with_mongo.py`


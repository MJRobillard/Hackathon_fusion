# AONP MongoDB Integration

## Overview

Integrated OpenMC + Agent MongoDB schema for durable run state, audit logging, and multi-worker coordination.

## Collections

### 1. `studies`
OpenMC-specific study specifications (deduplicated by spec_hash):
- `spec_hash` (unique) - SHA256 of canonical study spec
- `canonical_spec` - Full StudySpec JSON
- `created_at` - Timestamp

### 2. `runs`
Hybrid: combines OpenMC phases with agent pattern:
- `run_id` (unique) - Run identifier
- `spec_hash` → studies - Links to study
- `status`: `queued|running|succeeded|failed`
- `phase`: `bundle|execute|extract|done` (OpenMC phases)
- `claimed_by`, `lease_expires_at` - For atomic claiming
- `artifacts`: `{bundle_path, statepoint_path, parquet_path}`
- `created_at`, `started_at`, `ended_at` - Timestamps

### 3. `summaries`
OpenMC keff results:
- `run_id` → runs - Links to run
- `keff`, `keff_std`, `keff_uncertainty_pcm` - Results
- `n_batches`, `n_inactive`, `n_particles` - Settings
- `extracted_at` - Timestamp

### 4. `events`
Append-only audit log:
- `run_id` - Run identifier
- `ts` - Timestamp
- `type` - Event type (e.g., "phase_started", "error")
- `agent` - Optional agent/worker identifier
- `payload` - Event data

### 5. `agent_outputs` (optional)
Structured agent outputs:
- `run_id` - Run identifier
- `agent` - Agent name
- `kind` - Output kind (e.g., "plan", "report")
- `data` - Structured data
- `schema_version` - Version string
- `ts` - Timestamp

## Setup

### 1. Configure Environment Variables

Create a `.env` file in project root:

```bash
# MongoDB connection
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=aonp_db
```

### 2. Initialize Database

Run the initialization script to create indexes:

```bash
python scripts/init_db.py
```

This creates all required indexes for optimal query performance.

## Usage

### Basic Operations

```python
from aonp.db import (
    upsert_study,
    create_run,
    update_run_phase,
    insert_summary,
    append_event,
)

# 1. Store a study (deduplicated by spec_hash)
study = upsert_study(
    spec_hash="abc123...",
    canonical_spec={"name": "pincell", "geometry": {...}}
)

# 2. Create a run
run = create_run(
    run_id="run_xyz789",
    spec_hash="abc123...",
    initial_phase="bundle",
    initial_status="queued"
)

# 3. Update phase as work progresses
update_run_phase(
    run_id="run_xyz789",
    phase="execute",
    status="running",
    started=True
)

# 4. Store results
insert_summary(
    run_id="run_xyz789",
    keff=1.0234,
    keff_std=0.0012,
    keff_uncertainty_pcm=120,
    n_batches=100,
    n_inactive=20,
    n_particles=10000
)

# 5. Add audit events
append_event(
    run_id="run_xyz789",
    event_type="simulation_completed",
    payload={"exit_code": 0, "elapsed_seconds": 45.2}
)
```

### Multi-Worker Coordination (Atomic Claiming)

For distributed workers processing runs:

```python
from aonp.db import claim_next_run, release_run

# Worker claims a run (atomic, multi-worker safe)
worker_id = "worker-01"
run = claim_next_run(
    worker_id=worker_id,
    lease_seconds=300,  # 5-minute lease
    eligible_status="queued"
)

if run:
    try:
        # Process the run...
        process_run(run)
        
        # Release with success
        release_run(
            run_id=run["run_id"],
            worker_id=worker_id,
            status="succeeded",
            phase="done",
            ended=True
        )
    except Exception as e:
        # Release with failure
        release_run(
            run_id=run["run_id"],
            worker_id=worker_id,
            status="failed",
            error={"type": type(e).__name__, "message": str(e)},
            ended=True
        )
```

### Agent Integration (Optional)

Store structured agent outputs:

```python
from aonp.db import upsert_agent_output

upsert_agent_output(
    run_id="run_xyz789",
    agent="planner",
    kind="simulation_plan",
    data={
        "geometry_changes": [...],
        "material_updates": [...],
        "rationale": "..."
    },
    schema_version="0.1"
)
```

## API Integration

Update `aonp/api/main.py` to use MongoDB:

```python
from aonp.db import create_run, upsert_study, get_run

@app.post("/run", response_model=RunResponse)
async def submit_run(file: UploadFile = File(...)):
    contents = await file.read()
    data = yaml.safe_load(contents)
    study = StudySpec(**data)
    
    # Store study in MongoDB
    spec_hash = study.get_canonical_hash()
    upsert_study(spec_hash, study.model_dump())
    
    # Create run bundle
    run_dir, _ = create_run_bundle(study)
    run_id = run_dir.name
    
    # Create run in MongoDB
    create_run(
        run_id=run_id,
        spec_hash=spec_hash,
        initial_phase="bundle",
        initial_status="queued"
    )
    
    return RunResponse(
        run_id=run_id,
        spec_hash=spec_hash,
        status="queued",
        run_directory=str(run_dir)
    )
```

## Monitoring & Queries

```python
from aonp.db import col_runs, get_events

# Find all queued runs
queued_runs = list(col_runs().find({"status": "queued"}))

# Find runs for a specific study
runs_by_study = list(col_runs().find({"spec_hash": "abc123..."}).sort("created_at", -1))

# Get audit trail for a run
events = get_events(run_id="run_xyz789", limit=50)

# Count runs by status
from aonp.db import get_db
db = get_db()
pipeline = [
    {"$group": {"_id": "$status", "count": {"$sum": 1}}}
]
status_counts = list(db.runs.aggregate(pipeline))
```

## Indexes

All indexes are automatically created by `init_indexes()`:

**studies:**
- `spec_hash` (unique)
- `created_at`

**runs:**
- `run_id` (unique)
- `status + created_at` (compound)
- `spec_hash + created_at` (compound)
- `lease_expires_at`
- `phase + status` (compound)

**summaries:**
- `run_id` (unique)
- `extracted_at`

**events:**
- `run_id + ts` (compound)
- `type + ts` (compound)

**agent_outputs:**
- `run_id + agent + kind + ts` (compound)

## Testing

Test the connection:

```bash
python -c "from aonp.db import get_db; print(f'Connected to: {get_db().name}')"
```

Run initialization:

```bash
python scripts/init_db.py
```


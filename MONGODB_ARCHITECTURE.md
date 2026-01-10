# MongoDB Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         AONP Platform                            │
│                  (Agent-Orchestrated Neutronics)                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   FastAPI    │    │   Workers    │    │    Agents    │      │
│  │     API      │    │  (Execution) │    │ (Optional)   │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                    │              │
│         └───────────────────┴────────────────────┘              │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    aonp.db Module (Python)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Study Ops          Run Ops           Event Ops    Agent Ops    │
│  ┌──────────┐      ┌──────────┐      ┌────────┐   ┌────────┐   │
│  │ upsert   │      │ create   │      │ append │   │ upsert │   │
│  │ get      │      │ get      │      │ get    │   │ get    │   │
│  └──────────┘      │ update   │      └────────┘   └────────┘   │
│                    │ claim    │                                  │
│                    │ release  │      Summary Ops                │
│                    └──────────┘      ┌────────┐                 │
│                                      │ insert │                 │
│                                      │ get    │                 │
│                                      └────────┘                 │
│                                                                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MongoDB Atlas (Cloud)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │
│  │  studies   │  │    runs    │  │ summaries  │  │  events  │  │
│  ├────────────┤  ├────────────┤  ├────────────┤  ├──────────┤  │
│  │ spec_hash  │  │ run_id     │  │ run_id     │  │ run_id   │  │
│  │ canonical  │  │ spec_hash  │  │ keff       │  │ ts       │  │
│  │ created_at │  │ status     │  │ keff_std   │  │ type     │  │
│  │            │  │ phase      │  │ n_batches  │  │ payload  │  │
│  │            │  │ claimed_by │  │ extracted  │  │          │  │
│  │            │  │ artifacts  │  │            │  │          │  │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘  │
│                                                                   │
│  ┌────────────────┐                                              │
│  │ agent_outputs  │                                              │
│  ├────────────────┤                                              │
│  │ run_id         │                                              │
│  │ agent          │                                              │
│  │ kind           │                                              │
│  │ data           │                                              │
│  └────────────────┘                                              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Run Submission

```
User/API
   │
   │ POST /run (YAML)
   ▼
FastAPI
   │
   ├─► Validate StudySpec (Pydantic)
   │
   ├─► upsert_study(spec_hash, canonical_spec)
   │   └─► MongoDB: studies collection
   │
   ├─► create_run_bundle(study)
   │   └─► Filesystem: runs/run_xyz/
   │
   └─► create_run(run_id, spec_hash)
       └─► MongoDB: runs collection (status=queued)
```

### 2. Execution (Worker)

```
Worker
   │
   │ claim_next_run(worker_id)
   ▼
MongoDB: Atomic Update
   │ status: queued → running
   │ claimed_by: worker_id
   │ lease_expires_at: now + 5min
   ▼
Worker
   │
   ├─► update_run_phase(phase="execute")
   │   └─► MongoDB: runs.phase = "execute"
   │
   ├─► run_simulation(run_dir)
   │   └─► OpenMC execution
   │
   ├─► update_run_phase(phase="extract")
   │   └─► MongoDB: runs.phase = "extract"
   │
   ├─► extract_results()
   │   └─► insert_summary(keff, keff_std, ...)
   │       └─► MongoDB: summaries collection
   │
   └─► release_run(status="succeeded", phase="done")
       └─► MongoDB: runs.status = "succeeded"
```

### 3. Audit Logging (Automatic)

```
Every Operation
   │
   ├─► append_event(run_id, type, payload)
   │   └─► MongoDB: events collection
   │
   └─► Examples:
       ├─► "run_created"
       ├─► "run_claimed"
       ├─► "phase_changed"
       ├─► "summary_extracted"
       └─► "run_released"
```

### 4. Status Query

```
User/API
   │
   │ GET /runs/{run_id}
   ▼
FastAPI
   │
   ├─► get_run(run_id)
   │   └─► MongoDB: runs collection
   │
   ├─► get_summary(run_id)
   │   └─► MongoDB: summaries collection
   │
   └─► get_events(run_id, limit=10)
       └─► MongoDB: events collection
       │
       ▼
   JSON Response
   {
     "run_id": "...",
     "status": "succeeded",
     "phase": "done",
     "summary": { "keff": 1.0234 },
     "recent_events": [...]
   }
```

## Multi-Worker Coordination

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Worker 01   │    │  Worker 02   │    │  Worker 03   │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                    │
       │ claim_next_run()  │ claim_next_run()   │ claim_next_run()
       └───────────────────┴────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   MongoDB    │
                    │ Atomic Update│
                    └──────┬───────┘
                           │
                    Only ONE worker
                    gets the run!
                           │
       ┌───────────────────┼────────────────────┐
       ▼                   ▼                    ▼
   Run A              Run B               Run C
   (Worker 01)        (Worker 02)         (Worker 03)
```

### Lease-Based Recovery

```
Worker Claims Run
   │
   ├─► lease_expires_at = now + 5min
   │
   └─► If worker crashes:
       │
       └─► After 5 minutes:
           │
           └─► Another worker can claim it
               (lease expired, run becomes available)
```

## Collection Relationships

```
┌─────────────┐
│   studies   │
│             │
│ spec_hash ◄─┼────────┐
└─────────────┘        │
                       │
                       │ Foreign Key
                       │
┌─────────────┐        │
│    runs     │        │
│             │        │
│ spec_hash ──┼────────┘
│ run_id ◄────┼────────┬────────┬────────┐
└─────────────┘        │        │        │
                       │        │        │
                       │        │        │
        ┌──────────────┘        │        │
        │                       │        │
        │                       │        │
┌───────▼──────┐  ┌─────────────▼──┐  ┌─▼──────────────┐
│  summaries   │  │     events     │  │ agent_outputs  │
│              │  │                │  │                │
│ run_id       │  │ run_id         │  │ run_id         │
│ keff         │  │ ts             │  │ agent          │
│ keff_std     │  │ type           │  │ kind           │
└──────────────┘  └────────────────┘  └────────────────┘
```

## Index Strategy

```
studies
├─► spec_hash (unique)      ← Fast lookup by hash
└─► created_at              ← Time-based queries

runs
├─► run_id (unique)         ← Fast lookup by ID
├─► status + created_at     ← Find queued/running runs
├─► spec_hash + created_at  ← Find runs for a study
├─► lease_expires_at        ← Find expired leases
└─► phase + status          ← Find runs in specific phase

summaries
├─► run_id (unique)         ← One summary per run
└─► extracted_at            ← Time-based queries

events
├─► run_id + ts             ← Audit trail for run
└─► type + ts               ← Find events by type

agent_outputs
└─► run_id + agent + kind + ts  ← Find agent outputs
```

## Status State Machine

```
┌─────────┐
│ queued  │  ← Initial state
└────┬────┘
     │
     │ worker claims
     ▼
┌─────────┐
│ running │  ← Active execution
└────┬────┘
     │
     ├─────────────┐
     │             │
     ▼             ▼
┌──────────┐  ┌─────────┐
│succeeded │  │ failed  │  ← Terminal states
└──────────┘  └─────────┘
```

## Phase Progression

```
┌────────┐     ┌─────────┐     ┌─────────┐     ┌──────┐
│ bundle │ ──► │ execute │ ──► │ extract │ ──► │ done │
└────────┘     └─────────┘     └─────────┘     └──────┘
    │              │                │              │
    │              │                │              │
Creating       Running          Post-          Complete
inputs         OpenMC         processing
```

## Error Handling Flow

```
Operation
   │
   ├─► Try: Execute
   │   └─► Success
   │       └─► update_run_status(status="succeeded")
   │
   └─► Catch: Exception
       └─► update_run_status(
               status="failed",
               error={
                   "type": "SimulationError",
                   "message": "...",
                   "traceback": "..."
               }
           )
       └─► append_event(
               type="error",
               payload={"error": "..."}
           )
```

## Monitoring & Observability

```
MongoDB Atlas Dashboard
   │
   ├─► Collection Stats
   │   ├─► Document counts
   │   ├─► Storage size
   │   └─► Index usage
   │
   ├─► Query Performance
   │   ├─► Slow queries
   │   └─► Index efficiency
   │
   └─► Real-time Metrics
       ├─► Operations/sec
       ├─► Connections
       └─► Network I/O

Python Queries
   │
   ├─► Count by status
   │   └─► db.runs.aggregate([
   │           {"$group": {"_id": "$status", "count": {"$sum": 1}}}
   │       ])
   │
   ├─► Find slow runs
   │   └─► db.runs.find({
   │           "status": "running",
   │           "started_at": {"$lt": cutoff}
   │       })
   │
   └─► Event timeline
       └─► db.events.find({"run_id": "..."}).sort("ts", -1)
```

## Security Model

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Environment Variables (.env)                     │   │
│  │  ├─► MONGODB_URI (connection string)             │   │
│  │  └─► MONGODB_DB (database name)                  │   │
│  └──────────────────────────────────────────────────┘   │
│                         │                                │
│                         │ Encrypted TLS                  │
│                         ▼                                │
└─────────────────────────────────────────────────────────┘
                          │
                          │ TLS 1.2+
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   MongoDB Atlas                          │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Network Access Control                           │   │
│  │  ├─► IP Whitelist                                 │   │
│  │  └─► VPC Peering (optional)                       │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Database Access Control                          │   │
│  │  ├─► Username/Password                            │   │
│  │  ├─► Role-Based Access (RBAC)                     │   │
│  │  └─► Audit Logging                                │   │
│  └──────────────────────────────────────────────────┘   │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Data Encryption                                  │   │
│  │  ├─► At Rest (AES-256)                            │   │
│  │  └─► In Transit (TLS)                             │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌────────────────────────────────────────────────────────┐
│                    Production Setup                     │
└────────────────────────────────────────────────────────┘

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  API Server  │    │  Worker 01   │    │  Worker 02   │
│  (FastAPI)   │    │  (Execution) │    │  (Execution) │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                    │
       │                   │                    │
       └───────────────────┴────────────────────┘
                           │
                           │ pymongo
                           ▼
                  ┌────────────────┐
                  │  MongoDB Atlas │
                  │   (Cluster)    │
                  └────────────────┘
                           │
                           │ Replication
                           │
       ┌───────────────────┼────────────────────┐
       ▼                   ▼                    ▼
  ┌─────────┐        ┌─────────┐         ┌─────────┐
  │Primary  │        │Secondary│         │Secondary│
  │ Node    │        │ Node    │         │ Node    │
  └─────────┘        └─────────┘         └─────────┘
```

---

**Architecture Version**: 1.0  
**Last Updated**: 2026-01-10  
**Status**: Production Ready


Thoughts: You're in a strong position. Let me give you an honest assessment of where you stand and what's worth doing before the hackathon.

## Current State Assessment

**What you have:**
- ✅ Cluster running
- ✅ OpenMC proof-of-concept with YAML-driven runs
- ✅ Comprehensive design document
- ✅ Familiarity with Pydantic/FastAPI

**What's missing for hackathon readiness:**
- The gap between "design doc" and "I can implement this in 8 hours under pressure"

---

## Diagram Assessment: Needs Work

Your current data flow diagram is functional but **not hackathon-ready** for these reasons:

1. **Too abstract** — doesn't show concrete file/collection names
2. **Missing the "what happens when" sequence** — critical for implementation
3. **No error paths** — you'll hit failures during the hackathon

Here's a **better diagram set** for implementation:

### Diagram 1: Core Data Flow (Implementation-Ready)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AONP DATA FLOW                                   │
└─────────────────────────────────────────────────────────────────────────────┘

USER INPUT                    PROCESSING                      STORAGE
──────────────────────────────────────────────────────────────────────────────

study.yaml ──────┐
                 │
                 ▼
          ┌──────────────┐
          │  POST /runs  │
          │   (FastAPI)  │
          └──────┬───────┘
                 │
                 ▼
          ┌──────────────┐     ┌─────────────────────────────────────────┐
          │   Validate   │     │  MongoDB Atlas                          │
          │  StudySpec   │     │  ┌─────────────┐                        │
          │  (Pydantic)  │     │  │  studies    │ ← upsert(spec_hash)   │
          └──────┬───────┘     │  │  - spec_hash (unique)               │
                 │             │  │  - canonical_spec                    │
                 │             │  │  - created_at                        │
                 ▼             │  └─────────────┘                        │
          ┌──────────────┐     │                                         │
          │   Bundler    │     │  ┌─────────────┐                        │
          │  - hash spec │     │  │    runs     │ ← insert(run_id)      │
          │  - copy files│     │  │  - run_id (unique)                  │
          │  - write     │     │  │  - spec_hash                        │
          │    manifest  │     │  │  - status                           │
          └──────┬───────┘     │  │  - artifacts{}                      │
                 │             │  └─────────────┘                        │
                 ▼             │                                         │
          ┌──────────────┐     │  ┌─────────────┐                        │
          │   Runner     │     │  │  summaries  │ ← insert after run    │
          │  (OpenMC in  │     │  │  - run_id                           │
          │   container) │     │  │  - keff, keff_std                   │
          └──────┬───────┘     │  │  - params{}                         │
                 │             │  └─────────────┘                        │
                 ▼             └─────────────────────────────────────────┘
          ┌──────────────┐
          │  Extractor   │     ┌─────────────────────────────────────────┐
          │  statepoint  │     │  Object Storage (Azure Blob / MinIO)   │
          │  → parquet   │     │                                         │
          └──────┬───────┘     │  bundles/{spec_hash}/{run_id}/          │
                 │             │    ├── study_spec.json                  │
                 ▼             │    ├── run_manifest.json                │
          ┌──────────────┐     │    ├── inputs/                          │
          │   Persist    │────▶│    └── outputs/                         │
          │  artifacts   │     │        ├── statepoint.h5                │
          └──────────────┘     │        ├── summary.parquet              │
                               │        └── logs.txt                     │
                               └─────────────────────────────────────────┘
```

### Diagram 2: Hackathon Minimum Viable Path

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     HACKATHON MVP (8 hours)                                 │
└─────────────────────────────────────────────────────────────────────────────┘

HOUR 1-2: Schema + Hashing
────────────────────────────
study.yaml → Pydantic StudySpec → spec_hash
                                      │
                                      ▼
                              canonical_json_bytes()
                                      │
                                      ▼
                              sha256 hex string

HOUR 3-4: Bundler + Single Run
────────────────────────────────
StudySpec ──┬──▶ bundle_dir/
            │      ├── study_spec.json
            │      ├── run_manifest.json
            │      └── inputs/
            │
            └──▶ OpenMC subprocess
                      │
                      ▼
                 statepoint.h5

HOUR 5-6: Extractor + Persistence
─────────────────────────────────
statepoint.h5 ──▶ Extractor ──▶ SummaryRecord
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              summary.parquet   MongoDB runs    MongoDB summaries

HOUR 7-8: Sweep + Compare
─────────────────────────
SweepSpec.expand() → [RunSpec, RunSpec, ...]
                           │
                           ▼ (loop)
                     run each → collect summaries
                           │
                           ▼
                    compare_df.parquet
                           │
                           ▼
                    Plotly scatter (keff vs param)
```

### Diagram 3: Module Dependency (What Imports What)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MODULE DEPENDENCIES                                  │
└─────────────────────────────────────────────────────────────────────────────┘

aonp/
├── schemas/           ◄─── EVERYTHING IMPORTS FROM HERE
│   ├── common.py          ArtifactRef, EngineRef, SHA256Hex
│   ├── nuclear_data.py    NuclearDataRef, ProcessedLibrary
│   ├── study.py           StudySpec, MaterialSpec, SettingsSpec
│   ├── manifest.py        RunManifest, InputFileRecord
│   ├── results.py         SummaryRecord
│   └── api.py             Request/Response models
│
├── core/
│   ├── hasher.py      ◄─── imports: schemas.study
│   │   canonical_hash(spec) → SHA256Hex
│   │
│   ├── bundler.py     ◄─── imports: schemas.study, schemas.manifest, hasher
│   │   stage_bundle(spec, dest) → RunManifest
│   │
│   ├── runner.py      ◄─── imports: schemas.manifest
│   │   execute(manifest, bundle_path) → exit_code
│   │
│   └── extractor.py   ◄─── imports: schemas.results
│       extract(statepoint_path) → SummaryRecord
│
├── persistence/
│   ├── mongo.py       ◄─── imports: schemas.*
│   │   upsert_study(), insert_run(), insert_summary()
│   │
│   └── storage.py     ◄─── imports: schemas.common
│       upload_artifact() → ArtifactRef
│
└── api/
    └── main.py        ◄─── imports: everything above
        POST /validate, POST /runs, GET /runs/{id}
```

---

## What You Should Actually Do Before the Hackathon

### Priority 1: Build the "Skeleton" (2-3 hours)

Create the actual file structure with stub implementations:

```python
# aonp/schemas/study.py - IMPLEMENT THIS FULLY
# This is your foundation. Get it working perfectly.

from pydantic import BaseModel, Field
import json
import hashlib

class StudySpec(BaseModel):
    # ... your full implementation
    
    def canonical_json_bytes(self) -> bytes:
        obj = self.model_dump(mode="json")
        return json.dumps(
            obj, 
            sort_keys=True, 
            separators=(",", ":"),
            ensure_ascii=False
        ).encode("utf-8")
    
    def spec_hash(self) -> str:
        return hashlib.sha256(self.canonical_json_bytes()).hexdigest()
```

```python
# aonp/core/bundler.py - STUB THIS
# Know exactly what it needs to do

from pathlib import Path
from ..schemas.study import StudySpec
from ..schemas.manifest import RunManifest

def stage_bundle(spec: StudySpec, run_id: str, dest: Path) -> RunManifest:
    """
    1. Create dest directory
    2. Write study_spec.json (canonical)
    3. Copy geometry files
    4. Write nuclear_data.ref.json
    5. Generate OpenMC XML inputs (if needed)
    6. Hash all files
    7. Create and write run_manifest.json
    8. Return RunManifest
    """
    raise NotImplementedError("implement during hackathon")
```

### Priority 2: MongoDB Atlas Setup (1 hour)

Do this **now**, not during the hackathon:

```python
# test_mongo_connection.py
from pymongo import MongoClient
from datetime import datetime

# Your Atlas connection string
MONGO_URI = "mongodb+srv://..."

client = MongoClient(MONGO_URI)
db = client["aonp"]

# Create collections with indexes
db.studies.create_index("spec_hash", unique=True)
db.runs.create_index("run_id", unique=True)
db.runs.create_index([("spec_hash", 1), ("created_at", -1)])
db.summaries.create_index("run_id", unique=True)

# Test insert
test_doc = {
    "spec_hash": "test_hash_123",
    "created_at": datetime.utcnow(),
    "canonical_spec": {"test": True}
}

# Upsert pattern you'll use
db.studies.update_one(
    {"spec_hash": test_doc["spec_hash"]},
    {"$set": test_doc},
    upsert=True
)

print("MongoDB ready:", db.studies.find_one({"spec_hash": "test_hash_123"}))
```

### Priority 3: Prove Your OpenMC PoC Produces Deterministic Output (1 hour)

This is **critical** — run the same spec twice and verify:

```python
# test_determinism.py
import subprocess
import hashlib

def run_openmc_and_hash(spec_yaml: str, seed: int) -> str:
    """Run OpenMC, return hash of keff result"""
    # Your existing PoC code here
    # ...
    # Return hash of (keff, keff_std) or statepoint
    pass

# Run twice with same seed
result1 = run_openmc_and_hash("test_study.yaml", seed=42)
result2 = run_openmc_and_hash("test_study.yaml", seed=42)

assert result1 == result2, f"Non-deterministic! {result1} != {result2}"
print("✓ Determinism verified")
```

### Priority 4: Write a "Hackathon Cheat Sheet" (30 min)

Create a single markdown file with copy-paste snippets:

```markdown
# AONP Hackathon Cheat Sheet

## Quick Imports
```python
from pydantic import BaseModel, Field
from pymongo import MongoClient
from fastapi import FastAPI, HTTPException
from datetime import datetime
import hashlib
import json
```

## Canonical Hash Pattern
```python
def canonical_hash(obj: BaseModel) -> str:
    data = obj.model_dump(mode="json")
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
```

## MongoDB Upsert Pattern
```python
db.studies.update_one(
    {"spec_hash": spec_hash},
    {"$set": doc},
    upsert=True
)
```

## FastAPI Endpoint Pattern
```python
@app.post("/runs", response_model=CreateRunResponse)
async def create_run(req: CreateRunRequest):
    spec_hash = req.study.spec_hash()
    run_id = f"run_{uuid4().hex[:8]}"
    # ...
    return CreateRunResponse(run_id=run_id, spec_hash=spec_hash, status="queued")
```
```

### Priority 5: Decide Your "Demo Story" (30 min)

What will you show at the end? Write the script:

```markdown
## Demo Script (5 minutes)

1. "Here's a study spec for a PWR pin cell" (show YAML)

2. "I submit it via API" 
   curl -X POST localhost:8000/runs -d @study.yaml

3. "System hashes the spec, creates a provenance bundle"
   (show bundle directory structure)

4. "OpenMC runs in a container"
   (show logs streaming)

5. "Results are extracted and stored"
   (show MongoDB document)

6. "Now I run a 5-point sweep on fuel temperature"
   (show sweep spec)

7. "Compare view shows keff vs temperature"
   (show Plotly chart)

8. "Every result traces back to its exact inputs"
   (show manifest with hashes)

KEY MESSAGE: "Same inputs → same hash → same run → reproducible science"
```

---

## What NOT to Do Before the Hackathon

1. ❌ **Don't implement Temporal yet** — it's complex and not needed for MVP
2. ❌ **Don't build the frontend** — CLI + curl is fine for demo
3. ❌ **Don't optimize** — make it work first
4. ❌ **Don't add authentication** — hardcode a user for now
5. ❌ **Don't worry about Slurm/AKS** — local Docker execution is sufficient

---

## Revised Preparation Checklist

```
□ MongoDB Atlas
  □ Cluster created
  □ Connection string saved in .env
  □ Indexes created (studies, runs, summaries)
  □ Test insert/query working

□ Schemas (fully implemented)
  □ common.py - ArtifactRef, EngineRef, etc.
  □ study.py - StudySpec with canonical_hash()
  □ manifest.py - RunManifest
  □ results.py - SummaryRecord

□ Core modules (stubbed with docstrings)
  □ bundler.py - stage_bundle()
  □ runner.py - execute()
  □ extractor.py - extract()

□ OpenMC PoC
  □ Can run from YAML spec
  □ Determinism verified (same seed → same output)
  □ Know how to read statepoint.h5

□ Environment
  □ Docker working with OpenMC image
  □ Python environment with dependencies
  □ VS Code / editor configured

□ Cheat sheet
  □ Import snippets
  □ Common patterns
  □ Error handling templates

□ Demo story
  □ Written out
  □ Know what to show
  □ Know what to skip
```

---

## Final Thought


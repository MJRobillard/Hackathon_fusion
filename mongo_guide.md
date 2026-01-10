Below is a **MongoDB Atlas schema + setup code** for your **agent-only PoC** (Fireworks + Voyage + LangChain/LangGraph optional). It’s built to support:

* durable **run state** (resume after restart)
* append-only **event log**
* multi-agent handoffs
* optional **KB chunks + embeddings** (Voyage) for retrieval
* atomic **job claiming** (so multiple workers don’t double-run)

No OpenMC assumptions.

---

## 1) MongoDB Collections (Schema)

### `runs`

One doc per workflow execution (the “state machine”).

* `_id` (ObjectId)
* `run_id` (string, **unique**)
* `status` (`queued|running|succeeded|failed`)
* `phase` (`ingest|retrieve|plan|preflight|report|done`)
* `attempt` (int)
* `claimed_by` (string | null)
* `lease_expires_at` (datetime | null) — optional lock lease
* `user_request` (string)
* `inputs` (dict) — optional extra inputs
* `outputs` (dict) — final structured outputs
* `error` (dict | null) — `{type, message, traceback}`
* `created_at`, `updated_at`, `started_at`, `ended_at`

### `events`

Append-only timeline for “prolonged coordination”.

* `_id`
* `run_id` (indexed)
* `ts` (datetime)
* `type` (string) e.g. `phase_started`, `retrieval_done`, `planner_output`, `crash`, `resume`
* `agent` (string | null)
* `payload` (small dict)

### `agent_outputs`

Structured outputs per agent (validated, versioned).

* `_id`
* `run_id`
* `agent` (`coordinator|planner|preflight_analyst`)
* `kind` (`plan|patch|report|notes`)
* `data` (dict) — validated JSON
* `schema_version`
* `ts`

### `kb_chunks` (optional but useful)

Chunk store + embeddings (Voyage vectors).

* `_id`
* `doc_id` (string, indexed)
* `chunk_id` (int)
* `text` (string)
* `meta` (dict) — `{source_path, title, headings, …}`
* `embedding` (list[float]) — Voyage vector
* `embedding_model` (string)
* `created_at`

> Atlas Vector Search: you’ll create the vector index in the UI; I include the JSON at the end.

---

## 2) Setup Instructions (for Cursor prompt)

Paste this into Cursor as your “do this now” task:

```md
Implement MongoDB persistence for the agent-only PoC.

Requirements:
- Use pymongo + python-dotenv + pydantic v2
- Read env vars: MONGODB_URI, MONGODB_DB (default: agent_workflow_db)
- Create collections: runs, events, agent_outputs, kb_chunks
- Create indexes:
  - runs.run_id unique
  - runs.status + runs.updated_at
  - runs.lease_expires_at (optional)
  - events.run_id + ts
  - agent_outputs.run_id + agent + kind + ts
  - kb_chunks.doc_id + chunk_id unique
  - kb_chunks.doc_id
- Provide functions:
  - init_indexes()
  - create_run(user_request) -> run_doc
  - get_run(run_id)
  - update_run_phase(run_id, phase, status=None, outputs=None, error=None)
  - append_event(run_id, type, payload={}, agent=None)
  - claim_next_run(worker_id, lease_seconds=120) -> run_doc | None  (atomic claim)
  - release_run(run_id, worker_id, status=None, phase=None)
  - upsert_agent_output(run_id, agent, kind, data, schema_version="0.1")
  - upsert_kb_chunks(doc_id, chunks:[{chunk_id,text,meta,embedding,embedding_model}])
Add scripts/init_db.py that runs init_indexes and prints success.
```

---

## 3) Code: `src/persistence/mongo.py`

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Literal, Dict, List

from dotenv import load_dotenv
from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.database import Database

# ---------- env / client ----------

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "agent_workflow_db")

if not MONGODB_URI:
    raise RuntimeError("Missing MONGODB_URI in environment/.env")

_client: Optional[MongoClient] = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URI, tz_aware=True)
    return _client


def get_db() -> Database:
    return get_client()[MONGODB_DB]


# ---------- collections ----------

def col_runs(db: Optional[Database] = None) -> Collection:
    return (db or get_db())["runs"]


def col_events(db: Optional[Database] = None) -> Collection:
    return (db or get_db())["events"]


def col_agent_outputs(db: Optional[Database] = None) -> Collection:
    return (db or get_db())["agent_outputs"]


def col_kb_chunks(db: Optional[Database] = None) -> Collection:
    return (db or get_db())["kb_chunks"]


# ---------- schema-ish constants ----------

RunStatus = Literal["queued", "running", "succeeded", "failed"]
RunPhase = Literal["ingest", "retrieve", "plan", "preflight", "report", "done"]

# ---------- indexes ----------

def init_indexes(db: Optional[Database] = None) -> None:
    db = db or get_db()

    col_runs(db).create_index("run_id", unique=True)
    col_runs(db).create_index([("status", 1), ("updated_at", -1)])
    col_runs(db).create_index("lease_expires_at")  # for cleanup/monitoring

    col_events(db).create_index([("run_id", 1), ("ts", 1)])

    col_agent_outputs(db).create_index([("run_id", 1), ("agent", 1), ("kind", 1), ("ts", -1)])

    col_kb_chunks(db).create_index([("doc_id", 1), ("chunk_id", 1)], unique=True)
    col_kb_chunks(db).create_index("doc_id")


# ---------- core ops ----------

def create_run(
    user_request: str,
    *,
    run_id: str,
    inputs: Optional[Dict[str, Any]] = None,
    initial_phase: RunPhase = "ingest",
) -> Dict[str, Any]:
    """
    Creates a run doc in 'queued' status. Caller provides run_id (uuid, etc).
    """
    doc = {
        "run_id": run_id,
        "status": "queued",
        "phase": initial_phase,
        "attempt": 0,
        "claimed_by": None,
        "lease_expires_at": None,
        "user_request": user_request,
        "inputs": inputs or {},
        "outputs": {},
        "error": None,
        "created_at": utcnow(),
        "updated_at": utcnow(),
        "started_at": None,
        "ended_at": None,
    }
    col_runs().insert_one(doc)
    append_event(run_id, "run_created", {"phase": initial_phase, "status": "queued"})
    return doc


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    return col_runs().find_one({"run_id": run_id})


def update_run_phase(
    run_id: str,
    *,
    phase: Optional[RunPhase] = None,
    status: Optional[RunStatus] = None,
    outputs: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None,
    started: bool = False,
    ended: bool = False,
) -> Optional[Dict[str, Any]]:
    sets: Dict[str, Any] = {"updated_at": utcnow()}
    if phase is not None:
        sets["phase"] = phase
    if status is not None:
        sets["status"] = status
    if outputs is not None:
        # merge outputs shallowly
        sets["outputs"] = outputs
    if error is not None:
        sets["error"] = error
    if started:
        sets["started_at"] = utcnow()
    if ended:
        sets["ended_at"] = utcnow()

    doc = col_runs().find_one_and_update(
        {"run_id": run_id},
        {"$set": sets},
        return_document=ReturnDocument.AFTER,
    )
    return doc


def append_event(
    run_id: str,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    agent: Optional[str] = None,
) -> None:
    col_events().insert_one(
        {
            "run_id": run_id,
            "ts": utcnow(),
            "type": event_type,
            "agent": agent,
            "payload": payload or {},
        }
    )


# ---------- atomic claim pattern (multi-agent safe) ----------

def claim_next_run(
    worker_id: str,
    *,
    lease_seconds: int = 120,
    eligible_status: RunStatus = "queued",
) -> Optional[Dict[str, Any]]:
    """
    Atomically claims one run so only one coordinator/worker processes it.
    Uses a time-based lease to recover if a worker dies.
    """
    now = utcnow()
    lease_expires = now + timedelta(seconds=lease_seconds)

    query = {
        "status": eligible_status,
        "$or": [
            {"lease_expires_at": None},
            {"lease_expires_at": {"$lte": now}},  # expired lease
        ],
    }

    update = {
        "$set": {
            "status": "running",
            "claimed_by": worker_id,
            "lease_expires_at": lease_expires,
            "updated_at": now,
        },
        "$inc": {"attempt": 1},
        "$setOnInsert": {"created_at": now},
    }

    doc = col_runs().find_one_and_update(
        query,
        update,
        sort=[("updated_at", 1)],  # oldest first
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        append_event(doc["run_id"], "run_claimed", {"worker_id": worker_id, "lease_seconds": lease_seconds}, agent="coordinator")
    return doc


def renew_lease(run_id: str, worker_id: str, lease_seconds: int = 120) -> bool:
    now = utcnow()
    lease_expires = now + timedelta(seconds=lease_seconds)
    res = col_runs().update_one(
        {"run_id": run_id, "claimed_by": worker_id, "status": "running"},
        {"$set": {"lease_expires_at": lease_expires, "updated_at": now}},
    )
    return res.modified_count == 1


def release_run(
    run_id: str,
    worker_id: str,
    *,
    status: Optional[RunStatus] = None,
    phase: Optional[RunPhase] = None,
    error: Optional[Dict[str, Any]] = None,
    ended: bool = False,
) -> Optional[Dict[str, Any]]:
    sets: Dict[str, Any] = {"updated_at": utcnow(), "lease_expires_at": None}
    if status is not None:
        sets["status"] = status
    if phase is not None:
        sets["phase"] = phase
    if error is not None:
        sets["error"] = error
    if ended:
        sets["ended_at"] = utcnow()

    doc = col_runs().find_one_and_update(
        {"run_id": run_id, "claimed_by": worker_id},
        {"$set": sets},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        append_event(run_id, "run_released", {"worker_id": worker_id, "status": status, "phase": phase}, agent="coordinator")
    return doc


# ---------- agent outputs ----------

def upsert_agent_output(
    run_id: str,
    agent: str,
    kind: str,
    data: Dict[str, Any],
    *,
    schema_version: str = "0.1",
) -> None:
    doc = {
        "run_id": run_id,
        "agent": agent,
        "kind": kind,
        "data": data,
        "schema_version": schema_version,
        "ts": utcnow(),
    }
    col_agent_outputs().insert_one(doc)
    append_event(run_id, "agent_output_written", {"agent": agent, "kind": kind, "schema_version": schema_version}, agent=agent)


# ---------- KB chunk upserts ----------

def upsert_kb_chunks(doc_id: str, chunks: List[Dict[str, Any]]) -> None:
    """
    chunks: [{chunk_id:int, text:str, meta:dict, embedding:list[float], embedding_model:str}]
    """
    c = col_kb_chunks()
    now = utcnow()
    for ch in chunks:
        chunk_id = int(ch["chunk_id"])
        update = {
            "$set": {
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "text": ch["text"],
                "meta": ch.get("meta", {}),
                "embedding": ch.get("embedding"),
                "embedding_model": ch.get("embedding_model"),
                "created_at": ch.get("created_at", now),
            }
        }
        c.update_one({"doc_id": doc_id, "chunk_id": chunk_id}, update, upsert=True)
```

---

## 4) Code: `scripts/init_db.py`

```python
from src.persistence.mongo import init_indexes, get_db

if __name__ == "__main__":
    init_indexes(get_db())
    print("✅ MongoDB initialized: indexes created/verified.")
```

Run:

```bash
python scripts/init_db.py
```

---

## 5) Optional: Atlas Vector Search Index JSON (create in Atlas UI)

If you want vector search over `kb_chunks.embedding`, create a Vector Search index in Atlas on collection `kb_chunks` with something like:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1024,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "doc_id"
    }
  ]
}
```

**Note:** set `numDimensions` to match your Voyage embedding size (depends on model).

---

## 6) Minimal “how agents use this”

* Coordinator:

  * `claim_next_run(worker_id)`
  * `append_event(run_id, "phase_started", ...)`
  * call planner → `upsert_agent_output(... kind="plan")`
  * etc.
  * `release_run(... status="succeeded", phase="done", ended=True)`

This is enough to demo multi-agent durable coordination with Mongo as the context engine.

If you want, paste your current repo layout and I’ll drop these files into the exact paths you’re using (and add a tiny `make_run_id()` helper + FastAPI dependency injection snippet).

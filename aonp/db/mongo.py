"""
MongoDB persistence for integrated OpenMC + Agent workflow.

Schema:
- studies: Deduplicated OpenMC study specifications
- runs: Hybrid execution state (OpenMC phases + agent coordination)
- summaries: OpenMC keff results
- events: Audit log
- agent_outputs: Optional agent data
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Literal, Dict, List

from dotenv import load_dotenv
from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.database import Database

# ---------- env / client ----------

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "aonp_db")

if not MONGODB_URI:
    raise RuntimeError("Missing MONGODB_URI in environment/.env")

_client: Optional[MongoClient] = None


def utcnow() -> datetime:
    """Get current UTC timestamp with timezone awareness."""
    return datetime.now(timezone.utc)


def get_client() -> MongoClient:
    """Get singleton MongoDB client."""
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URI, tz_aware=True)
    return _client


def get_db() -> Database:
    """Get AONP database."""
    return get_client()[MONGODB_DB]


# ---------- collections ----------

def col_studies(db: Optional[Database] = None) -> Collection:
    """OpenMC study specifications (deduplicated by spec_hash)."""
    if db is None:
        db = get_db()
    return db["studies"]


def col_runs(db: Optional[Database] = None) -> Collection:
    """Hybrid: OpenMC phases + agent coordination."""
    if db is None:
        db = get_db()
    return db["runs"]


def col_summaries(db: Optional[Database] = None) -> Collection:
    """OpenMC keff results."""
    if db is None:
        db = get_db()
    return db["summaries"]


def col_events(db: Optional[Database] = None) -> Collection:
    """Append-only audit log."""
    if db is None:
        db = get_db()
    return db["events"]


def col_agent_outputs(db: Optional[Database] = None) -> Collection:
    """Optional agent outputs."""
    if db is None:
        db = get_db()
    return db["agent_outputs"]


# ---------- type definitions ----------

RunStatus = Literal["queued", "running", "succeeded", "failed"]
RunPhase = Literal["bundle", "execute", "extract", "done"]


# ---------- indexes ----------

def init_indexes(db: Optional[Database] = None) -> None:
    """Create all required indexes."""
    if db is None:
        db = get_db()
    
    # studies collection
    col_studies(db).create_index("spec_hash", unique=True)
    col_studies(db).create_index("created_at")
    
    # runs collection
    col_runs(db).create_index("run_id", unique=True)
    col_runs(db).create_index([("status", 1), ("created_at", -1)])
    col_runs(db).create_index([("spec_hash", 1), ("created_at", -1)])
    col_runs(db).create_index("lease_expires_at")  # for claim pattern
    col_runs(db).create_index([("phase", 1), ("status", 1)])
    
    # summaries collection
    col_summaries(db).create_index("run_id", unique=True)
    col_summaries(db).create_index("extracted_at")
    
    # events collection
    col_events(db).create_index([("run_id", 1), ("ts", 1)])
    col_events(db).create_index([("type", 1), ("ts", -1)])
    
    # agent_outputs collection
    col_agent_outputs(db).create_index([("run_id", 1), ("agent", 1), ("kind", 1), ("ts", -1)])


# ---------- study operations ----------

def upsert_study(spec_hash: str, canonical_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upsert a study specification (deduplicated by spec_hash).
    
    Args:
        spec_hash: Unique hash of canonical study spec
        canonical_spec: Full StudySpec as dict
        
    Returns:
        The study document
    """
    doc = col_studies().find_one_and_update(
        {"spec_hash": spec_hash},
        {
            "$setOnInsert": {
                "spec_hash": spec_hash,
                "canonical_spec": canonical_spec,
                "created_at": utcnow(),
            }
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc


def get_study_by_hash(spec_hash: str) -> Optional[Dict[str, Any]]:
    """Get study by spec_hash."""
    return col_studies().find_one({"spec_hash": spec_hash})


# ---------- run operations ----------

def create_run(
    run_id: str,
    spec_hash: str,
    *,
    initial_phase: RunPhase = "bundle",
    initial_status: RunStatus = "queued",
) -> Dict[str, Any]:
    """
    Create a new run in the database.
    
    Args:
        run_id: Unique run identifier (e.g., run_abc123xyz)
        spec_hash: Links to studies collection
        initial_phase: Starting phase (default: bundle)
        initial_status: Starting status (default: queued)
        
    Returns:
        The created run document
    """
    now = utcnow()
    doc = {
        "run_id": run_id,
        "spec_hash": spec_hash,
        "status": initial_status,
        "phase": initial_phase,
        "claimed_by": None,
        "lease_expires_at": None,
        "artifacts": {
            "bundle_path": None,
            "statepoint_path": None,
            "parquet_path": None,
        },
        "created_at": now,
        "started_at": None,
        "ended_at": None,
    }
    col_runs().insert_one(doc)
    append_event(run_id, "run_created", {"phase": initial_phase, "status": initial_status})
    return doc


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Get run by run_id."""
    return col_runs().find_one({"run_id": run_id})


def update_run_status(
    run_id: str,
    status: RunStatus,
    *,
    error: Optional[Dict[str, Any]] = None,
    ended: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Update run status.
    
    Args:
        run_id: Run identifier
        status: New status
        error: Optional error info {type, message, traceback}
        ended: Whether to set ended_at timestamp
        
    Returns:
        Updated run document
    """
    sets: Dict[str, Any] = {"status": status}
    if error is not None:
        sets["error"] = error
    if ended:
        sets["ended_at"] = utcnow()
    
    doc = col_runs().find_one_and_update(
        {"run_id": run_id},
        {"$set": sets},
        return_document=ReturnDocument.AFTER,
    )
    
    if doc:
        append_event(run_id, "status_changed", {"status": status, "error": error})
    
    return doc


def update_run_phase(
    run_id: str,
    phase: RunPhase,
    *,
    status: Optional[RunStatus] = None,
    started: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Update run phase (and optionally status).
    
    Args:
        run_id: Run identifier
        phase: New phase
        status: Optional new status
        started: Whether to set started_at timestamp
        
    Returns:
        Updated run document
    """
    sets: Dict[str, Any] = {"phase": phase}
    if status is not None:
        sets["status"] = status
    if started:
        sets["started_at"] = utcnow()
    
    doc = col_runs().find_one_and_update(
        {"run_id": run_id},
        {"$set": sets},
        return_document=ReturnDocument.AFTER,
    )
    
    if doc:
        append_event(run_id, "phase_changed", {"phase": phase, "status": status})
    
    return doc


def update_run_artifacts(
    run_id: str,
    artifacts: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Update run artifacts (bundle_path, statepoint_path, parquet_path).
    
    Args:
        run_id: Run identifier
        artifacts: Dict with artifact paths
        
    Returns:
        Updated run document
    """
    doc = col_runs().find_one_and_update(
        {"run_id": run_id},
        {"$set": {"artifacts": artifacts}},
        return_document=ReturnDocument.AFTER,
    )
    
    if doc:
        append_event(run_id, "artifacts_updated", artifacts)
    
    return doc


# ---------- atomic claim pattern (multi-worker safe) ----------

def claim_next_run(
    worker_id: str,
    *,
    lease_seconds: int = 300,
    eligible_status: RunStatus = "queued",
    eligible_phase: Optional[RunPhase] = None,
) -> Optional[Dict[str, Any]]:
    """
    Atomically claim the next available run.
    
    Uses a time-based lease to recover if worker dies.
    
    Args:
        worker_id: Identifier for the claiming worker
        lease_seconds: How long to hold the lease (default: 5 minutes)
        eligible_status: Which status to claim (default: queued)
        eligible_phase: Optional phase filter
        
    Returns:
        Claimed run document or None if no runs available
    """
    now = utcnow()
    lease_expires = now + timedelta(seconds=lease_seconds)
    
    query: Dict[str, Any] = {
        "status": eligible_status,
        "$or": [
            {"lease_expires_at": None},
            {"lease_expires_at": {"$lte": now}},  # expired lease
        ],
    }
    
    if eligible_phase is not None:
        query["phase"] = eligible_phase
    
    update = {
        "$set": {
            "status": "running",
            "claimed_by": worker_id,
            "lease_expires_at": lease_expires,
        },
        "$setOnInsert": {"created_at": now},
    }
    
    doc = col_runs().find_one_and_update(
        query,
        update,
        sort=[("created_at", 1)],  # oldest first (FIFO)
        return_document=ReturnDocument.AFTER,
    )
    
    if doc:
        append_event(
            doc["run_id"],
            "run_claimed",
            {"worker_id": worker_id, "lease_seconds": lease_seconds},
            agent=worker_id,
        )
    
    return doc


def renew_lease(run_id: str, worker_id: str, lease_seconds: int = 300) -> bool:
    """
    Renew the lease on a claimed run.
    
    Args:
        run_id: Run identifier
        worker_id: Worker that owns the lease
        lease_seconds: New lease duration
        
    Returns:
        True if renewed successfully
    """
    now = utcnow()
    lease_expires = now + timedelta(seconds=lease_seconds)
    
    res = col_runs().update_one(
        {"run_id": run_id, "claimed_by": worker_id, "status": "running"},
        {"$set": {"lease_expires_at": lease_expires}},
    )
    
    if res.modified_count == 1:
        append_event(run_id, "lease_renewed", {"worker_id": worker_id, "lease_seconds": lease_seconds})
    
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
    """
    Release a claimed run (clear lease).
    
    Args:
        run_id: Run identifier
        worker_id: Worker releasing the run
        status: Optional new status
        phase: Optional new phase
        error: Optional error info
        ended: Whether to set ended_at
        
    Returns:
        Updated run document
    """
    sets: Dict[str, Any] = {"lease_expires_at": None}
    
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
        append_event(
            run_id,
            "run_released",
            {"worker_id": worker_id, "status": status, "phase": phase},
            agent=worker_id,
        )
    
    return doc


# ---------- summary operations ----------

def insert_summary(
    run_id: str,
    keff: float,
    keff_std: float,
    keff_uncertainty_pcm: float,
    n_batches: int,
    n_inactive: int,
    n_particles: int,
) -> Dict[str, Any]:
    """
    Insert OpenMC summary results.
    
    Args:
        run_id: Run identifier
        keff: k-effective value
        keff_std: Standard deviation of k-eff
        keff_uncertainty_pcm: Uncertainty in pcm (parts per hundred thousand)
        n_batches: Number of batches
        n_inactive: Number of inactive batches
        n_particles: Particles per batch
        
    Returns:
        The inserted summary document
    """
    doc = {
        "run_id": run_id,
        "keff": keff,
        "keff_std": keff_std,
        "keff_uncertainty_pcm": keff_uncertainty_pcm,
        "n_batches": n_batches,
        "n_inactive": n_inactive,
        "n_particles": n_particles,
        "extracted_at": utcnow(),
    }
    
    col_summaries().insert_one(doc)
    append_event(run_id, "summary_extracted", {"keff": keff, "keff_std": keff_std})
    
    return doc


def get_summary(run_id: str) -> Optional[Dict[str, Any]]:
    """Get summary by run_id."""
    return col_summaries().find_one({"run_id": run_id})


# ---------- event operations ----------

def append_event(
    run_id: str,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    agent: Optional[str] = None,
) -> None:
    """
    Append an event to the audit log.
    
    Args:
        run_id: Run identifier
        event_type: Event type (e.g., "phase_started", "error", "summary_extracted")
        payload: Event data
        agent: Optional agent/worker identifier
    """
    col_events().insert_one(
        {
            "run_id": run_id,
            "ts": utcnow(),
            "type": event_type,
            "agent": agent,
            "payload": payload or {},
        }
    )


def get_events(
    run_id: str,
    *,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get events for a run.
    
    Args:
        run_id: Run identifier
        event_type: Optional filter by event type
        limit: Max events to return
        
    Returns:
        List of event documents
    """
    query: Dict[str, Any] = {"run_id": run_id}
    if event_type is not None:
        query["type"] = event_type
    
    return list(
        col_events()
        .find(query)
        .sort("ts", -1)
        .limit(limit)
    )


# ---------- agent outputs (optional) ----------

def upsert_agent_output(
    run_id: str,
    agent: str,
    kind: str,
    data: Dict[str, Any],
    *,
    schema_version: str = "0.1",
) -> None:
    """
    Store structured agent output.
    
    Args:
        run_id: Run identifier
        agent: Agent name
        kind: Output kind (e.g., "plan", "report", "analysis")
        data: Structured data
        schema_version: Schema version string
    """
    doc = {
        "run_id": run_id,
        "agent": agent,
        "kind": kind,
        "data": data,
        "schema_version": schema_version,
        "ts": utcnow(),
    }
    
    col_agent_outputs().insert_one(doc)
    append_event(
        run_id,
        "agent_output_written",
        {"agent": agent, "kind": kind, "schema_version": schema_version},
        agent=agent,
    )


def get_agent_outputs(
    run_id: str,
    *,
    agent: Optional[str] = None,
    kind: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get agent outputs for a run.
    
    Args:
        run_id: Run identifier
        agent: Optional filter by agent
        kind: Optional filter by kind
        
    Returns:
        List of agent output documents
    """
    query: Dict[str, Any] = {"run_id": run_id}
    if agent is not None:
        query["agent"] = agent
    if kind is not None:
        query["kind"] = kind
    
    return list(
        col_agent_outputs()
        .find(query)
        .sort("ts", -1)
    )


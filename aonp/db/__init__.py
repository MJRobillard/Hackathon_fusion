"""
MongoDB persistence layer for AONP.

Provides collections for:
- studies: OpenMC study specifications (deduplicated by spec_hash)
- runs: Hybrid OpenMC execution + agent coordination state
- summaries: OpenMC keff results and metrics
- events: Append-only audit log
- agent_outputs: Optional agent data storage
"""

from aonp.db.mongo import (
    # Connection
    get_client,
    get_db,
    init_indexes,
    
    # Collections
    col_studies,
    col_runs,
    col_summaries,
    col_events,
    col_agent_outputs,
    
    # Study operations
    upsert_study,
    get_study_by_hash,
    
    # Run operations
    create_run,
    get_run,
    update_run_status,
    update_run_phase,
    update_run_artifacts,
    claim_next_run,
    renew_lease,
    release_run,
    
    # Summary operations
    insert_summary,
    get_summary,
    
    # Event operations
    append_event,
    get_events,
    
    # Agent operations
    upsert_agent_output,
    get_agent_outputs,
)

__all__ = [
    "get_client",
    "get_db",
    "init_indexes",
    "col_studies",
    "col_runs",
    "col_summaries",
    "col_events",
    "col_agent_outputs",
    "upsert_study",
    "get_study_by_hash",
    "create_run",
    "get_run",
    "update_run_status",
    "update_run_phase",
    "update_run_artifacts",
    "claim_next_run",
    "renew_lease",
    "release_run",
    "insert_summary",
    "get_summary",
    "append_event",
    "get_events",
    "upsert_agent_output",
    "get_agent_outputs",
]


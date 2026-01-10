#!/usr/bin/env python3
"""
Populate MongoDB with sample data for testing and demonstration.

Creates:
- 3 studies (different reactor configurations)
- 10 runs (various states: queued, running, succeeded, failed)
- Summaries for completed runs
- Event logs for all runs
- Sample agent outputs

Usage:
    python scripts/populate_sample_data.py
    python scripts/populate_sample_data.py --clear  (clear existing data first)
"""

import sys
from pathlib import Path
import argparse
import random
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aonp.db import (
    get_db,
    upsert_study,
    create_run,
    update_run_phase,
    update_run_status,
    update_run_artifacts,
    insert_summary,
    append_event,
    upsert_agent_output,
    claim_next_run,
    release_run,
    col_studies,
    col_runs,
    col_summaries,
    col_events,
    col_agent_outputs,
)
from aonp.db.mongo import utcnow


def clear_all_data():
    """Clear all existing data from collections."""
    print("Clearing existing data...")
    db = get_db()
    
    counts = {
        "studies": col_studies(db).delete_many({}).deleted_count,
        "runs": col_runs(db).delete_many({}).deleted_count,
        "summaries": col_summaries(db).delete_many({}).deleted_count,
        "events": col_events(db).delete_many({}).deleted_count,
        "agent_outputs": col_agent_outputs(db).delete_many({}).deleted_count,
    }
    
    print(f"  Deleted {counts['studies']} studies")
    print(f"  Deleted {counts['runs']} runs")
    print(f"  Deleted {counts['summaries']} summaries")
    print(f"  Deleted {counts['events']} events")
    print(f"  Deleted {counts['agent_outputs']} agent outputs")
    print()


def create_sample_studies():
    """Create sample study specifications."""
    print("Creating sample studies...")
    
    studies = [
        {
            "spec_hash": "demo_pincell_uo2_4pct",
            "canonical_spec": {
                "name": "UO2 Pincell 4% Enrichment",
                "description": "Standard UO2 fuel pincell at 4% enrichment",
                "geometry": {
                    "type": "pincell",
                    "fuel_radius": 0.39218,
                    "clad_inner_radius": 0.40005,
                    "clad_outer_radius": 0.45720,
                    "pitch": 1.26
                },
                "materials": {
                    "fuel": {
                        "type": "UO2",
                        "enrichment": 4.0,
                        "density": 10.4
                    },
                    "clad": {
                        "type": "Zircaloy-4",
                        "density": 6.55
                    },
                    "moderator": {
                        "type": "H2O",
                        "density": 0.7,
                        "temperature": 600
                    }
                },
                "settings": {
                    "batches": 100,
                    "inactive": 20,
                    "particles": 10000
                },
                "nuclear_data": {
                    "library": "endfb71",
                    "temperatures": [600, 900]
                }
            }
        },
        {
            "spec_hash": "demo_pincell_uo2_5pct",
            "canonical_spec": {
                "name": "UO2 Pincell 5% Enrichment",
                "description": "Higher enrichment UO2 fuel pincell",
                "geometry": {
                    "type": "pincell",
                    "fuel_radius": 0.39218,
                    "clad_inner_radius": 0.40005,
                    "clad_outer_radius": 0.45720,
                    "pitch": 1.26
                },
                "materials": {
                    "fuel": {
                        "type": "UO2",
                        "enrichment": 5.0,
                        "density": 10.4
                    },
                    "clad": {
                        "type": "Zircaloy-4",
                        "density": 6.55
                    },
                    "moderator": {
                        "type": "H2O",
                        "density": 0.7,
                        "temperature": 600
                    }
                },
                "settings": {
                    "batches": 200,
                    "inactive": 40,
                    "particles": 20000
                },
                "nuclear_data": {
                    "library": "endfb71",
                    "temperatures": [600, 900]
                }
            }
        },
        {
            "spec_hash": "demo_pincell_mox",
            "canonical_spec": {
                "name": "MOX Pincell",
                "description": "Mixed-oxide fuel pincell",
                "geometry": {
                    "type": "pincell",
                    "fuel_radius": 0.39218,
                    "clad_inner_radius": 0.40005,
                    "clad_outer_radius": 0.45720,
                    "pitch": 1.26
                },
                "materials": {
                    "fuel": {
                        "type": "MOX",
                        "pu_content": 8.0,
                        "density": 10.3
                    },
                    "clad": {
                        "type": "Zircaloy-4",
                        "density": 6.55
                    },
                    "moderator": {
                        "type": "H2O",
                        "density": 0.7,
                        "temperature": 600
                    }
                },
                "settings": {
                    "batches": 150,
                    "inactive": 30,
                    "particles": 15000
                },
                "nuclear_data": {
                    "library": "endfb71",
                    "temperatures": [600, 900]
                }
            }
        }
    ]
    
    for study_data in studies:
        study = upsert_study(study_data["spec_hash"], study_data["canonical_spec"])
        print(f"  Created: {study_data['canonical_spec']['name']} ({study_data['spec_hash']})")
    
    print()
    return [s["spec_hash"] for s in studies]


def create_sample_runs(spec_hashes):
    """Create sample runs in various states."""
    print("Creating sample runs...")
    
    runs_data = [
        # Completed successful runs
        {
            "run_id": "run_demo_001",
            "spec_hash": spec_hashes[0],
            "status": "succeeded",
            "phase": "done",
            "keff": 1.18234,
            "keff_std": 0.00145,
            "scenario": "completed"
        },
        {
            "run_id": "run_demo_002",
            "spec_hash": spec_hashes[0],
            "status": "succeeded",
            "phase": "done",
            "keff": 1.18189,
            "keff_std": 0.00152,
            "scenario": "completed"
        },
        {
            "run_id": "run_demo_003",
            "spec_hash": spec_hashes[1],
            "status": "succeeded",
            "phase": "done",
            "keff": 1.24567,
            "keff_std": 0.00123,
            "scenario": "completed"
        },
        {
            "run_id": "run_demo_004",
            "spec_hash": spec_hashes[2],
            "status": "succeeded",
            "phase": "done",
            "keff": 1.15678,
            "keff_std": 0.00198,
            "scenario": "completed"
        },
        # Failed run
        {
            "run_id": "run_demo_005",
            "spec_hash": spec_hashes[1],
            "status": "failed",
            "phase": "execute",
            "error": {
                "type": "ConvergenceError",
                "message": "Source distribution failed to converge after 100 batches",
                "traceback": "Traceback (most recent call last):\n  File simulation.py..."
            },
            "scenario": "failed"
        },
        # Running runs
        {
            "run_id": "run_demo_006",
            "spec_hash": spec_hashes[0],
            "status": "running",
            "phase": "execute",
            "scenario": "running"
        },
        {
            "run_id": "run_demo_007",
            "spec_hash": spec_hashes[2],
            "status": "running",
            "phase": "extract",
            "scenario": "running"
        },
        # Queued runs
        {
            "run_id": "run_demo_008",
            "spec_hash": spec_hashes[1],
            "status": "queued",
            "phase": "bundle",
            "scenario": "queued"
        },
        {
            "run_id": "run_demo_009",
            "spec_hash": spec_hashes[2],
            "status": "queued",
            "phase": "bundle",
            "scenario": "queued"
        },
        {
            "run_id": "run_demo_010",
            "spec_hash": spec_hashes[0],
            "status": "queued",
            "phase": "bundle",
            "scenario": "queued"
        },
    ]
    
    for run_data in runs_data:
        scenario = run_data.pop("scenario")
        run_id = run_data["run_id"]
        spec_hash = run_data["spec_hash"]
        status = run_data["status"]
        phase = run_data["phase"]
        
        # Create run
        run = create_run(
            run_id=run_id,
            spec_hash=spec_hash,
            initial_phase="bundle",
            initial_status="queued"
        )
        
        print(f"  Created: {run_id} ({status}/{phase})")
        
        # Set up based on scenario
        if scenario == "completed":
            # Simulate completion
            update_run_phase(run_id, phase="execute", status="running", started=True)
            append_event(run_id, "execution_started", {"worker": "demo-worker-01"})
            
            update_run_artifacts(run_id, {
                "bundle_path": f"/data/runs/{run_id}",
                "statepoint_path": f"/data/runs/{run_id}/statepoint.100.h5",
                "parquet_path": f"/data/runs/{run_id}/summary.parquet"
            })
            
            # Extract phase
            update_run_phase(run_id, phase="extract", status="running")
            append_event(run_id, "extraction_started", {})
            
            # Insert summary
            insert_summary(
                run_id=run_id,
                keff=run_data["keff"],
                keff_std=run_data["keff_std"],
                keff_uncertainty_pcm=run_data["keff_std"] * 100000,  # Convert to pcm
                n_batches=100,
                n_inactive=20,
                n_particles=10000
            )
            
            # Complete
            update_run_phase(run_id, phase="done", status="succeeded")
            update_run_status(run_id, status="succeeded", ended=True)
            append_event(run_id, "run_completed", {
                "keff": run_data["keff"],
                "elapsed_seconds": random.randint(45, 120)
            })
            
        elif scenario == "failed":
            # Simulate failure
            update_run_phase(run_id, phase="execute", status="running", started=True)
            append_event(run_id, "execution_started", {"worker": "demo-worker-02"})
            
            update_run_artifacts(run_id, {
                "bundle_path": f"/data/runs/{run_id}",
                "statepoint_path": None,
                "parquet_path": None
            })
            
            # Fail
            update_run_status(
                run_id=run_id,
                status="failed",
                error=run_data["error"],
                ended=True
            )
            append_event(run_id, "execution_failed", run_data["error"])
            
        elif scenario == "running":
            # Simulate in-progress
            update_run_phase(run_id, phase=phase, status="running", started=True)
            append_event(run_id, f"{phase}_started", {"worker": "demo-worker-01"})
            
            update_run_artifacts(run_id, {
                "bundle_path": f"/data/runs/{run_id}",
                "statepoint_path": f"/data/runs/{run_id}/statepoint.100.h5" if phase == "extract" else None,
                "parquet_path": None
            })
            
        elif scenario == "queued":
            # Keep as queued
            update_run_artifacts(run_id, {
                "bundle_path": f"/data/runs/{run_id}",
                "statepoint_path": None,
                "parquet_path": None
            })
    
    print()
    return [r["run_id"] for r in runs_data]


def create_sample_agent_outputs(run_ids):
    """Create sample agent outputs."""
    print("Creating sample agent outputs...")
    
    # Add agent output for first successful run
    upsert_agent_output(
        run_id=run_ids[0],
        agent="planner",
        kind="simulation_plan",
        data={
            "objectives": [
                "Calculate k-effective for UO2 pincell",
                "Verify convergence within 150 pcm uncertainty"
            ],
            "parameters": {
                "batches": 100,
                "particles": 10000
            },
            "estimated_runtime_seconds": 60
        },
        schema_version="0.1"
    )
    print(f"  Added planner output for {run_ids[0]}")
    
    upsert_agent_output(
        run_id=run_ids[0],
        agent="analyzer",
        kind="result_analysis",
        data={
            "keff_value": 1.18234,
            "uncertainty_pcm": 145,
            "meets_criteria": True,
            "confidence": "high",
            "recommendations": [
                "Results show good convergence",
                "Uncertainty within acceptable range",
                "Ready for production use"
            ]
        },
        schema_version="0.1"
    )
    print(f"  Added analyzer output for {run_ids[0]}")
    
    # Add agent output for failed run
    upsert_agent_output(
        run_id=run_ids[4],  # Failed run
        agent="diagnostics",
        kind="failure_analysis",
        data={
            "error_type": "ConvergenceError",
            "likely_causes": [
                "Insufficient number of inactive batches",
                "Complex geometry causing slow convergence",
                "Initial source distribution poor"
            ],
            "recommended_fixes": [
                "Increase inactive batches to 50",
                "Use larger initial source",
                "Verify geometry definitions"
            ]
        },
        schema_version="0.1"
    )
    print(f"  Added diagnostics output for {run_ids[4]}")
    
    print()


def print_summary():
    """Print summary of created data."""
    print("=" * 70)
    print("Sample Data Summary")
    print("=" * 70)
    
    db = get_db()
    
    studies_count = col_studies(db).count_documents({})
    runs_count = col_runs(db).count_documents({})
    summaries_count = col_summaries(db).count_documents({})
    events_count = col_events(db).count_documents({})
    agent_outputs_count = col_agent_outputs(db).count_documents({})
    
    print(f"Studies:        {studies_count}")
    print(f"Runs:           {runs_count}")
    print(f"Summaries:      {summaries_count}")
    print(f"Events:         {events_count}")
    print(f"Agent Outputs:  {agent_outputs_count}")
    
    print()
    print("Run Status Breakdown:")
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_counts = list(col_runs(db).aggregate(pipeline))
    for item in status_counts:
        print(f"  {item['_id']:12s} {item['count']}")
    
    print()
    print("Run Phase Breakdown:")
    pipeline = [
        {"$group": {"_id": "$phase", "count": {"$sum": 1}}}
    ]
    phase_counts = list(col_runs(db).aggregate(pipeline))
    for item in phase_counts:
        print(f"  {item['_id']:12s} {item['count']}")
    
    print()
    print("Sample Queries:")
    print("  - List all runs: db.runs.find()")
    print("  - Get queued runs: db.runs.find({status: 'queued'})")
    print("  - Get study details: db.studies.find()")
    print("  - View events: db.events.find().sort({ts: -1})")
    print()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Populate MongoDB with sample data")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before populating"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("MongoDB Sample Data Populator")
    print("=" * 70)
    print()
    
    try:
        # Test connection
        db = get_db()
        db.command('ping')
        print(f"Connected to MongoDB: {db.name}")
        print()
        
        # Clear if requested
        if args.clear:
            clear_all_data()
        
        # Create sample data
        spec_hashes = create_sample_studies()
        run_ids = create_sample_runs(spec_hashes)
        create_sample_agent_outputs(run_ids)
        
        # Print summary
        print_summary()
        
        print("SUCCESS: Sample data created!")
        print()
        print("Next steps:")
        print("  - View in MongoDB Atlas dashboard")
        print("  - Query with: python -c \"from aonp.db import *; ...\"")
        print("  - Test API: uvicorn aonp.api.main_with_mongo:app --reload")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


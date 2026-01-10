"""
FastAPI application for AONP with MongoDB integration.

Example showing how to integrate MongoDB persistence with existing API endpoints.
This file demonstrates the integration pattern - you can merge these changes into main.py.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from aonp.schemas.study import StudySpec
from aonp.core.bundler import create_run_bundle
from aonp.runner.entrypoint import run_simulation

# MongoDB imports
from aonp.db import (
    upsert_study,
    create_run,
    get_run,
    update_run_phase,
    update_run_status,
    update_run_artifacts,
    get_summary,
    get_events,
    append_event,
)


app = FastAPI(
    title="AONP API with MongoDB",
    description="Agent-Orchestrated Neutronics Platform with durable state tracking",
    version="0.1.0"
)


class ValidationResponse(BaseModel):
    """Response for study validation."""
    validation_status: str
    canonical_hash: str
    study_name: str
    nuclear_data_library: str
    error: Optional[str] = None


class RunResponse(BaseModel):
    """Response for run submission."""
    run_id: str
    spec_hash: str
    status: str
    phase: str
    run_directory: str


class RunStatusResponse(BaseModel):
    """Response for run status query."""
    run_id: str
    spec_hash: str
    status: str
    phase: str
    created_at: str
    started_at: Optional[str]
    ended_at: Optional[str]
    artifacts: Dict[str, Any]
    summary: Optional[Dict[str, Any]] = None
    recent_events: list[Dict[str, Any]] = []


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AONP API",
        "version": "0.1.0",
        "description": "High-integrity neutronics simulation platform with MongoDB",
        "endpoints": {
            "validate": "/validate - Validate study YAML",
            "run": "/run - Submit simulation run",
            "runs": "/runs/{run_id} - Get run status",
            "execute": "/runs/{run_id}/execute - Execute a run",
            "docs": "/docs - API documentation"
        }
    }


@app.post("/validate", response_model=ValidationResponse)
async def validate_study(file: UploadFile = File(...)):
    """
    Validate a study YAML file and return its canonical hash.
    
    Optionally stores the study specification in MongoDB for deduplication.
    """
    try:
        # Read and validate
        contents = await file.read()
        data = yaml.safe_load(contents)
        study = StudySpec(**data)
        
        spec_hash = study.get_canonical_hash()
        
        # Store in MongoDB (deduplicated by spec_hash)
        upsert_study(
            spec_hash=spec_hash,
            canonical_spec=study.model_dump()
        )
        
        return ValidationResponse(
            validation_status="valid",
            canonical_hash=spec_hash,
            study_name=study.name,
            nuclear_data_library=study.nuclear_data.library
        )
        
    except Exception as e:
        return ValidationResponse(
            validation_status="invalid",
            canonical_hash="",
            study_name="",
            nuclear_data_library="",
            error=str(e)
        )


@app.post("/run", response_model=RunResponse)
async def submit_run(file: UploadFile = File(...)):
    """
    Submit a simulation run with MongoDB tracking.
    
    Creates:
    1. Study entry in MongoDB (deduplicated)
    2. Run bundle on filesystem
    3. Run entry in MongoDB (queued state)
    """
    try:
        # Read and validate study
        contents = await file.read()
        data = yaml.safe_load(contents)
        study = StudySpec(**data)
        
        spec_hash = study.get_canonical_hash()
        
        # 1. Store study in MongoDB
        upsert_study(
            spec_hash=spec_hash,
            canonical_spec=study.model_dump()
        )
        
        # 2. Create run bundle on filesystem
        run_dir, _ = create_run_bundle(study)
        run_id = run_dir.name
        
        # 3. Create run in MongoDB (queued state)
        run_doc = create_run(
            run_id=run_id,
            spec_hash=spec_hash,
            initial_phase="bundle",
            initial_status="queued"
        )
        
        # 4. Update artifacts with bundle path
        update_run_artifacts(
            run_id=run_id,
            artifacts={
                "bundle_path": str(run_dir),
                "statepoint_path": None,
                "parquet_path": None,
            }
        )
        
        return RunResponse(
            run_id=run_id,
            spec_hash=spec_hash,
            status=run_doc["status"],
            phase=run_doc["phase"],
            run_directory=str(run_dir)
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/runs/{run_id}/execute")
async def execute_run(run_id: str):
    """
    Execute a simulation run with MongoDB state tracking.
    
    Updates run phase through: bundle → execute → extract → done
    """
    try:
        # Get run from MongoDB
        run_doc = get_run(run_id)
        
        if not run_doc:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        
        run_dir = Path("runs") / run_id
        
        if not run_dir.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Run directory not found: {run_dir}"
            )
        
        # Update to execute phase
        update_run_phase(
            run_id=run_id,
            phase="execute",
            status="running",
            started=True
        )
        
        try:
            # Execute simulation (blocking)
            append_event(
                run_id=run_id,
                event_type="execution_started",
                payload={"run_dir": str(run_dir)}
            )
            
            exit_code = run_simulation(run_dir)
            
            if exit_code != 0:
                # Failed execution
                update_run_status(
                    run_id=run_id,
                    status="failed",
                    error={
                        "type": "ExecutionError",
                        "message": f"OpenMC exited with code {exit_code}",
                    },
                    ended=True
                )
                
                return {
                    "run_id": run_id,
                    "status": "failed",
                    "exit_code": exit_code
                }
            
            # Success - update to extract phase
            update_run_phase(
                run_id=run_id,
                phase="extract",
                status="running"
            )
            
            # TODO: Add extraction logic here
            # For now, just mark as done
            
            update_run_phase(
                run_id=run_id,
                phase="done",
                status="succeeded"
            )
            
            update_run_status(
                run_id=run_id,
                status="succeeded",
                ended=True
            )
            
            return {"run_id": run_id, "status": "completed", "phase": "done"}
            
        except Exception as e:
            # Execution error
            update_run_status(
                run_id=run_id,
                status="failed",
                error={
                    "type": type(e).__name__,
                    "message": str(e),
                },
                ended=True
            )
            raise
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/runs/{run_id}")
async def get_run_status(run_id: str):
    """
    Get status and results of a specific run from MongoDB.
    
    Returns:
    - Run state (status, phase, timestamps)
    - Artifacts paths
    - Summary results (if available)
    - Recent events (audit log)
    """
    # Get run from MongoDB
    run_doc = get_run(run_id)
    
    if not run_doc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    # Get summary if available
    summary_doc = get_summary(run_id)
    
    # Get recent events
    events = get_events(run_id, limit=10)
    
    # Format response
    return {
        "run_id": run_doc["run_id"],
        "spec_hash": run_doc["spec_hash"],
        "status": run_doc["status"],
        "phase": run_doc["phase"],
        "created_at": run_doc["created_at"].isoformat() if run_doc["created_at"] else None,
        "started_at": run_doc["started_at"].isoformat() if run_doc.get("started_at") else None,
        "ended_at": run_doc["ended_at"].isoformat() if run_doc.get("ended_at") else None,
        "artifacts": run_doc.get("artifacts", {}),
        "summary": {
            "keff": summary_doc["keff"],
            "keff_std": summary_doc["keff_std"],
            "keff_uncertainty_pcm": summary_doc["keff_uncertainty_pcm"],
            "n_batches": summary_doc["n_batches"],
            "n_inactive": summary_doc["n_inactive"],
            "n_particles": summary_doc["n_particles"],
        } if summary_doc else None,
        "recent_events": [
            {
                "type": e["type"],
                "timestamp": e["ts"].isoformat(),
                "agent": e.get("agent"),
                "payload": e.get("payload", {}),
            }
            for e in events
        ]
    }


@app.get("/runs")
async def list_runs(
    status: Optional[str] = None,
    limit: int = 50
):
    """
    List runs with optional filtering.
    
    Query params:
    - status: Filter by status (queued, running, succeeded, failed)
    - limit: Max results (default: 50)
    """
    from aonp.db import col_runs
    
    query = {}
    if status:
        query["status"] = status
    
    runs = list(
        col_runs()
        .find(query)
        .sort("created_at", -1)
        .limit(limit)
    )
    
    return {
        "count": len(runs),
        "runs": [
            {
                "run_id": r["run_id"],
                "spec_hash": r["spec_hash"],
                "status": r["status"],
                "phase": r["phase"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in runs
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with MongoDB status."""
    import sys
    
    # Check OpenMC
    try:
        import openmc
        openmc_available = True
        openmc_version = openmc.__version__
    except ImportError:
        openmc_available = False
        openmc_version = None
    
    # Check MongoDB
    try:
        from aonp.db import get_db
        db = get_db()
        db.command('ping')
        mongodb_available = True
        mongodb_db = db.name
    except Exception as e:
        mongodb_available = False
        mongodb_db = str(e)
    
    return {
        "status": "healthy",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "openmc_available": openmc_available,
        "openmc_version": openmc_version,
        "mongodb_available": mongodb_available,
        "mongodb_db": mongodb_db,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


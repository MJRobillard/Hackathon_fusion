"""
FastAPI application for AONP.

Provides REST endpoints for:
- Study validation
- Run submission
- Result retrieval
"""

import yaml
import tempfile
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from aonp.schemas.study import StudySpec
from aonp.core.bundler import create_run_bundle
from aonp.runner.entrypoint import run_simulation


app = FastAPI(
    title="AONP API",
    description="Agent-Orchestrated Neutronics Platform",
    version="0.1.0"
)


class ValidationResponse(BaseModel):
    """Response for study validation."""
    validation_status: str
    canonical_hash: str
    study_name: str
    nuclear_data_library: str
    error: str = None


class RunResponse(BaseModel):
    """Response for run submission."""
    run_id: str
    spec_hash: str
    status: str
    run_directory: str


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AONP API",
        "version": "0.1.0",
        "description": "High-integrity neutronics simulation platform",
        "endpoints": {
            "validate": "/validate - Validate study YAML",
            "run": "/run - Submit simulation run",
            "runs": "/runs/{run_id} - Get run status",
            "docs": "/docs - API documentation"
        }
    }


@app.post("/validate", response_model=ValidationResponse)
async def validate_study(file: UploadFile = File(...)):
    """
    Validate a study YAML file and return its canonical hash.
    
    Args:
        file: YAML file containing study specification
        
    Returns:
        Validation status and canonical hash
    """
    try:
        # Read uploaded file
        contents = await file.read()
        data = yaml.safe_load(contents)
        
        # Validate with Pydantic
        study = StudySpec(**data)
        
        return ValidationResponse(
            validation_status="valid",
            canonical_hash=study.get_canonical_hash(),
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
    Submit a simulation run.
    
    Args:
        file: YAML file containing study specification
        
    Returns:
        Run information including run_id and directory
    """
    try:
        # Read and validate study
        contents = await file.read()
        data = yaml.safe_load(contents)
        study = StudySpec(**data)
        
        # Create run bundle
        run_dir, spec_hash = create_run_bundle(study)
        
        return RunResponse(
            run_id=run_dir.name,
            spec_hash=spec_hash,
            status="created",
            run_directory=str(run_dir)
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/run/{run_id}/execute")
async def execute_run(run_id: str):
    """
    Execute a simulation run.
    
    Args:
        run_id: Run identifier
        
    Returns:
        Execution status
    """
    try:
        run_dir = Path("runs") / run_id
        
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        
        # Execute simulation (blocking - consider async/celery for production)
        exit_code = run_simulation(run_dir)
        
        if exit_code == 0:
            return {"run_id": run_id, "status": "completed"}
        else:
            return {"run_id": run_id, "status": "failed", "exit_code": exit_code}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/runs/{run_id}")
async def get_run_status(run_id: str):
    """
    Get status and results of a specific run.
    
    Args:
        run_id: Run identifier
        
    Returns:
        Run status and results (if available)
    """
    import json
    
    run_dir = Path("runs") / run_id
    
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    # Load manifest
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=500, detail="Run manifest not found")
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    # Check for results
    results = None
    summary_path = run_dir / "outputs" / "summary.parquet"
    if summary_path.exists():
        import pandas as pd
        df = pd.read_parquet(summary_path)
        results = df.to_dict('records')
    
    return {
        "run_id": run_id,
        "manifest": manifest,
        "results": results
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    import sys
    
    # Check OpenMC availability
    try:
        import openmc
        openmc_available = True
        openmc_version = openmc.__version__
    except ImportError:
        openmc_available = False
        openmc_version = None
    
    return {
        "status": "healthy",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "openmc_available": openmc_available,
        "openmc_version": openmc_version
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


"""
OpenMC Backend API - Direct access to OpenMC simulation engine

This API provides REST endpoints for:
- Submitting simulations
- Getting results
- Running parameter sweeps
- Querying run history
- Health checks

Runs independently from the agent system.
"""

import os
import sys
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4
import asyncio
import json

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from openmc_adapter import OpenMCAdapter
from aonp.core.bundler import create_run_bundle
from aonp.runner.streaming_runner import StreamingSimulationRunner
from aonp.core.extractor import extract_results

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

MONGODB_URI = os.getenv("MONGO_URI")
API_HOST = os.getenv("OPENMC_API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("OPENMC_API_PORT", 8001))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
RUNS_DIR = Path(os.getenv("OPENMC_RUNS_DIR", "runs"))

# ============================================================================
# STREAMING: RUN EVENT BUS
# ============================================================================


class RunEventBus:
    """Simple pub/sub for OpenMC run streaming events (SSE)."""

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(run_id, []).append(queue)
        return queue

    async def publish(self, run_id: str, event: dict):
        if run_id in self._subscribers:
            for queue in list(self._subscribers[run_id]):
                await queue.put(event)

    async def complete(self, run_id: str):
        if run_id in self._subscribers:
            for queue in list(self._subscribers[run_id]):
                await queue.put(None)

    def unsubscribe(self, run_id: str, queue: asyncio.Queue):
        if run_id in self._subscribers:
            self._subscribers[run_id].remove(queue)
            if not self._subscribers[run_id]:
                del self._subscribers[run_id]


run_event_bus = RunEventBus()


class RunEventPublisher:
    """Thread-safe publisher for run events from sync code."""

    def __init__(self, loop: asyncio.AbstractEventLoop, run_id: str):
        self.loop = loop
        self.run_id = run_id

    def _emit(self, event_type: str, data: dict):
        payload = {
            "type": event_type,
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        asyncio.run_coroutine_threadsafe(run_event_bus.publish(self.run_id, payload), self.loop)

    def log_line(self, line: str):
        self._emit("openmc_log", {"content": line})

    def tool_call(self, tool_name: str, message: str, args: Dict[str, Any]):
        self._emit(
            "tool_call",
            {
                "agent": "OpenMC",
                "tool_name": tool_name,
                "message": message,
                "args": args,
            },
        )

    def tool_result(self, tool_name: str, result: Dict[str, Any]):
        self._emit(
            "tool_result",
            {
                "agent": "OpenMC",
                "tool_name": tool_name,
                "result": result,
            },
        )

    def agent_blip(self, agent: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit an agent-style blip as an SSE event."""
        self._emit(
            "agent_thinking",
            {
                "agent": agent,
                "content": content,
                "metadata": metadata or {},
            },
        )


_BATCH_LINE_RE = re.compile(
    r"^\s*(?P<batch>\d+)\s*/\s*(?P<total>\d+)\s+(?P<keff>-?\d+\.\d+)\s*\+/-\s*(?P<keff_std>\d+\.\d+)"
)


def _stream_execute_openmc(
    spec_dict: Dict[str, Any],
    run_id: str,
    publisher: RunEventPublisher,
) -> Dict[str, Any]:
    """
    Execute OpenMC using the streaming runner and publish:
    - raw log lines (openmc_log)
    - parsed progress tool events (tool_call)
    - final result event (tool_result)
    """
    # Create full spec + bundle
    study = adapter.translate_simple_to_openmc(spec_dict, run_id)
    run_dir, spec_hash = create_run_bundle(study=study, run_id=run_id, base_dir=RUNS_DIR)

    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    log_path = outputs_dir / "openmc_stdout.log"

    publisher.tool_call(
        tool_name="openmc.run",
        message="Starting OpenMC run (streaming stdout)",
        args={"run_id": run_id, "spec_hash": spec_hash, "spec": spec_dict, "run_dir": str(run_dir)},
    )

    last_batch: Optional[int] = None
    total_batches: Optional[int] = None
    last_keff: Optional[float] = None
    last_keff_std: Optional[float] = None

    runner = StreamingSimulationRunner(run_dir)
    with open(log_path, "a", encoding="utf-8") as log_f:
        for line in runner.stream_simulation():
            # Ensure each line ends with newline for the UI/terminal
            if line and not line.endswith("\n"):
                line = line + "\n"

            log_f.write(line)
            log_f.flush()

            publisher.log_line(line)

            m = _BATCH_LINE_RE.match(line)
            if m:
                batch = int(m.group("batch"))
                total = int(m.group("total"))
                keff = float(m.group("keff"))
                keff_std = float(m.group("keff_std"))

                total_batches = total
                if last_batch != batch:
                    publisher.tool_call(
                        tool_name="openmc.batch_progress",
                        message=f"Batch {batch}/{total} — k-eff {keff:.5f} ± {keff_std:.5f}",
                        args={
                            "batch": batch,
                            "total_batches": total,
                            "keff": keff,
                            "keff_std": keff_std,
                            "progress_pct": round(100.0 * batch / max(1, total), 2),
                        },
                    )
                    last_batch = batch
                    last_keff = keff
                    last_keff_std = keff_std

    # Extract results (statepoint moved to outputs/ by runner)
    statepoint_files = sorted(outputs_dir.glob("statepoint.*.h5"))
    if not statepoint_files:
        result = {
            "status": "failed",
            "error": "No statepoint file found after OpenMC run",
            "run_id": run_id,
            "spec_hash": spec_hash,
            "run_dir": str(run_dir),
        }
        publisher.tool_result("openmc.run", result)
        return {**result, "keff": 0.0, "keff_std": 0.0, "runtime_seconds": 0.0}

    extracted = extract_results(statepoint_files[-1])

    # Runtime from manifest (written by StreamingSimulationRunner)
    runtime_seconds = 0.0
    manifest_path = run_dir / "run_manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            runtime_seconds = float(manifest.get("runtime_seconds", 0.0) or 0.0)
        except Exception:
            runtime_seconds = 0.0

    final = {
        "status": "completed",
        "run_id": run_id,
        "spec_hash": spec_hash,
        "run_dir": str(run_dir),
        "keff": extracted.get("keff", last_keff or 0.0),
        "keff_std": extracted.get("keff_std", last_keff_std or 0.0),
        "uncertainty_pcm": (extracted.get("keff_std", last_keff_std or 0.0) or 0.0) * 1e5,
        "runtime_seconds": runtime_seconds,
        "log_path": str(log_path),
        "total_batches": total_batches,
    }

    publisher.tool_result("openmc.run", final)
    return final


def _make_compare_blip(current: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a short, user-facing comparison blip between current and baseline runs.
    """
    cur_keff = float(current.get("keff", 0.0) or 0.0)
    cur_std = float(current.get("keff_std", 0.0) or 0.0)
    base_keff = float(baseline.get("keff", 0.0) or 0.0)
    base_std = float(baseline.get("keff_std", 0.0) or 0.0)

    delta = cur_keff - base_keff
    # combined 1-sigma (assuming independence)
    combined = (cur_std**2 + base_std**2) ** 0.5 if (cur_std or base_std) else None
    delta_pcm = delta * 1e5
    z = (delta / combined) if (combined and combined > 0) else None

    direction = "higher" if delta > 0 else "lower" if delta < 0 else "about the same"
    sig_text = ""
    if z is not None:
        sig_text = f" (~{abs(z):.1f}σ)"

    summary = (
        f"Compared to {baseline.get('run_id')}, this run’s k-eff is {direction} by {delta_pcm:+.1f} pcm{sig_text} "
        f"({cur_keff:.5f} ± {cur_std:.5f} vs {base_keff:.5f} ± {base_std:.5f})."
    )

    return {
        "baseline_run_id": baseline.get("run_id"),
        "delta_keff": delta,
        "delta_pcm": delta_pcm,
        "combined_std": combined,
        "z_score": z,
        "summary": summary,
    }


def _suggest_next_experiment(spec_dict: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple heuristic suggestion to run another experiment with a different input.
    """
    geometry = spec_dict.get("geometry")
    enrichment = spec_dict.get("enrichment_pct")
    temperature = spec_dict.get("temperature_K")
    particles = spec_dict.get("particles")
    batches = spec_dict.get("batches")

    # Prefer a parameter nudge: enrichment up/down, else increase particles for uncertainty reduction.
    suggestion = {
        "prompt": "Try another run with a different input to see if we can improve k-eff.",
        "candidate_inputs": [],
    }

    if isinstance(enrichment, (int, float)):
        step = 0.5
        suggestion["candidate_inputs"].append({**spec_dict, "enrichment_pct": round(float(enrichment) + step, 3)})
        suggestion["candidate_inputs"].append({**spec_dict, "enrichment_pct": max(0.0, round(float(enrichment) - step, 3))})
        suggestion["prompt"] = f"Next experiment: sweep enrichment around {enrichment}% (e.g., {enrichment - step}% and {enrichment + step}%)."
    elif isinstance(temperature, (int, float)):
        stepT = 50.0
        suggestion["candidate_inputs"].append({**spec_dict, "temperature_K": round(float(temperature) + stepT, 1)})
        suggestion["candidate_inputs"].append({**spec_dict, "temperature_K": max(0.0, round(float(temperature) - stepT, 1))})
        suggestion["prompt"] = f"Next experiment: vary temperature by ±{int(stepT)} K to see sensitivity."
    else:
        # fallback: reduce uncertainty
        if isinstance(particles, int):
            suggestion["candidate_inputs"].append({**spec_dict, "particles": int(particles * 2)})
        if isinstance(batches, int):
            suggestion["candidate_inputs"].append({**spec_dict, "batches": int(batches + 20)})
        suggestion["prompt"] = "Next experiment: increase particles/batches to reduce uncertainty and confirm the trend."

    suggestion["context"] = {
        "geometry": geometry,
        "current_run_id": current.get("run_id"),
        "current_keff": current.get("keff"),
        "current_keff_std": current.get("keff_std"),
    }
    return suggestion


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SimulationSpec(BaseModel):
    """Simplified simulation specification"""
    geometry: str = Field(..., description="Geometry type (e.g., 'PWR pin cell')")
    materials: List[str] = Field(..., description="List of materials (e.g., ['UO2', 'Water'])")
    enrichment_pct: float = Field(default=4.5, ge=0, le=20, description="U-235 enrichment percentage")
    temperature_K: float = Field(default=900.0, ge=0, description="Temperature in Kelvin")
    particles: int = Field(default=10000, ge=100, description="Number of particles per batch")
    batches: int = Field(default=50, ge=10, description="Number of batches")
    
    class Config:
        json_schema_extra = {
            "example": {
                "geometry": "PWR pin cell",
                "materials": ["UO2", "Water"],
                "enrichment_pct": 4.5,
                "temperature_K": 900.0,
                "particles": 10000,
                "batches": 50
            }
        }


class SimulationSubmitRequest(BaseModel):
    """Request to submit a simulation"""
    spec: SimulationSpec
    run_id: Optional[str] = Field(default=None, description="Optional custom run ID")
    priority: str = Field(default="normal", description="Priority: low, normal, high")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SimulationSubmitResponse(BaseModel):
    """Response after submitting a simulation"""
    run_id: str
    spec_hash: str
    status: str
    submitted_at: datetime
    estimated_duration_seconds: int


class SimulationResult(BaseModel):
    """Simulation result"""
    run_id: str
    spec_hash: str
    status: str
    keff: float
    keff_std: float
    uncertainty_pcm: float
    runtime_seconds: float
    run_dir: str
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class SweepRequest(BaseModel):
    """Request for parameter sweep"""
    base_spec: SimulationSpec
    parameter: str = Field(..., description="Parameter to sweep (e.g., 'enrichment_pct')")
    values: List[float] = Field(..., min_items=2, description="Values to sweep")
    
    class Config:
        json_schema_extra = {
            "example": {
                "base_spec": {
                    "geometry": "PWR pin cell",
                    "materials": ["UO2", "Water"],
                    "enrichment_pct": 4.5,
                    "temperature_K": 900.0,
                    "particles": 5000,
                    "batches": 20
                },
                "parameter": "enrichment_pct",
                "values": [3.0, 3.5, 4.0, 4.5, 5.0]
            }
        }


class SweepSubmitResponse(BaseModel):
    """Response after submitting a sweep"""
    sweep_id: str
    run_ids: List[str]
    total_runs: int
    status: str
    submitted_at: datetime


class SweepResult(BaseModel):
    """Sweep result"""
    sweep_id: str
    parameter: str
    total_runs: int
    completed_runs: int
    status: str
    results: List[Dict[str, Any]]
    submitted_at: datetime
    completed_at: Optional[datetime] = None


class RunQuery(BaseModel):
    """Query parameters for runs"""
    geometry: Optional[str] = None
    enrichment_min: Optional[float] = None
    enrichment_max: Optional[float] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    keff_min: Optional[float] = None
    keff_max: Optional[float] = None
    status: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class RunQueryResponse(BaseModel):
    """Response for run queries"""
    total: int
    limit: int
    offset: int
    runs: List[SimulationResult]


class CompareRequest(BaseModel):
    """Request to compare multiple runs"""
    run_ids: List[str] = Field(..., min_items=2, max_items=10)


class CompareResponse(BaseModel):
    """Comparison results"""
    num_runs: int
    keff_values: List[float]
    keff_stds: List[float]
    keff_mean: float
    keff_std_dev: float
    keff_min: float
    keff_max: float
    reactivity_span: float
    runs: List[Dict[str, Any]]


class Statistics(BaseModel):
    """Database statistics"""
    total_runs: int
    completed_runs: int
    failed_runs: int
    running_runs: int
    total_sweeps: int
    average_runtime_seconds: float
    recent_runs: List[Dict[str, Any]]


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]
    runs_directory: str
    available_runs: int


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

class Database:
    client: AsyncIOMotorClient = None

db = Database()


async def get_database():
    """Dependency for database access"""
    return db.client["aonp"]


async def startup_db():
    """Initialize MongoDB connection"""
    if MONGODB_URI:
        db.client = AsyncIOMotorClient(MONGODB_URI)
        await db.client.admin.command('ping')
        print(f"✅ Connected to MongoDB")
    else:
        print("⚠️  No MongoDB URI - running without database")


async def shutdown_db():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        print("✅ Closed MongoDB connection")


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="OpenMC Backend API",
    description="Direct access to OpenMC simulation engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global adapter instance
adapter = OpenMCAdapter(runs_dir=RUNS_DIR)

# Startup/Shutdown
@app.on_event("startup")
async def startup_event():
    await startup_db()
    RUNS_DIR.mkdir(exist_ok=True)
    print(f"✅ Runs directory: {RUNS_DIR.absolute()}")


@app.on_event("shutdown")
async def shutdown_event():
    await shutdown_db()


# ============================================================================
# BACKGROUND EXECUTION
# ============================================================================

async def execute_simulation_background(
    run_id: str,
    spec_dict: Dict[str, Any],
    mongodb
):
    """Execute simulation in background"""
    try:
        # Update status to running
        if mongodb:
            await mongodb.openmc_runs.update_one(
                {"run_id": run_id},
                {"$set": {"status": "running", "started_at": datetime.now(timezone.utc)}}
            )

        # Execute simulation (runs in thread pool since it's synchronous)
        loop = asyncio.get_event_loop()
        publisher = RunEventPublisher(loop=loop, run_id=run_id)
        result = await loop.run_in_executor(None, _stream_execute_openmc, spec_dict, run_id, publisher)
        
        # Calculate additional metrics
        uncertainty_pcm = result.get('keff_std', 0.0) * 1e5
        
        # Update database
        if mongodb:
            await mongodb.openmc_runs.update_one(
                {"run_id": run_id},
                {
                    "$set": {
                        "status": result["status"],
                        "keff": result["keff"],
                        "keff_std": result["keff_std"],
                        "uncertainty_pcm": uncertainty_pcm,
                        "runtime_seconds": result["runtime_seconds"],
                        "run_dir": result["run_dir"],
                        "completed_at": datetime.now(timezone.utc),
                        "error": result.get("error")
                    }
                }
            )
            
            # Also store in summaries if successful
            if result["status"] == "completed":
                await mongodb.summaries.insert_one({
                    "run_id": run_id,
                    "spec_hash": result["spec_hash"],
                    "keff": result["keff"],
                    "keff_std": result["keff_std"],
                    "status": result["status"],
                    "runtime_seconds": result["runtime_seconds"],
                    "created_at": datetime.now(timezone.utc),
                    "spec": spec_dict
                })

        # Compare Agent blip (best-effort)
        if mongodb and result.get("status") == "completed":
            try:
                # Find a relevant baseline: most recent completed run with same geometry (excluding current)
                geom = spec_dict.get("geometry")
                baseline = await mongodb.openmc_runs.find_one(
                    {
                        "run_id": {"$ne": run_id},
                        "status": "completed",
                        "spec.geometry": geom,
                        "keff": {"$exists": True},
                        "keff_std": {"$exists": True},
                    },
                    sort=[("completed_at", -1)],
                )
                if baseline:
                    compare = _make_compare_blip(
                        current={"run_id": run_id, **result},
                        baseline={
                            "run_id": baseline.get("run_id"),
                            "keff": baseline.get("keff"),
                            "keff_std": baseline.get("keff_std"),
                        },
                    )
                    # Emit as a tool_result so the UI shows it in the "tool events" feed
                    publisher.tool_result("compare_runs", compare)
                    # Also emit a short agent blip
                    publisher.agent_blip("Compare Agent", compare["summary"], {"baseline_run_id": compare["baseline_run_id"]})
            except Exception as e:
                publisher.agent_blip("Compare Agent", f"Comparison unavailable: {e}", {})

        # After 10 seconds: prompt another experiment
        if result.get("status") == "completed":
            await asyncio.sleep(10.0)
            suggestion = _suggest_next_experiment(spec_dict, result)
            publisher.agent_blip("Compare Agent", suggestion["prompt"], {"candidates": suggestion.get("candidate_inputs", [])[:2]})
            publisher.tool_call(
                tool_name="suggest_next_experiment",
                message=suggestion["prompt"],
                args={"candidates": suggestion.get("candidate_inputs", [])[:2]},
            )

        # Signal stream completion (after the delayed prompt)
        await run_event_bus.complete(run_id)
        
    except Exception as e:
        print(f"❌ Background execution failed for {run_id}: {e}")
        import traceback
        traceback.print_exc()
        
        if mongodb:
            await mongodb.openmc_runs.update_one(
                {"run_id": run_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.now(timezone.utc)
                    }
                }
            )

        # Publish error + complete stream
        await run_event_bus.publish(
            run_id,
            {
                "type": "openmc_error",
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            },
        )
        await run_event_bus.complete(run_id)


# ============================================================================
# ENDPOINTS: SIMULATION SUBMISSION
# ============================================================================

@app.post("/api/v1/simulations", response_model=SimulationSubmitResponse, status_code=202)
async def submit_simulation(
    request: SimulationSubmitRequest,
    background_tasks: BackgroundTasks,
    mongodb=Depends(get_database)
):
    """
    Submit a simulation to OpenMC
    
    The simulation runs asynchronously. Use GET /api/v1/simulations/{run_id} to check status.
    """
    # Generate run ID if not provided
    run_id = request.run_id or f"run_{uuid4().hex[:12]}"
    
    # Convert spec to dict
    spec_dict = request.spec.dict()
    
    # Translate to get spec hash
    study = adapter.translate_simple_to_openmc(spec_dict, run_id)
    spec_hash = study.get_short_hash()
    
    # Store in database
    submitted_at = datetime.now(timezone.utc)
    if mongodb:
        await mongodb.openmc_runs.insert_one({
            "run_id": run_id,
            "spec_hash": spec_hash,
            "status": "queued",
            "spec": spec_dict,
            "priority": request.priority,
            "metadata": request.metadata,
            "submitted_at": submitted_at,
            "started_at": None,
            "completed_at": None
        })
    
    # Start background execution
    background_tasks.add_task(
        execute_simulation_background,
        run_id,
        spec_dict,
        mongodb
    )
    
    # Estimate duration based on particles and batches
    estimated_duration = int((spec_dict["particles"] * spec_dict["batches"]) / 10000)
    
    return SimulationSubmitResponse(
        run_id=run_id,
        spec_hash=spec_hash,
        status="queued",
        submitted_at=submitted_at,
        estimated_duration_seconds=max(5, estimated_duration)
    )


@app.get("/api/v1/simulations/{run_id}/stream")
async def stream_simulation_output(run_id: str):
    """
    Stream OpenMC run output and parsed progress events via SSE.

    Events include:
    - openmc_log: raw stdout lines
    - tool_call: interpreted progress/tool-style events
    - tool_result: final summary
    - openmc_error: error details (if any)
    """
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run directory not found for {run_id}")

    async def event_generator():
        queue = run_event_bus.subscribe(run_id)

        # Replay recent log tail (best-effort)
        log_path = run_dir / "outputs" / "openmc_stdout.log"
        if log_path.exists():
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    tail = f.readlines()[-200:]
                for line in tail:
                    event = {
                        "type": "openmc_log",
                        "run_id": run_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "content": line,
                    }
                    yield f"event: openmc_log\n"
                    yield f"data: {json.dumps(event)}\n\n"
            except Exception:
                pass

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                if event is None:
                    break

                yield f"event: {event['type']}\n"
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            run_event_bus.unsubscribe(run_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/v1/simulations/{run_id}", response_model=SimulationResult)
async def get_simulation(
    run_id: str,
    mongodb=Depends(get_database)
):
    """
    Get simulation status and results
    """
    if not mongodb:
        raise HTTPException(status_code=503, detail="Database not available")
    
    run_doc = await mongodb.openmc_runs.find_one({"run_id": run_id})
    
    if not run_doc:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    return SimulationResult(
        run_id=run_doc["run_id"],
        spec_hash=run_doc["spec_hash"],
        status=run_doc["status"],
        keff=run_doc.get("keff", 0.0),
        keff_std=run_doc.get("keff_std", 0.0),
        uncertainty_pcm=run_doc.get("uncertainty_pcm", 0.0),
        runtime_seconds=run_doc.get("runtime_seconds", 0.0),
        run_dir=run_doc.get("run_dir", ""),
        submitted_at=run_doc.get("submitted_at"),
        completed_at=run_doc.get("completed_at"),
        error=run_doc.get("error")
    )


@app.delete("/api/v1/simulations/{run_id}")
async def cancel_simulation(
    run_id: str,
    mongodb=Depends(get_database)
):
    """
    Cancel a queued or running simulation
    """
    if not mongodb:
        raise HTTPException(status_code=503, detail="Database not available")
    
    result = await mongodb.openmc_runs.update_one(
        {"run_id": run_id, "status": {"$in": ["queued", "running"]}},
        {"$set": {"status": "cancelled", "completed_at": datetime.now(timezone.utc)}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Run not found or cannot be cancelled")
    
    return {"run_id": run_id, "status": "cancelled"}


# ============================================================================
# ENDPOINTS: PARAMETER SWEEPS
# ============================================================================

@app.post("/api/v1/sweeps", response_model=SweepSubmitResponse, status_code=202)
async def submit_sweep(
    request: SweepRequest,
    background_tasks: BackgroundTasks,
    mongodb=Depends(get_database)
):
    """
    Submit a parameter sweep
    
    Creates multiple simulations varying one parameter.
    """
    sweep_id = f"sweep_{uuid4().hex[:12]}"
    submitted_at = datetime.now(timezone.utc)
    
    # Validate parameter
    if request.parameter not in request.base_spec.dict():
        raise HTTPException(
            status_code=400,
            detail=f"Parameter '{request.parameter}' not found in spec"
        )
    
    # Create run IDs
    run_ids = []
    for i, value in enumerate(request.values):
        run_ids.append(f"{sweep_id}_p{i:03d}")
    
    # Store sweep metadata
    if mongodb:
        await mongodb.openmc_sweeps.insert_one({
            "sweep_id": sweep_id,
            "parameter": request.parameter,
            "values": request.values,
            "run_ids": run_ids,
            "total_runs": len(run_ids),
            "status": "queued",
            "submitted_at": submitted_at,
            "base_spec": request.base_spec.dict()
        })
    
    # Submit each simulation
    for run_id, value in zip(run_ids, request.values):
        # Create spec with modified parameter
        spec_dict = request.base_spec.dict()
        spec_dict[request.parameter] = value
        
        # Translate to get spec hash
        study = adapter.translate_simple_to_openmc(spec_dict, run_id)
        spec_hash = study.get_short_hash()
        
        # Store in database
        if mongodb:
            await mongodb.openmc_runs.insert_one({
                "run_id": run_id,
                "spec_hash": spec_hash,
                "sweep_id": sweep_id,
                "status": "queued",
                "spec": spec_dict,
                "submitted_at": submitted_at
            })
        
        # Start background execution
        background_tasks.add_task(
            execute_simulation_background,
            run_id,
            spec_dict,
            mongodb
        )
    
    return SweepSubmitResponse(
        sweep_id=sweep_id,
        run_ids=run_ids,
        total_runs=len(run_ids),
        status="queued",
        submitted_at=submitted_at
    )


@app.get("/api/v1/sweeps/{sweep_id}", response_model=SweepResult)
async def get_sweep(
    sweep_id: str,
    mongodb=Depends(get_database)
):
    """
    Get sweep status and results
    """
    if not mongodb:
        raise HTTPException(status_code=503, detail="Database not available")
    
    sweep_doc = await mongodb.openmc_sweeps.find_one({"sweep_id": sweep_id})
    
    if not sweep_doc:
        raise HTTPException(status_code=404, detail=f"Sweep {sweep_id} not found")
    
    # Get all run results
    run_ids = sweep_doc["run_ids"]
    runs_cursor = mongodb.openmc_runs.find({"run_id": {"$in": run_ids}})
    runs = await runs_cursor.to_list(length=len(run_ids))
    
    # Count completed
    completed_runs = sum(1 for r in runs if r["status"] == "completed")
    
    # Determine overall status
    if completed_runs == len(run_ids):
        status = "completed"
    elif any(r["status"] == "failed" for r in runs):
        status = "partial"
    else:
        status = "running"
    
    # Build results
    results = []
    for value, run in zip(sweep_doc["values"], runs):
        results.append({
            "parameter_value": value,
            "run_id": run["run_id"],
            "status": run["status"],
            "keff": run.get("keff", 0.0),
            "keff_std": run.get("keff_std", 0.0)
        })
    
    return SweepResult(
        sweep_id=sweep_id,
        parameter=sweep_doc["parameter"],
        total_runs=sweep_doc["total_runs"],
        completed_runs=completed_runs,
        status=status,
        results=results,
        submitted_at=sweep_doc["submitted_at"],
        completed_at=sweep_doc.get("completed_at")
    )


# ============================================================================
# ENDPOINTS: QUERIES
# ============================================================================

@app.get("/api/v1/runs", response_model=RunQueryResponse)
async def query_runs(
    geometry: Optional[str] = Query(None),
    enrichment_min: Optional[float] = Query(None),
    enrichment_max: Optional[float] = Query(None),
    temperature_min: Optional[float] = Query(None),
    temperature_max: Optional[float] = Query(None),
    keff_min: Optional[float] = Query(None),
    keff_max: Optional[float] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    mongodb=Depends(get_database)
):
    """
    Query simulation runs with filters
    """
    if not mongodb:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Build filter
    filter_query = {}
    
    if geometry:
        filter_query["spec.geometry"] = {"$regex": geometry, "$options": "i"}
    if enrichment_min is not None:
        filter_query.setdefault("spec.enrichment_pct", {})["$gte"] = enrichment_min
    if enrichment_max is not None:
        filter_query.setdefault("spec.enrichment_pct", {})["$lte"] = enrichment_max
    if temperature_min is not None:
        filter_query.setdefault("spec.temperature_K", {})["$gte"] = temperature_min
    if temperature_max is not None:
        filter_query.setdefault("spec.temperature_K", {})["$lte"] = temperature_max
    if keff_min is not None:
        filter_query.setdefault("keff", {})["$gte"] = keff_min
    if keff_max is not None:
        filter_query.setdefault("keff", {})["$lte"] = keff_max
    if status:
        filter_query["status"] = status
    
    # Get total count
    total = await mongodb.openmc_runs.count_documents(filter_query)
    
    # Query with pagination
    cursor = mongodb.openmc_runs.find(filter_query).sort("submitted_at", -1).skip(offset).limit(limit)
    results = await cursor.to_list(length=limit)
    
    # Format results
    runs = []
    for r in results:
        runs.append(SimulationResult(
            run_id=r["run_id"],
            spec_hash=r["spec_hash"],
            status=r["status"],
            keff=r.get("keff", 0.0),
            keff_std=r.get("keff_std", 0.0),
            uncertainty_pcm=r.get("uncertainty_pcm", 0.0),
            runtime_seconds=r.get("runtime_seconds", 0.0),
            run_dir=r.get("run_dir", ""),
            submitted_at=r.get("submitted_at"),
            completed_at=r.get("completed_at"),
            error=r.get("error")
        ))
    
    return RunQueryResponse(
        total=total,
        limit=limit,
        offset=offset,
        runs=runs
    )


@app.post("/api/v1/runs/compare", response_model=CompareResponse)
async def compare_runs(
    request: CompareRequest,
    mongodb=Depends(get_database)
):
    """
    Compare multiple simulation runs
    """
    if not mongodb:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Fetch runs
    cursor = mongodb.openmc_runs.find({"run_id": {"$in": request.run_ids}})
    runs = await cursor.to_list(length=len(request.run_ids))
    
    if len(runs) < 2:
        raise HTTPException(status_code=404, detail="Not enough runs found")
    
    # Extract k-eff values
    keff_values = [r["keff"] for r in runs if r.get("keff")]
    keff_stds = [r["keff_std"] for r in runs if r.get("keff_std")]
    
    if not keff_values:
        raise HTTPException(status_code=400, detail="No completed runs with k-eff values")
    
    # Calculate statistics
    import statistics
    keff_mean = statistics.mean(keff_values)
    keff_std_dev = statistics.stdev(keff_values) if len(keff_values) > 1 else 0.0
    keff_min = min(keff_values)
    keff_max = max(keff_values)
    reactivity_span = keff_max - keff_min
    
    # Format run details
    run_details = []
    for r in runs:
        run_details.append({
            "run_id": r["run_id"],
            "keff": r.get("keff", 0.0),
            "keff_std": r.get("keff_std", 0.0),
            "spec": r.get("spec", {})
        })
    
    return CompareResponse(
        num_runs=len(runs),
        keff_values=keff_values,
        keff_stds=keff_stds,
        keff_mean=keff_mean,
        keff_std_dev=keff_std_dev,
        keff_min=keff_min,
        keff_max=keff_max,
        reactivity_span=reactivity_span,
        runs=run_details
    )


# ============================================================================
# ENDPOINTS: FILES & ARTIFACTS
# ============================================================================

@app.get("/api/v1/simulations/{run_id}/files")
async def list_run_files(run_id: str):
    """
    List output files for a simulation
    """
    run_dir = RUNS_DIR / run_id
    
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run directory not found for {run_id}")
    
    # List files
    files = []
    for item in run_dir.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(run_dir)
            files.append({
                "path": str(rel_path),
                "size": item.stat().st_size,
                "modified": datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc).isoformat()
            })
    
    return {"run_id": run_id, "files": files}


@app.get("/api/v1/simulations/{run_id}/files/{file_path:path}")
async def download_run_file(run_id: str, file_path: str):
    """
    Download a specific file from a simulation
    """
    run_dir = RUNS_DIR / run_id
    file_full_path = run_dir / file_path
    
    # Security check - ensure path is within run directory
    if not str(file_full_path.resolve()).startswith(str(run_dir.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not file_full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_full_path)


# ============================================================================
# ENDPOINTS: STATISTICS & HEALTH
# ============================================================================

@app.get("/api/v1/statistics", response_model=Statistics)
async def get_statistics(mongodb=Depends(get_database)):
    """
    Get database and execution statistics
    """
    if not mongodb:
        raise HTTPException(status_code=503, detail="Database not available")
    
    total_runs = await mongodb.openmc_runs.count_documents({})
    completed_runs = await mongodb.openmc_runs.count_documents({"status": "completed"})
    failed_runs = await mongodb.openmc_runs.count_documents({"status": "failed"})
    running_runs = await mongodb.openmc_runs.count_documents({"status": "running"})
    total_sweeps = await mongodb.openmc_sweeps.count_documents({})
    
    # Calculate average runtime
    pipeline = [
        {"$match": {"status": "completed", "runtime_seconds": {"$exists": True}}},
        {"$group": {"_id": None, "avg_runtime": {"$avg": "$runtime_seconds"}}}
    ]
    result = await mongodb.openmc_runs.aggregate(pipeline).to_list(length=1)
    average_runtime = result[0]["avg_runtime"] if result else 0.0
    
    # Get recent runs
    cursor = mongodb.openmc_runs.find().sort("submitted_at", -1).limit(5)
    recent_docs = await cursor.to_list(length=5)
    
    recent_runs = [
        {
            "run_id": r["run_id"],
            "status": r["status"],
            "keff": r.get("keff", 0.0),
            "submitted_at": r["submitted_at"].isoformat()
        }
        for r in recent_docs
    ]
    
    return Statistics(
        total_runs=total_runs,
        completed_runs=completed_runs,
        failed_runs=failed_runs,
        running_runs=running_runs,
        total_sweeps=total_sweeps,
        average_runtime_seconds=average_runtime,
        recent_runs=recent_runs
    )


@app.get("/api/v1/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint
    """
    # Check MongoDB
    mongodb_status = "connected"
    if db.client:
        try:
            await db.client.admin.command('ping')
        except Exception:
            mongodb_status = "disconnected"
    else:
        mongodb_status = "not_configured"
    
    # Check OpenMC availability
    openmc_status = "available"
    try:
        import openmc
        openmc_version = openmc.__version__
    except ImportError:
        openmc_status = "not_installed"
        openmc_version = None
    
    # Check nuclear data
    nuclear_data_status = "configured" if os.getenv("OPENMC_CROSS_SECTIONS") else "not_configured"
    
    # Count available runs
    available_runs = len(list(RUNS_DIR.glob("*"))) if RUNS_DIR.exists() else 0
    
    # Overall status
    status = "healthy"
    if mongodb_status == "disconnected":
        status = "degraded"
    elif openmc_status != "available":
        status = "limited"
    
    services = {
        "mongodb": mongodb_status,
        "openmc": openmc_status,
        "nuclear_data": nuclear_data_status
    }
    
    if openmc_version:
        services["openmc_version"] = openmc_version
    
    return HealthCheck(
        status=status,
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        services=services,
        runs_directory=str(RUNS_DIR.absolute()),
        available_runs=available_runs
    )


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """API root"""
    return {
        "name": "OpenMC Backend API",
        "version": "1.0.0",
        "description": "Direct access to OpenMC simulation engine",
        "docs": "/docs",
        "health": "/api/v1/health",
        "endpoints": {
            "simulations": "/api/v1/simulations",
            "sweeps": "/api/v1/sweeps",
            "runs": "/api/v1/runs",
            "statistics": "/api/v1/statistics"
        }
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("OPENMC BACKEND API")
    print("=" * 80)
    print(f"Server: http://{API_HOST}:{API_PORT}")
    print(f"Docs: http://{API_HOST}:{API_PORT}/docs")
    print(f"Runs Directory: {RUNS_DIR.absolute()}")
    print("=" * 80)
    
    uvicorn.run(
        "openmc_api:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )


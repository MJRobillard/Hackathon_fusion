"""
OpenMC backend API router for simulation execution and streaming.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from aonp.core.bundler import create_run_bundle
from aonp.core.extractor import extract_results
from aonp.runner.openmc_adapter import OpenMCAdapter
from aonp.runner.streaming_runner import StreamingSimulationRunner


RUNS_DIR = Path(os.getenv("OPENMC_RUNS_DIR", "runs"))


@dataclass
class RunRecord:
    run_id: str
    spec: Dict[str, Any]
    status: str = "queued"
    submitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    run_dir: Optional[str] = None
    spec_hash: Optional[str] = None
    keff: Optional[float] = None
    keff_std: Optional[float] = None
    uncertainty_pcm: Optional[float] = None
    runtime_seconds: Optional[float] = None
    error: Optional[str] = None


RUN_RECORDS: Dict[str, RunRecord] = {}
SWEEP_RECORDS: Dict[str, Dict[str, Any]] = {}


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
_event_loop: Optional[asyncio.AbstractEventLoop] = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _event_loop
    _event_loop = loop


def _publish_event(run_id: str, event: dict) -> None:
    if _event_loop is None:
        return
    asyncio.run_coroutine_threadsafe(run_event_bus.publish(run_id, event), _event_loop)


def _publish_complete(run_id: str) -> None:
    if _event_loop is None:
        return
    asyncio.run_coroutine_threadsafe(run_event_bus.complete(run_id), _event_loop)


_BATCH_LINE_RE = re.compile(
    r"^\s*(?P<batch>\d+)\s*/\s*(?P<total>\d+)\s+(?P<keff>-?\d+\.\d+)\s*\+/-\s*(?P<keff_std>\d+\.\d+)"
)


class SimulationSpec(BaseModel):
    geometry: str = Field(..., description="Geometry type (e.g., 'PWR pin cell')")
    materials: List[str] = Field(..., description="List of materials (e.g., ['UO2', 'Water'])")
    enrichment_pct: float = Field(default=4.5, ge=0, le=20)
    temperature_K: float = Field(default=900.0, ge=0)
    particles: int = Field(default=10000, ge=100)
    batches: int = Field(default=50, ge=10)


class SimulationSubmitRequest(BaseModel):
    spec: SimulationSpec
    run_id: Optional[str] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SimulationSubmitResponse(BaseModel):
    run_id: str
    spec_hash: str
    status: str
    submitted_at: str


class SimulationResult(BaseModel):
    run_id: str
    spec_hash: Optional[str] = None
    status: str
    keff: float = 0.0
    keff_std: float = 0.0
    uncertainty_pcm: float = 0.0
    runtime_seconds: float = 0.0
    run_dir: str = ""
    submitted_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class SweepRequest(BaseModel):
    base_spec: SimulationSpec
    parameter: str
    values: List[float]


class SweepSubmitResponse(BaseModel):
    sweep_id: str
    run_ids: List[str]
    total_runs: int
    status: str
    submitted_at: str


class SweepResult(BaseModel):
    sweep_id: str
    parameter: str
    total_runs: int
    completed_runs: int
    status: str
    results: List[Dict[str, Any]]
    submitted_at: str
    completed_at: Optional[str] = None


class CompareRequest(BaseModel):
    run_ids: List[str] = Field(..., min_items=2, max_items=10)


router = APIRouter(prefix="/api/v1/openmc", tags=["openmc"])


def _execute_openmc_run(run_id: str, spec_dict: Dict[str, Any]) -> None:
    record = RUN_RECORDS[run_id]
    record.status = "running"
    record.started_at = datetime.now(timezone.utc).isoformat()

    try:
        adapter = OpenMCAdapter(runs_dir=RUNS_DIR)
        study = adapter.translate_simple_to_openmc(spec_dict, run_id=run_id)
        run_dir, spec_hash = create_run_bundle(study=study, run_id=run_id, base_dir=RUNS_DIR)

        record.run_dir = str(run_dir)
        record.spec_hash = spec_hash

        print(f"[OpenMC] Run {run_id} starting in {run_dir}")
        _publish_event(
            run_id,
            {
                "type": "tool_call",
                "agent": "OpenMC",
                "tool_name": "openmc.run",
                "message": "Starting OpenMC run",
                "args": {"run_id": run_id, "spec_hash": spec_hash, "run_dir": str(run_dir)},
            },
        )

        outputs_dir = run_dir / "outputs"
        outputs_dir.mkdir(exist_ok=True)
        log_path = outputs_dir / "openmc_stdout.log"

        runner = StreamingSimulationRunner(run_dir)
        with log_path.open("a", encoding="utf-8") as log_f:
            for line in runner.stream_simulation():
                if line and not line.endswith("\n"):
                    line = line + "\n"
                log_f.write(line)
                log_f.flush()
                if line.strip():
                    print(line, end="")
                _publish_event(
                    run_id,
                    {
                        "type": "openmc_log",
                        "run_id": run_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "content": line,
                    },
                )

                match = _BATCH_LINE_RE.match(line)
                if match:
                    batch = int(match.group("batch"))
                    total = int(match.group("total"))
                    keff = float(match.group("keff"))
                    keff_std = float(match.group("keff_std"))
                    _publish_event(
                        run_id,
                        {
                            "type": "tool_call",
                            "agent": "OpenMC",
                            "tool_name": "openmc.batch_progress",
                            "message": f"Batch {batch}/{total} — k-eff {keff:.5f} ± {keff_std:.5f}",
                            "args": {
                                "batch": batch,
                                "total_batches": total,
                                "keff": keff,
                                "keff_std": keff_std,
                                "progress_pct": round(100.0 * batch / max(1, total), 2),
                            },
                        },
                    )

        statepoint_files = sorted((run_dir / "outputs").glob("statepoint.*.h5"))
        if not statepoint_files:
            raise RuntimeError("No statepoint file found after OpenMC run")

        extracted = extract_results(statepoint_files[-1])

        manifest_path = run_dir / "run_manifest.json"
        runtime_seconds = 0.0
        if manifest_path.exists():
            try:
                with manifest_path.open("r", encoding="utf-8") as f:
                    manifest = json.load(f)
                runtime_seconds = float(manifest.get("runtime_seconds", 0.0) or 0.0)
            except Exception:
                runtime_seconds = 0.0

        record.status = "completed"
        record.completed_at = datetime.now(timezone.utc).isoformat()
        record.keff = float(extracted.get("keff", 0.0) or 0.0)
        record.keff_std = float(extracted.get("keff_std", 0.0) or 0.0)
        record.uncertainty_pcm = record.keff_std * 1e5
        record.runtime_seconds = runtime_seconds

        print(f"[OpenMC] Run {run_id} completed")
        _publish_event(
            run_id,
            {
                "type": "tool_result",
                "agent": "OpenMC",
                "tool_name": "openmc.run",
                "result": {
                    "status": "completed",
                    "run_id": run_id,
                    "spec_hash": record.spec_hash,
                    "run_dir": record.run_dir,
                    "keff": record.keff,
                    "keff_std": record.keff_std,
                    "uncertainty_pcm": record.uncertainty_pcm,
                    "runtime_seconds": record.runtime_seconds,
                    "summary": f"Run completed: k-eff {record.keff:.5f} ± {record.keff_std:.5f}",
                },
            },
        )
    except Exception as exc:
        record.status = "failed"
        record.completed_at = datetime.now(timezone.utc).isoformat()
        record.error = str(exc)
        print(f"[OpenMC] Run {run_id} failed: {exc}")
        _publish_event(
            run_id,
            {
                "type": "openmc_error",
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            },
        )
    finally:
        _publish_complete(run_id)


@router.post("/simulations", response_model=SimulationSubmitResponse, status_code=202)
def submit_simulation(request: SimulationSubmitRequest):
    run_id = request.run_id or f"run_{uuid4().hex[:12]}"
    record = RunRecord(run_id=run_id, spec=request.spec.dict())
    RUN_RECORDS[run_id] = record

    thread = threading.Thread(target=_execute_openmc_run, args=(run_id, record.spec), daemon=True)
    thread.start()

    return SimulationSubmitResponse(
        run_id=run_id,
        spec_hash=record.spec_hash or "",
        status=record.status,
        submitted_at=record.submitted_at,
    )


@router.get("/simulations/{run_id}", response_model=SimulationResult)
def get_simulation(run_id: str):
    record = RUN_RECORDS.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return SimulationResult(
        run_id=record.run_id,
        spec_hash=record.spec_hash,
        status=record.status,
        keff=record.keff or 0.0,
        keff_std=record.keff_std or 0.0,
        uncertainty_pcm=record.uncertainty_pcm or 0.0,
        runtime_seconds=record.runtime_seconds or 0.0,
        run_dir=record.run_dir or "",
        submitted_at=record.submitted_at,
        completed_at=record.completed_at,
        error=record.error,
    )


@router.delete("/simulations/{run_id}")
def cancel_simulation(run_id: str):
    record = RUN_RECORDS.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    if record.status in {"completed", "failed"}:
        return {"run_id": run_id, "status": record.status}
    record.status = "cancelled"
    record.completed_at = datetime.now(timezone.utc).isoformat()
    return {"run_id": run_id, "status": "cancelled"}


@router.get("/simulations/{run_id}/stream")
async def stream_simulation_output(run_id: str):
    if run_id not in RUN_RECORDS:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    async def event_generator():
        queue = run_event_bus.subscribe(run_id)

        log_path = RUNS_DIR / run_id / "outputs" / "openmc_stdout.log"
        if log_path.exists():
            try:
                tail = log_path.read_text(encoding="utf-8").splitlines()[-200:]
                for line in tail:
                    event = {
                        "type": "openmc_log",
                        "run_id": run_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "content": line + "\n",
                    }
                    yield "event: openmc_log\n"
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


@router.post("/sweeps", response_model=SweepSubmitResponse, status_code=202)
def submit_sweep(request: SweepRequest):
    sweep_id = f"sweep_{uuid4().hex[:12]}"
    submitted_at = datetime.now(timezone.utc).isoformat()
    run_ids = []
    for idx, value in enumerate(request.values):
        run_id = f"{sweep_id}_p{idx:03d}"
        run_ids.append(run_id)
        spec = request.base_spec.dict()
        spec[request.parameter] = value
        record = RunRecord(run_id=run_id, spec=spec)
        RUN_RECORDS[run_id] = record
        thread = threading.Thread(target=_execute_openmc_run, args=(run_id, spec), daemon=True)
        thread.start()

    SWEEP_RECORDS[sweep_id] = {
        "sweep_id": sweep_id,
        "parameter": request.parameter,
        "values": request.values,
        "run_ids": run_ids,
        "submitted_at": submitted_at,
    }

    return SweepSubmitResponse(
        sweep_id=sweep_id,
        run_ids=run_ids,
        total_runs=len(run_ids),
        status="queued",
        submitted_at=submitted_at,
    )


@router.get("/sweeps/{sweep_id}", response_model=SweepResult)
def get_sweep(sweep_id: str):
    sweep = SWEEP_RECORDS.get(sweep_id)
    if not sweep:
        raise HTTPException(status_code=404, detail=f"Sweep {sweep_id} not found")

    run_ids = sweep["run_ids"]
    runs = [RUN_RECORDS.get(run_id) for run_id in run_ids if run_id in RUN_RECORDS]
    completed_runs = sum(1 for r in runs if r and r.status == "completed")
    status = "completed" if completed_runs == len(run_ids) else "running"
    if any(r and r.status == "failed" for r in runs):
        status = "partial"

    results = []
    for value, run_id in zip(sweep["values"], run_ids):
        rec = RUN_RECORDS.get(run_id)
        results.append(
            {
                "parameter_value": value,
                "run_id": run_id,
                "status": rec.status if rec else "missing",
                "keff": rec.keff if rec else 0.0,
                "keff_std": rec.keff_std if rec else 0.0,
            }
        )

    return SweepResult(
        sweep_id=sweep_id,
        parameter=sweep["parameter"],
        total_runs=len(run_ids),
        completed_runs=completed_runs,
        status=status,
        results=results,
        submitted_at=sweep["submitted_at"],
    )


@router.get("/runs")
def query_runs(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    records = list(RUN_RECORDS.values())
    if status:
        records = [r for r in records if r.status == status]
    records = records[offset : offset + limit]
    return {
        "total": len(RUN_RECORDS),
        "limit": limit,
        "offset": offset,
        "runs": [
            {
                "run_id": r.run_id,
                "status": r.status,
                "keff": r.keff,
                "keff_std": r.keff_std,
                "runtime_seconds": r.runtime_seconds,
                "submitted_at": r.submitted_at,
            }
            for r in records
        ],
    }


@router.post("/runs/compare")
def compare_runs(request: CompareRequest):
    runs = [RUN_RECORDS.get(run_id) for run_id in request.run_ids]
    if not all(runs):
        raise HTTPException(status_code=404, detail="One or more runs not found")
    keff_values = [r.keff or 0.0 for r in runs]
    keff_stds = [r.keff_std or 0.0 for r in runs]
    return {
        "num_runs": len(runs),
        "keff_values": keff_values,
        "keff_stds": keff_stds,
        "keff_mean": sum(keff_values) / max(1, len(keff_values)),
        "keff_std_dev": 0.0,
        "keff_min": min(keff_values) if keff_values else 0.0,
        "keff_max": max(keff_values) if keff_values else 0.0,
        "reactivity_span": (max(keff_values) - min(keff_values)) if keff_values else 0.0,
        "runs": [
            {
                "run_id": r.run_id,
                "keff": r.keff,
                "keff_std": r.keff_std,
                "spec": r.spec,
            }
            for r in runs
        ],
    }


@router.get("/statistics")
def get_statistics():
    records = list(RUN_RECORDS.values())
    completed_runs = [r for r in records if r.status == "completed"]
    failed_runs = [r for r in records if r.status == "failed"]
    running_runs = [r for r in records if r.status == "running"]
    avg_runtime = (
        sum(r.runtime_seconds or 0.0 for r in completed_runs) / max(1, len(completed_runs))
    )
    return {
        "total_runs": len(records),
        "completed_runs": len(completed_runs),
        "failed_runs": len(failed_runs),
        "running_runs": len(running_runs),
        "total_sweeps": len(SWEEP_RECORDS),
        "average_runtime_seconds": avg_runtime,
        "recent_runs": [
            {
                "run_id": r.run_id,
                "status": r.status,
                "keff": r.keff,
                "submitted_at": r.submitted_at,
            }
            for r in records[-5:]
        ],
    }


@router.get("/health")
def health_check():
    openmc_available = True
    openmc_version = None
    try:
        import openmc  # type: ignore

        openmc_version = openmc.__version__
    except Exception:
        openmc_available = False

    services = {
        "openmc": openmc_available,
        "mongodb": False,
        "nuclear_data": bool(os.getenv("OPENMC_CROSS_SECTIONS")),
        "openmc_version": openmc_version,
    }

    status = "healthy" if openmc_available else "limited"

    return {
        "status": status,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
        "runs_directory": str(RUNS_DIR.absolute()),
        "available_runs": len(list(RUNS_DIR.glob("*"))) if RUNS_DIR.exists() else 0,
    }


@router.get("/simulations/{run_id}/files")
def list_run_files(run_id: str):
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run directory not found for {run_id}")

    files = []
    for item in run_dir.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(run_dir)
            files.append(
                {
                    "path": str(rel_path),
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc).isoformat(),
                }
            )
    return {"run_id": run_id, "files": files}


@router.get("/simulations/{run_id}/files/{file_path:path}")
def download_run_file(run_id: str, file_path: str):
    run_dir = RUNS_DIR / run_id
    file_full_path = run_dir / file_path
    if not str(file_full_path.resolve()).startswith(str(run_dir.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    if not file_full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_full_path)

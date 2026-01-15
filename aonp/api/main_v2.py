"""
v2 FastAPI application for AONP.

This version factors functionality into modular routers and adds
dedicated endpoints for OpenMC geometry visualization.
"""

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from aonp.api.terminal_streamer import terminal_broadcaster, install_terminal_interceptor
from aonp.api.geometry_router import router as geometry_router
from aonp.api.openmc_router import router as openmc_router, set_event_loop as set_openmc_event_loop
from aonp.api.query_router import router as query_router, set_event_loop as set_query_event_loop


app = FastAPI(
    title="AONP API v2",
    description="Agent-Orchestrated Neutronics Platform (modular routers, geometry visualization)",
    version="0.2.0",
)


# CORS configuration kept compatible with existing frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize terminal streaming on startup (same behaviour as v1)."""
    loop = asyncio.get_event_loop()
    terminal_broadcaster.set_event_loop(loop)
    set_openmc_event_loop(loop)
    set_query_event_loop(loop)

    install_terminal_interceptor()
    print("🚀 AONP API v2 Server Started")
    print("📡 Terminal streaming enabled at /terminal/stream")
    print("🧱 Geometry visualization endpoints mounted at /geometry")


# Mount routers
app.include_router(geometry_router)
app.include_router(openmc_router)
app.include_router(query_router)


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with high-level API information."""
    return {
        "name": "AONP API v2",
        "version": "0.2.0",
        "description": "High-integrity neutronics simulation platform with geometry visualization endpoints",
        "routers": {
            "geometry": "/geometry",
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


@app.get("/terminal/stream")
async def stream_terminal_output():
    """
    Stream ALL backend terminal output in real-time (stdout + stderr).

    Mirrors the behaviour of the v1 `/terminal/stream` endpoint so
    existing frontend components can be reused.
    """

    async def event_generator():
        """Generate SSE events from terminal output."""
        queue = terminal_broadcaster.subscribe()

        try:
            # Initial connection message
            yield f"data: {json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'stream': 'system', 'content': '[Connected to terminal stream]\\\\n'})}\n\n"

            while True:
                try:
                    # Wait for next event (30 second timeout for keepalive)
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # SSE keepalive comment
                    yield ": keepalive\n\n"
        finally:
            terminal_broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/v1/terminal/stream")
async def stream_terminal_output_v1():
    """Compatibility alias for frontend terminal stream."""
    return await stream_terminal_output()


@app.get("/health")
async def health_check():
    """Basic health check with OpenMC availability and router status."""
    import sys

    # Check OpenMC availability
    try:
        import openmc  # type: ignore

        openmc_available = True
        openmc_version = openmc.__version__
    except Exception:
        openmc_available = False
        openmc_version = None

    return {
        "status": "healthy",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "openmc_available": openmc_available,
        "openmc_version": openmc_version,
        "routers": {
            "geometry": True,
        },
        "terminal_streaming": True,
        "subscribers": len(terminal_broadcaster.subscribers),
    }


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🖥️  AONP v2 API Server")
    print("=" * 60)
    print("Running on: http://localhost:8001")
    print("Root endpoint: http://localhost:8001/")
    print("Geometry endpoints: http://localhost:8001/geometry")
    print("Terminal stream: http://localhost:8001/terminal/stream")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8001)


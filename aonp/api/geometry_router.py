"""
Geometry visualization API router for OpenMC runs.

This router exposes lightweight endpoints that surface the generated
OpenMC XML inputs (geometry/materials/settings) for a given run.
These XML payloads can be consumed directly by frontend visualizers.
"""

from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse


router = APIRouter(prefix="/geometry", tags=["geometry"])


def _get_run_inputs_dir(run_id: str) -> Path:
    """
    Resolve and validate the inputs directory for a run.

    Directory layout is defined in `aonp.core.bundler.create_run_bundle`:
        runs/<run_id>/inputs/{materials.xml, geometry.xml, settings.xml}
    """
    run_dir = Path("runs") / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    inputs_dir = run_dir / "inputs"
    if not inputs_dir.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Inputs directory missing for run: {run_id}",
        )

    return inputs_dir


@router.get("/runs/{run_id}/files")
async def list_geometry_files(run_id: str):
    """
    List available OpenMC input XML files for a run.

    Returns basic metadata (paths and existence flags) that a frontend
    can use to decide which resources to request for visualization.
    """
    inputs_dir = _get_run_inputs_dir(run_id)

    geometry_xml = inputs_dir / "geometry.xml"
    materials_xml = inputs_dir / "materials.xml"
    settings_xml = inputs_dir / "settings.xml"

    def _file_info(path: Path) -> dict:
        if not path.exists():
            return {"exists": False, "path": str(path), "size": None, "mtime": None}

        stat = path.stat()
        return {
            "exists": True,
            "path": str(path),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        }

    return {
        "run_id": run_id,
        "inputs_dir": str(inputs_dir),
        "geometry_xml": _file_info(geometry_xml),
        "materials_xml": _file_info(materials_xml),
        "settings_xml": _file_info(settings_xml),
    }


@router.get(
    "/runs/{run_id}/xml",
    response_class=PlainTextResponse,
)
async def get_geometry_xml(
    run_id: str,
    file: Literal["geometry", "materials", "settings"] = Query(
        "geometry",
        description="Which OpenMC input XML file to return.",
    ),
) -> PlainTextResponse:
    """
    Fetch the raw OpenMC input XML for a run.

    This endpoint is designed for frontend geometry viewers that can
    consume OpenMC XML directly and render plots client-side or via
    specialized libraries.
    """
    inputs_dir = _get_run_inputs_dir(run_id)

    filename_map = {
        "geometry": "geometry.xml",
        "materials": "materials.xml",
        "settings": "settings.xml",
    }

    xml_path = inputs_dir / filename_map[file]
    if not xml_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"{xml_path.name} not found for run: {run_id}",
        )

    try:
        contents = xml_path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read {xml_path.name}: {exc}",
        ) from exc

    # Use application/xml so browsers / viewers treat it as XML
    return PlainTextResponse(content=contents, media_type="application/xml")


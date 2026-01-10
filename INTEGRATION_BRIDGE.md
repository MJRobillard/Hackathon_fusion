# AONP Integration Bridge
**Connecting Agent Team (Playground) ↔ OpenMC Team (Main)**

**Date**: 2026-01-10  
**Status**: Design Document

---

## 🎯 The Problem

Two teams built independent systems with **incompatible interfaces**:

| Aspect | Agent Team (Playground) | OpenMC Team (Main) |
|--------|-------------------------|---------------------|
| **Spec Format** | Simplified natural language | Structured OpenMC definitions |
| **MongoDB** | Basic (studies, runs, summaries) | Advanced (with phases, workers, leases) |
| **Execution** | Mocked (`random.gauss()`) | Real OpenMC (`aonp/runner/entrypoint.py`) |
| **Location** | `Playground/backend/` | `aonp/` |

---

## 🏗️ Integration Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    USER & FRONTEND                             │
│                   (Next.js UI)                                 │
└───────────────────────────┬────────────────────────────────────┘
                            │ HTTP POST
                            │
┌───────────────────────────▼────────────────────────────────────┐
│              PLAYGROUND/BACKEND (Agent Team)                   │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  FastAPI (Playground/backend/api/main.py)                │ │
│  │  - POST /api/v1/requests                                 │ │
│  │  - Natural language processing                           │ │
│  └──────┬───────────────────────────────────────────────────┘ │
│         │                                                      │
│  ┌──────▼───────────────────────────────────────────────────┐ │
│  │  LangGraph Agents (aonp_agents.py)                       │ │
│  │  - Intent classifier                                     │ │
│  │  - Study planner                                         │ │
│  │  - Results analyzer                                      │ │
│  └──────┬───────────────────────────────────────────────────┘ │
│         │                                                      │
│  ┌──────▼───────────────────────────────────────────────────┐ │
│  │  Agent Tools (agent_tools.py)                            │ │
│  │  - submit_study() ← Uses simplified StudySpec           │ │
│  │  - Currently calls mock_openmc_execution()              │ │
│  └──────┬───────────────────────────────────────────────────┘ │
└─────────┼────────────────────────────────────────────────────┘
          │
          │ ⚠️  INTEGRATION POINT (Currently mocked)
          │
┌─────────▼────────────────────────────────────────────────────┐
│              🔧 ADAPTER LAYER (NEW)                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  spec_translator.py                                    │  │
│  │  - translate_simple_to_openmc(simple_spec)            │  │
│  │  - map_geometry_templates()                           │  │
│  │  - map_material_definitions()                         │  │
│  └────────┬───────────────────────────────────────────────┘  │
└───────────┼──────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────┐
│              MAIN/AONP (OpenMC Team)                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Bundler (aonp/core/bundler.py)                       │  │
│  │  - create_run_bundle() ← Needs full StudySpec         │  │
│  └────────┬───────────────────────────────────────────────┘  │
│           │                                                   │
│  ┌────────▼───────────────────────────────────────────────┐  │
│  │  Runner (aonp/runner/entrypoint.py)                    │  │
│  │  - run_simulation() ← Executes real OpenMC            │  │
│  └────────┬───────────────────────────────────────────────┘  │
│           │                                                   │
│  ┌────────▼───────────────────────────────────────────────┐  │
│  │  Extractor (aonp/core/extractor.py)                    │  │
│  │  - extract() ← Parses statepoint.h5                   │  │
│  └────────┬───────────────────────────────────────────────┘  │
└───────────┼──────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────┐
│                    MONGODB ATLAS                             │
│  - studies (Team 1 schema)                                   │
│  - runs (Team 1 schema with phases/leases)                   │
│  - summaries (Shared by both)                                │
│  - requests (Team 2 - agent tracking)                        │
│  - agent_traces (Team 2 - execution logs)                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Solution: Build an Adapter Layer

### Option 1: Adapter Inside Playground (Recommended for MVP)

**File**: `Playground/backend/openmc_adapter.py`

```python
"""
Adapter: Translate simplified agent specs → structured OpenMC specs
Then call the real OpenMC bundler/runner
"""

import sys
sys.path.append("../../aonp")  # Access main project

from pathlib import Path
from aonp.schemas.study import StudySpec as OpenMCStudySpec
from aonp.schemas.study import MaterialSpec, NuclideSpec, GeometrySpec, SettingsSpec, NuclearDataSpec
from aonp.core.bundler import create_run_bundle
from aonp.runner.entrypoint import run_simulation

# Geometry templates (map natural language → script files)
GEOMETRY_TEMPLATES = {
    "PWR pin cell": "../../examples/pincell_geometry.py",
    "BWR assembly": "../../examples/bwr_assembly_geometry.py",
    # Add more templates as needed
}

# Material libraries (map material names → nuclide definitions)
MATERIAL_LIBRARY = {
    "UO2": {
        "4.5% enriched": [
            {"name": "U235", "fraction": 0.045, "fraction_type": "ao"},
            {"name": "U238", "fraction": 0.955, "fraction_type": "ao"},
            {"name": "O16", "fraction": 2.0, "fraction_type": "ao"}
        ]
    },
    "Zircaloy": [
        {"name": "Zr90", "fraction": 0.98, "fraction_type": "ao"},
        {"name": "Sn120", "fraction": 0.02, "fraction_type": "ao"}
    ],
    "Water": [
        {"name": "H1", "fraction": 2.0, "fraction_type": "ao"},
        {"name": "O16", "fraction": 1.0, "fraction_type": "ao"}
    ]
}

def translate_simple_to_openmc(simple_spec: dict) -> OpenMCStudySpec:
    """
    Translate simplified agent spec → structured OpenMC spec
    
    Input (from agents):
    {
        "geometry": "PWR pin cell",
        "materials": ["UO2", "Zircaloy", "Water"],
        "enrichment_pct": 4.5,
        "temperature_K": 600,
        "particles": 10000,
        "batches": 50
    }
    
    Output: Full OpenMCStudySpec with materials/geometry/settings/nuclear_data
    """
    
    # 1. Map geometry
    geometry_name = simple_spec["geometry"]
    if geometry_name not in GEOMETRY_TEMPLATES:
        raise ValueError(f"Unknown geometry: {geometry_name}")
    
    geometry = GeometrySpec(
        type="script",
        script=GEOMETRY_TEMPLATES[geometry_name]
    )
    
    # 2. Build materials
    materials = {}
    temperature_K = simple_spec.get("temperature_K", 600)
    enrichment = simple_spec.get("enrichment_pct", 4.5)
    
    for mat_name in simple_spec["materials"]:
        if mat_name == "UO2":
            # Use enrichment-specific definition
            nuclides = [
                NuclideSpec(name="U235", fraction=enrichment/100, fraction_type="ao"),
                NuclideSpec(name="U238", fraction=(100-enrichment)/100, fraction_type="ao"),
                NuclideSpec(name="O16", fraction=2.0, fraction_type="ao")
            ]
            materials["fuel"] = MaterialSpec(
                density=10.4,
                density_units="g/cm3",
                temperature=temperature_K,
                nuclides=nuclides
            )
        elif mat_name == "Zircaloy":
            materials["clad"] = MaterialSpec(
                density=6.55,
                density_units="g/cm3",
                temperature=temperature_K,
                nuclides=[
                    NuclideSpec(name="Zr90", fraction=0.98, fraction_type="ao"),
                    NuclideSpec(name="Sn120", fraction=0.02, fraction_type="ao")
                ]
            )
        elif mat_name == "Water":
            materials["moderator"] = MaterialSpec(
                density=0.74,
                density_units="g/cm3",
                temperature=temperature_K,
                nuclides=[
                    NuclideSpec(name="H1", fraction=2.0, fraction_type="ao"),
                    NuclideSpec(name="O16", fraction=1.0, fraction_type="ao")
                ]
            )
    
    # 3. Settings
    settings = SettingsSpec(
        batches=simple_spec.get("batches", 50),
        inactive=10,
        particles=simple_spec.get("particles", 10000),
        seed=42
    )
    
    # 4. Nuclear data (hardcoded for MVP)
    nuclear_data = NuclearDataSpec(
        library="endfb71",
        path="/usr/local/share/openmc/data/endfb71"  # Adjust for your system
    )
    
    # 5. Create full spec
    openmc_spec = OpenMCStudySpec(
        name=f"{geometry_name} - {enrichment}% enrichment",
        description=f"Auto-generated from agent request",
        materials=materials,
        geometry=geometry,
        settings=settings,
        nuclear_data=nuclear_data
    )
    
    return openmc_spec


def execute_real_openmc(simple_spec: dict) -> dict:
    """
    Replace mock_openmc_execution() with real OpenMC execution
    
    1. Translate spec
    2. Create bundle
    3. Run simulation
    4. Extract results
    5. Return summary
    """
    
    # Translate
    openmc_spec = translate_simple_to_openmc(simple_spec)
    
    # Create bundle
    run_dir, spec_hash = create_run_bundle(
        study=openmc_spec,
        base_dir=Path("../../runs")
    )
    
    # Execute
    import time
    start = time.time()
    exit_code = run_simulation(run_dir)
    runtime = time.time() - start
    
    if exit_code != 0:
        return {
            "status": "failed",
            "error": "OpenMC execution failed",
            "runtime_seconds": runtime
        }
    
    # Extract results (simplified - you'd use extractor.py)
    # For MVP, read from manifest or statepoint
    manifest_path = run_dir / "run_manifest.json"
    with open(manifest_path) as f:
        import json
        manifest = json.load(f)
    
    # TODO: Use aonp.core.extractor to parse statepoint.h5
    # For now, return placeholder
    return {
        "keff": 1.287,  # Extract from statepoint
        "keff_std": 0.0003,
        "runtime_seconds": runtime,
        "status": "completed",
        "run_dir": str(run_dir),
        "spec_hash": spec_hash
    }
```

**Then update `agent_tools.py`:**

```python
# Replace this import
# from agent_tools import mock_openmc_execution

# With this
from openmc_adapter import execute_real_openmc

# In submit_study(), replace:
# result = mock_openmc_execution(spec)

# With:
result = execute_real_openmc(spec.model_dump())
```

---

### Option 2: Expose OpenMC as HTTP API (More Decoupled)

**File**: `aonp/api/openmc_service.py` (in main project)

```python
"""
OpenMC HTTP API - exposes bundler/runner as REST service
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path

from aonp.core.bundler import create_run_bundle
from aonp.runner.entrypoint import run_simulation
from aonp.schemas.study import StudySpec

app = FastAPI(title="OpenMC Execution Service")

class ExecuteRequest(BaseModel):
    study_spec: dict  # Full OpenMC StudySpec as JSON

class ExecuteResponse(BaseModel):
    run_id: str
    spec_hash: str
    status: str
    keff: float
    keff_std: float
    runtime_seconds: float

@app.post("/api/v1/execute", response_model=ExecuteResponse)
def execute_simulation(req: ExecuteRequest):
    """Execute OpenMC simulation and return results"""
    
    # Parse spec
    spec = StudySpec(**req.study_spec)
    
    # Create bundle
    run_dir, spec_hash = create_run_bundle(spec, base_dir=Path("runs"))
    
    # Run
    exit_code = run_simulation(run_dir)
    
    if exit_code != 0:
        raise HTTPException(status_code=500, detail="Simulation failed")
    
    # Extract results (use extractor)
    # ...
    
    return ExecuteResponse(
        run_id=run_dir.name,
        spec_hash=spec_hash,
        status="completed",
        keff=1.287,
        keff_std=0.0003,
        runtime_seconds=5.0
    )
```

**Then Playground calls this API:**

```python
# In Playground/backend/openmc_adapter.py

import requests

def execute_real_openmc(simple_spec: dict) -> dict:
    # Translate
    openmc_spec = translate_simple_to_openmc(simple_spec)
    
    # Call OpenMC service
    response = requests.post(
        "http://localhost:8001/api/v1/execute",
        json={"study_spec": openmc_spec.model_dump()}
    )
    
    return response.json()
```

---

## 📋 Integration Checklist

### Phase 1: Adapter Layer (2-3 hours)
- [ ] Create `Playground/backend/openmc_adapter.py`
- [ ] Implement `translate_simple_to_openmc()`
- [ ] Define geometry templates mapping
- [ ] Define material library mapping
- [ ] Test translation with sample specs

### Phase 2: Connect Real Execution (2 hours)
- [ ] Import main project's `aonp` modules
- [ ] Replace `mock_openmc_execution()` with `execute_real_openmc()`
- [ ] Handle errors and propagate status
- [ ] Test end-to-end execution

### Phase 3: Results Extraction (1-2 hours)
- [ ] Import `aonp.core.extractor`
- [ ] Parse statepoint.h5 files
- [ ] Extract keff, keff_std properly
- [ ] Store full results in MongoDB

### Phase 4: MongoDB Schema Alignment (1 hour)
- [ ] Decide: use Team 1's schema or keep separate?
- [ ] Update Playground to write to Team 1's collections
- [ ] Or: keep separate and sync via adapter

---

## 🎯 Recommended Approach for Hackathon

**Keep it simple:**

1. **Build adapter in Playground** (`openmc_adapter.py`)
2. **Import main project modules directly** (no HTTP API needed)
3. **Run OpenMC locally** via Python subprocess
4. **Share MongoDB** - both write to same collections

**Timeline**: 4-6 hours to fully integrate

---

## 🚨 Current Blockers

1. **Geometry templates don't exist yet** - need to create library of reusable geometries
2. **Material definitions incomplete** - need standard library
3. **Nuclear data path hardcoded** - needs config
4. **No error handling** for translation failures

---

## ✅ Next Steps

1. **Review this document** with both teams
2. **Pick integration approach** (Option 1 or 2)
3. **Define geometry/material templates**
4. **Implement adapter**
5. **Test with single simulation**
6. **Deploy integrated system**

---

**Questions? Contact integration lead.**


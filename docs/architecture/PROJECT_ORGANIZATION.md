# AONP Project Organization

## Folder Structure

```
Hackathon_fusion/
├── aonp/                          # Backend package
│   ├── api/                       # FastAPI apps
│   ├── core/                      # Bundling + extraction
│   ├── runner/                    # OpenMC execution
│   ├── schemas/                   # Pydantic models
│   └── examples/                  # Example inputs
├── frontend/                      # Next.js app
├── docs/                          # Consolidated documentation
├── runs/                          # Simulation outputs (created at runtime)
├── scripts/                       # Operational scripts
├── tests/                         # Test suites
└── verification_studies/          # Validation studies
```

## Integration Points

### 1) Spec Translation

**Location**: `aonp/runner/openmc_adapter.py`

**Purpose**: Translate simplified specs into full `StudySpec` objects.

### 2) Execution Flow

```
Frontend/Client
    ↓
aonp/api/main_v2.py (FastAPI)
    ↓
aonp/runner/openmc_adapter.py
    ↓
aonp/core/bundler.py
    ↓
aonp/runner/entrypoint.py
    ↓
aonp/core/extractor.py
```

### 3) Run Artifacts

Runs are written under `runs/` with the following layout:

```
runs/run_<id>/
├── study_spec.json
├── run_manifest.json
├── nuclear_data.ref.json
├── inputs/
└── outputs/
```

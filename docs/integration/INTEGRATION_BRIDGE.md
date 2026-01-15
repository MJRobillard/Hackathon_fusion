# AONP Integration Bridge

This document describes the simplified integration path now that the backend has been consolidated.

## Current Integration Architecture

```
Frontend/Client
    ↓
aonp/api/main_v2.py
    ↓
aonp/runner/openmc_adapter.py
    ↓
aonp/core/bundler.py
    ↓
aonp/runner/entrypoint.py
    ↓
aonp/core/extractor.py
```

## Adapter Responsibilities

- Translate simplified specs into full `StudySpec` objects
- Create run bundles under `runs/`
- Execute OpenMC and collect results

## Quick Start (Backend)

```bash
python aonp/api/main_v2.py
```

The health check is exposed at `/health`.

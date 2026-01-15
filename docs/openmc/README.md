# OpenMC Documentation

## Core Modules

- `aonp/core/bundler.py`: creates run bundles and OpenMC XML inputs
- `aonp/runner/entrypoint.py`: executes OpenMC in a run bundle
- `aonp/runner/openmc_adapter.py`: translates simplified specs to `StudySpec`

## Runs Directory

Runs are created under `runs/` at runtime. Geometry XML files are accessed by
`aonp/api/geometry_router.py`.

## Environment

- `OPENMC_CROSS_SECTIONS`: required for real OpenMC execution

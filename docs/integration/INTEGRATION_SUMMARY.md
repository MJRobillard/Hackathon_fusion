# AONP Integration Summary

This repository now uses a consolidated backend layout with the adapter in `aonp/runner/openmc_adapter.py` and the primary API entrypoint in `aonp/api/main_v2.py`.

## Key Integration Points

- **Adapter layer**: `aonp/runner/openmc_adapter.py`
- **Bundling**: `aonp/core/bundler.py`
- **Execution**: `aonp/runner/entrypoint.py`
- **Extraction**: `aonp/core/extractor.py`
- **API**: `aonp/api/main_v2.py`

## Test Coverage

- Adapter tests: `tests/test_adapter_e2e.py`
- Full pipeline tests: `tests/test_integration_complete.py`

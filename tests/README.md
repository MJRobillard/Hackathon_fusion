# AONP Test Suite

## Test Categories

### 1. Core Tests (`test_core_only.py`)

**No OpenMC required** - Tests fundamental functionality:

- ✅ Pydantic schema validation
- ✅ Deterministic hashing (SHA256)
- ✅ Hash stability (format-independent)
- ✅ Hash sensitivity (detects changes)
- ✅ Input validation (catches errors)

**Run**:
```bash
python tests/test_core_only.py
```

**Expected output**:
```
✓ Study validation passed
✓ Hash computation passed
✓ Hash stability passed
✓ Hash sensitivity passed
✓ Validation correctly rejected negative density
✓ Validation correctly rejected invalid fraction sum

✅ All core tests passed!
```

### 2. Acceptance Tests (`test_acceptance.py`)

**Requires OpenMC + nuclear data** - Tests full pipeline:

- ✅ Study loading and validation
- ✅ Bundle creation
- ✅ XML generation
- ✅ OpenMC execution
- ✅ Result extraction
- ✅ End-to-end reproducibility

**Run**:
```bash
python tests/test_acceptance.py
```

**Prerequisites**:
1. OpenMC installed: `pip install openmc`
2. Nuclear data available (ENDF/B-VII.1)
3. `OPENMC_CROSS_SECTIONS` environment variable set

**Expected output**:
```
✓ Reproducibility test passed
✓ Study validation passed
✓ Bundle creation passed
✓ Bundle structure validated
✓ OpenMC execution passed
✓ Result extraction passed
✓ Summary loading passed
✓ k-eff in expected range

✅ Full pipeline test passed!
```

## Running Tests with Pytest

Install pytest:
```bash
pip install pytest
```

Run all tests:
```bash
pytest tests/
```

Run specific test file:
```bash
pytest tests/test_core_only.py -v
```

Run with coverage:
```bash
pip install pytest-cov
pytest tests/ --cov=aonp --cov-report=html
```

## Continuous Integration

For CI/CD pipelines (GitHub Actions, GitLab CI, etc.):

**Minimal CI (no OpenMC)**:
```yaml
- name: Run core tests
  run: |
    pip install -r requirements.txt
    python tests/test_core_only.py
```

**Full CI (with OpenMC)**:
```yaml
- name: Install OpenMC
  run: |
    conda install -c conda-forge openmc
    
- name: Download nuclear data
  run: |
    # Download and extract ENDF/B-VII.1
    # Set OPENMC_CROSS_SECTIONS environment variable
    
- name: Run acceptance tests
  run: |
    python tests/test_acceptance.py
```

## Test-Driven Development

When adding new features:

1. **Write test first** (in appropriate test file)
2. **Run test** (should fail)
3. **Implement feature**
4. **Run test** (should pass)
5. **Refactor** if needed

Example:
```python
# tests/test_new_feature.py
def test_new_tally_generation():
    """Test tally XML generation."""
    study = create_study_with_tallies()
    bundle = create_run_bundle(study)
    
    tally_xml = bundle / "inputs" / "tallies.xml"
    assert tally_xml.exists()
    # ... more assertions
```

## Regression Testing

To prevent breaking changes, keep reference results:

```python
# tests/test_regression.py
def test_keff_regression():
    """Ensure k-eff hasn't changed for reference case."""
    REFERENCE_KEFF = 1.60991
    TOLERANCE = 0.00300  # 3 sigma
    
    result = run_reference_case()
    assert abs(result['keff'] - REFERENCE_KEFF) < TOLERANCE
```

## Performance Testing

For benchmarking:

```python
import time

def test_performance():
    """Ensure bundle creation is fast."""
    start = time.time()
    create_run_bundle(study)
    elapsed = time.time() - start
    
    assert elapsed < 1.0, f"Bundle creation too slow: {elapsed:.2f}s"
```

## Troubleshooting

### OpenMC Not Found

**Error**: `ImportError: No module named 'openmc'`

**Solution**:
- Install OpenMC: `pip install openmc`
- Or use conda: `conda install -c conda-forge openmc`
- On Windows: Use WSL or Docker

### Nuclear Data Not Found

**Error**: `FileNotFoundError: cross_sections.xml not found`

**Solution**:
```bash
# Download ENDF/B-VII.1
bash install_openmc_conda.sh

# Or set environment variable
export OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml
```

### Geometry Script Not Found

**Error**: `FileNotFoundError: Geometry script not found`

**Solution**:
- Ensure script path in YAML is correct
- Use absolute path or path relative to project root
- Check file exists: `ls aonp/examples/pincell_geometry.py`

## Test Coverage Goals

| Component | Target Coverage |
|-----------|----------------|
| Schemas | 100% |
| Bundler | 95% |
| Runner | 80% |
| Extractor | 90% |
| API | 85% |

## Writing Good Tests

**DO**:
- Test one thing per test
- Use descriptive test names
- Include both positive and negative cases
- Clean up temporary files
- Make tests deterministic

**DON'T**:
- Rely on external services
- Use hardcoded paths (use tempfile)
- Test implementation details
- Make tests dependent on each other

## Example Test Template

```python
def test_feature_name():
    """
    Test that feature works correctly.
    
    Given: Initial state
    When: Action is performed
    Then: Expected result occurs
    """
    # Arrange
    study = create_test_study()
    
    # Act
    result = perform_action(study)
    
    # Assert
    assert result.is_valid()
    assert result.value == expected_value
```


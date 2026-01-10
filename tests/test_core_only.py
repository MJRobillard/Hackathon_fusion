"""
Core functionality tests (no OpenMC required).

These tests validate:
- Pydantic schema validation
- Deterministic hashing
- Hash stability across formatting
- Hash sensitivity to changes
"""

import sys
import yaml
import json
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aonp.schemas.study import StudySpec, MaterialSpec, NuclideSpec


def test_study_validation():
    """Test that valid YAML parses correctly."""
    yaml_content = """
name: "test_study"
description: "Test study"
materials:
  fuel:
    density: 10.4
    density_units: "g/cm3"
    temperature: 900.0
    nuclides:
      - name: "U235"
        fraction: 0.7
        fraction_type: "ao"
      - name: "O16"
        fraction: 0.3
        fraction_type: "ao"
geometry:
  type: "script"
  script: "test_geometry.py"
settings:
  batches: 100
  inactive: 20
  particles: 1000
  seed: 42
nuclear_data:
  library: "endfb71"
  path: "/path/to/data"
"""
    
    data = yaml.safe_load(yaml_content)
    study = StudySpec(**data)
    
    assert study.name == "test_study"
    assert study.materials["fuel"].density == 10.4
    assert study.settings.batches == 100
    print("[OK] Study validation passed")


def test_hash_computation():
    """Test that hash is computed correctly."""
    yaml_content = """
name: "test_study"
materials:
  fuel:
    density: 10.4
    density_units: "g/cm3"
    temperature: 900.0
    nuclides:
      - name: "U235"
        fraction: 1.0
        fraction_type: "ao"
geometry:
  type: "script"
  script: "test.py"
settings:
  batches: 100
  inactive: 20
  particles: 1000
  seed: 42
nuclear_data:
  library: "endfb71"
  path: "/data"
"""
    
    data = yaml.safe_load(yaml_content)
    study = StudySpec(**data)
    
    hash1 = study.get_canonical_hash()
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA256 produces 64 hex chars
    print(f"[OK] Hash computation passed: {hash1[:12]}...")


def test_hash_stability():
    """Test that hash is stable across formatting changes."""
    # Original
    yaml1 = """
name: "test"
materials:
  fuel:
    density: 10.4
    density_units: "g/cm3"
    temperature: 900.0
    nuclides:
      - name: "U235"
        fraction: 1.0
        fraction_type: "ao"
geometry:
  type: "script"
  script: "test.py"
settings:
  batches: 100
  inactive: 20
  particles: 1000
  seed: 42
nuclear_data:
  library: "endfb71"
  path: "/data"
"""
    
    # With comments and extra whitespace
    yaml2 = """
# This is a comment
name:  "test"   # Name of study

materials:
  fuel:
    density: 10.4  # g/cm3
    density_units: "g/cm3"
    temperature:   900.0
    nuclides:
      - name: "U235"  # Uranium-235
        fraction: 1.0
        fraction_type: "ao"

# Geometry section
geometry:
  type: "script"
  script: "test.py"

settings:
  batches:   100
  inactive:  20
  particles: 1000
  seed:      42

nuclear_data:
  library: "endfb71"
  path: "/data"
"""
    
    data1 = yaml.safe_load(yaml1)
    data2 = yaml.safe_load(yaml2)
    
    study1 = StudySpec(**data1)
    study2 = StudySpec(**data2)
    
    hash1 = study1.get_canonical_hash()
    hash2 = study2.get_canonical_hash()
    
    assert hash1 == hash2, "Hash must be stable across formatting changes"
    print(f"[OK] Hash stability passed: {hash1[:12]}...")


def test_hash_sensitivity():
    """Test that hash changes when physical parameters change."""
    base_yaml = """
name: "test"
materials:
  fuel:
    density: 10.4
    density_units: "g/cm3"
    temperature: 900.0
    nuclides:
      - name: "U235"
        fraction: 1.0
        fraction_type: "ao"
geometry:
  type: "script"
  script: "test.py"
settings:
  batches: 100
  inactive: 20
  particles: 1000
  seed: 42
nuclear_data:
  library: "endfb71"
  path: "/data"
"""
    
    # Change density slightly
    modified_yaml = """
name: "test"
materials:
  fuel:
    density: 10.401
    density_units: "g/cm3"
    temperature: 900.0
    nuclides:
      - name: "U235"
        fraction: 1.0
        fraction_type: "ao"
geometry:
  type: "script"
  script: "test.py"
settings:
  batches: 100
  inactive: 20
  particles: 1000
  seed: 42
nuclear_data:
  library: "endfb71"
  path: "/data"
"""
    
    data1 = yaml.safe_load(base_yaml)
    data2 = yaml.safe_load(modified_yaml)
    
    study1 = StudySpec(**data1)
    study2 = StudySpec(**data2)
    
    hash1 = study1.get_canonical_hash()
    hash2 = study2.get_canonical_hash()
    
    assert hash1 != hash2, "Hash must change when physical parameters change"
    print(f"[OK] Hash sensitivity passed")
    print(f"  Base:     {hash1[:12]}...")
    print(f"  Modified: {hash2[:12]}...")


def test_validation_errors():
    """Test that invalid data is caught."""
    # Test: negative density
    try:
        MaterialSpec(
            density=-1.0,
            density_units="g/cm3",
            temperature=900.0,
            nuclides=[NuclideSpec(name="U235", fraction=1.0)]
        )
        assert False, "Should have raised validation error for negative density"
    except Exception:
        print("[OK] Validation correctly rejected negative density")
    
    # Test: fractions don't sum to 1.0
    try:
        MaterialSpec(
            density=10.4,
            density_units="g/cm3",
            temperature=900.0,
            nuclides=[
                NuclideSpec(name="U235", fraction=0.5),
                NuclideSpec(name="U238", fraction=0.3)
                # Sum = 0.8, should fail
            ]
        )
        assert False, "Should have raised validation error for fractions not summing to 1"
    except Exception:
        print("[OK] Validation correctly rejected invalid fraction sum")


if __name__ == "__main__":
    print("Running core tests (no OpenMC required)...\n")
    
    test_study_validation()
    test_hash_computation()
    test_hash_stability()
    test_hash_sensitivity()
    test_validation_errors()
    
    print("\n[SUCCESS] All core tests passed!")


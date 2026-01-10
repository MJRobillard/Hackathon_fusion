"""
Pydantic models for study specifications with deterministic hashing.
"""

import json
import hashlib
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class NuclideSpec(BaseModel):
    """Specification for a single nuclide in a material."""
    
    name: str = Field(..., pattern=r'^[A-Z][a-z]?\d+$', description="Nuclide name (e.g., U235, H1)")
    fraction: float = Field(..., gt=0.0, le=1.0, description="Atomic or weight fraction")
    fraction_type: Literal["ao", "wo"] = Field(default="ao", description="Fraction type: ao=atomic, wo=weight")


class MaterialSpec(BaseModel):
    """Specification for a material."""
    
    density: float = Field(..., gt=0.0, description="Material density")
    density_units: Literal["g/cm3", "atom/b-cm"] = Field(default="g/cm3", description="Density units")
    temperature: float = Field(..., gt=0.0, description="Temperature in Kelvin")
    nuclides: List[NuclideSpec] = Field(..., min_length=1, description="List of nuclides in material")
    
    @field_validator('nuclides')
    @classmethod
    def validate_fractions(cls, v):
        """Ensure fractions sum to approximately 1.0."""
        total = sum(n.fraction for n in v)
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Nuclide fractions must sum to 1.0 (got {total:.4f})")
        return v


class SourceSpec(BaseModel):
    """Optional source specification."""
    
    type: Literal["point", "box"] = Field(default="point", description="Source type")
    position: List[float] = Field(default=[0.0, 0.0, 0.0], description="Source position [x, y, z]")
    energy: float = Field(default=1.0e6, description="Source energy in eV")


class GeometrySpec(BaseModel):
    """Geometry specification."""
    
    type: Literal["script", "inline"] = Field(default="script", description="Geometry definition type")
    script: Optional[str] = Field(default=None, description="Path to geometry script")
    
    @field_validator('script')
    @classmethod
    def validate_script(cls, v, info):
        """Ensure script is provided when type is 'script'."""
        if info.data.get('type') == 'script' and not v:
            raise ValueError("script path required when type='script'")
        return v


class SettingsSpec(BaseModel):
    """Monte Carlo simulation settings."""
    
    batches: int = Field(..., gt=0, description="Total number of batches")
    inactive: int = Field(..., ge=0, description="Number of inactive batches")
    particles: int = Field(..., gt=0, description="Particles per batch")
    seed: int = Field(default=42, description="Random number seed for reproducibility")
    source: Optional[SourceSpec] = Field(default=None, description="Optional custom source")
    
    @field_validator('inactive')
    @classmethod
    def validate_inactive(cls, v, info):
        """Ensure inactive < batches."""
        if 'batches' in info.data and v >= info.data['batches']:
            raise ValueError(f"inactive ({v}) must be less than batches ({info.data['batches']})")
        return v


class NuclearDataSpec(BaseModel):
    """Nuclear data library specification."""
    
    library: str = Field(..., description="Library identifier (e.g., 'endfb71')")
    path: str = Field(..., description="Path to nuclear data directory")
    temperature_method: Literal["interpolation", "nearest"] = Field(
        default="interpolation",
        description="Temperature interpolation method"
    )
    temperature_tolerance: float = Field(default=200.0, description="Temperature tolerance in Kelvin")


class StudySpec(BaseModel):
    """
    Complete specification for a neutronics study.
    
    This is the root model that contains all information needed to execute
    a reproducible OpenMC simulation.
    """
    
    name: str = Field(..., description="Study name")
    description: str = Field(default="", description="Study description")
    materials: Dict[str, MaterialSpec] = Field(..., min_length=1, description="Material definitions")
    geometry: GeometrySpec = Field(..., description="Geometry definition")
    settings: SettingsSpec = Field(..., description="Monte Carlo settings")
    nuclear_data: NuclearDataSpec = Field(..., description="Nuclear data library")
    
    def get_canonical_hash(self) -> str:
        """
        Generate deterministic SHA256 hash of study specification.
        
        This hash is:
        - Format-independent (YAML comments/whitespace don't affect it)
        - Order-independent (dictionary key order doesn't matter)
        - Reproducible (same input always produces same hash)
        
        Returns:
            64-character hexadecimal hash string
        """
        # Convert Pydantic model to dict
        data = self.model_dump()
        
        # Serialize to JSON with sorted keys, no whitespace
        canonical_json = json.dumps(
            data,
            sort_keys=True,           # Order-independent
            separators=(',', ':'),    # No spaces
            ensure_ascii=True         # Portable encoding
        )
        
        # Hash the bytes
        hash_obj = hashlib.sha256(canonical_json.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def get_short_hash(self, length: int = 12) -> str:
        """Get shortened version of canonical hash for display."""
        return self.get_canonical_hash()[:length]


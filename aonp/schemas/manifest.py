"""
Provenance tracking models for run manifests.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RunManifest(BaseModel):
    """
    Provenance record for a simulation run.
    
    This manifest links every result to its exact input configuration
    and execution environment.
    """
    
    run_id: str = Field(..., description="Unique run identifier")
    spec_hash: str = Field(..., description="SHA256 hash of input specification")
    timestamp: str = Field(..., description="ISO 8601 timestamp of run creation")
    schema_version: str = Field(default="0.1.0", description="AONP schema version")
    
    # Execution environment
    openmc_version: Optional[str] = Field(default=None, description="OpenMC version used")
    python_version: Optional[str] = Field(default=None, description="Python version used")
    
    # Execution results
    status: str = Field(default="pending", description="Run status: pending, running, completed, failed")
    runtime_seconds: Optional[float] = Field(default=None, description="Total runtime in seconds")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    
    # Nuclear data reference
    nuclear_data_library: Optional[str] = Field(default=None, description="Nuclear data library identifier")
    cross_sections_path: Optional[str] = Field(default=None, description="Path to cross_sections.xml")
    
    @staticmethod
    def create(run_id: str, spec_hash: str) -> "RunManifest":
        """Create a new manifest with current timestamp."""
        return RunManifest(
            run_id=run_id,
            spec_hash=spec_hash,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


class NuclearDataReference(BaseModel):
    """Reference to nuclear data library used in simulation."""
    
    library: str = Field(..., description="Library identifier")
    version: str = Field(..., description="Library version")
    cross_sections_path: str = Field(..., description="Path to cross_sections.xml")
    timestamp: str = Field(..., description="ISO 8601 timestamp of reference creation")
    
    @staticmethod
    def create(library: str, version: str, cross_sections_path: str) -> "NuclearDataReference":
        """Create a new nuclear data reference with current timestamp."""
        return NuclearDataReference(
            library=library,
            version=version,
            cross_sections_path=cross_sections_path,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


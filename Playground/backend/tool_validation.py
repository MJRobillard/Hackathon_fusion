"""
Tool call validation before execution.

Validates tool calls against schemas and physical constraints
to prevent errors before execution.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ValidationError, Field, field_validator, model_validator
import re


class StudySpecSchema(BaseModel):
    """Schema for study specification validation."""
    geometry: str
    materials: List[str] = Field(default_factory=lambda: ["UO2", "Zircaloy", "Water"])
    enrichment_pct: Optional[float] = Field(None, ge=0, le=20)
    temperature_K: Optional[float] = Field(None, ge=300, le=1500)
    particles: int = Field(10000, ge=1000)
    batches: int = Field(50, ge=10)
    inactive: Optional[int] = Field(None, ge=0)
    
    @field_validator("enrichment_pct")
    @classmethod
    def validate_enrichment(cls, v):
        if v is not None and (v < 0 or v > 20):
            raise ValueError(f"Enrichment {v}% outside valid range (0-20%)")
        return v
    
    @field_validator("temperature_K")
    @classmethod
    def validate_temperature(cls, v):
        if v is not None and (v < 300 or v > 1500):
            raise ValueError(f"Temperature {v}K outside typical range (300-1500K)")
        return v


class SweepConfigSchema(BaseModel):
    """Schema for sweep configuration validation."""
    base_spec: Dict[str, Any]
    param_name: str = Field(..., pattern="^(enrichment_pct|temperature_K)$")
    param_values: List[float] = Field(..., min_length=2, max_length=20)
    
    @model_validator(mode="after")
    def validate_param_values_against_name(self):
        """Validate param_values against param_name after model is created."""
        param_name = self.param_name
        if param_name == "enrichment_pct":
            for val in self.param_values:
                if val < 0 or val > 20:
                    raise ValueError(f"Enrichment value {val}% outside valid range")
        elif param_name == "temperature_K":
            for val in self.param_values:
                if val < 300 or val > 1500:
                    raise ValueError(f"Temperature value {val}K outside typical range")
        return self


def validate_study_spec(spec: Dict[str, Any]) -> tuple[bool, Optional[StudySpecSchema], List[str]]:
    """
    Validate study specification.
    
    Returns:
        (is_valid, validated_spec, errors)
    """
    errors = []
    try:
        validated = StudySpecSchema(**spec)
        return True, validated, []
    except ValidationError as e:
        for error in e.errors():
            errors.append(f"{error['loc']}: {error['msg']}")
        return False, None, errors


def validate_sweep_config(config: Dict[str, Any]) -> tuple[bool, Optional[SweepConfigSchema], List[str]]:
    """
    Validate sweep configuration.
    
    Returns:
        (is_valid, validated_config, errors)
    """
    errors = []
    try:
        # First validate base_spec
        base_spec = config.get("base_spec", {})
        base_valid, _, base_errors = validate_study_spec(base_spec)
        if not base_valid:
            errors.extend([f"base_spec.{e}" for e in base_errors])
        
        # Then validate sweep config
        validated = SweepConfigSchema(**config)
        return len(errors) == 0, validated, errors
    except ValidationError as e:
        for error in e.errors():
            errors.append(f"{error['loc']}: {error['msg']}")
        return False, None, errors


def validate_tool_call(tool_name: str, params: Dict[str, Any]) -> tuple[bool, Optional[Dict[str, Any]], List[str]]:
    """
    Validate a tool call before execution.
    
    Args:
        tool_name: Name of the tool
        params: Parameters for the tool
    
    Returns:
        (is_valid, validated_params, errors)
    """
    if tool_name == "submit_study":
        valid, validated, errors = validate_study_spec(params)
        if valid:
            return True, validated.dict(), []
        return False, None, errors
    
    elif tool_name == "generate_sweep":
        valid, validated, errors = validate_sweep_config(params)
        if valid:
            return True, validated.dict(), []
        return False, None, errors
    
    # Unknown tool - allow but warn
    return True, params, [f"Unknown tool {tool_name}, validation skipped"]

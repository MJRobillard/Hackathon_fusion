"""
Runtime orchestration configuration.

This module centralizes "how we orchestrate" behavior that should be easy to tune:
- Tool-call prompt templates (how tool calls are narrated to the UI)
- Convergence defaults (how iterative runs decide "good enough")

The API layer can PATCH this config at runtime for demos.
"""

from __future__ import annotations

from threading import Lock
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ToolPromptConfig(BaseModel):
    """
    Templates used when emitting agent tool_call/tool_result events.
    Available template variables:
      - {tool_name}
      - {agent}
      - {run_id}
      - {iteration}
    """

    tool_call_template: str = Field(
        default="Calling {tool_name}",
        description="Default message emitted for tool_call events",
    )
    tool_result_template: str = Field(
        default="{tool_name} completed",
        description="Default message emitted for tool_result events",
    )
    per_tool_call_template: Dict[str, str] = Field(
        default_factory=dict,
        description="Overrides for specific tools (by tool_name)",
    )

    def format_tool_call(
        self,
        *,
        tool_name: str,
        agent: str,
        run_id: Optional[str] = None,
        iteration: Optional[int] = None,
    ) -> str:
        tmpl = self.per_tool_call_template.get(tool_name, self.tool_call_template)
        return tmpl.format(
            tool_name=tool_name,
            agent=agent,
            run_id=run_id or "",
            iteration=iteration if iteration is not None else "",
        ).strip()

    def format_tool_result(
        self,
        *,
        tool_name: str,
        agent: str,
        run_id: Optional[str] = None,
        iteration: Optional[int] = None,
    ) -> str:
        return self.tool_result_template.format(
            tool_name=tool_name,
            agent=agent,
            run_id=run_id or "",
            iteration=iteration if iteration is not None else "",
        ).strip()


class ConvergenceConfig(BaseModel):
    """Defaults for 'continue until it converges'."""

    enabled: bool = True
    target_uncertainty_pcm: float = 50.0
    stable_delta_pcm: float = 25.0
    max_iterations: int = 5
    max_particles: int = 1_000_000
    max_batches: int = 2_000
    batches_step: int = 100
    particles_min_step: int = 1000


class OrchestrationConfig(BaseModel):
    tool_prompts: ToolPromptConfig = Field(default_factory=ToolPromptConfig)
    convergence: ConvergenceConfig = Field(default_factory=ConvergenceConfig)


_lock = Lock()
_config = OrchestrationConfig(
    tool_prompts=ToolPromptConfig(
        tool_call_template="🔧 {agent}: {tool_name}",
        tool_result_template="✅ {agent}: {tool_name} completed",
        per_tool_call_template={
            "submit_study": "🚀 {agent}: launch OpenMC run (iter {iteration})",
            "validate_physics": "🧪 {agent}: validate physics inputs",
            "compare_runs": "📊 {agent}: compare candidate runs",
        },
    ),
)


def get_orchestration_config() -> OrchestrationConfig:
    with _lock:
        return _config.model_copy(deep=True)


def patch_orchestration_config(patch: Dict[str, Any]) -> OrchestrationConfig:
    """
    Patch config using a dict. Supports partial updates.
    """
    global _config
    with _lock:
        _config = _config.model_copy(update=patch, deep=True)
        return _config.model_copy(deep=True)



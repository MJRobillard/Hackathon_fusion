"""LLM client utilities (e.g., Fireworks, local DeepSeek)."""

# Re-export for convenience
from aonp.llm.fireworks_client import (
    FireworksError,
    chat_completion,
    extract_text,
)

__all__ = [
    "FireworksError",
    "chat_completion",
    "extract_text",
]


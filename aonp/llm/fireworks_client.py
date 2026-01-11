"""
Minimal Fireworks chat-completions client (OpenAI-compatible) using stdlib only.

Environment:
- FIREWORKS: API key (required)
- FIREWORKS_MODEL: model name (optional)
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, List, Optional


FIREWORKS_CHAT_COMPLETIONS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"

# Default to the repo's deployed model used elsewhere (Playground/team2).
# Can be overridden via FIREWORKS_MODEL env var.
DEFAULT_FIREWORKS_MODEL = (
    "accounts/robillard-matthew22/deployedModels/nvidia-nemotron-nano-9b-v2-nsoeqcp4"
)


class FireworksError(RuntimeError):
    pass


def _get_api_key() -> str:
    key = os.getenv("FIREWORKS")
    if not key:
        raise FireworksError("Missing FIREWORKS API key in environment")
    return key


def chat_completion(
    *,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 900,
    timeout_s: float = 30.0,
) -> Dict[str, Any]:
    """
    Call Fireworks chat completions (OpenAI-compatible).

    Returns the full JSON response.
    """
    api_key = _get_api_key()
    model = model or os.getenv("FIREWORKS_MODEL") or DEFAULT_FIREWORKS_MODEL

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    req = urllib.request.Request(
        FIREWORKS_CHAT_COMPLETIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except Exception as e:
        raise FireworksError(f"Fireworks chat completion failed: {e}") from e


def extract_text(response: Dict[str, Any]) -> str:
    """Extract assistant text from a Fireworks/OpenAI compatible chat response."""
    try:
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        raise FireworksError(f"Unexpected response shape: {e}") from e



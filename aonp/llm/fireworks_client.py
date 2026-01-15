"""
Minimal Fireworks chat-completions client (OpenAI-compatible) using stdlib only.

Environment:
- FIREWORKS: API key (required unless RUN_LOCAL=true)
- FIREWORKS_MODEL: model name (optional)
- RUN_LOCAL: if "true" or "1", use local DeepSeek via Ollama instead
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


def _should_use_local() -> bool:
    """Check if RUN_LOCAL is set to use local DeepSeek."""
    run_local = os.getenv("RUN_LOCAL", "").lower()
    return run_local in ("true", "1", "yes", "on")


def _get_api_key() -> str:
    """Get API key, or None if using local mode."""
    if _should_use_local():
        return None
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
    
    If RUN_LOCAL is set, falls back to local DeepSeek via Ollama.

    Returns the full JSON response.
    """
    # Check if we should use local DeepSeek
    if _should_use_local():
        try:
            from aonp.llm.local_deepseek_client import chat_completion as local_chat_completion
            return local_chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout_s=timeout_s,
            )
        except ImportError:
            # If import fails, try Fireworks fallback if available
            if os.getenv("FIREWORKS"):
                print("⚠️  Warning: Local DeepSeek unavailable, falling back to Fireworks")
                # Continue to Fireworks code below
            else:
                raise FireworksError(
                    "RUN_LOCAL is set but local_deepseek_client could not be imported "
                    "and no FIREWORKS key available. Ensure ollama is installed and running."
                )
        except Exception as e:
            # If local fails, try Fireworks as fallback (if available)
            if os.getenv("FIREWORKS"):
                print(f"⚠️  Warning: Local DeepSeek failed ({e}), falling back to Fireworks")
                # Continue to Fireworks code below
            else:
                raise FireworksError(
                    f"Local DeepSeek failed and no FIREWORKS key available: {e}"
                ) from e
    
    # Use Fireworks API
    api_key = _get_api_key()
    if not api_key:
        raise FireworksError("Missing FIREWORKS API key in environment")
    
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



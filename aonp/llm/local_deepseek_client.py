"""
Local DeepSeek client using Ollama (OpenAI-compatible API).

Environment:
- LOCAL_DEEPSEEK_MODEL: Ollama model name (default: "deepseek-r1:1.5b")
- LOCAL_DEEPSEEK_URL: Ollama API base URL (default: "http://localhost:11434")
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, List, Optional


DEFAULT_LOCAL_MODEL = "deepseek-r1:1.5b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"


class LocalDeepSeekError(RuntimeError):
    pass


def _get_ollama_url() -> str:
    """Get Ollama API base URL from environment or default."""
    return os.getenv("LOCAL_DEEPSEEK_URL", DEFAULT_OLLAMA_URL)


def _get_model_name() -> str:
    """Get model name from environment or default."""
    return os.getenv("LOCAL_DEEPSEEK_MODEL", DEFAULT_LOCAL_MODEL)


def chat_completion(
    *,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 900,
    timeout_s: float = 30.0,
) -> Dict[str, Any]:
    """
    Call local Ollama DeepSeek model (OpenAI-compatible).

    Returns the full JSON response in OpenAI-compatible format.
    """
    base_url = _get_ollama_url()
    model_name = model or _get_model_name()
    
    # Ollama uses /api/chat endpoint
    url = f"{base_url}/api/chat"
    
    # Convert messages format (Ollama expects "content" directly)
    ollama_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        ollama_messages.append({"role": role, "content": content})
    
    payload: Dict[str, Any] = {
        "model": model_name,
        "messages": ollama_messages,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,  # Ollama uses num_predict instead of max_tokens
        },
        "stream": False,
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            response = json.loads(raw)
            
            # Convert Ollama response to OpenAI-compatible format
            # Ollama returns: {"message": {"role": "assistant", "content": "..."}, ...}
            # OpenAI returns: {"choices": [{"message": {"role": "assistant", "content": "..."}}], ...}
            ollama_content = response.get("message", {}).get("content", "")
            
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": ollama_content,
                        },
                        "finish_reason": response.get("done", True) and "stop" or None,
                    }
                ],
                "model": model_name,
                "usage": {
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "completion_tokens": response.get("eval_count", 0),
                    "total_tokens": (
                        response.get("prompt_eval_count", 0) + response.get("eval_count", 0)
                    ),
                },
            }
    except urllib.error.URLError as e:
        raise LocalDeepSeekError(
            f"Failed to connect to Ollama at {base_url}. "
            f"Is Ollama running? Error: {e}"
        ) from e
    except Exception as e:
        raise LocalDeepSeekError(f"Local DeepSeek chat completion failed: {e}") from e


def extract_text(response: Dict[str, Any]) -> str:
    """Extract assistant text from OpenAI-compatible response."""
    try:
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        raise LocalDeepSeekError(f"Unexpected response shape: {e}") from e


def check_ollama_available() -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        base_url = _get_ollama_url()
        model_name = _get_model_name()
        
        # Check if Ollama is running
        list_url = f"{base_url}/api/tags"
        req = urllib.request.Request(list_url, method="GET")
        
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            models_data = json.loads(resp.read().decode("utf-8"))
            available_models = [
                model.get("name", "") for model in models_data.get("models", [])
            ]
            
            # Check if our model is available
            return any(model_name in name or name in model_name for name in available_models)
    except urllib.error.URLError as e:
        # Connection error - Ollama is not running or not accessible
        return False
    except Exception as e:
        # Other errors (JSON parsing, etc.)
        return False

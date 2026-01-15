#!/usr/bin/env python3
"""
Test script to verify local DeepSeek setup via Ollama.

Usage:
    # Test with local mode
    RUN_LOCAL=true python scripts/test_local_deepseek.py
    
    # Or test Ollama directly
    python scripts/test_local_deepseek.py --direct
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from aonp.llm.local_deepseek_client import (
        chat_completion,
        extract_text,
        check_ollama_available,
        LocalDeepSeekError,
    )
    from aonp.llm.fireworks_client import chat_completion as fw_chat_completion
except ImportError as e:
    print(f"❌ Failed to import: {e}")
    print("Ensure you're in the project root directory")
    sys.exit(1)


def test_ollama_connection():
    """Test if Ollama is available."""
    print("Testing Ollama connection...")
    if check_ollama_available():
        print("✓ Ollama is running and model is available")
        return True
    else:
        print("❌ Ollama is not available or model not found")
        print("   Run: ollama pull deepseek-r1:1.5b")
        return False


def test_direct_ollama():
    """Test Ollama directly."""
    print("\n" + "=" * 60)
    print("Direct Ollama Test")
    print("=" * 60)
    
    if not test_ollama_connection():
        return False
    
    print("\nSending test message to local DeepSeek...")
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello from local DeepSeek!' in exactly those words."}
        ]
        
        response = chat_completion(
            messages=messages,
            temperature=0.2,
            max_tokens=50,
            timeout_s=30.0,
        )
        
        text = extract_text(response)
        print(f"\n✓ Response received:")
        print(f"  {text}")
        
        # Check response structure
        assert "choices" in response
        assert len(response["choices"]) > 0
        assert "message" in response["choices"][0]
        assert "content" in response["choices"][0]["message"]
        
        print("\n✓ Response format is correct (OpenAI-compatible)")
        return True
        
    except LocalDeepSeekError as e:
        print(f"\n❌ Local DeepSeek error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fireworks_wrapper():
    """Test the fireworks_client wrapper with RUN_LOCAL."""
    print("\n" + "=" * 60)
    print("Fireworks Client Wrapper Test (RUN_LOCAL=true)")
    print("=" * 60)
    
    # Ensure RUN_LOCAL is set
    original = os.environ.get("RUN_LOCAL")
    os.environ["RUN_LOCAL"] = "true"
    
    try:
        print("\nSending test message via fireworks_client wrapper...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Respond with just: 'Wrapper test successful'"}
        ]
        
        response = fw_chat_completion(
            messages=messages,
            temperature=0.2,
            max_tokens=50,
            timeout_s=30.0,
        )
        
        from aonp.llm.fireworks_client import extract_text as fw_extract_text
        text = fw_extract_text(response)
        print(f"\n✓ Response received via wrapper:")
        print(f"  {text}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore original value
        if original is not None:
            os.environ["RUN_LOCAL"] = original
        elif "RUN_LOCAL" in os.environ:
            del os.environ["RUN_LOCAL"]


def main():
    parser = argparse.ArgumentParser(description="Test local DeepSeek setup")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Test Ollama directly (not via wrapper)",
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("Local DeepSeek Test Script")
    print("=" * 60)
    print()
    
    if args.direct:
        success = test_direct_ollama()
    else:
        # Test both
        direct_success = test_direct_ollama()
        wrapper_success = test_fireworks_wrapper() if direct_success else False
        
        success = direct_success and wrapper_success
    
    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed!")
        print("\nLocal DeepSeek is ready to use.")
        print("Set RUN_LOCAL=true in your .env to use it.")
    else:
        print("❌ Some tests failed")
        print("\nTroubleshooting:")
        print("1. Ensure Ollama is running: ollama serve")
        print("2. Ensure model is downloaded: ollama pull deepseek-r1:1.5b")
        print("3. Check Ollama is accessible: curl http://localhost:11434/api/tags")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()

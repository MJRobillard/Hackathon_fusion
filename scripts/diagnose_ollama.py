#!/usr/bin/env python3
"""
Diagnostic script to check Ollama setup and identify issues.

Usage:
    python scripts/diagnose_ollama.py
"""

import os
import sys
import json
import urllib.request
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_ollama_service():
    """Check if Ollama service is running."""
    print("=" * 80)
    print("Ollama Diagnostic Tool")
    print("=" * 80)
    print()
    
    # Get configuration
    base_url = os.getenv("LOCAL_DEEPSEEK_URL", "http://localhost:11434")
    model_name = os.getenv("LOCAL_DEEPSEEK_MODEL", "deepseek-r1:1.5b")
    
    print(f"Configuration:")
    print(f"  Ollama URL: {base_url}")
    print(f"  Expected model: {model_name}")
    print()
    
    # Test 1: Check if Ollama is accessible
    print("Test 1: Checking if Ollama service is running...")
    try:
        list_url = f"{base_url}/api/tags"
        req = urllib.request.Request(list_url, method="GET")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            print(f"  ✓ Ollama is accessible at {base_url}")
            models_data = json.loads(resp.read().decode("utf-8"))
            available_models = [
                model.get("name", "") for model in models_data.get("models", [])
            ]
            
            if available_models:
                print(f"  ✓ Found {len(available_models)} model(s):")
                for model in available_models:
                    print(f"    - {model}")
            else:
                print(f"  ⚠️  No models found (Ollama is running but no models downloaded)")
            
            print()
            
            # Test 2: Check if expected model is available
            print("Test 2: Checking if expected model is available...")
            model_found = any(model_name in name or name in model_name for name in available_models)
            if model_found:
                print(f"  ✓ Model '{model_name}' is available")
                print()
                print("=" * 80)
                print("✓ All checks passed! Ollama is ready to use.")
                print("=" * 80)
                return True
            else:
                print(f"  ❌ Model '{model_name}' not found")
                print(f"  Available models: {', '.join(available_models) if available_models else 'none'}")
                print()
                print("Solution:")
                print(f"  Run: ollama pull {model_name}")
                print()
                print("=" * 80)
                print("❌ Model not found. Please download it first.")
                print("=" * 80)
                return False
                
    except urllib.error.URLError as e:
        print(f"  ❌ Cannot connect to Ollama at {base_url}")
        print(f"  Error: {e}")
        print()
        print("Possible issues:")
        print("  1. Ollama is not installed")
        print("  2. Ollama service is not running")
        print("  3. Wrong URL (check LOCAL_DEEPSEEK_URL)")
        print()
        print("Solutions:")
        print("  Linux/WSL/macOS:")
        print("    - Install: curl -fsSL https://ollama.com/install.sh | sh")
        print("    - Start: ollama serve")
        print()
        print("  Windows:")
        print("    - Download from: https://ollama.com/download/windows")
        print("    - Ollama runs as a service automatically")
        print("    - Check if service is running in Task Manager")
        print()
        print("=" * 80)
        print("❌ Ollama is not accessible. Please install and start it.")
        print("=" * 80)
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("=" * 80)
        print("❌ Error checking Ollama.")
        print("=" * 80)
        return False


def main():
    """Run diagnostics."""
    success = check_ollama_service()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

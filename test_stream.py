#!/usr/bin/env python3
"""
Test OpenMC streaming endpoint
"""

import sys
import requests
from pathlib import Path

def test_stream(run_id: str, api_url: str = "http://localhost:8000"):
    """Test the streaming endpoint"""
    
    stream_url = f"{api_url}/runs/{run_id}/stream"
    
    print("="*60)
    print("OpenMC Terminal Streaming Test")
    print("="*60)
    print(f"Run ID: {run_id}")
    print(f"Endpoint: {stream_url}")
    print("")
    print("Connecting to stream...")
    print("-"*60)
    
    try:
        # Stream the response
        with requests.get(stream_url, stream=True, timeout=300) as response:
            response.raise_for_status()
            
            # Read line by line
            for line in response.iter_lines():
                if line:
                    # Decode SSE format (remove "data: " prefix)
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data: '):
                        content = decoded[6:]  # Remove "data: " prefix
                        print(content, end='')
                    else:
                        print(decoded)
                        
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Could not connect to {api_url}")
        print("Make sure the backend server is running:")
        print("  uvicorn aonp.api.main:app --reload")
    except requests.exceptions.Timeout:
        print(f"\n[ERROR] Stream timed out after 5 minutes")
    except KeyboardInterrupt:
        print(f"\n\n[INFO] Stream interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
    
    print()
    print("-"*60)
    print("Stream ended")


def list_runs():
    """List available runs"""
    runs_dir = Path("runs")
    if not runs_dir.exists():
        print("No runs directory found")
        return []
    
    runs = sorted([d.name for d in runs_dir.iterdir() if d.is_dir() and d.name.startswith("run_")])
    return runs


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_stream.py <run_id>")
        print("")
        print("Example: python test_stream.py run_abc123def456")
        print("")
        
        runs = list_runs()
        if runs:
            print("Available runs:")
            for run in runs[:10]:
                print(f"  - {run}")
            if len(runs) > 10:
                print(f"  ... and {len(runs) - 10} more")
        else:
            print("No runs found in ./runs/ directory")
            print("")
            print("Create a run first:")
            print("  python quick_start.py")
        
        sys.exit(1)
    
    run_id = sys.argv[1]
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    
    test_stream(run_id, api_url)


#!/usr/bin/env python3
"""
Test the global terminal streaming endpoint
"""

import sys
import json
import requests
import time

def test_global_stream(api_url: str = "http://localhost:8000"):
    """Test the global terminal streaming endpoint"""
    
    stream_url = f"{api_url}/terminal/stream"
    
    print("="*60)
    print("Global Backend Terminal Streaming Test")
    print("="*60)
    print(f"Endpoint: {stream_url}")
    print("")
    print("This will show ALL backend output in real-time:")
    print("  - API request logs")
    print("  - OpenMC simulation output")
    print("  - Agent execution logs")
    print("  - Errors and warnings")
    print("")
    print("Connecting to stream...")
    print("-"*60)
    
    try:
        # Stream the response
        with requests.get(stream_url, stream=True, timeout=None) as response:
            response.raise_for_status()
            
            # Read line by line
            for line in response.iter_lines():
                if line:
                    # Decode SSE format
                    decoded = line.decode('utf-8')
                    
                    if decoded.startswith('data: '):
                        # Extract JSON data
                        json_str = decoded[6:]  # Remove "data: " prefix
                        try:
                            event = json.loads(json_str)
                            timestamp = event.get('timestamp', '')[:19]
                            stream_type = event.get('stream', 'unknown')
                            content = event.get('content', '')
                            
                            # Color code based on stream type
                            if stream_type == 'stderr' or 'ERROR' in content:
                                prefix = f"\033[91m[{stream_type}]\033[0m"  # Red
                            elif stream_type == 'stdout':
                                prefix = f"\033[92m[{stream_type}]\033[0m"  # Green
                            else:
                                prefix = f"\033[94m[{stream_type}]\033[0m"  # Blue
                            
                            print(f"{prefix} {content}", end='')
                        except json.JSONDecodeError:
                            # If not JSON, just print it
                            print(decoded)
                    elif decoded.startswith(':'):
                        # Keepalive comment - ignore
                        pass
                    else:
                        print(decoded)
                        
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Could not connect to {api_url}")
        print("Make sure the backend server is running:")
        print("  uvicorn aonp.api.main:app --reload")
    except KeyboardInterrupt:
        print(f"\n\n[INFO] Stream interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
    
    print()
    print("-"*60)
    print("Stream ended")


if __name__ == "__main__":
    api_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print("\n💡 Tip: Open another terminal and make API requests to see them stream here!")
    print("Example: curl http://localhost:8000/health\n")
    time.sleep(2)
    
    test_global_stream(api_url)


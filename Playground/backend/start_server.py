#!/usr/bin/env python3
"""
Simple Python script to start the AONP API server
No bash/permissions needed!
"""

import os
import sys
from pathlib import Path

# Load .env if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Check MongoDB
if not os.getenv("MONGO_URI"):
    print("❌ ERROR: MONGO_URI not set")
    print("Please set MONGO_URI environment variable")
    print("Example: export MONGO_URI='mongodb://localhost:27017'")
    sys.exit(1)

print("✓ MONGO_URI set")

# Check Fireworks (optional)
if not os.getenv("FIREWORKS"):
    print("⚠️  WARNING: FIREWORKS key not set")
    print("   Using fast keyword routing (no LLM)")
else:
    print("✓ FIREWORKS key set")

# Set defaults
os.environ.setdefault("API_HOST", "0.0.0.0")
os.environ.setdefault("API_PORT", "8000")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")

print("")
print("=" * 80)
print("  AONP Multi-Agent API Server")
print("=" * 80)
print(f"  Host: {os.getenv('API_HOST')}")
print(f"  Port: {os.getenv('API_PORT')}")
print(f"  CORS: {os.getenv('CORS_ORIGINS')}")
print("")
print(f"  📡 Server: http://{os.getenv('API_HOST')}:{os.getenv('API_PORT')}")
print(f"  📚 API Docs: http://{os.getenv('API_HOST')}:{os.getenv('API_PORT')}/docs")
print(f"  📖 ReDoc: http://{os.getenv('API_HOST')}:{os.getenv('API_PORT')}/redoc")
print("=" * 80)
print("")

if __name__ == "__main__":
    # Start server
    try:
        import uvicorn
        
        # Change to API directory
        api_dir = Path(__file__).parent / "api"
        os.chdir(api_dir)
        
        # Detect if running on Windows (disable reload to avoid multiprocessing issues)
        is_windows = sys.platform.startswith('win') or 'microsoft' in os.uname().release.lower()
        use_reload = not is_windows
        
        if is_windows:
            print("⚠️  Note: Auto-reload disabled on Windows")
            print("")
        
        # Run server
        uvicorn.run(
            "main_v2:app",
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            reload=use_reload,
            log_level="info"
        )
        
    except ImportError:
        print("❌ ERROR: uvicorn not installed")
        print("Install with: pip install uvicorn")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped")
        sys.exit(0)


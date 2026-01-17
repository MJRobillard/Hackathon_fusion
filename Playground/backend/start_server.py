#!/usr/bin/env python3
"""
Simple Python script to start the AONP API server
No bash/permissions needed!
"""

import os
import sys
from pathlib import Path
import traceback

# Load .env if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Set nuclear data path (relative to project root)
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
nuclear_data_path = project_root / "nuclear_data" / "endfb-vii.1-hdf5" / "cross_sections.xml"

if nuclear_data_path.exists():
    os.environ["OPENMC_CROSS_SECTIONS"] = str(nuclear_data_path)
    print(f"✓ OPENMC_CROSS_SECTIONS set to: {nuclear_data_path}")
elif not os.getenv("OPENMC_CROSS_SECTIONS"):
    print("")
    print("=" * 80)
    print("⚠️  NUCLEAR DATA NOT FOUND")
    print("=" * 80)
    print(f"Expected path: {nuclear_data_path}")
    print("")
    print("OpenMC requires nuclear data to run simulations.")
    print("Please download it using one of the following methods:")
    print("")
    print("Method 1: Using openmc_data_downloader (Recommended)")
    print("  docker compose exec backend openmc_data_downloader install --dest /app/nuclear_data")
    print("  # Or use the helper script:")
    print("  docker compose exec backend bash download-nuclear-data-openmc-downloader.sh")
    print("")
    print("Method 2: Using Python openmc.data")
    print("  docker compose exec backend python -c 'import openmc; openmc.data.download_endfb71()'")
    print("")
    print("Method 3: From inside the container")
    print("  docker compose exec backend bash")
    print("  mkdir -p /app/nuclear_data && cd /app/nuclear_data")
    print("  openmc_data_downloader install --dest /app/nuclear_data")
    print("  # Or:")
    print("  python -c 'import openmc; openmc.data.download_endfb71()'")
    print("")
    print("Method 4: On host machine (then mount via volume)")
    print("  mkdir -p ./nuclear_data && cd ./nuclear_data")
    print("  openmc_data_downloader install --dest ./nuclear_data")
    print("  # Or:")
    print("  python -c 'import openmc; openmc.data.download_endfb71()'")
    print("")
    print("Note: The download is ~2-3 GB and may take several minutes.")
    print("After downloading, restart the container:")
    print("  docker compose restart backend")
    print("")
    print("Alternatively, set OPENMC_CROSS_SECTIONS environment variable to point")
    print("to an existing nuclear data location.")
    print("=" * 80)
    print("")
    print("⚠️  Server will start, but OpenMC simulations will fail without nuclear data.")
    print("")

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
        # Debug: Show Python info
        import sys
        print(f"DEBUG: Python executable: {sys.executable}")
        print(f"DEBUG: Python version: {sys.version}")
        print(f"DEBUG: Python path: {sys.path[:5]}...")  # Show first 5 entries
        
        # Try to find uvicorn
        import importlib.util
        uvicorn_path = None
        for path in sys.path:
            potential = f"{path}/uvicorn"
            if importlib.util.find_spec("uvicorn") is not None:
                spec = importlib.util.find_spec("uvicorn")
                if spec and spec.origin:
                    uvicorn_path = spec.origin
                    print(f"DEBUG: Found uvicorn at: {uvicorn_path}")
                    break
        
        if not uvicorn_path:
            print(f"DEBUG: uvicorn not found in sys.path")
            print(f"DEBUG: Checking site-packages...")
            import site
            print(f"DEBUG: site.getsitepackages(): {site.getsitepackages()}")
        
        try:
            import uvicorn
        except ModuleNotFoundError as exc:
            # Only treat missing `uvicorn` as a uvicorn install problem; other import
            # errors should be surfaced clearly.
            if getattr(exc, "name", None) == "uvicorn":
                print("❌ ERROR: uvicorn not installed")
                print("Install with: pip install uvicorn")
                sys.exit(1)
            raise

        print(f"DEBUG: Successfully imported uvicorn {uvicorn.__version__}")
        
        # Change to API directory
        api_dir = Path(__file__).parent / "api"
        os.chdir(api_dir)
        # Ensure programmatic uvicorn import can find `main_v2.py` in this directory
        # (when running via `python start_server.py`, sys.path[0] points to the script
        # directory, not the chdir() target).
        if str(api_dir) not in sys.path:
            sys.path.insert(0, str(api_dir))

        # Preflight import so we fail with a useful traceback if the app module
        # (or any of its dependencies) is missing/broken.
        try:
            import importlib
            importlib.import_module("main_v2")
        except Exception:
            print("❌ ERROR: Failed to import API module `main_v2` (or one of its dependencies).")
            traceback.print_exc()
            sys.exit(1)
        
        # Detect if running on Windows (disable reload to avoid multiprocessing issues)
        is_windows = sys.platform.startswith("win") or (
            hasattr(os, "uname") and "microsoft" in os.uname().release.lower()
        )
        use_reload = not is_windows
        
        if is_windows:
            print("⚠️  Note: Auto-reload disabled on Windows")
            print("")
        
        # Run server
        try:
            uvicorn.run(
                "main_v2:app",
                host=os.getenv("API_HOST", "0.0.0.0"),
                port=int(os.getenv("API_PORT", "8000")),
                reload=use_reload,
                log_level="info",
            )
        except Exception:
            print("❌ ERROR: Uvicorn failed to start.")
            traceback.print_exc()
            sys.exit(1)
        
    except ImportError:
        # Keep a helpful message, but don't hide the underlying cause.
        print("❌ ERROR: ImportError during server startup.")
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped")
        sys.exit(0)


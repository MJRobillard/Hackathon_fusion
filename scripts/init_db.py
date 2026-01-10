#!/usr/bin/env python3
"""
Initialize MongoDB database for AONP.

Creates all required indexes for:
- studies
- runs
- summaries
- events
- agent_outputs

Usage:
    python scripts/init_db.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aonp.db import init_indexes, get_db


def main():
    """Initialize database indexes."""
    try:
        db = get_db()
        print(f"Connected to MongoDB database: {db.name}")
        print("Creating indexes...")
        
        init_indexes(db)
        
        print("✅ MongoDB initialized successfully!")
        print("\nIndexes created for collections:")
        print("  - studies (spec_hash unique, created_at)")
        print("  - runs (run_id unique, status+created_at, spec_hash+created_at, lease_expires_at, phase+status)")
        print("  - summaries (run_id unique, extracted_at)")
        print("  - events (run_id+ts, type+ts)")
        print("  - agent_outputs (run_id+agent+kind+ts)")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


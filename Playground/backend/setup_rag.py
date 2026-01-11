#!/usr/bin/env python3
"""
RAG System Setup Script
Initialize Voyage AI, ChromaDB, and index documents
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from rag_components import setup_rag_components


def main():
    print("=" * 60)
    print("RAG SYSTEM SETUP")
    print("=" * 60)
    
    # Check environment variables
    voyage_key = os.getenv("VOYAGE_API_KEY")
    mongo_uri = os.getenv("MONGO_URI")
    
    if not voyage_key:
        print("❌ VOYAGE_API_KEY not found in environment")
        print("   Please set it in your .env file:")
        print("   VOYAGE_API_KEY=your_key_here")
        return 1
    
    if not mongo_uri:
        print("❌ MONGO_URI not found in environment")
        print("   Please set it in your .env file:")
        print("   MONGO_URI=mongodb://localhost:27017")
        return 1
    
    print(f"✅ VOYAGE_API_KEY: {voyage_key[:20]}...")
    print(f"✅ MONGO_URI: {mongo_uri}")
    print()
    
    # Setup components
    print("Initializing RAG components...")
    embedder, vector_store, pdf_indexer, sim_indexer = setup_rag_components(
        voyage_api_key=voyage_key,
        mongo_uri=mongo_uri,
        chroma_dir="./rag/chroma_db"
    )
    print("✅ RAG components initialized\n")
    
    # Check current state
    papers_count = vector_store.get_collection_count("papers")
    runs_count = vector_store.get_collection_count("runs")
    
    print(f"Current state:")
    print(f"  Papers indexed: {papers_count}")
    print(f"  Runs indexed: {runs_count}")
    print()
    
    # Index PDFs
    pdf_dir = Path("../../RAG/docs")
    if pdf_dir.exists():
        pdf_files = [p for p in pdf_dir.glob("*.pdf") if "Zone.Identifier" not in p.name]
        
        if pdf_files:
            print(f"Found {len(pdf_files)} PDF files in {pdf_dir}")
            response = input("Index these PDFs? (y/n): ")
            
            if response.lower() == 'y':
                pdf_indexer.index_directory(pdf_dir)
                print()
    else:
        print(f"⚠️  PDF directory not found: {pdf_dir}")
        print()
    
    # Index simulation runs
    if sim_indexer:
        from pymongo import MongoClient
        client = MongoClient(mongo_uri)
        runs_collection = client["aonp"]["runs"]
        total_runs = runs_collection.count_documents({})
        
        if total_runs > 0:
            print(f"Found {total_runs} simulation runs in MongoDB")
            response = input(f"Index all {total_runs} runs? (y/n): ")
            
            if response.lower() == 'y':
                sim_indexer.index_all_runs()
                print()
    
    # Final state
    papers_count = vector_store.get_collection_count("papers")
    runs_count = vector_store.get_collection_count("runs")
    
    print("=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print(f"✅ Papers indexed: {papers_count}")
    print(f"✅ Runs indexed: {runs_count}")
    print()
    print("You can now start the API server with:")
    print("  python start_server.py")
    print()
    print("RAG endpoints will be available at:")
    print("  http://localhost:8000/api/v1/rag/")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


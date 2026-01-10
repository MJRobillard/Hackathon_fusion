"""
Inspect the AONP MongoDB database to understand schema
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pprint import pprint

load_dotenv()

# Get MongoDB connection string from environment
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    print("ERROR: MONGO_URI not found in .env file")
    print("Expected format: MONGO_URI=mongodb+srv://...")
    exit(1)

print("=" * 80)
print("AONP DATABASE INSPECTION")
print("=" * 80)

try:
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client["aonp"]
    
    print("\n[CONNECTION] Connected successfully")
    
    # List all collections
    collections = db.list_collection_names()
    print(f"\n[COLLECTIONS] Found {len(collections)} collections:")
    for col in collections:
        print(f"  - {col}")
    
    # Inspect each collection
    for collection_name in collections:
        collection = db[collection_name]
        count = collection.count_documents({})
        
        print(f"\n{'=' * 80}")
        print(f"COLLECTION: {collection_name}")
        print(f"{'=' * 80}")
        print(f"Document count: {count}")
        
        if count > 0:
            print("\nSample document:")
            sample = collection.find_one()
            pprint(sample, width=80)
            
            print("\nIndexes:")
            for index in collection.list_indexes():
                print(f"  - {index['name']}: {index.get('key', {})}")
        else:
            print("(empty collection)")
    
    # Check if collections exist but are empty
    expected_collections = ["studies", "runs", "summaries"]
    missing = [col for col in expected_collections if col not in collections]
    
    if missing:
        print(f"\n[WARNING] Expected collections not found: {missing}")
        print("Creating collections with indexes...")
        
        for col in missing:
            if col == "studies":
                db.studies.create_index("spec_hash", unique=True)
                print(f"  ✓ Created studies collection with spec_hash index")
            elif col == "runs":
                db.runs.create_index("run_id", unique=True)
                db.runs.create_index([("spec_hash", 1), ("created_at", -1)])
                print(f"  ✓ Created runs collection with indexes")
            elif col == "summaries":
                db.summaries.create_index("run_id", unique=True)
                print(f"  ✓ Created summaries collection with run_id index")
    
    print("\n" + "=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)
    
except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    print("\nTroubleshooting:")
    print("1. Check MONGO_URI in .env file")
    print("2. Verify network access to MongoDB Atlas")
    print("3. Ensure IP address is whitelisted")


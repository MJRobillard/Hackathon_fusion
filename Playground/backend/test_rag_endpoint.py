"""
Quick test to diagnose RAG endpoint issues
"""
import os
import sys
import asyncio
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Test imports
print("=" * 60)
print("Testing RAG System Components")
print("=" * 60)

# 1. Check environment variables
print("\n1. Environment Variables:")
mongo_uri = os.getenv("MONGO_URI")
fireworks_key = os.getenv("FIREWORKS")
print(f"   MONGO_URI: {'✓ Set' if mongo_uri else '✗ Missing'}")
print(f"   FIREWORKS: {'✓ Set' if fireworks_key else '✗ Missing'}")

if not mongo_uri:
    print("\n❌ MONGO_URI not set in .env file")
    sys.exit(1)
    
if not fireworks_key:
    print("\n❌ FIREWORKS API key not set in .env file")
    sys.exit(1)

# 2. Test MongoDB connection
print("\n2. MongoDB Connection:")
try:
    mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    mongo_client.admin.command('ping')
    print("   ✓ MongoDB connected")
    
    # Check for runs collection
    db = mongo_client["aonp"]
    runs_count = db.runs.count_documents({})
    print(f"   ✓ Found {runs_count} runs in database")
except Exception as e:
    print(f"   ✗ MongoDB connection failed: {e}")
    sys.exit(1)

# 3. Test Fireworks LLM
print("\n3. Fireworks LLM:")
try:
    from langchain_fireworks import ChatFireworks
    from langchain_core.messages import HumanMessage
    
    llm = ChatFireworks(
        api_key=fireworks_key,
        model="accounts/robillard-matthew22/deployedModels/nvidia-nemotron-nano-9b-v2-nsoeqcp4",
        temperature=0.7
    )
    
    # Test simple call
    response = llm.invoke([HumanMessage(content="Hello, respond with just 'OK'")])
    print(f"   ✓ Fireworks LLM responding")
    print(f"   Response: {response.content[:50]}...")
except Exception as e:
    print(f"   ✗ Fireworks LLM failed: {e}")
    sys.exit(1)

# 4. Test SimpleRAGAgent initialization
print("\n4. SimpleRAGAgent Initialization:")
try:
    from simple_rag_agent import SimpleRAGAgent
    
    agent = SimpleRAGAgent(mongo_client)
    print(f"   ✓ Agent initialized")
    print(f"   Papers read: {agent.papers_read}")
    print(f"   Studies learned: {agent.studies_learned}")
except Exception as e:
    print(f"   ✗ Agent initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. Test agent.invoke()
print("\n5. Testing agent.invoke():")
async def test_invoke():
    try:
        result = await agent.invoke("What is nuclear fusion?")
        print(f"   ✓ Agent invoke successful")
        print(f"   Intent: {result.get('intent')}")
        print(f"   Result preview: {result.get('result', '')[:100]}...")
        return True
    except Exception as e:
        print(f"   ✗ Agent invoke failed: {e}")
        import traceback
        traceback.print_exc()
        return False

success = asyncio.run(test_invoke())

# Final verdict
print("\n" + "=" * 60)
if success:
    print("✅ ALL TESTS PASSED - RAG system should work!")
    print("\nThe backend is ready. Make sure:")
    print("1. Backend server is running: cd Playground/backend/api && python main_v2.py")
    print("2. Check backend console for: '✅ RAG Copilot endpoints registered'")
    print("3. Frontend API_BASE_URL points to http://localhost:8000")
else:
    print("❌ TESTS FAILED - See errors above")
print("=" * 60)


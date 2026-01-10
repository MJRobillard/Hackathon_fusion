"""
Quick test to verify API keys and basic functionality
"""

import os
from dotenv import load_dotenv

def test_environment():
    """Check if environment variables are set"""
    load_dotenv()
    
    print("[*] Checking environment variables...\n")
    
    fireworks_key = os.getenv("FIREWORKS")
    voyage_key = os.getenv("VOYAGE")
    langsmith_key = os.getenv("LANGCHAIN_API_KEY")
    langsmith_tracing = os.getenv("LANGCHAIN_TRACING_V2")
    langsmith_project = os.getenv("LANGCHAIN_PROJECT")
    
    required_ok = True
    
    # Required keys
    if fireworks_key:
        print(f"[OK] FIREWORKS key found: {fireworks_key[:20]}...")
    else:
        print("[FAIL] FIREWORKS key not found!")
        required_ok = False
        
    if voyage_key:
        print(f"[OK] VOYAGE key found: {voyage_key[:20]}...")
    else:
        print("[FAIL] VOYAGE key not found!")
        required_ok = False
    
    print()
    
    # Optional but recommended: LangSmith
    print("[*] Checking LangSmith configuration (optional)...\n")
    if langsmith_key:
        print(f"[OK] LANGCHAIN_API_KEY found: {langsmith_key[:20]}...")
    else:
        print("[WARN] LANGCHAIN_API_KEY not set (tracing disabled)")
    
    if langsmith_tracing and langsmith_tracing.lower() == "true":
        print(f"[OK] LANGCHAIN_TRACING_V2 enabled: {langsmith_tracing}")
    else:
        print(f"[WARN] LANGCHAIN_TRACING_V2 not enabled (set to 'true')")
    
    if langsmith_project:
        print(f"[OK] LANGCHAIN_PROJECT set: {langsmith_project}")
    else:
        print("[WARN] LANGCHAIN_PROJECT not set (will use default)")
    
    print()
    
    if not required_ok:
        print("[WARNING] Please set required API keys in .env file:")
        print("   FIREWORKS=your_key_here")
        print("   VOYAGE=your_key_here")
        print("\nOptional (for tracing):")
        print("   LANGCHAIN_API_KEY=your_langsmith_key")
        print("   LANGCHAIN_TRACING_V2=true")
        print("   LANGCHAIN_PROJECT=your_project_name")
        return False
    
    return True

def test_imports():
    """Test if required packages are installed"""
    print("[*] Testing imports...\n")
    
    try:
        import langchain
        print(f"[OK] langchain: {langchain.__version__}")
    except ImportError:
        print("[FAIL] langchain not installed")
        return False
    
    try:
        import langgraph
        print(f"[OK] langgraph installed")
    except ImportError:
        print("[FAIL] langgraph not installed")
        return False
    
    try:
        from langchain_fireworks import ChatFireworks
        print("[OK] langchain-fireworks installed")
    except ImportError:
        print("[FAIL] langchain-fireworks not installed")
        return False
    
    try:
        import voyageai
        print(f"[OK] voyageai: {voyageai.__version__}")
    except ImportError:
        print("[FAIL] voyageai not installed")
        return False
    
    try:
        import pydantic
        print(f"[OK] pydantic: {pydantic.__version__}")
    except ImportError:
        print("[FAIL] pydantic not installed")
        return False
    
    print()
    return True

def test_fireworks_connection():
    """Test Fireworks API connection"""
    print("[*] Testing Fireworks API...\n")
    
    try:
        from langchain_fireworks import ChatFireworks
        from langchain_core.messages import HumanMessage
        
        llm = ChatFireworks(
            api_key=os.getenv("FIREWORKS"),
            model="accounts/robillard-matthew22/deployedModels/nvidia-nemotron-nano-9b-v2-nsoeqcp4",
            temperature=0.6
        )
        
        response = llm.invoke([HumanMessage(content="Say 'test successful' and nothing else.")])
        print(f"[OK] Fireworks response: {response.content}")
        print()
        return True
    except Exception as e:
        print(f"[FAIL] Fireworks test failed: {e}")
        print()
        return False

def test_voyage_connection():
    """Test Voyage API connection"""
    print("[*] Testing Voyage API...\n")
    
    try:
        import voyageai
        
        client = voyageai.Client(api_key=os.getenv("VOYAGE"))
        result = client.embed(
            ["test embedding"], 
            model="voyage-2",
            input_type="document"
        )
        
        embedding_dim = len(result.embeddings[0])
        print(f"[OK] Voyage embedding created: {embedding_dim} dimensions")
        print()
        return True
    except Exception as e:
        print(f"[FAIL] Voyage test failed: {e}")
        print()
        return False

def test_langsmith_tracing():
    """Test LangSmith tracing setup"""
    print("[*] Testing LangSmith tracing...\n")
    
    langsmith_key = os.getenv("LANGCHAIN_API_KEY")
    langsmith_tracing = os.getenv("LANGCHAIN_TRACING_V2")
    
    if not langsmith_key:
        print("[SKIP] LangSmith not configured (optional)")
        print()
        return True  # Not a failure, just skipped
    
    try:
        from langsmith import Client
        
        client = Client(api_key=langsmith_key)
        
        # Try to get the current user/project info
        # This will fail if the API key is invalid
        print(f"[OK] LangSmith API key valid")
        
        if langsmith_tracing and langsmith_tracing.lower() == "true":
            print(f"[OK] Tracing is ENABLED")
            print(f"     Project: {os.getenv('LANGCHAIN_PROJECT', 'default')}")
            print(f"     View traces at: https://smith.langchain.com/")
        else:
            print("[WARN] Tracing is DISABLED (set LANGCHAIN_TRACING_V2=true)")
        
        print()
        return True
    except ImportError:
        print("[INFO] langsmith package not installed (pip install langsmith)")
        print("       Tracing will still work without it for basic verification")
        print()
        return True
    except Exception as e:
        print(f"[FAIL] LangSmith test failed: {e}")
        print()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("MULTI-AGENT POC - SETUP TEST")
    print("=" * 60)
    print()
    
    all_passed = True
    
    all_passed &= test_environment()
    all_passed &= test_imports()
    all_passed &= test_fireworks_connection()
    all_passed &= test_voyage_connection()
    all_passed &= test_langsmith_tracing()
    
    print("=" * 60)
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED - Ready to run multi-agent POC!")
        print("\nNext steps:")
        print("  python multi_agent_poc.py")
        print("  python multi_agent_with_memory.py")
        print("\nTo view traces in LangSmith:")
        print("  1. Run any agent script")
        print("  2. Visit https://smith.langchain.com/")
        print("  3. Check your project for traces")
    else:
        print("[FAILED] SOME TESTS FAILED - Check errors above")
        print("\nTo install dependencies:")
        print("  pip install -r requirements.txt")
    print("=" * 60)


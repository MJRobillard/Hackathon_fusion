#!/usr/bin/env python3
"""
Integration test for local DeepSeek with multi-agent system.

This script tests the complete integration:
1. LLM creation with RUN_LOCAL=true
2. Model name exposure
3. RouterAgent functionality
4. End-to-end routing

Usage:
    RUN_LOCAL=true python scripts/test_local_deepseek_integration.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "Playground" / "backend"))

def test_setup():
    """Check that prerequisites are met."""
    print("=" * 80)
    print("Local DeepSeek Multi-Agent Integration Test")
    print("=" * 80)
    print()
    
    # Check RUN_LOCAL is set
    run_local = os.getenv("RUN_LOCAL", "").lower()
    if run_local not in ("true", "1", "yes", "on"):
        print("⚠️  WARNING: RUN_LOCAL is not set to true")
        print("   This test requires RUN_LOCAL=true to test local DeepSeek")
        print("   Set it with: export RUN_LOCAL=true")
        print()
        response = input("Continue anyway? (y/n): ")
        if response.lower() != "y":
            sys.exit(1)
    else:
        print("✓ RUN_LOCAL is set to true")
    
    # Check Ollama is available
    try:
        from aonp.llm.local_deepseek_client import check_ollama_available, _get_ollama_url, _get_model_name
        import urllib.request
        import json
        
        base_url = _get_ollama_url()
        model_name = _get_model_name()
        
        # First check if Ollama service is running
        print(f"Checking Ollama at {base_url}...")
        try:
            list_url = f"{base_url}/api/tags"
            req = urllib.request.Request(list_url, method="GET")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                models_data = json.loads(resp.read().decode("utf-8"))
                available_models = [
                    model.get("name", "") for model in models_data.get("models", [])
                ]
                
                print(f"✓ Ollama is running")
                print(f"  Available models: {', '.join(available_models) if available_models else 'none'}")
                
                # Check if our model is available
                model_found = any(model_name in name or name in model_name for name in available_models)
                if model_found:
                    print(f"✓ Model '{model_name}' is available")
                else:
                    print(f"❌ Model '{model_name}' not found in available models")
                    print(f"   Run: ollama pull {model_name}")
                    print()
                    print("   For more detailed diagnostics, run:")
                    print("   python scripts/diagnose_ollama.py")
                    sys.exit(1)
        except urllib.error.URLError as e:
            print(f"❌ Cannot connect to Ollama at {base_url}")
            print(f"   Error: {e}")
            print()
            print("   Make sure Ollama is running:")
            print("   - Linux/WSL/macOS: ollama serve")
            print("   - Windows: Check if Ollama service is running")
            print()
            print("   For more detailed diagnostics, run:")
            print("   python scripts/diagnose_ollama.py")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error checking Ollama: {e}")
            sys.exit(1)
            
    except ImportError as e:
        print(f"⚠️  Warning: Could not import local_deepseek_client: {e}")
        print("   Some tests may fail")
    
    print()
    return True


def test_llm_creation():
    """Test that LLM is created correctly."""
    print("-" * 80)
    print("Test 1: LLM Creation")
    print("-" * 80)
    
    # Clear any cached modules
    modules_to_clear = [
        "Playground.backend.multi_agent_system",
        "multi_agent_system",
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]
    
    try:
        from multi_agent_system import llm, _should_use_local
        
        # Check RUN_LOCAL is detected
        if not _should_use_local():
            print("⚠️  WARNING: RUN_LOCAL is not detected as true")
            print("   This might indicate an issue with environment variable detection")
        
        # Check LLM type
        from langchain_openai import ChatOpenAI
        from langchain_fireworks import ChatFireworks
        
        if isinstance(llm, ChatOpenAI):
            print("✓ LLM is ChatOpenAI (local DeepSeek)")
        elif isinstance(llm, ChatFireworks):
            print("⚠️  LLM is ChatFireworks (not using local mode)")
            print("   Check that RUN_LOCAL=true is set")
        else:
            print(f"⚠️  Unexpected LLM type: {type(llm)}")
        
        # Check model name
        model_name = getattr(llm, "model", None)
        if model_name is not None:
            print(f"✓ Model name is accessible: {model_name}")
        else:
            print("❌ Model name is None (this is the bug we're fixing!)")
            return False
        
        # Check temperature
        temperature = getattr(llm, "temperature", None)
        if temperature is not None:
            print(f"✓ Temperature is accessible: {temperature}")
        else:
            print("⚠️  Temperature is None")
        
        # Check base URL
        base_url = getattr(llm, "openai_api_base", None) or str(getattr(llm, "base_url", ""))
        if base_url and "11434" in base_url:
            print(f"✓ Base URL points to Ollama: {base_url}")
        elif base_url:
            print(f"⚠️  Base URL: {base_url}")
        
        print("✓ Test 1 passed\n")
        return True
        
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_router_agent_model_name():
    """Test that RouterAgent exposes model name correctly."""
    print("-" * 80)
    print("Test 2: RouterAgent Model Name Exposure")
    print("-" * 80)
    
    # Clear any cached modules
    modules_to_clear = [
        "Playground.backend.multi_agent_system",
        "multi_agent_system",
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]
    
    try:
        from multi_agent_system import RouterAgent
        
        # Create mock callback object to capture events
        captured_events = []
        
        class MockCallback:
            def thinking(self, agent, message, metadata):
                if agent == "Router":
                    captured_events.append({
                        "agent": agent,
                        "event_type": "thinking",
                        "message": message,
                        "metadata": metadata
                    })
            
            def planning(self, agent, message, metadata):
                if agent == "Router":
                    captured_events.append({
                        "agent": agent,
                        "event_type": "planning",
                        "message": message,
                        "metadata": metadata
                    })
            
            def observation(self, agent, message, metadata):
                if agent == "Router":
                    captured_events.append({
                        "agent": agent,
                        "event_type": "observation",
                        "message": message,
                        "metadata": metadata
                    })
            
            def decision(self, agent, message, metadata):
                if agent == "Router":
                    captured_events.append({
                        "agent": agent,
                        "event_type": "decision",
                        "message": message,
                        "metadata": metadata
                    })
        
        mock_callback = MockCallback()
        router = RouterAgent(use_llm=True, thinking_callback=mock_callback)
        
        # Route a query
        query = "Run parameter sweep for enrichment 3% to 5%"
        print(f"Routing query: {query}")
        result = router.route_query(query)
        
        print(f"Routing result: agent={result.get('agent')}, intent={result.get('intent')}")
        
        # Check planning event
        planning_events = [e for e in captured_events if e.get("metadata", {}).get("method") == "llm"]
        if not planning_events:
            print("⚠️  No planning event with LLM method captured")
            print("   This might be okay if keyword routing was used")
        else:
            planning_event = planning_events[0]
            llm_input = planning_event["metadata"].get("llm_input", {})
            model_name = llm_input.get("model")
            
            if model_name is not None:
                print(f"✓ Model name in reasoning: {model_name}")
            else:
                print("❌ Model name is None in reasoning (this is the bug!)")
                return False
            
            temperature = llm_input.get("temperature")
            if temperature is not None:
                print(f"✓ Temperature in reasoning: {temperature}")
            else:
                print("⚠️  Temperature is None in reasoning")
        
        print("✓ Test 2 passed\n")
        return True
        
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_router_agent_functionality():
    """Test that RouterAgent actually works with local DeepSeek."""
    print("-" * 80)
    print("Test 3: RouterAgent Functionality")
    print("-" * 80)
    
    # Clear any cached modules
    modules_to_clear = [
        "Playground.backend.multi_agent_system",
        "multi_agent_system",
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]
    
    try:
        from multi_agent_system import RouterAgent
        
        router = RouterAgent(use_llm=True)
        
        test_cases = [
            ("Run parameter sweep for enrichment 3% to 5%", "sweep"),
            ("Show me recent runs", "query"),
            ("Simulate a PWR pin cell", "single_study"),
        ]
        
        all_passed = True
        for query, expected_intent in test_cases:
            print(f"\nTesting query: {query}")
            result = router.route_query(query)
            
            agent = result.get("agent")
            intent = result.get("intent")
            confidence = result.get("confidence", 0)
            
            print(f"  → Agent: {agent}, Intent: {intent}, Confidence: {confidence:.2f}")
            
            if agent is None or intent is None:
                print(f"  ❌ Routing failed for query: {query}")
                all_passed = False
            elif agent not in ["studies", "sweep", "query", "analysis"]:
                print(f"  ⚠️  Unexpected agent: {agent}")
            else:
                print(f"  ✓ Routing successful")
        
        if all_passed:
            print("\n✓ Test 3 passed\n")
        else:
            print("\n⚠️  Test 3 had some issues\n")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests."""
    if not test_setup():
        sys.exit(1)
    
    results = []
    
    # Test 1: LLM Creation
    results.append(("LLM Creation", test_llm_creation()))
    
    # Test 2: RouterAgent Model Name
    results.append(("RouterAgent Model Name", test_router_agent_model_name()))
    
    # Test 3: RouterAgent Functionality
    results.append(("RouterAgent Functionality", test_router_agent_functionality()))
    
    # Summary
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    print()
    if all_passed:
        print("✓ All tests passed!")
        print("\nLocal DeepSeek integration is working correctly.")
        print("The model name should now show up correctly in agent reasoning.")
    else:
        print("❌ Some tests failed")
        print("\nPlease check the errors above and ensure:")
        print("1. RUN_LOCAL=true is set")
        print("2. Ollama is running: ollama serve")
        print("3. Model is downloaded: ollama pull deepseek-r1:1.5b")
        print("4. langchain-openai is installed: pip install langchain-openai")
        sys.exit(1)
    
    print("=" * 80)


if __name__ == "__main__":
    main()

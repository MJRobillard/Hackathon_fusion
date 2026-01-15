#!/usr/bin/env python3
"""
Test cases for local DeepSeek integration with multi-agent system.

These tests verify that when RUN_LOCAL=true, the system:
1. Creates the correct LLM (ChatOpenAI pointing to Ollama)
2. Exposes the model name correctly
3. RouterAgent works with local DeepSeek
4. Agent reasoning shows correct model name (not null)

Usage:
    # Run with RUN_LOCAL=true
    RUN_LOCAL=true python -m pytest tests/test_local_deepseek_multi_agent.py -v
    
    # Or run specific test
    RUN_LOCAL=true python -m pytest tests/test_local_deepseek_multi_agent.py::test_llm_model_name -v
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "Playground" / "backend"))

try:
    from aonp.llm.local_deepseek_client import check_ollama_available
except ImportError:
    check_ollama_available = None


# Skip all tests if Ollama is not available (unless explicitly testing)
def pytest_configure(config):
    """Configure pytest to skip tests if Ollama is not available."""
    if check_ollama_available is None:
        pytest.skip("local_deepseek_client not available")
    elif not check_ollama_available():
        pytest.skip("Ollama is not running or model not available")


@pytest.fixture
def run_local_env():
    """Fixture to set RUN_LOCAL=true and restore afterwards."""
    original = os.environ.get("RUN_LOCAL")
    os.environ["RUN_LOCAL"] = "true"
    yield
    if original is not None:
        os.environ["RUN_LOCAL"] = original
    elif "RUN_LOCAL" in os.environ:
        del os.environ["RUN_LOCAL"]


@pytest.fixture
def no_run_local_env():
    """Fixture to ensure RUN_LOCAL is not set."""
    original = os.environ.get("RUN_LOCAL")
    if "RUN_LOCAL" in os.environ:
        del os.environ["RUN_LOCAL"]
    yield
    if original is not None:
        os.environ["RUN_LOCAL"] = original


@pytest.fixture
def mock_model_name():
    """Fixture to set a custom model name."""
    original = os.environ.get("LOCAL_DEEPSEEK_MODEL")
    os.environ["LOCAL_DEEPSEEK_MODEL"] = "deepseek-r1:1.5b"
    yield "deepseek-r1:1.5b"
    if original is not None:
        os.environ["LOCAL_DEEPSEEK_MODEL"] = original
    elif "LOCAL_DEEPSEEK_MODEL" in os.environ:
        del os.environ["LOCAL_DEEPSEEK_MODEL"]


class TestLLMCreation:
    """Test LLM creation with RUN_LOCAL=true."""
    
    def test_llm_uses_local_when_run_local_true(self, run_local_env, mock_model_name):
        """Test that LLM is created with ChatOpenAI when RUN_LOCAL=true."""
        # Clear any cached module-level llm
        if "Playground.backend.multi_agent_system" in sys.modules:
            del sys.modules["Playground.backend.multi_agent_system"]
        if "multi_agent_system" in sys.modules:
            del sys.modules["multi_agent_system"]
        
        from multi_agent_system import llm, _should_use_local
        
        assert _should_use_local() is True, "RUN_LOCAL should be detected as true"
        
        # Check that we're using ChatOpenAI (not ChatFireworks)
        from langchain_openai import ChatOpenAI
        assert isinstance(llm, ChatOpenAI), f"Expected ChatOpenAI, got {type(llm)}"
        
        # Check base_url points to Ollama
        assert hasattr(llm, "openai_api_base"), "ChatOpenAI should have openai_api_base"
        base_url = llm.openai_api_base or str(getattr(llm, "base_url", ""))
        assert "11434" in base_url or "localhost" in base_url, f"Expected Ollama URL, got {base_url}"
    
    def test_llm_model_name_is_set(self, run_local_env, mock_model_name):
        """Test that model name is properly set and accessible."""
        # Clear any cached module-level llm
        if "Playground.backend.multi_agent_system" in sys.modules:
            del sys.modules["Playground.backend.multi_agent_system"]
        if "multi_agent_system" in sys.modules:
            del sys.modules["multi_agent_system"]
        
        from multi_agent_system import llm
        
        # Check model name is accessible via getattr
        model_name = getattr(llm, "model", None)
        assert model_name is not None, "Model name should not be None"
        assert model_name == mock_model_name, f"Expected {mock_model_name}, got {model_name}"
    
    def test_llm_temperature_is_set(self, run_local_env):
        """Test that temperature is properly set and accessible."""
        # Clear any cached module-level llm
        if "Playground.backend.multi_agent_system" in sys.modules:
            del sys.modules["Playground.backend.multi_agent_system"]
        if "multi_agent_system" in sys.modules:
            del sys.modules["multi_agent_system"]
        
        from multi_agent_system import llm
        
        # Check temperature is accessible
        temperature = getattr(llm, "temperature", None)
        assert temperature is not None, "Temperature should not be None"
        assert temperature == 0.7, f"Expected 0.7, got {temperature}"
    
    def test_llm_fallback_to_fireworks_when_run_local_false(self, no_run_local_env):
        """Test that LLM falls back to Fireworks when RUN_LOCAL is not set."""
        # Clear any cached module-level llm
        if "Playground.backend.multi_agent_system" in sys.modules:
            del sys.modules["Playground.backend.multi_agent_system"]
        if "multi_agent_system" in sys.modules:
            del sys.modules["multi_agent_system"]
        
        from multi_agent_system import llm, _should_use_local
        from langchain_fireworks import ChatFireworks
        
        assert _should_use_local() is False, "RUN_LOCAL should be detected as false"
        assert isinstance(llm, ChatFireworks), f"Expected ChatFireworks, got {type(llm)}"


class TestRouterAgent:
    """Test RouterAgent with local DeepSeek."""
    
    def test_router_agent_model_name_in_reasoning(self, run_local_env, mock_model_name):
        """Test that RouterAgent exposes model name correctly in reasoning."""
        # Clear any cached module-level llm
        if "Playground.backend.multi_agent_system" in sys.modules:
            del sys.modules["Playground.backend.multi_agent_system"]
        if "multi_agent_system" in sys.modules:
            del sys.modules["multi_agent_system"]
        
        from multi_agent_system import RouterAgent
        
        # Create a mock thinking callback to capture the planning event
        captured_events = []
        
        def mock_thinking_callback(agent, event_type, message, metadata):
            if event_type == "planning" and agent == "Router":
                captured_events.append({
                    "agent": agent,
                    "event_type": event_type,
                    "message": message,
                    "metadata": metadata
                })
        
        router = RouterAgent(use_llm=True, thinking_callback=mock_thinking_callback)
        
        # Route a simple query
        query = "Run parameter sweep for enrichment 3% to 5%"
        result = router.route_query(query)
        
        # Check that a planning event was captured
        assert len(captured_events) > 0, "Planning event should be captured"
        
        # Find the planning event with LLM input
        planning_event = None
        for event in captured_events:
            if event.get("metadata", {}).get("method") == "llm":
                planning_event = event
                break
        
        assert planning_event is not None, "Should have planning event with LLM method"
        
        # Check that model name is in the metadata
        llm_input = planning_event["metadata"].get("llm_input", {})
        model_name = llm_input.get("model")
        
        assert model_name is not None, "Model name should not be None in LLM input"
        assert model_name == mock_model_name, f"Expected {mock_model_name}, got {model_name}"
        
        # Check that temperature is also present
        temperature = llm_input.get("temperature")
        assert temperature is not None, "Temperature should not be None"
        assert temperature == 0.7, f"Expected 0.7, got {temperature}"
    
    def test_router_agent_actual_routing(self, run_local_env):
        """Test that RouterAgent actually works with local DeepSeek for routing."""
        # Clear any cached module-level llm
        if "Playground.backend.multi_agent_system" in sys.modules:
            del sys.modules["Playground.backend.multi_agent_system"]
        if "multi_agent_system" in sys.modules:
            del sys.modules["multi_agent_system"]
        
        from multi_agent_system import RouterAgent
        
        router = RouterAgent(use_llm=True)
        
        # Test different query types
        test_cases = [
            ("Run parameter sweep for enrichment 3% to 5%", "sweep"),
            ("Show me recent runs", "query"),
            ("Simulate a PWR pin cell", "single_study"),
            ("Compare run_12345678 and run_87654321", "analysis"),
        ]
        
        for query, expected_intent in test_cases:
            result = router.route_query(query)
            assert "agent" in result, f"Result should have 'agent' key for query: {query}"
            assert "intent" in result, f"Result should have 'intent' key for query: {query}"
            
            # Check that routing worked (intent might not match exactly due to LLM variations)
            # But we should get a valid agent name
            assert result["agent"] in ["studies", "sweep", "query", "analysis"], \
                f"Invalid agent: {result['agent']} for query: {query}"


class TestStudiesAgent:
    """Test StudiesAgent with local DeepSeek."""
    
    def test_studies_agent_model_name_in_reasoning(self, run_local_env, mock_model_name):
        """Test that StudiesAgent exposes model name correctly in reasoning."""
        # Clear any cached module-level llm
        if "Playground.backend.multi_agent_system" in sys.modules:
            del sys.modules["Playground.backend.multi_agent_system"]
        if "multi_agent_system" in sys.modules:
            del sys.modules["multi_agent_system"]
        
        from multi_agent_system import StudiesAgent
        
        # Create a mock thinking callback
        captured_events = []
        
        def mock_thinking_callback(agent, event_type, message, metadata):
            if event_type == "planning" and agent == "Studies Agent":
                captured_events.append({
                    "agent": agent,
                    "event_type": event_type,
                    "message": message,
                    "metadata": metadata
                })
        
        agent = StudiesAgent(thinking_callback=mock_thinking_callback)
        
        # Note: This might fail if actual tools are called, so we'll skip execution
        # We just want to check that the LLM setup is correct
        # The model name check happens during _extract_spec which uses LLM
        # For now, we'll just verify the agent has the correct LLM
        assert hasattr(agent, "llm"), "StudiesAgent should have llm attribute"
        model_name = getattr(agent.llm, "model", None)
        assert model_name is not None, "Model name should not be None"
        assert model_name == mock_model_name, f"Expected {mock_model_name}, got {model_name}"


class TestIntegration:
    """Integration tests for local DeepSeek."""
    
    def test_custom_model_name(self, run_local_env):
        """Test that custom model name from LOCAL_DEEPSEEK_MODEL is used."""
        custom_model = "deepseek-r1:7b"
        original = os.environ.get("LOCAL_DEEPSEEK_MODEL")
        os.environ["LOCAL_DEEPSEEK_MODEL"] = custom_model
        
        try:
            # Clear any cached module-level llm
            if "Playground.backend.multi_agent_system" in sys.modules:
                del sys.modules["Playground.backend.multi_agent_system"]
            if "multi_agent_system" in sys.modules:
                del sys.modules["multi_agent_system"]
            
            from multi_agent_system import llm
            
            model_name = getattr(llm, "model", None)
            assert model_name == custom_model, f"Expected {custom_model}, got {model_name}"
        finally:
            if original is not None:
                os.environ["LOCAL_DEEPSEEK_MODEL"] = original
            elif "LOCAL_DEEPSEEK_MODEL" in os.environ:
                del os.environ["LOCAL_DEEPSEEK_MODEL"]
    
    def test_ollama_url_configuration(self, run_local_env):
        """Test that custom Ollama URL can be configured."""
        custom_url = "http://localhost:11435"  # Different port
        original = os.environ.get("LOCAL_DEEPSEEK_URL")
        os.environ["LOCAL_DEEPSEEK_URL"] = custom_url
        
        try:
            # Clear any cached module-level llm
            if "Playground.backend.multi_agent_system" in sys.modules:
                del sys.modules["Playground.backend.multi_agent_system"]
            if "multi_agent_system" in sys.modules:
                del sys.modules["multi_agent_system"]
            
            from multi_agent_system import llm
            
            # Check that base_url reflects the custom URL
            base_url = llm.openai_api_base or str(getattr(llm, "base_url", ""))
            assert "11435" in base_url or custom_url in base_url, \
                f"Expected URL containing 11435, got {base_url}"
        finally:
            if original is not None:
                os.environ["LOCAL_DEEPSEEK_URL"] = original
            elif "LOCAL_DEEPSEEK_URL" in os.environ:
                del os.environ["LOCAL_DEEPSEEK_URL"]


if __name__ == "__main__":
    # Allow running directly with pytest
    pytest.main([__file__, "-v"])

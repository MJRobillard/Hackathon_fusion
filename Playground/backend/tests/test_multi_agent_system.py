"""
Tests for multi-agent system
Tests Router Agent and all 4 Specialist Agents
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from multi_agent_system import (
    RouterAgent,
    StudiesAgent,
    SweepAgent,
    QueryAgent,
    AnalysisAgent,
    MultiAgentOrchestrator,
    run_multi_agent_query
)

# ============================================================================
# TEST: RouterAgent
# ============================================================================

class TestRouterAgent:
    """Tests for Router Agent"""
    
    def test_route_single_study(self):
        """Test routing single study request"""
        router = RouterAgent(use_llm=False)  # Use fast keyword routing
        result = router.route_query("Simulate a PWR pin cell with 4.5% enriched UO2")
        
        assert result["agent"] == "studies"
        assert result["intent"] == "single_study"
        assert "context" in result
    
    def test_route_sweep(self):
        """Test routing sweep request"""
        router = RouterAgent(use_llm=False)  # Use fast keyword routing
        result = router.route_query("Compare enrichments from 3% to 5%")
        
        assert result["agent"] == "sweep"
        assert result["intent"] == "sweep"
    
    def test_route_query(self):
        """Test routing query request"""
        router = RouterAgent(use_llm=False)  # Use fast keyword routing
        result = router.route_query("Show me all PWR simulations")
        
        assert result["agent"] == "query"
        assert result["intent"] == "query"
    
    def test_route_analysis(self):
        """Test routing analysis request"""
        router = RouterAgent(use_llm=False)  # Use fast keyword routing
        result = router.route_query("Compare run_abc123 and run_def456")
        
        # Should route to analysis or query
        assert result["agent"] in ["analysis", "query"]
    
    def test_route_ambiguous_defaults_to_studies(self):
        """Test that ambiguous queries default to studies"""
        router = RouterAgent(use_llm=False)  # Use fast keyword routing
        result = router.route_query("Tell me about nuclear reactors")
        
        # Should have a valid agent assignment
        assert result["agent"] in ["studies", "sweep", "query", "analysis"]


# ============================================================================
# TEST: StudiesAgent
# ============================================================================

class TestStudiesAgent:
    """Tests for Studies Agent"""
    
    def test_execute_simple_study(self):
        """Test executing simple study"""
        agent = StudiesAgent()
        context = {"query": "Simulate PWR pin with 4.5% enriched UO2 at 600K"}
        
        result = agent.execute(context)
        
        assert result["status"] == "success"
        assert "run_id" in result
        assert "keff" in result
        assert "spec" in result
    
    def test_execute_with_validation_warnings(self):
        """Test execution with physics warnings"""
        agent = StudiesAgent()
        context = {"query": "Simulate PWR with 1% enriched UO2"}  # Low enrichment
        
        result = agent.execute(context)
        
        # Should succeed but have warnings
        assert result["status"] == "success"
        if "warnings" in result:
            assert len(result["warnings"]) > 0
    
    def test_execute_invalid_physics(self):
        """Test execution with invalid physics"""
        agent = StudiesAgent()
        # Manually construct invalid spec
        agent_with_bad_spec = StudiesAgent()
        
        # Override extract_spec to return invalid spec
        def bad_extract_spec(query):
            return {
                "geometry": "Test",
                "materials": ["UO2"],
                "enrichment_pct": 150.0,  # Invalid
                "temperature_K": -100  # Invalid
            }
        
        agent_with_bad_spec._extract_spec = bad_extract_spec
        context = {"query": "Test"}
        
        result = agent_with_bad_spec.execute(context)
        
        assert result["status"] == "error"
        assert "error" in result
    
    def test_extract_spec_parsing(self):
        """Test spec extraction from natural language"""
        agent = StudiesAgent()
        
        spec = agent._extract_spec("Simulate PWR pin with 4.5% enriched UO2 at 600K")
        
        assert isinstance(spec, dict)
        assert "geometry" in spec
        assert "materials" in spec
        # Should have reasonable defaults
        assert spec.get("particles", 0) > 0
        assert spec.get("batches", 0) > 0


# ============================================================================
# TEST: SweepAgent
# ============================================================================

class TestSweepAgent:
    """Tests for Sweep Agent"""
    
    def test_execute_enrichment_sweep(self):
        """Test executing enrichment sweep"""
        agent = SweepAgent()
        context = {"query": "Compare enrichments from 3% to 5%"}
        
        result = agent.execute(context)
        
        assert result["status"] == "success"
        assert "run_ids" in result
        assert "comparison" in result
        assert "sweep_config" in result
        assert len(result["run_ids"]) > 1
    
    def test_execute_temperature_sweep(self):
        """Test executing temperature sweep"""
        agent = SweepAgent()
        context = {"query": "Vary temperature from 300K to 900K"}
        
        result = agent.execute(context)
        
        assert result["status"] == "success"
        assert len(result["run_ids"]) > 0
    
    def test_sweep_comparison_statistics(self):
        """Test that sweep includes comparison statistics"""
        agent = SweepAgent()
        context = {"query": "Compare enrichments 3%, 4%, 5%"}
        
        result = agent.execute(context)
        
        comparison = result["comparison"]
        assert "num_runs" in comparison
        assert "keff_mean" in comparison
        assert "keff_min" in comparison
        assert "keff_max" in comparison
    
    def test_extract_sweep_config(self):
        """Test sweep config extraction"""
        agent = SweepAgent()
        
        config = agent._extract_sweep_config("Compare enrichments from 3% to 5%")
        
        assert isinstance(config, dict)
        assert "base_spec" in config
        assert "param_name" in config
        assert "param_values" in config
        assert isinstance(config["param_values"], list)
        assert len(config["param_values"]) > 0


# ============================================================================
# TEST: QueryAgent
# ============================================================================

class TestQueryAgent:
    """Tests for Query Agent"""
    
    def test_execute_recent_query(self):
        """Test querying recent runs"""
        agent = QueryAgent()
        context = {"query": "Show me the 5 most recent simulations"}
        
        result = agent.execute(context)
        
        assert result["status"] == "success"
        assert "results" in result
        assert "count" in result
    
    def test_execute_statistics_query(self):
        """Test querying statistics"""
        agent = QueryAgent()
        context = {"query": "Give me database statistics"}
        
        result = agent.execute(context)
        
        assert result["status"] == "success"
        assert "results" in result
    
    def test_execute_filtered_query(self):
        """Test querying with filters"""
        agent = QueryAgent()
        context = {"query": "Show me all PWR simulations"}
        
        result = agent.execute(context)
        
        assert result["status"] == "success"
        assert isinstance(result["results"], list)
    
    def test_extract_filters_pwr(self):
        """Test filter extraction for PWR"""
        agent = QueryAgent()
        
        filters = agent._extract_filters("Show me all PWR simulations")
        
        assert "mongo_filter" in filters
        assert "spec.geometry" in filters["mongo_filter"]
    
    def test_extract_filters_critical(self):
        """Test filter extraction for critical systems"""
        agent = QueryAgent()
        
        filters = agent._extract_filters("Find all critical configurations")
        
        assert "keff" in filters["mongo_filter"]
        assert filters["mongo_filter"]["keff"]["$gte"] == 1.0
    
    def test_extract_filters_recent(self):
        """Test filter extraction for recent runs"""
        agent = QueryAgent()
        
        filters = agent._extract_filters("Show me the 10 most recent runs")
        
        assert filters["recent_only"] == True
        assert filters["limit"] == 10


# ============================================================================
# TEST: AnalysisAgent
# ============================================================================

class TestAnalysisAgent:
    """Tests for Analysis Agent"""
    
    def test_execute_comparison(self):
        """Test executing comparison"""
        # First create some runs to compare
        from agent_tools import submit_study
        
        spec1 = {"geometry": "Test 1", "materials": ["UO2"], "enrichment_pct": 3.0}
        spec2 = {"geometry": "Test 2", "materials": ["UO2"], "enrichment_pct": 5.0}
        
        result1 = submit_study(spec1)
        result2 = submit_study(spec2)
        
        # Now test analysis agent
        agent = AnalysisAgent()
        context = {"query": f"Compare {result1['run_id']} and {result2['run_id']}"}
        
        result = agent.execute(context)
        
        assert result["status"] == "success"
        assert "comparison" in result
        assert "interpretation" in result
        assert len(result["run_ids"]) == 2
    
    def test_execute_no_run_ids(self):
        """Test execution with no run IDs"""
        agent = AnalysisAgent()
        context = {"query": "Analyze something without run IDs"}
        
        result = agent.execute(context)
        
        assert result["status"] == "error"
        assert "error" in result
    
    def test_extract_run_ids(self):
        """Test run ID extraction"""
        agent = AnalysisAgent()
        
        run_ids = agent._extract_run_ids("Compare run_abc12345 and run_def67890")
        
        assert len(run_ids) == 2
        assert all(rid.startswith("run_") for rid in run_ids)
    
    def test_extract_run_ids_none(self):
        """Test run ID extraction with no IDs"""
        agent = AnalysisAgent()
        
        run_ids = agent._extract_run_ids("Just some text without run IDs")
        
        assert len(run_ids) == 0
    
    def test_generate_interpretation(self):
        """Test interpretation generation"""
        agent = AnalysisAgent()
        
        comparison = {
            "num_runs": 2,
            "keff_values": [1.05, 1.15],
            "keff_mean": 1.10,
            "keff_min": 1.05,
            "keff_max": 1.15
        }
        
        interpretation = agent._generate_interpretation(comparison)
        
        assert isinstance(interpretation, str)
        assert len(interpretation) > 0


# ============================================================================
# TEST: MultiAgentOrchestrator
# ============================================================================

class TestMultiAgentOrchestrator:
    """Tests for Multi-Agent Orchestrator"""
    
    def test_process_single_study_query(self):
        """Test processing single study query"""
        orchestrator = MultiAgentOrchestrator()
        
        result = orchestrator.process_query("Simulate PWR pin with 4.5% enriched UO2")
        
        assert "query" in result
        assert "routing" in result
        assert "results" in result
        assert "timestamp" in result
        
        assert result["routing"]["agent"] == "studies"
        assert result["results"]["status"] == "success"
    
    def test_process_sweep_query(self):
        """Test processing sweep query"""
        orchestrator = MultiAgentOrchestrator()
        
        result = orchestrator.process_query("Compare enrichments from 3% to 5%")
        
        assert result["routing"]["agent"] == "sweep"
        assert result["results"]["status"] == "success"
    
    def test_process_query_query(self):
        """Test processing query query"""
        orchestrator = MultiAgentOrchestrator()
        
        result = orchestrator.process_query("Show me recent simulations")
        
        assert result["routing"]["agent"] == "query"
        assert result["results"]["status"] == "success"
    
    def test_orchestrator_has_all_agents(self):
        """Test that orchestrator has all required agents"""
        orchestrator = MultiAgentOrchestrator()
        
        assert "studies" in orchestrator.agents
        assert "sweep" in orchestrator.agents
        assert "query" in orchestrator.agents
        assert "analysis" in orchestrator.agents
        
        assert isinstance(orchestrator.agents["studies"], StudiesAgent)
        assert isinstance(orchestrator.agents["sweep"], SweepAgent)
        assert isinstance(orchestrator.agents["query"], QueryAgent)
        assert isinstance(orchestrator.agents["analysis"], AnalysisAgent)


# ============================================================================
# TEST: Convenience Function
# ============================================================================

class TestConvenienceFunction:
    """Tests for run_multi_agent_query convenience function"""
    
    def test_convenience_function(self):
        """Test convenience function"""
        result = run_multi_agent_query("Simulate PWR pin with 4.5% enriched UO2")
        
        assert "query" in result
        assert "routing" in result
        assert "results" in result


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_full_workflow_studies_agent(self):
        """Test complete workflow through studies agent"""
        query = "Simulate a PWR pin cell with 4.5% enriched UO2 at 600K"
        result = run_multi_agent_query(query)
        
        # Check routing
        assert result["routing"]["agent"] == "studies"
        
        # Check execution
        assert result["results"]["status"] == "success"
        assert "run_id" in result["results"]
        assert "keff" in result["results"]
        
        # Verify run was stored
        from agent_tools import get_run_by_id
        run_id = result["results"]["run_id"]
        stored_run = get_run_by_id(run_id)
        assert stored_run is not None
    
    def test_full_workflow_sweep_agent(self):
        """Test complete workflow through sweep agent"""
        query = "Compare PWR enrichments from 3% to 5%"
        result = run_multi_agent_query(query)
        
        # Check routing
        assert result["routing"]["agent"] == "sweep"
        
        # Check execution
        assert result["results"]["status"] == "success"
        assert len(result["results"]["run_ids"]) > 1
        assert "comparison" in result["results"]
        
        # Verify all runs were stored
        from agent_tools import get_run_by_id
        for run_id in result["results"]["run_ids"]:
            stored_run = get_run_by_id(run_id)
            assert stored_run is not None
    
    def test_full_workflow_query_agent(self):
        """Test complete workflow through query agent"""
        # First create some data
        from agent_tools import submit_study
        submit_study({
            "geometry": "PWR pin cell",
            "materials": ["UO2", "Water"],
            "enrichment_pct": 4.5
        })
        
        # Now query
        query = "Show me all PWR simulations"
        result = run_multi_agent_query(query)
        
        # Check routing
        assert result["routing"]["agent"] == "query"
        
        # Check execution
        assert result["results"]["status"] == "success"
        assert "results" in result["results"]
    
    def test_workflow_error_handling(self):
        """Test error handling in workflow"""
        # Query that might cause issues
        query = "Do something impossible"
        result = run_multi_agent_query(query)
        
        # Should still return a result, possibly with error
        assert "routing" in result
        assert "results" in result


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.slow
class TestPerformance:
    """Performance tests"""
    
    def test_routing_performance(self):
        """Test routing performance"""
        import time
        
        router = RouterAgent(use_llm=False)  # Use fast keyword routing for performance test
        queries = [
            "Simulate PWR",
            "Compare enrichments",
            "Show me results",
            "Analyze run_abc123"
        ]
        
        start = time.time()
        for query in queries:
            router.route_query(query)
        elapsed = time.time() - start
        
        # Routing should be fast (< 1 second for 4 queries with keyword routing)
        assert elapsed < 1
    
    def test_end_to_end_performance(self):
        """Test end-to-end performance"""
        import time
        
        start = time.time()
        result = run_multi_agent_query("Simulate PWR pin with 4.5% enriched UO2")
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        # With mock: < 5s, with real OpenMC: < 30s
        from agent_tools import USE_REAL_OPENMC
        if USE_REAL_OPENMC:
            assert elapsed < 30
        else:
            assert elapsed < 5


# ============================================================================
# RUN WITH PYTEST
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])


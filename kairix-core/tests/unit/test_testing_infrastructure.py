"""Test the testing infrastructure itself to ensure mocks work correctly."""

import pytest
from kairix_core.types.cognition import Stimulus, StimulusType, Perception
from kairix_core.testing.conftest import MockPerceptor, MockPersona, MockInferenceProvider


class TestTestingInfrastructure:
    """Verify that our testing mocks work as expected."""
    
    def test_mock_imports(self):
        """Test that all mocks can be imported."""
        from kairix_core.testing import (
            MockAgent,
            MockRunResult,
            MockRunResultStreaming
        )
        
        # Verify classes exist
        assert MockAgent is not None
        assert MockRunResult is not None
        assert MockRunResultStreaming is not None
        
    @pytest.mark.asyncio
    async def test_mock_perceptor(self):
        """Test MockPerceptor functionality."""
        # Create with default perceptions
        perceptor = MockPerceptor()
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        
        perceptions = await perceptor.perceive(stimulus)
        assert len(perceptions) == 1
        assert perceptions[0].source == "mock_perceptor"
        assert perceptions[0].confidence == 0.9
        
        # Create with custom perceptions
        custom_perceptions = [
            Perception(source="custom", content="Test 1", confidence=0.95),
            Perception(source="custom", content="Test 2", confidence=0.85)
        ]
        custom_perceptor = MockPerceptor("custom", custom_perceptions)
        
        perceptions = await custom_perceptor.perceive(stimulus)
        assert len(perceptions) == 2
        assert perceptions[0].content == "Test 1"
        
    @pytest.mark.asyncio
    async def test_mock_persona(self):
        """Test MockPersona functionality."""
        # Default persona
        persona = MockPersona()
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        
        response = ""
        async for chunk in persona.react(stimulus):
            response += chunk
        assert response == "Hello from mock persona!"
        
        # Custom responses
        custom_persona = MockPersona(["Custom", " test"])
        response = ""
        async for chunk in custom_persona.react(stimulus):
            response += chunk
        assert response == "Custom test"
    
    def test_mock_inference_provider(self):
        """Test MockInferenceProvider functionality."""
        # Default provider
        provider = MockInferenceProvider()
        result = provider.predict("test", {})
        assert result == "Mock inference response"
        
        # Custom response
        custom_provider = MockInferenceProvider("Custom response")
        result = custom_provider.predict("test", {})
        assert result == "Custom response"
    
    def test_fixture_availability(
        self,
        mock_agent_runtime,
        mock_cache_runtime,
        mock_logging_runtime,
        mock_neo4j_runtime
    ):
        """Test that fixtures are available and configured."""
        # Agent runtime
        assert mock_agent_runtime is not None
        assert mock_agent_runtime.configuration_set.name == "test_config"
        
        # Cache runtime
        assert mock_cache_runtime is not None
        mock_cache_runtime.cache_index['test'] = 'value'
        assert mock_cache_runtime.cache_index['test'] == 'value'
        
        # Logging runtime
        assert mock_logging_runtime is not None
        mock_logging_runtime.logger.info("test")
        mock_logging_runtime.logger.info.assert_called_once_with("test")
        
        # Neo4j runtime
        assert mock_neo4j_runtime is not None
        assert mock_neo4j_runtime.embedded_memory_shard_store is not None
    
    @pytest.mark.asyncio
    async def test_async_mocks(
        self,
        mock_conversation_history_perceptor,
        mock_environmental_context_perceptor,
        mock_embedded_data_store
    ):
        """Test async mock functionality."""
        # Perceptor
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        perceptions = await mock_conversation_history_perceptor.perceive(stimulus)
        assert len(perceptions) == 1
        
        # Get recent turns
        turns = await mock_conversation_history_perceptor.get_recent_turns()
        assert len(turns) == 2
        assert turns[0][0] == "User: Hello"
        
        # Environmental context
        perceptions = await mock_environmental_context_perceptor.perceive(stimulus)
        assert "Current time" in perceptions[0].content
        
        # Embedded store
        results = await mock_embedded_data_store.search("query")
        assert len(results) == 2
        assert results[0]['similarity'] == 0.95
    
    def test_complete_environment(self, complete_mock_environment):
        """Test complete mock environment."""
        assert 'agent_runtime' in complete_mock_environment
        assert 'cache_runtime' in complete_mock_environment
        assert 'logging_runtime' in complete_mock_environment
        assert 'neo4j_runtime' in complete_mock_environment
        assert 'env_vars' in complete_mock_environment
        
        # All components are configured
        agent_runtime = complete_mock_environment['agent_runtime']
        assert agent_runtime.configuration_set.default_provider == "openai"
    
    @pytest.mark.asyncio 
    async def test_async_utils(self, async_test_utils):
        """Test async utility functions."""
        utils = async_test_utils
        
        # Test collect_async_iter
        async def gen():
            yield 1
            yield 2
            yield 3
        
        results = await utils['collect_async_iter'](gen())
        assert results == [1, 2, 3]
        
        # Test timeout_after
        async def quick_op():
            return "done"
        
        result = await utils['timeout_after'](quick_op(), seconds=1.0)
        assert result == "done"
"""Example test file demonstrating how to use the mock fixtures.

This file shows various ways to use the provided mocks in tests.
"""

import pytest
from kairix_core.types.cognition import Stimulus, StimulusType


class TestMockUsageExamples:
    """Examples of using various mock fixtures."""
    
    def test_agent_runtime_mock(self, mock_agent_runtime):
        """Example of using the mock agent runtime."""
        # The runtime is already configured
        assert mock_agent_runtime.configuration_set.name == "test_config"
        
        # You can call methods
        result = mock_agent_runtime.run("test_agent", "Hello")
        assert result.data == "Mock response"
        
        # You can customize the mock behavior
        mock_agent_runtime.run.return_value.data = "Custom response"
        result = mock_agent_runtime.run("test_agent", "Hello")
        assert result.data == "Custom response"
    
    @pytest.mark.asyncio
    async def test_perceptor_mock(self, mock_conversation_history_perceptor):
        """Example of using a mock perceptor."""
        stimulus = Stimulus(
            content="Hello, world!",
            type=StimulusType.user_message
        )
        
        perceptions = await mock_conversation_history_perceptor.perceive(stimulus)
        assert len(perceptions) == 1
        assert perceptions[0].source == "conversation_history"
        
        # Access additional methods
        recent_turns = await mock_conversation_history_perceptor.get_recent_turns()
        assert len(recent_turns) == 2
    
    @pytest.mark.asyncio
    async def test_persona_mock(self, mock_conversational_persona):
        """Example of using a mock persona."""
        stimulus = Stimulus(
            content="Tell me a story",
            type=StimulusType.user_message
        )
        
        # Collect streaming response
        response_parts = []
        async for part in mock_conversational_persona.react(stimulus):
            response_parts.append(part)
        
        assert "".join(response_parts) == "Hello from mock persona!"
        
        # Verify reflect was not called yet
        mock_conversational_persona.reflect.assert_not_called()
    
    def test_complete_environment(self, complete_mock_environment):
        """Example of using the complete mock environment."""
        # Access all mocked components
        agent_runtime = complete_mock_environment['agent_runtime']
        cache_runtime = complete_mock_environment['cache_runtime']
        neo4j_runtime = complete_mock_environment['neo4j_runtime']
        
        # Everything is pre-configured and ready to use
        assert agent_runtime.configuration_set.default_provider == "openai"
        assert neo4j_runtime.embedded_memory_shard_store is not None
        
        # Cache behaves like a dict
        cache_runtime.cache_index['test_key'] = 'test_value'
        assert cache_runtime.cache_index['test_key'] == 'test_value'
    
    @pytest.mark.asyncio
    async def test_embedded_store_mock(self, mock_embedded_data_store):
        """Example of using the mock embedded data store."""
        results = await mock_embedded_data_store.search("test query", limit=5)
        
        assert len(results) == 2
        assert results[0]['similarity'] > results[1]['similarity']
        
        # Test embedding generation
        embedding = mock_embedded_data_store.model.encode("test text")
        assert len(embedding[0]) == 768  # Standard embedding size
    
    def test_static_methods_mock(self, mock_static_methods):
        """Example of using mocked static methods."""
        # Concept composite key is mocked
        composite_key = mock_static_methods['concept_composite_key']
        assert composite_key("example", "entity") == "entity://example"
        
        # get_or_raise is mocked
        get_or_raise = mock_static_methods['get_or_raise']
        assert get_or_raise('KAIRIX_AGENT_CONFIGURATION_SET_KEY') == 'test_config'
        assert get_or_raise('UNKNOWN_KEY') == 'mock-UNKNOWN_KEY'
    
    @pytest.mark.asyncio
    async def test_custom_mock_configuration(self):
        """Example of creating custom mock configurations."""
        from kairix_core.testing.conftest import MockPerceptor, MockPersona
        from kairix_core.types.cognition import Perception
        
        # Create custom perceptor with specific perceptions
        custom_perceptor = MockPerceptor(
            name="custom_perceptor",
            perceptions=[
                Perception(source="custom", content="Special insight", confidence=0.99),
                Perception(source="custom", content="Another insight", confidence=0.95)
            ]
        )
        
        stimulus = Stimulus(content="test", type=StimulusType.user_message)
        perceptions = await custom_perceptor.perceive(stimulus)
        assert len(perceptions) == 2
        assert perceptions[0].confidence == 0.99
        
        # Create custom persona with specific responses
        custom_persona = MockPersona(responses=["Custom", " response", " here!"])
        response_parts = []
        async for part in custom_persona.react(stimulus):
            response_parts.append(part)
        assert "".join(response_parts) == "Custom response here!"
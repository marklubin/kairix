import pytest
from unittest.mock import Mock, patch
from typing import List

from cognition_engine.perceptor.conversation_remembering_perceptor import (
    ConversationRememberingPerceptor
)
from cognition_engine.types import Stimulus, StimulusType, Perception


class TestConversationRememberingPerceptor:
    """Test suite for ConversationRememberingPerceptor"""

    @pytest.fixture
    def mock_runner(self):
        """Create a mock runner with necessary methods"""
        runner = Mock()
        # Mock the run_sync method
        mock_result = Mock()
        mock_result.final_output_as.return_value = "test query keywords"
        runner.run_sync.return_value = mock_result
        
        # Mock the async run method for insight extraction
        async def mock_run(agent, memory):
            result = Mock()
            result.final_output_as.return_value = f"Insight from: {memory[:20]}..."
            return result
        
        runner.run = mock_run
        return runner

    @pytest.fixture
    def mock_memory_provider(self):
        """Create a mock memory provider that returns test memories"""
        def memory_provider(query: str, k: int) -> List[str]:
            return [f"Memory {i}: Test content for {query}" for i in range(k)]
        return memory_provider

    @pytest.fixture
    def perceptor(self, mock_runner, mock_memory_provider):
        """Create a ConversationRememberingPerceptor instance with mocks"""
        return ConversationRememberingPerceptor(
            runner=mock_runner,
            memory_provider=mock_memory_provider,
            k_memories=3
        )

    def test_init(self, mock_runner, mock_memory_provider):
        """Test perceptor initialization"""
        perceptor = ConversationRememberingPerceptor(
            runner=mock_runner,
            memory_provider=mock_memory_provider,
            k_memories=5
        )
        
        assert perceptor.runner == mock_runner
        assert perceptor.memory_provider == mock_memory_provider
        assert perceptor.k_memories == 5
        assert hasattr(perceptor, 'query_generating_agent')
        assert hasattr(perceptor, 'insight_extraction_agent')

    def test_perceive_with_user_message(self, perceptor, mock_runner, mock_memory_provider):
        """Test perceive method with a user message stimulus"""
        stimulus = Stimulus(
            content="Hello, how are you?",
            type=StimulusType.user_message
        )
        
        perceptions = perceptor.perceive(stimulus)
        
        # Verify query generation was called
        mock_runner.run_sync.assert_called_once()
        agent_call = mock_runner.run_sync.call_args[0]
        assert agent_call[0].name == "query_gen"
        assert agent_call[1] == "Hello, how are you?"
        
        # Verify memory provider was called with generated query
        # Can't directly check mock_memory_provider calls since it's a function, not a Mock
        # But we can verify the results
        
        # Should have 3 perceptions (one for each memory)
        assert len(perceptions) == 3
        
        # Check perception properties
        for i, perception in enumerate(perceptions):
            assert isinstance(perception, Perception)
            assert perception.source == "conversation_remembering_perceptor"
            assert perception.confidence == 1.0
            assert perception.content.startswith("Insight from: Memory")

    def test_perceive_with_non_user_message(self, perceptor):
        """Test perceive method with non-user message stimulus types"""
        # Test with TIME_TICK
        stimulus = Stimulus(
            content="tick",
            type=StimulusType.time_tick
        )
        perceptions = perceptor.perceive(stimulus)
        assert perceptions == []
        
        # Test with EXECUTION_ATTEMPT
        stimulus = Stimulus(
            content="execution data",
            type=StimulusType.execution_attempt
        )
        perceptions = perceptor.perceive(stimulus)
        assert perceptions == []

    def test_perceive_with_empty_memories(self, mock_runner):
        """Test perceive when memory provider returns empty list"""
        # Create memory provider that returns empty list
        def empty_memory_provider(query, k):
            return []
        
        perceptor = ConversationRememberingPerceptor(
            runner=mock_runner,
            memory_provider=empty_memory_provider,
            k_memories=3
        )
        
        stimulus = Stimulus(
            content="Hello",
            type=StimulusType.user_message
        )
        
        perceptions = perceptor.perceive(stimulus)
        assert perceptions == []

    def test_run_insights_async_behavior(self, perceptor):
        """Test that _run_insights properly handles async execution"""
        memories = ["Memory 1", "Memory 2", "Memory 3"]
        
        # Run the async method
        insights = perceptor._run_insights(memories)
        
        # Should return list of insights
        assert len(insights) == 3
        assert all(isinstance(insight, str) for insight in insights)
        assert all(insight.startswith("Insight from:") for insight in insights)

    def test_different_k_memories_values(self, mock_runner, mock_memory_provider):
        """Test perceptor with different k_memories values"""
        for k in [1, 5, 10]:
            perceptor = ConversationRememberingPerceptor(
                runner=mock_runner,
                memory_provider=mock_memory_provider,
                k_memories=k
            )
            
            stimulus = Stimulus(
                content="Test message",
                type=StimulusType.user_message
            )
            
            perceptions = perceptor.perceive(stimulus)
            assert len(perceptions) == k

    @patch('cognition_engine.perceptor.conversation_remembering_perceptor.logger')
    def test_logging_behavior(self, mock_logger, perceptor):
        """Test that appropriate logging occurs"""
        # Test user message logging
        stimulus = Stimulus(
            content="Test",
            type=StimulusType.user_message
        )
        perceptor.perceive(stimulus)
        
        # Check info logs
        mock_logger.info.assert_any_call(
            "ConversationRememberingPerceptor received: StimulusType.user_message"
        )
        mock_logger.info.assert_any_call("Gathering top 3 memories...")
        mock_logger.info.assert_any_call("Running paralleized insight generation agents...")
        mock_logger.info.assert_any_call("Extracted 3 relevant insights.")
        
        # Reset and test non-user message
        mock_logger.reset_mock()
        stimulus = Stimulus(
            content="",
            type=StimulusType.time_tick
        )
        perceptor.perceive(stimulus)
        
        mock_logger.info.assert_any_call("...taking no action.")

    def test_memory_provider_integration(self, mock_runner):
        """Test that memory provider is called correctly with query and k"""
        mock_memory_provider = Mock(return_value=["Memory 1", "Memory 2"])
        
        perceptor = ConversationRememberingPerceptor(
            runner=mock_runner,
            memory_provider=mock_memory_provider,
            k_memories=2
        )
        
        stimulus = Stimulus(
            content="Test input",
            type=StimulusType.user_message
        )
        
        perceptor.perceive(stimulus)
        
        # Verify memory provider was called with correct arguments
        mock_memory_provider.assert_called_once_with("test query keywords", 2)

    def test_agent_names_and_instructions(self, perceptor):
        """Test that agents are created with correct names and instructions"""
        assert perceptor.query_generating_agent.name == "query_gen"
        assert perceptor.insight_extraction_agent.name == "insight_extractor"
        
        # Check that instructions contain expected content
        assert "embedding vector database" in perceptor.query_generating_agent.instructions
        assert "bullet points" in perceptor.insight_extraction_agent.instructions

    def test_multiple_memories_processed(self, mock_runner):
        """Test that multiple memories are processed correctly"""
        # Custom memory provider that returns specific memories
        def custom_memory_provider(query: str, k: int) -> List[str]:
            return [f"Memory about {i}: {query}" for i in range(k)]
        
        perceptor = ConversationRememberingPerceptor(
            runner=mock_runner,
            memory_provider=custom_memory_provider,
            k_memories=5
        )
        
        stimulus = Stimulus(
            content="What did we discuss?",
            type=StimulusType.user_message
        )
        
        perceptions = perceptor.perceive(stimulus)
        
        # Should process all 5 memories
        assert len(perceptions) == 5
        
        # Each perception should have unique content
        contents = [p.content for p in perceptions]
        assert len(set(contents)) == 5  # All unique
        
        # All should have same source and confidence
        for p in perceptions:
            assert p.source == "conversation_remembering_perceptor"
            assert p.confidence == 1.0
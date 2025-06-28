"""Test implementation for IncrementalSummarizationPerceptor."""

import datetime
import numpy as np
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pytz import utc

from kairix_core.cognition.perceptor.incremental_reflection import IncrementalSummarizationPerceptor
from kairix_core.types.cognition import Stimulus, StimulusType, Perception
from kairix_core.types.neo4j import Agent


class TestIncrementalSummarizationPerceptor:
    """Test cases for IncrementalSummarizationPerceptor class."""
    
    @pytest.fixture
    def mock_agent(self):
        """Mock Agent object."""
        agent = Mock(spec=Agent)
        agent.uid = "test-agent-123"
        agent.name = "Test Agent"
        return agent
    
    @pytest.fixture
    def mock_runtime(self):
        """Mock AgentRuntime."""
        runtime = Mock()
        runtime.run = AsyncMock(return_value="This is a summarized version of the conversation.")
        return runtime
    
    @pytest.fixture
    def mock_embedder(self):
        """Mock SentenceTransformer embedder."""
        embedder = Mock()
        # Return a mock numpy array that has tolist() method
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        embedder.encode = Mock(return_value=mock_embedding)
        return embedder
    
    @pytest.fixture
    def mock_cache(self):
        """Mock CacheRuntime."""
        with patch('kairix_core.cognition.perceptor.incremental_reflection.cache') as mock_cache:
            mock_cache.__setitem__ = Mock()
            yield mock_cache
    
    @pytest.fixture
    def mock_memory_shard(self):
        """Mock MemoryShard class."""
        with patch('kairix_core.cognition.perceptor.incremental_reflection.MemoryShard') as mock_shard_class:
            mock_instance = Mock()
            mock_instance.save = Mock()
            mock_shard_class.return_value = mock_instance
            yield mock_shard_class
    
    @pytest.fixture
    def perceptor(self, mock_agent, mock_runtime, mock_embedder):
        """Create a perceptor instance with mocked dependencies."""
        return IncrementalSummarizationPerceptor(
            agent=mock_agent,
            runtime=mock_runtime,
            embedder=mock_embedder,
            summarization_interval=3  # Small interval for testing
        )
    
    def test_initialization(self, mock_agent, mock_runtime, mock_embedder):
        """Test IncrementalSummarizationPerceptor initialization."""
        # Test with default values
        perceptor = IncrementalSummarizationPerceptor(
            agent=mock_agent,
            runtime=mock_runtime,
            embedder=mock_embedder
        )
        
        assert perceptor.summarization_interval == 20
        assert perceptor._pending_messages == []
        assert perceptor.agent == mock_agent
        assert perceptor.runtime == mock_runtime
        assert perceptor.embedder == mock_embedder
        assert perceptor.last_summary == ""
        
        # Test with custom interval
        perceptor_custom = IncrementalSummarizationPerceptor(
            agent=mock_agent,
            runtime=mock_runtime,
            embedder=mock_embedder,
            summarization_interval=50
        )
        
        assert perceptor_custom.summarization_interval == 50
    
    @pytest.mark.asyncio
    async def test_perceive_user_message(self, perceptor):
        """Test perceiving user messages."""
        stimulus = Stimulus(
            type=StimulusType.user_message,
            content="Hello, how are you?"
        )
        
        result = await perceptor.perceive(stimulus)
        
        # Should return empty list since no summary has been generated yet
        assert result == []
        assert len(perceptor._pending_messages) == 1
        assert perceptor._pending_messages[0] == "User: Hello, how are you?"
    
    @pytest.mark.asyncio
    async def test_perceive_self_perception(self, perceptor):
        """Test perceiving self perception messages."""
        stimulus = Stimulus(
            type=StimulusType.self_perception,
            content="I'm doing well, thank you!"
        )
        
        result = await perceptor.perceive(stimulus)
        
        # Should return empty list since no summary has been generated yet
        assert result == []
        assert len(perceptor._pending_messages) == 1
        assert perceptor._pending_messages[0] == "Assistant: I'm doing well, thank you!"
    
    @pytest.mark.asyncio
    async def test_perceive_other_stimulus_type(self, perceptor):
        """Test perceiving other stimulus types."""
        with patch('kairix_core.cognition.perceptor.incremental_reflection.logger') as mock_logger:
            stimulus = Stimulus(
                type=StimulusType.world_event,
                content="World event"
            )
            
            result = await perceptor.perceive(stimulus)
            
            assert result == []
            assert len(perceptor._pending_messages) == 0
            mock_logger.info.assert_called_with(
                f"kairix_core.cognition.perceptor.incremental_reflection not responding to stimulus, {StimulusType.world_event}"
            )
    
    @pytest.mark.asyncio
    async def test_summarization_triggered(self, perceptor, mock_memory_shard, mock_cache):
        """Test that summarization is triggered when reaching the interval."""
        with patch('kairix_core.cognition.perceptor.incremental_reflection.logger') as mock_logger:
            with patch('kairix_core.cognition.perceptor.incremental_reflection.uuid.uuid4', return_value='test-uuid'):
                # Add messages up to the summarization interval
                for i in range(3):
                    if i % 2 == 0:
                        stimulus = Stimulus(
                            type=StimulusType.user_message,
                            content=f"User message {i}"
                        )
                    else:
                        stimulus = Stimulus(
                            type=StimulusType.self_perception,
                            content=f"Assistant message {i}"
                        )
                    await perceptor.perceive(stimulus)
                
                # Verify summarization was triggered
                assert len(perceptor._pending_messages) == 0  # Messages cleared
                assert mock_logger.info.call_count >= 3  # At least 3 info logs
                
                # Verify runtime.run was called with the conversation
                expected_conversation = 'User: User message 0\nAssistant: Assistant message 1\nUser: User message 2'
                perceptor.runtime.run.assert_called_once_with(perceptor.agent, expected_conversation)
                
                # Verify embedder was called with the summary
                perceptor.embedder.encode.assert_called_once_with("This is a summarized version of the conversation.")
                
                # Verify MemoryShard was created correctly
                mock_memory_shard.assert_called_once_with(
                    uid='test-uuid',
                    shard_contents="This is a summarized version of the conversation.",
                    vector_address=[0.1, 0.2, 0.3, 0.4, 0.5]
                )
                
                # Verify save was called
                mock_memory_shard.return_value.save.assert_called_once()
                
                # Verify last_summary was updated
                assert perceptor.last_summary == "This is a summarized version of the conversation."
    
    @pytest.mark.asyncio
    async def test_summarization_error_handling(self, perceptor, mock_memory_shard, mock_cache):
        """Test error handling during summarization."""
        with patch('kairix_core.cognition.perceptor.incremental_reflection.logger') as mock_logger:
            with patch('kairix_core.cognition.perceptor.incremental_reflection.datetime') as mock_datetime:
                mock_now = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=utc)
                mock_datetime.datetime.now.return_value = mock_now
                
                # Make runtime.run raise an exception
                perceptor.runtime.run.side_effect = Exception("Agent error")
                
                # Add messages to trigger summarization
                for i in range(3):
                    stimulus = Stimulus(
                        type=StimulusType.user_message,
                        content=f"Message {i}"
                    )
                    await perceptor.perceive(stimulus)
                
                # Verify error was logged
                expected_label = f'incremental-reflection-v1.{mock_now}'
                expected_content = 'User: Message 0\nUser: Message 1\nUser: Message 2'
                
                mock_logger.info.assert_any_call(
                    "Failed to generate reflective summarization. Error was: Agent error. "
                    "Persisting to disk for later processing"
                )
                
                # Verify content was cached
                mock_cache.__setitem__.assert_called_once_with(expected_label, expected_content)
                
                # Verify MemoryShard was not created due to error
                mock_memory_shard.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_no_summarization_below_interval(self, perceptor, mock_memory_shard):
        """Test that summarization is not triggered below the interval."""
        # Add messages below the interval
        for i in range(2):  # Less than interval of 3
            stimulus = Stimulus(
                type=StimulusType.user_message,
                content=f"Message {i}"
            )
            await perceptor.perceive(stimulus)
        
        # Verify messages are still pending
        assert len(perceptor._pending_messages) == 2
        
        # Verify no summarization occurred
        mock_memory_shard.assert_not_called()
        perceptor.runtime.run.assert_not_called()
        perceptor.embedder.encode.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_mixed_message_types_formatting(self, perceptor):
        """Test correct formatting of mixed message types."""
        # Add user message
        await perceptor.perceive(Stimulus(
            type=StimulusType.user_message,
            content="What's the weather?"
        ))
        
        # Add assistant message
        await perceptor.perceive(Stimulus(
            type=StimulusType.self_perception,
            content="The weather is sunny."
        ))
        
        # Verify formatting
        assert perceptor._pending_messages == [
            "User: What's the weather?",
            "Assistant: The weather is sunny."
        ]
    
    @pytest.mark.asyncio
    async def test_embedding_error_handling(self, perceptor, mock_memory_shard, mock_cache):
        """Test that embedding errors are handled gracefully."""
        with patch('kairix_core.cognition.perceptor.incremental_reflection.logger'):
            with patch('kairix_core.cognition.perceptor.incremental_reflection.datetime') as mock_datetime:
                mock_now = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=utc)
                mock_datetime.datetime.now.return_value = mock_now
                
                # Make embedder raise an exception
                perceptor.embedder.encode.side_effect = Exception("Embedding error")
                
                # Add messages to trigger summarization
                for i in range(3):
                    stimulus = Stimulus(
                        type=StimulusType.user_message,
                        content=f"Message {i}"
                    )
                    await perceptor.perceive(stimulus)
                
                # Verify runtime.run was called
                perceptor.runtime.run.assert_called_once()
                
                # Verify embedder was attempted
                perceptor.embedder.encode.assert_called_once()
                
                # Verify error was caught and content was cached
                expected_label = f'incremental-reflection-v1.{mock_now}'
                expected_content = 'User: Message 0\nUser: Message 1\nUser: Message 2'
                mock_cache.__setitem__.assert_called_once_with(expected_label, expected_content)
                
                # Verify MemoryShard was not created due to error
                mock_memory_shard.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_memory_shard_save_error(self, perceptor, mock_memory_shard, mock_cache):
        """Test handling when MemoryShard save fails."""
        with patch('kairix_core.cognition.perceptor.incremental_reflection.logger'):
            with patch('kairix_core.cognition.perceptor.incremental_reflection.datetime') as mock_datetime:
                mock_now = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=utc)
                mock_datetime.datetime.now.return_value = mock_now
                
                # Make MemoryShard save raise an exception
                mock_memory_shard.return_value.save.side_effect = Exception("Save error")
                
                # Add messages to trigger summarization
                for i in range(3):
                    stimulus = Stimulus(
                        type=StimulusType.user_message,
                        content=f"Message {i}"
                    )
                    await perceptor.perceive(stimulus)
                
                # Verify the full pipeline was attempted
                perceptor.runtime.run.assert_called_once()
                perceptor.embedder.encode.assert_called_once()
                mock_memory_shard.assert_called_once()
                mock_memory_shard.return_value.save.assert_called_once()
                
                # Verify error was caught and content was cached
                expected_label = f'incremental-reflection-v1.{mock_now}'
                expected_content = 'User: Message 0\nUser: Message 1\nUser: Message 2'
                mock_cache.__setitem__.assert_called_once_with(expected_label, expected_content)
    
    @pytest.mark.asyncio
    async def test_perception_returned_after_summarization(self, perceptor, mock_memory_shard):
        """Test that Perception is returned with last summary after summarization."""
        # Initially, no perception should be returned
        stimulus = Stimulus(type=StimulusType.user_message, content="First message")
        result = await perceptor.perceive(stimulus)
        assert result == []
        
        # Add more messages to trigger summarization
        for i in range(2):
            stimulus = Stimulus(
                type=StimulusType.user_message,
                content=f"Message {i+1}"
            )
            result = await perceptor.perceive(stimulus)
        
        # After summarization, perception should be returned
        assert len(result) == 1
        perception = result[0]
        assert isinstance(perception, Perception)
        assert perception.source == "incremental_summary.v1"
        assert perception.content == "This is a summarized version of the conversation."
        
        # Subsequent calls should continue returning the last summary
        stimulus = Stimulus(type=StimulusType.user_message, content="Another message")
        result = await perceptor.perceive(stimulus)
        assert len(result) == 1
        assert result[0].content == "This is a summarized version of the conversation."
    
    @pytest.mark.asyncio
    async def test_multiple_summarization_cycles(self, perceptor, mock_memory_shard):
        """Test multiple summarization cycles update the last summary."""
        # First summarization cycle
        for i in range(3):
            stimulus = Stimulus(
                type=StimulusType.user_message,
                content=f"First cycle message {i}"
            )
            result = await perceptor.perceive(stimulus)
        
        # Should have the first summary
        assert len(result) == 1
        assert result[0].content == "This is a summarized version of the conversation."
        
        # Update the mock to return a different summary
        perceptor.runtime.run = AsyncMock(return_value="This is the second summary.")
        
        # Second summarization cycle
        for i in range(3):
            stimulus = Stimulus(
                type=StimulusType.user_message,
                content=f"Second cycle message {i}"
            )
            result = await perceptor.perceive(stimulus)
        
        # Should have the updated summary
        assert len(result) == 1
        assert result[0].content == "This is the second summary."
        assert perceptor.last_summary == "This is the second summary."

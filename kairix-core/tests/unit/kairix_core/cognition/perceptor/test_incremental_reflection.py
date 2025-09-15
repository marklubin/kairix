import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
import numpy as np

from kairix_core.cognition.perceptor.incremental_reflection import (
    IncrementalReflectionPerceptor
)
from kairix_core.cognition.perceptor import Perception
from kairix_core.configuration.agent import AgentConfiguration
from kairix_core.runtime.message import Message
from kairix_core.embedding.litellm import LiteLLMEmbedder


class TestIncrementalReflectionPerceptor:
    """Test cases for IncrementalReflectionPerceptor focusing on type safety."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent configuration."""
        agent = Mock(spec=AgentConfiguration)
        agent.name = "test_agent"
        return agent
    
    @pytest.fixture
    def mock_embedder(self):
        """Create a mock embedder that returns proper numpy array."""
        embedder = Mock(spec=LiteLLMEmbedder)
        # Return a proper 768-dimensional numpy array
        embedder.embed_text.return_value = np.zeros(768, dtype=np.float32)
        return embedder
    
    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache runtime."""
        with patch('kairix_core.cognition.perceptor.incremental_reflection.CacheRuntime') as mock_cache_cls:
            cache_instance = MagicMock()
            cache_instance.summarization_errors = {}
            mock_cache_cls.return_value = cache_instance
            yield cache_instance
    
    @pytest.fixture
    def perceptor(self, mock_agent, mock_embedder, mock_cache):
        """Create an IncrementalReflectionPerceptor instance."""
        return IncrementalReflectionPerceptor(mock_agent, mock_embedder)
    
    @pytest.mark.asyncio
    async def test_perceive_returns_correct_type(self, perceptor):
        """Test that perceive always returns List[Perception]."""
        # Test with no messages
        result = await perceptor.perceive([])
        assert isinstance(result, list)
        assert all(isinstance(p, Perception) for p in result)
        
        # Test with messages but no summary yet
        messages = [
            Message(sender="user", content="Hello", timestamp=datetime.now()),
            Message(sender="assistant", content="Hi", timestamp=datetime.now())
        ]
        result = await perceptor.perceive(messages)
        assert isinstance(result, list)
        assert all(isinstance(p, Perception) for p in result)
    
    @pytest.mark.asyncio
    async def test_perceive_with_existing_summary(self, perceptor):
        """Test that perceive returns Perception when summary exists."""
        # Set a last summary
        perceptor.last_summary = "Test summary"
        
        result = await perceptor.perceive([])
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Perception)
        assert result[0].source == "incremental_summary.v1"
        assert result[0].content == "Test summary"
        assert result[0].confidence == 1.0
    
    @pytest.mark.asyncio
    async def test_perception_attributes(self, perceptor):
        """Test that Perception objects have correct attributes."""
        perceptor.last_summary = "Test summary content"
        
        result = await perceptor.perceive([])
        perception = result[0]
        
        # Check all required attributes
        assert hasattr(perception, 'source')
        assert hasattr(perception, 'content')
        assert hasattr(perception, 'confidence')
        
        # Check attribute types
        assert isinstance(perception.source, str)
        assert isinstance(perception.content, str)
        assert isinstance(perception.confidence, (int, float))
    
    @pytest.mark.asyncio
    async def test_summarization_error_handling(self, perceptor, mock_cache):
        """Test that summarization errors don't cause type errors."""
        # Create enough messages to trigger summarization
        messages = []
        for i in range(25):  # More than summarization_interval
            messages.append(
                Message(sender="user", content=f"Message {i}", timestamp=datetime.now())
            )
        
        # Mock the summarizer to raise an exception
        with patch('kairix_core.cognition.perceptor.incremental_reflection.generate_summary') as mock_summarize:
            mock_summarize.side_effect = Exception("Summarization failed")
            
            # This should not raise, and should return empty list
            result = await perceptor.perceive(messages)
            assert isinstance(result, list)
            assert len(result) == 0
            
            # Check that error was cached
            assert len(mock_cache.summarization_errors) > 0
    
    @pytest.mark.asyncio
    async def test_database_persistence_type_safety(self, perceptor, mock_embedder):
        """Test that database persistence handles types correctly."""
        # Mock the DAOs
        with patch('kairix_core.cognition.perceptor.incremental_reflection.AgentDAO') as mock_agent_dao_cls, \
             patch('kairix_core.cognition.perceptor.incremental_reflection.MemoryDAO') as mock_memory_dao_cls, \
             patch('kairix_core.cognition.perceptor.incremental_reflection.generate_summary') as mock_summarize:
            
            # Setup mocks
            mock_agent_dao = Mock()
            mock_memory_dao = Mock()
            mock_agent_dao_cls.return_value = mock_agent_dao
            mock_memory_dao_cls.return_value = mock_memory_dao
            
            mock_db_agent = Mock()
            mock_db_agent.id = 1
            mock_agent_dao.find_one_by.return_value = mock_db_agent
            
            mock_summarize.return_value = "Test summary"
            
            # Create messages to trigger summarization
            messages = []
            for i in range(25):
                messages.append(
                    Message(sender="user", content=f"Message {i}", timestamp=datetime.now())
                )
            
            # Run perception
            result = await perceptor.perceive(messages)
            
            # Verify memory_dao.create was called with correct types
            mock_memory_dao.create.assert_called_once()
            call_args = mock_memory_dao.create.call_args[1]
            
            assert isinstance(call_args['contents'], str)
            assert isinstance(call_args['embedding_type'], str)
            assert isinstance(call_args['embedding'], np.ndarray)
            assert isinstance(call_args['agent_id'], int)
            assert call_args['embedding'].shape == (768,)
    
    @pytest.mark.asyncio
    async def test_empty_list_return_type(self, perceptor):
        """Test that empty list is returned when no perception available."""
        # No messages and no last summary
        result = await perceptor.perceive([])
        assert result == []
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_message_accumulation_type_safety(self, perceptor):
        """Test that message accumulation handles types correctly."""
        # Add messages incrementally
        for i in range(10):
            message = Message(
                sender="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                timestamp=datetime.now()
            )
            result = await perceptor.perceive([message])
            
            # Should always return a list
            assert isinstance(result, list)
            
        # Check internal state
        assert len(perceptor.messages) == 10
        assert all(isinstance(msg, str) for msg in perceptor.messages)
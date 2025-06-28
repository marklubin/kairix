"""Test implementation for ConversationHistoryPerceptor."""

import pytest
from unittest.mock import Mock, patch
from rich import pretty

from kairix_core.cognition.perceptor.conversation_history import ConversationHistoryPerceptor
from kairix_core.types.cognition import Stimulus, StimulusType, Perception


class TestConversationHistoryPerceptor:
    """Test cases for ConversationHistoryPerceptor class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock the neomodel database."""
        with patch('kairix_core.cognition.perceptor.conversation_history.db') as mock_db:
            # Default to empty results
            mock_db.cypher_query = Mock(return_value=([], {}))
            yield mock_db
    
    @pytest.fixture
    def perceptor(self, mock_db):
        """Create a perceptor instance with mocked database."""
        return ConversationHistoryPerceptor(agent_id="test_agent", window_size=10)
    
    def test_initialization(self):
        """Test ConversationHistoryPerceptor initialization."""
        # Test with default values
        perceptor = ConversationHistoryPerceptor()
        assert perceptor.agent_id == "default"
        assert perceptor.window_size == 50
        assert perceptor.transient_user_msg_buffer == ""
        assert perceptor._cached_history is None
        
        # Test with custom values
        perceptor_custom = ConversationHistoryPerceptor(
            agent_id="custom_agent",
            window_size=100
        )
        assert perceptor_custom.agent_id == "custom_agent"
        assert perceptor_custom.window_size == 100
    
    @pytest.mark.asyncio
    async def test_perceive_user_message(self, perceptor, mock_db):
        """Test perceiving user messages."""
        # Mock empty history
        mock_db.cypher_query.return_value = ([], {})
        
        stimulus = Stimulus(
            type=StimulusType.user_message,
            content="Hello, how are you?"
        )
        
        result = await perceptor.perceive(stimulus)
        
        # Should buffer the message
        assert perceptor.transient_user_msg_buffer == "Hello, how are you?"
        
        # Should return perception with empty history
        assert len(result) == 1
        assert isinstance(result[0], Perception)
        assert result[0].source == "conversation-history.v1"
        assert result[0].content == pretty.pretty_repr([])
    
    @pytest.mark.asyncio
    async def test_perceive_self_perception_with_buffer(self, perceptor, mock_db):
        """Test perceiving self perception with buffered user message."""
        # Mock empty initial history
        mock_db.cypher_query.return_value = ([], {})
        
        # First, add a user message
        user_stimulus = Stimulus(
            type=StimulusType.user_message,
            content="What's the weather?"
        )
        await perceptor.perceive(user_stimulus)
        
        # Mock the store operation to return count
        mock_db.cypher_query.return_value = ([[1]], {})
        
        # Then add assistant response
        assistant_stimulus = Stimulus(
            type=StimulusType.self_perception,
            content="The weather is sunny."
        )
        result = await perceptor.perceive(assistant_stimulus)
        
        # Should clear the buffer
        assert perceptor.transient_user_msg_buffer == ""
        
        # Should have stored the conversation pair
        expected_query_params = {
            "agent_id": "test_agent",
            "user_message": "What's the weather?",
            "assistant_message": "The weather is sunny."
        }
        
        # Find the store query call
        store_call = None
        for call in mock_db.cypher_query.call_args_list:
            if "CREATE" in call[0][0]:
                store_call = call
                break
        
        assert store_call is not None
        assert store_call[0][1] == expected_query_params
        
        # Cache should be updated
        assert len(perceptor._cached_history) == 1
        assert perceptor._cached_history[0] == {
            "user": "What's the weather?",
            "assistant": "The weather is sunny."
        }
        
        # Result should contain updated history
        assert len(result) == 1
        assert result[0].source == "conversation-history.v1"
    
    @pytest.mark.asyncio
    async def test_perceive_self_perception_without_buffer(self, perceptor, mock_db):
        """Test perceiving self perception without buffered user message."""
        # Initialize with empty history
        mock_db.cypher_query.return_value = ([], {})
        
        with patch('kairix_core.cognition.perceptor.conversation_history.logger') as mock_logger:
            assistant_stimulus = Stimulus(
                type=StimulusType.self_perception,
                content="Some response"
            )
            await perceptor.perceive(assistant_stimulus)
            
            # Should log warning
            mock_logger.warning.assert_called_with(
                "Transient user message unexpectedly empty upon receipt of self reflection."
            )
    
    @pytest.mark.asyncio
    async def test_perceive_other_stimulus_types(self, perceptor, mock_db):
        """Test perceiving other stimulus types."""
        mock_db.cypher_query.return_value = ([], {})
        
        with patch('kairix_core.cognition.perceptor.conversation_history.logger') as mock_logger:
            stimulus = Stimulus(
                type=StimulusType.world_event,
                content="Some event"
            )
            result = await perceptor.perceive(stimulus)
            
            # Should log info
            mock_logger.info.assert_called_with(
                f"No action for Conversation History on stimulus of type {StimulusType.world_event}"
            )
            
            # Should still return perception with current history
            assert len(result) == 1
            assert result[0].source == "conversation-history.v1"
    
    @pytest.mark.asyncio
    async def test_multiple_user_messages_warning(self, perceptor, mock_db):
        """Test warning when multiple user messages are received."""
        mock_db.cypher_query.return_value = ([], {})
        
        # First user message
        await perceptor.perceive(Stimulus(
            type=StimulusType.user_message,
            content="First message"
        ))
        
        with patch('kairix_core.cognition.perceptor.conversation_history.logger') as mock_logger:
            # Second user message without assistant response
            await perceptor.perceive(Stimulus(
                type=StimulusType.user_message,
                content=" Second message"
            ))
            
            # Should log warning
            mock_logger.warning.assert_called_with(
                "Invocation of additional user message with transient outstanding,"
                " ambiguous behavior. Assuming additivity."
            )
            
            # Should concatenate messages
            assert perceptor.transient_user_msg_buffer == "First message Second message"
    
    @pytest.mark.asyncio
    async def test_load_history_from_db(self, perceptor, mock_db):
        """Test loading history from database."""
        # Mock database results
        mock_db.cypher_query.return_value = ([
            ["Hello", "Hi there"],
            ["How are you?", "I'm doing well"],
            ["What's new?", "Not much"]
        ], {})
        
        history = await perceptor._load_history_from_db()
        
        # Should reverse order (DB returns DESC, we want chronological)
        assert history == [
            {"user": "What's new?", "assistant": "Not much"},
            {"user": "How are you?", "assistant": "I'm doing well"},
            {"user": "Hello", "assistant": "Hi there"}
        ]
        
        # Verify query parameters
        mock_db.cypher_query.assert_called_once()
        call_args = mock_db.cypher_query.call_args[0]
        assert call_args[1]["agent_id"] == "test_agent"
        assert call_args[1]["limit"] == 10
    
    @pytest.mark.asyncio
    async def test_get_recent_context(self, perceptor, mock_db):
        """Test getting recent context."""
        # Mock some history
        mock_db.cypher_query.return_value = ([
            ["Message 1", "Response 1"],
            ["Message 2", "Response 2"],
            ["Message 3", "Response 3"]
        ], {})
        
        # Get all context
        context = await perceptor.get_recent_context()
        assert len(context) == 3
        
        # Get limited context
        context_limited = await perceptor.get_recent_context(limit=2)
        assert len(context_limited) == 2
        assert context_limited == [
            {"user": "Message 2", "assistant": "Response 2"},
            {"user": "Message 1", "assistant": "Response 1"}
        ]
    
    @pytest.mark.asyncio
    async def test_window_size_enforcement(self, perceptor, mock_db):
        """Test that window size is enforced in cache."""
        # Start with empty history
        mock_db.cypher_query.return_value = ([], {})
        perceptor.window_size = 3  # Small window for testing
        
        # Add multiple conversation pairs
        for i in range(5):
            # Add user message
            await perceptor.perceive(Stimulus(
                type=StimulusType.user_message,
                content=f"Message {i}"
            ))
            
            # Mock store operation
            mock_db.cypher_query.return_value = ([[i+1]], {})
            
            # Add assistant response
            await perceptor.perceive(Stimulus(
                type=StimulusType.self_perception,
                content=f"Response {i}"
            ))
        
        # Cache should only have last 3 items
        assert len(perceptor._cached_history) == 3
        assert perceptor._cached_history[0]["user"] == "Message 2"
        assert perceptor._cached_history[2]["user"] == "Message 4"
    
    @pytest.mark.asyncio
    async def test_perception_always_returned(self, perceptor, mock_db):
        """Test that perception is always returned regardless of stimulus type."""
        mock_db.cypher_query.return_value = ([], {})
        
        stimulus_types = [
            StimulusType.user_message,
            StimulusType.self_perception,
            StimulusType.world_event,
            StimulusType.execution_attempt,
            StimulusType.time_tick
        ]
        
        for stim_type in stimulus_types:
            stimulus = Stimulus(type=stim_type, content="Test")
            result = await perceptor.perceive(stimulus)
            
            assert len(result) == 1
            assert isinstance(result[0], Perception)
            assert result[0].source == "conversation-history.v1"
            assert isinstance(result[0].content, str)
"""Test implementation for ConversationHistoryPerceptor."""

import pytest
from unittest.mock import Mock, patch

from kairix_core.cognition.perceptor.conversation_history import ConversationHistoryPerceptor
from kairix_core.types.cognition import Stimulus, StimulusType


class TestConversationHistoryPerceptor:
    """Test cases for ConversationHistoryPerceptor class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock the neomodel database."""
        with patch('kairix_core.cognition.perceptor.conversation_history.db') as mock_db:
            mock_db.cypher_query = Mock(return_value=([], {}))
            yield mock_db
    
    @pytest.fixture
    def mock_neomodel_config(self):
        """Mock neomodel config."""
        with patch('kairix_core.cognition.perceptor.conversation_history.neomodel.config') as mock_config:
            yield mock_config
    
    def test_initialization(self, mock_db, mock_neomodel_config):
        """Test ConversationHistoryPerceptor initialization."""
        # Test with default values
        perceptor = ConversationHistoryPerceptor(store_url="bolt://localhost:7687")
        
        assert perceptor.agent_id == "default"
        assert perceptor.max_pairs == 10
        assert perceptor._pending_user_message is None
        mock_neomodel_config.DATABASE_URL = "bolt://localhost:7687"
        mock_db.set_connection.assert_called_once_with("bolt://localhost:7687")
        
        # Test with custom values
        mock_db.reset_mock()
        perceptor_custom = ConversationHistoryPerceptor(
            store_url="bolt://custom:7687",
            agent_id="test_agent",
            max_pairs=20
        )
        
        assert perceptor_custom.agent_id == "test_agent"
        assert perceptor_custom.max_pairs == 20
        mock_db.set_connection.assert_called_once_with("bolt://custom:7687")
    
    @pytest.mark.asyncio
    async def test_perceive_user_message(self, mock_db, mock_neomodel_config):
        """Test perceive method with user_message stimulus."""
        perceptor = ConversationHistoryPerceptor(store_url="bolt://localhost:7687")
        
        # Test user message stimulus
        stimulus = Stimulus(
            content="Hello, how are you?",
            type=StimulusType.user_message
        )
        
        perceptions = await perceptor.perceive(stimulus)
        
        # Should store message internally but return empty perceptions
        assert perceptions == []
        assert perceptor._pending_user_message == "Hello, how are you?"
        
        # Database should not be called for user messages
        mock_db.cypher_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_perceive_action_reflection(self, mock_db, mock_neomodel_config):
        """Test perceive method with action_reflection stimulus."""
        perceptor = ConversationHistoryPerceptor(store_url="bolt://localhost:7687")
        
        # Set up mock return value
        mock_db.cypher_query.return_value = ([[5]], {})
        
        # First store a user message
        user_stimulus = Stimulus(
            content="What's the weather?",
            type=StimulusType.user_message
        )
        await perceptor.perceive(user_stimulus)
        
        # Create mock stimulus with action_reflection type
        reflection_stimulus = Mock()
        reflection_stimulus.type = Mock()
        reflection_stimulus.type.value = "action_reflection"
        reflection_stimulus.content = "The weather is sunny today."
        
        # Process reflection
        perceptions = await perceptor.perceive(reflection_stimulus)
        
        # Should return empty perceptions
        assert perceptions == []
        assert perceptor._pending_user_message is None
        
        # Verify database call
        mock_db.cypher_query.assert_called_once()
        call_args = mock_db.cypher_query.call_args
        assert call_args[0][0].strip().startswith("// Create new conversation pair")
        assert call_args[0][1]["agent_id"] == "default"
        assert call_args[0][1]["user_message"] == "What's the weather?"
        assert call_args[0][1]["assistant_message"] == "The weather is sunny today."
        assert call_args[0][1]["max_pairs"] == 10
    
    @pytest.mark.asyncio
    async def test_perceive_other_stimulus_types(self, mock_db, mock_neomodel_config):
        """Test perceive method with other stimulus types."""
        perceptor = ConversationHistoryPerceptor(store_url="bolt://localhost:7687")
        
        # Test with time_tick stimulus
        stimulus = Stimulus(
            content="2024-01-01T12:00:00",
            type=StimulusType.time_tick
        )
        
        perceptions = await perceptor.perceive(stimulus)
        
        # Should return empty and not affect state
        assert perceptions == []
        assert perceptor._pending_user_message is None
        mock_db.cypher_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_action_reflection_without_pending_message(self, mock_db, mock_neomodel_config):
        """Test action_reflection without a pending user message."""
        perceptor = ConversationHistoryPerceptor(store_url="bolt://localhost:7687")
        
        # Create reflection without user message
        reflection_stimulus = Mock()
        reflection_stimulus.type = Mock()
        reflection_stimulus.type.value = "action_reflection"
        reflection_stimulus.content = "This is a response."
        
        perceptions = await perceptor.perceive(reflection_stimulus)
        
        # Should return empty and not call database
        assert perceptions == []
        mock_db.cypher_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_recent_context(self, mock_db, mock_neomodel_config):
        """Test retrieving recent conversation context."""
        perceptor = ConversationHistoryPerceptor(store_url="bolt://localhost:7687")
        
        # Mock database response
        mock_db.cypher_query.return_value = ([
            ["How are you?", "I'm doing well!"],
            ["What's the weather?", "It's sunny today."],
            ["Tell me a joke", "Why did the chicken cross the road?"]
        ], {})
        
        # Test with default limit
        context = await perceptor.get_recent_context()
        
        # Verify query
        mock_db.cypher_query.assert_called_once()
        call_args = mock_db.cypher_query.call_args
        assert "MATCH (cp:ConversationPair {agent_id: $agent_id})" in call_args[0][0]
        assert call_args[0][1]["agent_id"] == "default"
        assert call_args[0][1]["limit"] == 10
        
        # Verify results are reversed (chronological order)
        assert len(context) == 3
        assert context[0] == {"user": "Tell me a joke", "assistant": "Why did the chicken cross the road?"}
        assert context[1] == {"user": "What's the weather?", "assistant": "It's sunny today."}
        assert context[2] == {"user": "How are you?", "assistant": "I'm doing well!"}
    
    @pytest.mark.asyncio
    async def test_get_recent_context_with_custom_limit(self, mock_db, mock_neomodel_config):
        """Test retrieving context with custom limit."""
        perceptor = ConversationHistoryPerceptor(store_url="bolt://localhost:7687", max_pairs=20)
        
        mock_db.cypher_query.return_value = ([
            ["Message 1", "Response 1"],
            ["Message 2", "Response 2"]
        ], {})
        
        context = await perceptor.get_recent_context(limit=5)
        
        # Verify custom limit is used
        call_args = mock_db.cypher_query.call_args
        assert call_args[0][1]["limit"] == 5
        
        assert len(context) == 2
    
    @pytest.mark.asyncio
    async def test_get_recent_context_empty(self, mock_db, mock_neomodel_config):
        """Test retrieving context when no conversations exist."""
        perceptor = ConversationHistoryPerceptor(store_url="bolt://localhost:7687")
        
        mock_db.cypher_query.return_value = ([], {})
        
        context = await perceptor.get_recent_context()
        
        assert context == []
    
    @pytest.mark.asyncio
    async def test_rolling_window_behavior(self, mock_db, mock_neomodel_config):
        """Test that old conversations are deleted when limit is exceeded."""
        perceptor = ConversationHistoryPerceptor(
            store_url="bolt://localhost:7687",
            max_pairs=3
        )
        
        # Mock return showing 4 total pairs (one will be deleted)
        mock_db.cypher_query.return_value = ([[4]], {})
        
        # Store a conversation pair
        await perceptor.perceive(Stimulus(content="User message", type=StimulusType.user_message))
        
        reflection_stimulus = Mock()
        reflection_stimulus.type = Mock()
        reflection_stimulus.type.value = "action_reflection"
        reflection_stimulus.content = "Assistant response"
        
        await perceptor.perceive(reflection_stimulus)
        
        # Verify the query includes deletion logic
        call_args = mock_db.cypher_query.call_args
        query = call_args[0][0]
        assert "DELETE oldPair" in query
        assert "$max_pairs" in query
        assert call_args[0][1]["max_pairs"] == 3
    
    @pytest.mark.asyncio
    async def test_special_character_handling(self, mock_db, mock_neomodel_config):
        """Test handling of special characters in messages."""
        perceptor = ConversationHistoryPerceptor(store_url="bolt://localhost:7687")
        
        mock_db.cypher_query.return_value = ([[1]], {})
        
        # Test with special characters
        special_content = 'Hello "world"! How\'s it going? \n\t Special chars: $@#%'
        
        await perceptor.perceive(Stimulus(content=special_content, type=StimulusType.user_message))
        
        reflection_stimulus = Mock()
        reflection_stimulus.type = Mock()
        reflection_stimulus.type.value = "action_reflection"
        reflection_stimulus.content = 'Response with "quotes" and \nnewlines'
        
        await perceptor.perceive(reflection_stimulus)
        
        # Verify special characters are passed correctly
        call_args = mock_db.cypher_query.call_args
        assert call_args[0][1]["user_message"] == special_content
        assert call_args[0][1]["assistant_message"] == 'Response with "quotes" and \nnewlines'
    
    def test_database_connection_initialization(self, mock_db, mock_neomodel_config):
        """Test that database connection is properly initialized."""
        store_url = "bolt://neo4j:password@localhost:7687"
        
        ConversationHistoryPerceptor(store_url=store_url)
        
        # Verify neomodel config is set
        mock_neomodel_config.DATABASE_URL = store_url
        
        # Verify connection is established
        mock_db.set_connection.assert_called_once_with(store_url)
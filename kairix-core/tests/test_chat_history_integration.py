from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from kairix_apps.basic_chat import Chat
from kairix_core.cognition.perceptor.conversation_history_perceptor import ConversationHistoryPerceptor


@pytest.fixture
def mock_perceptor():
    """Fixture providing a mock perceptor"""
    perceptor = Mock()
    perceptor.perceive = AsyncMock(return_value=[])
    return perceptor


@pytest.fixture
def mock_runner():
    """Fixture providing a mock runner"""
    runner = Mock()
    runner.run_streamed = AsyncMock()
    return runner


@pytest.fixture
def mock_history_perceptor():
    """Fixture providing a mock history perceptor"""
    perceptor = Mock(spec=ConversationHistoryPerceptor)
    perceptor.perceive = AsyncMock(return_value=[])
    perceptor.get_recent_context = AsyncMock(return_value=[])
    return perceptor


@pytest_asyncio.fixture
async def chat_with_history(mock_perceptor, mock_runner, mock_history_perceptor):
    """Fixture providing a Chat instance with history perceptor"""
    chat_instance = Chat(
        user_name="TestUser",
        agent_name="TestAgent",
        runner=mock_runner,
        perceptor=mock_perceptor,
        history_perceptor=mock_history_perceptor,
        environmental_perceptor=None
    )
    await chat_instance.initialize()
    yield chat_instance
    await chat_instance.close()


class TestChatHistoryIntegration:
    """Test cases for Chat with ConversationHistoryPerceptor integration"""

    @pytest.mark.asyncio
    async def test_chat_loads_recent_context(
        self, chat_with_history, mock_history_perceptor
    ):
        """Test that chat loads recent context on initialization"""
        # Setup mock to return some history
        mock_history_perceptor.get_recent_context.return_value = [
            {"user": "Hello", "assistant": "Hi there!"},
            {"user": "How are you?", "assistant": "I'm doing well, thanks!"}
        ]
        
        # Re-initialize to load context
        await chat_with_history.initialize()
        
        # Verify context was loaded
        assert len(chat_with_history.history) == 4  # 2 pairs = 4 messages
        assert chat_with_history.history[0].content == "Hello"
        assert chat_with_history.history[1].content == "Hi there!"
        assert chat_with_history.history[2].content == "How are you?"
        assert chat_with_history.history[3].content == "I'm doing well, thanks!"

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_chat_sends_stimuli_to_history_perceptor(
        self, mock_helper, chat_with_history, mock_runner, mock_history_perceptor
    ):
        """Test that chat sends both user and assistant messages to history perceptor"""
        # Setup
        mock_result = Mock()
        mock_result.final_output_as.return_value = "I'm here to help!"
        mock_runner.run_streamed.return_value = mock_result
        
        # Mock the stream helper
        async def mock_stream():
            yield "I'm "
            yield "here "
            yield "to "
            yield "help!"
        
        mock_helper.stream_text_from.return_value = mock_stream()
        
        # Execute
        response_chunks = []
        async for chunk in chat_with_history.chat("Hello!"):
            response_chunks.append(chunk)
        
        # Verify history perceptor was called twice
        assert mock_history_perceptor.perceive.call_count == 2
        
        # First call should be for user message
        first_call = mock_history_perceptor.perceive.call_args_list[0]
        user_stimulus = first_call[0][0]
        assert user_stimulus.content == "Hello!"
        assert user_stimulus.type.value == "user_message"
        
        # Second call should be for assistant response
        second_call = mock_history_perceptor.perceive.call_args_list[1]
        assistant_stimulus = second_call[0][0]
        assert assistant_stimulus.content == "I'm here to help!"
        # The type will be our custom ActionReflectionStimulus

    @pytest.mark.asyncio
    async def test_chat_without_history_perceptor(self, mock_perceptor, mock_runner):
        """Test that chat works without history perceptor"""
        chat_instance = Chat(
            user_name="TestUser",
            agent_name="TestAgent",
            runner=mock_runner,
            perceptor=mock_perceptor,
            history_perceptor=None,
            environmental_perceptor=None
        )
        
        await chat_instance.initialize()
        
        # Should initialize without errors
        assert chat_instance.history_perceptor is None
        assert len(chat_instance.history) == 0

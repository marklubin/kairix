from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
import yaml

from kairix_engine.basic_chat import Chat


@pytest.fixture
def mock_perceptor():
    """Fixture providing a mock perceptor"""
    perceptor = Mock()
    perceptor.perceive = AsyncMock(return_value=[])
    return perceptor


@pytest_asyncio.fixture
async def chat_with_history(mock_perceptor, tmp_path):
    """Fixture providing a Chat instance with message history enabled"""
    chat_instance = Chat(
        user_name="TestUser",
        agent_name="TestAgent",
        perceptor=mock_perceptor,
        enable_history=True,
        history_log_dir=str(tmp_path / "chat_logs"),
        max_context_pairs=5
    )
    await chat_instance.initialize()
    yield chat_instance
    await chat_instance.close()


class TestChatHistoryIntegration:
    """Test cases for Chat with MessageHistory integration"""

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    async def test_chat_persists_messages(self, mock_runner, chat_with_history):
        """Test that chat messages are persisted to file"""
        # Setup
        test_input = "Hello, how are you?"
        expected_response = "I'm doing well, thank you!"
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = expected_response
        mock_runner.run = AsyncMock(return_value=mock_result)
        
        # Execute
        await chat_with_history.chat(test_input)
        
        # Wait for async write
        import asyncio
        await asyncio.sleep(0.1)
        
        # Verify message was persisted
        log_file = next(
            chat_with_history.message_history._filename.parent.glob("*.yaml")
        )
        import aiofiles
        async with aiofiles.open(log_file) as f:
            content = await f.read()
            data = yaml.safe_load(content)
        
        assert len(data["messages"]) == 1
        assert data["messages"][0]["user"] == test_input
        assert data["messages"][0]["assistant"] == expected_response

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_persists_messages(
        self, mock_helper, mock_runner, chat_with_history
    ):
        """Test that run() streaming method persists messages"""
        # Setup
        test_input = "Tell me a story"
        expected_response = "Once upon a time..."
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = expected_response
        mock_runner.run_streamed.return_value = mock_result
        
        # Mock streaming
        async def mock_stream(*args):
            yield "Once "
            yield "upon "
            yield "a time..."
        
        mock_helper.stream_text_from.return_value = mock_stream()
        
        # Execute
        chunks = []
        async for chunk in chat_with_history.run(test_input):
            chunks.append(chunk)
        
        # Wait for async write
        import asyncio
        await asyncio.sleep(0.1)
        
        # Verify message was persisted
        log_file = next(
            chat_with_history.message_history._filename.parent.glob("*.yaml")
        )
        import aiofiles
        async with aiofiles.open(log_file) as f:
            content = await f.read()
            data = yaml.safe_load(content)
        
        assert len(data["messages"]) == 1
        assert data["messages"][0]["user"] == test_input
        assert data["messages"][0]["assistant"] == expected_response

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    async def test_chat_loads_history_on_init(
        self, mock_runner, mock_perceptor, tmp_path
    ):
        """Test that chat loads previous messages on initialization"""
        # Create a history file with existing messages
        log_dir = tmp_path / "chat_logs"
        log_dir.mkdir()
        
        import datetime
        today = datetime.date.today()
        log_file = log_dir / f"chat_{today.strftime('%Y-%m-%d')}.yaml"
        
        existing_messages = {
            "messages": [
                {
                    "timestamp": "2025-01-15T10:00:00Z",
                    "user": "Previous question",
                    "assistant": "Previous answer"
                },
                {
                    "timestamp": "2025-01-15T10:01:00Z",
                    "user": "Another question",
                    "assistant": "Another answer"
                }
            ]
        }
        
        import aiofiles
        async with aiofiles.open(log_file, 'w') as f:
            await f.write(yaml.dump(existing_messages))
        
        # Create chat instance
        chat = Chat(
            user_name="TestUser",
            agent_name="TestAgent",
            perceptor=mock_perceptor,
            enable_history=True,
            history_log_dir=str(log_dir),
            max_context_pairs=10
        )
        
        await chat.initialize()
        
        # Verify history was loaded
        assert len(chat.history) == 4  # 2 user + 2 assistant messages
        assert chat.history[0].content == "Previous question"
        assert chat.history[1].content == "Previous answer"
        assert chat.history[2].content == "Another question"
        assert chat.history[3].content == "Another answer"
        
        await chat.close()

    @pytest.mark.asyncio
    async def test_chat_without_history(self, mock_perceptor):
        """Test that chat works with history disabled"""
        chat = Chat(
            user_name="TestUser",
            agent_name="TestAgent",
            perceptor=mock_perceptor,
            enable_history=False
        )
        
        await chat.initialize()
        
        # Verify no message history was created
        assert chat.message_history is None
        
        await chat.close()
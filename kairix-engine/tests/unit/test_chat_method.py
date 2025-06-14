from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from kairix_engine.basic_chat import Chat, KairixMessage


@pytest.fixture
def mock_perceptor():
    """Fixture providing a mock perceptor"""
    perceptor = Mock()
    perceptor.perceive = AsyncMock(return_value=[])
    return perceptor


@pytest_asyncio.fixture
async def chat(mock_perceptor):
    """Fixture providing a Chat instance with mocked dependencies"""
    chat_instance = Chat(
        user_name="TestUser",
        agent_name="TestAgent",
        perceptor=mock_perceptor,
        enable_history=False  # Disable file history for tests
    )
    await chat_instance.initialize()
    yield chat_instance
    await chat_instance.close()


class TestChatMethod:
    """Test cases for the Chat.chat() method"""

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    async def test_chat_basic_interaction(self, mock_runner, chat):
        """Test basic chat interaction flow"""
        # Setup
        test_input = "Hello, how are you?"
        expected_response = "I'm doing well, thank you!"
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = expected_response
        mock_runner.run = AsyncMock(return_value=mock_result)
        
        # Execute
        response = await chat.chat(test_input)
        
        # Verify
        assert response == expected_response
        mock_runner.run.assert_called_once()
        assert mock_result.final_output_as.called_with(str)
        
        # Check history
        assert len(chat.history) == 2
        assert chat.history[0].role == "user"
        assert chat.history[0].content == test_input
        assert chat.history[1].role == "assistant"
        assert chat.history[1].content == expected_response

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    @patch("kairix_engine.basic_chat.Stimulus")
    async def test_chat_with_memory_integration(
        self, mock_stimulus, mock_runner, chat, mock_perceptor
    ):
        """Test chat with memory/perceptor integration"""
        # Setup
        test_input = "What did we discuss yesterday?"
        expected_response = "Yesterday we discussed your project deadline."
        
        # Mock perception with memory
        mock_perception = Mock()
        mock_perception.content = "Previous discussion about project deadline"
        mock_perception.confidence = "0.95"
        mock_perception.source = "conversation_2024_01_01"
        mock_perceptor.perceive = AsyncMock(return_value=[mock_perception])
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = expected_response
        mock_runner.run = AsyncMock(return_value=mock_result)
        
        # Execute
        response = await chat.chat(test_input)
        
        # Verify
        assert response == expected_response
        mock_perceptor.perceive.assert_called_once()
        mock_stimulus.assert_called_once()
        
        # Verify the agent was called with context including memories
        call_args = mock_runner.run.call_args[0]
        agent_prompt = call_args[1]
        assert "RECOLLECTIONS" in agent_prompt
        # Check memory content is included
        assert "Previous discussion about project deadline" in agent_prompt

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    async def test_chat_conversation_continuity(self, mock_runner, chat):
        """Test that conversation history is maintained across multiple calls"""
        # Setup responses
        responses = [
            "Hello! I'm your AI assistant.",
            "Your name is TestUser.",
            "We've been talking about names."
        ]
        
        mock_result = Mock()
        mock_runner.run = AsyncMock(return_value=mock_result)
        
        # Execute multiple interactions
        inputs = [
            "Hello!",
            "What's my name?",
            "What have we been talking about?"
        ]
        
        for _i, (user_input, expected_response) in enumerate(
            zip(inputs, responses, strict=False)
        ):
            mock_result.final_output_as.return_value = expected_response
            response = await chat.chat(user_input)
            assert response == expected_response
        
        # Verify history accumulation
        assert len(chat.history) == 6  # 3 user + 3 assistant messages
        
        # Verify history content
        for i in range(3):
            assert chat.history[i*2].role == "user"
            assert chat.history[i*2].content == inputs[i]
            assert chat.history[i*2+1].role == "assistant"
            assert chat.history[i*2+1].content == responses[i]

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    async def test_chat_system_prompt_integration(self, mock_runner, chat):
        """Test that system prompt is properly integrated"""
        # Setup
        test_input = "Tell me about yourself"
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = "I am TestAgent"
        mock_runner.run = AsyncMock(return_value=mock_result)
        
        # Execute
        await chat.chat(test_input)
        
        # Verify agent was initialized with proper system prompt
        agent = chat.agent
        assert "TestAgent" in agent.instructions
        assert "TestUser" in agent.instructions
        assert "AI Assistant" in agent.instructions

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    @patch("kairix_engine.basic_chat.logger")
    async def test_chat_memory_logging(
        self, mock_logger, mock_runner, chat, mock_perceptor
    ):
        """Test that memory recovery is properly logged"""
        # Setup with memories
        mock_perception = Mock()
        mock_perception.content = "Important memory content"
        mock_perception.confidence = "0.87"
        mock_perception.source = "memory_source_123"
        mock_perceptor.perceive = AsyncMock(return_value=[mock_perception])
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = "Response based on memory"
        mock_runner.run = AsyncMock(return_value=mock_result)
        
        # Execute
        await chat.chat("What do you remember?")
        
        # Verify logging
        assert mock_logger.debug.called
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("[Memory Recovered]" in str(call) for call in debug_calls)
        assert any("memory_source_123" in str(call) for call in debug_calls)
        assert any("0.87" in str(call) for call in debug_calls)

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    async def test_chat_empty_input_handling(self, mock_runner, chat):
        """Test handling of empty input"""
        # Setup
        mock_result = Mock()
        mock_result.final_output_as.return_value = "Please provide some input."
        mock_runner.run = AsyncMock(return_value=mock_result)
        
        # Execute
        response = await chat.chat("")
        
        # Verify
        assert response == "Please provide some input."
        assert len(chat.history) == 2

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    async def test_chat_error_propagation(self, mock_runner, chat):
        """Test that errors from Runner are properly propagated"""
        # Setup
        mock_runner.run = AsyncMock(side_effect=Exception("Runner failed"))
        
        # Execute and verify
        with pytest.raises(Exception) as exc_info:
            await chat.chat("Test input")
        
        assert str(exc_info.value) == "Runner failed"
        # History should still contain the user message
        assert len(chat.history) == 1
        assert chat.history[0].content == "Test input"


class TestKairixMessage:
    """Test cases for the KairixMessage dataclass"""

    def test_user_message_creation(self):
        """Test creating a user message"""
        msg = KairixMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert str(msg) == "user:\tHello\n"

    def test_assistant_message_creation(self):
        """Test creating an assistant message"""
        msg = KairixMessage(role="assistant", content="Hi there")
        assert msg.role == "assistant"
        assert msg.content == "Hi there"
        assert str(msg) == "assistant:\tHi there\n"

    def test_message_string_representation(self):
        """Test string representation of messages"""
        user_msg = KairixMessage(role="user", content="Question?")
        assistant_msg = KairixMessage(role="assistant", content="Answer!")
        
        assert str(user_msg) == "user:\tQuestion?\n"
        assert str(assistant_msg) == "assistant:\tAnswer!\n"


class TestChatTemplates:
    """Test cases for chat template functions"""

    def test_chat_template_formatting(self):
        """Test chat_template function formatting"""
        from kairix_engine.basic_chat import chat_template
        
        recollections = "Memory 1\nMemory 2"
        dialog = "User: Hello\nAssistant: Hi"
        
        result = chat_template(recollections, dialog)
        
        assert "<RECOLLECTIONS>" in result
        assert recollections in result
        assert "<DIALOG>" in result
        assert dialog in result
        assert "first person" in result

    def test_system_message_template(self):
        """Test system_messge_template function"""
        from kairix_engine.basic_chat import system_messge_template
        
        result = system_messge_template("TestAgent", "TestUser")
        
        assert "TestAgent" in result
        assert "TestUser" in result
        assert "AI Assistant" in result
        assert "Core Operating Principles" in result
        assert "Precision & Clarity" in result
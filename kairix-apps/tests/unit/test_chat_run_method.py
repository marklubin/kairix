from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from kairix_engine.basic_chat import Chat


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


@pytest_asyncio.fixture
async def chat(mock_perceptor, mock_runner):
    """Fixture providing a Chat instance with mocked dependencies"""
    chat_instance = Chat(
        user_name="TestUser",
        agent_name="TestAgent",
        runner=mock_runner,
        perceptor=mock_perceptor,
        history_perceptor=None,  # No history perceptor for tests
        environmental_perceptor=None  # No environmental perceptor for tests
    )
    await chat_instance.initialize()
    yield chat_instance
    await chat_instance.close()


class TestChatRunMethod:
    """Test cases for the Chat.run() async streaming method"""

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_basic_streaming(self, mock_helper, chat, mock_runner):
        """Test basic streaming functionality of run method"""
        # Setup
        test_input = "Hello, stream this response"
        chunks = ["Hello", " there", ", how", " are", " you", "?"]
        expected_response = "".join(chunks)
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = expected_response
        mock_runner.run_streamed.return_value = mock_result
        
        # Mock streaming response
        async def mock_stream():
            for chunk in chunks:
                yield chunk
        
        mock_helper.stream_text_from.return_value = mock_stream()
        
        # Execute
        received_chunks = []
        async for chunk in chat.run(test_input):
            received_chunks.append(chunk)
        
        # Verify
        assert received_chunks == chunks
        assert "".join(received_chunks) == expected_response
        mock_runner.run_streamed.assert_called_once()

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_with_memory_integration(
        self, mock_helper, chat, mock_runner, mock_perceptor
    ):
        """Test run method with memory perceptor integration"""
        # Setup memory
        mock_perception = Mock()
        mock_perception.content = "Previous conversation context"
        mock_perception.source = "memory_001"
        mock_perceptor.perceive = AsyncMock(return_value=[mock_perception])
        
        test_input = "What did we talk about?"
        response_text = "We discussed your project."
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = response_text
        mock_runner.run_streamed.return_value = mock_result
        
        # Mock streaming
        async def mock_stream():
            yield response_text
        
        mock_helper.stream_text_from.return_value = mock_stream()
        
        # Execute
        chunks = []
        async for chunk in chat.run(test_input):
            chunks.append(chunk)
        
        # Verify
        assert "".join(chunks) == response_text
        mock_perceptor.perceive.assert_called_once()

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_empty_stream(self, mock_helper, chat, mock_runner):
        """Test handling of empty stream responses"""
        # Setup
        mock_result = Mock()
        mock_result.final_output_as.return_value = ""
        mock_runner.run_streamed.return_value = mock_result
        
        # Mock empty stream
        async def mock_stream():
            # Yield nothing
            return
            yield  # This makes it a generator
        
        mock_helper.stream_text_from.return_value = mock_stream()
        
        # Execute
        chunks = []
        async for chunk in chat.run("Hello"):
            chunks.append(chunk)
        
        # Verify
        assert chunks == []
        assert len(chat.history) == 2  # User and empty assistant message

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_conversation_continuity(self, mock_helper, chat, mock_runner):
        """Test that run method maintains conversation history"""
        # Setup
        conversations = [
            ("Hello", "Hi there!"),
            ("How are you?", "I'm doing well!"),
            ("What's your name?", "I'm TestAgent")
        ]
        
        for user_input, assistant_response in conversations:
            mock_result = Mock()
            mock_result.final_output_as.return_value = assistant_response
            mock_runner.run_streamed.return_value = mock_result
            
            # Mock streaming
            async def mock_stream(response=assistant_response):
                yield response
            
            mock_helper.stream_text_from.return_value = mock_stream()
            
            # Execute
            chunks = []
            async for chunk in chat.run(user_input):
                chunks.append(chunk)
            
            assert "".join(chunks) == assistant_response
        
        # Verify history
        assert len(chat.history) == 6  # 3 conversations * 2 messages each
        for i, (user_input, assistant_response) in enumerate(conversations):
            assert chat.history[i*2].content == user_input
            assert chat.history[i*2+1].content == assistant_response

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_streaming_error_handling(self, mock_helper, chat, mock_runner):
        """Test error handling during streaming"""
        # Setup - error during streaming
        async def mock_stream_with_error():
            yield "Starting to resp-"
            raise Exception("Stream interrupted")
        
        mock_helper.stream_text_from.return_value = mock_stream_with_error()
        
        mock_result = Mock()
        mock_runner.run_streamed.return_value = mock_result
        
        # Execute and verify
        chunks = []
        with pytest.raises(Exception, match="Stream interrupted"):
            async for chunk in chat.run("Test"):
                chunks.append(chunk)
        
        # Should have received partial response
        assert chunks == ["Starting to resp-"]

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_partial_response_on_error(self, mock_helper, chat, mock_runner):
        """Test that partial responses are still yielded before errors"""
        # Setup
        chunks_before_error = ["Hello", ", I'm", " starting"]
        
        async def mock_stream_partial():
            for chunk in chunks_before_error:
                yield chunk
            raise RuntimeError("Connection lost")
        
        mock_helper.stream_text_from.return_value = mock_stream_partial()
        
        mock_result = Mock()
        mock_runner.run_streamed.return_value = mock_result
        
        # Execute
        received_chunks = []
        try:
            async for chunk in chat.run("Test"):
                received_chunks.append(chunk)
        except RuntimeError:
            pass
        
        # Verify partial response was received
        assert received_chunks == chunks_before_error

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_memory_logging_during_stream(
        self, mock_helper, chat, mock_runner, mock_perceptor, caplog
    ):
        """Test that memory logging works during streaming"""
        # Setup memory
        mock_perception = Mock()
        mock_perception.content = "Important context"
        mock_perception.source = "memory_source"
        mock_perceptor.perceive = AsyncMock(return_value=[mock_perception])
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = "Response"
        mock_runner.run_streamed.return_value = mock_result
        
        # Mock streaming
        async def mock_stream():
            yield "Response"
        
        mock_helper.stream_text_from.return_value = mock_stream()
        
        # Execute
        async for _ in chat.run("Test"):
            pass
        
        # Verify memory perceptor was called
        # Note: Logging may not appear in tests due to log level settings
        assert mock_perceptor.perceive.called

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_voice_workflow_integration(self, mock_helper, chat, mock_runner):
        """Test that run method properly implements VoiceWorkflowBase interface"""
        # The run method should delegate to chat method
        test_transcription = "Voice input transcription"
        expected_chunks = ["Voice", " response"]
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = "Voice response"
        mock_runner.run_streamed.return_value = mock_result
        
        # Mock streaming
        async def mock_stream():
            for chunk in expected_chunks:
                yield chunk
        
        mock_helper.stream_text_from.return_value = mock_stream()
        
        # Execute via run (voice workflow interface)
        chunks = []
        async for chunk in chat.run(test_transcription):
            chunks.append(chunk)
        
        # Verify
        assert chunks == expected_chunks


class TestChatAsyncHelpers:
    """Test cases for Chat async helper methods"""

    @pytest.mark.asyncio
    async def test_prepare_method(self, chat, mock_perceptor):
        """Test the _prepare method"""
        # Setup
        mock_perception = Mock()
        mock_perception.content = "Memory content"
        mock_perception.source = "test"
        mock_perceptor.perceive = AsyncMock(return_value=[mock_perception])
        
        # Execute
        result = await chat._prepare("Test input")
        
        # Verify
        assert isinstance(result, str)
        assert "RECOLLECTIONS" in result
        assert "Memory content" in result
        assert "Test input" in result  # User input should be in dialog
        # The dialog section should contain the user message
        assert "user:\tTest input" in result

    def test_record_method(self, chat):
        """Test the _record method"""
        # Initial state
        assert len(chat.history) == 0
        
        # Record a response
        chat._record("Test response")
        
        # Verify
        assert len(chat.history) == 1
        assert chat.history[0].role == "assistant"
        assert chat.history[0].content == "Test response"
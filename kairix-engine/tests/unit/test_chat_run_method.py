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


class TestChatRunMethod:
    """Test cases for the Chat.run() async streaming method"""

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_basic_streaming(self, mock_helper, mock_runner, chat):
        """Test basic streaming functionality of run method"""
        # Setup
        test_input = "Hello, stream this response"
        chunks = ["Hello", " there", ", how", " are", " you", "?"]
        full_response = "".join(chunks)
        
        # Mock the streaming result
        mock_result = Mock()
        mock_result.final_output_as.return_value = full_response
        mock_runner.run_streamed.return_value = mock_result
        
        # Mock the async generator for streaming
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
        mock_runner.run_streamed.assert_called_once()
        mock_helper.stream_text_from.assert_called_once_with(mock_result)
        
        # Check history is updated after streaming
        assert len(chat.history) == 2
        assert chat.history[0].role == "user"
        assert chat.history[0].content == test_input
        assert chat.history[1].role == "assistant"
        assert chat.history[1].content == full_response

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_with_memory_integration(
        self, mock_helper, mock_runner, chat, mock_perceptor
    ):
        """Test streaming with memory/perceptor integration"""
        # Setup
        test_input = "What did we discuss in our last meeting?"
        
        # Mock perception with memory
        mock_perception = Mock()
        mock_perception.content = "Meeting notes from last week"
        mock_perception.confidence = "0.92"
        mock_perception.source = "meeting_2024_01_15"
        mock_perceptor.perceive = AsyncMock(return_value=[mock_perception])
        
        # Mock streaming
        chunks = ["We discussed", " the project", " timeline."]
        full_response = "".join(chunks)
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = full_response
        mock_runner.run_streamed.return_value = mock_result
        
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
        mock_perceptor.perceive.assert_called_once()
        
        # Verify the agent was called with context including memories
        call_args = mock_runner.run_streamed.call_args[0]
        agent_prompt = call_args[1]
        assert "RECOLLECTIONS" in agent_prompt
        assert "Meeting notes from last week" in agent_prompt

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_empty_stream(self, mock_helper, mock_runner, chat):
        """Test handling of empty streaming response"""
        # Setup
        test_input = "Give me nothing"
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = ""
        mock_runner.run_streamed.return_value = mock_result
        
        # Mock empty stream
        async def mock_stream():
            return
            yield  # Makes it a generator but yields nothing
        
        mock_helper.stream_text_from.return_value = mock_stream()
        
        # Execute
        received_chunks = []
        async for chunk in chat.run(test_input):
            received_chunks.append(chunk)
        
        # Verify
        assert received_chunks == []
        assert len(chat.history) == 2
        assert chat.history[1].content == ""

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_conversation_continuity(self, mock_helper, mock_runner, chat):
        """Test that conversation history is maintained across streaming calls"""
        # Setup multiple interactions
        interactions = [
            ("Hello!", ["Hi", " there!"]),
            ("What's your name?", ["I am", " TestAgent"]),
            ("Nice to meet you", ["Nice to", " meet you", " too!"])
        ]
        
        mock_result = Mock()
        mock_runner.run_streamed.return_value = mock_result
        
        # Execute multiple streaming interactions
        for user_input, expected_chunks in interactions:
            full_response = "".join(expected_chunks)
            mock_result.final_output_as.return_value = full_response
            
            async def mock_stream(chunks=expected_chunks):
                for chunk in chunks:
                    yield chunk
            
            mock_helper.stream_text_from.return_value = mock_stream()
            
            received_chunks = []
            async for chunk in chat.run(user_input):
                received_chunks.append(chunk)
            
            assert received_chunks == expected_chunks
        
        # Verify history accumulation
        assert len(chat.history) == 6  # 3 user + 3 assistant messages
        
        # Verify history content
        for i, (user_input, chunks) in enumerate(interactions):
            assert chat.history[i*2].role == "user"
            assert chat.history[i*2].content == user_input
            assert chat.history[i*2+1].role == "assistant"
            assert chat.history[i*2+1].content == "".join(chunks)

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_streaming_error_handling(self, mock_helper, mock_runner, chat):
        """Test error handling during streaming"""
        # Setup
        test_input = "This will fail"
        
        mock_result = Mock()
        mock_runner.run_streamed.return_value = mock_result
        
        # Mock stream that raises an error
        async def mock_stream_with_error():
            yield "Starting..."
            raise Exception("Stream failed")
        
        mock_helper.stream_text_from.return_value = mock_stream_with_error()
        
        # Execute and verify
        received_chunks = []
        with pytest.raises(Exception) as exc_info:
            async for chunk in chat.run(test_input):
                received_chunks.append(chunk)
        
        assert str(exc_info.value) == "Stream failed"
        assert received_chunks == ["Starting..."]
        # User message should be in history, but not assistant message
        assert len(chat.history) == 1
        assert chat.history[0].content == test_input

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_partial_response_on_error(self, mock_helper, mock_runner, chat):
        """Test that partial responses are handled correctly on error"""
        # Setup
        test_input = "Stream with partial failure"
        chunks_before_error = ["Hello", " world"]
        
        mock_result = Mock()
        # This should be called even if streaming fails partway
        mock_result.final_output_as.return_value = "Hello world"
        mock_runner.run_streamed.return_value = mock_result
        
        # Mock stream that yields some chunks then fails
        async def mock_partial_stream():
            for chunk in chunks_before_error:
                yield chunk
            raise Exception("Partial stream failed")
        
        mock_helper.stream_text_from.return_value = mock_partial_stream()
        
        # Execute
        received_chunks = []
        try:
            async for chunk in chat.run(test_input):
                received_chunks.append(chunk)
        except Exception:
            pass
        
        # Verify partial response was received
        assert received_chunks == chunks_before_error

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    @patch("kairix_engine.basic_chat.logger")
    async def test_run_memory_logging_during_stream(
        self, mock_logger, mock_helper, mock_runner, chat, mock_perceptor
    ):
        """Test that memory recovery logging works with streaming"""
        # Setup with memories
        mock_perception = Mock()
        mock_perception.content = "Streaming memory content"
        mock_perception.confidence = "0.88"
        mock_perception.source = "stream_memory_123"
        mock_perceptor.perceive = AsyncMock(return_value=[mock_perception])
        
        # Setup streaming
        chunks = ["Memory", " response"]
        full_response = "".join(chunks)
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = full_response
        mock_runner.run_streamed.return_value = mock_result
        
        async def mock_stream():
            for chunk in chunks:
                yield chunk
        
        mock_helper.stream_text_from.return_value = mock_stream()
        
        # Execute
        async for _ in chat.run("Remember something"):
            pass
        
        # Verify logging
        assert mock_logger.debug.called
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("[Memory Recovered]" in str(call) for call in debug_calls)
        assert any("stream_memory_123" in str(call) for call in debug_calls)

    @pytest.mark.asyncio
    @patch("kairix_engine.basic_chat.Runner")
    @patch("kairix_engine.basic_chat.VoiceWorkflowHelper")
    async def test_run_voice_workflow_integration(self, mock_helper, mock_runner, chat):
        """Test that run method properly integrates with VoiceWorkflowBase"""
        # This test verifies that Chat inherits from VoiceWorkflowBase properly
        # and implements the required run method for voice workflows
        
        # Setup
        test_transcription = "Voice input transcription"
        chunks = ["Voice", " response"]
        full_response = "".join(chunks)
        
        mock_result = Mock()
        mock_result.final_output_as.return_value = full_response
        mock_runner.run_streamed.return_value = mock_result
        
        async def mock_stream():
            for chunk in chunks:
                yield chunk
        
        mock_helper.stream_text_from.return_value = mock_stream()
        
        # Execute - using it as a voice workflow
        received_chunks = []
        async for chunk in chat.run(test_transcription):
            received_chunks.append(chunk)
        
        # Verify it works as a voice workflow
        assert received_chunks == chunks
        assert hasattr(chat, 'run')  # Required by VoiceWorkflowBase
        # Note: chat.run is an async generator, not a regular coroutine function
        import inspect
        assert inspect.isasyncgenfunction(chat.run)


class TestChatAsyncHelpers:
    """Test helper methods used in async context"""

    @pytest.mark.asyncio
    async def test_prepare_method(self, chat):
        """Test the _prepare method used by both chat and run"""
        # Execute
        result = await chat._prepare("Test message")
        
        # Verify
        assert "RECOLLECTIONS" in result
        assert "DIALOG" in result
        assert "Test message" in result
        assert len(chat.history) == 1
        assert chat.history[0].content == "Test message"

    def test_record_method(self, chat):
        """Test the _record method used to update history"""
        # Execute
        chat._record("Assistant response")
        
        # Verify
        assert len(chat.history) == 1
        assert chat.history[0].role == "assistant"
        assert chat.history[0].content == "Assistant response"
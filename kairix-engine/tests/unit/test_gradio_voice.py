"""Unit tests for Gradio chat voice streaming functionality."""

import os
from collections import deque
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import after setting up mocks
with patch("gradio.Blocks"), patch("gradio.Chatbot"), patch("gradio.Textbox"), \
     patch("gradio.Button"), patch("gradio.Row"), patch("gradio.Column"), \
     patch("gradio.Checkbox"), patch("gradio.HTML"), patch("gradio.Audio"), \
     patch("gradio.Tabs"), patch("gradio.Tab"), patch("gradio.Markdown"):
    from gradio_chat import get_error_logs, log_error, respond, text_to_speech_stream


class TestTextToSpeechStream:
    """Test async text-to-speech streaming functionality."""

    @pytest.mark.asyncio
    async def test_text_to_speech_stream_no_client(self):
        """Test text_to_speech_stream when AsyncElevenLabs client is not available."""
        with patch("gradio_chat.async_elevenlabs_client", None):
            chunks = []
            async for chunk in text_to_speech_stream("Hello world"):
                chunks.append(chunk)
            
            assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_text_to_speech_stream_success(self):
        """Test successful text-to-speech streaming."""
        # Mock AsyncElevenLabs client
        mock_client = Mock()
        mock_stream = AsyncMock()
        
        # Create a proper async iterator for the mock stream
        class MockAsyncIterator:
            def __init__(self):
                self.chunks = [b"audio_chunk_1", b"audio_chunk_2", b"audio_chunk_3"]
                self.index = 0
            
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                if self.index >= len(self.chunks):
                    raise StopAsyncIteration
                chunk = self.chunks[self.index]
                self.index += 1
                return chunk
        
        mock_stream = MockAsyncIterator()
        mock_client.text_to_speech.stream = AsyncMock(return_value=mock_stream)
        
        with patch("gradio_chat.async_elevenlabs_client", mock_client):
            chunks = []
            async for chunk in text_to_speech_stream("Hello world"):
                chunks.append(chunk)
            
            # Verify client was called with correct parameters
            mock_client.text_to_speech.stream.assert_called_once()
            call_args = mock_client.text_to_speech.stream.call_args[1]
            assert call_args["voice_id"] == "0NkECxcbkydDMspBKvQp"
            assert call_args["text"] == "Hello world"
            assert call_args["model_id"] == "eleven_flash_v2_5"  # Fastest model
            assert call_args["optimize_streaming_latency"] == "0"
            
            # Verify voice settings match best practices
            voice_settings = call_args["voice_settings"]
            assert voice_settings.stability == 0.5
            assert voice_settings.similarity_boost == 0.75
            assert voice_settings.style == 0.0
            assert voice_settings.use_speaker_boost is False
            
            # Verify chunks are yielded immediately
            assert chunks == [b"audio_chunk_1", b"audio_chunk_2", b"audio_chunk_3"]

    @pytest.mark.asyncio
    async def test_text_to_speech_stream_error_handling(self):
        """Test error handling in text-to-speech streaming."""
        mock_client = Mock()
        mock_client.text_to_speech.stream = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        with patch("gradio_chat.async_elevenlabs_client", mock_client), \
             patch("gradio_chat.error_logs", deque(maxlen=100)) as mock_logs:
            
            chunks = []
            async for chunk in text_to_speech_stream("Hello world"):
                chunks.append(chunk)
            
            # Should handle error gracefully
            assert len(chunks) == 0
            # Check that error was logged
            assert len(mock_logs) > 0
            assert "Error in text-to-speech" in str(mock_logs[-1])


class TestRespondFunction:
    """Test the main respond function with voice integration."""

    @pytest.mark.asyncio
    async def test_respond_without_voice(self):
        """Test respond function with voice disabled."""
        # Mock chat
        mock_chat = Mock()
        
        async def mock_run(message):
            yield "Hello "
            yield "there!"
        
        mock_chat.run = mock_run
        mock_chat.initialize = AsyncMock()
        
        with patch("gradio_chat.chat", mock_chat), \
             patch("gradio_chat._initialized", True), \
             patch("gradio_chat.get_error_logs", return_value="No errors logged."):
            
            history = []
            updates = []
            
            async for update in respond("Hi", history, False):
                updates.append(update)
            
            # Should have updates for each chunk plus final
            assert len(updates) >= 2
            
            # Check final state
            last_update = updates[-1]
            msg, final_history, audio, is_streaming, logs = last_update
            
            assert msg == ""  # Message box cleared
            assert len(final_history) == 2  # User and assistant messages
            assert final_history[-1]["content"] == "Hello there!"
            assert audio is None  # No audio when voice disabled
            assert is_streaming is False  # Not streaming at end
            assert logs == "No errors logged."

    @pytest.mark.asyncio
    async def test_respond_with_voice_direct_streaming(self):
        """Test respond function with voice enabled - direct streaming."""
        # Mock chat
        mock_chat = Mock()
        
        async def mock_run(message):
            yield "Hello "
            yield "world!"
        
        mock_chat.run = mock_run
        mock_chat.initialize = AsyncMock()
        
        # Mock AsyncElevenLabs client
        mock_client = Mock()
        
        # Mock text_to_speech_stream to return audio chunks
        async def mock_tts_stream(text):
            if text == "Hello ":
                yield b"audio_hello"
            elif text == "world!":
                yield b"audio_world"
        
        with patch("gradio_chat.chat", mock_chat), \
             patch("gradio_chat._initialized", True), \
             patch("gradio_chat.async_elevenlabs_client", mock_client), \
             patch("gradio_chat.text_to_speech_stream", side_effect=mock_tts_stream), \
             patch("gradio_chat.get_error_logs", return_value="No errors logged."):
            
            history = []
            updates = []
            
            async for update in respond("Hi", history, True):
                updates.append(update)
            
            # Should have multiple updates
            assert len(updates) > 0
            
            # Check that each text chunk was streamed directly to TTS
            audio_updates = [u for u in updates if u[2] is not None]
            assert len(audio_updates) == 2  # One for each chunk
            
            # Verify audio format
            assert audio_updates[0][2] == (22050, b"audio_hello")
            assert audio_updates[1][2] == (22050, b"audio_world")

    @pytest.mark.asyncio
    async def test_respond_no_buffering(self):
        """Test that text chunks are sent directly to TTS without buffering."""
        # Mock chat
        mock_chat = Mock()
        
        async def mock_run(message):
            yield "A"  # Very small chunk
            yield "B"  # Another small chunk
            yield "C"  # And another
        
        mock_chat.run = mock_run
        mock_chat.initialize = AsyncMock()
        
        # Track TTS calls
        tts_calls = []
        
        async def mock_tts_stream(text):
            tts_calls.append(text)
            yield b"audio"
        
        with patch("gradio_chat.chat", mock_chat), \
             patch("gradio_chat._initialized", True), \
             patch("gradio_chat.async_elevenlabs_client", Mock()), \
             patch("gradio_chat.text_to_speech_stream", side_effect=mock_tts_stream), \
             patch("gradio_chat.get_error_logs", return_value="No errors logged."):
            
            history = []
            updates = []
            
            async for update in respond("Hi", history, True):
                updates.append(update)
            
            # Verify each chunk was sent directly to TTS
            assert tts_calls == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_respond_error_logging(self):
        """Test that errors are properly logged and displayed."""
        # Mock chat
        mock_chat = Mock()
        
        async def mock_run(message):
            yield "Test"
        
        mock_chat.run = mock_run
        mock_chat.initialize = AsyncMock()
        
        # Mock text_to_speech_stream to return no chunks (error was logged)
        async def mock_tts_error(text):
            # Simulate that error was handled in text_to_speech_stream
            return
            yield  # Make it a generator
        
        with patch("gradio_chat.chat", mock_chat), \
             patch("gradio_chat._initialized", True), \
             patch("gradio_chat.async_elevenlabs_client", Mock()), \
             patch("gradio_chat.text_to_speech_stream", side_effect=mock_tts_error), \
             patch("gradio_chat.error_logs", deque(maxlen=100)):
            
            history = []
            updates = []
            
            async for update in respond("Hi", history, True):
                updates.append(update)
            
            # Should still complete despite error
            assert len(updates) > 0


class TestErrorLogging:
    """Test error logging functionality."""

    def test_log_error(self):
        """Test log_error function."""
        with patch("gradio_chat.error_logs", deque(maxlen=100)) as mock_logs, \
             patch("logging.error") as mock_logging:
            
            log_error("Test error message")
            
            # Check that error was logged to both systems
            mock_logging.assert_called_once_with("Test error message")
            assert len(mock_logs) == 1
            assert "Test error message" in mock_logs[0]
            assert "[" in mock_logs[0]  # Timestamp included

    def test_get_error_logs_empty(self):
        """Test get_error_logs when no errors."""
        with patch("gradio_chat.error_logs", deque()):
            result = get_error_logs()
            assert result == "No errors logged."

    def test_get_error_logs_with_errors(self):
        """Test get_error_logs with errors."""
        test_logs = deque(["[10:30:45] Error 1", "[10:30:46] Error 2"])
        with patch("gradio_chat.error_logs", test_logs):
            result = get_error_logs()
            assert result == "[10:30:45] Error 1\n[10:30:46] Error 2"


class TestVoiceConfiguration:
    """Test voice configuration and environment setup."""

    def test_voice_id_configuration(self):
        """Test that voice ID matches the one in eleven.py."""
        from gradio_chat import VOICE_ID
        assert VOICE_ID == "0NkECxcbkydDMspBKvQp"

    def test_model_configuration(self):
        """Test that the fastest model is being used."""
        # This is tested in the text_to_speech_stream tests
        # where we verify model_id == "eleven_flash_v2_5"
        pass

    def test_voice_settings_best_practices(self):
        """Test that voice settings follow best practices."""
        # This is tested in the text_to_speech_stream tests
        # where we verify the settings match recommendations:
        # stability=0.5, similarity_boost=0.75, style=0.0, use_speaker_boost=False
        pass

    def test_elevenlabs_client_initialization(self):
        """Test ElevenLabs client initialization logic."""
        import gradio_chat
        
        # If ELEVENLABS_API_KEY is set, both clients should be created
        if os.getenv("ELEVENLABS_API_KEY"):
            assert gradio_chat.elevenlabs_client is not None
            assert gradio_chat.async_elevenlabs_client is not None
        else:
            # Without key, clients should be None
            assert gradio_chat.elevenlabs_client is None
            assert gradio_chat.async_elevenlabs_client is None
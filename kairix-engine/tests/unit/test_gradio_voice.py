"""Unit tests for Gradio chat voice streaming functionality."""

import os
from unittest.mock import Mock, patch

import pytest

# Import after setting up mocks
with patch("gradio.Blocks"), patch("gradio.Chatbot"), patch("gradio.Textbox"), \
     patch("gradio.Button"), patch("gradio.Row"), patch("gradio.Column"), \
     patch("gradio.Checkbox"), patch("gradio.HTML"), patch("gradio.Audio"):
    from gradio_chat import respond, text_to_speech


class TestTextToSpeech:
    """Test text-to-speech functionality."""

    def test_text_to_speech_no_client(self):
        """Test text_to_speech when ElevenLabs client is not available."""
        with patch("gradio_chat.elevenlabs_client", None):
            result = text_to_speech("Hello world")
            assert result is None

    def test_text_to_speech_success(self):
        """Test successful text-to-speech conversion."""
        # Mock ElevenLabs client
        mock_client = Mock()
        mock_response = [b"audio_chunk_1", b"audio_chunk_2", b"audio_chunk_3"]
        mock_client.text_to_speech.convert.return_value = mock_response
        
        with patch("gradio_chat.elevenlabs_client", mock_client):
            result = text_to_speech("Hello world")
            
            # Verify client was called with correct parameters
            mock_client.text_to_speech.convert.assert_called_once()
            call_args = mock_client.text_to_speech.convert.call_args[1]
            assert call_args["voice_id"] == "0NkECxcbkydDMspBKvQp"
            assert call_args["text"] == "Hello world"
            assert call_args["optimize_streaming_latency"] == "0"
            
            # Verify audio data is concatenated
            expected = b"audio_chunk_1audio_chunk_2audio_chunk_3"
            assert result == expected

    def test_text_to_speech_error_handling(self):
        """Test error handling in text-to-speech conversion."""
        mock_client = Mock()
        mock_client.text_to_speech.convert.side_effect = Exception("API Error")
        
        with patch("gradio_chat.elevenlabs_client", mock_client), \
             patch("logging.error") as mock_log:
            
            result = text_to_speech("Hello world")
            
            # Should handle error gracefully
            assert result is None
            mock_log.assert_called_once()
            assert "Error in text-to-speech" in str(mock_log.call_args)


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
        mock_chat.initialize = Mock()
        
        with patch("gradio_chat.chat", mock_chat), \
             patch("gradio_chat._initialized", True):
            
            history = []
            updates = []
            
            async for update in respond("Hi", history, False):
                updates.append(update)
            
            # Should have updates for each chunk
            assert len(updates) >= 2
            
            # Check final state
            last_update = updates[-1]
            msg, final_history, audio, is_streaming = last_update
            
            assert msg == ""  # Message box cleared
            assert len(final_history) == 2  # User and assistant messages
            assert final_history[-1]["content"] == "Hello there!"
            assert audio is None  # No audio when voice disabled
            assert is_streaming is False  # Not streaming at end

    @pytest.mark.asyncio
    async def test_respond_with_voice(self):
        """Test respond function with voice enabled."""
        # Mock chat
        mock_chat = Mock()
        
        async def mock_run(message):
            yield "Hello. "
            yield "How are you?"
        
        mock_chat.run = mock_run
        mock_chat.initialize = Mock()
        
        # Mock ElevenLabs client
        mock_client = Mock()
        mock_audio_data = b"fake_audio_data"
        
        with patch("gradio_chat.chat", mock_chat), \
             patch("gradio_chat._initialized", True), \
             patch("gradio_chat.elevenlabs_client", mock_client), \
             patch("gradio_chat.text_to_speech", return_value=mock_audio_data):
            
            history = []
            updates = []
            
            async for update in respond("Hi", history, True):
                updates.append(update)
            
            # Should have multiple updates
            assert len(updates) > 0
            
            # Check for audio data in updates
            has_audio = False
            for update in updates:
                if update[2] is not None and update[2] != (None, None):
                    has_audio = True
                    # Check audio format (sample_rate, data)
                    assert update[2][0] == 44100
                    assert update[2][1] == mock_audio_data
            
            assert has_audio, "Should have audio data in updates"

    @pytest.mark.asyncio
    async def test_respond_sentence_buffering(self):
        """Test that sentences are buffered correctly for TTS."""
        # Mock chat
        mock_chat = Mock()
        
        async def mock_run(message):
            yield "This is "
            yield "the first sentence. "
            yield "And this "
            yield "is the second!"
        
        mock_chat.run = mock_run
        mock_chat.initialize = Mock()
        
        # Track TTS calls
        tts_calls = []
        
        def mock_tts(text):
            tts_calls.append(text)
            return b"audio"
        
        with patch("gradio_chat.chat", mock_chat), \
             patch("gradio_chat._initialized", True), \
             patch("gradio_chat.elevenlabs_client", Mock()), \
             patch("gradio_chat.text_to_speech", side_effect=mock_tts):
            
            history = []
            updates = []
            
            async for update in respond("Hi", history, True):
                updates.append(update)
            
            # Check that sentences were processed correctly
            assert len(tts_calls) >= 2
            assert "This is the first sentence." in tts_calls[0]
            assert "And this is the second!" in tts_calls[-1]


class TestVoiceConfiguration:
    """Test voice configuration and environment setup."""

    def test_voice_id_configuration(self):
        """Test that voice ID matches the one in eleven.py."""
        from gradio_chat import VOICE_ID
        assert VOICE_ID == "0NkECxcbkydDMspBKvQp"

    def test_elevenlabs_client_initialization(self):
        """Test ElevenLabs client initialization logic."""
        import gradio_chat
        
        # If ELEVENLABS_API_KEY is set, client should be created
        if os.getenv("ELEVENLABS_API_KEY"):
            assert gradio_chat.elevenlabs_client is not None
        else:
            # Without key, client should be None
            assert gradio_chat.elevenlabs_client is None
import io
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest
from pydub import AudioSegment

from cognition_engine.tts.elevenlabs_tts import ElevenLabsTTS


class TestElevenLabsTTS:
    """Test suite for ElevenLabsTTS class."""

    @pytest.fixture
    def mock_api_key(self):
        return "test-api-key-123"

    @pytest.fixture
    def tts_instance(self, mock_api_key):
        return ElevenLabsTTS(api_key=mock_api_key)

    @pytest.fixture
    def sample_audio_bytes(self):
        """Create sample MP3 audio bytes for testing."""
        # Create a simple audio segment
        sample_rate = 16000
        samples = np.sin(2 * np.pi * 440 * np.arange(sample_rate) / sample_rate)
        audio = AudioSegment(
            samples.tobytes(),
            frame_rate=sample_rate,
            sample_width=2,
            channels=1,
        )
        buffer = io.BytesIO()
        audio.export(buffer, format="mp3")
        return buffer.getvalue()

    def test_initialization_with_defaults(self, mock_api_key):
        """Test ElevenLabsTTS initialization with default parameters."""
        tts = ElevenLabsTTS(api_key=mock_api_key)
        assert tts.voice_id == "21m00Tcm4TlvDq8ikWAM"
        assert tts.model_id == "eleven_monolingual_v1"
        assert tts.voice_settings.stability == 0.5
        assert tts.voice_settings.similarity_boost == 0.5
        assert tts.voice_settings.style == 0.5
        assert tts.voice_settings.use_speaker_boost is True
        assert tts.sample_rate == 16000

    def test_initialization_with_custom_params(self, mock_api_key):
        """Test ElevenLabsTTS initialization with custom parameters."""
        tts = ElevenLabsTTS(
            api_key=mock_api_key,
            voice_id="custom-voice-id",
            model_id="eleven_turbo_v2",
            stability=0.7,
            similarity_boost=0.8,
            style=0.6,
            use_speaker_boost=False,
            sample_rate=22050,
        )
        assert tts.voice_id == "custom-voice-id"
        assert tts.model_id == "eleven_turbo_v2"
        assert tts.voice_settings.stability == 0.7
        assert tts.voice_settings.similarity_boost == 0.8
        assert tts.voice_settings.style == 0.6
        assert tts.voice_settings.use_speaker_boost is False
        assert tts.sample_rate == 22050

    def test_convert_audio_format(self, tts_instance, sample_audio_bytes):
        """Test audio format conversion from MP3 bytes to numpy array."""
        result = tts_instance._convert_audio_format(sample_audio_bytes)

        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32
        assert result.ndim == 1  # Should be 1D array
        assert -1.0 <= result.min() <= result.max() <= 1.0  # Normalized range

    def test_convert_audio_format_stereo_to_mono(self, tts_instance):
        """Test conversion of stereo audio to mono."""
        # Create stereo audio
        sample_rate = 16000
        samples = np.sin(2 * np.pi * 440 * np.arange(sample_rate // 2) / sample_rate)
        stereo_audio = AudioSegment(
            samples.tobytes(),
            frame_rate=sample_rate,
            sample_width=2,
            channels=2,  # Stereo
        )
        buffer = io.BytesIO()
        stereo_audio.export(buffer, format="mp3")

        result = tts_instance._convert_audio_format(buffer.getvalue())
        assert isinstance(result, np.ndarray)
        assert result.ndim == 1  # Should be mono

    @patch("cognition_engine.tts.elevenlabs_tts.ElevenLabs")
    def test_tts_sync(self, mock_elevenlabs_class, tts_instance, sample_audio_bytes):
        """Test synchronous TTS generation."""
        mock_client = Mock()
        mock_elevenlabs_class.return_value = mock_client
        # Properly mock the text_to_speech attribute
        mock_text_to_speech = Mock()
        # Mock to return an iterator of bytes (like the real API)
        mock_text_to_speech.convert = Mock(return_value=iter([sample_audio_bytes]))
        mock_client.text_to_speech = mock_text_to_speech

        # Reinitialize to use mocked client
        tts_instance.client = mock_client

        sample_rate, audio_array = tts_instance.tts("Hello, world!")

        assert sample_rate == 16000
        assert isinstance(audio_array, np.ndarray)
        assert audio_array.dtype == np.float32
        mock_client.text_to_speech.convert.assert_called_once()

    @patch("cognition_engine.tts.elevenlabs_tts.ElevenLabs")
    def test_tts_sync_with_custom_voice(
        self, mock_elevenlabs_class, tts_instance, sample_audio_bytes
    ):
        """Test synchronous TTS with custom voice ID."""
        mock_client = Mock()
        mock_elevenlabs_class.return_value = mock_client
        # Properly mock the text_to_speech attribute
        mock_text_to_speech = Mock()
        # Mock to return an iterator of bytes (like the real API)
        mock_text_to_speech.convert = Mock(return_value=iter([sample_audio_bytes]))
        mock_client.text_to_speech = mock_text_to_speech

        tts_instance.client = mock_client

        sample_rate, audio_array = tts_instance.tts(
            "Hello, world!", voice_id="custom-voice"
        )

        assert sample_rate == 16000
        call_args = mock_client.text_to_speech.convert.call_args
        assert call_args[1]["voice_id"] == "custom-voice"

    @patch("cognition_engine.tts.elevenlabs_tts.ElevenLabs")
    def test_stream_tts_sync(
        self, mock_elevenlabs_class, tts_instance, sample_audio_bytes
    ):
        """Test synchronous streaming TTS."""
        mock_client = Mock()
        mock_elevenlabs_class.return_value = mock_client

        # Properly mock the text_to_speech attribute
        mock_text_to_speech = Mock()
        mock_text_to_speech.stream = Mock()
        mock_client.text_to_speech = mock_text_to_speech

        # Simulate streaming chunks
        chunk_size = len(sample_audio_bytes) // 3
        chunks = [
            sample_audio_bytes[i : i + chunk_size]
            for i in range(0, len(sample_audio_bytes), chunk_size)
        ]
        mock_text_to_speech.stream.return_value = iter(chunks)

        tts_instance.client = mock_client

        results = list(tts_instance.stream_tts_sync("Hello, streaming!"))

        assert len(results) > 0
        for sample_rate, audio_chunk in results:
            assert sample_rate == 16000
            assert isinstance(audio_chunk, np.ndarray)
            assert audio_chunk.dtype == np.float32

    @patch("cognition_engine.tts.elevenlabs_tts.ElevenLabs")
    def test_stream_tts_sync_error_handling(self, mock_elevenlabs_class, tts_instance):
        """Test error handling in synchronous streaming."""
        mock_client = Mock()
        mock_elevenlabs_class.return_value = mock_client
        # Properly mock the text_to_speech attribute
        mock_text_to_speech = Mock()
        mock_text_to_speech.stream = Mock(side_effect=Exception("API Error"))
        mock_client.text_to_speech = mock_text_to_speech

        tts_instance.client = mock_client

        with pytest.raises(Exception, match="API Error"):
            list(tts_instance.stream_tts_sync("Test"))

    @pytest.mark.asyncio
    @patch("cognition_engine.tts.elevenlabs_tts.AsyncElevenLabs")
    async def test_atts_async(
        self, mock_async_elevenlabs_class, tts_instance, sample_audio_bytes
    ):
        """Test asynchronous TTS generation."""
        mock_async_client = AsyncMock()
        mock_async_elevenlabs_class.return_value = mock_async_client
        # Properly mock the text_to_speech attribute
        mock_async_text_to_speech = Mock()

        # Mock to return an async iterator
        async def async_iterator():
            yield sample_audio_bytes

        mock_async_text_to_speech.convert = Mock(return_value=async_iterator())
        mock_async_client.text_to_speech = mock_async_text_to_speech

        tts_instance.async_client = mock_async_client

        sample_rate, audio_array = await tts_instance.atts("Hello, async world!")

        assert sample_rate == 16000
        assert isinstance(audio_array, np.ndarray)
        assert audio_array.dtype == np.float32
        mock_async_client.text_to_speech.convert.assert_called_once()

    @pytest.mark.asyncio
    @patch("cognition_engine.tts.elevenlabs_tts.AsyncElevenLabs")
    async def test_stream_tts_async(
        self, mock_async_elevenlabs_class, tts_instance, sample_audio_bytes
    ):
        """Test asynchronous streaming TTS."""
        mock_async_client = AsyncMock()
        mock_async_elevenlabs_class.return_value = mock_async_client

        # Simulate async streaming chunks
        chunk_size = len(sample_audio_bytes) // 3
        chunks = [
            sample_audio_bytes[i : i + chunk_size]
            for i in range(0, len(sample_audio_bytes), chunk_size)
        ]

        async def async_generator():
            for chunk in chunks:
                yield chunk

        # Properly mock the text_to_speech attribute
        mock_async_text_to_speech = Mock()
        # Mock to return the async generator directly (not a coroutine)
        mock_async_text_to_speech.stream = Mock(return_value=async_generator())
        mock_async_client.text_to_speech = mock_async_text_to_speech
        tts_instance.async_client = mock_async_client

        results = []
        async for sample_rate, audio_chunk in tts_instance.stream_tts(
            "Hello, async streaming!"
        ):
            results.append((sample_rate, audio_chunk))

        assert len(results) > 0
        for sample_rate, audio_chunk in results:
            assert sample_rate == 16000
            assert isinstance(audio_chunk, np.ndarray)
            assert audio_chunk.dtype == np.float32

    @pytest.mark.asyncio
    @patch("cognition_engine.tts.elevenlabs_tts.AsyncElevenLabs")
    async def test_stream_tts_async_error_handling(
        self, mock_async_elevenlabs_class, tts_instance
    ):
        """Test error handling in asynchronous streaming."""
        mock_async_client = AsyncMock()
        mock_async_elevenlabs_class.return_value = mock_async_client
        # Properly mock the text_to_speech attribute
        mock_async_text_to_speech = Mock()
        # Mock to raise an exception when called
        mock_async_text_to_speech.stream = Mock(
            side_effect=Exception("Async API Error")
        )
        mock_async_client.text_to_speech = mock_async_text_to_speech

        tts_instance.async_client = mock_async_client

        with pytest.raises(Exception, match="Async API Error"):
            async for _ in tts_instance.stream_tts("Test"):
                pass

    def test_empty_audio_handling(self, tts_instance):
        """Test handling of empty audio data."""
        # Create a very short silent audio instead of completely empty
        # because ffmpeg can't handle truly empty MP3 files
        sample_rate = 16000
        duration_ms = 10  # 10ms of silence
        int(sample_rate * duration_ms / 1000)
        silent_audio = AudioSegment.silent(duration=duration_ms, frame_rate=sample_rate)

        buffer = io.BytesIO()
        silent_audio.export(buffer, format="mp3")

        result = tts_instance._convert_audio_format(buffer.getvalue())
        assert isinstance(result, np.ndarray)
        assert len(result) > 0  # Should have some samples
        assert np.allclose(result, 0, atol=1e-3)  # Should be mostly silence

    @patch("cognition_engine.tts.elevenlabs_tts.ElevenLabs")
    def test_stream_with_small_chunks(
        self, mock_elevenlabs_class, tts_instance, sample_audio_bytes
    ):
        """Test streaming with very small chunks to test buffering logic."""
        mock_client = Mock()
        mock_elevenlabs_class.return_value = mock_client

        # Create many small chunks
        chunk_size = 100  # Very small chunks
        chunks = [
            sample_audio_bytes[i : i + chunk_size]
            for i in range(0, len(sample_audio_bytes), chunk_size)
        ]
        # Properly mock the text_to_speech attribute
        mock_text_to_speech = Mock()
        mock_text_to_speech.stream = Mock(return_value=iter(chunks))
        mock_client.text_to_speech = mock_text_to_speech

        tts_instance.client = mock_client

        results = list(tts_instance.stream_tts_sync("Test small chunks"))

        # Should still produce valid output
        assert len(results) > 0
        for sample_rate, audio_chunk in results:
            assert sample_rate == 16000
            assert isinstance(audio_chunk, np.ndarray)

    @patch("cognition_engine.tts.elevenlabs_tts.logger")
    @patch("cognition_engine.tts.elevenlabs_tts.ElevenLabs")
    def test_chunk_conversion_error_handling(
        self, mock_elevenlabs_class, mock_logger, tts_instance
    ):
        """Test handling of chunk conversion errors during streaming."""
        mock_client = Mock()
        mock_elevenlabs_class.return_value = mock_client

        # Create invalid audio data that will fail conversion
        invalid_chunk = b"invalid audio data"
        valid_chunk = b"valid chunk"  # This would need to be real audio data

        # Mock the conversion to fail on invalid data
        original_convert = tts_instance._convert_audio_format

        def mock_convert(data):
            if data == invalid_chunk:
                raise ValueError("Invalid audio format")
            return original_convert(data)

        tts_instance._convert_audio_format = mock_convert
        # Properly mock the text_to_speech attribute
        mock_text_to_speech = Mock()
        mock_text_to_speech.stream = Mock(
            return_value=iter([invalid_chunk, valid_chunk])
        )
        mock_client.text_to_speech = mock_text_to_speech
        tts_instance.client = mock_client

        # Should skip invalid chunks and log warnings
        list(tts_instance.stream_tts_sync("Test"))

        # Check that warning was logged
        mock_logger.warning.assert_called()

    def test_different_sample_rates(self, mock_api_key):
        """Test TTS with different sample rates."""
        for sample_rate in [8000, 16000, 22050, 44100, 48000]:
            tts = ElevenLabsTTS(api_key=mock_api_key, sample_rate=sample_rate)
            assert tts.sample_rate == sample_rate

    def test_voice_settings_boundaries(self, mock_api_key):
        """Test voice settings with boundary values."""
        # Test minimum values
        tts_min = ElevenLabsTTS(
            api_key=mock_api_key,
            stability=0.0,
            similarity_boost=0.0,
            style=0.0,
        )
        assert tts_min.voice_settings.stability == 0.0
        assert tts_min.voice_settings.similarity_boost == 0.0
        assert tts_min.voice_settings.style == 0.0

        # Test maximum values
        tts_max = ElevenLabsTTS(
            api_key=mock_api_key,
            stability=1.0,
            similarity_boost=1.0,
            style=1.0,
        )
        assert tts_max.voice_settings.stability == 1.0
        assert tts_max.voice_settings.similarity_boost == 1.0
        assert tts_max.voice_settings.style == 1.0

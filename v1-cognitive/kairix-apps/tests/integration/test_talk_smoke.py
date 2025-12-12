import os

import pytest
from dotenv import load_dotenv
from kairix_core.tts import ElevenLabsTTS

# Load environment variables
# Try to load from env/ directory if ENV is set
env_name = os.environ.get("ENV", "mac")
env_path = f"env/{env_name}.env"
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()  # Fallback to default .env


class TestTalkSmoke:
    """Quick smoke tests for ElevenLabs integration."""

    @pytest.fixture
    def api_key(self):
        """Get API key from environment."""
        key = os.environ.get("ELEVENLABS_API_KEY")
        if not key:
            pytest.skip("ELEVENLABS_API_KEY not set")
        assert isinstance(key, str)  # Type narrowing for type checker
        return key

    def test_tts_initialization(self, api_key):
        """Test that TTS can be initialized with API key."""
        tts = ElevenLabsTTS(api_key=api_key)
        assert tts is not None
        assert tts.voice_id == "0NkECxcbkydDMspBKvQp"  # Default voice

    def test_tts_simple_generation(self, api_key):
        """Test basic TTS generation with a short phrase."""
        tts = ElevenLabsTTS(api_key=api_key)

        # Generate audio for a simple phrase
        sample_rate, audio_array = tts.tts("Hello")

        # Verify output
        assert sample_rate == 16000
        assert audio_array is not None
        assert len(audio_array) > 0
        assert audio_array.dtype.name == "float32"
        assert -1.0 <= audio_array.min() <= audio_array.max() <= 1.0

    def test_tts_streaming(self, api_key):
        """Test streaming TTS generation."""
        tts = ElevenLabsTTS(api_key=api_key)

        # Generate streaming audio
        chunks = list(tts.stream_tts_sync("Test"))

        # Should produce at least one chunk
        assert len(chunks) > 0

        # Verify first chunk
        sample_rate, audio_chunk = chunks[0]
        assert sample_rate == 16000
        assert len(audio_chunk) > 0

    @pytest.mark.asyncio
    async def test_async_tts(self, api_key):
        """Test async TTS generation."""
        tts = ElevenLabsTTS(api_key=api_key)

        # Generate audio asynchronously
        sample_rate, audio_array = await tts.atts("Async test")

        # Verify output
        assert sample_rate == 16000
        assert audio_array is not None
        assert len(audio_array) > 0

    def test_voice_configuration(self, api_key):
        """Test TTS with different voice configurations."""
        # Test with custom settings
        tts = ElevenLabsTTS(
            api_key=api_key,
            voice_id="AZnzlk1XvdvUeBnXmlld",  # Domi voice
            stability=0.3,
            similarity_boost=0.9,
            style=0.2,
            use_speaker_boost=False,
        )

        # Should work with custom settings
        sample_rate, audio_array = tts.tts("Custom voice test")
        assert sample_rate == 16000
        assert len(audio_array) > 0

    def test_error_handling(self):
        """Test error handling with invalid API key."""
        tts = ElevenLabsTTS(api_key="invalid-key-12345")

        # Should raise an error with invalid key
        with pytest.raises(Exception):  # noqa: B017
            tts.tts("This should fail")

import os
import random
import time
from difflib import SequenceMatcher
from typing import ClassVar

import numpy as np
import pytest
from dotenv import load_dotenv
from elevenlabs import ElevenLabs
from fastrtc import get_stt_model
from Levenshtein import distance as levenshtein_distance
from pydub import AudioSegment

from kairix_engine.engine import KairixEngine
from kairix_engine.tts import ElevenLabsTTS

# Load environment variables
# Try to load from env/ directory if ENV is set
env_name = os.environ.get("ENV", "mac")
env_path = f"env/{env_name}.env"
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()  # Fallback to default .env


class TestTalkIntegration:
    """Integration tests for the talk.py audio pipeline."""

    # Test phrases with varying complexity
    TEST_PHRASES: ClassVar[list[str]] = [
        "Hello, how are you today?",
        "What is the weather like?",
        "Can you help me with a coding problem?",
        "Tell me about artificial intelligence.",
        "I need to schedule a meeting for tomorrow.",
    ]

    # Random English voices from ElevenLabs
    ENGLISH_VOICES: ClassVar[list[str]] = [
        "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "AZnzlk1XvdvUeBnXmlld",  # Domi
        "EXAVITQu4vr4xnSDxMaL",  # Bella
        "ErXwobaYiN019PkySvjV",  # Antoni
        "MF3mGyEYCl7XYWbV9V6O",  # Elli
        "TxGEqnHWrfWFTfGW9XjX",  # Josh
        "VR6AewLTigWG4xSOukaG",  # Arnold
        "pNInz6obpgDQGcFmaJgB",  # Adam
        "yoZ06aMxZJJ28mfd3POQ",  # Sam
    ]

    @pytest.fixture
    def elevenlabs_client(self):
        """Create ElevenLabs client."""
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            pytest.skip("ELEVENLABS_API_KEY not set")
        assert isinstance(api_key, str)  # Type narrowing for type checker
        return ElevenLabs(api_key=api_key)

    @pytest.fixture
    def tts_instance(self):
        """Create TTS instance with random voice."""
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            pytest.skip("ELEVENLABS_API_KEY not set")
        
        assert isinstance(api_key, str)  # Type narrowing for type checker
        random_voice = random.choice(self.ENGLISH_VOICES)
        return ElevenLabsTTS(
            api_key=api_key,
            voice_id=random_voice,
            model_id="eleven_monolingual_v1",
            stability=0.5,
            similarity_boost=0.75,  # Higher for better clarity
            style=0.0,  # Lower for clearer pronunciation
            use_speaker_boost=True,
        )

    @pytest.fixture
    def stt_model(self):
        """Get STT model."""
        return get_stt_model()

    @pytest.fixture
    async def chat_instance(self):
        """Create chat instance."""
        chat = KairixEngine.get_chat_for_environment()
        await chat.initialize()
        return chat

    def calculate_similarity(self, text1: str, text2: str) -> dict:
        """Calculate various similarity metrics between two texts.
        
        Returns dict with:
        - levenshtein: Edit distance
        - normalized_levenshtein: Edit distance normalized by max length
        - sequence_similarity: Ratio of matching subsequences
        - word_accuracy: Percentage of matching words
        """
        # Normalize texts for comparison
        text1_norm = text1.lower().strip()
        text2_norm = text2.lower().strip()
        
        # Levenshtein distance
        lev_dist = levenshtein_distance(text1_norm, text2_norm)
        max_len = max(len(text1_norm), len(text2_norm))
        normalized_lev = lev_dist / max_len if max_len > 0 else 0
        
        # Sequence similarity
        seq_similarity = SequenceMatcher(None, text1_norm, text2_norm).ratio()
        
        # Word-level accuracy
        words1 = text1_norm.split()
        words2 = text2_norm.split()
        matching_words = sum(
            1 for w1, w2 in zip(words1, words2, strict=False) if w1 == w2
        )
        max_words = max(len(words1), len(words2))
        word_accuracy = matching_words / max_words if max_words > 0 else 0
        
        return {
            "levenshtein": lev_dist,
            "normalized_levenshtein": normalized_lev,
            "sequence_similarity": seq_similarity,
            "word_accuracy": word_accuracy,
        }

    def audio_to_numpy(
        self, audio_segment: AudioSegment, sample_rate: int = 16000
    ) -> np.ndarray:
        """Convert AudioSegment to numpy array."""
        # Ensure mono
        if audio_segment.channels > 1:
            audio_segment = audio_segment.set_channels(1)
        
        # Resample
        audio_segment = audio_segment.set_frame_rate(sample_rate)
        
        # Convert to numpy
        samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
        samples = samples / (2**15)  # Normalize to [-1, 1]
        
        return samples

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_phrase", TEST_PHRASES)
    async def test_tts_to_stt_accuracy(
        self, tts_instance, stt_model, test_phrase, tmp_path
    ):
        """Test TTS->STT accuracy without the chat component."""
        print(f"\nTesting phrase: '{test_phrase}'")
        print(f"Using voice: {tts_instance.voice_id}")
        
        # Generate audio from text using TTS
        sample_rate, audio_array = tts_instance.tts(test_phrase)
        
        # Convert numpy array back to AudioSegment for STT
        audio_segment = AudioSegment(
            (audio_array * 32767).astype(np.int16).tobytes(),
            frame_rate=sample_rate,
            sample_width=2,
            channels=1,
        )
        
        # Save for debugging if needed
        debug_path = tmp_path / f"test_audio_{int(time.time())}.wav"
        audio_segment.export(debug_path, format="wav")
        print(f"Debug audio saved to: {debug_path}")
        
        # Run STT on the generated audio
        transcribed_text = stt_model.stt((sample_rate, audio_array))
        
        print(f"Original: '{test_phrase}'")
        print(f"Transcribed: '{transcribed_text}'")
        
        # Calculate similarity metrics
        similarity = self.calculate_similarity(test_phrase, transcribed_text)
        print(f"Similarity metrics: {similarity}")
        
        # Assert thresholds
        assert similarity["normalized_levenshtein"] < 0.3, (
            f"Normalized edit distance too high: {similarity['normalized_levenshtein']}"
        )
        assert similarity["sequence_similarity"] > 0.7, (
            f"Sequence similarity too low: {similarity['sequence_similarity']}"
        )
        assert similarity["word_accuracy"] > 0.6, (
            f"Word accuracy too low: {similarity['word_accuracy']}"
        )

    @pytest.mark.asyncio
    async def test_full_conversation_loop(
        self, tts_instance, stt_model, chat_instance, tmp_path
    ):
        """Test full conversation loop: TTS -> STT -> Chat -> Response."""
        test_phrase = "What is two plus two?"
        expected_keywords = ["four", "4"]
        
        print(f"\nTesting full conversation loop with: '{test_phrase}'")
        print(f"Using voice: {tts_instance.voice_id}")
        
        # Step 1: Generate audio from test phrase
        sample_rate, audio_array = tts_instance.tts(test_phrase)
        
        # Step 2: Run STT to get transcription
        transcribed_text = stt_model.stt((sample_rate, audio_array))
        print(f"STT transcribed: '{transcribed_text}'")
        
        # Step 3: Send to chat and get response
        chat_response = await chat_instance.chat(transcribed_text)
        print(f"Chat response: '{chat_response}'")
        
        # Step 4: Verify response contains expected content
        response_lower = chat_response.lower()
        assert any(keyword in response_lower for keyword in expected_keywords), (
            f"Expected keywords {expected_keywords} not found in response: "
            f"'{chat_response}'"
        )
        
        # Step 5: Generate audio from response (to verify TTS works with response)
        # Limit response length for audio generation
        response_sample_rate, response_audio = tts_instance.tts(
            chat_response[:100]
        )
        assert response_audio is not None
        assert len(response_audio) > 0

    @pytest.mark.asyncio
    async def test_voice_consistency(self, elevenlabs_client):
        """Test that different voices produce different audio characteristics."""
        test_phrase = "This is a voice consistency test."
        
        # Test with two different voices
        voice1 = self.ENGLISH_VOICES[0]
        voice2 = self.ENGLISH_VOICES[1]
        
        tts1 = ElevenLabsTTS(
            api_key=elevenlabs_client.api_key,
            voice_id=voice1,
        )
        tts2 = ElevenLabsTTS(
            api_key=elevenlabs_client.api_key,
            voice_id=voice2,
        )
        
        # Generate audio with both voices
        _, audio1 = tts1.tts(test_phrase)
        _, audio2 = tts2.tts(test_phrase)
        
        # Audio should be different
        assert not np.array_equal(audio1, audio2), (
            "Different voices produced identical audio"
        )
        
        # But both should have content
        assert len(audio1) > 0
        assert len(audio2) > 0

    @pytest.mark.asyncio
    async def test_streaming_accuracy(self, tts_instance, stt_model):
        """Test streaming TTS accuracy."""
        test_phrase = "Streaming test with multiple words."
        
        # Collect streamed audio chunks
        audio_chunks = []
        sample_rate = None
        for sr, chunk in tts_instance.stream_tts_sync(test_phrase):
            if sample_rate is None:
                sample_rate = sr
            audio_chunks.append(chunk)
        
        # Concatenate chunks
        full_audio = np.concatenate(audio_chunks)
        
        # Run STT on concatenated audio
        transcribed_text = stt_model.stt((sample_rate, full_audio))
        
        print(f"Original: '{test_phrase}'")
        print(f"Transcribed from stream: '{transcribed_text}'")
        
        # Calculate similarity
        similarity = self.calculate_similarity(test_phrase, transcribed_text)
        print(f"Streaming similarity: {similarity}")
        
        # Should maintain good accuracy
        assert similarity["sequence_similarity"] > 0.7

    @pytest.mark.asyncio
    async def test_edge_cases(self, tts_instance, stt_model):
        """Test edge cases like empty strings, special characters, etc."""
        edge_cases = [
            "",  # Empty string
            "123",  # Numbers only
            "Hello!!!",  # Punctuation
            "a",  # Single character
            "Café résumé naïve",  # Accented characters
        ]
        
        for test_case in edge_cases:
            if not test_case:  # Skip empty string for STT
                continue
                
            print(f"\nTesting edge case: '{test_case}'")
            
            try:
                # Generate audio
                sample_rate, audio_array = tts_instance.tts(test_case)
                
                # Should produce some audio
                assert len(audio_array) > 0
                
                # Try STT (may not be perfect for edge cases)
                transcribed = stt_model.stt((sample_rate, audio_array))
                print(f"Transcribed: '{transcribed}'")
                
            except Exception as e:
                pytest.fail(f"Failed on edge case '{test_case}': {e}")

    @pytest.mark.asyncio
    async def test_multilingual_robustness(self, tts_instance, stt_model):
        """Test system robustness with non-English input (should handle gracefully)."""
        # These should work but may have lower accuracy
        test_phrases = [
            "Hello world",  # English baseline
            "Bonjour monde",  # French
            "Hola mundo",  # Spanish
        ]
        
        for phrase in test_phrases:
            print(f"\nTesting phrase: '{phrase}'")
            
            try:
                # Generate audio
                sample_rate, audio_array = tts_instance.tts(phrase)
                
                # Should produce audio regardless
                assert len(audio_array) > 0
                
                # STT (English model may struggle with non-English)
                transcribed = stt_model.stt((sample_rate, audio_array))
                print(f"Transcribed: '{transcribed}'")
                
                # For English, should be accurate
                if phrase == "Hello world":
                    similarity = self.calculate_similarity(phrase, transcribed)
                    assert similarity["sequence_similarity"] > 0.8
                
            except Exception as e:
                pytest.fail(f"System failed on '{phrase}': {e}")

    def test_configuration_from_environment(self):
        """Test that TTS can be configured from environment variables."""
        # Set test environment variables
        test_env = {
            "ELEVENLABS_API_KEY": "test-key",
            "ELEVENLABS_VOICE_ID": "test-voice",
            "ELEVENLABS_MODEL_ID": "eleven_turbo_v2",
            "ELEVENLABS_STABILITY": "0.7",
            "ELEVENLABS_SIMILARITY_BOOST": "0.8",
            "ELEVENLABS_STYLE": "0.6",
            "ELEVENLABS_USE_SPEAKER_BOOST": "false",
        }
        
        # Temporarily set environment
        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            # Create TTS with environment config
            tts = ElevenLabsTTS(
                api_key=os.environ["ELEVENLABS_API_KEY"],
                voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "default"),
                model_id=os.environ.get("ELEVENLABS_MODEL_ID", "eleven_monolingual_v1"),
                stability=float(os.environ.get("ELEVENLABS_STABILITY", "0.5")),
                similarity_boost=float(
                    os.environ.get("ELEVENLABS_SIMILARITY_BOOST", "0.5")
                ),
                style=float(os.environ.get("ELEVENLABS_STYLE", "0.5")),
                use_speaker_boost=(
                    os.environ.get("ELEVENLABS_USE_SPEAKER_BOOST", "true").lower()
                    == "true"
                ),
            )
            
            # Verify configuration
            assert tts.voice_id == "test-voice"
            assert tts.model_id == "eleven_turbo_v2"
            assert tts.voice_settings.stability == 0.7
            assert tts.voice_settings.similarity_boost == 0.8
            assert tts.voice_settings.style == 0.6
            assert tts.voice_settings.use_speaker_boost is False
            
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
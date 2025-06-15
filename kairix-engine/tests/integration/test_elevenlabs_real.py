"""Integration test for ElevenLabs API with real streaming."""

import os
from pathlib import Path

import pytest
from elevenlabs import VoiceSettings
from elevenlabs.client import AsyncElevenLabs
from pydub import AudioSegment


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ELEVENLABS_API_KEY"),
    reason="ELEVENLABS_API_KEY not set"
)
class TestElevenLabsRealAPI:
    """Test real ElevenLabs API streaming functionality."""
    
    @pytest.mark.asyncio
    async def test_stream_real_audio(self):
        """Test streaming real audio from ElevenLabs API."""
        # Initialize client
        api_key = os.getenv("ELEVENLABS_API_KEY")
        client = AsyncElevenLabs(api_key=api_key)
        
        # Test text
        test_text = (
            "Hello, this is a test of the ElevenLabs text to speech API. "
            "Testing streaming functionality."
        )
        
        # Voice settings
        voice_id = "0NkECxcbkydDMspBKvQp"  # From eleven.py
        
        # Collect audio chunks
        audio_chunks = []
        total_size = 0
        chunk_count = 0
        
        # Stream audio
        audio_stream = client.text_to_speech.stream(
            voice_id=voice_id,
            text=test_text,
            model_id="eleven_flash_v2_5",  # Fastest model
            optimize_streaming_latency=0,
            output_format="mp3_22050_32",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.0,
                use_speaker_boost=False,
            ),
        )
        
        async for chunk in audio_stream:
            if chunk:
                audio_chunks.append(chunk)
                total_size += len(chunk)
                chunk_count += 1
        
        # Verify we received audio data
        assert chunk_count > 0, "No audio chunks received"
        assert total_size > 1000, f"Audio size too small: {total_size} bytes"
        assert total_size < 1000000, f"Audio size too large: {total_size} bytes"
        
        # Combine chunks
        audio_data = b"".join(audio_chunks)
        
        # Save as MP3 first
        mp3_path = Path("data/test_output.mp3")
        mp3_path.parent.mkdir(exist_ok=True)
        mp3_path.write_bytes(audio_data)
        
        # Convert to WAV using pydub
        audio = AudioSegment.from_mp3(mp3_path)
        wav_path = Path("data/test_output.wav")
        audio.export(wav_path, format="wav")
        
        # Verify WAV file exists and has content
        assert wav_path.exists(), "WAV file was not created"
        wav_size = wav_path.stat().st_size
        assert wav_size > 1000, f"WAV file too small: {wav_size} bytes"
        
        # Clean up MP3
        mp3_path.unlink()
        
        print(f"✓ Successfully streamed {chunk_count} chunks")
        print(f"✓ Total audio size: {total_size:,} bytes")
        print(f"✓ WAV file saved to: {wav_path}")
        print(f"✓ WAV file size: {wav_size:,} bytes")
    
    @pytest.mark.asyncio
    async def test_stream_latency(self):
        """Test streaming latency by measuring time to first chunk."""
        import time
        
        api_key = os.getenv("ELEVENLABS_API_KEY")
        client = AsyncElevenLabs(api_key=api_key)
        
        test_text = "Quick test."
        voice_id = "0NkECxcbkydDMspBKvQp"
        
        start_time = time.time()
        first_chunk_time = None
        
        audio_stream = client.text_to_speech.stream(
            voice_id=voice_id,
            text=test_text,
            model_id="eleven_flash_v2_5",
            optimize_streaming_latency=0,
            output_format="mp3_22050_32",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.0,
                use_speaker_boost=False,
            ),
        )
        
        async for chunk in audio_stream:
            if chunk and first_chunk_time is None:
                first_chunk_time = time.time()
                break
        
        assert first_chunk_time is not None, "No audio chunks received"
        latency = first_chunk_time - start_time
        assert latency < 1.0, f"Latency too high: {latency:.2f}s"
        
        print(f"✓ First chunk latency: {latency*1000:.0f}ms")
import io
import logging
from collections.abc import AsyncGenerator, Generator

import numpy as np
from elevenlabs import ElevenLabs, VoiceSettings
from elevenlabs.client import AsyncElevenLabs
from pydub import AudioSegment

logger = logging.getLogger(__name__)


class ElevenLabsTTS:
    """ElevenLabs TTS implementation compatible with fastrtc interface."""

    def __init__(
        self,
        api_key: str,
        voice_id: str = "0NkECxcbkydDMspBKvQp",
        model_id: str = "eleven_flash_v2_5",
        stability: float = 0.5,
        similarity_boost: float = 0.5,
        style: float = 0.5,
        use_speaker_boost: bool = True,
        sample_rate: int = 16000,
    ):
        """Initialize ElevenLabs TTS.

        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID to use
            model_id: Model ID to use
            stability: Voice stability (0-1)
            similarity_boost: Voice similarity boost (0-1)
            style: Voice style (0-1)
            use_speaker_boost: Whether to use speaker boost
            sample_rate: Output sample rate in Hz
        """
        self.client = ElevenLabs(api_key=api_key)
        self.async_client = AsyncElevenLabs(api_key=api_key)
        self.voice_id = voice_id
        self.model_id = model_id
        self.voice_settings = VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=use_speaker_boost,
        )
        self.sample_rate = sample_rate

    def _convert_audio_format(self, audio_bytes: bytes) -> np.ndarray:
        """Convert ElevenLabs audio output to numpy array.

        Args:
            audio_bytes: Raw audio bytes from ElevenLabs

        Returns:
            Audio as numpy array with shape (n_samples,)
        """
        # Load audio from bytes
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")

        # Convert to mono if stereo
        if audio_segment.channels > 1:
            audio_segment = audio_segment.set_channels(1)

        # Resample to target sample rate
        audio_segment = audio_segment.set_frame_rate(self.sample_rate)

        # Convert to numpy array
        samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)

        # Normalize to [-1, 1] range
        max_val = 2**15  # 16-bit audio
        samples_normalized = samples / max_val

        return samples_normalized.astype(np.float32)

    def stream_tts_sync(
        self, text: str, voice_id: str | None = None
    ) -> Generator[tuple[int, np.ndarray], None, None]:
        """Stream TTS synchronously, compatible with fastrtc interface.

        Args:
            text: Text to synthesize
            voice_id: Optional voice ID override

        Yields:
            Tuple of (sample_rate, audio_chunk) where audio_chunk is numpy array
        """
        try:
            # Generate audio with ElevenLabs
            audio_stream = self.client.text_to_speech.stream(
                text=text,
                voice_id=voice_id or self.voice_id,
                voice_settings=self.voice_settings,
                model_id=self.model_id,
            )

            # Buffer to accumulate audio chunks
            audio_buffer = io.BytesIO()

            for chunk in audio_stream:
                if chunk:
                    audio_buffer.write(chunk)

                    # Process when we have enough data (e.g., 1 second worth)
                    if audio_buffer.tell() > self.sample_rate * 2:  # 2 bytes per sample
                        audio_buffer.seek(0)
                        audio_data = audio_buffer.read()
                        audio_buffer = io.BytesIO()

                        try:
                            audio_array = self._convert_audio_format(audio_data)
                            yield (self.sample_rate, audio_array)
                        except Exception as e:
                            logger.warning(
                                f"Failed to convert audio chunk: {e}, skipping"
                            )

            # Process any remaining audio
            if audio_buffer.tell() > 0:
                audio_buffer.seek(0)
                audio_data = audio_buffer.read()
                try:
                    audio_array = self._convert_audio_format(audio_data)
                    yield (self.sample_rate, audio_array)
                except Exception as e:
                    logger.warning(f"Failed to convert final audio chunk: {e}")

        except Exception as e:
            logger.error(f"Error in ElevenLabs TTS: {e}")
            raise

    async def stream_tts(
        self, text: str, voice_id: str | None = None
    ) -> AsyncGenerator[tuple[int, np.ndarray], None]:
        """Stream TTS asynchronously.

        Args:
            text: Text to synthesize
            voice_id: Optional voice ID override

        Yields:
            Tuple of (sample_rate, audio_chunk) where audio_chunk is numpy array
        """
        try:
            # Generate audio with ElevenLabs async client
            audio_stream = self.async_client.text_to_speech.stream(
                text=text,
                voice_id=voice_id or self.voice_id,
                voice_settings=self.voice_settings,
                model_id=self.model_id,
            )

            # Buffer to accumulate audio chunks
            audio_buffer = io.BytesIO()

            async for chunk in audio_stream:
                if chunk:
                    audio_buffer.write(chunk)

                    # Process when we have enough data
                    if audio_buffer.tell() > self.sample_rate * 2:
                        audio_buffer.seek(0)
                        audio_data = audio_buffer.read()
                        audio_buffer = io.BytesIO()

                        try:
                            audio_array = self._convert_audio_format(audio_data)
                            yield (self.sample_rate, audio_array)
                        except Exception as e:
                            logger.warning(
                                f"Failed to convert audio chunk: {e}, skipping"
                            )

            # Process any remaining audio
            if audio_buffer.tell() > 0:
                audio_buffer.seek(0)
                audio_data = audio_buffer.read()
                try:
                    audio_array = self._convert_audio_format(audio_data)
                    yield (self.sample_rate, audio_array)
                except Exception as e:
                    logger.warning(f"Failed to convert final audio chunk: {e}")

        except Exception as e:
            logger.error(f"Error in ElevenLabs TTS: {e}")
            raise

    def tts(self, text: str, voice_id: str | None = None) -> tuple[int, np.ndarray]:
        """Generate TTS synchronously (non-streaming).

        Args:
            text: Text to synthesize
            voice_id: Optional voice ID override

        Returns:
            Tuple of (sample_rate, audio_array)
        """
        try:
            # Generate complete audio
            audio_iterator = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id or self.voice_id,
                voice_settings=self.voice_settings,
                model_id=self.model_id,
            )
            
            # Collect all bytes from the iterator
            audio_bytes = b''.join(audio_iterator)

            # Convert to numpy array
            audio_array = self._convert_audio_format(audio_bytes)
            return (self.sample_rate, audio_array)

        except Exception as e:
            logger.error(f"Error in ElevenLabs TTS: {e}")
            raise

    async def atts(
        self, text: str, voice_id: str | None = None
    ) -> tuple[int, np.ndarray]:
        """Generate TTS asynchronously (non-streaming).

        Args:
            text: Text to synthesize
            voice_id: Optional voice ID override

        Returns:
            Tuple of (sample_rate, audio_array)
        """
        try:
            # Generate complete audio
            audio_iterator = self.async_client.text_to_speech.convert(
                text=text,
                voice_id=voice_id or self.voice_id,
                voice_settings=self.voice_settings,
                model_id=self.model_id,
            )
            
            # Collect all bytes from the async iterator
            chunks = []
            async for chunk in audio_iterator:
                chunks.append(chunk)
            audio_bytes = b''.join(chunks)

            # Convert to numpy array
            audio_array = self._convert_audio_format(audio_bytes)
            return (self.sample_rate, audio_array)

        except Exception as e:
            logger.error(f"Error in ElevenLabs TTS: {e}")
            raise

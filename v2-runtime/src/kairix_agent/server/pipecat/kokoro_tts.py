"""Kokoro TTS service for Pipecat.

Uses the OpenAI-compatible Kokoro-FastAPI server for local TTS.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from openai import BadRequestError
from pipecat.frames.frames import ErrorFrame, Frame, TTSAudioRawFrame, TTSStartedFrame, TTSStoppedFrame
from pipecat.services.openai.tts import OpenAITTSService

logger = logging.getLogger(__name__)


class KokoroTTSService(OpenAITTSService):
    """Kokoro TTS using OpenAI-compatible API.

    Kokoro is a lightweight 82M parameter TTS model that runs locally.
    It exposes an OpenAI-compatible API at /v1/audio/speech.

    Voices available (67 total):
        - af_* : American Female (bella, heart, jessica, nicole, nova, sarah, sky...)
        - am_* : American Male (adam, echo, liam, michael, onyx...)
        - bf_* : British Female
        - bm_* : British Male
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:8880/v1",
        voice: str = "af_bella",
        model: str = "kokoro",
        sample_rate: int = 24000,
        **kwargs,
    ) -> None:
        """Initialize Kokoro TTS service.

        Args:
            base_url: Kokoro server URL (default: http://localhost:8880/v1)
            voice: Voice ID (default: af_bella)
            model: Model name (default: kokoro)
            sample_rate: Audio sample rate (default: 24000)
            **kwargs: Additional arguments passed to OpenAITTSService
        """
        super().__init__(
            api_key="not-needed",  # Kokoro doesn't require auth
            base_url=base_url,
            voice=voice,
            model=model,
            sample_rate=sample_rate,
            **kwargs,
        )

    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """Generate speech from text using Kokoro TTS.

        Overrides OpenAITTSService.run_tts to bypass VALID_VOICES validation
        since Kokoro uses its own voice IDs.

        Args:
            text: The text to synthesize into speech.

        Yields:
            Frame: Audio frames containing the synthesized speech data.
        """
        logger.debug("%s: Generating TTS [%s]", self, text)
        try:
            await self.start_ttfb_metrics()

            # Pass voice directly instead of looking up in VALID_VOICES
            create_params = {
                "input": text,
                "model": self.model_name,
                "voice": self._voice_id,  # Use voice directly, not VALID_VOICES lookup
                "response_format": "pcm",
            }

            async with self._client.audio.speech.with_streaming_response.create(
                **create_params
            ) as r:
                if r.status_code != 200:
                    error = await r.text()
                    logger.error(
                        "%s error getting audio (status: %s, error: %s)",
                        self,
                        r.status_code,
                        error,
                    )
                    yield ErrorFrame(
                        error=f"Error getting audio (status: {r.status_code}, error: {error})"
                    )
                    return

                await self.start_tts_usage_metrics(text)

                chunk_size = self.chunk_size

                yield TTSStartedFrame()
                async for chunk in r.iter_bytes(chunk_size):
                    if len(chunk) > 0:
                        await self.stop_ttfb_metrics()
                        frame = TTSAudioRawFrame(chunk, self.sample_rate, 1)
                        yield frame
                yield TTSStoppedFrame()
        except BadRequestError as e:
            logger.exception("Kokoro TTS error")
            yield ErrorFrame(error=f"Kokoro TTS error: {e}")

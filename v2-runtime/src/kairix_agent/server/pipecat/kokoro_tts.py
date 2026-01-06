"""Kokoro TTS service for Pipecat.

Uses the OpenAI-compatible Kokoro-FastAPI server for local TTS.
"""

from __future__ import annotations

from pipecat.services.openai.tts import OpenAITTSService


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

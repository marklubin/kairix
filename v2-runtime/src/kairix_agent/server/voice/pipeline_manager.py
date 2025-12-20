"""Pipeline manager for tracking active voice pipelines."""

import asyncio
import logging
from collections import defaultdict

from pipecat.frames.frames import TTSUpdateSettingsFrame
from pipecat.services.cartesia.tts import CartesiaTTSService

logger = logging.getLogger(__name__)


class VoicePipelineManager:
    """Manages active voice pipelines per agent.

    Tracks TTS services for each agent_id so we can push
    TTSUpdateSettingsFrame when voice settings change.
    """

    def __init__(self) -> None:
        self._pipelines: dict[str, set[CartesiaTTSService]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def register(self, agent_id: str, tts: CartesiaTTSService) -> None:
        """Register a TTS service for an agent."""
        async with self._lock:
            self._pipelines[agent_id].add(tts)
            logger.info(
                "Registered TTS pipeline for agent %s (total: %d)",
                agent_id,
                len(self._pipelines[agent_id]),
            )

    async def unregister(self, agent_id: str, tts: CartesiaTTSService) -> None:
        """Unregister a TTS service for an agent."""
        async with self._lock:
            self._pipelines[agent_id].discard(tts)
            if not self._pipelines[agent_id]:
                del self._pipelines[agent_id]
            logger.info("Unregistered TTS pipeline for agent %s", agent_id)

    async def update_voice(self, agent_id: str, provider_voice_id: str) -> int:
        """Push voice update to all active pipelines for an agent.

        Args:
            agent_id: The agent whose pipelines to update.
            provider_voice_id: The new Cartesia voice ID.

        Returns:
            Number of pipelines updated.
        """
        async with self._lock:
            services = list(self._pipelines.get(agent_id, []))

        if not services:
            logger.debug("No active pipelines for agent %s", agent_id)
            return 0

        update_frame = TTSUpdateSettingsFrame(settings={"voice_id": provider_voice_id})
        updated = 0
        for tts in services:
            try:
                await tts.queue_frame(update_frame)
                updated += 1
                logger.info(
                    "Updated voice to %s for agent %s", provider_voice_id, agent_id
                )
            except Exception:
                logger.exception("Failed to update TTS voice for agent %s", agent_id)

        return updated


# Singleton instance
voice_pipeline_manager = VoicePipelineManager()

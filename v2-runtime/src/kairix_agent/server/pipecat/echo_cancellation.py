"""Echo cancellation processor for Pipecat pipeline.

Raises VAD threshold during bot speech to prevent echo triggers while
still allowing genuine user interruptions (barge-in).

This is Layer 2 of the echo cancellation strategy:
- Layer 1 (Client): iOS hardware AEC via AVAudioSessionModeVoiceChat
- Layer 2 (Server): Adaptive VAD thresholds (this module)
"""

from __future__ import annotations

import logging

from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    VADParamsUpdateFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

logger = logging.getLogger(__name__)


class EchoCancellationProcessor(FrameProcessor):
    """Raises VAD threshold during bot speech to prevent echo triggers.

    When the bot starts speaking, raises min_volume threshold so only
    loud genuine speech triggers interruption. When bot stops, restores
    normal threshold.

    Thresholds are configurable at runtime via update_thresholds().
    """

    def __init__(
        self,
        *,
        normal_min_volume: float = 0.4,
        speaking_min_volume: float = 0.7,
        name: str | None = None,
    ) -> None:
        super().__init__(name=name)
        self._normal_volume = normal_min_volume
        self._speaking_volume = speaking_min_volume
        self._bot_speaking = False

    def update_thresholds(self, normal: float, speaking: float) -> None:
        """Update thresholds at runtime (called from API endpoint)."""
        logger.info(
            "Updating echo cancellation thresholds: normal=%.2f, speaking=%.2f",
            normal,
            speaking,
        )
        self._normal_volume = normal
        self._speaking_volume = speaking

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, BotStartedSpeakingFrame):
            self._bot_speaking = True
            logger.debug("Bot started speaking, raising VAD threshold to %.2f", self._speaking_volume)
            await self._push_vad_update(self._speaking_volume)
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_speaking = False
            logger.debug("Bot stopped speaking, restoring VAD threshold to %.2f", self._normal_volume)
            await self._push_vad_update(self._normal_volume)

        await self.push_frame(frame, direction)

    async def _push_vad_update(self, min_volume: float) -> None:
        """Push VAD params update upstream to transport."""
        params = VADParams(min_volume=min_volume)
        await self.push_frame(
            VADParamsUpdateFrame(params=params),
            FrameDirection.UPSTREAM,
        )

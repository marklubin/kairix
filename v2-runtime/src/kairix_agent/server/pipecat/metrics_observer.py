"""Metrics observer for Pipecat pipeline.

Tracks latency for each pipeline stage by observing frame flow:
- STT: UserStoppedSpeakingFrame → TranscriptionFrame
- LLM: UserTurnMessageFrame → LLMFullResponseEndFrame
- TTS: TextFrame → TTSAudioRawFrame

Also tracks interruptions (BotInterruptedFrame) and turns.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from pipecat.frames.frames import (
    BotInterruptionFrame,
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from kairix_agent.server.metrics import (
    record_interruption,
    record_llm_latency,
    record_llm_ttfb,
    record_stt_latency,
    record_tts_latency,
    record_turn,
)
from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnMessageFrame

logger = logging.getLogger(__name__)


@dataclass
class TurnTiming:
    """Timing data for a single conversation turn."""

    # User speaking phase
    user_started_at: float | None = None
    user_stopped_at: float | None = None
    transcript_received_at: float | None = None

    # LLM phase
    llm_started_at: float | None = None
    llm_first_token_at: float | None = None
    llm_ended_at: float | None = None

    # TTS phase
    tts_started_at: float | None = None
    tts_first_audio_at: float | None = None
    tts_ended_at: float | None = None

    def reset(self) -> None:
        """Reset all timing data."""
        self.user_started_at = None
        self.user_stopped_at = None
        self.transcript_received_at = None
        self.llm_started_at = None
        self.llm_first_token_at = None
        self.llm_ended_at = None
        self.tts_started_at = None
        self.tts_first_audio_at = None
        self.tts_ended_at = None


class PipelineMetricsObserver(FrameProcessor):
    """Observes pipeline frames to collect latency metrics.

    Insert this after each stage you want to measure, or use a single
    observer at the end of the pipeline to capture all frames.

    Metrics collected:
    - STT latency: time from user stop speaking to final transcript
    - LLM TTFB: time from user turn message to first LLM token
    - LLM latency: time from user turn message to response complete
    - TTS latency: time from first text to first audio

    Also counts:
    - Turns (UserTurnMessageFrame)
    - Interruptions (BotInterruptedFrame)
    """

    def __init__(self, agent_id: str, *, name: str | None = None) -> None:
        """Initialize the metrics observer.

        Args:
            agent_id: Agent ID for metric labels.
            name: Optional name for this processor.
        """
        super().__init__(name=name or "metrics_observer")
        self._agent_id = agent_id
        self._timing = TurnTiming()
        self._in_llm_response = False
        self._in_tts = False

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Process frames and collect timing metrics."""
        await super().process_frame(frame, direction)

        # Only track downstream frames
        if direction == FrameDirection.DOWNSTREAM:
            self._track_frame(frame)

        # Always pass frame through
        await self.push_frame(frame, direction)

    def _track_frame(self, frame: Frame) -> None:
        """Track timing for a frame."""
        now = time.perf_counter()

        # === User Speaking Phase ===
        if isinstance(frame, UserStartedSpeakingFrame):
            self._timing.reset()
            self._timing.user_started_at = now
            logger.debug("User started speaking")

        elif isinstance(frame, UserStoppedSpeakingFrame):
            self._timing.user_stopped_at = now
            logger.debug("User stopped speaking")

        elif isinstance(frame, TranscriptionFrame):
            # Final transcript received
            if self._timing.transcript_received_at is None:
                self._timing.transcript_received_at = now
                # Record STT latency (time from user stop to transcript)
                if self._timing.user_stopped_at is not None:
                    latency = now - self._timing.user_stopped_at
                    record_stt_latency(latency, self._agent_id)
                    logger.debug("STT latency: %.3fs", latency)

        # === LLM Phase ===
        elif isinstance(frame, UserTurnMessageFrame):
            self._timing.llm_started_at = now
            self._in_llm_response = False
            record_turn(self._agent_id)
            logger.debug("Turn started, waiting for LLM response")

        elif isinstance(frame, LLMFullResponseStartFrame):
            # LLM started generating
            if self._timing.llm_started_at is not None and not self._in_llm_response:
                self._in_llm_response = True

        elif isinstance(frame, TextFrame) and self._in_llm_response:
            # First text token from LLM
            if self._timing.llm_first_token_at is None and self._timing.llm_started_at is not None:
                self._timing.llm_first_token_at = now
                ttfb = now - self._timing.llm_started_at
                record_llm_ttfb(ttfb, self._agent_id)
                logger.debug("LLM TTFB: %.3fs", ttfb)
                # Also mark TTS start (first text going to TTS)
                self._timing.tts_started_at = now

        elif isinstance(frame, LLMFullResponseEndFrame):
            if self._timing.llm_started_at is not None:
                self._timing.llm_ended_at = now
                latency = now - self._timing.llm_started_at
                record_llm_latency(latency, self._agent_id)
                logger.debug("LLM total latency: %.3fs", latency)
            self._in_llm_response = False

        # === TTS Phase ===
        elif isinstance(frame, TTSStartedFrame):
            self._in_tts = True

        elif isinstance(frame, TTSAudioRawFrame):
            # First audio from TTS
            if self._timing.tts_first_audio_at is None and self._timing.tts_started_at is not None:
                self._timing.tts_first_audio_at = now
                latency = now - self._timing.tts_started_at
                record_tts_latency(latency, self._agent_id)
                logger.debug("TTS latency: %.3fs", latency)

        elif isinstance(frame, TTSStoppedFrame):
            self._in_tts = False
            self._timing.tts_ended_at = now

        # === Interruptions ===
        elif isinstance(frame, BotInterruptionFrame):
            record_interruption(self._agent_id)
            logger.debug("Bot interrupted by user")

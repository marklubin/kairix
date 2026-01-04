"""Letta LLM service for Pipecat pipelines.

This bridges Letta's streaming API into Pipecat's frame-based architecture.
Uses the shared ConversationService for consistent behavior with the /ws endpoint.
"""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from pipecat.frames.frames import (
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from kairix_agent.server.conversation import ConversationService
from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnMessageFrame

if TYPE_CHECKING:
    from saq import Queue

logger = getLogger(__name__)


class LettaLLMService(FrameProcessor):
    """Pipecat LLM service that uses Letta as the backend.

    This processor receives transcription frames (from STT) and emits text
    frames (for TTS) by calling the Letta agent API via the shared
    ConversationService.

    Letta manages conversation history server-side, so we don't need Pipecat's
    context aggregator - we just forward each utterance to Letta.

    Frame Flow:
        Input:  UserTurnMessageFrame (from UserTurnAggregator)
        Output: LLMFullResponseStartFrame → TextFrame(s) → LLMFullResponseEndFrame
    """

    def __init__(
        self,
        *,
        agent_id: str,
        base_url: str | None = None,
        name: str | None = None,
        queue: Queue | None = None,
    ) -> None:
        """Initialize the Letta LLM service.

        Args:
            agent_id: The Letta agent ID to use for conversations.
            base_url: The Letta server URL (defaults to LETTA_BASE_URL env var).
            name: Optional name for this processor (for logging/debugging).
            queue: Optional SAQ queue for enqueuing background jobs.
        """
        super().__init__(name=name)
        self._agent_id = agent_id
        # Use shared ConversationService for consistent behavior with /ws
        self._conversation = ConversationService(
            agent_id=agent_id,
            base_url=base_url,
            queue=queue,
            filter_markdown=True,
        )

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Process incoming frames and generate LLM responses.

        Args:
            frame: The incoming frame to process.
            direction: The direction of frame flow (downstream/upstream).
        """
        await super().process_frame(frame, direction)

        # We only process text-bearing frames going downstream
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        # Extract user message from frame
        user_message = self._extract_message(frame)
        if user_message is None:
            # Pass through frames we don't handle (audio, system frames, etc.)
            await self.push_frame(frame, direction)
            return

        logger.info("LettaLLMService received message: %s", user_message)

        # Signal response is starting
        await self.push_frame(LLMFullResponseStartFrame())

        # Stream response via shared ConversationService
        # (handles markdown filtering and background job enqueueing)
        async for chunk in self._conversation.stream_response(user_message):
            await self.push_frame(TextFrame(text=chunk))

        # Signal response is complete
        await self.push_frame(LLMFullResponseEndFrame())

    def _extract_message(self, frame: Frame) -> str | None:
        if isinstance(frame, UserTurnMessageFrame):
            return frame.text
        return None

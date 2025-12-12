"""Letta LLM service for Pipecat pipelines.

This bridges Letta's streaming API into Pipecat's frame-based architecture.
"""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from letta_client import AsyncLetta, AsyncStream
from letta_client.types.agents import AssistantMessage, LettaStreamingResponse
from pipecat.frames.frames import (
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter
from rich.pretty import pretty_repr

from kairix_agent.config import Config
from kairix_agent.server.pipecat.user_turn_aggregator import UserTurnMessageFrame
from kairix_agent.worker.jobs import TRIGGER_INSIGHTS_JOB

if TYPE_CHECKING:
    from saq import Queue

logger = getLogger(__name__)


class LettaLLMService(FrameProcessor):
    """Pipecat LLM service that uses Letta as the backend.

    This processor receives transcription frames (from STT) and emits text
    frames (for TTS) by calling the Letta agent API.

    Letta manages conversation history server-side, so we don't need Pipecat's
    context aggregator - we just forward each utterance to Letta.

    Frame Flow:
        Input:  TranscriptionFrame (from STT) or TextFrame
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
        if base_url is None:
            base_url = Config.LETTA_BASE_URL.value
        self._base_url = base_url
        self._client = AsyncLetta(base_url=base_url)
        self._agent_id = agent_id
        self._filter = MarkdownTextFilter()
        self._queue = queue

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

        response_stream: AsyncStream[
            LettaStreamingResponse
        ] = await self._client.agents.messages.stream(
            agent_id=self._agent_id, input=user_message, streaming=True, stream_tokens=True
        )

        async for response in response_stream:
            pretty_response = pretty_repr(response)
            logger.info(
                "Got letta response of type %s, with content: \n\n %s \n\n",
                response.message_type,
                pretty_response,
            )
            if isinstance(response, AssistantMessage):
                if not isinstance(response.content, str):
                    logger.info("Unexpected content type for response: %s", type(response.content))
                else:
                    filtered_text = await self._filter.filter(response.content)
                    await self.push_frame(TextFrame(text=filtered_text))

        # Signal response is complete
        await self.push_frame(LLMFullResponseEndFrame())

        # Enqueue background insights job
        await self._enqueue_insights()

    async def _enqueue_insights(self) -> None:
        """Enqueue an insights reflection job after LLM response."""
        if self._queue is None:
            logger.debug("No queue configured, skipping insights trigger")
            return

        try:
            await self._queue.enqueue(
                TRIGGER_INSIGHTS_JOB,
                agent_id=self._agent_id,
                letta_url=self._base_url,
                timeout=60,
            )
            logger.info("Enqueued insights job for agent %s", self._agent_id)
        except Exception:
            logger.exception("Failed to enqueue insights job")

    def _extract_message(self, frame: Frame) -> str | None:
        if isinstance(frame, UserTurnMessageFrame):
            return frame.text
        return None

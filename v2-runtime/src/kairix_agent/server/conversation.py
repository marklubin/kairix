"""Shared conversation service for text and voice endpoints.

This module provides a unified code path for streaming responses from Letta,
ensuring consistent behavior (markdown filtering, background jobs) across
both the /ws text endpoint and the /voice pipeline.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from letta_client import AsyncLetta, AsyncStream
from letta_client.types.agents import AssistantMessage, LettaStreamingResponse
from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter

from kairix_agent.config import Config
from kairix_agent.worker.jobs import TRIGGER_INSIGHTS_JOB

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from saq import Queue

logger = logging.getLogger(__name__)


class ConversationService:
    """Unified service for streaming Letta responses.

    Used by both /ws (text) and /voice (Pipecat) endpoints to ensure
    consistent behavior:
    - Markdown filtering on response text
    - Background job enqueueing (insights)

    Example:
        service = ConversationService(agent_id="agent-123", queue=job_queue)
        async for chunk in service.stream_response("Hello"):
            print(chunk)
    """

    def __init__(
        self,
        *,
        agent_id: str,
        base_url: str | None = None,
        queue: Queue | None = None,
        filter_markdown: bool = True,
    ) -> None:
        """Initialize the conversation service.

        Args:
            agent_id: The Letta agent ID to use for conversations.
            base_url: The Letta server URL (defaults to LETTA_BASE_URL env var).
            queue: Optional SAQ queue for enqueuing background jobs.
            filter_markdown: Whether to filter markdown from responses (default True).
        """
        if base_url is None:
            base_url = Config.LETTA_BASE_URL.value
        self._base_url = base_url
        self._client = AsyncLetta(base_url=base_url)
        self._agent_id = agent_id
        self._queue = queue
        self._filter_markdown = filter_markdown
        self._filter = MarkdownTextFilter() if filter_markdown else None

    async def stream_response(self, user_message: str) -> AsyncIterator[str]:
        """Stream a response from Letta for the given user message.

        Args:
            user_message: The user's input text.

        Yields:
            Text chunks from the assistant's response.
        """
        logger.info("ConversationService received message: %s", user_message)

        response_stream: AsyncStream[
            LettaStreamingResponse
        ] = await self._client.agents.messages.stream(
            agent_id=self._agent_id,
            input=user_message,
            streaming=True,
            stream_tokens=True,
        )

        async for response in response_stream:
            logger.debug(
                "Letta response type=%s content=%s",
                response.message_type,
                getattr(response, "content", None),
            )
            if isinstance(response, AssistantMessage):
                content = response.content
                if not isinstance(content, str):
                    logger.warning("Unexpected content type: %s", type(content))
                    continue

                # Apply markdown filtering if enabled
                if self._filter is not None:
                    content = await self._filter.filter(content)

                if content:
                    yield content

        # Enqueue background insights job after response completes
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

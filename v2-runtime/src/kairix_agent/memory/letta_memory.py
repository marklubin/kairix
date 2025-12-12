"""Letta memory service for archival memory operations.

Wraps the Letta SDK to provide:
- Message history retrieval (for session detection)
- Passage creation (for storing summaries)
- Passage search (for retrieving summaries)
"""

from collections.abc import AsyncIterator
from datetime import datetime
from logging import getLogger

from letta_client import AsyncLetta
from letta_client.types.agents import Message

from kairix_agent.config import Config
from kairix_agent.memory.models import ConversationSummary

logger = getLogger(__name__)


class LettaMemoryService:
    """Service for interacting with Letta's memory systems."""

    def __init__(
        self,
        agent_id: str,
        archive_id: str,
        base_url: str | None = None,
    ) -> None:
        """Initialize the memory service.

        Args:
            agent_id: The Letta agent ID for message queries.
            archive_id: The Letta archive ID for storing passages.
            base_url: The Letta server URL (defaults to LETTA_BASE_URL env var).
        """
        if base_url is None:
            base_url = Config.LETTA_BASE_URL.value
        self.client = AsyncLetta(base_url=base_url)
        self.agent_id = agent_id
        self.archive_id = archive_id

    async def get_messages_since(
        self,
        after_message_id: str | None = None,
        limit: int = 100,
    ) -> AsyncIterator[Message]:
        """Get messages since a cursor position.

        Uses Letta's message ID-based pagination. If no cursor is provided,
        returns messages from the beginning.

        Args:
            after_message_id: Message ID to start after (exclusive).
            limit: Maximum messages per page.

        Yields:
            Message objects in chronological order.
        """
        # The AsyncPaginator automatically handles iteration across pages
        # It implements __aiter__ which yields items directly
        paginator = self.client.agents.messages.list(
            agent_id=self.agent_id,
            after=after_message_id,
            limit=limit,
            order="asc",
            order_by="created_at",
        )

        async for message in paginator:
            yield message

    async def store_summary(self, summary: ConversationSummary) -> str:
        """Store a summary as a passage in archival memory.

        Args:
            summary: The summary to store.

        Returns:
            The created passage ID.
        """
        passage = await self.client.archives.passages.create(
            archive_id=self.archive_id,
            text=summary.to_passage_text(),
            tags=[summary.to_tag()],
            metadata={
                "summary_id": str(summary.summary_id),
                "summary_type": summary.summary_type.value,
                "period_start": summary.period_start.isoformat(),
                "period_end": summary.period_end.isoformat(),
                "message_count": summary.message_count,
                "source_message_ids": summary.source_message_ids,
            },
        )

        logger.info(
            "Stored %s summary for period %s to %s (passage_id=%s)",
            summary.summary_type.value,
            summary.period_start,
            summary.period_end,
            passage.id,
        )

        return passage.id or ""

    async def search_summaries(
        self,
        query: str,
        summary_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 10,
    ) -> list[dict[str, object]]:
        """Search for relevant summaries.

        Args:
            query: Semantic search query.
            summary_type: Filter by summary type (e.g., "session", "daily").
            start_date: Filter to summaries after this date.
            end_date: Filter to summaries before this date.
            limit: Maximum number of results.

        Returns:
            List of matching passages with relevance scores.
        """
        tags = [f"summary:{summary_type}"] if summary_type else None

        response = await self.client.passages.search(
            query=query,
            agent_id=self.agent_id,
            tags=tags,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

        # Extract passage data with scores
        results: list[dict[str, object]] = []
        for item in response:
            passage = item.passage
            results.append({
                "id": passage.id,
                "text": passage.text,
                "tags": passage.tags,
                "metadata": passage.metadata,
                "created_at": passage.created_at,
                "score": item.score,
            })

        return results

"""Redis-based cursor storage for tracking summarization progress."""

from datetime import datetime
from logging import getLogger

from redis.asyncio import Redis

from kairix_agent.memory.models import SummarizationCursor

logger = getLogger(__name__)


class CursorStore:
    """Store and retrieve summarization cursors from Redis."""

    def __init__(self, redis: Redis) -> None:  # type: ignore[type-arg]
        """Initialize cursor store with Redis client.

        Args:
            redis: Async Redis client instance.
        """
        self.redis = redis

    async def get_cursor(self, agent_id: str) -> SummarizationCursor | None:
        """Get the current cursor for an agent.

        Args:
            agent_id: The Letta agent ID.

        Returns:
            The cursor if it exists, None otherwise.
        """
        key = f"summarization_cursor:{agent_id}"
        data = await self.redis.hgetall(key)  # type: ignore[misc]

        if not data:
            return None

        # Redis returns bytes, decode to strings
        decoded = {k.decode(): v.decode() for k, v in data.items()}

        return SummarizationCursor(
            agent_id=decoded["agent_id"],
            last_summarized_at=datetime.fromisoformat(decoded["last_summarized_at"]),
            last_message_id=decoded["last_message_id"],
        )

    async def set_cursor(self, cursor: SummarizationCursor) -> None:
        """Save a cursor to Redis.

        Args:
            cursor: The cursor to save.
        """
        key = cursor.redis_key()
        data = {
            "agent_id": cursor.agent_id,
            "last_summarized_at": cursor.last_summarized_at.isoformat(),
            "last_message_id": cursor.last_message_id,
        }

        await self.redis.hset(key, mapping=data)  # type: ignore[misc]

        logger.debug(
            "Saved cursor for agent %s: last_message_id=%s",
            cursor.agent_id,
            cursor.last_message_id,
        )

    async def delete_cursor(self, agent_id: str) -> None:
        """Delete a cursor from Redis.

        Args:
            agent_id: The Letta agent ID.
        """
        key = f"summarization_cursor:{agent_id}"
        await self.redis.delete(key)  # type: ignore[misc]
        logger.debug("Deleted cursor for agent %s", agent_id)

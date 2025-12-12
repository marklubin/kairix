"""Event publisher for background worker jobs."""

import logging

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kairix_agent.config import Config
from kairix_agent.events.models import AgentEvent, EventType

logger = logging.getLogger(__name__)

# Async engine and session factory (lazy initialized)
_engine = create_async_engine(Config.DATABASE_URL.value, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

# Redis client (lazy initialized)
_redis: redis.Redis | None = None


async def _get_redis() -> redis.Redis:  # type: ignore[type-arg]
    """Get or create the Redis client."""
    global _redis
    if _redis is None:
        _redis = redis.from_url(Config.REDIS_URL.value)
    return _redis


async def publish_event(
    agent_id: str,
    event_type: EventType,
    payload: dict | None = None,  # type: ignore[type-arg]
) -> AgentEvent:
    """Publish an event by inserting into Postgres and notifying via Redis.

    Args:
        agent_id: The agent this event belongs to.
        event_type: Type of event (from EventType enum).
        payload: Optional event-specific data.

    Returns:
        The created AgentEvent record.
    """
    # 1. Insert into Postgres (source of truth)
    async with _async_session() as session:
        event = AgentEvent(
            agent_id=agent_id,
            event_type=event_type.value,
            payload=payload or {},
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)

    # 2. Notify via Redis pub/sub (for real-time streaming)
    r = await _get_redis()
    channel = f"agent_events:{agent_id}"
    await r.publish(channel, event.id)
    logger.debug("Published event %s to Redis channel %s", event.id, channel)

    return event

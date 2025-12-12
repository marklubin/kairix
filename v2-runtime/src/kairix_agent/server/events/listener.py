"""Redis pub/sub listener for agent events."""

import asyncio
import logging

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kairix_agent.config import Config
from kairix_agent.events.models import AgentEvent
from kairix_agent.server.events.connection_manager import connection_manager

logger = logging.getLogger(__name__)

# Database session for fetching event details
_engine = create_async_engine(Config.DATABASE_URL.value, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _fetch_event(event_id: str) -> dict | None:  # type: ignore[type-arg]
    """Fetch event details from Postgres by ID.

    Args:
        event_id: The event UUID.

    Returns:
        Event data dict or None if not found.
    """
    logger.debug("[fetch] Looking up event %s in database", event_id)
    async with _async_session() as session:
        result = await session.execute(
            select(AgentEvent).where(AgentEvent.id == event_id)
        )
        event = result.scalar_one_or_none()
        if event is None:
            logger.warning("[fetch] Event %s not found in database", event_id)
            return None
        logger.debug("[fetch] Found event %s: type=%s, agent=%s", event_id, event.event_type, event.agent_id)
        return {
            "id": event.id,
            "agent_id": event.agent_id,
            "event_type": event.event_type,
            "payload": event.payload,
            "created_at": event.created_at.isoformat(),
        }


async def start_event_listener() -> None:
    """Start the Redis pub/sub listener for agent events.

    This is a long-running task that should be started on server startup.
    It subscribes to the 'agent_events:*' pattern and dispatches events
    to connected WebSocket clients via the ConnectionManager.
    """
    logger.info("[listener] Starting Redis event listener...")
    logger.info("[listener] Redis URL: %s", Config.REDIS_URL.value)

    while True:
        try:
            logger.info("[listener] Connecting to Redis...")
            r = redis.from_url(Config.REDIS_URL.value)
            pubsub = r.pubsub()

            # Subscribe to pattern: agent_events:{agent_id}
            await pubsub.psubscribe("agent_events:*")
            logger.info("[listener] Subscribed to 'agent_events:*' pattern, waiting for messages...")

            async for message in pubsub.listen():
                logger.debug("[listener] Received raw message: type=%s", message.get("type"))

                if message["type"] != "pmessage":
                    logger.debug("[listener] Skipping non-pmessage: %s", message.get("type"))
                    continue

                try:
                    # Extract channel and decode if bytes
                    channel = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode("utf-8")
                    logger.info("[listener] Message on channel: %s", channel)

                    # Extract agent_id from channel name
                    agent_id = channel.replace("agent_events:", "")
                    logger.info("[listener] Extracted agent_id: %s", agent_id)

                    # Get event ID from message data
                    event_id = message["data"]
                    if isinstance(event_id, bytes):
                        event_id = event_id.decode("utf-8")
                    logger.info("[listener] Event ID: %s", event_id)

                    # Fetch full event from Postgres
                    logger.info("[listener] Fetching event details from Postgres...")
                    event_data = await _fetch_event(event_id)
                    if event_data is None:
                        logger.error("[listener] Event %s not found in database, skipping", event_id)
                        continue
                    logger.info("[listener] Fetched event: type=%s", event_data.get("event_type"))

                    # Dispatch to connected WebSocket clients
                    logger.info("[listener] Dispatching to ConnectionManager for agent %s...", agent_id)
                    await connection_manager.dispatch(agent_id, event_data)
                    logger.info(
                        "[listener] Successfully dispatched %s event for agent %s",
                        event_data.get("event_type"),
                        agent_id,
                    )

                except Exception:
                    logger.exception("[listener] Error processing Redis message")

        except asyncio.CancelledError:
            logger.info("[listener] Shutting down (cancelled)")
            raise
        except Exception:
            logger.exception("[listener] Connection error, reconnecting in 5s...")
            await asyncio.sleep(5)
"""Session boundary detection job."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import redis.asyncio as redis
from saq import Queue

from kairix_agent.agent_config import get_agent_config
from kairix_agent.config import Config
from kairix_agent.events import EventType, publish_event
from kairix_agent.memory import LettaMemoryService
from kairix_agent.sessions import (
    create_session,
    get_latest_session_end,
    get_pending_session_for_agent,
)

if TYPE_CHECKING:
    from saq.types import Context

logger = logging.getLogger(__name__)

# Lock settings
BOUNDARY_CHECK_LOCK_TTL = 120  # 2 minutes - longer than job timeout


async def _check_agent_session(
    queue: Queue,
    agent_id: str,
    letta_url: str,
    redis_client: redis.Redis,
) -> dict[str, object]:
    """Check session boundary for a single agent.

    Uses Redis locking to prevent race conditions between concurrent checks.

    Args:
        queue: SAQ queue for enqueueing summarization jobs.
        agent_id: The agent ID to check.
        letta_url: The Letta server URL.
        redis_client: Redis client for distributed locking.

    Returns:
        Status dict with detection results for this agent.
    """
    # Try to acquire a distributed lock for this agent
    lock_key = f"session_boundary_lock:{agent_id}"
    lock_acquired = await redis_client.set(
        lock_key,
        "1",
        nx=True,  # Only set if not exists
        ex=BOUNDARY_CHECK_LOCK_TTL,
    )

    if not lock_acquired:
        logger.info(
            "Session boundary check already running for agent %s, skipping",
            agent_id,
        )
        return {"status": "skipped", "reason": "lock_held"}

    try:
        return await _check_agent_session_locked(queue, agent_id, letta_url)
    finally:
        # Release the lock
        await redis_client.delete(lock_key)


async def _check_agent_session_locked(
    queue: Queue,
    agent_id: str,
    letta_url: str,
) -> dict[str, object]:
    """Check session boundary for a single agent (lock already held).

    Args:
        queue: SAQ queue for enqueueing summarization jobs.
        agent_id: The agent ID to check.
        letta_url: The Letta server URL.

    Returns:
        Status dict with detection results for this agent.
    """
    # Check if there's already a pending session (prevents duplicates)
    pending_session = await get_pending_session_for_agent(agent_id)
    if pending_session:
        logger.info(
            "Agent %s already has pending session %s, skipping boundary check",
            agent_id,
            pending_session.id,
        )
        return {
            "status": "skipped",
            "reason": "pending_session_exists",
            "session_id": pending_session.id,
        }

    # Load agent config (cached per agent_id after first call)
    agent_config = await get_agent_config(agent_id=agent_id, letta_url=letta_url)

    if not agent_config.archive_id:
        logger.warning(
            "Agent %s has no archive attached, skipping",
            agent_id,
        )
        return {"status": "skipped", "reason": "no archive attached"}

    memory_service = LettaMemoryService(
        agent_id=agent_config.agent_id,
        archive_id=agent_config.archive_id,
        base_url=letta_url,
    )

    # Get the latest session end time for this agent (to filter out already-tracked messages)
    latest_session_end = await get_latest_session_end(agent_config.agent_id)

    # Fetch all messages and filter to user/assistant messages AFTER the last session
    all_messages = await memory_service.get_all_messages()
    messages = [
        m for m in all_messages
        if m.message_type in ("user_message", "assistant_message")
        and (latest_session_end is None or m.date > latest_session_end)
    ]

    if not messages:
        logger.debug("No new conversation messages for agent %s", agent_config.agent_id)
        await publish_event(
            agent_id=agent_config.agent_id,
            event_type=EventType.SESSION_BOUNDARY,
            payload={
                "boundary_detected": False,
                "gap_minutes": 0,
                "message_count": 0,
            },
        )
        return {"status": "ok", "messages_found": 0}

    # Check if last message is old enough (session gap exceeded)
    last_message = messages[-1]
    last_message_time = last_message.date
    now = datetime.now(tz=UTC)
    gap = now - last_message_time
    session_gap_minutes = Config.SESSION_GAP_MINUTES.value

    if gap < timedelta(minutes=session_gap_minutes):
        logger.debug(
            "Session still active for agent %s (gap: %s < %s minutes)",
            agent_config.agent_id,
            gap,
            session_gap_minutes,
        )
        await publish_event(
            agent_id=agent_config.agent_id,
            event_type=EventType.SESSION_BOUNDARY,
            payload={
                "boundary_detected": False,
                "gap_minutes": gap.total_seconds() / 60,
                "message_count": len(messages),
            },
        )
        return {
            "status": "ok",
            "messages_found": len(messages),
            "session_active": True,
            "gap_seconds": gap.total_seconds(),
        }

    # Extract message IDs for the session
    message_ids = [m.id for m in messages]
    first_message = messages[0]

    # Session boundary detected - create session and proceed
    logger.info(
        "Detected session boundary for agent %s: %d messages, gap %s",
        agent_config.agent_id,
        len(messages),
        gap,
    )

    # Create session record in our database
    new_session = await create_session(
        agent_id=agent_config.agent_id,
        message_ids=message_ids,
        period_start=first_message.date,
        period_end=last_message.date,
    )
    logger.info(
        "Created session %s for agent %s with %d messages",
        new_session.id,
        agent_config.agent_id,
        len(message_ids),
    )

    # Publish session boundary event
    await publish_event(
        agent_id=agent_config.agent_id,
        event_type=EventType.SESSION_BOUNDARY,
        payload={
            "boundary_detected": True,
            "gap_minutes": gap.total_seconds() / 60,
            "message_count": len(messages),
            "session_id": new_session.id,
        },
    )
    logger.info("Published SESSION_BOUNDARY event for agent %s", agent_config.agent_id)

    # Enqueue summarization job with session_id instead of message_ids
    await queue.enqueue(
        "summarize_session",
        session_id=new_session.id,
        agent_id=agent_config.agent_id,
        letta_url=letta_url,
        archive_id=agent_config.archive_id,
        reflector_agent_id=agent_config.reflector_agent_id,
        timeout=300,  # 5 minutes for summarization
    )

    return {
        "status": "ok",
        "messages_found": len(messages),
        "session_complete": True,
        "summarization_enqueued": True,
        "session_id": new_session.id,
    }


async def check_session_boundaries(
    ctx: Context,
    *,
    agents: list[dict[str, Any]],
) -> dict[str, object]:
    """Check for completed sessions across all configured agents.

    Uses Redis distributed locking to prevent race conditions.

    Args:
        ctx: SAQ job context (contains queue reference for enqueueing).
        agents: List of agent configs, each with 'agent_id' and 'letta_url'.

    Returns:
        Status dict with detection results per agent.
    """
    if not agents:
        logger.warning("No agents configured, skipping session check")
        return {"status": "skipped", "reason": "no agents configured"}

    # Get queue from SAQ worker
    worker = ctx.get("worker")
    queue_obj = getattr(worker, "queue", None) if worker else None
    if not isinstance(queue_obj, Queue):
        logger.error("No queue in context (worker=%s)", worker)
        return {"status": "error", "reason": "no queue in context"}

    queue: Queue = queue_obj

    # Create Redis client for distributed locking
    redis_client = redis.from_url(Config.REDIS_URL.value)

    results: dict[str, object] = {}

    try:
        for agent_cfg in agents:
            agent_id = agent_cfg["agent_id"]
            letta_url = agent_cfg["letta_url"]

            try:
                result = await _check_agent_session(
                    queue=queue,
                    agent_id=agent_id,
                    letta_url=letta_url,
                    redis_client=redis_client,
                )
                results[agent_id] = result
            except Exception:
                logger.exception("Error checking session for agent %s", agent_id)
                results[agent_id] = {"status": "error", "reason": "exception"}
    finally:
        await redis_client.aclose()

    return {"status": "ok", "agents": results}

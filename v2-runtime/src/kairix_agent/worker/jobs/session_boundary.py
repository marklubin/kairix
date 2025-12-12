"""Session boundary detection job."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from saq import Queue

from kairix_agent.agent_config import get_agent_config
from kairix_agent.config import Config
from kairix_agent.events import EventType, publish_event
from kairix_agent.memory import LettaMemoryService

if TYPE_CHECKING:
    from saq.types import Context

logger = logging.getLogger(__name__)


async def _check_agent_session(
    queue: Queue,
    agent_id: str,
    letta_url: str,
) -> dict[str, object]:
    """Check session boundary for a single agent.

    Args:
        queue: SAQ queue for enqueueing summarization jobs.
        agent_id: The agent ID to check.
        letta_url: The Letta server URL.

    Returns:
        Status dict with detection results for this agent.
    """
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

    # Fetch all messages (no cursor needed - messages are reset after summarization)
    # Filter out system messages - only count user/assistant conversation
    all_messages = [
        message async for message in memory_service.get_messages_since(None)
    ]
    messages = [
        m for m in all_messages
        if m.message_type in ("user_message", "assistant_message")
    ]

    if not messages:
        logger.debug("No conversation messages for agent %s", agent_config.agent_id)
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

    # We have a completed session! Enqueue summarization
    logger.info(
        "Detected session boundary for agent %s: %d messages, gap %s",
        agent_config.agent_id,
        len(messages),
        gap,
    )

    # Extract message IDs for the session
    message_ids = [m.id for m in messages]
    first_message = messages[0]

    # Publish session boundary event
    await publish_event(
        agent_id=agent_config.agent_id,
        event_type=EventType.SESSION_BOUNDARY,
        payload={
            "boundary_detected": True,
            "gap_minutes": gap.total_seconds() / 60,
            "message_count": len(messages),
        },
    )
    logger.info("Published SESSION_BOUNDARY event for agent %s", agent_config.agent_id)

    # Enqueue summarization job with extended timeout (LLM calls can take a while)
    await queue.enqueue(
        "summarize_session",
        agent_id=agent_config.agent_id,
        letta_url=letta_url,
        archive_id=agent_config.archive_id,
        reflector_agent_id=agent_config.reflector_agent_id,
        message_ids=message_ids,
        period_start=first_message.date.isoformat(),
        period_end=last_message.date.isoformat(),
        timeout=300,  # 5 minutes for summarization
    )

    return {
        "status": "ok",
        "messages_found": len(messages),
        "session_complete": True,
        "summarization_enqueued": True,
    }


async def check_session_boundaries(
    ctx: Context,
    *,
    agents: list[dict[str, Any]],
) -> dict[str, object]:
    """Check for completed sessions across all configured agents.

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

    results: dict[str, object] = {}

    for agent_cfg in agents:
        agent_id = agent_cfg["agent_id"]
        letta_url = agent_cfg["letta_url"]

        try:
            result = await _check_agent_session(
                queue=queue,
                agent_id=agent_id,
                letta_url=letta_url,
            )
            results[agent_id] = result
        except Exception:
            logger.exception("Error checking session for agent %s", agent_id)
            results[agent_id] = {"status": "error", "reason": "exception"}

    return {"status": "ok", "agents": results}

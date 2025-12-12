"""Background insights job.

Periodically checks if an active conversation is happening and sends recent
messages to the background insights agent to evaluate/update the insights block.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from letta_client import AsyncLetta
from letta_client.types.agents import AssistantMessage

from kairix_agent.agent_config import get_agent_config
from kairix_agent.config import Config
from kairix_agent.events import EventType, publish_event
from kairix_agent.worker.jobs.transcript import format_transcript

if TYPE_CHECKING:
    from saq.types import Context

logger = logging.getLogger(__name__)

# Job name constant for enqueuing
TRIGGER_INSIGHTS_JOB = "trigger_insights"

RECENT_MESSAGE_COUNT = 10


async def _check_agent_insights(
        client: AsyncLetta,
        agent_id: str,
        insights_agent_id: str,
) -> dict[str, object]:
    """Check and potentially update insights for a single agent.

    Args:
        client: Letta client.
        agent_id: Conversational agent ID.
        insights_agent_id: Background insights agent ID.

    Returns:
        Status dict.
    """
    # Pull all messages and take last N (Letta API ignores order=desc)
    all_messages: list[Any] = [
        msg
        async for msg in client.agents.messages.list(
            agent_id=agent_id,
            order="asc",
            order_by="created_at",
        )
    ]

    if len(all_messages) > 1000:
        msg = f"Agent {agent_id} has {len(all_messages)} messages - need to implement proper pagination"
        raise RuntimeError(msg)

    # Take last N messages (most recent, in chronological order)
    messages = all_messages[-RECENT_MESSAGE_COUNT:] if all_messages else []

    if not messages:
        logger.info("No messages for agent %s, skipping insights check", agent_id)
        return {"status": "skipped", "reason": "no_messages"}

    # Debug: dump message IDs and timestamps
    logger.info(
        "Got %d messages for agent %s (from %d total):", len(messages), agent_id, len(all_messages)
    )
    for i, m in enumerate(messages[-5:]):
        logger.info("  [%d] %s | %s | %s", i, m.id, m.date, m.message_type)

    # Check if newest message is recent enough (within session gap)
    # messages[-1] is newest since we're in chronological order
    last_message = messages[-1]
    last_message_time = last_message.date
    now = datetime.now(tz=UTC)
    gap = now - last_message_time
    session_gap_minutes = Config.SESSION_GAP_MINUTES.value

    if gap >= timedelta(minutes=session_gap_minutes):
        logger.debug(
            "No active conversation for agent %s (gap: %s >= %s minutes), skipping",
            agent_id,
            gap,
            session_gap_minutes,
        )
        # Publish event with triggered=False (no active conversation)
        await publish_event(
            agent_id=agent_id,
            event_type=EventType.INSIGHTS_COMPLETE,
            payload={
                "triggered": False,
                "response": None,
            },
        )
        return {
            "status": "skipped",
            "reason": "no_active_conversation",
            "gap_seconds": gap.total_seconds(),
        }

    # Active conversation - messages already in chronological order
    conversation_text = format_transcript(messages)

    prompt = f"""Review the current conversation and determine if your background_insights block needs updating.

<recent_conversation>
{conversation_text}
</recent_conversation>

Your background_insights block is visible in your memory. Evaluate whether it supports this conversation:
1. If relevant: respond briefly acknowledging no update needed
2. If stale/irrelevant:
   - Search archival memory for relevant context
   - Optionally search the web for current information
   - Update the background_insights block using core_memory_replace

Remember: only update if truly necessary. Irrelevant updates add noise."""

    logger.info(
        "Sending %d messages to insights agent %s for evaluation", len(messages), insights_agent_id
    )

    response = await client.agents.messages.create(
        agent_id=insights_agent_id,
        input=prompt,
    )

    # Extract response text
    response_text = ""
    for msg in response.messages:
        if isinstance(msg, AssistantMessage) and msg.content:
            if isinstance(msg.content, str):
                response_text += msg.content
            else:
                for item in msg.content:
                    if hasattr(item, "text"):
                        response_text += item.text

    logger.info(
        "Insights agent response (%d chars): %s...",
        len(response_text),
        response_text[:100] if response_text else "(empty)",
    )

    # Reset insights agent to prevent context buildup
    await client.agents.messages.reset(agent_id=insights_agent_id)
    logger.debug("Reset insights agent %s message history", insights_agent_id)

    # Publish event for connected clients
    await publish_event(
        agent_id=agent_id,
        event_type=EventType.INSIGHTS_COMPLETE,
        payload={
            "triggered": True,
            "response": response_text,
        },
    )
    logger.info("Published INSIGHTS_COMPLETE event for agent %s", agent_id)

    return {
        "status": "ok",
        "messages_checked": len(messages),
        "response_length": len(response_text),
    }


async def check_insights_relevance(
        _ctx: Context,
        *,
        agents: list[dict[str, Any]],
) -> dict[str, object]:
    """Check if background insights need updating for monitored agents.

    This job runs every minute. For each agent:
    1. Pull last 10 messages
    2. If last message is older than SESSION_GAP_MINUTES, skip (no active conversation)
    3. Otherwise, send messages to insights agent for evaluation
    4. Reset insights agent after each run

    Args:
        _ctx: SAQ job context.
        agents: List of agent configs with agent_id and letta_url.

    Returns:
        Status dict with results per agent.
    """
    if not agents:
        logger.warning("No agents configured, skipping insights check")
        return {"status": "skipped", "reason": "no_agents_configured"}

    results: dict[str, object] = {}

    for agent_cfg in agents:
        agent_id = agent_cfg["agent_id"]
        letta_url = agent_cfg["letta_url"]

        try:
            # Load agent config to get insights_agent_id
            config = await get_agent_config(agent_id=agent_id, letta_url=letta_url)

            if not config.insights_agent_id:
                logger.debug("No insights agent configured for %s, skipping", agent_id)
                results[agent_id] = {"status": "skipped", "reason": "no_insights_agent"}
                continue

            client = AsyncLetta(base_url=letta_url)
            result = await _check_agent_insights(
                client=client,
                agent_id=agent_id,
                insights_agent_id=config.insights_agent_id,
            )
            results[agent_id] = result

        except Exception:
            logger.exception("Error checking insights for agent %s", agent_id)
            results[agent_id] = {"status": "error", "reason": "exception"}

    return {"status": "ok", "agents": results}


async def trigger_insights(
    _ctx: Context,
    *,
    agent_id: str,
    letta_url: str,
) -> dict[str, object]:
    """Trigger insights check for a single agent (on-demand).

    This job is enqueued after each LLM response to immediately check
    if insights need updating based on the conversation.

    Unlike check_insights_relevance (cron), this skips the session gap check
    since we know there's an active conversation.

    Args:
        _ctx: SAQ job context.
        agent_id: The conversational agent ID.
        letta_url: The Letta server URL.

    Returns:
        Status dict with results.
    """
    try:
        config = await get_agent_config(agent_id=agent_id, letta_url=letta_url)

        if not config.insights_agent_id:
            logger.debug("No insights agent configured for %s, skipping", agent_id)
            return {"status": "skipped", "reason": "no_insights_agent"}

        client = AsyncLetta(base_url=letta_url)

        # Use the internal helper but we'll inline a simplified version
        # that skips the session gap check (we know conversation is active)
        all_messages: list[Any] = [
            msg
            async for msg in client.agents.messages.list(
                agent_id=agent_id,
                order="asc",
                order_by="created_at",
            )
        ]

        if len(all_messages) > 1000:
            msg = f"Agent {agent_id} has {len(all_messages)} messages - need pagination"
            raise RuntimeError(msg)

        messages = all_messages[-RECENT_MESSAGE_COUNT:] if all_messages else []

        if not messages:
            logger.info("No messages for agent %s, skipping triggered insights", agent_id)
            return {"status": "skipped", "reason": "no_messages"}

        # Format and send to insights agent (skip session gap check)
        conversation_text = format_transcript(messages)

        prompt = f"""Review the current conversation and determine if your background_insights block needs updating.

<recent_conversation>
{conversation_text}
</recent_conversation>

Your background_insights block is visible in your memory. Evaluate whether it supports this conversation:
1. If relevant: respond briefly acknowledging no update needed
2. If stale/irrelevant:
   - Search archival memory for relevant context
   - Optionally search the web for current information
   - Update the background_insights block using core_memory_replace

Remember: only update if truly necessary. Irrelevant updates add noise."""

        logger.info(
            "Triggered insights: sending %d messages to insights agent %s",
            len(messages),
            config.insights_agent_id,
        )

        response = await client.agents.messages.create(
            agent_id=config.insights_agent_id,
            input=prompt,
        )

        response_text = ""
        for msg in response.messages:
            if isinstance(msg, AssistantMessage) and msg.content:
                if isinstance(msg.content, str):
                    response_text += msg.content
                else:
                    for item in msg.content:
                        if hasattr(item, "text"):
                            response_text += item.text

        logger.info(
            "Triggered insights response (%d chars): %s...",
            len(response_text),
            response_text[:100] if response_text else "(empty)",
        )

        # Reset insights agent
        await client.agents.messages.reset(agent_id=config.insights_agent_id)

        # Publish event
        await publish_event(
            agent_id=agent_id,
            event_type=EventType.INSIGHTS_COMPLETE,
            payload={
                "triggered": True,
                "response": response_text,
            },
        )

        return {
            "status": "ok",
            "messages_checked": len(messages),
            "response_length": len(response_text),
        }

    except Exception:
        logger.exception("Error in triggered insights for agent %s", agent_id)
        return {"status": "error", "reason": "exception"}

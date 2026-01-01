"""Background insights job.

Periodically checks if an active conversation is happening and uses
BlockManagerAgent (with DeepSeek + KP3 search tool) to update the insights block.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from letta_client import AsyncLetta

from kairix_agent.config import Config
from kairix_agent.events import EventType, emit_context_state, publish_event
from kairix_agent.llm import BlockManagerAgent
from kairix_agent.llm.configs import INSIGHTS_CONFIG
from kairix_agent.llm.tools import handle_search_kp3
from kairix_agent.worker.agents import get_all_agents
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
        letta_url: str,
) -> dict[str, object]:
    """Check and potentially update insights for a single agent.

    Uses BlockManagerAgent with DeepSeek + KP3 search tool.

    Args:
        client: Letta client.
        agent_id: Conversational agent ID.
        letta_url: Letta server URL (for context state emission).

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

    # Check if newest message is recent enough (within insights activity window)
    # messages[-1] is newest since we're in chronological order
    last_message = messages[-1]
    last_message_time = last_message.date
    now = datetime.now(tz=UTC)
    gap = now - last_message_time
    activity_minutes = Config.INSIGHTS_ACTIVITY_MINUTES.value

    if gap >= timedelta(minutes=activity_minutes):
        logger.debug(
            "No recent activity for agent %s (gap: %s >= %s minutes), skipping insights",
            agent_id,
            gap,
            activity_minutes,
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

    # Active conversation - format transcript
    conversation_text = format_transcript(messages)

    logger.info(
        "Running BlockManagerAgent insights for agent %s (%d messages)",
        agent_id,
        len(messages),
    )

    # Create insights agent with search tool (scoped to this agent)
    insights_agent = BlockManagerAgent(INSIGHTS_CONFIG)

    async def scoped_search(query: str, limit: int = 5) -> str:
        return await handle_search_kp3(query, limit, agent_id=agent_id)

    insights_agent.register_tool_handler("search_kp3", scoped_search)

    # Run - agent will call search_kp3 tool if it decides context is needed
    response_text = await insights_agent.run(
        input_text=conversation_text,
        agent_id=agent_id,
        letta_client=client,
        template_vars={"conversation": conversation_text},
    )

    logger.info(
        "Insights response (%d chars): %s...",
        len(response_text),
        response_text[:100] if response_text else "(empty)",
    )

    # Check if update was needed
    no_update = "NO_UPDATE_NEEDED" in response_text.upper()
    if no_update:
        logger.info("Insights agent determined no update needed for agent %s", agent_id)

    # Publish event for connected clients
    await publish_event(
        agent_id=agent_id,
        event_type=EventType.INSIGHTS_COMPLETE,
        payload={
            "triggered": True,
            "response": response_text,
            "updated": not no_update,
        },
    )
    logger.info("Published INSIGHTS_COMPLETE event for agent %s", agent_id)

    # Emit context state update (blocks may have changed)
    await emit_context_state(agent_id=agent_id, letta_url=letta_url)

    return {
        "status": "ok",
        "messages_checked": len(messages),
        "response_length": len(response_text),
        "updated": not no_update,
    }


async def check_insights_relevance(
        _ctx: Context,
        *,
        agents: list[dict[str, Any]] | None = None,
) -> dict[str, object]:
    """Check if background insights need updating for all agents.

    This job runs every minute. For each agent:
    1. Pull last 10 messages
    2. If last message is older than SESSION_GAP_MINUTES, skip (no active conversation)
    3. Otherwise, send messages to BlockManagerAgent for evaluation

    Args:
        _ctx: SAQ job context.
        agents: Optional list of agent configs. If None, fetches all agents from Letta.

    Returns:
        Status dict with results per agent.
    """
    # Fetch agents from Letta if not provided
    if not agents:
        agents = get_all_agents()

    if not agents:
        logger.warning("No agents found, skipping insights check")
        return {"status": "skipped", "reason": "no_agents_found"}

    results: dict[str, object] = {}

    for agent_cfg in agents:
        agent_id = agent_cfg["agent_id"]
        letta_url = agent_cfg["letta_url"]

        try:
            client = AsyncLetta(base_url=letta_url)
            result = await _check_agent_insights(
                client=client,
                agent_id=agent_id,
                letta_url=letta_url,
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

    Uses BlockManagerAgent with DeepSeek + KP3 search tool.

    Args:
        _ctx: SAQ job context.
        agent_id: The conversational agent ID.
        letta_url: The Letta server URL.

    Returns:
        Status dict with results.
    """
    try:
        client = AsyncLetta(base_url=letta_url)

        # Fetch recent messages (skip session gap check - we know conversation is active)
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

        # Format transcript
        conversation_text = format_transcript(messages)

        logger.info(
            "Triggered insights: sending %d messages to BlockManagerAgent",
            len(messages),
        )

        # Create insights agent with search tool (scoped to this agent)
        insights_agent = BlockManagerAgent(INSIGHTS_CONFIG)

        async def scoped_search(query: str, limit: int = 5) -> str:
            return await handle_search_kp3(query, limit, agent_id=agent_id)

        insights_agent.register_tool_handler("search_kp3", scoped_search)

        # Run - agent will call search_kp3 tool if it decides context is needed
        response_text = await insights_agent.run(
            input_text=conversation_text,
            agent_id=agent_id,
            letta_client=client,
            template_vars={"conversation": conversation_text},
        )

        logger.info(
            "Triggered insights response (%d chars): %s...",
            len(response_text),
            response_text[:100] if response_text else "(empty)",
        )

        # Check if update was needed
        no_update = "NO_UPDATE_NEEDED" in response_text.upper()
        if no_update:
            logger.info("Triggered insights determined no update needed for agent %s", agent_id)

        # Publish event
        await publish_event(
            agent_id=agent_id,
            event_type=EventType.INSIGHTS_COMPLETE,
            payload={
                "triggered": True,
                "response": response_text,
                "updated": not no_update,
            },
        )

        # Emit context state update (blocks may have changed)
        await emit_context_state(agent_id=agent_id, letta_url=letta_url)

        return {
            "status": "ok",
            "messages_checked": len(messages),
            "response_length": len(response_text),
            "updated": not no_update,
        }

    except Exception:
        logger.exception("Error in triggered insights for agent %s", agent_id)
        return {"status": "error", "reason": "exception"}

"""Session summarization job."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from letta_client import AsyncLetta
from letta_client.types.agents import AssistantMessage

from kairix_agent.events import EventType, publish_event
from kairix_agent.worker.jobs.transcript import format_transcript

if TYPE_CHECKING:
    from saq.types import Context

logger = logging.getLogger(__name__)


async def _format_session_for_reflector(
    client: AsyncLetta,
    agent_id: str,
    message_ids: list[str],
    period_start: str,
    period_end: str,
) -> str:
    """Format session messages into a prompt for the reflector agent.

    Args:
        client: Letta client.
        agent_id: The conversational agent ID.
        message_ids: List of message IDs in the session.
        period_start: ISO timestamp of session start.
        period_end: ISO timestamp of session end.

    Returns:
        Formatted prompt string for the reflector.
    """
    # Fetch messages and filter to those in this session
    message_id_set = set(message_ids)
    messages = [
        msg async for msg in client.agents.messages.list(agent_id)
        if msg.id in message_id_set
    ]

    session_transcript = format_transcript(messages)

    return f"""Please summarize the following conversation session.

Session Period: {period_start} to {period_end}
Message Count: {len(message_ids)}

<session_transcript>
{session_transcript}
</session_transcript>

Create a semantically rich summary that:
1. Captures the main topics, decisions, and insights
2. Notes any action items or commitments made
3. Identifies emotional tone and relationship dynamics
4. Includes specific details useful for future retrieval
5. Is written to maximize semantic searchability

Before writing your summary, search archival memory for related past sessions \
that might provide context."""


async def summarize_session(
    _ctx: Context,
    *,
    agent_id: str,
    letta_url: str,
    archive_id: str,
    reflector_agent_id: str | None,
    message_ids: list[str],
    period_start: str,
    period_end: str,
) -> dict[str, object]:
    """Summarize a completed session and store in archival memory.

    This job:
    1. Sends session transcript to reflector for summarization
    2. Resets the reflector agent's message history
    3. Stores the summary in the conversational agent's archival memory
    4. Updates the last_session_summary block
    5. Resets the conversational agent's message history

    Args:
        _ctx: SAQ job context.
        agent_id: The conversational Letta agent ID.
        letta_url: The Letta server URL.
        archive_id: The archive ID to store summaries in.
        reflector_agent_id: The reflector agent ID (or None if not provisioned).
        message_ids: List of message IDs in the session.
        period_start: ISO timestamp of first message.
        period_end: ISO timestamp of last message.

    Returns:
        Status dict with summarization results.
    """
    logger.info(
        "Summarizing session for agent %s: %d messages from %s to %s",
        agent_id,
        len(message_ids),
        period_start,
        period_end,
    )

    if not reflector_agent_id:
        logger.error("Cannot summarize: no reflector agent configured for %s", agent_id)
        return {
            "status": "error",
            "error": "reflector_not_configured",
            "agent_id": agent_id,
        }

    client = AsyncLetta(base_url=letta_url)

    # 1. Format session for reflector
    prompt = await _format_session_for_reflector(
        client, agent_id, message_ids, period_start, period_end
    )

    # 2. Send to reflector and get summary
    logger.info("Sending session to reflector %s for summarization", reflector_agent_id)
    response = await client.agents.messages.create(
        agent_id=reflector_agent_id,
        input=prompt,
    )

    # Extract summary from response - look for AssistantMessage with content
    summary_text = ""
    for msg in response.messages:
        if isinstance(msg, AssistantMessage) and msg.content:
            # content can be a string or list of content items
            if isinstance(msg.content, str):
                summary_text += msg.content
            else:
                # It's a list of content items, extract text from each
                for item in msg.content:
                    if hasattr(item, "text"):
                        summary_text += item.text

    if not summary_text:
        logger.warning("Reflector returned empty summary")
        return {
            "status": "error",
            "error": "empty_summary",
            "agent_id": agent_id,
        }

    logger.info("Received summary (%d chars) from reflector", len(summary_text))

    # 3. Reset the reflector agent to prevent context buildup
    await client.agents.messages.reset(agent_id=reflector_agent_id)
    logger.info("Reset reflector agent %s message history", reflector_agent_id)

    # 4. Store summary in archival memory
    await client.archives.passages.create(
        archive_id=archive_id,
        text=f"[Session Summary: {period_start} to {period_end}]\n\n{summary_text}",
    )
    logger.info("Stored summary in archival memory (archive %s)", archive_id)

    # 5. Update the last_session_summary block in the conversational agent's core memory
    # This keeps the summary in-window for continuity after reset
    try:
        await client.agents.blocks.update(
            "last_session_summary",
            agent_id=agent_id,
            value=f"[Session: {period_start} to {period_end}]\n\n{summary_text}",
        )
        logger.info("Updated last_session_summary block for agent %s", agent_id)
    except Exception:
        logger.exception("Failed to update last_session_summary block")

    # 6. Reset message history (Letta preserves the system message automatically)
    await client.agents.messages.reset(agent_id=agent_id)
    logger.info("Reset message history for agent %s (system message preserved)", agent_id)

    # 7. Publish event for connected clients
    await publish_event(
        agent_id=agent_id,
        event_type=EventType.SUMMARY_COMPLETE,
        payload={
            "message_count": len(message_ids),
            "summary": summary_text,
        },
    )
    logger.info("Published SUMMARY_COMPLETE event for agent %s", agent_id)

    return {
        "status": "ok",
        "agent_id": agent_id,
        "reflector_id": reflector_agent_id,
        "message_count": len(message_ids),
        "period_start": period_start,
        "period_end": period_end,
        "summary_length": len(summary_text),
        "summary_stored": True,
    }

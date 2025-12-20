"""Session summarization job."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from letta_client import AsyncLetta
from letta_client.types.agents import AssistantMessage

from kairix_agent.events import EventType, emit_context_state, publish_event
from kairix_agent.sessions import (
    SessionStatus,
    get_session,
    get_session_message_ids,
    update_session_status,
)
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
    session_id: str,
    agent_id: str,
    letta_url: str,
    archive_id: str,
    reflector_agent_id: str | None,
) -> dict[str, object]:
    """Summarize a completed session and store in archival memory.

    This job:
    1. Loads session info from our database
    2. Resets the reflector agent (clears stale context from failed jobs)
    3. Sends session transcript to reflector for summarization
    4. Resets the reflector agent again (defense in depth)
    5. Stores the summary in the conversational agent's archival memory
    6. Updates the last_session_summary block
    7. Resets the conversational agent's message history
    8. Updates session status in our database

    Args:
        _ctx: SAQ job context.
        session_id: Our session tracking ID.
        agent_id: The conversational Letta agent ID.
        letta_url: The Letta server URL.
        archive_id: The archive ID to store summaries in.
        reflector_agent_id: The reflector agent ID (or None if not provisioned).

    Returns:
        Status dict with summarization results.
    """
    # Load session from our database
    session = await get_session(session_id)
    if session is None:
        logger.error("Session %s not found in database", session_id)
        return {
            "status": "error",
            "error": "session_not_found",
            "session_id": session_id,
        }

    message_ids = await get_session_message_ids(session_id)
    period_start = session.period_start.isoformat()
    period_end = session.period_end.isoformat()

    logger.info(
        "Summarizing session %s for agent %s: %d messages from %s to %s",
        session_id,
        agent_id,
        len(message_ids),
        period_start,
        period_end,
    )

    if not reflector_agent_id:
        logger.error("Cannot summarize: no reflector agent configured for %s", agent_id)
        await update_session_status(
            session_id=session_id,
            status=SessionStatus.FAILED,
            error_message="reflector_not_configured",
        )
        return {
            "status": "error",
            "error": "reflector_not_configured",
            "agent_id": agent_id,
            "session_id": session_id,
        }

    client = AsyncLetta(base_url=letta_url)

    # 1. Reset reflector BEFORE summarization to ensure clean context
    # This prevents accumulation from failed previous jobs
    await client.agents.messages.reset(agent_id=reflector_agent_id)
    logger.info("Reset reflector agent %s before summarization", reflector_agent_id)

    # 2. Format session for reflector
    prompt = await _format_session_for_reflector(
        client, agent_id, message_ids, period_start, period_end
    )

    # 3. Send to reflector and get summary
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
        await update_session_status(
            session_id=session_id,
            status=SessionStatus.FAILED,
            error_message="empty_summary",
        )
        return {
            "status": "error",
            "error": "empty_summary",
            "agent_id": agent_id,
            "session_id": session_id,
        }

    logger.info("Received summary (%d chars) from reflector", len(summary_text))

    # 4. Reset the reflector agent after summarization (defense in depth)
    # The pre-summarization reset handles failed jobs; this handles successful ones
    await client.agents.messages.reset(agent_id=reflector_agent_id)
    logger.info("Reset reflector agent %s message history", reflector_agent_id)

    # 5. Store summary in archival memory
    passage = await client.archives.passages.create(
        archive_id=archive_id,
        text=f"[Session Summary: {period_start} to {period_end}]\n\n{summary_text}",
    )
    logger.info("Stored summary in archival memory (archive %s, passage %s)", archive_id, passage.id)

    # 6. Update the last_session_summary block in the conversational agent's core memory
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

    # 7. Reset message history (Letta preserves the system message automatically)
    await client.agents.messages.reset(agent_id=agent_id)
    logger.info("Reset message history for agent %s (system message preserved)", agent_id)

    # 8. Publish event for connected clients
    await publish_event(
        agent_id=agent_id,
        event_type=EventType.SUMMARY_COMPLETE,
        payload={
            "message_count": len(message_ids),
            "summary": summary_text,
        },
    )
    logger.info("Published SUMMARY_COMPLETE event for agent %s", agent_id)

    # 9. Emit context state update (blocks have changed)
    await emit_context_state(agent_id=agent_id, letta_url=letta_url)

    # 10. Update session status to summarized
    await update_session_status(
        session_id=session_id,
        status=SessionStatus.SUMMARIZED,
        summary_passage_id=passage.id,
        summarized_at=datetime.now(UTC),
    )
    logger.info("Updated session %s status to summarized", session_id)

    return {
        "status": "ok",
        "session_id": session_id,
        "agent_id": agent_id,
        "reflector_id": reflector_agent_id,
        "message_count": len(message_ids),
        "period_start": period_start,
        "period_end": period_end,
        "summary_length": len(summary_text),
        "summary_stored": True,
        "passage_id": passage.id,
    }

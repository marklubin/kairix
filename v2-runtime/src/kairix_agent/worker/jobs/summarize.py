"""Session summarization job."""

from __future__ import annotations

import json
import logging
import traceback
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import redis.asyncio as redis
from letta_client import AsyncLetta
from saq import Queue

from kairix_agent.config import Config
from kairix_agent.events import EventType, emit_context_state, publish_event
from kairix_agent.llm import BlockManagerAgent
from kairix_agent.llm.configs import SUMMARIZER_CONFIG
from kairix_agent.sessions import (
    SessionStatus,
    get_session,
    get_session_message_ids,
    update_session_status,
)
from kairix_agent.worker.jobs.step_memory import STEP_MEMORY_JOB
from kairix_agent.worker.jobs.transcript import format_transcript
from kairix_agent.worker.metrics import instrument_job, record_block_update
from kairix_agent.worker.retry import LLM_RETRY_CONFIG

if TYPE_CHECKING:
    from saq.types import Context

logger = logging.getLogger(__name__)

# Redis key for the summarization dead letter queue
SUMMARIZATION_DLQ_KEY = "kairix:dlq:summarization"


async def _push_to_dlq(
    session_id: str,
    agent_id: str,
    error: str,
    error_traceback: str,
    message_ids: list[str],
    period_start: str,
    period_end: str,
    prompt: str | None = None,
) -> None:
    """Push a failed summarization job to the dead letter queue.

    Args:
        session_id: The session ID that failed.
        agent_id: The agent ID.
        error: The error message.
        error_traceback: Full traceback string.
        message_ids: List of message IDs in the session.
        period_start: Session start timestamp.
        period_end: Session end timestamp.
        prompt: The formatted prompt that was sent to the reflector (if available).
    """
    try:
        redis_client = redis.from_url(Config.REDIS_URL.value)
        dlq_entry = {
            "session_id": session_id,
            "agent_id": agent_id,
            "error": error,
            "error_traceback": error_traceback,
            "message_ids": message_ids,
            "period_start": period_start,
            "period_end": period_end,
            "prompt": prompt,
            "failed_at": datetime.now(UTC).isoformat(),
        }
        await redis_client.lpush(SUMMARIZATION_DLQ_KEY, json.dumps(dlq_entry))  # type: ignore[misc]
        await redis_client.aclose()
        logger.info("Pushed failed session %s to DLQ", session_id)
    except Exception:
        logger.exception("Failed to push session %s to DLQ", session_id)


async def _format_session_transcript(
    client: AsyncLetta,
    agent_id: str,
    message_ids: list[str],
    period_start: str,
    period_end: str,
) -> str:
    """Format session messages into a transcript for summarization.

    Args:
        client: Letta client.
        agent_id: The conversational agent ID.
        message_ids: List of message IDs in the session.
        period_start: ISO timestamp of session start.
        period_end: ISO timestamp of session end.

    Returns:
        Formatted transcript string for the summarizer.
    """
    # Fetch messages and filter to those in this session
    message_id_set = set(message_ids)
    messages = [
        msg async for msg in client.agents.messages.list(agent_id) if msg.id in message_id_set
    ]

    session_transcript = format_transcript(messages)

    return f"""Session Period: {period_start} to {period_end}
Message Count: {len(message_ids)}

<session_transcript>
{session_transcript}
</session_transcript>"""


@instrument_job("summarize")
async def summarize_session(
    ctx: Context,
    *,
    session_id: str,
    agent_id: str,
    letta_url: str,
    archive_id: str,
) -> dict[str, object]:
    """Summarize a completed session and store in archival memory.

    This job:
    1. Loads session info from our database
    2. Formats session transcript
    3. Uses BlockManagerAgent to call DeepSeek for summarization
    4. BlockManagerAgent updates the last_session_summary block
    5. BlockManagerAgent stores summary to KP3 as session_summary passage
    6. Stores the summary in Letta archival memory for agent search
    7. Resets the conversational agent's message history
    8. Updates session status in our database

    Args:
        _ctx: SAQ job context.
        session_id: Our session tracking ID.
        agent_id: The conversational Letta agent ID.
        letta_url: The Letta server URL.
        archive_id: The archive ID to store summaries in.

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

    # Idempotency check: skip if already summarized or failed
    if session.status != SessionStatus.PENDING.value:
        logger.info(
            "Session %s already processed (status=%s), skipping",
            session_id,
            session.status,
        )
        return {
            "status": "skipped",
            "reason": "already_processed",
            "session_id": session_id,
            "session_status": session.status,
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

    # Track transcript for DLQ in case of failure
    transcript: str | None = None

    try:
        client = AsyncLetta(base_url=letta_url)

        # 1. Format session transcript
        transcript = await _format_session_transcript(
            client, agent_id, message_ids, period_start, period_end
        )

        # 2. Use BlockManagerAgent to summarize via DeepSeek
        # This will: call DeepSeek API, update the last_session_summary block, store to KP3
        summarizer = BlockManagerAgent(SUMMARIZER_CONFIG)
        summary_text = await summarizer.run(
            input_text=transcript,
            agent_id=agent_id,
            letta_client=client,
            template_vars={"transcript": transcript},
            metadata={
                "session_id": session_id,
                "period_start": period_start,
                "period_end": period_end,
            },
        )

        if not summary_text:
            logger.warning("Summarizer returned empty summary")
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

        logger.info("Received summary (%d chars) from DeepSeek", len(summary_text))

        # Record block update metric (BlockManagerAgent updated last_session_summary)
        record_block_update("last_session_summary", updated=True, agent_id=agent_id)

        # 3. Store summary in Letta archival memory (for conversational agent search)
        passage = await client.archives.passages.create(
            archive_id=archive_id,
            text=f"[Session Summary: {period_start} to {period_end}]\n\n{summary_text}",
        )
        logger.info(
            "Stored summary in archival memory (archive %s, passage %s)", archive_id, passage.id
        )

        # 4. Reset message history (Letta preserves the system message automatically)
        await client.agents.messages.reset(agent_id=agent_id)
        logger.info("Reset message history for agent %s (system message preserved)", agent_id)

        # 5. Publish event for connected clients
        await publish_event(
            agent_id=agent_id,
            event_type=EventType.SUMMARY_COMPLETE,
            payload={
                "message_count": len(message_ids),
                "summary": summary_text,
            },
        )
        logger.info("Published SUMMARY_COMPLETE event for agent %s", agent_id)

        # 6. Emit context state update (blocks have changed)
        await emit_context_state(agent_id=agent_id, letta_url=letta_url)

        # 7. Update session status to summarized
        await update_session_status(
            session_id=session_id,
            status=SessionStatus.SUMMARIZED,
            summary_passage_id=passage.id,
            summarized_at=datetime.now(UTC),
        )
        logger.info("Updated session %s status to summarized", session_id)

        # 8. Enqueue step job to update persona/human/world blocks
        # Step failures are independent - session is already summarized
        # Uses same retry strategy as summarization (exponential backoff)
        worker = ctx.get("worker")
        queue = getattr(worker, "queue", None) if worker else None
        if isinstance(queue, Queue):
            await queue.enqueue(
                STEP_MEMORY_JOB,
                agent_id=agent_id,
                letta_url=letta_url,
                session_summary=summary_text,
                period_start=period_start,
                period_end=period_end,
                timeout=300,  # 5 minutes (3 agents run in parallel)
                retries=LLM_RETRY_CONFIG.retries,
                retry_delay=LLM_RETRY_CONFIG.retry_delay,
                retry_backoff=LLM_RETRY_CONFIG.retry_backoff,
            )
            logger.info(
                "Enqueued %s job for agent %s (retries=%d, retry_delay=%.1fs)",
                STEP_MEMORY_JOB,
                agent_id,
                LLM_RETRY_CONFIG.retries,
                LLM_RETRY_CONFIG.retry_delay,
            )
        else:
            logger.warning("No queue available, skipping step_memory enqueue")

        return {
            "status": "ok",
            "session_id": session_id,
            "agent_id": agent_id,
            "message_count": len(message_ids),
            "period_start": period_start,
            "period_end": period_end,
            "summary_length": len(summary_text),
            "summary_stored": True,
            "passage_id": passage.id,
        }

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"

        # Check if this is the final attempt (SAQ will retry if attempts < retries)
        job = ctx.get("job")
        attempts = job.attempts if job else 0
        retries = job.retries if job else 0
        is_final_attempt = attempts >= retries

        if is_final_attempt:
            # Final attempt failed - mark session as failed and push to DLQ
            logger.exception(
                "Summarization failed permanently for session %s after %d attempts: %s",
                session_id,
                attempts + 1,
                error_msg,
            )

            await update_session_status(
                session_id=session_id,
                status=SessionStatus.FAILED,
                error_message=error_msg[:500],  # Truncate long errors
            )

            await _push_to_dlq(
                session_id=session_id,
                agent_id=agent_id,
                error=error_msg,
                error_traceback=traceback.format_exc(),
                message_ids=message_ids,
                period_start=period_start,
                period_end=period_end,
                prompt=transcript,
            )
        else:
            # Will be retried - just log
            logger.warning(
                "Summarization failed for session %s (attempt %d/%d), will retry: %s",
                session_id,
                attempts + 1,
                retries + 1,
                error_msg,
            )

        # Re-raise so SAQ handles retry/failure
        raise

"""Service layer for session tracking operations."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from kairix_agent.config import Config
from kairix_agent.sessions.models import Session, SessionMessage, SessionStatus

# Async engine and session factory (lazy initialized)
_engine = create_async_engine(Config.DATABASE_URL.value, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_latest_session_end(agent_id: str) -> datetime | None:
    """Get the period_end of the most recent SUMMARIZED session for an agent.

    Only considers successfully summarized sessions. Failed sessions are excluded
    so their messages can be re-processed in a future summarization attempt.

    Args:
        agent_id: The Letta agent ID.

    Returns:
        The period_end timestamp of the latest summarized session, or None if none exist.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(Session.period_end)
            .where(Session.agent_id == agent_id)
            .where(Session.status == SessionStatus.SUMMARIZED.value)
            .order_by(Session.period_end.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def get_pending_session_for_agent(agent_id: str) -> Session | None:
    """Check if there's a pending or failed session for an agent.

    Used to prevent duplicate session creation during race conditions.
    Also blocks re-creation when a session failed (manual intervention needed).

    Args:
        agent_id: The Letta agent ID.

    Returns:
        The pending/failed Session if one exists, None otherwise.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(Session)
            .where(Session.agent_id == agent_id)
            .where(Session.status.in_([SessionStatus.PENDING.value, SessionStatus.FAILED.value]))
            .order_by(Session.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def create_session(
    agent_id: str,
    message_ids: list[str],
    period_start: datetime,
    period_end: datetime,
) -> Session:
    """Create a new session with associated messages.

    Args:
        agent_id: The Letta agent ID.
        message_ids: List of Letta message IDs in this session.
        period_start: Timestamp of first message.
        period_end: Timestamp of last message.

    Returns:
        The created Session object.
    """
    async with _async_session() as db:
        # Create session
        new_session = Session(
            agent_id=agent_id,
            period_start=period_start,
            period_end=period_end,
            message_count=len(message_ids),
            status=SessionStatus.PENDING.value,
        )
        db.add(new_session)
        await db.flush()  # Get the session ID

        # Create message associations
        for msg_id in message_ids:
            db.add(SessionMessage(session_id=new_session.id, message_id=msg_id))

        await db.commit()
        await db.refresh(new_session)
        return new_session


async def get_session(session_id: str) -> Session | None:
    """Get a session by ID.

    Args:
        session_id: The session UUID.

    Returns:
        The Session object or None if not found.
    """
    async with _async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()


async def get_session_message_ids(session_id: str) -> list[str]:
    """Get all message IDs for a session.

    Args:
        session_id: The session UUID.

    Returns:
        List of Letta message IDs in this session.
    """
    async with _async_session() as db:
        result = await db.execute(
            select(SessionMessage.message_id).where(
                SessionMessage.session_id == session_id
            )
        )
        return list(result.scalars().all())


async def update_session_status(
    session_id: str,
    status: SessionStatus,
    summary_passage_id: str | None = None,
    error_message: str | None = None,
    summarized_at: datetime | None = None,
) -> Session | None:
    """Update session status after summarization attempt.

    Args:
        session_id: The session UUID.
        status: New status (summarized or failed).
        summary_passage_id: Letta passage ID if summarized successfully.
        error_message: Error message if failed.
        summarized_at: Timestamp of summarization completion.

    Returns:
        Updated Session object or None if not found.
    """
    async with _async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if session is None:
            return None

        session.status = status.value
        if summary_passage_id:
            session.summary_passage_id = summary_passage_id
        if error_message:
            session.error_message = error_message
        if summarized_at:
            session.summarized_at = summarized_at

        await db.commit()
        await db.refresh(session)
        return session

"""SQLAlchemy models for agent events."""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class EventType(str, Enum):
    """Types of background events emitted by worker jobs."""

    SESSION_BOUNDARY = "session_boundary"
    SUMMARY_COMPLETE = "summary_complete"
    INSIGHTS_COMPLETE = "insights_complete"


class AgentEvent(Base):
    """Persistent record of background events for an agent.

    Events are stored in Postgres (source of truth) and notifications
    are sent via Redis pub/sub for real-time streaming to clients.
    """

    __tablename__ = "agent_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)  # type: ignore[type-arg]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )

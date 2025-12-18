"""SQLAlchemy models for session tracking."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kairix_agent.events.models import Base


class SessionStatus(str, Enum):
    """Status of a session summarization."""

    PENDING = "pending"
    SUMMARIZED = "summarized"
    FAILED = "failed"


class Session(Base):
    """A completed conversation session.

    Tracks sessions that have been detected by the boundary detection job
    to prevent duplicate summarization.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    message_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(32), default=SessionStatus.PENDING.value
    )
    summary_passage_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    summarized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship to session_messages
    messages: Mapped[list["SessionMessage"]] = relationship(
        "SessionMessage",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class SessionMessage(Base):
    """Join table linking sessions to Letta message IDs."""

    __tablename__ = "session_messages"

    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    message_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
        index=True,
    )

    # Relationship back to session
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="messages",
    )

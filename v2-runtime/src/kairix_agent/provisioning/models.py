"""SQLAlchemy models for provisioning configuration."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from kairix_agent.events.models import Base


class AgentDefinition(Base):
    """Agent definition configuration by agent type.

    Stores configuration for each agent type (conversational, reflector,
    insights). All agents of a given type share the same definition.

    Currently stores system_prompt, but can be extended with additional
    agent attributes (model, tools, etc.) in the future.
    """

    __tablename__ = "agent_definitions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    agent_type: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=datetime.utcnow,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )
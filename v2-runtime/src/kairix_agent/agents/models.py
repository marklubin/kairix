"""SQLAlchemy model for unified agent configuration."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kairix_agent.events.models import Base


class Agent(Base):
    """Unified agent configuration table.

    This is the single source of truth for agent configuration. All agent
    settings are stored here, including LLM config, block schema, voice,
    and KP3/Letta integration state.
    """

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # Primary LLM Config (for Letta conversational agent)
    inference_model: Mapped[str] = mapped_column(String(256), nullable=False)
    inference_provider_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    embedding_model: Mapped[str] = mapped_column(
        String(256), nullable=False, default="openai/text-embedding-3-small"
    )
    context_window: Mapped[int] = mapped_column(Integer, nullable=False, default=25000)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=4096)
    enable_reasoner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_reasoning_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1024)

    # Background LLM Config (for BlockManagerAgent: summarizer, insights, etc.)
    background_llm_model: Mapped[str] = mapped_column(
        String(256), nullable=False, default="deepseek-chat"
    )
    background_llm_url: Mapped[str] = mapped_column(
        String(512), nullable=False, default="https://api.deepseek.com"
    )

    # Block Schema (JSONB - defines structure, not content)
    block_schema: Mapped[list[dict]] = mapped_column(  # type: ignore[type-arg]
        JSONB, nullable=False, default=list
    )

    # Tools
    tools: Mapped[list[str]] = mapped_column(
        ARRAY(String(128)), nullable=False, server_default="{}", default=list
    )
    include_base_tools: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Voice (FK to voices table)
    voice_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("voices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # KP3 Integration
    kp3_ref_prefix: Mapped[str | None] = mapped_column(String(128), nullable=True)
    kp3_hooks_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Letta Sync State
    letta_agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    letta_archive_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    letta_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    letta_sync_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=lambda: datetime.now(UTC),
        nullable=True,
    )

    # Relationships
    voice: Mapped["Voice | None"] = relationship("Voice")  # type: ignore[name-defined] # noqa: F821

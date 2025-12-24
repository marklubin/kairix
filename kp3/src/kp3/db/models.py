"""SQLAlchemy models for KP3."""

from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all models."""

    type_annotation_map: ClassVar[dict[type, type]] = {
        dict[str, Any]: JSONB,
    }


class Passage(Base):
    """A text passage with metadata and optional embeddings."""

    __tablename__ = "passages"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    content_tsv: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', content)", persisted=True),
        nullable=True,
    )

    passage_type: Mapped[str] = mapped_column(String(64), nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )

    # External source tracking
    source_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_external_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Embeddings (1024-dim, truncated from qwen3-embedding:4b)
    embedding_qwen3: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    derived_from: Mapped[list["PassageDerivation"]] = relationship(
        "PassageDerivation",
        foreign_keys="PassageDerivation.derived_passage_id",
        back_populates="derived_passage",
    )
    derives: Mapped[list["PassageDerivation"]] = relationship(
        "PassageDerivation",
        foreign_keys="PassageDerivation.source_passage_id",
        back_populates="source_passage",
    )

    __table_args__ = (
        Index("idx_passages_type", "passage_type"),
        Index("idx_passages_period", "period_start", "period_end"),
        Index("idx_passages_tsv", "content_tsv", postgresql_using="gin"),
        Index(
            "idx_passages_embedding",
            "embedding_qwen3",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding_qwen3": "vector_cosine_ops"},
        ),
    )


class PassageArchive(Base):
    """Archive of passage versions before in-place updates."""

    __tablename__ = "passages_archive"

    archive_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    archived_by_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("processing_runs.id"), nullable=True
    )

    # Snapshot of original passage data
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    passage_type: Mapped[str] = mapped_column(String(64), nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    source_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_external_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    embedding_qwen3: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    archived_by_run: Mapped["ProcessingRun | None"] = relationship(
        "ProcessingRun", back_populates="archived_passages"
    )

    __table_args__ = (
        Index("idx_archive_passage", "id"),
        Index("idx_archive_run", "archived_by_run_id"),
    )


class PassageDerivation(Base):
    """Links derived passages to their source passages."""

    __tablename__ = "passage_derivations"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    derived_passage_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("passages.id"), nullable=False
    )
    source_passage_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("passages.id"), nullable=False
    )
    processing_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("processing_runs.id"), nullable=False
    )
    source_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    derived_passage: Mapped[Passage] = relationship(
        "Passage", foreign_keys=[derived_passage_id], back_populates="derived_from"
    )
    source_passage: Mapped[Passage] = relationship(
        "Passage", foreign_keys=[source_passage_id], back_populates="derives"
    )
    processing_run: Mapped["ProcessingRun"] = relationship(
        "ProcessingRun", back_populates="derivations"
    )

    __table_args__ = (
        UniqueConstraint("derived_passage_id", "source_passage_id"),
        Index("idx_derivations_derived", "derived_passage_id"),
        Index("idx_derivations_source", "source_passage_id"),
        Index("idx_derivations_run", "processing_run_id"),
    )


class ProcessingRun(Base):
    """A processing run execution record."""

    __tablename__ = "processing_runs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )

    # Input query
    input_sql: Mapped[str] = mapped_column(Text, nullable=False)

    # Processor configuration
    processor_type: Mapped[str] = mapped_column(String(64), nullable=False)
    processor_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Execution state
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    total_groups: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processed_groups: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    derivations: Mapped[list[PassageDerivation]] = relationship(
        "PassageDerivation", back_populates="processing_run"
    )
    archived_passages: Mapped[list[PassageArchive]] = relationship(
        "PassageArchive", back_populates="archived_by_run"
    )

    __table_args__ = (Index("idx_runs_status", "status"),)


class PassageRef(Base):
    """Mutable pointer to a passage, analogous to git refs."""

    __tablename__ = "passage_refs"

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    passage_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("passages.id"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )

    # Relationships
    passage: Mapped[Passage] = relationship("Passage")

    __table_args__ = (Index("idx_passage_refs_passage_id", "passage_id"),)


class ExtractionPrompt(Base):
    """Versioned prompts for world model extraction."""

    __tablename__ = "extraction_prompts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    field_descriptions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_extraction_prompts_name_version"),
        Index("idx_extraction_prompts_name", "name"),
    )

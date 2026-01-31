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

    # Agent scoping - passages belong to a specific agent
    agent_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)

    # Embeddings (OpenAI text-embedding-3-large, 1024-dim)
    embedding_openai: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)

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
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="passage_tags",
        back_populates="passages",
    )

    __table_args__ = (
        Index("idx_passages_type", "passage_type"),
        Index("idx_passages_period", "period_start", "period_end"),
        Index("idx_passages_tsv", "content_tsv", postgresql_using="gin"),
        Index(
            "idx_passages_embedding_openai",
            "embedding_openai",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding_openai": "vector_cosine_ops"},
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
    embedding_openai: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
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


class PassageRefHistory(Base):
    """History of ref changes for auditing and time-travel queries."""

    __tablename__ = "passage_ref_history"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    ref_name: Mapped[str] = mapped_column(Text, nullable=False)
    passage_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("passages.id"), nullable=False
    )
    previous_passage_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("passages.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )

    # Relationships
    passage: Mapped[Passage] = relationship("Passage", foreign_keys=[passage_id])
    previous_passage: Mapped[Passage | None] = relationship(
        "Passage", foreign_keys=[previous_passage_id]
    )

    __table_args__ = (
        Index("idx_passage_ref_history_ref_name", "ref_name"),
        Index("idx_passage_ref_history_changed_at", "changed_at"),
    )


class PassageRefHook(Base):
    """Configurable hooks triggered on ref updates."""

    __tablename__ = "passage_ref_hooks"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    ref_name: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., "webhook"
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("idx_passage_ref_hooks_ref_name", "ref_name"),)


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


# =============================================================================
# World Model Shadow Tables
# =============================================================================
# These tables store normalized copies of world model entities for future use.
# The canonical source remains the JSON blocks in passages, but these tables
# enable efficient querying and future features like entity linking.
#
# Entity keys use canonical format:
#   - Lowercase
#   - Whitespace normalized (single spaces, trimmed)
#   - Stored in `canonical_key` column for dedup
#   - Original `name` preserved for display


class WorldModelProject(Base):
    """Shadow storage for project entities from world model."""

    __tablename__ = "world_model_projects"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    agent_id: Mapped[str] = mapped_column(Text, nullable=False)  # Agent ID for segmentation
    canonical_key: Mapped[str] = mapped_column(Text, nullable=False)  # Normalized for dedup
    name: Mapped[str] = mapped_column(Text, nullable=False)  # Original display name
    status: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    last_occurrence: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("agent_id", "canonical_key", name="uq_world_model_projects_agent_key"),
        Index("idx_world_model_projects_agent", "agent_id"),
        Index("idx_world_model_projects_last_occurrence", "last_occurrence"),
    )


class WorldModelEntity(Base):
    """Shadow storage for durable entities from world model."""

    __tablename__ = "world_model_entities"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    agent_id: Mapped[str] = mapped_column(Text, nullable=False)  # Agent ID for segmentation
    canonical_key: Mapped[str] = mapped_column(Text, nullable=False)  # Normalized for dedup
    name: Mapped[str] = mapped_column(Text, nullable=False)  # Original display name
    relevance: Mapped[str] = mapped_column(Text, nullable=False)
    last_occurrence: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("agent_id", "canonical_key", name="uq_world_model_entities_agent_key"),
        Index("idx_world_model_entities_agent", "agent_id"),
        Index("idx_world_model_entities_last_occurrence", "last_occurrence"),
    )


class WorldModelTheme(Base):
    """Shadow storage for recurring themes from world model."""

    __tablename__ = "world_model_themes"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    agent_id: Mapped[str] = mapped_column(Text, nullable=False)  # Agent ID for segmentation
    canonical_key: Mapped[str] = mapped_column(Text, nullable=False)  # Normalized for dedup
    name: Mapped[str] = mapped_column(Text, nullable=False)  # Original display name
    description: Mapped[str] = mapped_column(Text, nullable=False)
    last_occurrence: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("agent_id", "canonical_key", name="uq_world_model_themes_agent_key"),
        Index("idx_world_model_themes_agent", "agent_id"),
        Index("idx_world_model_themes_last_occurrence", "last_occurrence"),
    )


# =============================================================================
# World Model Branches
# =============================================================================
# Branches group the 3 refs (human/persona/world) as a single unit.
# They enable experimentation without firing hooks on production agents.


class WorldModelBranch(Base):
    """A branch grouping 3 world model refs (human, persona, world) as a unit.

    Branches allow running fold operations without firing hooks on production agents.
    The HEAD branch is the main/production branch with hooks enabled.
    Experiment branches can be created, folded against, and promoted to HEAD when ready.
    """

    __tablename__ = "world_model_branches"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )

    # Branch identity
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)  # e.g., "corindel/exp-1"
    ref_prefix: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., "corindel"
    branch_name: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., "exp-1" or "HEAD"

    # The 3 ref names this branch manages
    human_ref: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., "corindel/human/exp-1"
    persona_ref: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., "corindel/persona/exp-1"
    world_ref: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., "corindel/world/exp-1"

    # Lineage
    parent_branch_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("world_model_branches.id"), nullable=True
    )

    # Config
    is_main: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )  # True for HEAD branches
    hooks_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )  # Only True for main branches

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    parent_branch: Mapped["WorldModelBranch | None"] = relationship(
        "WorldModelBranch", remote_side=[id], back_populates="child_branches"
    )
    child_branches: Mapped[list["WorldModelBranch"]] = relationship(
        "WorldModelBranch", back_populates="parent_branch"
    )

    __table_args__ = (
        UniqueConstraint("ref_prefix", "branch_name", name="uq_world_model_branches_prefix_name"),
        Index("idx_world_model_branches_prefix", "ref_prefix"),
    )


# =============================================================================
# Tags
# =============================================================================
# Tags enable flexible categorization of passages with FTS and semantic search.


class Tag(Base):
    """A tag that can be attached to passages."""

    __tablename__ = "tags"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    agent_id: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_key: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    name_tsv: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', name || ' ' || coalesce(description, ''))",
            persisted=True,
        ),
        nullable=True,
    )
    embedding_openai: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    passage_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    passages: Mapped[list["Passage"]] = relationship(
        "Passage",
        secondary="passage_tags",
        back_populates="tags",
    )

    __table_args__ = (
        UniqueConstraint("agent_id", "canonical_key", name="uq_tags_agent_canonical_key"),
        Index("idx_tags_agent_id", "agent_id"),
        Index("idx_tags_name_tsv", "name_tsv", postgresql_using="gin"),
        Index(
            "idx_tags_embedding_openai",
            "embedding_openai",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding_openai": "vector_cosine_ops"},
        ),
    )


class PassageTag(Base):
    """Junction table linking passages to tags."""

    __tablename__ = "passage_tags"

    passage_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("passages.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_passage_tags_passage_id", "passage_id"),
        Index("idx_passage_tags_tag_id", "tag_id"),
    )


# =============================================================================
# Memory Scopes
# =============================================================================
# Scopes define dynamic search closures using refs and literal passage IDs.
# Scope definitions are stored as passages (type="scope_definition").


class MemoryScope(Base):
    """A memory scope defining a closure of passages for search.

    Scopes use refs infrastructure for versioning and history.
    The actual scope definition (refs + passage IDs) is stored as a passage
    with type="scope_definition", and the head_ref points to the current version.
    """

    __tablename__ = "memory_scopes"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    agent_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    head_ref: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("agent_id", "name", name="uq_memory_scopes_agent_name"),
        Index("idx_memory_scopes_agent_id", "agent_id"),
    )

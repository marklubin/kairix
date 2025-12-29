"""SQLAlchemy models for evaluation framework."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from kp3.db.models import Base


class EvalTestCase(Base):
    """A test case for agent evaluation.
    
    Test cases define:
    - Input state (memory blocks, prior messages)
    - The test prompt
    - Expected behavior and scoring criteria
    
    Test cases are reusable across eval runs.
    """

    __tablename__ = "eval_test_cases"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    
    # Identity
    name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # continuity, tone, memory
    
    # Input state - what the agent sees
    memory_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )  # {persona: "...", human: "...", world: "...", ...}
    prior_messages: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )  # Conversation history to prepend
    input_message: Mapped[str] = mapped_column(Text, nullable=False)  # The actual test prompt
    
    # Expected behavior
    expected_behavior: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Human description of what should happen
    eval_criteria: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )  # {auto: [...], human: [...]}
    
    # Optional gold response for comparison
    gold_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Metadata
    difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)  # easy/medium/hard
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    results: Mapped[list["EvalResult"]] = relationship("EvalResult", back_populates="test_case")

    __table_args__ = (
        Index("idx_eval_test_cases_category", "category"),
        Index("idx_eval_test_cases_tags", "tags", postgresql_using="gin"),
    )


class EvalRun(Base):
    """A run of evaluation against a set of test cases.
    
    Each run captures:
    - The system prompt being tested
    - Model configuration
    - Execution state and timing
    
    Runs are comparable to track progress over iterations.
    """

    __tablename__ = "eval_runs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    
    # What we're testing
    system_prompt_ref: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Points to passage ref if versioned
    system_prompt_text: Mapped[str] = mapped_column(Text, nullable=False)  # Snapshot of actual prompt
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )  # Other params (temp, max_tokens)
    
    # Filter for which test cases to run
    test_case_filter: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )  # {category: "continuity", tags: [...]}
    
    # Execution state
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending, running, completed, failed
    total_cases: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Aggregate scores (computed after run)
    aggregate_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    
    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    results: Mapped[list["EvalResult"]] = relationship("EvalResult", back_populates="run")

    __table_args__ = (
        Index("idx_eval_runs_status", "status"),
        Index("idx_eval_runs_created", "created_at"),
    )


class EvalResult(Base):
    """Result of running a single test case.
    
    Captures:
    - The actual agent output
    - Tool calls made
    - Automated and human scores
    - Embedding for later clustering/analysis
    """

    __tablename__ = "eval_results"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("eval_runs.id"), nullable=False
    )
    test_case_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("eval_test_cases.id"), nullable=False
    )
    
    # What happened
    raw_output: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    thinking: Mapped[str | None] = mapped_column(Text, nullable=True)  # If extended thinking enabled
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Automated scores (filled immediately)
    auto_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )  # {searched_when_should: 1, ...}
    
    # Human ratings (nullable, fill in later)
    human_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    human_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Composite score (computed from auto + human with weights)
    composite_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # For learning later - embed output for clustering
    output_embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    
    # Execution metadata
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    run: Mapped[EvalRun] = relationship("EvalRun", back_populates="results")
    test_case: Mapped[EvalTestCase] = relationship("EvalTestCase", back_populates="results")

    __table_args__ = (
        Index("idx_eval_results_run", "run_id"),
        Index("idx_eval_results_test_case", "test_case_id"),
        Index("idx_eval_results_composite_score", "composite_score"),
    )


class EvalScoreDimension(Base):
    """Defines what we're scoring and how.
    
    Dimensions are shared across test cases and provide:
    - Consistent scoring criteria
    - Weights for composite scoring
    - Category (objective vs subjective)
    """

    __tablename__ = "eval_score_dimensions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)  # "auto" or "human"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Scoring guidance
    score_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="binary"
    )  # binary, 1-5, 1-10
    rubric: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # Detailed scoring guide
    
    # For composite scoring
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("idx_eval_score_dimensions_category", "category"),)

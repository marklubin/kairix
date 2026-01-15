"""Pydantic schemas for cognitive memory API endpoints."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = [
    "CognitionConfig",
    "CognitionIncrementRequest",
    "CognitionIncrementResponse",
    "CognitionInputData",
    "CognitionProcessConfig",
    "DerivationDerivedResponse",
    "DerivationInfo",
    "DerivationSourceResponse",
    "EntityCreateRequest",
    "EntityCreateResponse",
    "FrameActivateResponse",
    "FrameCreateRequest",
    "FrameForkRequest",
    "FrameResolveResponse",
    "FrameResponse",
    "FrameScopedSearchRequest",
    "FrameScopedSearchResponse",
    "JudgeDecision",
    "PassageResponse",
    "PerceptionConfig",
    "RefHistoryEntry",
    "RefHistoryResponse",
    "RefListResponse",
    "RefResponse",
    "RefUpdateInfo",
    "RefUpdateRequest",
    "RefUpdateResponse",
    "RefWithPassageResponse",
]


# =============================================================================
# Ref Schemas
# =============================================================================


class RefResponse(BaseModel):
    """Response for GET /refs/{name} endpoint."""

    name: str
    passage_id: UUID
    version: int = Field(description="Version number for optimistic locking")
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class RefWithPassageResponse(BaseModel):
    """Response for GET /refs/{name} with resolved passage content."""

    name: str
    passage_id: UUID
    version: int
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    passage_content: str | None = Field(
        default=None, description="Resolved passage content if requested"
    )
    passage_type: str | None = None


class RefUpdateRequest(BaseModel):
    """Request body for PUT /refs/{name} endpoint."""

    passage_id: UUID
    expected_version: int | None = Field(
        default=None,
        description=(
            "Expected current version for optimistic locking. "
            "If provided, update fails with 409 if mismatch."
        ),
    )
    metadata: dict[str, Any] | None = None


class RefUpdateResponse(BaseModel):
    """Response from PUT /refs/{name} endpoint."""

    name: str
    passage_id: UUID
    version: int
    updated_at: datetime
    previous_passage_id: UUID | None = None


class RefHistoryEntry(BaseModel):
    """A single entry in ref history."""

    id: UUID
    ref_name: str
    passage_id: UUID
    previous_passage_id: UUID | None
    changed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class RefHistoryResponse(BaseModel):
    """Response from GET /refs/{name}/history endpoint."""

    ref_name: str
    entries: list[RefHistoryEntry]
    count: int


class RefListResponse(BaseModel):
    """Response from GET /refs endpoint."""

    refs: list[RefResponse]
    count: int


# =============================================================================
# Derivation Schemas
# =============================================================================


class DerivationSourceResponse(BaseModel):
    """Response for GET /passages/{id}/sources endpoint."""

    passage_id: UUID
    sources: list[UUID]
    count: int


class DerivationDerivedResponse(BaseModel):
    """Response for GET /passages/{id}/derived endpoint."""

    passage_id: UUID
    derived: list[UUID]
    count: int


# =============================================================================
# Cognitive Frame Schemas
# =============================================================================


class PerceptionConfig(BaseModel):
    """Configuration for a single perception within a frame."""

    name: str = Field(description="Perception name (e.g., 'persona', 'human', 'world')")
    ref: str = Field(description="Full ref path (e.g., 'test-agent/perception/persona')")
    process: str = Field(description="Process step ID for updates")


class CognitionProcessConfig(BaseModel):
    """Configuration for a cognition process."""

    prompt: str = Field(description="Prompt name or ID")
    trigger: str = Field(description="Trigger event (e.g., 'session_end', 'manual')")


class CognitionConfig(BaseModel):
    """Configuration for cognition processing."""

    llm_provider: str = Field(default="openai")
    model: str = Field(default="gpt-4o")
    processes: dict[str, CognitionProcessConfig] = Field(default_factory=dict)


class FrameCreateRequest(BaseModel):
    """Request body for POST /frames endpoint."""

    name: str = Field(description="Frame name (e.g., 'production', 'experiment-1')")
    agent_id: str = Field(description="Agent ID this frame belongs to")
    perceptions: list[PerceptionConfig] = Field(
        description="List of perceptions managed by this frame"
    )
    cognition_config: CognitionConfig = Field(default_factory=CognitionConfig)
    hooks_enabled: bool = Field(default=True, description="Whether hooks fire on ref updates")


class FrameResponse(BaseModel):
    """Response for frame endpoints."""

    id: UUID
    name: str
    agent_id: str
    ref_name: str = Field(description="Full ref name pointing to this frame")
    perceptions: list[PerceptionConfig]
    cognition_config: CognitionConfig
    hooks_enabled: bool
    created_at: datetime


class FrameForkRequest(BaseModel):
    """Request body for POST /frames/{name}/fork endpoint."""

    new_name: str = Field(description="Name for the forked frame")
    hooks_enabled: bool = Field(
        default=False, description="Whether hooks fire on the new frame"
    )


class FrameActivateResponse(BaseModel):
    """Response from POST /frames/{name}/activate endpoint."""

    frame_ref: str
    activated_at: datetime


class FrameResolveResponse(BaseModel):
    """Response from POST /frames/{name}/resolve endpoint.

    Returns a frozen snapshot with pinned passage IDs.
    """

    frame_name: str
    agent_id: str
    resolved_at: datetime
    pinned_refs: dict[str, UUID] = Field(
        description="Map of ref name to pinned passage ID at resolution time"
    )


# =============================================================================
# Cognition Increment Schemas
# =============================================================================


class CognitionInputData(BaseModel):
    """Input data for cognition increment."""

    content: str
    content_type: str = Field(default="text/plain")
    metadata: dict[str, Any] = Field(default_factory=dict)


class CognitionIncrementRequest(BaseModel):
    """Request body for POST /cognition/increment endpoint."""

    agent_id: str

    frame_ref: str = Field(description="Ref to the cognitive frame to use")
    frame_snapshot_mode: Literal["live", "frozen"] = Field(
        default="live",
        description="'live' resolves refs at read time, 'frozen' uses pinned passage IDs",
    )

    perception_ref: str = Field(description="Ref to the perception being updated")

    input: CognitionInputData = Field(description="Input data to process")

    context_refs: list[str] = Field(
        default_factory=list, description="Additional refs to include as context"
    )

    process_step_id: str = Field(description="ID of the cognition process step to run")
    llm_config: dict[str, Any] = Field(default_factory=dict)

    expected_previous_passage_id: UUID | None = Field(
        default=None,
        description="For optimistic locking: expected current passage ID. 409 on mismatch.",
    )

    idempotency_key: str | None = Field(
        default=None,
        description="Idempotency key to prevent duplicate processing",
    )


class DerivationInfo(BaseModel):
    """Information about the derivation created."""

    derived_passage_id: UUID
    source_passage_ids: list[UUID]
    context_passage_ids: list[UUID]
    process_step_id: str


class RefUpdateInfo(BaseModel):
    """Information about the ref update."""

    applied: bool
    new_ref_version: int


class CognitionIncrementResponse(BaseModel):
    """Response from POST /cognition/increment endpoint."""

    ok: bool
    perception_ref: str
    previous_passage_id: UUID | None
    new_passage_id: UUID

    derivation: DerivationInfo
    ref_update: RefUpdateInfo

    trace_id: str | None = None


# =============================================================================
# Entity Dedupe Schemas
# =============================================================================


class EntityCreateRequest(BaseModel):
    """Request for creating/getting a canonical entity."""

    agent_id: str
    entity_name: str
    entity_type: str = Field(default="entity", description="Entity namespace/type")
    metadata: dict[str, Any] = Field(default_factory=dict)


class JudgeDecision(BaseModel):
    """LLM judge decision for entity deduplication."""

    decision: Literal["DUPLICATE", "NOT_DUPLICATE", "UNSURE"]
    canonical_ref: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)


class EntityCreateResponse(BaseModel):
    """Response from entity creation."""

    ref_name: str
    passage_id: UUID
    is_new: bool = Field(description="True if a new canonical entity was created")
    judge_decision: JudgeDecision | None = None


# =============================================================================
# Search Schemas
# =============================================================================


class FrameScopedSearchRequest(BaseModel):
    """Request for frame-scoped search."""

    query: str
    frame_ref: str
    mode: Literal["fts", "semantic", "hybrid"] = Field(default="hybrid")
    limit: int = Field(default=10, ge=1, le=100)


class FrameScopedSearchResponse(BaseModel):
    """Response from frame-scoped search."""

    query: str
    frame_ref: str
    mode: str
    results: list[dict[str, Any]]
    count: int


# =============================================================================
# Passage Schemas (extended)
# =============================================================================


class PassageResponse(BaseModel):
    """Full passage response."""

    id: UUID
    content: str
    content_hash: str
    passage_type: str
    agent_id: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

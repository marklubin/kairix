"""Pydantic schemas for Memory Scopes API.

Scopes define dynamic search closures using refs and literal passage IDs.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from kp3.schemas.api import PassageResult


class ScopeDefinition(BaseModel):
    """Defines a closure of passages.

    This is stored as the content of a passage with type="scope_definition".
    """

    refs: list[str] = Field(
        default_factory=lambda: list[str](), description="Ref names to resolve to passage IDs"
    )
    passages: list[UUID] = Field(
        default_factory=lambda: list[UUID](), description="Literal passage IDs"
    )
    version: int = Field(default=1, description="Increments on each update")
    created_from: UUID | None = Field(
        default=None, description="Previous definition passage ID (for lineage)"
    )


# =============================================================================
# Request schemas
# =============================================================================


class MemoryScopeCreate(BaseModel):
    """Request body for POST /scopes endpoint."""

    name: str = Field(min_length=1, max_length=256, description="Scope name")
    description: str | None = Field(
        default=None, max_length=1024, description="Optional description"
    )


class ScopedPassageCreate(BaseModel):
    """Request body for POST /scopes/{name}/passages endpoint."""

    content: str = Field(min_length=1, description="Passage content")
    passage_type: str = Field(min_length=1, description="Passage type")
    metadata: dict[str, object] | None = Field(default=None, description="Optional metadata")
    period_start: datetime | None = Field(default=None, description="Period start timestamp")
    period_end: datetime | None = Field(default=None, description="Period end timestamp")


class ScopeAddRequest(BaseModel):
    """Request body for POST /scopes/{name}/add endpoint."""

    passage_ids: list[UUID] = Field(
        default_factory=lambda: list[UUID](), description="Passage IDs to add"
    )
    refs: list[str] = Field(default_factory=lambda: list[str](), description="Ref names to add")


class ScopeRemoveRequest(BaseModel):
    """Request body for POST /scopes/{name}/remove endpoint."""

    passage_ids: list[UUID] = Field(
        default_factory=lambda: list[UUID](), description="Passage IDs to remove"
    )
    refs: list[str] = Field(default_factory=lambda: list[str](), description="Ref names to remove")


class ScopeRevertRequest(BaseModel):
    """Request body for POST /scopes/{name}/revert endpoint."""

    to_version: int = Field(ge=1, description="Version number to revert to")


# =============================================================================
# Response schemas
# =============================================================================


class MemoryScopeResponse(BaseModel):
    """Response for scope endpoints."""

    id: UUID
    name: str
    agent_id: str
    head_ref: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class MemoryScopeListResponse(BaseModel):
    """Response from GET /scopes endpoint."""

    scopes: list[MemoryScopeResponse]
    count: int


class ScopedPassageCreateResponse(BaseModel):
    """Response from POST /scopes/{name}/passages endpoint."""

    passage_id: UUID
    content: str
    passage_type: str
    scope_version: int


class ScopeModifyResponse(BaseModel):
    """Response from POST /scopes/{name}/add or /scopes/{name}/remove endpoints."""

    scope_version: int
    modified_count: int


class ScopeRevertResponse(BaseModel):
    """Response from POST /scopes/{name}/revert endpoint."""

    scope_version: int
    reverted_from: int


class ScopeHistoryEntry(BaseModel):
    """A single entry in scope history."""

    version: int
    changed_at: datetime
    passage_id: UUID


class ScopeHistoryResponse(BaseModel):
    """Response from GET /scopes/{name}/history endpoint."""

    history: list[ScopeHistoryEntry]
    count: int


class ScopedSearchResponse(BaseModel):
    """Response from GET /scopes/{name}/search endpoint."""

    query: str
    mode: str
    search_type: str
    results: list[PassageResult]
    count: int
    scope: str
    scope_version: int

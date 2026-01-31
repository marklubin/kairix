"""Pydantic schemas for KP3 API.

These types define the API request/response models for the KP3 service.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# Search mode type
SearchMode = Literal["fts", "semantic", "hybrid"]

# Search type - content search vs tag search
SearchType = Literal["content", "tags"]


class PromptResponse(BaseModel):
    """Response from GET /prompts/{name} endpoint.

    Contains the active extraction prompt for a given name.
    """

    id: str
    name: str
    version: int
    system_prompt: str
    user_prompt_template: str
    field_descriptions: dict[str, Any]


class PassageResult(BaseModel):
    """A single passage in search results."""

    id: UUID
    content: str
    passage_type: str
    score: float = Field(description="Relevance score (higher is better)")


class SearchResponse(BaseModel):
    """Response from GET /passages/search endpoint."""

    query: str
    mode: str
    search_type: str = Field(default="content", description="Search type: content or tags")
    results: list[PassageResult]
    count: int = Field(description="Number of results returned")


class PassageCreate(BaseModel):
    """Request body for POST /passages endpoint."""

    content: str
    passage_type: str
    metadata: dict[str, Any] | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None


class PassageCreateResponse(BaseModel):
    """Response from POST /passages endpoint."""

    id: UUID
    content: str
    passage_type: str


# =============================================================================
# Tag schemas
# =============================================================================


class TagCreate(BaseModel):
    """Request body for POST /tags endpoint."""

    name: str = Field(min_length=1, max_length=256, description="Tag display name")
    description: str | None = Field(
        default=None, max_length=1024, description="Optional description"
    )


class TagResponse(BaseModel):
    """Response for tag endpoints."""

    id: UUID
    name: str
    description: str | None
    passage_count: int
    created_at: datetime
    updated_at: datetime


class TagListResponse(BaseModel):
    """Response from GET /tags endpoint."""

    tags: list[TagResponse]
    count: int


class PassageTagsRequest(BaseModel):
    """Request body for attaching/detaching tags to/from passages."""

    tag_ids: list[UUID] = Field(min_length=1, description="List of tag UUIDs")


class PassageTagsResponse(BaseModel):
    """Response for passage tags endpoints."""

    passage_id: UUID
    tags: list[TagResponse]

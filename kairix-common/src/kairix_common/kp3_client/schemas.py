"""Pydantic schemas for KP3 API responses.

These types define the client-side view of KP3 API responses,
used by consumers like v2-runtime when calling KP3 endpoints.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# Search mode type
SearchMode = Literal["fts", "semantic", "hybrid"]


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

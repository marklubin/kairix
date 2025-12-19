"""Pydantic models for query service API."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PassageResult(BaseModel):
    """A single passage in search results."""

    id: UUID
    content: str
    passage_type: str
    score: float = Field(description="Relevance score (higher is better)")


class SearchRequest(BaseModel):
    """Search request parameters."""

    query: str = Field(min_length=1, description="Search query text")
    mode: Literal["fts", "semantic", "hybrid"] = Field(
        default="hybrid",
        description="Search mode: fts (full-text), semantic (vector), or hybrid (RRF fusion)",
    )
    limit: int = Field(default=5, ge=1, le=50, description="Maximum results to return")


class SearchResponse(BaseModel):
    """Search response with results."""

    query: str
    mode: str
    results: list[PassageResult]
    count: int = Field(description="Number of results returned")

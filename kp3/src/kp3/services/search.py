"""Passage search service supporting FTS, semantic, and hybrid search."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.config import get_settings
from kp3.processors.embedding import generate_embedding

# Search mode type - single source of truth
SearchMode = Literal["fts", "semantic", "hybrid"]

# Passage types that are searchable (opt-in)
SEARCHABLE_PASSAGE_TYPES = {"memory_shard", "session_summary"}


class PassageSearchResult(BaseModel):
    """A single passage search result."""

    id: UUID
    content: str
    passage_type: str
    score: float


async def search_passages(
    session: AsyncSession,
    query: str,
    *,
    mode: SearchMode = "hybrid",
    limit: int = 5,
    agent_id: str,
) -> list[PassageSearchResult]:
    """Search passages using FTS, semantic, or hybrid search.

    Args:
        session: Database session
        query: Search query text
        mode: Search mode - "fts" (full-text), "semantic" (vector), or "hybrid" (RRF fusion)
        limit: Maximum number of results to return
        agent_id: Agent ID to scope results (required)

    Returns:
        List of passage search results ordered by relevance score

    Raises:
        ValueError: If agent_id is empty
    """
    if not agent_id:
        raise ValueError("agent_id is required for search")

    if mode == "fts":
        return await _search_fts(session, query, limit, agent_id)
    elif mode == "semantic":
        return await _search_semantic(session, query, limit, agent_id)
    else:  # hybrid
        return await _search_hybrid(session, query, limit, agent_id)


async def _search_fts(
    session: AsyncSession,
    query: str,
    limit: int,
    agent_id: str,
) -> list[PassageSearchResult]:
    """Full-text search using PostgreSQL tsvector."""
    sql = text("""
        SELECT id, content, passage_type,
               ts_rank(content_tsv, websearch_to_tsquery('english', :query)) as score
        FROM passages
        WHERE content_tsv @@ websearch_to_tsquery('english', :query)
          AND passage_type = ANY(:searchable_types)
          AND agent_id = :agent_id
        ORDER BY score DESC
        LIMIT :limit
    """)
    params: dict[str, object] = {
        "query": query,
        "limit": limit,
        "searchable_types": list(SEARCHABLE_PASSAGE_TYPES),
        "agent_id": agent_id,
    }
    result = await session.execute(sql, params)
    rows = result.fetchall()

    return [
        PassageSearchResult(
            id=row.id,
            content=row.content,
            passage_type=row.passage_type,
            score=float(row.score),
        )
        for row in rows
    ]


async def _search_semantic(
    session: AsyncSession,
    query: str,
    limit: int,
    agent_id: str,
) -> list[PassageSearchResult]:
    """Semantic search using vector similarity."""
    query_embedding = await generate_embedding(query)
    sql = text("""
        WITH query_vec AS (
            SELECT cast(:embedding as vector) as vec
        ),
        scored AS (
            SELECT p.id, p.content, p.passage_type,
                   1 - (p.embedding_qwen3 <=> q.vec) as score
            FROM passages p, query_vec q
            WHERE p.embedding_qwen3 IS NOT NULL
              AND p.passage_type = ANY(:searchable_types)
              AND p.agent_id = :agent_id
        )
        SELECT * FROM scored ORDER BY score DESC LIMIT :limit
    """)
    params: dict[str, object] = {
        "embedding": str(query_embedding),
        "limit": limit,
        "searchable_types": list(SEARCHABLE_PASSAGE_TYPES),
        "agent_id": agent_id,
    }
    result = await session.execute(sql, params)
    rows = result.fetchall()

    return [
        PassageSearchResult(
            id=row.id,
            content=row.content,
            passage_type=row.passage_type,
            score=float(row.score),
        )
        for row in rows
    ]


async def _search_hybrid(
    session: AsyncSession,
    query: str,
    limit: int,
    agent_id: str,
) -> list[PassageSearchResult]:
    """Hybrid search combining FTS, semantic, and recency with Reciprocal Rank Fusion.

    RRF weights are configurable via environment variables:
    - KP3_RRF_WEIGHT_FTS (default: 1.0)
    - KP3_RRF_WEIGHT_SEMANTIC (default: 1.0)
    - KP3_RRF_WEIGHT_RECENCY (default: 0.5)
    """
    settings = get_settings()
    query_embedding = await generate_embedding(query)
    sql = text("""
        WITH query_vec AS (
            SELECT cast(:embedding as vector) as vec
        ),
        fts AS (
            SELECT id,
                   row_number() OVER (
                       ORDER BY ts_rank(content_tsv, websearch_to_tsquery('english', :query)) DESC
                   ) as rank
            FROM passages
            WHERE content_tsv @@ websearch_to_tsquery('english', :query)
              AND passage_type = ANY(:searchable_types)
              AND agent_id = :agent_id
        ),
        semantic AS (
            SELECT p.id, row_number() OVER (ORDER BY p.embedding_qwen3 <=> q.vec) as rank
            FROM passages p, query_vec q
            WHERE p.embedding_qwen3 IS NOT NULL
              AND p.passage_type = ANY(:searchable_types)
              AND p.agent_id = :agent_id
        ),
        recency AS (
            SELECT id, row_number() OVER (ORDER BY created_at DESC) as rank
            FROM passages
            WHERE passage_type = ANY(:searchable_types)
              AND agent_id = :agent_id
        )
        SELECT p.id, p.content, p.passage_type,
               :w_fts * COALESCE(1.0 / (60 + fts.rank), 0) +
               :w_semantic * COALESCE(1.0 / (60 + semantic.rank), 0) +
               :w_recency * COALESCE(1.0 / (60 + recency.rank), 0) as score
        FROM passages p
        LEFT JOIN fts ON p.id = fts.id
        LEFT JOIN semantic ON p.id = semantic.id
        LEFT JOIN recency ON p.id = recency.id
        WHERE (fts.id IS NOT NULL OR semantic.id IS NOT NULL)
          AND p.passage_type = ANY(:searchable_types)
          AND p.agent_id = :agent_id
        ORDER BY score DESC
        LIMIT :limit
    """)
    params: dict[str, object] = {
        "query": query,
        "embedding": str(query_embedding),
        "limit": limit,
        "searchable_types": list(SEARCHABLE_PASSAGE_TYPES),
        "agent_id": agent_id,
        "w_fts": settings.rrf_weight_fts,
        "w_semantic": settings.rrf_weight_semantic,
        "w_recency": settings.rrf_weight_recency,
    }
    result = await session.execute(sql, params)
    rows = result.fetchall()

    return [
        PassageSearchResult(
            id=row.id,
            content=row.content,
            passage_type=row.passage_type,
            score=float(row.score),
        )
        for row in rows
    ]

"""Passage search service supporting FTS, semantic, and hybrid search."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.processors.embedding import generate_embedding

# Search mode type - single source of truth
SearchMode = Literal["fts", "semantic", "hybrid"]


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
) -> list[PassageSearchResult]:
    """Search passages using FTS, semantic, or hybrid search.

    Args:
        session: Database session
        query: Search query text
        mode: Search mode - "fts" (full-text), "semantic" (vector), or "hybrid" (RRF fusion)
        limit: Maximum number of results to return

    Returns:
        List of passage search results ordered by relevance score
    """
    if mode == "fts":
        return await _search_fts(session, query, limit)
    elif mode == "semantic":
        return await _search_semantic(session, query, limit)
    else:  # hybrid
        return await _search_hybrid(session, query, limit)


async def _search_fts(
    session: AsyncSession,
    query: str,
    limit: int,
) -> list[PassageSearchResult]:
    """Full-text search using PostgreSQL tsvector."""
    sql = text("""
        SELECT id, content, passage_type,
               ts_rank(content_tsv, websearch_to_tsquery('english', :query)) as score
        FROM passages
        WHERE content_tsv @@ websearch_to_tsquery('english', :query)
          AND passage_type NOT LIKE 'state:%'
        ORDER BY score DESC
        LIMIT :limit
    """)
    result = await session.execute(sql, {"query": query, "limit": limit})
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
              AND p.passage_type NOT LIKE 'state:%'
        )
        SELECT * FROM scored ORDER BY score DESC LIMIT :limit
    """)
    result = await session.execute(sql, {"embedding": str(query_embedding), "limit": limit})
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
) -> list[PassageSearchResult]:
    """Hybrid search combining FTS and semantic with Reciprocal Rank Fusion."""
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
              AND passage_type NOT LIKE 'state:%'
        ),
        semantic AS (
            SELECT p.id, row_number() OVER (ORDER BY p.embedding_qwen3 <=> q.vec) as rank
            FROM passages p, query_vec q
            WHERE p.embedding_qwen3 IS NOT NULL
              AND p.passage_type NOT LIKE 'state:%'
        )
        SELECT p.id, p.content, p.passage_type,
               COALESCE(1.0 / (60 + fts.rank), 0) +
               COALESCE(1.0 / (60 + semantic.rank), 0) as score
        FROM passages p
        LEFT JOIN fts ON p.id = fts.id
        LEFT JOIN semantic ON p.id = semantic.id
        WHERE (fts.id IS NOT NULL OR semantic.id IS NOT NULL)
          AND p.passage_type NOT LIKE 'state:%'
        ORDER BY score DESC
        LIMIT :limit
    """)
    result = await session.execute(
        sql, {"query": query, "embedding": str(query_embedding), "limit": limit}
    )
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

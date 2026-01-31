"""Passage search service supporting FTS, semantic, and hybrid search."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.config import get_settings
from kp3.processors.embedding import generate_embedding

# Search mode type - single source of truth
SearchMode = Literal["fts", "semantic", "hybrid"]

# Search type - content search vs tag search
SearchType = Literal["content", "tags"]


class PassageSearchResult(BaseModel):
    """A single passage search result."""

    id: UUID
    content: str
    passage_type: str
    score: float


def _build_timestamp_filters(
    *,
    period_start_after: datetime | None = None,
    period_end_before: datetime | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> tuple[str, dict[str, object]]:
    """Build SQL WHERE clauses for timestamp filters.

    Returns:
        Tuple of (SQL fragment, params dict)
    """
    clauses: list[str] = []
    params: dict[str, object] = {}

    if period_start_after is not None:
        clauses.append("p.period_start >= :period_start_after")
        params["period_start_after"] = period_start_after

    if period_end_before is not None:
        clauses.append("p.period_end <= :period_end_before")
        params["period_end_before"] = period_end_before

    if created_after is not None:
        clauses.append("p.created_at >= :created_after")
        params["created_after"] = created_after

    if created_before is not None:
        clauses.append("p.created_at <= :created_before")
        params["created_before"] = created_before

    sql_fragment = " AND ".join(clauses) if clauses else ""
    return sql_fragment, params


async def search_passages(
    session: AsyncSession,
    query: str,
    *,
    search_type: SearchType = "content",
    mode: SearchMode = "hybrid",
    limit: int = 5,
    agent_id: str,
    scope_ids: set[UUID] | None = None,
    period_start_after: datetime | None = None,
    period_end_before: datetime | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> list[PassageSearchResult]:
    """Search passages using FTS, semantic, or hybrid search.

    Args:
        session: Database session
        query: Search query text
        search_type: "content" (search passage content) or "tags" (search by tag names)
        mode: Search mode - "fts" (full-text), "semantic" (vector), or "hybrid" (RRF fusion)
        limit: Maximum number of results to return
        agent_id: Agent ID to scope results (required)
        scope_ids: Optional set of passage IDs to restrict search to (pre-resolved scope)
        period_start_after: Filter passages with period_start >= this value
        period_end_before: Filter passages with period_end <= this value
        created_after: Filter passages with created_at >= this value
        created_before: Filter passages with created_at <= this value

    Returns:
        List of passage search results ordered by relevance score

    Raises:
        ValueError: If agent_id is empty
    """
    if not agent_id:
        raise ValueError("agent_id is required for search")

    # If scope_ids is empty set, return no results (empty scope)
    if scope_ids is not None and len(scope_ids) == 0:
        return []

    timestamp_filters, timestamp_params = _build_timestamp_filters(
        period_start_after=period_start_after,
        period_end_before=period_end_before,
        created_after=created_after,
        created_before=created_before,
    )

    if search_type == "tags":
        if mode == "fts":
            return await _search_passages_by_tags_fts(
                session, query, limit, agent_id, timestamp_filters, timestamp_params, scope_ids
            )
        elif mode == "semantic":
            return await _search_passages_by_tags_semantic(
                session, query, limit, agent_id, timestamp_filters, timestamp_params, scope_ids
            )
        else:  # hybrid
            return await _search_passages_by_tags_hybrid(
                session, query, limit, agent_id, timestamp_filters, timestamp_params, scope_ids
            )
    else:  # content
        if mode == "fts":
            return await _search_fts(
                session, query, limit, agent_id, timestamp_filters, timestamp_params, scope_ids
            )
        elif mode == "semantic":
            return await _search_semantic(
                session, query, limit, agent_id, timestamp_filters, timestamp_params, scope_ids
            )
        else:  # hybrid
            return await _search_hybrid(
                session, query, limit, agent_id, timestamp_filters, timestamp_params, scope_ids
            )


async def _search_fts(
    session: AsyncSession,
    query: str,
    limit: int,
    agent_id: str,
    timestamp_filters: str,
    timestamp_params: dict[str, object],
    scope_ids: set[UUID] | None = None,
) -> list[PassageSearchResult]:
    """Full-text search on passage content using PostgreSQL tsvector."""
    where_clause = (
        "p.content_tsv @@ websearch_to_tsquery('english', :query) AND p.agent_id = :agent_id"
    )
    if timestamp_filters:
        where_clause += f" AND {timestamp_filters}"
    if scope_ids is not None:
        where_clause += " AND p.id = ANY(:scope_ids)"

    sql = text(f"""
        SELECT p.id, p.content, p.passage_type,
               ts_rank(p.content_tsv, websearch_to_tsquery('english', :query)) as score
        FROM passages p
        WHERE {where_clause}
        ORDER BY score DESC
        LIMIT :limit
    """)
    params: dict[str, object] = {
        "query": query,
        "limit": limit,
        "agent_id": agent_id,
        **timestamp_params,
    }
    if scope_ids is not None:
        params["scope_ids"] = list(scope_ids)
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
    timestamp_filters: str,
    timestamp_params: dict[str, object],
    scope_ids: set[UUID] | None = None,
) -> list[PassageSearchResult]:
    """Semantic search on passage content using vector similarity."""
    query_embedding = await generate_embedding(query)

    where_clause = "p.embedding_openai IS NOT NULL AND p.agent_id = :agent_id"
    if timestamp_filters:
        where_clause += f" AND {timestamp_filters}"
    if scope_ids is not None:
        where_clause += " AND p.id = ANY(:scope_ids)"

    sql = text(f"""
        WITH query_vec AS (
            SELECT cast(:embedding as vector) as vec
        ),
        scored AS (
            SELECT p.id, p.content, p.passage_type,
                   1 - (p.embedding_openai <=> q.vec) as score
            FROM passages p, query_vec q
            WHERE {where_clause}
        )
        SELECT * FROM scored ORDER BY score DESC LIMIT :limit
    """)
    params: dict[str, object] = {
        "embedding": str(query_embedding),
        "limit": limit,
        "agent_id": agent_id,
        **timestamp_params,
    }
    if scope_ids is not None:
        params["scope_ids"] = list(scope_ids)
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
    timestamp_filters: str,
    timestamp_params: dict[str, object],
    scope_ids: set[UUID] | None = None,
) -> list[PassageSearchResult]:
    """Hybrid search on passage content combining FTS, semantic, and recency with RRF."""
    settings = get_settings()
    query_embedding = await generate_embedding(query)

    # Build filter clause for timestamp filters
    filter_where = "p.agent_id = :agent_id"
    if timestamp_filters:
        filter_where += f" AND {timestamp_filters}"
    if scope_ids is not None:
        filter_where += " AND p.id = ANY(:scope_ids)"

    sql = text(f"""
        WITH query_vec AS (
            SELECT cast(:embedding as vector) as vec
        ),
        fts AS (
            SELECT p.id,
                   row_number() OVER (
                       ORDER BY ts_rank(p.content_tsv, websearch_to_tsquery('english', :query)) DESC
                   ) as rank
            FROM passages p
            WHERE p.content_tsv @@ websearch_to_tsquery('english', :query)
              AND {filter_where}
        ),
        semantic AS (
            SELECT p.id, row_number() OVER (ORDER BY p.embedding_openai <=> q.vec) as rank
            FROM passages p, query_vec q
            WHERE p.embedding_openai IS NOT NULL
              AND {filter_where}
        ),
        recency AS (
            SELECT p.id, row_number() OVER (ORDER BY p.created_at DESC) as rank
            FROM passages p
            WHERE {filter_where}
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
          AND {filter_where}
        ORDER BY score DESC
        LIMIT :limit
    """)
    params: dict[str, object] = {
        "query": query,
        "embedding": str(query_embedding),
        "limit": limit,
        "agent_id": agent_id,
        "w_fts": settings.rrf_weight_fts,
        "w_semantic": settings.rrf_weight_semantic,
        "w_recency": settings.rrf_weight_recency,
        **timestamp_params,
    }
    if scope_ids is not None:
        params["scope_ids"] = list(scope_ids)
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


# =============================================================================
# Tag-based search functions
# =============================================================================


async def _search_passages_by_tags_fts(
    session: AsyncSession,
    query: str,
    limit: int,
    agent_id: str,
    timestamp_filters: str,
    timestamp_params: dict[str, object],
    scope_ids: set[UUID] | None = None,
) -> list[PassageSearchResult]:
    """Search passages by matching tags using FTS on tag names/descriptions."""
    passage_filter = "p.agent_id = :agent_id"
    if timestamp_filters:
        passage_filter += f" AND {timestamp_filters}"
    if scope_ids is not None:
        passage_filter += " AND p.id = ANY(:scope_ids)"

    sql = text(f"""
        WITH tag_scores AS (
            SELECT t.id as tag_id,
                   ts_rank(t.name_tsv, websearch_to_tsquery('english', :query)) as score
            FROM tags t
            WHERE t.name_tsv @@ websearch_to_tsquery('english', :query)
              AND t.agent_id = :agent_id
        ),
        passage_scores AS (
            SELECT DISTINCT ON (p.id) p.id, p.content, p.passage_type, ts.score
            FROM passages p
            JOIN passage_tags pt ON pt.passage_id = p.id
            JOIN tag_scores ts ON ts.tag_id = pt.tag_id
            WHERE {passage_filter}
            ORDER BY p.id, ts.score DESC
        )
        SELECT * FROM passage_scores
        ORDER BY score DESC
        LIMIT :limit
    """)
    params: dict[str, object] = {
        "query": query,
        "limit": limit,
        "agent_id": agent_id,
        **timestamp_params,
    }
    if scope_ids is not None:
        params["scope_ids"] = list(scope_ids)
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


async def _search_passages_by_tags_semantic(
    session: AsyncSession,
    query: str,
    limit: int,
    agent_id: str,
    timestamp_filters: str,
    timestamp_params: dict[str, object],
    scope_ids: set[UUID] | None = None,
) -> list[PassageSearchResult]:
    """Search passages by matching tags using semantic search on tag embeddings."""
    query_embedding = await generate_embedding(query)

    passage_filter = "p.agent_id = :agent_id"
    if timestamp_filters:
        passage_filter += f" AND {timestamp_filters}"
    if scope_ids is not None:
        passage_filter += " AND p.id = ANY(:scope_ids)"

    sql = text(f"""
        WITH query_vec AS (
            SELECT cast(:embedding as vector) as vec
        ),
        tag_scores AS (
            SELECT t.id as tag_id,
                   1 - (t.embedding_openai <=> q.vec) as score
            FROM tags t, query_vec q
            WHERE t.embedding_openai IS NOT NULL
              AND t.agent_id = :agent_id
        ),
        passage_scores AS (
            SELECT DISTINCT ON (p.id) p.id, p.content, p.passage_type, ts.score
            FROM passages p
            JOIN passage_tags pt ON pt.passage_id = p.id
            JOIN tag_scores ts ON ts.tag_id = pt.tag_id
            WHERE {passage_filter}
            ORDER BY p.id, ts.score DESC
        )
        SELECT * FROM passage_scores
        ORDER BY score DESC
        LIMIT :limit
    """)
    params: dict[str, object] = {
        "embedding": str(query_embedding),
        "limit": limit,
        "agent_id": agent_id,
        **timestamp_params,
    }
    if scope_ids is not None:
        params["scope_ids"] = list(scope_ids)
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


async def _search_passages_by_tags_hybrid(
    session: AsyncSession,
    query: str,
    limit: int,
    agent_id: str,
    timestamp_filters: str,
    timestamp_params: dict[str, object],
    scope_ids: set[UUID] | None = None,
) -> list[PassageSearchResult]:
    """Search passages by matching tags using hybrid RRF fusion."""
    settings = get_settings()
    query_embedding = await generate_embedding(query)

    passage_filter = "p.agent_id = :agent_id"
    if timestamp_filters:
        passage_filter += f" AND {timestamp_filters}"
    if scope_ids is not None:
        passage_filter += " AND p.id = ANY(:scope_ids)"

    sql = text(f"""
        WITH query_vec AS (
            SELECT cast(:embedding as vector) as vec
        ),
        -- FTS ranking of tags
        tag_fts AS (
            SELECT t.id as tag_id,
                   row_number() OVER (
                       ORDER BY ts_rank(t.name_tsv, websearch_to_tsquery('english', :query)) DESC
                   ) as rank
            FROM tags t
            WHERE t.name_tsv @@ websearch_to_tsquery('english', :query)
              AND t.agent_id = :agent_id
        ),
        -- Semantic ranking of tags
        tag_semantic AS (
            SELECT t.id as tag_id,
                   row_number() OVER (ORDER BY t.embedding_openai <=> q.vec) as rank
            FROM tags t, query_vec q
            WHERE t.embedding_openai IS NOT NULL
              AND t.agent_id = :agent_id
        ),
        -- Combined tag scores using RRF
        tag_rrf AS (
            SELECT COALESCE(tf.tag_id, ts.tag_id) as tag_id,
                   :w_fts * COALESCE(1.0 / (60 + tf.rank), 0) +
                   :w_semantic * COALESCE(1.0 / (60 + ts.rank), 0) as score
            FROM tag_fts tf
            FULL OUTER JOIN tag_semantic ts ON tf.tag_id = ts.tag_id
            WHERE tf.tag_id IS NOT NULL OR ts.tag_id IS NOT NULL
        ),
        -- Map tags to passages, taking best tag score per passage
        passage_scores AS (
            SELECT DISTINCT ON (p.id) p.id, p.content, p.passage_type, tr.score
            FROM passages p
            JOIN passage_tags pt ON pt.passage_id = p.id
            JOIN tag_rrf tr ON tr.tag_id = pt.tag_id
            WHERE {passage_filter}
            ORDER BY p.id, tr.score DESC
        )
        SELECT * FROM passage_scores
        ORDER BY score DESC
        LIMIT :limit
    """)
    params: dict[str, object] = {
        "query": query,
        "embedding": str(query_embedding),
        "limit": limit,
        "agent_id": agent_id,
        "w_fts": settings.rrf_weight_fts,
        "w_semantic": settings.rrf_weight_semantic,
        **timestamp_params,
    }
    if scope_ids is not None:
        params["scope_ids"] = list(scope_ids)
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

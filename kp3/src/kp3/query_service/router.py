"""REST API router for passage search."""

from fastapi import APIRouter, Query

from kp3.db.engine import async_session
from kp3.query_service.models import PassageResult, SearchResponse
from kp3.services.search import SearchMode, search_passages

router = APIRouter(prefix="/passages", tags=["passages"])


@router.get("/search", response_model=SearchResponse)
async def search(
    query: str = Query(min_length=1, description="Search query text"),
    mode: SearchMode = Query(
        default="hybrid",
        description="Search mode: fts, semantic, or hybrid",
    ),
    limit: int = Query(default=5, ge=1, le=50, description="Maximum results"),
) -> SearchResponse:
    """Search passages using full-text, semantic, or hybrid search.

    - **fts**: Full-text search using PostgreSQL tsvector
    - **semantic**: Vector similarity search using embeddings
    - **hybrid**: Reciprocal Rank Fusion combining both methods (default)
    """
    async with async_session() as session:
        results = await search_passages(session, query, mode=mode, limit=limit)

    return SearchResponse(
        query=query,
        mode=mode,
        results=[
            PassageResult(
                id=r.id,
                content=r.content,
                passage_type=r.passage_type,
                score=r.score,
            )
            for r in results
        ],
        count=len(results),
    )

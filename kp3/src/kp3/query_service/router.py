"""REST API router for passage search and management."""

from fastapi import APIRouter, HTTPException, Query
from kairix_common.kp3_client import (
    PassageCreate,
    PassageCreateResponse,
    PassageResult,
    PromptResponse,
    SearchResponse,
)

from kp3.db.engine import async_session
from kp3.services.passages import create_passage
from kp3.services.prompts import get_active_prompt
from kp3.services.search import SearchMode, search_passages

router = APIRouter(tags=["passages"])


@router.get("/passages/search", response_model=SearchResponse)
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


@router.post("/passages", response_model=PassageCreateResponse)
async def create_new_passage(payload: PassageCreate) -> PassageCreateResponse:
    """Create a new passage.

    The passage will be automatically embedded for semantic search.
    Duplicate content (by SHA256 hash) will be rejected.
    """
    async with async_session() as session:
        passage = await create_passage(
            session,
            content=payload.content,
            passage_type=payload.passage_type,
            metadata=payload.metadata,
            period_start=payload.period_start,
            period_end=payload.period_end,
        )
        await session.commit()

        return PassageCreateResponse(
            id=passage.id,
            content=passage.content,
            passage_type=passage.passage_type,
        )


@router.get("/prompts/{name}", response_model=PromptResponse)
async def get_prompt_by_name(name: str) -> PromptResponse:
    """Get the active prompt by name.

    Returns the currently active version of the named prompt.
    """
    async with async_session() as session:
        prompt = await get_active_prompt(session, name)

    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")

    return PromptResponse(
        id=str(prompt.id),
        name=prompt.name,
        version=prompt.version,
        system_prompt=prompt.system_prompt,
        user_prompt_template=prompt.user_prompt_template,
        field_descriptions=prompt.field_descriptions or {},
    )

"""REST API router for passage search and management."""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query

from kp3.db.engine import async_session
from kp3.processors.embedding import generate_embedding
from kp3.schemas.api import (
    PassageCreate,
    PassageCreateResponse,
    PassageResult,
    PassageTagsRequest,
    PassageTagsResponse,
    PromptResponse,
    SearchResponse,
    TagCreate,
    TagListResponse,
    TagResponse,
)
from kp3.schemas.scope import (
    MemoryScopeCreate,
    MemoryScopeListResponse,
    MemoryScopeResponse,
    ScopeAddRequest,
    ScopedPassageCreate,
    ScopedPassageCreateResponse,
    ScopedSearchResponse,
    ScopeHistoryEntry,
    ScopeHistoryResponse,
    ScopeModifyResponse,
    ScopeRemoveRequest,
    ScopeRevertRequest,
    ScopeRevertResponse,
)
from kp3.services.passages import create_passage
from kp3.services.prompts import get_active_prompt
from kp3.services.scopes import (
    add_passages_to_scope,
    add_refs_to_scope,
    create_passage_in_scope,
    create_scope,
    delete_scope,
    get_current_version,
    get_scope,
    get_scope_history,
    list_scopes,
    remove_from_scope,
    resolve_scope,
    revert_scope,
)
from kp3.services.search import SearchMode, SearchType, search_passages
from kp3.services.tags import (
    attach_tags_to_passage,
    create_tag,
    delete_tag,
    detach_tags_from_passage,
    get_passage_tags,
    get_tag,
    list_tags,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["passages"])


@router.get("/passages/search", response_model=SearchResponse)
async def search(
    query: str = Query(min_length=1, description="Search query text"),
    search_type: SearchType = Query(
        default="content",
        description="Search type: content (search passage text) or tags (search by tag names)",
    ),
    mode: SearchMode = Query(
        default="hybrid",
        description="Search mode: fts, semantic, or hybrid",
    ),
    limit: int = Query(default=5, ge=1, le=50, description="Maximum results"),
    period_start_after: datetime | None = Query(
        default=None, description="Filter: period_start >= this value"
    ),
    period_end_before: datetime | None = Query(
        default=None, description="Filter: period_end <= this value"
    ),
    created_after: datetime | None = Query(
        default=None, description="Filter: created_at >= this value"
    ),
    created_before: datetime | None = Query(
        default=None, description="Filter: created_at <= this value"
    ),
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> SearchResponse:
    """Search passages using full-text, semantic, or hybrid search.

    **Search types:**
    - **content**: Search passage content directly (default)
    - **tags**: Search by tag names/descriptions, return passages with matching tags

    **Search modes (apply to both types):**
    - **fts**: Full-text search using PostgreSQL tsvector
    - **semantic**: Vector similarity search using embeddings
    - **hybrid**: Reciprocal Rank Fusion combining both methods (default)

    **Timestamp filters** can be applied to both search types.

    Requires X-Agent-ID header. Only returns passages for that specific agent.
    """
    async with async_session() as session:
        results = await search_passages(
            session,
            query,
            search_type=search_type,
            mode=mode,
            limit=limit,
            agent_id=x_agent_id,
            period_start_after=period_start_after,
            period_end_before=period_end_before,
            created_after=created_after,
            created_before=created_before,
        )

    return SearchResponse(
        query=query,
        mode=mode,
        search_type=search_type,
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
async def create_new_passage(
    payload: PassageCreate,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> PassageCreateResponse:
    """Create a new passage.

    All passages are automatically embedded for semantic search.
    Duplicate content (by SHA256 hash) will be rejected.

    Requires X-Agent-ID header to scope passage to an agent.
    """
    # Generate embedding (required for all passages)
    try:
        embedding = await generate_embedding(payload.content)
        logger.info(
            "Generated embedding for %s passage (%d dims)",
            payload.passage_type,
            len(embedding),
        )
    except Exception as e:
        logger.exception("Failed to generate embedding")
        raise HTTPException(status_code=502, detail=f"Embedding generation failed: {e}") from e

    async with async_session() as session:
        passage = await create_passage(
            session,
            content=payload.content,
            passage_type=payload.passage_type,
            metadata=payload.metadata,
            period_start=payload.period_start,
            period_end=payload.period_end,
            embedding_openai=embedding,
            agent_id=x_agent_id,
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


# =============================================================================
# Tag endpoints
# =============================================================================


@router.post("/tags", response_model=TagResponse, status_code=201)
async def create_new_tag(
    payload: TagCreate,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> TagResponse:
    """Create a new tag.

    Tags are automatically embedded for semantic search.
    Tags are deduplicated by canonical name (lowercase, normalized whitespace).

    Requires X-Agent-ID header to scope tag to an agent.
    """
    async with async_session() as session:
        try:
            tag = await create_tag(
                session,
                name=payload.name,
                agent_id=x_agent_id,
                description=payload.description,
            )
            await session.commit()
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

        return TagResponse(
            id=tag.id,
            name=tag.name,
            description=tag.description,
            passage_count=tag.passage_count,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        )


@router.get("/tags", response_model=TagListResponse)
async def list_all_tags(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    order_by: str = Query(
        default="name",
        description="Order by: name, created_at, passage_count",
    ),
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> TagListResponse:
    """List all tags for the agent.

    Requires X-Agent-ID header. Only returns tags for that specific agent.
    """
    async with async_session() as session:
        tags = await list_tags(
            session,
            agent_id=x_agent_id,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

        return TagListResponse(
            tags=[
                TagResponse(
                    id=t.id,
                    name=t.name,
                    description=t.description,
                    passage_count=t.passage_count,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                for t in tags
            ],
            count=len(tags),
        )


@router.get("/tags/{tag_id}", response_model=TagResponse)
async def get_tag_by_id(
    tag_id: UUID,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> TagResponse:
    """Get a tag by ID.

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        tag = await get_tag(session, tag_id, x_agent_id)

    if not tag:
        raise HTTPException(status_code=404, detail=f"Tag '{tag_id}' not found")

    return TagResponse(
        id=tag.id,
        name=tag.name,
        description=tag.description,
        passage_count=tag.passage_count,
        created_at=tag.created_at,
        updated_at=tag.updated_at,
    )


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag_by_id(
    tag_id: UUID,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> None:
    """Delete a tag.

    This will also remove the tag from all passages it was attached to.

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        deleted = await delete_tag(session, tag_id, x_agent_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Tag '{tag_id}' not found")
        await session.commit()


# =============================================================================
# Passage-tag endpoints
# =============================================================================


@router.get("/passages/{passage_id}/tags", response_model=PassageTagsResponse)
async def get_tags_for_passage(
    passage_id: UUID,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> PassageTagsResponse:
    """Get all tags attached to a passage.

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        tags = await get_passage_tags(session, passage_id, x_agent_id)

        return PassageTagsResponse(
            passage_id=passage_id,
            tags=[
                TagResponse(
                    id=t.id,
                    name=t.name,
                    description=t.description,
                    passage_count=t.passage_count,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                for t in tags
            ],
        )


@router.post("/passages/{passage_id}/tags", response_model=PassageTagsResponse)
async def attach_tags_to_passage_endpoint(
    passage_id: UUID,
    payload: PassageTagsRequest,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> PassageTagsResponse:
    """Attach tags to a passage.

    Tags that are already attached will be silently ignored.

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        await attach_tags_to_passage(session, passage_id, payload.tag_ids, x_agent_id)
        await session.commit()

        tags = await get_passage_tags(session, passage_id, x_agent_id)

        return PassageTagsResponse(
            passage_id=passage_id,
            tags=[
                TagResponse(
                    id=t.id,
                    name=t.name,
                    description=t.description,
                    passage_count=t.passage_count,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                for t in tags
            ],
        )


@router.delete("/passages/{passage_id}/tags", response_model=PassageTagsResponse)
async def detach_tags_from_passage_endpoint(
    passage_id: UUID,
    payload: PassageTagsRequest,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> PassageTagsResponse:
    """Detach tags from a passage.

    Tags that are not attached will be silently ignored.

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        await detach_tags_from_passage(session, passage_id, payload.tag_ids, x_agent_id)
        await session.commit()

        tags = await get_passage_tags(session, passage_id, x_agent_id)

        return PassageTagsResponse(
            passage_id=passage_id,
            tags=[
                TagResponse(
                    id=t.id,
                    name=t.name,
                    description=t.description,
                    passage_count=t.passage_count,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                for t in tags
            ],
        )


# =============================================================================
# Memory Scope endpoints
# =============================================================================


@router.post("/scopes", response_model=MemoryScopeResponse, status_code=201)
async def create_new_scope(
    payload: MemoryScopeCreate,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> MemoryScopeResponse:
    """Create a new memory scope.

    Scopes define dynamic search closures using refs and literal passage IDs.
    The scope is initialized with an empty definition.

    Requires X-Agent-ID header to scope the scope to an agent.
    """
    async with async_session() as session:
        try:
            scope = await create_scope(
                session,
                name=payload.name,
                agent_id=x_agent_id,
                description=payload.description,
            )
            await session.commit()
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

        return MemoryScopeResponse(
            id=scope.id,
            name=scope.name,
            agent_id=scope.agent_id,
            head_ref=scope.head_ref,
            description=scope.description,
            created_at=scope.created_at,
            updated_at=scope.updated_at,
        )


@router.get("/scopes", response_model=MemoryScopeListResponse)
async def list_all_scopes(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> MemoryScopeListResponse:
    """List all memory scopes for the agent.

    Requires X-Agent-ID header. Only returns scopes for that specific agent.
    """
    async with async_session() as session:
        scopes = await list_scopes(session, x_agent_id, limit=limit, offset=offset)

        return MemoryScopeListResponse(
            scopes=[
                MemoryScopeResponse(
                    id=s.id,
                    name=s.name,
                    agent_id=s.agent_id,
                    head_ref=s.head_ref,
                    description=s.description,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
                for s in scopes
            ],
            count=len(scopes),
        )


@router.get("/scopes/{name}", response_model=MemoryScopeResponse)
async def get_scope_by_name(
    name: str,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> MemoryScopeResponse:
    """Get a scope by name.

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        scope = await get_scope(session, name, x_agent_id)

    if not scope:
        raise HTTPException(status_code=404, detail=f"Scope '{name}' not found")

    return MemoryScopeResponse(
        id=scope.id,
        name=scope.name,
        agent_id=scope.agent_id,
        head_ref=scope.head_ref,
        description=scope.description,
        created_at=scope.created_at,
        updated_at=scope.updated_at,
    )


@router.delete("/scopes/{name}", status_code=204)
async def delete_scope_by_name(
    name: str,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> None:
    """Delete a scope.

    Note: This does not delete the scope definition passages or ref history.

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        deleted = await delete_scope(session, name, x_agent_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Scope '{name}' not found")
        await session.commit()


@router.post("/scopes/{name}/passages", response_model=ScopedPassageCreateResponse, status_code=201)
async def create_passage_in_scope_endpoint(
    name: str,
    payload: ScopedPassageCreate,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> ScopedPassageCreateResponse:
    """Create a passage and add it to the scope atomically.

    The passage is automatically embedded for semantic search.

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        scope = await get_scope(session, name, x_agent_id)
        if not scope:
            raise HTTPException(status_code=404, detail=f"Scope '{name}' not found")

        # Generate embedding
        try:
            embedding = await generate_embedding(payload.content)
        except Exception as e:
            logger.exception("Failed to generate embedding")
            raise HTTPException(status_code=502, detail=f"Embedding generation failed: {e}") from e

        passage, new_version = await create_passage_in_scope(
            session,
            scope,
            content=payload.content,
            passage_type=payload.passage_type,
            metadata=payload.metadata,
            period_start=payload.period_start,
            period_end=payload.period_end,
            embedding_openai=embedding,
        )
        await session.commit()

        return ScopedPassageCreateResponse(
            passage_id=passage.id,
            content=passage.content,
            passage_type=passage.passage_type,
            scope_version=new_version,
        )


@router.post("/scopes/{name}/add", response_model=ScopeModifyResponse)
async def add_to_scope(
    name: str,
    payload: ScopeAddRequest,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> ScopeModifyResponse:
    """Add passages and/or refs to a scope.

    Passages that don't exist are silently ignored.
    Refs are added without validation (resolved at search time).

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        scope = await get_scope(session, name, x_agent_id)
        if not scope:
            raise HTTPException(status_code=404, detail=f"Scope '{name}' not found")

        total_added = 0
        new_version = await get_current_version(session, scope)

        if payload.passage_ids:
            new_version, passages_added = await add_passages_to_scope(
                session, scope, payload.passage_ids
            )
            total_added += passages_added

        if payload.refs:
            new_version, refs_added = await add_refs_to_scope(session, scope, payload.refs)
            total_added += refs_added

        await session.commit()

        return ScopeModifyResponse(
            scope_version=new_version,
            modified_count=total_added,
        )


@router.post("/scopes/{name}/remove", response_model=ScopeModifyResponse)
async def remove_from_scope_endpoint(
    name: str,
    payload: ScopeRemoveRequest,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> ScopeModifyResponse:
    """Remove passages and/or refs from a scope.

    Items that are not in the scope are silently ignored.

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        scope = await get_scope(session, name, x_agent_id)
        if not scope:
            raise HTTPException(status_code=404, detail=f"Scope '{name}' not found")

        new_version, total_removed = await remove_from_scope(
            session,
            scope,
            passage_ids=payload.passage_ids if payload.passage_ids else None,
            refs=payload.refs if payload.refs else None,
        )
        await session.commit()

        return ScopeModifyResponse(
            scope_version=new_version,
            modified_count=total_removed,
        )


@router.get("/scopes/{name}/history", response_model=ScopeHistoryResponse)
async def get_scope_history_endpoint(
    name: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum entries"),
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> ScopeHistoryResponse:
    """Get the history of scope changes.

    Returns history entries ordered by most recent first.

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        scope = await get_scope(session, name, x_agent_id)
        if not scope:
            raise HTTPException(status_code=404, detail=f"Scope '{name}' not found")

        history = await get_scope_history(session, scope, limit=limit)

        return ScopeHistoryResponse(
            history=[
                ScopeHistoryEntry(
                    version=h["version"],
                    changed_at=h["changed_at"],
                    passage_id=h["passage_id"],
                )
                for h in history
            ],
            count=len(history),
        )


@router.post("/scopes/{name}/revert", response_model=ScopeRevertResponse)
async def revert_scope_endpoint(
    name: str,
    payload: ScopeRevertRequest,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> ScopeRevertResponse:
    """Revert a scope to a previous version.

    Creates a new version with the same definition as the target version.
    This is non-destructive - history is preserved.

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        scope = await get_scope(session, name, x_agent_id)
        if not scope:
            raise HTTPException(status_code=404, detail=f"Scope '{name}' not found")

        try:
            new_version, reverted_from = await revert_scope(session, scope, payload.to_version)
            await session.commit()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        return ScopeRevertResponse(
            scope_version=new_version,
            reverted_from=reverted_from,
        )


@router.get("/scopes/{name}/search", response_model=ScopedSearchResponse)
async def search_in_scope(
    name: str,
    query: str = Query(min_length=1, description="Search query text"),
    search_type: SearchType = Query(
        default="content",
        description="Search type: content or tags",
    ),
    mode: SearchMode = Query(
        default="hybrid",
        description="Search mode: fts, semantic, or hybrid",
    ),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results"),
    period_start_after: datetime | None = Query(
        default=None, description="Filter: period_start >= this value"
    ),
    period_end_before: datetime | None = Query(
        default=None, description="Filter: period_end <= this value"
    ),
    created_after: datetime | None = Query(
        default=None, description="Filter: created_at >= this value"
    ),
    created_before: datetime | None = Query(
        default=None, description="Filter: created_at <= this value"
    ),
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> ScopedSearchResponse:
    """Search passages within a scope.

    Only searches passages that are part of the scope (via literal IDs or resolved refs).

    Requires X-Agent-ID header.
    """
    async with async_session() as session:
        scope = await get_scope(session, name, x_agent_id)
        if not scope:
            raise HTTPException(status_code=404, detail=f"Scope '{name}' not found")

        # Resolve scope to passage IDs
        scope_ids = await resolve_scope(session, scope)
        scope_version = await get_current_version(session, scope)

        # If scope is empty, return empty results
        if not scope_ids:
            return ScopedSearchResponse(
                query=query,
                mode=mode,
                search_type=search_type,
                results=[],
                count=0,
                scope=name,
                scope_version=scope_version,
            )

        # Search within scope
        results = await search_passages(
            session,
            query,
            search_type=search_type,
            mode=mode,
            limit=limit,
            agent_id=x_agent_id,
            scope_ids=scope_ids,
            period_start_after=period_start_after,
            period_end_before=period_end_before,
            created_after=created_after,
            created_before=created_before,
        )

        return ScopedSearchResponse(
            query=query,
            mode=mode,
            search_type=search_type,
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
            scope=name,
            scope_version=scope_version,
        )

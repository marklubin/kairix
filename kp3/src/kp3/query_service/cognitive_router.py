"""REST API router for cognitive memory endpoints.

Implements the Unified Cognitive Memory Architecture API:
- Refs: mutable pointers to passages with optimistic locking
- Derivations: provenance tracking
- Frames: cognitive configuration closures
- Cognition increment: atomic state transitions
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Path, Query
from sqlalchemy import select

from kp3.db import engine as db_engine
from kp3.db.models import Passage, PassageRef
from kp3.query_service.schemas import (
    CognitionIncrementRequest,
    CognitionIncrementResponse,
    DerivationDerivedResponse,
    DerivationInfo,
    DerivationSourceResponse,
    FrameActivateResponse,
    FrameCreateRequest,
    FrameForkRequest,
    FrameResolveResponse,
    FrameResponse,
    PassageResponse,
    PerceptionConfig,
    RefHistoryEntry,
    RefHistoryResponse,
    RefListResponse,
    RefResponse,
    RefUpdateInfo,
    RefUpdateRequest,
    RefUpdateResponse,
    RefWithPassageResponse,
)
from kp3.services.cognition import (
    CognitionConflictError,
    CognitionFrameError,
    increment_perception,
)
from kp3.services.derivations import get_derived, get_sources
from kp3.services.frames import (
    activate_frame,
    create_frame,
    fork_frame,
    get_frame,
    get_ref_version,
    list_frames,
    resolve_frame,
)
from kp3.services.passages import get_passage
from kp3.services.refs import (
    delete_ref,
    get_ref,
    get_ref_history,
    list_refs,
    set_ref,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cognitive"])


# =============================================================================
# Ref Endpoints
# =============================================================================


# NOTE: History endpoint must come BEFORE the generic GET endpoint
# because {ref_name:path} is greedy and would match "/history" as part of the ref name
@router.get("/refs/{ref_name:path}/history", response_model=RefHistoryResponse)
async def get_ref_history_endpoint(
    ref_name: str = Path(..., description="Full ref name"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> RefHistoryResponse:
    """Get the change history for a ref."""
    async with db_engine.async_session() as session:
        history = await get_ref_history(session, ref_name, limit=limit)

        if not history:
            # Check if ref exists at all
            if await get_ref(session, ref_name) is None:
                raise HTTPException(status_code=404, detail=f"Ref '{ref_name}' not found")

        entries = [
            RefHistoryEntry(
                id=h["id"],
                ref_name=h["ref_name"],
                passage_id=h["passage_id"],
                previous_passage_id=h.get("previous_passage_id"),
                changed_at=h["changed_at"],
                metadata=h.get("metadata", {}),
            )
            for h in history
        ]

        return RefHistoryResponse(
            ref_name=ref_name,
            entries=entries,
            count=len(entries),
        )


@router.get("/refs/{ref_name:path}", response_model=RefWithPassageResponse)
async def get_ref_endpoint(
    ref_name: str = Path(..., description="Full ref name (e.g., 'test-agent/perception/persona')"),
    resolve: bool = Query(default=False, description="Include resolved passage content"),
) -> RefWithPassageResponse:
    """Get a ref by name, optionally with resolved passage content."""
    async with db_engine.async_session() as session:
        # Get ref
        stmt = select(PassageRef).where(PassageRef.name == ref_name)
        result = await session.execute(stmt)
        ref = result.scalar_one_or_none()

        if not ref:
            raise HTTPException(status_code=404, detail=f"Ref '{ref_name}' not found")

        # Get version
        version = await get_ref_version(session, ref_name)

        response = RefWithPassageResponse(
            name=ref.name,
            passage_id=ref.passage_id,
            version=version,
            updated_at=ref.updated_at,
            metadata=ref.metadata_ or {},
        )

        if resolve:
            passage = await session.get(Passage, ref.passage_id)
            if passage:
                response.passage_content = passage.content
                response.passage_type = passage.passage_type

        return response


@router.get("/refs", response_model=RefListResponse)
async def list_refs_endpoint(
    prefix: str | None = Query(default=None, description="Filter refs by prefix"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> RefListResponse:
    """List refs, optionally filtered by prefix."""
    async with db_engine.async_session() as session:
        refs_data = await list_refs(session, prefix=prefix, limit=limit)

        refs = []
        for r in refs_data:
            version = await get_ref_version(session, r["name"])
            refs.append(
                RefResponse(
                    name=r["name"],
                    passage_id=r["passage_id"],
                    version=version,
                    updated_at=r["updated_at"],
                    metadata=r.get("metadata", {}),
                )
            )

        return RefListResponse(refs=refs, count=len(refs))


@router.put("/refs/{ref_name:path}", response_model=RefUpdateResponse)
async def update_ref_endpoint(
    payload: RefUpdateRequest,
    ref_name: str = Path(..., description="Full ref name"),
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> RefUpdateResponse:
    """Update a ref to point to a new passage.

    Supports optimistic locking via expected_version.
    Returns 409 Conflict if version doesn't match.
    """
    async with db_engine.async_session() as session:
        # Get current state for optimistic locking
        current_passage_id = await get_ref(session, ref_name)
        current_version = await get_ref_version(session, ref_name)

        # Check optimistic lock
        if payload.expected_version is not None:
            if current_version != payload.expected_version:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "version_conflict",
                        "expected_version": payload.expected_version,
                        "actual_version": current_version,
                    },
                )

        # Verify passage exists
        passage = await get_passage(session, payload.passage_id)
        if not passage:
            raise HTTPException(
                status_code=404,
                detail=f"Passage '{payload.passage_id}' not found",
            )

        # Update ref
        ref = await set_ref(
            session,
            ref_name,
            payload.passage_id,
            metadata=payload.metadata,
            fire_hooks=True,  # Fire hooks by default
        )

        await session.commit()

        new_version = await get_ref_version(session, ref_name)

        return RefUpdateResponse(
            name=ref.name,
            passage_id=ref.passage_id,
            version=new_version,
            updated_at=ref.updated_at,
            previous_passage_id=current_passage_id,
        )


@router.delete("/refs/{ref_name:path}")
async def delete_ref_endpoint(
    ref_name: str = Path(..., description="Full ref name"),
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> dict[str, bool]:
    """Delete a ref."""
    async with db_engine.async_session() as session:
        deleted = await delete_ref(session, ref_name)
        await session.commit()

        if not deleted:
            raise HTTPException(status_code=404, detail=f"Ref '{ref_name}' not found")

        return {"deleted": True}


# =============================================================================
# Passage Endpoints (extended)
# =============================================================================


@router.get("/passages/{passage_id}", response_model=PassageResponse)
async def get_passage_endpoint(
    passage_id: UUID = Path(..., description="Passage UUID"),
) -> PassageResponse:
    """Get a passage by ID."""
    async with db_engine.async_session() as session:
        passage = await get_passage(session, passage_id)

        if not passage:
            raise HTTPException(status_code=404, detail=f"Passage '{passage_id}' not found")

        return PassageResponse(
            id=passage.id,
            content=passage.content,
            content_hash=passage.content_hash,
            passage_type=passage.passage_type,
            agent_id=passage.agent_id,
            metadata=passage.metadata_ or {},
            created_at=passage.created_at,
        )


# =============================================================================
# Derivation Endpoints
# =============================================================================


@router.get("/passages/{passage_id}/sources", response_model=DerivationSourceResponse)
async def get_passage_sources(
    passage_id: UUID = Path(..., description="Passage UUID"),
) -> DerivationSourceResponse:
    """Get the source passages that this passage was derived from."""
    async with db_engine.async_session() as session:
        # Verify passage exists
        passage = await get_passage(session, passage_id)
        if not passage:
            raise HTTPException(status_code=404, detail=f"Passage '{passage_id}' not found")

        sources = await get_sources(session, passage_id)

        return DerivationSourceResponse(
            passage_id=passage_id,
            sources=[s.id for s in sources],
            count=len(sources),
        )


@router.get("/passages/{passage_id}/derived", response_model=DerivationDerivedResponse)
async def get_passage_derived(
    passage_id: UUID = Path(..., description="Passage UUID"),
) -> DerivationDerivedResponse:
    """Get passages that were derived from this passage."""
    async with db_engine.async_session() as session:
        # Verify passage exists
        passage = await get_passage(session, passage_id)
        if not passage:
            raise HTTPException(status_code=404, detail=f"Passage '{passage_id}' not found")

        derived = await get_derived(session, passage_id)

        return DerivationDerivedResponse(
            passage_id=passage_id,
            derived=[d.id for d in derived],
            count=len(derived),
        )


# =============================================================================
# Frame Endpoints
# =============================================================================


@router.get("/frames", response_model=list[FrameResponse])
async def list_frames_endpoint(
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> list[FrameResponse]:
    """List all cognitive frames for the agent."""
    async with db_engine.async_session() as session:
        frames = await list_frames(session, x_agent_id)

        return [
            FrameResponse(
                id=f["id"],
                name=f["name"],
                agent_id=f["agent_id"],
                ref_name=f["ref_name"],
                perceptions=[PerceptionConfig(**p) for p in f["perceptions"]],
                cognition_config=f["cognition_config"],
                hooks_enabled=f["hooks_enabled"],
                created_at=f["created_at"],
            )
            for f in frames
        ]


@router.get("/frames/{name}", response_model=FrameResponse)
async def get_frame_endpoint(
    name: str = Path(..., description="Frame name"),
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> FrameResponse:
    """Get a cognitive frame by name."""
    async with db_engine.async_session() as session:
        frame = await get_frame(session, x_agent_id, name)

        if not frame:
            raise HTTPException(status_code=404, detail=f"Frame '{name}' not found")

        return FrameResponse(
            id=frame["id"],
            name=frame["name"],
            agent_id=frame["agent_id"],
            ref_name=frame["ref_name"],
            perceptions=[PerceptionConfig(**p) for p in frame["perceptions"]],
            cognition_config=frame["cognition_config"],
            hooks_enabled=frame["hooks_enabled"],
            created_at=frame["created_at"],
        )


@router.post("/frames", response_model=FrameResponse)
async def create_frame_endpoint(
    payload: FrameCreateRequest,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> FrameResponse:
    """Create a new cognitive frame."""
    async with db_engine.async_session() as session:
        try:
            frame = await create_frame(
                session,
                name=payload.name,
                agent_id=payload.agent_id,
                perceptions=[p.model_dump() for p in payload.perceptions],
                cognition_config=payload.cognition_config.model_dump(),
                hooks_enabled=payload.hooks_enabled,
            )
            await session.commit()
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from None

        return FrameResponse(
            id=frame["id"],
            name=frame["name"],
            agent_id=frame["agent_id"],
            ref_name=frame["ref_name"],
            perceptions=[PerceptionConfig(**p) for p in frame["perceptions"]],
            cognition_config=frame["cognition_config"],
            hooks_enabled=frame["hooks_enabled"],
            created_at=frame["created_at"],
        )


@router.post("/frames/{name}/fork", response_model=FrameResponse)
async def fork_frame_endpoint(
    payload: FrameForkRequest,
    name: str = Path(..., description="Source frame name"),
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> FrameResponse:
    """Fork an existing frame to create a derived version."""
    async with db_engine.async_session() as session:
        try:
            frame = await fork_frame(
                session,
                agent_id=x_agent_id,
                source_name=name,
                new_name=payload.new_name,
                hooks_enabled=payload.hooks_enabled,
            )
            await session.commit()
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from None

        return FrameResponse(
            id=frame["id"],
            name=frame["name"],
            agent_id=frame["agent_id"],
            ref_name=frame["ref_name"],
            perceptions=[PerceptionConfig(**p) for p in frame["perceptions"]],
            cognition_config=frame["cognition_config"],
            hooks_enabled=frame["hooks_enabled"],
            created_at=frame["created_at"],
        )


@router.post("/frames/{name}/activate", response_model=FrameActivateResponse)
async def activate_frame_endpoint(
    name: str = Path(..., description="Frame name to activate"),
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> FrameActivateResponse:
    """Activate a frame as the current active frame for the agent."""
    async with db_engine.async_session() as session:
        try:
            result = await activate_frame(session, x_agent_id, name)
            await session.commit()
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from None

        return FrameActivateResponse(
            frame_ref=result["frame_ref"],
            activated_at=result["activated_at"],
        )


@router.post("/frames/{name}/resolve", response_model=FrameResolveResponse)
async def resolve_frame_endpoint(
    name: str = Path(..., description="Frame name to resolve"),
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> FrameResolveResponse:
    """Resolve a frame to a frozen snapshot with pinned passage IDs."""
    async with db_engine.async_session() as session:
        try:
            result = await resolve_frame(session, x_agent_id, name)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from None

        return FrameResolveResponse(
            frame_name=result["frame_name"],
            agent_id=result["agent_id"],
            resolved_at=result["resolved_at"],
            pinned_refs=result["pinned_refs"],
        )


# =============================================================================
# Cognition Increment Endpoint
# =============================================================================


@router.post("/cognition/increment", response_model=CognitionIncrementResponse)
async def cognition_increment_endpoint(
    payload: CognitionIncrementRequest,
    x_agent_id: str = Header(..., alias="X-Agent-ID"),
) -> CognitionIncrementResponse:
    """Execute an atomic cognition increment.

    This is the primary write primitive for cognitive state transitions:
    1. Resolve frame closure
    2. Read previous perception state
    3. Compute next state via LLM
    4. Create new passage + derivation
    5. Advance ref using optimistic locking
    6. Fire hooks if enabled

    Returns:
        - 200: Success with new passage ID and derivation info
        - 409: Conflict - expected_previous_passage_id doesn't match current
        - 422: Unprocessable - frame closure missing required refs
        - 503: Service unavailable - LLM failure, no partial writes committed
    """
    async with db_engine.async_session() as session:
        try:
            result = await increment_perception(
                session,
                agent_id=payload.agent_id,
                frame_ref=payload.frame_ref,
                frame_snapshot_mode=payload.frame_snapshot_mode,
                perception_ref=payload.perception_ref,
                input_content=payload.input.content,
                input_content_type=payload.input.content_type,
                input_metadata=payload.input.metadata,
                context_refs=payload.context_refs,
                process_step_id=payload.process_step_id,
                llm_config=payload.llm_config,
                expected_previous_passage_id=payload.expected_previous_passage_id,
                idempotency_key=payload.idempotency_key,
                llm_stub=True,  # Use stub for now
            )
            await session.commit()

        except CognitionConflictError as e:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "conflict",
                    "ref_name": e.ref_name,
                    "expected_passage_id": str(e.expected_passage_id),
                    "actual_passage_id": str(e.actual_passage_id),
                },
            ) from None

        except CognitionFrameError as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "frame_error",
                    "message": str(e),
                    "missing_refs": e.missing_refs,
                },
            ) from None

        return CognitionIncrementResponse(
            ok=result["ok"],
            perception_ref=result["perception_ref"],
            previous_passage_id=result["previous_passage_id"],
            new_passage_id=result["new_passage_id"],
            derivation=DerivationInfo(
                derived_passage_id=result["derivation"]["derived_passage_id"],
                source_passage_ids=result["derivation"]["source_passage_ids"],
                context_passage_ids=result["derivation"]["context_passage_ids"],
                process_step_id=result["derivation"]["process_step_id"],
            ),
            ref_update=RefUpdateInfo(
                applied=result["ref_update"]["applied"],
                new_ref_version=result["ref_update"]["new_ref_version"],
            ),
            trace_id=result.get("trace_id"),
        )
